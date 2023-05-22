import os.path

from storytoolkitai.core.logger import *

import spacy
from spacy.language import Language
from spacy_langdetect import LanguageDetector

import tqdm
import hashlib
import json

import requests

class TextAnalysis:

    def __init__(self):

        self.spacy_model_name = None

        # initialize an empty spacy model
        # the processing function will load the model if needed
        self.spacy_model = None

    def detect_language(self, text: str):
        # create a factory for the LanguageDetector
        @Language.factory("language_detector")
        def create_language_detector(nlp, name):
            return LanguageDetector()

        # we can use this spacy model for initial language detection
        # and then switch to whatever we need
        nlp = self.load_spacy_language_model(model_name='en_core_web_sm')

        if not nlp:
            logger.error("Could not load spaCy language model to detect the language.")
            return None

        # add the LanguageDetector to the pipeline
        nlp.add_pipe('language_detector', last=True)

        # run the text through the pipeline
        doc = nlp(text)

        # get the language code
        lang_code = doc._.language['language']

        logger.debug("Detected language: " + lang_code)

        # delete the model and reset the spacy_model variables
        del nlp
        self.spacy_model = None
        self.spacy_model_name =None

        return lang_code

    def get_spacy_models(self, language):
        '''
        This queries the spaCy models repository on GitHub
        and returns a list of available models for the given language.
        '''
        models = []

        def fetch_models(url):

            response = requests.get(url)

            # get the model names from the response but strip the version number
            for model in response.json():

                if model['tag_name'].startswith(language) and model['tag_name'].split('-')[0] not in models:
                    models.append(model['tag_name'].split('-')[0])

            # Check if there's another page with models, if so call this function again
            next_link = response.links.get("next", None)
            if next_link:
                fetch_models(next_link['url'])

        try:
            logger.info("Checking spaCy models repository for models available for your language...")
            url = "https://api.github.com/repos/explosion/spacy-models/releases?per_page=100"
            fetch_models(url)
        except:
            logger.error('Could not fetch the list of available spaCy models. Please check your internet connection.')
            return None

        return models

    def auto_select_model(self, language):
        '''
        This function tries to automatically select the best model for the given language.
        '''

        # get the available models over the internet
        models = self.get_spacy_models(language)

        if models is not None:

            size_priority = ["lg", "md", "sm"]

            for size in size_priority:
                for model in models:
                    if model.endswith(size):
                        return model
        return None

    def load_spacy_language_model(self, lang: str = None, model_name: str = None):
        '''
        This function loads a spaCy language model.
        If the model is not installed, it will try to download it.
        '''

        from spacy.cli.download import download as spacy_model_download

        # start with an empty model
        model = None
        spacy_model_name = None

        # try to make use of the lang parameter if the model is not specified
        if model_name is None:

            # if the language is a string, use it auto select the model
            if isinstance(lang, str) and len(lang) > 0:
                spacy_model_name = self.auto_select_model(lang)

                if spacy_model_name is None:
                    logger.error(f'Could not find a spaCy model for {lang}.')
                    return None
                else:
                    logger.info(f'Using spaCy model {spacy_model_name} for {lang}.')

            # if the language is None, try to use the model that was set in the constructor
            if lang is None:
                spacy_model_name = self.spacy_model_name

        # if the model name is specified, use it
        else:
            spacy_model_name = model_name

        # abort if the model name is still None
        if spacy_model_name is None:
            logger.error('Could not load the spaCy model. Please specify a language.')
            return None

        # try to load the model
        try:
            model = spacy.load(spacy_model_name)

        # if there's an IOError, try to download the model
        except IOError:
            logger.info(f"Downloading spaCy {spacy_model_name} model...")

            # try to download the model
            try:
                spacy_model_download(spacy_model_name)

                # Load the model from the custom directory
                model = spacy.load(spacy_model_name)

            except:
                logger.error(f"Could not download spaCy {spacy_model_name} model.")

        # if the model was loaded successfully do this:
        if model is not None:
            # set the model name
            self.spacy_model_name = spacy_model_name

            # add the EntityRecognizer to the pipeline if it's not already there
            if 'ner' not in model.pipe_names:
                model.add_pipe('ner')

            # make the model available to the class
            self.spacy_model = model

        return model

    def merge_segment(self, segment, receiving_segment, segment_idx, timed=True):
        '''
        This makes sure that all the important elements of a segment are merged with the receiver segment.
        :param segment: the segment to be merged
        :param receiving_segment: the segment that receives the merge
        :param segment_idx: the index (or ID) of the segment to be merged
        :param timed: if True, the segments MUST have start and end times
        :return: the merged segment
        '''

        if timed and \
            ('start' not in segment or 'end' not in segment):
            logger.error('The segment has no start or end time. Cannot perform merge.')
            return receiving_segment

        if timed and \
            ('start' not in receiving_segment or 'end' not in receiving_segment):
            logger.error('The segment has no start or end time. Cannot perform merge.')
            return receiving_segment

        # if the receiving segment has no time, fail
        if 'text' not in receiving_segment:
            logger.error('The receiving segment has no text. Cannot perform merge.')
            return receiving_segment

        # if the current segment has no time, fail
        if 'text' not in segment:
            logger.error('The segment has no text. Cannot perform merge.')
            return receiving_segment

        # add the text to the previous segment
        receiving_segment['text'] += ' ' + segment['text']

        # add the words to the previous segment
        if 'words' in segment and 'words' in receiving_segment:
            receiving_segment['words'] += segment['words']

        # the start time of the previous segment remains the same (or we add this one if there is none)
        if 'start' not in receiving_segment:
            receiving_segment['start'] = segment['start']

        # the end time of the previous segment becomes the end time of the current segment
        if 'end' in segment:
            receiving_segment['end'] = segment['end']

        # if the previous segment has no index key, add it
        # this way we track the segments that were merged into it (using their indexes from the original segments list)
        if 'idx' not in receiving_segment:
            receiving_segment['idx'] = []

        # add the current segment to the segments key of the previous segment
        receiving_segment['idx'].append(segment_idx)

        return receiving_segment

    def get_model_name(self):
        '''
        Returns the name of the spaCy model that is currently loaded.
        '''

        return self.spacy_model_name

    def cluster_segment_by_time_diff(self,
                                     segment: dict,
                                     segment_idx: int,
                                    resulting_segments: list=[],
                                    time_threshold: int=0.1) \
            -> (list, int):
        '''
        Checks if the current segment is close enough to the last segment in the resulting segments list.
        And if it is, it merges the current segment with the last segment in the resulting segments list.
        :param segment: the current segment
        :param segment_idx: the index of the current segment
        :param resulting_segments: the resulting segments list
        :param unprocessed_segments: the unprocessed segments list
        :param time_threshold: the time threshold
        :return: the resulting segments, the unprocessed segments and the time difference (None if the time difference cannot be calculated)
        '''

        # if the current segment has no time fail
        if 'start' not in segment or 'end' not in segment or 'text' not in segment:
            logger.warn('The segment has no text, start or end time. Skipping it.')
            return resulting_segments, segment, None

        # if resulting_segments is None, initialize it
        if resulting_segments is None:
            resulting_segments = []

        # if resulting_segments is empty, add the current segment to it
        if len(resulting_segments) == 0:
            resulting_segments.append(segment)
            return resulting_segments, segment, None

        # get the time difference between the end of the previous segment and the start of the current one
        time_diff = segment['start'] - resulting_segments[-1]['end']

        # if the time threshold has been met,
        # merge the current segment with the previous one
        if time_diff <= time_threshold:

            # merge the current segment with the previous one
            resulting_segments[-1] = self.merge_segment(segment, resulting_segments[-1], segment_idx, timed=True)

            # and return the resulting segments, the empty segment and the time difference
            return resulting_segments, None, time_diff

        # if the time threshold has not been met,
        # return the resulting segments as they were and the untouched current segment
        else:
            return resulting_segments, segment, time_diff


    def cluster_unfinished_sentences(self,
                                 segment: dict,
                                 segment_idx: int,
                                 resulting_segments: list=[],
                                 spacy_model=None,
                                 use_grammar: bool=True) \
            -> (list, dict or None):
        '''
        Checks if the previous segment is an unfinished sentence or if the current segment is a continuation of the previous one.
        And if it is, it merges it with the current segment.
        :param segment: the current segment
        :param segment_idx: the index of the current segment
        :param resulting_segments: the resulting segments list
        :param spacy_model: the language of the transcription
        :param use_grammar: whether to use grammar to detect unfinished sentences instead of sentence stop words/punctuation
                            (coordinating conjunctions, subordinating conjunctions, etc.)
        :return: the resulting segments list
        '''

        if spacy_model is None:
            logger.error('No spaCy model provided. Cannot perform analysis.')
            return resulting_segments, segment

        # if the current segment has no text fail
        if 'text' not in segment:
            logger.warn('The segment has no text. Skipping it.')
            return resulting_segments, segment

        # if resulting_segments is None, initialize it
        if resulting_segments is None:
            resulting_segments = []

        # if resulting_segments is empty, add the current segment to it
        if len(resulting_segments) == 0:
            resulting_segments.append(segment)
            return resulting_segments, segment

        # get the previous segment
        previous_segment = resulting_segments[-1]

        # if the previous segment has no text fail
        if 'text' not in previous_segment:
            logger.warn('The previous segment has no text. Skipping it.')
            return resulting_segments, segment

        # get the current segment's text
        current_segment_text = segment['text']

        # get the current segment's text as a spacy doc
        current_segment_doc = spacy_model(current_segment_text.strip())

        # get the current segment's first token
        current_segment_first_token = current_segment_doc[0]

        # if we're supposed to use grammar
        # look for coordinating conjunctions that might indicate unfinished sentences
        if use_grammar:

            #logger.info('Using grammar to detect unfinished sentences.')

            # if the current segment's first token is a coordinating conjunction
            if current_segment_first_token.pos_ in ['CCONJ']:

                # merge the current segment with the previous one
                resulting_segments[-1] = \
                    self.merge_segment(segment, resulting_segments[-1], segment_idx, timed=False)

                # if the segment was merged,
                # the current segment is basically empty, so we return it as None
                return resulting_segments, None

        # next stage is to check if the previous segment is an unfinished sentence
        # if it is, merge the current segment with the previous one

        # get the previous segment's text
        previous_segment_text = previous_segment['text']

        # get the previous segment's text as a spacy doc
        previous_segment_doc = spacy_model(previous_segment_text.strip())

        # get the previous segment's last token
        previous_segment_last_token = previous_segment_doc[-1]

        # if the last token of the previous segment is not a punctuation mark
        # and the first token of the current segment is not uppercase
        # (or it is uppercase, but it's a person name)
        if previous_segment_last_token.pos_ not in ['PUNCT'] \
                and (not current_segment_first_token.is_upper
                     or (current_segment_first_token.is_upper
                         and current_segment_first_token.ent_type_
                         in ['PERSON', 'NORP', 'ORG', 'GPE', 'LOC', 'FAC', 'PRODUCT', 'EVENT']
                     )
        ):

            # merge the current segment with the previous one
            resulting_segments[-1] = \
                self.merge_segment(segment, resulting_segments[-1], segment_idx, timed=False)

            # if the segment was merged,
            # the current segment is basically empty, so we return it as None
            return resulting_segments, None

        # if the previous segment's last token is not a sentence end
        # or the current segment's first token is not a sentence start
        if not previous_segment_last_token.is_sent_end \
                or not current_segment_first_token.is_sent_start:

            # merge the current segment with the previous one
            resulting_segments[-1] = \
                self.merge_segment(segment, resulting_segments[-1], segment_idx, timed=False)

            # if the segment was merged,
            # the current segment is basically empty, so we return it as None
            return resulting_segments, None


        return resulting_segments, segment

    def remove_minor_segments(self,
                             segment: dict,
                             spacy_model=None,
                             minor_threshold: float=0.5,
                             max_tokens=10) \
            -> dict or None:
        '''
        Checks if the current segment contains a ratio of interjections, adverbs, adjectives over the minor_threshold (0 to 1).
        If it does, it empties the current segment

        For eg., the sentence "Oh, beautiful!" would be removed, since it contains 1 interjection and 1 adjective and no other words.

        :param segment: the current segment
        :param spacy_model: the spacy model
        :param minor_threshold: the threshold of interjections over which the segment is removed
        :param max_tokens: beyond this number of tokens, the segment analysis is not performed

        :return: the resulting segments list
        '''

        if spacy_model is None:
            logger.error('No spaCy model provided. Cannot perform analysis.')
            return segment

        # if the current segment has no text fail
        if 'text' not in segment:
            logger.warn('The segment has no text. Skipping it.')
            return segment

        # get the current segment's text
        current_segment_text = segment['text']

        # get the current segment's text as a spacy doc
        current_segment_doc = spacy_model(current_segment_text.strip())

        # if the current segment has more than max_tokens tokens, skip it
        if len(current_segment_doc) > max_tokens:
            return segment

        # remove punctuation, determiners, spaces, symbols, etc. from the ratio calculation
        current_segment_doc = [token for token in current_segment_doc if token.pos_ not in ['PUNCT', 'DET', 'SPACE', 'SYM']]

        # get the current segment's interjections, adverbs, adjectives
        current_segment_interjections = [token for token in current_segment_doc if token.pos_ in ['INTJ', 'ADV', 'ADJ']]

        # if the current segment has no interjections, skip it
        if len(current_segment_interjections) == 0:
            return segment

        # get the current segment's interjections ratio
        current_segment_interjections_ratio = len(current_segment_interjections) / len(current_segment_doc)

        # if the current segment's interjections ratio is over the interjection_threshold
        if current_segment_interjections_ratio > minor_threshold:

            # the current segment is basically empty, so we return it as None
            return None

        return segment

    def cluster_dependent_segments(self,
                                    segment: dict,
                                    segment_idx: int,
                                    resulting_segments: list,
                                    spacy_model=None) \
            -> (list, dict or None):
        '''
        This method checks if the current segment is a dependent of last one in the resulting segments.
        '''

        # WORK IN PROGRESS
        return resulting_segments, segment

        # if the current segment has no text fail
        if 'text' not in segment:
            logger.warn('The segment has no text. Skipping it.')
            return resulting_segments, segment

        # get the current segment's text
        current_segment_text = segment['text'].strip()
        previous_segment_text = resulting_segments[-1]['text'].strip()

        text = f"{previous_segment_text} {current_segment_text}"

        # Perform coreference resolution using Hugging Face Transformers
        resolved_text = coref_pipeline(text)
        resolved_text = ' '.join([cluster[0] for cluster in resolved_text['clusters']])

        # Process the text with Spacy model
        doc = spacy_model(resolved_text)

        # Print the dependency relationship between tokens
        for token in doc:
            print(f"{token.text:<15} {token.dep_:<10} {token.head.text:<15}")

        # Assuming,you want to return True if there is at least one dependency between any
        # pair of tokens from the two sentences.
        for token1 in doc.sents:      # Iterate through sentences
            if token1 == current_segment_text:
                break
            for token2 in doc:         # Iterate through tokens
                if token1.dep_ != 'ROOT' and token2.dep_ != 'ROOT' and token1.head == token2.head:

                    # merge the current segment with the previous one
                    resulting_segments[-1] = \
                        self.merge_segment(segment, resulting_segments[-1], segment_idx, timed=False)

                    # if the segment was merged,
                    # the current segment is basically empty, so we return it as None
                    return resulting_segments, None

        return resulting_segments, segment


    def process_segments(self, segments, time_difference_threshold=0, cluster_unfinished=True,
                         minor_threshold=0.7, cluster_dependents=False, spacy_model=None,
                         cache_dir=None, **kwargs):
        '''
        This method processes the segments and merges them (by time, grammar, punctuation etc.)
        :param segments: the segments to be processed
        :param time_difference_threshold: the time difference threshold
        :param cluster_unfinished: if True, we analyze grammar to see if we can merge unfinished sentences
        :param minor_threshold: if a segment contains more than this percentage of interjections, it will be removed
        :param cluster_dependents: if True, we analyze grammar to see if we can merge dependent sentences
        :param spacy_model: the spacy model
        :param cache_dir: where to store the cache for the processed segments, if None, no cache is used
        :param kwargs: additional arguments - for eg. additional_segment_info
                - a dict containing additional info that will be added to all segments
        '''

        # if a model name was passed, try to load it
        if kwargs.get('model_name', None) is not None:
            spacy_model = self.load_spacy_language_model(model_name=kwargs.get('model_name', None))

            # and if we have a model, set the variables
            if spacy_model is not None:
                self.spacy_model = spacy_model
                self.spacy_model_name = kwargs.get('model_name', None)

        # try to get the spacy model from the object
        if spacy_model is None:
            spacy_model = self.spacy_model

        # if we still have an empty spacy model, try to load with the correct lang parameter
        if spacy_model is None:

            # if no lang is provided, try to detect it
            if kwargs.get('lang', None) is None:

                logger.debug('No language provided. Trying to detect it from the segments text.')

                # detect the language of the transcription file
                lang = self.detect_language(''.join([segment['text'] for segment in segments]))

            else:
                lang = kwargs.get('lang', None)

            spacy_model = self.load_spacy_language_model(lang=lang)

        if spacy_model is None:
            logger.error('No spaCy model provided. Cannot perform analysis.')
            return segments

        # create the cache dir if it does not exist
        if cache_dir and not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)

        cache_file_path = None

        # if caching is enabled
        if cache_dir:

            # use the current parameters together with the segments to create a hash to be used as a cache file name
            cache_file_name_dict = {
                'time_difference_threshold': time_difference_threshold,
                'cluster_unfinished': cluster_unfinished,
                'minor_threshold': minor_threshold,
                'cluster_dependents': cluster_dependents,
                'other': kwargs,
                'segments': segments,
                'spacy_model': self.spacy_model_name
            }

            # calculate the cache file name
            cache_file_name = "analysis_"\
                              + hashlib.md5(json.dumps(cache_file_name_dict, sort_keys=True)
                                            .encode('utf-8')).hexdigest()

            # add the cache dir to form the full path
            cache_file_path = os.path.join(cache_dir, cache_file_name)

            # if the cache file exists, load it and return it
            if os.path.isfile(cache_file_path):
                logger.info(f'Using analyzed text from cache {cache_file_path}')
                with open(cache_file_path, 'r') as f:
                    return json.load(f)

        # the resulting segments will only contain the segments that were not merged
        # and only their text, start and end times, words and an segments key to keep track which of the original segments were merged
        resulting_segments = []

        # make sure we assign an index to each segment so we know where we started from
        # but we use a list, in case we need to merge the segment with others and we need to keep track of the original segments
        for segment_idx, segment in enumerate(segments):
            segment['idx'] = [segment_idx]

            # also add here any additional info that we might need later
            if kwargs.get('additional_segment_info', None) is not None and \
                    isinstance(kwargs['additional_segment_info'], dict):

                # merge the additional info with the segment
                segments[segment_idx] = {**segment, **kwargs['additional_segment_info']}

        #for segment_idx, segment in enumerate(segments):
        # use tqdm to show a progress bar
        for segment_idx, segment in tqdm.tqdm(enumerate(segments), total=len(segments), desc='Analyzing text'):

            # use this to keep track of the current segment
            current_segment = segment

            # if the current_segment has no idx key, add it
            if 'idx' not in current_segment:
                current_segment['idx'] = [segment_idx]

            # just add the first segment to the resulting segments
            if segment_idx == 0:
                resulting_segments.append(current_segment)
                continue

            # take the segment through time clustering
            if time_difference_threshold is not None:
                resulting_segments, current_segment, time_diff = \
                    self.cluster_segment_by_time_diff(segment=current_segment,
                                                      segment_idx=segment_idx,
                                                      resulting_segments=resulting_segments,
                                                      time_threshold=time_difference_threshold)

                # if the current segment is empty now, go to the next one
                if current_segment is None:
                    continue

            # take the segment through unfinished sentence clustering
            # this will merge the current segment with the previous one
            # if the previous one looks unfinished
            if cluster_unfinished:

                # don't cluster if the segments are too far apart in time
                # (but only if we have a time difference threshold
                #   - but don't use the threshold, just use 3 seconds)
                if (time_difference_threshold is not None and time_diff < 3)\
                        or time_difference_threshold is None:

                    resulting_segments, current_segment = self.cluster_unfinished_sentences(
                        segment=current_segment,
                        segment_idx=segment_idx,
                        resulting_segments=resulting_segments,
                        spacy_model=spacy_model,
                        use_grammar=kwargs.get('use_grammar', True)
                    )

                # if the current segment is empty now, go to the next one
                if current_segment is None:
                    continue

            # remove all segments that that have a ratio of interjections, adverbs, adjectives
            # over the specified minor_threshold (0 to 1)
            if minor_threshold:
                current_segment = self.remove_minor_segments(
                    segment=current_segment,
                    spacy_model=spacy_model,
                    minor_threshold=minor_threshold
                )

                # if the current segment is empty now, go to the next one
                if current_segment is None:
                    continue

            # cluster dependents
            #if cluster_dependents:
            #    resulting_segments, current_segment = self.cluster_dependent_segments(
            #        segment=current_segment,
            #        segment_idx=segment_idx,
            #        resulting_segments=resulting_segments,
            #        spacy_model=spacy_model
            #    )
            #
            #    # if the current segment is empty now, go to the next one
            #    if current_segment is None:
            #        continue

            # finally, if we reached this point,
            # just add the segment to the resulting segments
            resulting_segments.append(current_segment)

        # if caching is enabled, save the resulting segments to the cache file
        if cache_dir and cache_file_path and os.path.isdir(os.path.dirname(cache_file_path)):
            logger.debug(f'Saving analyzed segments to cache file {cache_file_path}')
            with open(cache_file_path, 'w') as f:
                json.dump(resulting_segments, f)

        return resulting_segments