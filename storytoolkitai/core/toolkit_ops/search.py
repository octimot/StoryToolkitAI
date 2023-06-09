import os
import time
import json
import re
import hashlib

import pickle

from storytoolkitai.core.logger import logger
from sentence_transformers import SentenceTransformer, util
import torch

from .transcription import Transcription, TranscriptionSegment, TranscriptionUtils
from .textanalysis import TextAnalysis


class ToolkitSearch:
    '''
    This is the main class for the search engine
    '''

    def __init__(self, toolkit_ops_obj):
        # load the toolkit ops object
        self.toolkit_ops_obj = toolkit_ops_obj

        # load the stAI object
        self.stAI = self.toolkit_ops_obj.stAI

        # keep all the search_corpuses here to find them easy by search_id
        # this also optimizes the search so that the corpus is only compiled once per search session
        self.search_corpuses = {}

        # keep all the embeddings in this cache to find them easy by search_id
        # this also optimizes the search so that the embeddings are only compiled once per search session
        self.search_embeddings = {}

        # define the possible search types here
        self.available_search_types = ['semantic']

        # default search type
        self.default_search_type = 'semantic'

    def is_file_searchable(self, file_path):
        '''
        This function will check if the file has the right extension to be searchable
        :param file_path:
        :return:
        '''

        # check if the file ends with one of the extensions we're looking for
        return file_path.endswith(('.transcription.json', '.txt', 'project.json'))

    def search(self):
        pass


class SearchItem(ToolkitSearch):
    '''
    This is a class that represents a single search item.
    It should be instantiated for each search and then used to pass queries
    and results between UI and the search engine

    '''

    _instances = {}

    def __init__(self, **kwargs):

        super().__init__(toolkit_ops_obj=kwargs.get('toolkit_ops_obj', None))

        # get all the attributes that were passed at init
        self.search_id = kwargs.get('search_id', None)
        self.search_type = kwargs.get('search_type', None)

        self.search_file_paths = kwargs.get('search_file_paths', None)

        self.search_corpus = kwargs.get('search_corpus', None)
        self.search_corpus_assoc = kwargs.get('search_corpus_assoc', None)
        self.search_results = kwargs.get('search_results', None)

        # we're using self.toolkit_ops_obj.s_semantic_search_model_name as default for now
        self.model_name = kwargs.get('model_name', self.toolkit_ops_obj.s_semantic_search_model_name)
        self.search_model = None

        self.max_results = kwargs.get('max_results', 5)

        self.start_search_time = kwargs.get('start_search_time', None)

        self.query = kwargs.get('query', None)

        self.search_corpus_hash = None
        self.search_corpus_cache_dir = kwargs.get('search_corpus_cache_dir', None)
        self.corpus_cache_file_path = kwargs.get('corpus_cache_file_path', None)

    def is_file_searchable(self, file_path):

        return super().is_file_searchable(file_path)

    def process_file_paths(self, search_paths: str or list = None) -> list:
        '''
        This function will process the file paths that were passed to the search function
        and return a list of file paths that are searchable
        :return:
        '''

        search_file_paths = []

        if search_paths is None:
            logger.debug('No search paths were passed to the search function')
            return None

        # is this a search for a single file or a directory?
        # if it's a single file, we'll just add it to the search_file_paths list
        if search_paths is not None and type(search_paths) is str and os.path.isfile(search_paths) \
                and self.is_file_searchable(search_paths):
            search_file_paths = [search_paths]

        # if it's a list of files, we'll just add it to the search_file_paths list
        elif search_paths is not None and (type(search_paths) is list or type(search_paths) is tuple):

            # but we only add the path if it's a file
            for search_path in search_paths:
                if os.path.isfile(search_path) and self.is_file_searchable(search_path):
                    search_file_paths.append(search_path)

        # if it's a directory, we'll process all the files in the directory
        elif search_paths is not None and type(search_paths) is str and os.path.isdir(search_paths):

            for root, dirs, files in os.walk(search_paths):
                for file in files:
                    if self.is_file_searchable(file):
                        search_file_paths.append(os.path.join(root, file))

        return search_file_paths

    def prepare_search_corpus(self):
        '''
        Takes all the segments from the search_transcriptions and turns them into a search corpus
        :param search_files:
        :param search_id:
        :return:
        '''

        search_file_paths = self.search_file_paths
        search_id = self.search_id

        # if no transcription file paths were provided
        if search_file_paths is None or len(search_file_paths) == 0:
            # throw an error if no transcription file was passed
            logger.error('Cannot search. No file path was passed.')

        # if only one transcription file path is given, make it a list
        if type(search_file_paths) is str:
            search_file_paths = [search_file_paths]

        # if there is a search corpus cache directory set in the config
        default_search_cache_dir = self.stAI.get_app_setting(setting_name='default_search_cache_dir',
                                                             default_if_none='')
        if default_search_cache_dir != '' and os.path.isdir(default_search_cache_dir):
            self.search_corpus_cache_dir = default_search_cache_dir

        # otherwise, just use the directory of the first file in the list
        else:
            self.search_corpus_cache_dir = os.path.join(os.path.dirname(search_file_paths[0]), 'cache')

        # re-organize the search corpus into a dictionary of phrases
        # with the transcription file path as the key
        # and the value being a list of phrases compiled from the transcription file text using
        # the punctuation as dividers.
        # this will make it easier to search for phrases in the transcription files
        search_corpus_phrases = []

        # use this to keep track of the transcription file path and the phrase index
        search_corpus_assoc = {}

        # and if the hasn't already been created, just create it
        if not self.search_corpus:

            logger.debug('Reading search corpus from files.')

            # load the TextAnalysis object
            ta = TextAnalysis(torch_device_name=self.toolkit_ops_obj.torch_device)

            # sort the search file paths alphabetically
            search_file_paths.sort()

            # take each file path and load the search data
            for s_file_path in search_file_paths:

                # decide what to do based on the file extension

                # if it's TRANSCRIPTION FILE
                if s_file_path.endswith('.transcription.json'):

                    # first get the transcription
                    transcription = Transcription(transcription_file_path=s_file_path)

                    if not transcription.is_transcription_file:
                        logger.warning('Transcription file {} is not in the right format. Skipping.'
                                       .format(s_file_path))

                    elif transcription.has_segments:

                        # create a dictionary version of the segments
                        segments_as_dict = [segment.to_dict() for segment in transcription.get_segments()]

                        # detect the language of the transcription if we don't know it already
                        # also make sure we have a language code that is 2 characters long (ISO 639-1)
                        if not transcription.language or len(transcription.language) != 2:

                            transcription_language \
                                = ta.detect_language(''.join(
                                [segment.text for segment in transcription.get_segments()]))

                            # if we know the language of the transcription
                            if transcription_language is not None:
                                transcription.set('language', transcription_language)
                                transcription.save_soon()

                        else:
                            transcription_language = transcription.language

                        # try to see if we know which model to use for this language
                        # (if not the TextAnalysis will try to get the model itself)
                        spacy_models_per_language \
                            = self.stAI.get_app_setting(setting_name='spacy_models_per_language',
                                                        default_if_none={})

                        if transcription_language in spacy_models_per_language:
                            selected_model_name = spacy_models_per_language[transcription_language]
                        else:
                            selected_model_name = None

                        # run it through the TextAnalysis to cluster and clean up the text
                        filtered_transcription_segments = \
                            ta.process_segments(
                                segments=segments_as_dict,
                                time_difference_threshold=None,
                                cache_dir=self.search_corpus_cache_dir,
                                lang=transcription_language,
                                model_name=selected_model_name
                            )

                        # if we didn't know the textanalysis model before, check if we know it now
                        # check if we know the spacy model after running it through the TextAnalysis
                        if selected_model_name is None:
                            selected_model_name = ta.get_model_name()

                            # and if it's not empty, add it to the config so we know it for next time
                            if selected_model_name is not None:
                                spacy_models_per_language[transcription_language] = selected_model_name
                                self.stAI.save_config(setting_name='spacy_models_per_language',
                                                      setting_value=spacy_models_per_language)

                        transcription_file_path = s_file_path

                        logger.debug('Adding {} to the search corpus.'.format(transcription_file_path))

                        # does this transcription file contain timecodes?
                        timecode_data = transcription.get_timecode_data()

                        # group the segment texts into phrases using punctuation as dividers
                        # instead of how they're currently segmented
                        # once they are grouped, add them to the search corpus
                        # plus add them to the search corpus association list so we know
                        # from which transcription file and from which segment they came from originally

                        # initialize the current phrase and the previous phrase
                        current_phrase = ''
                        previous_phrase = ''

                        # loop through the segments of this transcription file
                        for segment_index, segment in enumerate(filtered_transcription_segments):

                            filtered_segment_index = None

                            # if there is a segment index in the segment
                            # it means that these segments may have been filtered
                            if 'idx' in segment:

                                # so let's use the first segment index as the segment index for the results
                                filtered_segment_index = segment['idx'][0]

                                # and if there is a filtered segment index, use that instead
                                # note: all_lines is a list of all the lines that are connected to this segment
                                # therefore, all_lines below will take this value too
                                # (+1 on each index to compensate for line numbers)
                                if filtered_segment_index is not None:
                                    segment_index = filtered_segment_index

                            # first remember the transcription file path and the segment index
                            # if this is a new phrase (i.e. the current phrase is empty)
                            if current_phrase == '':
                                # this is the segment index relative to the whole search corpus that
                                # contains all the transcription file segments (not just the current transcription file)
                                general_segment_index = len(search_corpus_phrases)

                                timecode = None \
                                    if not timecode_data \
                                    else transcription.seconds_to_timecode(
                                    segment['start'],
                                    transcription.timeline_fps, transcription.timeline_start_tc
                                )

                                search_corpus_assoc[general_segment_index] = {
                                    'transcription_file_path': transcription_file_path,
                                    'name': transcription.name
                                    if transcription.name else os.path.basename(transcription_file_path),
                                    'segment': segment['text'],
                                    'segment_index': segment_index,
                                    'start': segment['start'],
                                    'timecode': timecode,
                                    'all_lines': [int(segment_index) + 1]
                                    if 'idx' not in segment
                                    else [sgm + 1 for sgm in segment['idx']],
                                    'type': 'transcription'
                                }

                            # otherwise, if this is not a new phrase
                            else:
                                # just append the current segment index to the list of all lines
                                search_corpus_assoc[general_segment_index]['all_lines'].append(
                                    int(segment_index) + 1)

                            # add the segment text to the current phrase
                            # but only if it's longer than 2 chars to avoid adding stuff that is meaningless
                            # like punctuation marks
                            if 'text' in segment and type(segment['text']) is str:

                                # keep adding segments to the current phrase until we find a punctuation mark

                                # first get the segment text
                                segment_text = str(segment['text'])

                                # add the segment to the current phrase
                                current_phrase += segment_text.strip() + ' '

                                # if a punctuation mark exists in the last 5 characters of the segment text
                                # it means that the current phrase is complete
                                if re.search(r'[\.\?\!]{1}\s*$', segment_text[-5:]):
                                    # "close" the current phrase by adding it to the search corpus
                                    search_corpus_phrases.append(current_phrase.strip())

                                    # and remember it as the previous phrase
                                    previous_phrase = current_phrase

                                    # then empty the current phrase
                                    current_phrase = ''

                        if transcription.transcript_groups:

                            # take each transcript group
                            for transcript_group in transcription.transcript_groups:
                                general_segment_index = len(search_corpus_phrases)

                                # and add the transcript group name and group notes to the search corpus association
                                search_corpus_assoc[general_segment_index] = {
                                    'file_path': transcription_file_path,
                                    'transcription_name': transcription.name
                                    if transcription.name else os.path.basename(transcription_file_path),
                                    'type': 'transcript_group',
                                    'group_name': transcript_group
                                }

                                # and add the transcript group name to the search corpus phrases
                                search_corpus_phrases.append(
                                    transcription.transcript_groups[transcript_group]['name']
                                    + ': '
                                    + transcription.transcript_groups[transcript_group]['notes']
                                )


                # if it's a TEXT FILE
                elif s_file_path.endswith('.txt'):

                    # if there is an exact file with the .transcription.json extension in the search file paths
                    # skip this .txt file to avoid reading the same content twice
                    # (we're making the assumption that that .txt file was saved with the transcription file)
                    if s_file_path.replace('.txt', '.transcription.json') in search_file_paths:
                        # also remove it from the search file paths list
                        search_file_paths.remove(s_file_path)

                        logger.debug('Skipping {}. Transcription file counterpart is included '
                                     'in the current file list.'.format(s_file_path))
                        continue

                    # first read the file
                    with open(s_file_path, 'r', encoding='utf-8') as f:
                        file_text = f.read()

                    # split the text into phrases using punctuation or double new lines as dividers
                    phrases = re.split(r'[\.\?\!]{1}\s+|[\.\?\!]{1}$|[\n]{2,}', file_text)

                    # then add each phrase to the search corpus
                    for phrase_index, phrase in enumerate(phrases):

                        # but only if it's longer than x characters
                        # to avoid adding stuff that is most likely meaningless
                        # like punctuation marks
                        if len(phrase) > self.stAI.get_app_setting(
                                setting_name='search_corpus_min_length', default_if_none=2):
                            # add the phrase to the search corpus
                            search_corpus_phrases.append(phrase.strip())

                            # remember the text file path and the phrase number
                            # this is the phrase index relative to the whole search corpus that
                            general_segment_index = len(search_corpus_phrases)

                            # add the phrase to the search corpus association list
                            search_corpus_assoc[general_segment_index] = {'file_path': s_file_path,
                                                                          'text': phrase.strip(),
                                                                          'phrase_index': phrase_index,
                                                                          'type': 'text'
                                                                          }

                # if it's a PROJECT FILE
                elif s_file_path.endswith('project.json'):

                    # read it as a json file
                    with open(s_file_path, 'r', encoding='utf-8') as f:
                        project_file_data = json.load(f)

                    # first check if it contains the project name
                    if 'name' not in project_file_data or 'timelines' not in project_file_data:
                        logger.warning('Project file {} is not in the right format. Skipping.'
                                       .format(s_file_path))
                        continue

                    # take each timeline and add all its markers to the search corpus
                    for timeline_name in project_file_data['timelines']:

                        timeline = project_file_data['timelines'][timeline_name]

                        # if the timeline has markers
                        if 'markers' in timeline and type(timeline['markers']) is dict:

                            # loop through the markers
                            for marker in timeline['markers']:

                                # add the marker name to the search corpus
                                if 'name' in timeline['markers'][marker]:
                                    marker_content = timeline['markers'][marker]['name']

                                    # add the marker name to the search corpus
                                    search_corpus_phrases.append(marker_content)

                                    # remember the project file path and the marker name
                                    # this is the marker index relative to the whole search corpus that
                                    general_segment_index = len(search_corpus_phrases)

                                    # add the marker to the search corpus association list
                                    search_corpus_assoc[general_segment_index] = {'file_path': s_file_path,
                                                                                  'text': marker_content,
                                                                                  'timeline': timeline_name,
                                                                                  'project': project_file_data[
                                                                                      'name'],
                                                                                  'marker_index': marker,
                                                                                  'type': 'marker'
                                                                                  }

                                # add the marker note to the search corpus
                                if 'note' in timeline['markers'][marker]:
                                    marker_content = timeline['markers'][marker]['note']

                                    # add the marker name to the search corpus
                                    search_corpus_phrases.append(marker_content)

                                    # remember the project file path and the marker name
                                    # this is the marker index relative to the whole search corpus that
                                    general_segment_index = len(search_corpus_phrases)

                                    # add the marker to the search corpus association list
                                    search_corpus_assoc[general_segment_index] = {'file_path': s_file_path,
                                                                                  'text': marker_content,
                                                                                  'timeline': timeline_name,
                                                                                  'project': project_file_data[
                                                                                      'name'],
                                                                                  'marker_index': marker,
                                                                                  'type': 'marker'
                                                                                  }

            # add the corpus to the search corpus dict, so we don't have to re-create it every time we search
            # for eg. we could use the search window id as the key
            self.search_corpuses[search_id] = {'corpus': {}, 'assoc': {}}
            self.search_corpuses[search_id]['corpus'] = search_corpus_phrases
            self.search_corpuses[search_id]['assoc'] = search_corpus_assoc

            self.search_file_paths = search_file_paths
            self.search_corpus = search_corpus_phrases
            self.search_corpus_assoc = search_corpus_assoc

        return self.search_corpuses[search_id]['corpus'], self.search_corpuses[search_id]['assoc']

    def prepare_search_query(self, query, max_results: int = 5, search_type='semantic'):
        '''
        This interprets the query and prepares it for searching.
        With this, we can filter out and use certain arguments to perform the search

        For eg:
        [semantic] about AI - will search for the phrase "about AI" using semantic search
        [semantic,10] about AI - will search semantically for the phrase "about AI" and return the top 10 results

        :param query:
        :param max_results: the maximum number of results to return (can be overridden within the query)
        :param search_type: the type of search to perform (can be overridden within the query)
        :return:
        '''

        # the users can include a "[search_type]" in the query to specify the search type
        # for eg. [semantic]
        # if they do, then use that search type instead of the default
        if re.search(r'\[(.+?)\]', query):
            query_search_type = re.search(r'\[(.+?)\]', query).group(1)

            # if the query search type is just a number, then it's a max results value
            if query_search_type.isdigit():
                query_max_results = str(query_search_type)

                # but that means that the user didn't specify a search type
                # so use the default search type
                query_search_type = self.default_search_type

                just_max_results = True

            # if the search type also contains a comma, then it means that the user also specified a max results
            # for eg [semantic, 10] means that the user wants to use the semantic search type and return 10 results
            # so extract that too
            elif not query_search_type.isdigit() and re.search(r',', query_search_type):
                query_search_type_list = query_search_type.split(',')
                query_search_type = query_search_type_list[0]
                query_max_results = str(query_search_type_list[1]).strip()

            # otherwise it's just a [max_results] value
            else:
                query_max_results = str(max_results)

            # if the search type is valid, use it
            if query_search_type in self.available_search_types:
                search_type = query_search_type

            # if the max results is valid, use it
            if query_max_results.isdigit():
                max_results = int(query_max_results)

            # remove the search type and max results from the query
            query = re.sub(r'\[(.+?)\]', '', query).strip()

        # the user can divide multiple search terms with a | character
        # if that is the case, split them into multiple queries
        # so that we can search for each of them separately later
        if '|' in query:
            # split the query into multiple queries
            query = query.split('|')

        self.query = query
        self.search_type = search_type
        self.max_results = max_results

        return query, search_type, max_results

    def load_model(self, model_name):
        '''
        Loads the model specified by the user, but also clears the search corpus embeddings
        for the current search item
        :param model_name:
        :return:
        '''

        # if the model name is different from the current model name,
        # clear the search corpus embeddings
        if model_name != self.model_name:

            # clear the search model
            self.search_model = None

            # clear the search corpus embeddings
            if self.search_id is not None and self.search_id in self.search_embeddings:
                del self.search_embeddings[self.search_id]

            # clear other search corpus data to force it to be re-created
            self.search_corpus_hash = None
            self.corpus_cache_file_path = None

            # assign the new model name
            self.model_name = model_name

        # load the sentence transformer model if it hasn't been loaded yet
        if self.search_model is None:
            logger.info(
                'Loading sentence transformer model "{}" on {}.'
                .format(self.model_name, self.toolkit_ops_obj.torch_device)
            )

            # if the sentence transformer model was never downloaded, log that we're downloading it
            model_downloaded_before = True
            if self.stAI.get_app_setting(setting_name='s_semantic_search_model_downloaded_{}'
                    .format(self.model_name), default_if_none=False) is False:
                logger.warning('The sentence transformer model {} may need to be downloaded and could take a while '
                               'depending on the Internet connection speed. '
                               .format(self.model_name)
                               )
                model_downloaded_before = False

            # load the sentence transformer model
            self.search_model = SentenceTransformer(self.model_name)

            # set the torch device to the same device as the toolkit
            self.search_model.to(self.toolkit_ops_obj.torch_device)

            # once the model has been loaded, we can note that in the app settings
            # this is a wat to keep track if the model has been downloaded or not
            # but it's not 100% reliable and we may need to find a better way to do this in the future
            if not model_downloaded_before:
                self.stAI.save_config(setting_name='s_semantic_search_model_downloaded_{}'
                                      .format(self.model_name),
                                      setting_value=True)

            return self.search_model

        # if the model name is the same as the current model name,
        # then we don't need to load the model again
        else:
            return self.search_model

        return None

    def search(self, query: str):
        '''
        Searches the corpus for the query using the search type passed by the user

        In the future, we should use this for any type of search (incl. for frames etc.)

        :param query:
        :return:
        '''

        self.query = query

        # prepare the query
        query, search_type, max_results = self.prepare_search_query(query=self.query)

        # now let's search the corpus based on the search type
        if search_type == 'semantic':
            results, max_results = self.search_semantic()
        else:
            logger.debug('Aborting. Invalid search type: {}'.format(search_type))
            return None

        # return the results
        return results, max_results

    def search_similar(self, query, search_corpus_phrases, search_corpus_assoc, search_id=None, max_results=10,
                       start_search_time=None):

        # WORK IN PROGRESS

        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        # reset the search results
        search_results = []

        top_k = max_results

        model = SentenceTransformer('all-MiniLM-L6-v2')

        paraphrase_results = []

        # take each phrase in the search corpus and compare it to the query
        paraphrases = util.paraphrase_mining(model, search_corpus_phrases, top_k=max_results)

        for paraphrase in paraphrases:
            score, i, j = paraphrase
            if score < 1.0:
                print("{} \t\t {} \t\t Score: {:.4f}".format(search_corpus_phrases[i], search_corpus_phrases[j],
                                                             score))

        return search_results, top_k

    def get_corpus_cache_file_path(self, search_type=None):

        # compute a hash of the search corpus + the search type + the search model
        # we will use this to name the file where we will store the search corpus embeddings for later use
        # this means that if anything changes in this search corpus, we will need to re-encode it
        # it also means that we might have a lot of orphaned cache files if we don't clean them up...
        if self.search_corpus_hash is None:
            self.search_corpus_hash = hashlib.md5(
                str('{}--{}--{}'.format(str(self.search_corpus), search_type, self.model_name)).encode('utf-8')
            ).hexdigest()

        self.corpus_cache_file_path = os.path.join(self.search_corpus_cache_dir,
                                                   'search_{}.pkl'.format(self.search_corpus_hash))

        return self.corpus_cache_file_path

    def save_corpus_embeddings_to_file(self, embeddings, model, file_path=None):
        """
        This function saves the corpus embeddings to a file,
        but changes the device to cpu temporarily to make the embedding file compatible with all systems
        """

        # only save the embeddings if they and the model are valid
        if embeddings is None:
            logger.warning('Cannot save encoded corpus to file - invalid embeddings.')
            return

        if model is None:
            logger.warning('Cannot save encoded corpus to file - invalid model.')
            return

        # if no file path was passed, try to use the one from the class
        if file_path is None:
            file_path = self.corpus_cache_file_path

        if file_path is None:
            logger.warning('Cannot save encoded corpus to file - no cache file path specified.')
            return

        try:

            # check if the directory exists
            if not os.path.exists(os.path.dirname(file_path)):
                # otherwise, create it
                os.makedirs(os.path.dirname(file_path))

            # get the current device of the embedder
            model_device = model.device

            # move the model to the cpu for saving to ensure compatibility with all systems
            if str(model_device) != 'cpu':
                # move the model to the cpu
                logger.debug('Moving embedder from "{}" to cpu temporarily to save embeddings to file.'
                             .format(model_device))
                model.to('cpu')

                # get the embeddings from the model again
                embeddings = embeddings.to('cpu')

            # save the corpus embeddings to a file
            with open(file_path, 'wb') as f:
                pickle.dump(embeddings, f)

            # save a json file next to the pickle file with the same name
            # that contains the file list and full path of all the files in the corpus
            # this is useful in case we want to clean up the corpus cache directory
            with open('{}.json'.format(file_path), 'w') as f:
                json.dump(self.search_file_paths, f, indent=4)

            logger.debug('Saved encoded search corpus to {}'.format(file_path))

            # move the model back to the original device
            if str(model_device) != 'cpu':
                logger.debug('Moving model back to {}.'.format(model_device))
                model.to(model_device)
                embeddings = embeddings.to(model_device)

            return True

        except Exception as e:

            logger.error('Could not save search embeddings to file:'.format(file_path), exc_info=True)
            return False

    def search_semantic(self):
        '''
        This function searches for a search term in a search corpus and returns the results.
        :param query:
        :param search_corpus_phrases:
        :param search_corpus_assoc:
        :param search_id:
        :param max_results: the maximum number of results to return (default: 10, maximum = corpus len)
        :param start_search_time: the time that the search started (default: None)
        :return:
        '''

        query = self.query
        search_corpus_phrases = self.search_corpus
        search_corpus_assoc = self.search_corpus_assoc
        search_id = self.search_id
        max_results = self.max_results
        start_search_time = self.start_search_time

        # if the search corpus is empty, try to prepare it
        if self.search_file_paths and not self.search_corpus:
            # prepare the search corpus
            self.prepare_search_corpus()

            # reload all the variables that might have changed
            search_corpus_phrases = self.search_corpus
            search_corpus_assoc = self.search_corpus_assoc
            search_id = self.search_id
            max_results = self.max_results
            start_search_time = self.start_search_time

        corpus_cache_file_path = self.get_corpus_cache_file_path(search_type='semantic')

        if query is None or query == '':
            logger.warning('Query empty.')
            return [], 0

        # if the corpus is empty, abort
        if not search_corpus_phrases:
            logger.warning('Search corpus empty.')
            return [], 0

        logger.debug('Performing semantic search on {} phrases.'.format(len(search_corpus_phrases)))

        if start_search_time is not None:
            logger.debug('Time: ' + str(time.time() - start_search_time))

        # define the model into this variable for easier access
        embedder = self.load_model(model_name=self.model_name)

        if embedder is None:
            logger.warning('Search model not loaded.')
            return [], 0

        if start_search_time is not None:
            logger.debug('Time: ' + str(time.time() - start_search_time))

        # if we haven't loaded the search corpus embeddings in the cache,
        # check if we have them in a file
        if (search_id is None or search_id not in self.search_embeddings) \
                and os.path.exists(corpus_cache_file_path):

            # get the current device of the embedder
            transformer_embedder_device = embedder.device

            # if the embedder device is not cpu, move it to cpu temporarily
            # to ensure compatibility with all systems - basically the embeddings saved to files must be on cpu
            if str(transformer_embedder_device) != 'cpu':
                logger.debug('Moving embedder from "{}" to "cpu" temporarily to load embeddings from file.'
                             .format(transformer_embedder_device))
                embedder.to('cpu')

            logger.debug('Loading encoded search corpus from {}'.format(corpus_cache_file_path))

            # if the try fails, we can assume that the cache file is corrupted
            try:

                # load the corpus embeddings from the file
                with open(corpus_cache_file_path, 'rb') as f:
                    corpus_embeddings = pickle.load(f)

                # move the embeddings from the file to the same device as the model
                corpus_embeddings = corpus_embeddings.to(transformer_embedder_device)

                # move the embedder back to the original device
                if str(transformer_embedder_device) != 'cpu':
                    embedder.to(transformer_embedder_device)

                # touch the file to update the last modified time
                # this will be useful if we want to ever clean up the cache
                # (e.g. delete files unused for 90 days)
                os.utime(corpus_cache_file_path, None)

                # add the corpus embeddings to the memory cache
                self.search_embeddings[search_id] = corpus_embeddings

            except:

                logger.warning('Could not load encoded search corpus from file: {}'.format(corpus_cache_file_path),
                               exc_info=True)

                # move the embedder back to the original device
                if str(transformer_embedder_device) != 'cpu':
                    embedder.to(transformer_embedder_device)

        # if we haven't found the search corpus embeddings in the cache or in a file
        # then we need to encode it now
        if search_id is None or search_id not in self.search_embeddings:

            # encode the search corpus
            corpus_embeddings = embedder.encode(search_corpus_phrases, convert_to_tensor=True,
                                                show_progress_bar=True)

            logger.debug('Encoded search corpus.')

            # add the embeddings to the memory cache
            self.search_embeddings[search_id] = corpus_embeddings

            # save the embeddings to the file cache for later use
            self.save_corpus_embeddings_to_file(corpus_embeddings, model=embedder)

        else:
            # load the embeddings from the cache
            corpus_embeddings = self.search_embeddings[search_id]

            logger.info('Using search corpus embeddings from cache.')

        if start_search_time is not None:
            logger.debug('Time: ' + str(time.time() - start_search_time))

        # if the query is string, consider that the query consists of a single search term
        # otherwise, consider that the query is a list of search terms
        queries = [query] if isinstance(query, str) else query

        # reset the search results
        search_results = []

        # Find the closest 5 sentences of the corpus for each query sentence based on cosine similarity
        logger.info('Finding the closest sentences in the corpus for the query {}.'.format(queries))

        # the top_k parameter defines how many results to return
        # it's either the max_results parameter or the length of the search corpus,
        # whatever is smaller
        top_k = min(max_results, len(search_corpus_phrases))
        for query in queries:

            # remove whitespaces from the query
            query = query.strip()

            query_embedding = embedder.encode(query, convert_to_tensor=True, show_progress_bar=True)

            logger.debug('Encoded the query.')

            if start_search_time is not None:
                logger.debug('Time: ' + str(time.time() - start_search_time))

            # we use cosine-similarity and torch.topk to find the highest top_k scores
            cos_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]
            top_results = torch.topk(cos_scores, k=top_k, sorted=True)

            # reverse the results so that they are in descending order
            top_results = (top_results[0].tolist()[::-1], top_results[1].tolist()[::-1])

            logger.debug('Found results.')

            if start_search_time is not None:
                logger.debug('Time: ' + str(time.time() - start_search_time))

            # compile the search results
            # but take the source file into consideration
            for score, idx in zip(top_results[0], top_results[1]):

                if str(search_corpus_phrases[idx]) != '':
                    self.add_search_result(
                        search_results=search_results,
                        query=query,
                        search_corpus_phrases=search_corpus_phrases,
                        search_corpus_assoc=search_corpus_assoc,
                        idx=idx,
                        score=score
                    )

        self.search_results = search_results
        self.top_k = top_k

        return search_results, top_k

    def add_search_result(self, search_results, query, search_corpus_phrases, search_corpus_assoc, idx, score):
        '''
        This function adds a search result to the search results list.
        :param search_results:
        :param query:
        :param search_corpus_assoc:
        :param idx:
        :param score:
        :return:
        '''

        # sometimes the search corpus phrases are not in the search corpus assoc
        # which should not happen - it's most probably because of a text formatting issue
        # so we can't associate it with a source file, but we're still going to output it as a result
        if int(idx) not in search_corpus_assoc:
            logger.debug('Cannot find phrase with idx {} in search corpus assoc.'.format(int(idx)))

            # just add the phrase to the search results
            # but keep in mind that it's not associated with a source file!
            search_results.append({
                'search_term': query,
                'file_path': '',
                'idx': int(idx),
                'score': score,
                'text': search_corpus_phrases[idx],
                'type': 'Unknown'
            })

        # in case the source file was a transcription
        elif search_corpus_assoc[int(idx)]['type'] == 'transcription':
            transcription_file_path = search_corpus_assoc[int(idx)]['transcription_file_path']
            transcription_name = search_corpus_assoc[int(idx)]['name']
            segment_index = search_corpus_assoc[int(idx)]['segment_index']
            transcript_time = search_corpus_assoc[int(idx)]['start']
            line_no = int(segment_index) + 1
            all_lines = search_corpus_assoc[int(idx)]['all_lines']
            type = search_corpus_assoc[int(idx)]['type']

            # compile the results into the search results dict
            search_results.append({
                'search_term': query,
                'transcription_file_path': transcription_file_path,
                'name': transcription_name,
                'idx': int(idx),
                'segment_index': segment_index,
                'line_no': line_no,
                'all_lines': all_lines,
                'transcript_time': transcript_time,
                'timecode': search_corpus_assoc[int(idx)]['timecode'],
                'score': score,
                'text': search_corpus_phrases[idx],
                'type': type
            })

        elif search_corpus_assoc[int(idx)]['type'] == 'marker':
            search_results.append({
                'search_term': query,
                'file_path': search_corpus_assoc[int(idx)]['file_path'],
                'idx': int(idx),
                'score': score,
                'text': search_corpus_phrases[idx],
                'type': search_corpus_assoc[int(idx)]['type'],
                'marker_index': search_corpus_assoc[int(idx)]['marker_index'],
                'timeline': search_corpus_assoc[int(idx)]['timeline'],
                'project': search_corpus_assoc[int(idx)]['project']
            })

        elif search_corpus_assoc[int(idx)]['type'] == 'transcript_group':
            transcription_name = search_corpus_assoc[int(idx)]['transcription_name']

            search_results.append({
                'idx': int(idx),
                'search_term': query,
                'file_path': search_corpus_assoc[int(idx)]['file_path'],
                'transcription_name': search_corpus_assoc[int(idx)]['transcription_name'],
                'type': search_corpus_assoc[int(idx)]['type'],
                'text': search_corpus_phrases[idx],
                'group_name': search_corpus_assoc[int(idx)]['group_name'],
                'score': score,
            })

        else:
            # in case the source file was a text file
            file_path = search_corpus_assoc[int(idx)]['file_path']
            type = search_corpus_assoc[int(idx)]['type']

            # compile the results into the search results dict
            search_results.append({
                'search_term': query,
                'file_path': file_path,
                'idx': int(idx),
                'score': score,
                'text': search_corpus_phrases[idx],
                'type': type
            })

        return True
