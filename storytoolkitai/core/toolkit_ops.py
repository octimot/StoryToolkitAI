import os
import sys
import time
import json
import codecs

from threading import Thread
from threading import Timer as threadingTimer

import torch
import torchaudio
import storytoolkitai.integrations.mots_whisper as whisper
from whisper import tokenizer as whisper_tokenizer

import openai
import tiktoken
from transformers import GPT2TokenizerFast, pipeline

import librosa
import soundfile

import numpy as np
import tqdm

from storytoolkitai.core.logger import *
from storytoolkitai import USER_DATA_PATH, OLD_USER_DATA_PATH, APP_CONFIG_FILE_NAME

from storytoolkitai.integrations.mots_resolve import MotsResolve

import re
from sentence_transformers import SentenceTransformer, util

from timecode import Timecode

import hashlib
import pickle

from storytoolkitai.core.textanalysis import TextAnalysis

class NLE:
    '''
    Use this class to store any data that is supposed to be shared with the NLE (for eg. Resolve)
    '''

    # the current project name
    current_project = None

    # the current timeline dict
    current_timeline = None

    # a dict with the current timeline markers
    current_timeline_markers = None

    # the current timecode
    current_tc = None

    # the current timeline fps
    current_timeline_fps = None

    # the current bin
    current_bin = None

    # resolve specific attributes
    resolve_error = 0
    resolve = None
    resolve_poll_num = 0

    def reset_all(self=None):

        NLE.current_timeline \
            = NLE.current_project \
            = NLE.current_timeline_markers \
            = NLE.current_tc \
            = NLE.current_timeline_fps \
            = NLE.current_bin \
            = None

    def is_connected(self=None):
        '''
        Check if the NLE is connected
        '''

        if NLE.resolve is None:
            return False
        else:
            return True


class Observer:
    def update(self, subject):
        pass


class ToolkitOps:

    def __init__(self, stAI=None, disable_resolve_api=False):

        # this will be used to store all the transcripts that are ready to be transcribed
        self.transcription_queue = {}

        # keep a reference to the StoryToolkitAI object here if one was passed
        self.stAI = stAI

        # define the path to the  queue file relative to the user_data_path
        if self.stAI is not None:
            self.QUEUE_FILE_PATH = os.path.join(stAI.user_data_path, 'queue.json')

        # use a relative path for the queue file, if no stAI was passed
        else:
            self.QUEUE_FILE_PATH = 'queue.json'

        # initialize the toolkit search engine
        self.t_search_obj = self.ToolkitSearch(toolkit_ops_obj=self)

        # initialize the TranscriptGroups object
        self.t_groups_obj = self.TranscriptGroups(toolkit_ops_obj=self)

        # this is used to get fast the name of what is being transcribed currently
        self.transcription_queue_current_name = None

        # this is to keep track of the current transcription item
        # the format is {queue_id: transcription_item_attributes}
        self.transcription_queue_current_item = {}

        # declare this as none for now so we know it exists
        self.toolkit_UI_obj = None

        # use this to store the whisper model later
        self.whisper_model = None

        # load the whisper model from the config
        # we're recommending the medium model for better accuracy vs. time it takes to process
        # if in doubt use the large model but that will need more time
        self.whisper_model_name = self.stAI.get_app_setting(setting_name='whisper_model_name', default_if_none='medium')

        # get the whisper device setting
        # currently, the setting may be cuda, cpu or auto
        self.torch_device = stAI.get_app_setting('torch_device', default_if_none='auto')

        self.torch_device = self.torch_device_type_select(self.torch_device)

        # now let's deal with the sentence transformer model
        # this is the transformer model name that we will use to search semantically
        self.s_semantic_search_model_name \
            = self.stAI.get_app_setting(setting_name='s_semantic_search_model_name',
                                        default_if_none='msmarco-distilbert-base-v4')

        # for now define an empty model here which should be loaded the first time it's needed
        # it's very likely that the model will not be loaded here, but in the SearchItem, for each search
        self.s_semantic_search_model = None

        self.processing_queue = self.ProcessingQueue(toolkit_ops_obj=self)

        # this is used by the queue dispatcher to know which functions to call depending on the task
        # the key is the name of the task, the value is a list of functions to call for that task
        # the queue dispatcher may also merge multiple tasks into one (for eg. if transcribe+ingest is called)
        self.queue_tasks = {
            'transcribe': [self.whisper_transcribe],
            'translate': [self.whisper_transcribe],
            'group_questions': [self.group_questions]
            # 'ingest': [self.index_video] # this will be added soon
        }

        # use this to store all the devices that can be used for processing queue tasks
        self.queue_devices = self.get_torch_available_devices()

        # use this to know whether the resolve API is disabled or not for this session
        self.disable_resolve_api = disable_resolve_api

        # if this is True, it means that there is a polling thread running
        self.polling_resolve = False

        # to hold the resolve API object
        self.resolve_api = None

        # init Resolve but if...

        # ... if --noresolve was passed as an argument, disable the resolve API
        if '--noresolve' in sys.argv:
            self.resolve_api = None
            self.disable_resolve_api = True
            logger.debug('Resolve API disabled via --noresolve argument.')

        # ... and if the resolve API is disabled via config, disable the resolve API
        elif self.stAI.get_app_setting('disable_resolve_api', default_if_none=True):
            self.resolve_api = None
            self.disable_resolve_api = True
            logger.debug('Resolve API disabled via config.')

        # ... then, init Resolve
        if not self.disable_resolve_api:
            self.resolve_enable()

        # resume the transcription queue if there's anything in it
        if self.processing_queue.resume_queue_from_file():
            logger.info('Resuming queue from file')

        # add observers so that we can update the UI when something changes
        # this dictionary will hold all the actions and their observers (for eg. from the UI)
        self._observers = {}

    def attach_observer(self, action, observer):
        """
        Attach an observer to an action
        """

        if action not in self._observers:
            self._observers[action] = []

        # add the observer to the list of observers for this action
        self._observers[action].append(observer)

    def dettach_observer(self, action, observer):
        """
        Dettach an observer from an action
        """

        if action not in self._observers:
            return False

        # add the observer to the list of observers for this action
        self._observers[action].remove(observer)

        # if the list is empty, remove the action
        if len(self._observers[action]) == 0:
            del self._observers[action]

    def notify_observers(self, action):
        """
        Use this to notify all observers if a certain action has been performed
        """

        # no observers for this action
        if action not in self._observers:
            return False

        # notify all observers for this action
        for observer in self._observers[action]:

            observer.update()

    class ToolkitAssistant:
        '''
        This is the main class for the assistant
        '''

        def __init__(self, toolkit_ops_obj):
            # load the toolkit ops object
            self.toolkit_ops_obj = toolkit_ops_obj

            # load the stAI object
            self.stAI = self.toolkit_ops_obj.stAI

            # load the toolkit UI object
            self.toolkit_UI_obj = self.toolkit_ops_obj.toolkit_UI_obj

    class AssistantGPT(ToolkitAssistant):
        '''
        This is a class that is used to create an OpenAI GPT-based assistant
        It should be instantiated for each assistant and then used to pass queries
        and results between UI and whatever assistant model / API we're using
        '''

        def __init__(self, **kwargs):

            super().__init__(toolkit_ops_obj=kwargs.get('toolkit_ops_obj', None))

            # get the stAI object (needed for statistics)
            self.stAI = self.toolkit_ops_obj.stAI

            # save the model provider for internal use
            self.model_provider = 'openai'

            # get all the attributes from the kwargs
            self.model_name = kwargs.get('model_name', "gpt-3.5-turbo")

            # store the number of tokens used for the assistant
            self.usage = 0

            # the price per 1000 tokens - this should probably be stored somewhere else
            self.price = 0.002

            self.initial_system = kwargs.get('initial_system',
                                             "You are an assistant editor that gives succinct answers.")

            # keep a chat history, which can be also altered if needed
            # if no chat history is passed, we'll use a default one which defines the system
            self.chat_history = kwargs.get('chat_history',
                                           [{"role": "system", "content": self.initial_system}])

            # to keep track of the context
            self.context = kwargs.get('context', None)

            # and the index of the context in the chat history
            self.context_idx = None

            if self.context is not None:
                # add the context to the chat history
                self.add_context(self.context)

            # get the API key from the config
            openai.api_key = self.api_key \
                = self.stAI.get_app_setting(setting_name='openai_api_key', default_if_none=None)

        def reset(self):
            '''
            This function is used to reset the assistant, by clearing the chat history
            '''

            # just reset the chat history to the initial system message
            self.chat_history = [{"role": "system", "content": self.initial_system}]

            # also re-add the context if it exists
            if self.context is not None:
                self.context_idx = len(self.chat_history)

                # add the context to the chat history
                self.chat_history.append({"role": "user", "content": self.context})

        def set_initial_system(self, initial_system):

            initial_system_changed = False

            # check so that the initial system message is not empty
            if not initial_system:

                # set the initial system message
                self.initial_system = initial_system

                # find the system message in the chat history
                for i, message in enumerate(self.chat_history):

                    # if the role is system, then we've found the system message
                    if message['role'] == 'system':
                        # set the new system message
                        self.chat_history[i]['content'] = self.initial_system

                        initial_system_changed = True

                        break

                # if we didn't find the system message, then we'll just add it on top
                self.chat_history.insert(0, {"role": "system", "content": self.initial_system})

                return True

            # just return false if the initial system message is empty
            logger.debug('Initial system message is empty. Not changing it.')
            return False

        def add_context(self, context):
            '''
            This function is used to add context to the assistant by introducing a message with the context string,
            right after the initial system message
            '''

            # check so that the context is not empty
            if context:

                # if we already set the context, then we'll just change it
                if self.context is not None and self.context_idx is not None:
                    # change the context in the chat history
                    self.chat_history[self.context_idx]['content'] = context

                    # remember that we've changed the context
                    self.context = context

                    logger.debug('Changed context in the chat history.')

                    return True

                # otherwise we'll just add it
                # find the system message in the chat history
                for i, message in enumerate(self.chat_history):

                    # if the role is system, then we've found the system message
                    if message['role'] == 'system':
                        # insert the context message right after the system message
                        self.chat_history.insert(i + 1, {"role": "user", "content": context})

                        # remember that we've added the context
                        self.context = context

                        # remember the index of the context in case we need to change it later
                        self.context_idx = i + 1

                        logger.debug('Added context to the chat history.')

                        return True

                logger.debug('Could not find the system message in the chat history. Adding the context on top.')

                # if we didn't find the system message, then we'll just add it on top
                self.chat_history.insert(0, {"role": "user", "content": context})

                # remember that we've added the context
                self.context = context

                return True

            elif context is not None and context == '':

                # just remove any context that might exist
                if self.context is not None and self.context_idx is not None:
                    # remove the context from the chat history
                    self.chat_history.pop(self.context_idx)

                    # remember that we've removed the context
                    self.context = None
                    self.context_idx = None

                    logger.debug('Removed context from the chat history.')

            else:
                logger.debug('Context is empty. Ignoring add context request.')
                return False

        def calculate_history(self):
            '''
            This calculates the amount of tokens used by the assistant
            on each query taken into consideration the current chat_history (but without the query itself)
            '''

            # use tiktoken to calculate the number of tokens used by the assistant
            # encoding = tiktoken.get_encoding("cl100k_base")
            encoding = tiktoken.encoding_for_model(self.model_name)

            # turn the chat history into a string take the 'content' field from each message
            chat_history_str = ' '.join([message['content'] for message in self.chat_history])

            # the number of tokens used for the chat history
            tokens = len(encoding.encode(chat_history_str))

            return tokens

        def add_usage(self, tokens):
            '''
            This function is used to add usage of the assistant
            '''

            # add the usage for the current assistant item
            self.usage += tokens

            # but also keep track of the total usage of this model since the tool was started
            self.stAI.update_statistics('assistant_usage_{}_{}'.format(self.model_provider, self.model_name),
                                        self.usage)

            # print(self.stAI.statistics)

        def send_query(self, content):
            '''
            This function is used to send a query to the assistant
            '''

            # the query should always contain the role and the content
            # the role should be either user, system or assistant
            # in this case, since we're sending a query, the role should be user

            query = {"role": "user", "content": content}

            # add the query to the chat history
            self.chat_history.append(query)

            # print(json.dumps(self.chat_history, indent=4))

            # now send the query to the assistant
            try:
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=self.chat_history
                )

            except openai.error.AuthenticationError as e:

                error_message = 'Please check your OpenAI Key in the preferences window.\n' + \
                                str(e)

                logger.debug('OpenAI API key is invalid. Please check your key in the preferences window.')
                return error_message

            except Exception as e:
                logger.debug('Error sending query to AssistantGPT: ')
                logger.debug(e)
                return str(e) + "\nI'm sorry, I'm having trouble connecting to the assistant. Please try again later."

            result = ''
            for choice in response.choices:
                result += choice.message.content

                # add the result to the chat history
                self.chat_history.append({"role": "assistant", "content": result})

            # add the usage to the total usage
            self.add_usage(response.usage.total_tokens)

            return result

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

    class SearchItem(ToolkitSearch):
        '''
        This is a class that represents a single search item.
        It should be instantiated for each search and then used to pass queries
        and results between UI and the search engine

        '''

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

        def process_file_paths(self, search_paths=None):
            '''
            This function will process the file paths that were passed to the search function
            :return:
            '''

            search_file_paths = []

            if search_paths is None:
                logger.debug('No search paths were passed to the search function')
                return None

            # if the search path contains only one file
            # which ends with .pkl we'll return it directly
            # to be used as a search corpus (search cache)
            # if search_paths is not None \
            #        and ((type(search_paths) is str and os.path.isfile(search_paths)) \
            #             or ((type(search_paths) is list or type(search_paths) is tuple)
            #                 and len(search_paths) == 1 and os.path.isfile(search_paths[0]))) \
            #        and search_paths[0].endswith('.pkl'):
            #    return search_paths[0]

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

        def load_file_paths_to_search_dict(self, file_paths):
            '''
            Loads the file paths to a dictionary that can be used for searching
            :param file_paths: this can be a list of file paths or a single file path
            :return:
            '''

            # if no transcription file paths were provided
            if file_paths is None or len(file_paths) == 0:
                # throw an error if no transcription file was passed
                logger.error('Cannot search. No file path was passed.')

            # if only one transcription file path is given, make it a list
            if type(file_paths) is str:
                file_paths = [file_paths]

            # define the transcriptions dict
            search_files = {}

            # take all the transcription file paths and load them into the search_transcriptions dictionary
            for s_file_path in file_paths:

                # if a specific transcription file was passed, use that in the search
                if s_file_path is not None:

                    # don't include the file if it doesn't exist
                    if not os.path.isfile(s_file_path):
                        logger.error('File {} not found. Skipping.'.format(s_file_path))
                        continue

                    # now read the transcription file contents
                    search_files[s_file_path] = \
                        self.toolkit_ops_obj.get_transcription_file_data(
                            transcription_file_path=s_file_path)

            return search_files

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
                ta = TextAnalysis()

                # take each file path and load the search data
                for s_file_path in search_file_paths:

                    # decide what to do based on the file extension

                    # if it's TRANSCRIPTION FILE
                    if s_file_path.endswith('.transcription.json'):

                        # first get the transcription file data
                        transcription_file_data = self.toolkit_ops_obj.get_transcription_file_data(
                            transcription_file_path=s_file_path)

                        if type(transcription_file_data) is not dict \
                                or 'segments' not in transcription_file_data:
                            logger.warning('Transcription file {} is not in the right format. Skipping.'
                                           .format(s_file_path))

                        elif type(transcription_file_data) is dict \
                                and 'segments' in transcription_file_data \
                                and type(transcription_file_data['segments']) is list:

                            # detect the language of the transcription if we don't know it already
                            if 'language' not in transcription_file_data:
                                transcription_language \
                                    = ta.detect_language(''.join([segment['text']
                                                                  for segment in transcription_file_data['segments']]))

                                # if we know the language of the transcription
                                if transcription_language is not None:

                                    transcription_file_data['language'] = transcription_language

                                    # save it to the transcription file
                                    if self.toolkit_ops_obj.save_transcription_file(
                                            transcription_file_path=s_file_path,
                                            transcription_data=transcription_file_data,
                                            backup='backup'):
                                        logger.debug(
                                            'Saved language to transcription file: {}'.format(s_file_path))

                            else:
                                transcription_language = transcription_file_data['language']

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
                                    segments=transcription_file_data['segments'],
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
                            timecode_data = \
                                self.toolkit_ops_obj.transcription_has_timecode_data(transcription_file_data)

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
                                        else self.toolkit_ops_obj.convert_sec_to_transcription_timecode(
                                        segment['start'], transcription_file_data
                                    )

                                    search_corpus_assoc[general_segment_index] = {
                                        'transcription_file_path': transcription_file_path,
                                        'name': transcription_file_data['name']
                                        if 'name' in transcription_file_data else os.path.basename(
                                            transcription_file_path),
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
                                # but only if it's longer than 2 characters to avoid adding stuff that is most likely meaningless
                                # like punctuation marks
                                if 'text' in segment and type(segment['text']) is str:

                                    # keep adding segments to the current phrase until we find a punctuation mark

                                    # first get the segment text
                                    segment_text = str(segment['text'])

                                    # add the segment to the current phrase
                                    current_phrase += segment_text.strip() + ' '

                                    # if a punctuation mark exists in the last 5 characters of the segment text
                                    # it means that the current phrase is complete
                                    if re.search(r'[\.\?\!]{1}$', segment_text[-5:]):
                                        # "close" the current phrase by adding it to the search corpus
                                        search_corpus_phrases.append(current_phrase.strip())

                                        # and remember it as the previous phrase
                                        previous_phrase = current_phrase

                                        # then empty the current phrase
                                        current_phrase = ''

                            if 'transcript_groups' in transcription_file_data:

                                # take each transcript group
                                for transcript_group in transcription_file_data['transcript_groups']:
                                    general_segment_index = len(search_corpus_phrases)

                                    # and add the transcript group name and group notes to the search corpus association
                                    search_corpus_assoc[general_segment_index] = {
                                        'file_path': transcription_file_path,
                                        'transcription_name': transcription_file_data['name']
                                        if 'name' in transcription_file_data else os.path.basename(
                                            transcription_file_path),
                                        'type': 'transcript_group',
                                        'group_name': transcript_group
                                    }

                                    # and add the transcript group name to the search corpus phrases
                                    search_corpus_phrases.append(
                                        transcription_file_data['transcript_groups'][transcript_group]['name']
                                        + ': '
                                        + transcription_file_data['transcript_groups'][transcript_group]['notes']
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
                    'Loading sentence transformer model {}.'.format(self.model_name))

                # if the sentence transformer model was never downloaded, log that we're downloading it
                model_downloaded_before = True
                if self.stAI.get_app_setting(setting_name='s_semantic_search_model_downloaded_{}'
                        .format(self.model_name), default_if_none=False) is False:
                    logger.warning('The sentence transformer model {} may need to be downloaded and could take a while '
                                   'depending on the Internet connection speed. '
                                   .format(self.model_name)
                                   )
                    model_downloaded_before = False

                self.search_model \
                    = SentenceTransformer(self.model_name)

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

        def save_corpus_embeddings_to_file(self, embeddings, file_path=None):

            if file_path is None:
                file_path = self.corpus_cache_file_path

            if file_path is None:
                logger.debug('Aborting. No cache file path specified.')
                return

            try:

                # check if the directory exists
                if not os.path.exists(os.path.dirname(file_path)):
                    # otherwise, create it
                    os.makedirs(os.path.dirname(file_path))

                # save the corpus embeddings to a file
                with open(file_path, 'wb') as f:
                    pickle.dump(embeddings, f)

                # save a json file next to the pickle file with the same name
                # that contains the file list and full path of all the files in the corpus
                # this is useful in case we want to clean up the corpus cache directory
                with open('{}.json'.format(file_path), 'w') as f:
                    json.dump(self.search_file_paths, f, indent=4)

                logger.debug('Saved encoded search corpus to {}'.format(file_path))

                return True

            except Exception as e:

                import traceback
                traceback.print_exc()

                logger.error('Could not save search embeddings to file {}'.format(file_path))
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
                # load the corpus embeddings from the file
                with open(corpus_cache_file_path, 'rb') as f:
                    corpus_embeddings = pickle.load(f)

                # touch the file to update the last modified time
                # this will be useful if we want to ever clean up the cache
                # (e.g. delete files unused for 90 days)
                os.utime(corpus_cache_file_path, None)

                # add the corpus embeddings to the memory cache
                self.search_embeddings[search_id] = corpus_embeddings

                logger.debug('Loaded encoded search corpus from {}'.format(corpus_cache_file_path))

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
                self.save_corpus_embeddings_to_file(corpus_embeddings)

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

    class TranscriptGroups:
        '''
        This class contains functions for working with transcript groups.
        '''

        def __init__(self, toolkit_ops_obj):

            # define the toolkit operations object
            self.toolkit_ops_obj = toolkit_ops_obj

            # and the stAI object
            self.stAI = toolkit_ops_obj.stAI

        def get_all_transcript_groups(self, transcription_file_path: str = None, transcription_data=None) \
                -> dict or None:
            '''
            This function returns a list of transcript groups for a given transcription file or transcription data.

            :param: transcription_file_path: the path to the transcription file
            :return: a dict of transcript groups or None if the transcription file doesn't exist
            '''

            if transcription_data is None and transcription_file_path is None:
                logger.error('Unable to get transcript groups '
                             '- no transcription file path or transcription data provided.')
                return None

            # if no transcription data was provided, load the transcription file
            if transcription_data is None:
                # load the transcription file
                # get the contents of the transcription file
                transcription_data = \
                    self.toolkit_ops_obj.get_transcription_file_data(
                        transcription_file_path=transcription_file_path)

            # if the transcription file data was cannot be loaded, return None
            if transcription_data is False:
                return None

            # check if the transcription has any transcript groups
            # and return accordingly
            if 'transcript_groups' not in transcription_data:
                return {}
            else:
                logger.debug('Transcript groups found in transcription {}'.format(transcription_file_path))
                return transcription_data['transcript_groups']

        def get_transcript_group(self, transcription_file_path: str, transcript_group_id: str) -> dict or None:
            '''
            Get a transcript group by its name from a given transcription file.

            The groups are stored in a list in the transcription file.

            :param transcription_file_path:
            :param transcript_group_id:
            :return: a list of transcript groups or None if the transcription file doesn't exist
            '''

            # get the transcript groups
            transcript_groups = self.get_all_transcript_groups(transcription_file_path=transcription_file_path)

            # if the previous call returned None it's likely that the transcription file cannot be loaded
            if transcript_groups is None:
                return None

            # loop through the transcript groups
            # the groups are stored in a list, and each group is a dict, with the group name as the key
            for transcript_group in transcript_groups:

                # if the transcript group name matches the one we're looking for, return it
                if transcript_group_id in transcript_group:
                    return transcript_group[transcript_group_id]

            # if we get here, the transcript group was not found
            return {}

        def save_transcript_groups(self, transcription_file_path: str, transcript_groups: dict,
                                   group_id: str = None) -> dict or bool or None:
            '''
            This function saves transcript groups to a transcription file.

            It will overwrite any existing transcript groups in the transcription file.

            :param transcription_file_path:
            :param transcript_groups:
            :param group_id: If this is passed, we will only save the transcript group with this group id
            :return: The group dict if the groups were saved successfully, False otherwise
                    or None if there were other problems transcription file
            '''

            # first, get the transcription file data
            transcription_file_data = \
                self.toolkit_ops_obj.get_transcription_file_data(
                    transcription_file_path=transcription_file_path)

            # if the transcription file data was cannot be loaded, return None
            if transcription_file_data is None:
                return None

            # if no group id was passed, overwrite all transcript groups
            if group_id is None:

                # overwrite the transcript groups with the passed transcript_groups
                transcription_file_data['transcript_groups'] = transcript_groups

            # otherwise, only focus on the passed group id
            else:

                # one final strip and lower to make sure that the group_id is in the right format
                group_id = group_id.strip().lower()

                # but make sure that it was passed correctly in the transcript_groups dict
                if group_id not in transcript_groups:
                    logger.error('The transcript group id {} was not found in the transcript_groups dict.'
                                 .format(group_id))
                    return False

                # if the transcript groups key doesn't exist, create it
                if 'transcript_groups' not in transcription_file_data:
                    transcription_file_data['transcript_groups'] = {}

                # if the group with the group_id exists, remove it
                if group_id in transcription_file_data['transcript_groups']:
                    del transcription_file_data['transcript_groups'][group_id]

                # now add the transcript group to the transcript groups
                transcription_file_data['transcript_groups'][group_id] = transcript_groups[group_id]

            # save the transcription file data
            saved = self.toolkit_ops_obj.save_transcription_file(
                transcription_file_path=transcription_file_path,
                transcription_data=transcription_file_data,
                backup='backup')

            if not saved:
                return False

            # return the saved transcript groups
            return transcription_file_data['transcript_groups']

        def group_id_from_name(self, group_name):
            '''
            This function returns a group id from a group name.

            For now, we're simply stripping and lowercasing the group name.

            :param group_name:
            :return: the group id
            '''

            # first, strip and lower the group name
            group_name = group_name.strip().lower()

            # and return the group name
            return group_name

        def prepare_transcript_group(self, group_name: str, time_intervals: list,
                                     group_id: str = None, group_notes: str = '',
                                     existing_transcript_groups: list = None,
                                     overwrite_existing: bool = False) -> dict:
            '''
            This function prepares a transcript group dict.

            Each group is a dict with the following keys: name, notes, time_intervals

            The purpose is to be able to group together segments of a transcription, although the start and end times
            of the groups are not necessarily always the same as the start and end times of the segments.

            :param group_name:
            :param time_intervals:
            :param group_id:
            :param group_notes:
            :param existing_transcript_groups: if a transcript group is being updated, pass its contents here
            :param overwrite_existing: if the same group_id is found in the existing transcript groups, overwrite it
            :return: the transcript group dict or None if something went wrong
            '''

            # trim the group name and group notes
            group_name = group_name.strip()
            group_notes = group_notes.strip()

            # if the group id is not provided, use the group name
            if group_id is None:
                # generate a group id
                group_id = self.group_id_from_name(str(group_name))

            # always lowercase the group id
            group_id = group_id.lower()

            # if we're not overwriting an existing group, see if the group id already exists in existing groups
            if not overwrite_existing \
                    and existing_transcript_groups is not None \
                    and type(existing_transcript_groups) is list \
                    and len(existing_transcript_groups) > 0:

                # keep coming up with group id suffixes until we find one that doesn't exist
                group_name_suffix = 1
                while True:

                    # first try the group name as is
                    if group_name_suffix != 1:
                        # but after the first iteration, add a suffix (should start at 2)
                        group_id = self.group_id_from_name(group_name + '_' + str(group_name_suffix))

                    # if the group id doesn't exist in the existing groups, break out of the loop
                    # (convert all to lowercase for comparison to avoid any sort of case sensitivity issues)
                    if str(group_id).lower() not in list(map(str.lower, existing_transcript_groups)):
                        break

                    # if the group id already exists, increment the suffix and try again
                    group_name_suffix += 1

            # return the prepared transcript group
            return {
                group_id: {
                    'name': group_name,
                    'notes': group_notes,
                    'time_intervals': time_intervals
                }
            }

        def segments_to_groups(self, segments: list, group_name: str, group_id: str = None,
                               group_notes: str = '', existing_transcript_groups: list = None,
                               overwrite_existing: bool = False) -> dict or None:
            '''
            This function converts a list of transcript segments to a transcript group

            :param segments: a list of transcript segments
            :param group_name: the name of the transcript group
            :param group_id: the id of the transcript group
            :param group_notes: the notes of the transcript group
            :param existing_transcript_groups: if a transcript group is being updated, pass its contents here
            :param overwrite_existing: if the same group_id is found in the existing transcript groups, overwrite it
            :return: the transcript group dict or None if something went wrong
            '''

            # first, get the time intervals from the segments
            group_time_intervals = []

            # if the segments are empty or not a list, return None
            if segments is None or type(segments) is not list:
                return None

            # get a proper list of time intervals based on the segments
            group_time_intervals = self.toolkit_ops_obj.transcript_segments_to_time_intervals(segments=segments)

            if group_time_intervals is None:
                return None

            # if the time intervals are empty, return None
            if len(group_time_intervals) == 0:
                return None

            # prepare the transcript group
            transcript_group = \
                self.prepare_transcript_group(
                    group_name=group_name,
                    time_intervals=group_time_intervals,
                    group_id=group_id,
                    group_notes=group_notes,
                    existing_transcript_groups=existing_transcript_groups,
                    overwrite_existing=overwrite_existing)

            return transcript_group

        def save_segments_as_group_in_transcription_file(self,
                                                         transcription_file_path: str,
                                                         segments: list,
                                                         group_name: str,
                                                         group_id: str = None,
                                                         group_notes: str = '',
                                                         existing_transcript_groups: list = None,
                                                         overwrite_existing: bool = False) -> str or None:
            '''
            This function saves a list of transcript segments as a group in a transcription file

            The transcription file must already exist in order to save the transcript group.

            :param transcription_file_path:
            :param segments: a list of transcript segments
            :param group_name: the name of the transcript group
            :param group_id: the id of the transcript group
            :param group_notes: the notes of the transcript group
            :param existing_transcript_groups: if a transcript group is being updated, pass its contents here
            :param overwrite_existing: if the same group_id is found in the existing transcript groups, overwrite it
            :return: the transcript group id or None if something went wrong
            '''

            # first, prepare the transcript group
            transcript_group = self.segments_to_groups(segments=segments, group_name=group_name, group_id=group_id,
                                                       group_notes=group_notes,
                                                       existing_transcript_groups=existing_transcript_groups,
                                                       overwrite_existing=overwrite_existing)

            if transcript_group is None or type(transcript_group) is not dict:
                logger.debug('Could not prepare transcript group from segments for saving')
                return None

            # get the group id that may have been generated while creating the transcript group
            group_id = list(transcript_group.keys())[0]

            # finally, save the transcript group
            saved = self.save_transcript_groups(transcription_file_path=transcription_file_path,
                                                transcript_groups=transcript_group, group_id=group_id)

            if not saved:
                logger.debug('Could not save to transcription file {} the following transcript group: {}'.
                             format(transcription_file_path, transcript_group))

            # elif :
            #    saved = group_id

            logger.debug('Saved transcript groups {} to transcription file {}'
                         .format(list(transcript_group.keys()), transcription_file_path))
            return saved

    class ProcessingQueue:
        '''
        This class handles the processing queue:
        '''

        def __init__(self, toolkit_ops_obj=None, toolkit_UI_obj=None):
            self.toolkit_ops_obj = toolkit_ops_obj
            self.toolkit_UI_obj = toolkit_UI_obj

            # this holds the queue ids of the items that need to be processed next
            # once the item is sent for processing, it is removed from this list and only remains in the queue history
            # since it's an ordered list, the first item in the list is the next item to be processed
            self.queue = []

            # this holds the queue history
            # - when an object is added to the queue it must also have a corresponding entry in the queue history
            # - we are only tracking the status of the object in the queue history
            # - when an object sent for processing it will remain in the history so that we can track its status
            self.queue_history = []

            # this keeps track of the threads that are processing the queue by device
            # the key is the device name and the value is a dict with the queue id and the thread object
            # for eg. {'cuda:0': {'queue_id': queue_id, 'thread': <Thread(Thread-1, started 1234567890123)>}, ...}
            self.queue_threads = {}

            # this holds other variables that don't need to be part of the queue history,
            # but can be shared between threads
            # the key is the queue id and the value is a dict variable names and values
            self.queue_variables = {}

            # how much to wait until checking if there are items in the queue that can be processed
            # disabled for now - if we activate this we need to make sure that the device is not used by another thread
            # by checking the queue_threads dict
            # self.queue_check_interval = 30 # seconds

        def generate_queue_id(self, name: str=None) -> str:
            """
            This function generates a queue id for a task
            """

            # keep generating a queue id until it's not similar to one that already exists in the queue history
            while True:

                # use the name if one was provided
                # and a timestamp to make it as unique as possible
                queue_id = "{}{}".format(((name.replace(' ', '') + '-') if name else ''), time.time())

                # if the queue id doesn't return an item
                if not self.get_item(queue_id=queue_id):

                    # add it to the queue history
                    self.queue_history.append({'queue_id': queue_id, 'status': 'pending'})

                    logger.debug('Added queue id {} to queue history'.format(queue_id))

                    return queue_id

        def add_to_queue(self,
                         tasks: list or str = None,
                         queue_id: str = None,
                         source_file_path=None,
                         task_data=None,
                         device=None,
                         required_device_type=None,
                         **kwargs
                         ) -> str or bool:
            """
            This function adds a task to the processing queue
            It either needs a source_file_path (audio, video etc.)
            or directly the task_data (transcription, search corpus etc.)

            Once it adds the task, it also pings the queue manager to start processing the queue
            (if it is not already running)

            :param tasks: a list of tasks to be added to the queue, or a single task
                (don't confuse with the task queue, which will be determined by the task dispatcher based on this list)
            :param queue_id: the queue id of the task - if None, one will be generated
            :param source_file_path: the path(s) to the source file(s) - if empty, we need to have the task_data
            :param task_data: the task data (transcription, search corpus etc.) - if empty, we need a source_file_path
            :param device: the device to use for processing the task, if empty,
                            we will use the next available device suitable for the task (device_required must be passed)
            :param required_device_type: the device type required for processing the task (cpu, cuda, etc.)
            :param kwargs: any other key-value pairs to be added to the queue item
            :return: the queue id of the task or False if something went wrong

            """

            # if the queue id is not passed, generate one
            if not queue_id:
                queue_id = self.generate_queue_id(name=kwargs.get('name', None))

            # check if we have task queue (a list of functions to be executed) via the task dispatcher
            task_queue = self.task_dispatcher(tasks=tasks)

            # if we don't have a task queue, abort
            if not task_queue:
                logger.error('Empty task queue - could not add item {} to queue'.format(queue_id))
                return False

            # if we have a task queue, add it to the kwargs
            kwargs['task_queue'] = task_queue

            # also add the tasks for future reference
            kwargs['tasks'] = tasks

            # if we don't have source files nor task data, abort
            if not source_file_path and not task_data:
                logger.error('Invalid task (no source files or data) - could not add item {} to queue'
                             .format(queue_id))
                return False

            # add the queue_id to the kwargs
            kwargs['queue_id'] = queue_id

            # if we have a source file path, add it to the kwargs
            if source_file_path:
                kwargs['source_file_path'] = source_file_path

            # if we have task data, add it to the kwargs
            if task_data:
                kwargs['task_data'] = task_data

            # if we have a device, add it to the kwargs
            if device is None:
                logger.error('Device must be specified when adding an item to the queue')
                return False

            # make sure we have a string as a device, and not a torch.device object
            if isinstance(device, torch.device):
                device = str(device.type)

            kwargs['device'] = device

            # if we have a required device type, add it to the kwargs
            if required_device_type:
                kwargs['required_device_type'] = required_device_type

            # add the 'queued' status to the kwargs
            kwargs['status'] = 'queued'

            # check if the queue id already exists in the queue history
            item = self.get_item(queue_id=queue_id)
            if not item:

                # add the kwargs to the queue history
                self.queue_history.append(kwargs)

                logger.debug('Added item {} to queue history'.format(queue_id))

            else:
                # just update the item, but make sure that the queue id is not stripped
                kwargs['queue_id'] = queue_id
                self.update_queue_item(**kwargs)

            # add the queue id to the queue
            self.queue.append(queue_id)

            logger.debug('Added item {} to queue'.format(queue_id))

            # ping the queue to start processing
            self.ping_queue()

            # save the queue to a file
            self.save_queue_to_file()

            # throttle for a bit to avoid queue id queue id collisions,
            # if this is a batch
            time.sleep(0.01)

            # return the queue id if we reached this point
            return queue_id

        def add_dependency(self, queue_id, dependency_id = None):
            """
            This adds the dependency_id to the list of dependencies of the queue_id
            """

            # get the item
            item = self.get_item(queue_id)

            # if the item doesn't exist, abort
            if not item:
                logger.error('Unable to add dependency - queue id {} not found in queue history'.format(queue_id))
                return False

            # if the item exists, add the dependency_id to the list of dependencies
            if dependency_id:

                if 'dependencies' not in item:
                    item['dependencies'] = []

                item['dependencies'].append(dependency_id)

            # update the item
            self.update_queue_item(**item)

            # return the item
            return item

        def pass_dependency_data(self, queue_id, dependency_id, override=False, save_to_file=False):
            """
            This passes all the data from the item with the dependency_id to the item with the queue_id
            (all except the queue_id and name)

            This will not overwrite any existing data in the item with the queue_id, unless override is set to True
            """

            # the stuff that we're never supposed to override
            override_not_allowed = ['queue_id', 'name', 'tasks', 'device', 'task_queue', 'dependencies']

            # get the item
            item = self.get_item(queue_id)

            # if the item doesn't exist, abort
            if not item:
                logger.error('Unable to pass dependency data - queue id {} not found in queue history'.format(queue_id))
                return False

            # get the dependency item
            dependency_item = self.get_item(dependency_id)

            # if the dependency item doesn't exist, abort
            if not dependency_item:
                logger.error('Unable to pass dependency data - dependency id {} not found in queue history'
                             .format(dependency_id))
                return False

            # if the dependency item exists, pass all the data from the dependency item to the item
            # except the queue-related data above
            for key, value in dependency_item.items():

                # we will use the override_not_allowed list to make sure we don't override stuff
                # also, we will only override if override is set to True
                if (override or key not in item) and key not in override_not_allowed:

                    # pass the key-value pair to the item
                    item[key] = value

            # update the item
            self.update_queue_item(**item, save_to_file=save_to_file)

        def update_queue_item(self, queue_id, save_to_file=True, **kwargs):
            """
            This function updates a queue item in the queue history

            :param queue_id: the queue id of the queue item to be updated
            :param save_to_file: whether to save the queue to a file after updating the item
            :param kwargs: the key-value pairs to be updated

            :return: the updated queue item or False if something went wrong
            """

            # get the full item and make sure you don't strip the queue id
            item = self.get_item(queue_id)

            if not item:
                logger.error('Unable to update queue item - queue id {} not found in queue history'.format(queue_id))
                return False

            # update the item
            new_item = item

            # keep all the existing keys and values, but update the ones that are passed in kwargs
            for key, value in kwargs.items():
                new_item[key] = value

            # make sure to always pass the queue id too
            new_item['queue_id'] = queue_id

            # find the item index in the queue history according to its queue id
            for index, item in enumerate(self.queue_history):
                if 'queue_id' in item and item['queue_id'] == queue_id:
                    item_index = index

                    # replace the item in the queue history
                    self.queue_history[item_index] = new_item

                    # whenever the status is updated, make sure you update the window too
                    # but only if the UI object exists
                    if self.toolkit_ops_obj.is_UI_obj_available():
                        self.toolkit_ops_obj.toolkit_UI_obj.update_queue_window()

                    # todo: use observer pattern to notify the UI object instead of the above
                    # self.toolkit_ops_obj.notify_observers('update_queue_item_{}'.format(queue_id))

                    # save the queue to a file
                    if save_to_file:
                        self.save_queue_to_file()

                    # and return the updated item
                    return new_item

            # let's hope this doesn't happen...
            return False

        def reorder_queue(self, new_queue_order) -> bool:
            """
            This function takes the new queue order and re-orders the queue and the queue history accordingly,
            but does not add items that are not in the queue

            :param new_queue_order: the new queue order
            :return:
            """

            # return False if the new queue order is not a list
            if not isinstance(new_queue_order, list):
                logger.error('Unable to reorder queue - new queue order is not a list')
                return False

            # first, reorder the QUEUE (then the queue history)

            # start by removing all the items that are not in the queue
            new_queue_order = [item for item in new_queue_order if item in self.queue]

            # now check that the new queue is the same length as the old queue
            if len(new_queue_order) != len(self.queue):
                logger.error('Unable to reorder queue - new queue order is not the same length as the queue')
                return False

            # but if the queues are empty, just return True
            if not new_queue_order and not self.queue:
                logger.debug("Queue is empty, nothing to reorder.")
                return True

            # re-order the queue
            self.queue = new_queue_order

            # now re-order the QUEUE HISTORY

            # organize all the items that have the status 'processing', 'done', or 'failed' in a list
            # these items will stay at the beginning of the queue history
            # with their original order since they're finished
            processed_items = [item for item in self.queue_history
                               if 'queue_id' in item
                               and 'status' in item
                               and item['status'] in ['processing', 'done', 'failed', 'canceled', 'canceling']
                               ]

            # extract queue_ids of processed items
            processed_ids = [item['queue_id'] for item in processed_items]

            # remove any processed items from the new_queue_order list by the 'queue_id' key in processed_items
            new_queue_order = [item for item in new_queue_order if item['queue_id'] not in processed_ids]

            # now create a list of dictionaries with the remaining items in the new_queue_order
            # - keep their entire dictionary structure from the queue history
            # - but use the order in the new_queue_order list

            # start the remaining items list with the processed items
            queue_history = processed_items
            for item in new_queue_order:

                # get the item from the queue history
                queue_item = self.get_item(queue_id=item['queue_id'])

                # if the item is not in the queue history, skip it
                if queue_item is None:
                    continue

                # add the item to the remaining items list
                queue_history.append(queue_item)

            # now replace the queue history with the remaining items list
            self.queue_history = queue_history

            return True

        def cancel_item(self, queue_id: str):
            '''
            This function removes a task from the queue of items to be processed

            And updates the status in the queue history to 'canceled'
            '''

            if queue_id is None:
                logger.error('Unable to cancel item - queue id is None')
                return False

            # remove the item from the queue
            # (to avoid processing it if it's not already being processed)
            if queue_id in self.queue:
                self.queue.remove(queue_id)

            # try to get the item from the queue history
            item = self.get_item(queue_id)

            if not item:
                logger.warning('Unable to cancel item - queue id {} not found in queue history'.format(queue_id))
                return None

            # if the current status is 'done' or 'failed',
            # it doesn't make sense to cancel it
            if item['status'] in ['done', 'failed']:
                logger.debug('Item {} is already done or failed, cannot cancel.'
                             .format(queue_id))

            # check if the item is currently processing in the thread pool
            # if it is, set the status to 'canceling', since we can't remove it from the thread pool

            # go through all the threads in queue_threads
            for thread in self.queue_threads:

                if isinstance(thread, dict) \
                        and 'queue_id' in thread \
                        and thread['queue_id'] == queue_id:

                    # set the status to 'canceling' in the queue history
                    # and hope that someone will be watching the status and cancel the item!
                    return self.update_queue_item(queue_id=queue_id, status='canceled')

            # if we reached this point,
            # the item is not currently being processed,
            # so we can remove it from the queue history
            return self.update_queue_item(queue_id=queue_id, status='canceled')

        def cancel_if_canceled(self, queue_id):
            """
            Checks if the a queue item has been canceled and cancels it if it has
            This usually happens if a process sends a 'canceled' status
            so that item is canceled when the current task is finished

            :param queue_id: the queue id of the item to check
            :return True if the item was canceled, False otherwise
            """

            queue_item = self.get_item(queue_id=queue_id)

            # if the status is 'canceling' or 'canceled', cancel the item
            if queue_item \
                    and isinstance(queue_item, dict) \
                    and 'status' in queue_item \
                    and queue_item['status'] in ['canceling', 'canceled']:

                # cancel the item
                self.cancel_item(queue_id=queue_id)

                # the item was canceled
                return True

            # the item was not canceled
            return False

        def set_to_canceled(self, queue_id):
            """
            This function sets the status of a queue item to 'canceling' in the queue history
            This is useful if we want the queue item to finish processing the current task before it is canceled,
            to avoid killing a process in the middle of a task

            Once it finishes it current task, the cancel_if_canceled function should wait before the next task

            :param queue_id: the queue id of the item to set to 'canceled'
            :return: True if the item was set to 'canceled', False otherwise
            """

            # get the item from the queue history
            item = self.get_item(queue_id=queue_id)

            if not item or not isinstance(item, dict):
                logger.warning('Unable to set item to canceled - queue id {} not found in queue history'.format(queue_id))
                return False

            # if the current status is 'done' or 'failed',
            # it doesn't make sense to cancel it
            if item['status'] in ['done', 'failed']:
                logger.debug('Item {} is already done or failed, cannot cancel.'
                             .format(queue_id))

            # if the item is not currently being processed by one of the threads,
            # we can simply set the status to 'canceled'
            if not self.is_item_in_thread(queue_id=queue_id):
                return self.update_queue_item(queue_id=queue_id, status='canceled')

            return self.update_queue_item(queue_id=queue_id, status='canceling', progress='')

        def get_item(self, queue_id: str) -> dict or None:
            """
            This function checks if a queue id is in the queue history and returns the item if it is
            :param queue_id: the queue id to check
            :param strip_id: if True, the queue id will be removed from the item before it is returned
            :return: the item if it is in the queue history, None otherwise
            """

            found_item = None

            if queue_id is None:
                return None

            # the queue history is a list of dictionaries, so we need to iterate through it to find the item
            for item in self.queue_history:

                # if we found the item by its queue id, use it and break the loop
                if 'queue_id' in item and item['queue_id'] == queue_id:
                    found_item = item
                    break

            return found_item

        def get_status(self, queue_id: str) -> str or None:
            """
            This function checks if a queue id is in the queue history and returns the status if it is
            :param queue_id: the queue id to check
            :return: the status if it is in the queue history, None otherwise
            """

            item = self.get_item(queue_id=queue_id)

            if item and isinstance(item, dict) and 'status' in item:
                return item['status']

            return None

        def get_progress(self, queue_id: str) -> str or None:
            """
            This function returns the 'progress' of a queue item,
            0 if it has no progress or None if the item doesn't exist
            """

            item = self.get_item(queue_id=queue_id)

            if not item:
                return None

            if isinstance(item, dict) and 'progress' in item:
                return item['progress']

            else:
                return '0'

        def get_all_queue_items(self, status: str or list or None = None, not_status: str or list or None = None) -> list:
            """
            This function returns all the items in the queue history in an dict,
            where the queue id is the key and the value is the item
            """

            # if the status is a string, convert it to a list
            if isinstance(status, str):
                status = [status]

            # if the not_status is a string, convert it to a list
            if isinstance(not_status, str):
                not_status = [not_status]

            all_queue_items = {}

            for item in self.queue_history:

                # if the status is not None check if the item has the status we are looking for
                # and if not, skip it
                if status is not None \
                        and 'status' in item and item['status'] not in status:
                    continue

                # if the not_status is not None check if the item has the status we don't want
                # and if it does, skip it
                if not_status is not None \
                    and 'status' in item and item['status'] in not_status:
                    continue

                all_queue_items[item['queue_id']] = item

            return all_queue_items

        def set_item_variable(self, queue_id: str, variable_name: str, variable_value, append=False) -> bool:
            """
            This function sets a variable for a queue item, that can be accessed by any function.
            These variables will not be saved to the queue history
            """

            # we are using the self.queue_variables dictionary to store the variables
            # so we need to make sure it exists
            if queue_id not in self.queue_variables:
                self.queue_variables[queue_id] = {}

            # set an empty variable if it doesn't exist
            if variable_name not in self.queue_variables[queue_id]:
                self.queue_variables[queue_id][variable_name] = ''

            # set the variable (this will also overwrite the variable if it already exists)
            self.queue_variables[queue_id][variable_name] = variable_value if not append else \
                self.queue_variables[queue_id][variable_name] + variable_value

            return True

        def get_item_variable(self, queue_id: str, variable_name: str):
            """
            This function gets a variable for a queue item (do not confuse for variables in the queue history/item)
            """

            # if the queue id is not in the queue variables, return None
            if queue_id not in self.queue_variables:
                return None

            # if the variable name is not in the queue variables, return None
            if variable_name not in self.queue_variables[queue_id]:
                return None

            return self.queue_variables[queue_id][variable_name]

        def task_dispatcher(self, tasks: list or str) -> list or bool:
            """
            This function dispatches the tasks to the appropriate function(s)
            This function should be called by the queue manager before a task is added to the queue.

            Each task had a 'task_queue' key that holds a list of functions that need to be executed
            in order to complete the task. The functions are executed in the order they are in the list.

            We will store possible tasks in a dictionary, where the key is the task name and the value is a list of
            functions that need to be executed in order to complete the task.

            The dictionary will be stored in the toolkit_ops_obj and will be called 'queue_tasks'

            :param tasks: the list of tasks to dispatch, or a single task as a string
            :param custom_queue_tasks: a dictionary of tasks in addition to the object self.queue_tasks dictionary
            :return: The list of queue tasks that need to be executed, or False if there was an error

            """

            task_queue = []

            # take each task in the list of tasks
            # and dispatch the appropriate function(s)
            if tasks is None:
                logger.warning('Unable to dispatch tasks - no tasks were specified')
                return False

            # if the tasks is a string, convert it to a list of one item
            if isinstance(tasks, str):
                tasks = [tasks]

            # iterate through the list of tasks
            for task in tasks:

                # if the task is not in the queue tasks, return False
                if task not in self.toolkit_ops_obj.queue_tasks.keys():
                    logger.warning('Unable to dispatch task {} - task not in queue tasks'.format(task))
                    continue

                # get the task queue from the queue tasks dictionary in the toolkit ops object
                task_queue.extend(self.toolkit_ops_obj.queue_tasks[task])

                # if the task queue is empty, return False
                if len(task_queue) == 0:
                    logger.error('Unable to dispatch task {} - task queue is empty'.format(task))
                    continue

            return task_queue

        def execute_item_tasks(self, queue_id, task_queue: list, **kwargs):
            """
            This function executes the functions in the task queue for a given queue item
            """

            # cancel item if someone or something requested it
            if self.cancel_if_canceled(queue_id=queue_id):
                return False

            if task_queue is None:
                logger.error('Unable to execute tasks for item {} - no tasks were specified'.format(queue_id))
                return False

            # keep track of the device we're using
            device = kwargs.get('device', None)

            # get the item details from the queue history
            item = self.get_item(queue_id=queue_id)

            # if the item has dependencies, pass_dependency_data for all of them
            if 'dependencies' in item:
                for dependency_id in item['dependencies']:
                    self.pass_dependency_data(queue_id=queue_id, dependency_id=dependency_id,
                                              override=True, save_to_file=False)

            # take each task in the list of tasks
            for task in task_queue:

                # stop if the item cannot be found anymore - that would be strange
                if item is None:
                    logger.error('Unable to execute task {} for item {} - item not found in queue history'
                                 .format(task, queue_id))
                    return False

                # stop if the item's status is 'canceling'
                # - this means that the user has requested to cancel the item
                if item['status'] == 'canceling':
                    self.update_status(queue_id=queue_id, status='canceled')
                    return False

                # stop also if something set the status to 'failed'
                if item['status'] == 'failed':
                    return False

                try:

                    # update the 'last_task' key in the queue item
                    # so we know which task is being executed but also which task failed if the execution fails
                    self.update_queue_item(queue_id=queue_id, last_task=task)

                    # update the status of the queue item to 'processing'
                    # - this should be updated in more detail from within the task itself (if needed)
                    self.update_status(queue_id=queue_id, status='processing')

                    # get the item one last time to pass it to the task
                    item = self.get_item(queue_id=queue_id)

                    # only merge if the kwargs is a dictionary
                    # (whisper transcribe returns bool or a string right now - we need to fix that)
                    kwargs = {**kwargs, **item} if isinstance(kwargs, dict) else item

                    # execute the task, but merge the kwargs with the item
                    # then re-update the kwargs with the result of the task
                    kwargs = task(**{**kwargs, **item})

                    logger.debug('Finished execution of {} for queue item {}'.format(task.__name__, queue_id))

                except Exception as e:
                    import traceback

                    # add the error to the logger
                    logger.error(traceback.format_exc())

                    logger.error('Unable to execute task {} for queue item {}'.format(task, queue_id))

                    # update the status of the queue item to 'failed'
                    self.update_status(queue_id=queue_id, status='failed')

                    # stop the execution
                    return False

            # remove the thread from the queue threads to free up the device
            self.remove_thread_from_queue_threads(device=device)

            # then ping the queue again
            self.ping_queue()

            # if we get here, the execution was successful
            return True

        def update_status(self, queue_id, status):
            """
            This function updates the status of a queue item
            """

            item = self.get_item(queue_id=queue_id)
            if not item:
                logger.error('Unable to update status for queue item {} - item not found'.format(queue_id))
                return False

            item['status'] = status

            # also reset the progress if the status update is 'done', 'failed', 'canceled' or 'canceling'
            if status in ['done', 'failed', 'canceled', 'canceling']:
                item['progress'] = ''

            self.update_queue_item(**item)

        def ping_queue(self):
            """
            Checks if there are items left in the queue and executes the first one if there are
            """

            # if there are no items in the queue, return False
            if len(self.queue) == 0:

                logger.debug('No items left in the queue. Ping the queue again to restart processing.')

                #logger.info('No items in the queue. Checking again in {}'
                #             .format(str(self.queue_check_interval)
                #                     + ' seconds' if self.queue_check_interval == 1 else 'second'))
                #
                # start a timer to check the queue again according to the queue check interval
                #threadingTimer(self.queue_check_interval, self.ping_queue).start()

                return False

            # get the first item in the queue
            queue_index = 0
            queue_id = self.queue[queue_index]
            reorder_queue = False

            # todo: fix this
            """
            # try to see if we can start this item
            # and loop through the queue until we find one that we can start
            # or until we reach the end of the queue
            # todo: update the item status to failed if we get a None returned from _item_can_start
            while not self._item_can_start(queue_id=queue_id):

                # add +1 to the queue index
                queue_index += 1

                # and try again (if the queue index is out of range, this will return False)
                if queue_index >= len(self.queue):
                    logger.debug('Left queue items not ready to start. Try again later.')
                    return False

                # get the next item in the queue
                queue_id = self.queue[queue_index]

                # mark that we need to reorder the queue
                reorder_queue = True

            # make sure that we re-order the queue
            if reorder_queue:

                # first get the old order
                # (use a copy of the list to avoid changing the original list due to mutability)
                new_queue_order = [queue_id for queue_id in self.queue]

                # then remove the item from the old order (from whatever position it was in)
                new_queue_order.pop(queue_index)

                # and add it back to the beginning of the list
                new_queue_order.insert(0, queue_id)

                self.reorder_queue(new_queue_order=new_queue_order)
            """

            # get the item details from the queue history
            kwargs = self.get_item(queue_id=queue_id)

            # check if the device is available
            if not self.is_device_available(device=kwargs['device']):
                logger.debug('Device busy. Try again later.')
                return False

            # create a thread to execute the tasks for this item
            thread = Thread(target=self.execute_item_tasks, kwargs=kwargs)

            # add the thread to the threads dictionary so that other processes know that the device is busy
            self.add_thread_to_queue_threads(device=kwargs['device'], queue_id=kwargs['queue_id'], thread=thread)

            # start the thread
            thread.start()

            # remove the first item from the queue
            self.queue.pop(0)

            return True

        def _item_can_start(self, queue_id, item_data = None):
            """
            This determines if a certain item can start based on its dependencies
            If any of its dependencies has failed, this will return None
            """

            if item_data is None:
                item_data = self.get_item(queue_id=queue_id)

            # if the item has no dependencies, it can start
            if 'dependencies' not in item_data:
                return True

            # if the item has dependencies, check if they are all completed
            for dependency_id in item_data['dependencies']:

                dependency_item_data = self.get_item(queue_id=dependency_id)

                # return None if the dependency item is not found
                # since it's impossible to determine if the dependency finished or not
                if not dependency_item_data:
                    return None

                # if the status of the dependency is not in the item data,
                if 'status' not in dependency_item_data:
                    return False

                # if the dependency has failed, return None
                if dependency_item_data['status'] == 'failed':
                    return None

                # if the dependency is not completed, return False
                if dependency_item_data['status'] != 'done':
                    return False

            return True

        def add_thread_to_queue_threads(self, device, queue_id, thread):
            """
            This function adds a thread to the queue_threads dict
            (it will replace anything related to that device without checking if the old thread is still running!)
            """

            # if the device is not in the queue_threads dict, add it
            self.queue_threads[device] = {'queue_id': queue_id, 'thread': thread}

            return self.queue_threads

        def remove_thread_from_queue_threads(self, device):
            """
            This function removes a thread from the queue_threads dict
            """

            if device is None:
                logger.warning('Unable to remove thread from queue threads - no device specified')

            # if the device is in the queue_threads dict, remove it
            if device in self.queue_threads:
                self.queue_threads.pop(device)

            return self.queue_threads

        def is_device_available(self, device):
            """
            This function checks if a device is busy processing something by checking the queue_threads dict.
            There's no way, of course, to know if the device is busy with some other process,
            but this helps keep the queue running smoothly internally.
            """

            # if the device is in the queue_threads dict, it's busy
            if device in self.queue_threads:

                # check if the thread is still running
                if self.queue_threads[device]['thread'].is_alive():

                    # if it's still running, it's busy
                    return False

                # if it's not running, it's not busy so remove it from the queue_threads dict
                else:
                    self.remove_thread_from_queue_threads(device)

            return True

        def is_item_in_thread(self, queue_id):
            """
            This function checks if a queue item is in the queue_threads dict
            """

            for device in self.queue_threads:
                if queue_id == self.queue_threads[device]['queue_id']:
                    return True

            return False

        def save_queue_to_file(self):
            """
            This function saves the queue history to the queue file
            """

            # get all the queue items
            queue_items = self.queue_history

            # if we don't have a list of queue items, create an empty one
            if not isinstance(queue_items, list):
                queue_items = []

            # we need to clean up the task_queue list before saving it to file
            # because we're unable to serialize the task_queue items with the thread objects
            # but, no worries, when we load the queue from file,
            # the add_to_queue function will dispatch the tasks again as needed
            save_queue_items = []
            for item in queue_items:

                save_item = {k: v for k, v in item.items() if k not in ('task_queue', 'last_task')}
                save_queue_items.append(save_item)

            # the queue file
            queue_file = self.toolkit_ops_obj.QUEUE_FILE_PATH

            # save the queue items to the queue json file
            try:
                with open(queue_file, 'w') as f:
                    json.dump(save_queue_items, f, indent=4)
                    return True

            except Exception as e:
                logger.error('Could not save queue to file: {}'.format(e))
                return False

        def load_queue_from_file(self):
            """
            Reads the queue from the queue file
            """

            # the empty queue history list
            queue_history = []

            # the queue file
            queue_file = self.toolkit_ops_obj.QUEUE_FILE_PATH

            try:
                if os.path.exists(queue_file):
                    with open(queue_file, 'r') as f:
                        queue_history = json.load(f)

            except Exception as e:
                logger.error('Could not load queue from file: {}'.format(e))

            return queue_history

        def resume_queue_from_file(self):
            """
            This loads the queue file and adds it to the queue and queue history
            """

            queue_history = self.load_queue_from_file()

            # if we have a list
            if isinstance(queue_history, list) and len(queue_history) > 0:

                # first, rebuild the entire queue history from the queue file
                # but only if we're supposed to see the finished items in the queue too
                if not self.toolkit_ops_obj.stAI.get_app_setting('queue_ignore_finished', True):
                    self.queue_history = queue_history

                # take each item in the queue history and add it to the queue
                for idx, item in enumerate(queue_history):

                    # skip if there's no queue_id or either the source_file_path or task_data is missing
                    # it doesn't make sense to put it back in the queue since we can't do anything with it
                    if not item.get('queue_id', None) \
                        or not (item.get('source_file_path', None) or item.get('task_data', None)):

                        # remove the item from the queue history
                        # removing this will make sure we don't add it next time we save the queue file
                        if not self.toolkit_ops_obj.stAI.get_app_setting('queue_ignore_finished', True):
                            self.queue_history.pop(idx)

                        continue

                    # reset any progress
                    item['progress'] = ''

                    # if it has no status, just queue it
                    if 'status' not in item:
                        item['status'] = 'queued'

                        # add to the queue
                        self.add_to_queue(**item)

                        continue

                    # if the status is 'canceling', cancel it
                    if item['status'] == 'canceling':
                        item['status'] = 'canceled'
                        continue

                    # if the status is not ['done', 'failed', 'canceled'] add it to the queue
                    if item['status'] not in ['done', 'failed', 'canceled']:
                        self.add_to_queue(**item)

                # once we finished re-building the queue, we need to ping it
                self.ping_queue()

                # if we processed the queue, we've resumed it
                return True

            # if we reached this point, we don't have a queue to resume
            return False

    def get_torch_available_devices(self) -> list or None:

        # prepare a list of available devices
        available_devices = ['cpu']

        # and add cuda to the available devices, if it is available
        if torch.cuda.is_available():
            available_devices.append('CUDA')

        return available_devices

    # TRANSCRIPTION MANAGEMENT

    def get_all_valid_media_paths_in_dir(self, dir_path, recursive=False):

        # if the source file path is a directory, get all the valid media files in the directory
        if not os.path.isdir(dir_path):
            logger.warning('The source file path is not a directory. Aborting.')
            return False

        # if the source file path is a file, return the file path
        elif os.path.isdir(dir_path):

            # get all the files in the directory
            # either reccursively
            if not recursive:
                all_files = os.listdir(dir_path)
            else:
                all_files = []
                for root, dirs, files in os.walk(dir_path):
                    for file in files:
                        all_files.append(os.path.join(root, file))

                        if len(all_files) > self.stAI.get_app_setting('ingest_files_limit', default_if_none=30):
                            logger.error('Too many files in the directory. Aborting.')

            # filter out the valid media files
            valid_media_files \
                = [os.path.join(dir_path, file) for file in all_files if self.is_valid_media_file(file)]

            return valid_media_files

        # if the source file path is neither a file nor a directory, return False
        return False

    def is_valid_media_file(self, source_file_path):
        """
        This checks if the source file path is a valid media file by checking the extension
        """

        if not source_file_path:
            return False

        # get the file extension
        file_extension = os.path.splitext(source_file_path)[1].lower()

        # check if the file extension is valid
        if file_extension in ['.mov', '.mp4', '.mp3', '.wav', '.aif', '.aiff']:
            return True

        # if the file extension is not valid, return False
        return False

    def add_media_to_queue(self, source_file_paths: str or list=None, queue_id: str=None,
                           transcription_settings = None, video_indexing_settings = None,
                           **kwargs):
        """
        This adds one media item to the ingest queue
        (the task however might split into multiple queue items, for eg. transcription and video indexing)
        """

        # if no source file path was passed, return False
        if not source_file_paths:
            logger.warning('No source file path was passed for ingest. Aborting.')

            # update the queue item status
            if queue_id is not None:
                self.processing_queue.update_queue_item(queue_id=queue_id, status='failed')

            return False

        # if the source file path is a string, convert it to a list
        if isinstance(source_file_paths, str):
            source_file_paths = [source_file_paths]

        # this is the path variable we'll use to send the items to the queue
        valid_source_file_paths = []

        # loop through the source file paths
        for source_file_path in source_file_paths:

            # check if the source file path exists
            if not os.path.exists(source_file_path):
                # if it doesn't exist, log a warning and go to the next path
                logger.warning('Source file path does not exist: ' + source_file_path)
                continue

            # if it's a folder, add all the valid media files in the folder to the queue
            if os.path.isdir(source_file_path):

                # get all the valid media files in the folder
                valid_source_file_paths += self.get_all_valid_media_paths_in_dir(source_file_path, recursive=True)

            # if it's a file, check if it's a valid media file
            if os.path.isfile(source_file_path):

                # if it's a valid media file, add it to the queue
                if self.is_valid_media_file(source_file_path):
                    valid_source_file_paths.append(source_file_path)

                # if it's not a valid media file, log a warning and go to the next path
                else:
                    logger.debug('Skipping file path - not a valid media file: ' + source_file_path)
                    continue

        # if there are no valid source file paths, return False
        if not valid_source_file_paths:
            return False

        queued = []

        # if there are valid source file paths, add each of them to the queue
        for source_file_path in valid_source_file_paths:

            # create a transcription job only if we have transcription settings
            if transcription_settings is not None and isinstance(transcription_settings, dict):

                transcription_settings['name'] = os.path.basename(source_file_path)

                # make sure to generate a new queue id for each type of task (transcription, video indexing, etc.)
                # if a queue_id exists use it for the first item
                if queue_id is not None:

                    current_queue_id = queue_id

                    # then reset it, so we make sure we generate a new queue_id if there are multiple files
                    queue_id = None

                else:
                    current_queue_id = self.processing_queue.generate_queue_id(name=transcription_settings['name'])

                # get the ingest settings
                #ingest_settings = self.get_ingest_settings(source_file_path, ingest_task=ingest_task, **kwargs)

                # send the item to ingest queue
                #self.processing_queue.add_queue_item(source_file_path, **ingest_settings)

                # don't forget the queue_id
                transcription_settings['queue_id'] = current_queue_id

                # remove the audio_file_path from the transcription settings
                transcription_settings['audio_file_path'] = source_file_path

                # send the item to transcription queue
                self.add_transcription_to_queue(**transcription_settings)

                # add this to the queued list
                queued.append(current_queue_id)

                # throttle a bit to avoid collisions etc.
                time.sleep(0.05)

        # confirm that stuff was added to the queue
        if len(queued) > 0:
            return queued

        # otherwise return false
        return False

    def add_transcription_to_queue(self, transcription_task=None, audio_file_path: str=None, queue_id: str=None,
                                   **kwargs):
        """
        This adds a transcription item to the transcription queue
        (it also splits it into two queue items, if it's a transcribe+translate transcription_task)

        Here, we are processing the options that have something to do with the queue processing
        The whisper options are processed by the whisper_transcribe function,
        since we might still need them in the queue history later
        """

        # if no audio file path was passed, return False
        if not audio_file_path:
            logger.warning('No audio file path was passed for transcription. Aborting.')

            # update the queue item status
            if queue_id is not None:
                self.processing_queue.update_queue_item(queue_id=queue_id, status='failed')

            return False

        # as name, use either the passed name or the file name if nothing was passed
        name = kwargs.get('name', os.path.basename(audio_file_path))

        # get the right device via torch_device_type_select
        kwargs['device'] = self.torch_device_type_select(kwargs.get('device', None))

        # select the 'transcribe' if neither transcribe or translate was passed
        if transcription_task is None \
                or transcription_task not in ['transcribe', 'translate', 'transcribe+translate']:
            transcription_task = 'transcribe'

        # only allow 'transcribe' or 'translate'
        if transcription_task in ['transcribe', 'translate']:

            # just do that task
            transcription_tasks = [transcription_task]

        # if user asked for 'transcribe+translate'
        # split this into two items to add them separately to the queuee
        elif transcription_task == 'transcribe+translate':
            # add both tasks
            transcription_tasks = ['transcribe', 'translate']

        # we will never get to this, but let's have it
        else:
            return False

        # add all the above tasks to the queue
        for i, c_task in enumerate(transcription_tasks):

            # generate a unique id if one hasn't been passed
            if queue_id is None:
                next_queue_id = self.processing_queue.generate_queue_id(name=name)

            else:
                # if a unique id was passed, only use it for the first transcription_task
                next_queue_id = queue_id

                # then reset it
                queue_id = None

            c_name = name
            # add the task name to the name if there are multiple tasks
            if i > 0:
                c_name += ' - ' + str(c_task)

            # pass the queue tasks via kwargs
            # we're not all the transcription tasks into a single item but going through this loop,
            # because we want to be able to pass different settings for each task,
            # plus we want to see the progress on each queue item separately
            # therefore splitting them into separate queue items makes more sense
            kwargs['tasks'] = [c_task]

            # pass the name and queue id
            kwargs['name'] = c_name
            kwargs['queue_id'] = next_queue_id

            # add the audio file path as source file path
            kwargs['source_file_path'] = audio_file_path

            # send each item to the universal queue
            self.processing_queue.add_to_queue(**kwargs)

            # if we need to group questions, add the group questions tasks too
            if kwargs.get('transcription_group_questions', False):

                kwargs['tasks'] = ['group_questions']
                kwargs['name'] = '{} {}'.format(kwargs['name'], '(Group Questions)')
                kwargs['queue_id'] = None

                group_questions_queue_id = self.processing_queue.add_to_queue(**kwargs)

                # add the main transcription queue item as a dependency to the group questions queue item
                # this way, when the transcription is done, the group questions item will start
                # and retrieve all the all the data from the transcription queue item
                self.processing_queue.add_dependency(queue_id=group_questions_queue_id, dependency_id=next_queue_id)

    def transcription_progress(self, queue_id=None, progress=None):
        '''
        Updates the progress of a transcription item in the transcription log
        :param queue_id:
        :param progress:
        :return:
        '''

        # if a progress was passed, update the progress
        if queue_id and progress:
            self.processing_queue.update_queue_item(queue_id=queue_id, save_to_file=False, progress=progress)

        # if no progress was passed, just return the current progress
        elif queue_id:
            return self.processing_queue.get_progress(queue_id=queue_id)

    # TRANSCRIPTION METHODS

    def whisper_options(self, **parameters):
        """
        This function looks at all the passed parameters
        and returns the ones that are relevant to mots_whisper
        """

        allowed_parameters = [
            ('audio_file_path', str),
            ('language', str),
            ('model', str),
            ('device', str),
            ('task', str),
            ('initial_prompt', str),

            ('beam_size', int),
            ('best_of', int),
            ('temperature', float),
            ('compression_ratio_threshold', float),
            ('logprob_threshold', float),
            ('no_speech_threshold', float),
            ('word_timestamps', bool),
            ('prepend_punctuations', bool),
            ('append_punctuations', bool),
            ('prompt', str),

            # mots_whisper specific parameters
            ('queue_id', str)
        ]

        filtered_parameters = {}

        # filter out the parameters that are not allowed
        # by checking if they are in the allowed_parameters list
        for param, param_type in allowed_parameters:

            # if the parameter is in the list and is of the correct type
            if param in parameters and isinstance(parameters[param], param_type):

                # add it to the filtered parameters
                filtered_parameters[param] = parameters[param]

        # return only the filtered parameters
        return filtered_parameters

    def time_intervals_to_transcript_segments(self, time_intervals: list, segments: list) -> list or None:
        '''
        This function converts a list of time intervals to a list of transcript segments

        :param time_intervals: a list of time intervals
        :param segments: a dict of transcript segments
        :return: a list of transcript segments
        '''

        # if the time intervals or segments are empty or not a list/dict, return None
        if time_intervals is None or type(time_intervals) is not list \
                or segments is None or type(segments) is not list:
            return None

        # if the time intervals are empty, return None
        if len(time_intervals) == 0:
            return []

        # take all time intervals and check if they overlap with any of the segments
        # if they do, add the segment to the list of segments to return
        segments_to_return = []

        # first sort the time intervals by start time
        time_intervals = sorted(time_intervals, key=lambda x: x['start'])

        # then sort the segments by start time
        segments = sorted(segments, key=lambda x: x['start'])

        # now take all the time intervals and check if they overlap with any of the segments
        for current_time_interval in time_intervals:

            # test this time interval against all segments
            for current_segment in segments:

                # if the current time interval overlaps with the current segment, add it to the list of segments
                if current_segment['start'] >= current_time_interval['start'] \
                        and current_segment['end'] <= current_time_interval['end']:

                    segments_to_return.append(current_segment)

                # otherwise, if the current segment is after the current time interval, break
                # this only works if the segments and time intervals have been sorted
                elif current_segment['start'] > current_time_interval['end']:
                    break

        return segments_to_return

    def transcript_segments_to_time_intervals(self, segments: list) -> list or None:
        '''
        This function takes a list of transcript segments, groups them together if they don't have
        any gaps between them.
        :param segments:
        :return: the list of time intervals or None if something went wrong
        '''

        # if the segments are not empty or not a dict, return None
        if segments is None or type(segments) is not list or len(segments) == 0:
            logger.debug('Could not convert transcript segments to time intervals '
                         'because the segments are empty or not a list')
            return None

        # these are the group time intervals that we'll return eventually
        # this group will consist of multiple time intervals taken from transcript segments that
        # are next to each other (end_time of previous segment matches the start_time of current segment)
        time_intervals = [{}]

        time_interval_num = 0

        # remove duplicates from segments
        # this is important because if there are duplicates, the time intervals might repeat
        segments_unique = []
        [segments_unique.append(x) for x in segments if x not in segments_unique]

        # place the unique segments back into the original list
        segments = segments_unique

        # sort the segments by start time
        segments = sorted(segments, key=lambda x: x['start'])

        # loop through the segments
        for current_segment in segments:

            # print('current segment {}-{}: {}'
            #       .format(current_segment['start'], current_segment['end'], current_segment['text']))

            # if the current time interval doesn't have a start time, add it
            # (i.e. this segment is the first in this time interval)
            if 'start' not in time_intervals[time_interval_num]:
                time_intervals[time_interval_num]['start'] = current_segment['start']

            # if the end time of the current time_interval matches the start time of the current segment,
            # it means that there's no gap between the current time_interval and the current segment,
            # so add the current segment to the current time interval, by simply updating the end time
            # this extends the time interval to include the current segment too
            if 'end' not in time_intervals[time_interval_num] or \
                    time_intervals[time_interval_num]['end'] == current_segment['start']:

                time_intervals[time_interval_num]['end'] = current_segment['end']

            # otherwise, it means that the current segment is not next to the current time interval,
            # so start a new time interval containing the current segment
            else:
                time_interval_num += 1
                time_intervals.append({
                    'start': current_segment['start'],
                    'end': current_segment['end']
                })

        return time_intervals

    def get_whisper_available_languages(self) -> list or None:

        available_languages = whisper_tokenizer.LANGUAGES.values()

        if not available_languages or available_languages is None:
            available_languages = []

        return sorted(available_languages)

    def torch_device_type_select(self, device = None):
        '''
        A standardized way of selecting the right Torch device type
        :param device:
        :return:
        '''

        allowed_devices = ['cuda', 'CUDA', 'gpu', 'GPU', 'cpu', 'CPU']

        # change the torch device if it was passed as a parameter
        if device is not None and device in allowed_devices:
            self.torch_device = device

        # if the torch device is set to cuda
        if self.torch_device in ['cuda', 'CUDA', 'gpu', 'GPU']:

            # use CUDA only if available
            if torch.cuda.is_available():
                self.torch_device = device = torch.device('cuda')

            # or let the user know that cuda is not available and switch to cpu
            else:
                logger.warning('CUDA not available. Switching to cpu.')
                self.torch_device = device = torch.device('cpu')

        # if the torch device is set to cpu
        elif self.torch_device in ['cpu', 'CPU']:
            self.torch_device = device = torch.device('cpu')

        # any other setting, defaults to automatic selection
        else:
            # use CUDA if available, or CPU otherwise
            self.torch_device = device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        logger.debug('Using {} for Torch.'.format(device))

        return self.torch_device

    def split_audio_by_intervals(self, audio_array, time_intervals=None, sr=16_000):
        """
        Splits the audio_array according to the time_intervals
        and returns a audio_segments list with multiple audio_arrays
        together with the time_intervals passed to the function
        """

        # reset the audio segments list
        audio_segments = []

        # if there are time segments
        if time_intervals is not None and time_intervals \
                and type(time_intervals) == list and len(time_intervals) > 0:

            # sort the audio segments by start time
            time_intervals = sorted(time_intervals, key=lambda x: x[0])

            # combine overlapping segments
            time_intervals = self.combine_intervals(time_intervals, 0)

            # take each time segment
            for time_interval in time_intervals:
                # calculate duration based on start and end times!!

                # and add it to an audio segments list
                # the format is [start_time, end_time, audio_array]
                audio_segment = [time_interval[0],
                                 time_interval[1],
                                 audio_array[int(time_interval[0] * sr): int(time_interval[1] * sr)]
                                 ]

                audio_segments.append(audio_segment)
            return audio_segments, time_intervals

        # if time_intervals is empty, define it as a single segment,
        # from the beginning to the end (i.e. we're transcribing the full audio)
        time_intervals = [[0, len(audio_array) / sr]]
        audio_segments = [[0, len(audio_array / sr), audio_array]]
        return audio_segments, time_intervals

    def get_speech_intervals(self, audio_segment, **kwargs):
        """
        Returns the an array of start and end times of the segments of speech in the audio_segment

        :param audio_segment: a numpy array with the audio segment
        :return: a list of start and end times of the segments of speech in the audio_segment
        """

        sample_rate = kwargs.get('sample_rate', 16_000)

        # Removes silences from the audio file.
        # This results in better transcription quality, without hallucinations.
        vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False,
                                          onnx=True, trust_repo=True, verbose=False)
        (get_speech_timestamps, _, read_audio, _, collect_chunks) = utils

        # convert the audio_segment to a torch tensor
        # if the audio segment is a list containing the start time, end time and the audio array,
        #  we only take the audio array
        if type(audio_segment) == list and len(audio_segment) == 3:
            audio_segment_torch = torch.from_numpy(audio_segment[2])
        else:
            audio_segment_torch = torch.from_numpy(audio_segment)

        speech_timestamps = get_speech_timestamps(audio_segment_torch, vad_model,
                                                  sampling_rate=sample_rate,
                                                  window_size_samples=512,
                                                  speech_pad_ms=kwargs.get('silence_threshold', 200),
                                                  threshold=kwargs.get('silence_threshold', 0.5),
                                                  )

        # convert speech_timestamps to seconds using the sample rate
        # the speech_timestamps format is [{'start': start_time, 'end': end_time], ...]
        speech_timestamps = [[speech_timestamp['start'] / sample_rate, speech_timestamp['end'] / sample_rate]
                             for speech_timestamp in speech_timestamps]

        # combine all the speech_timestamps that are less than X seconds apart
        # this is to avoid having too many small segments
        speech_timestamps = self.combine_intervals(speech_timestamps,
                                                   combine_min_time=kwargs.get('combine_speech_min_time', 3))

        # if the first speech_timestamp starts after 0 but before 1 second
        # we set the start time to 0
        if type(speech_timestamps) is list and \
                speech_timestamps[0][0] > 0 and speech_timestamps[0][0] < 1:
            speech_timestamps[0][0] = 0

        return speech_timestamps

    def combine_intervals(self, intervals, combine_min_time):
        """
        Combines intervals that are less than combine_min_time apart
        :param intervals: a list of timestamps
        :param combine_min_time: the minimum time (seconds) between two timestamps to be combined
        :return:
        """

        # sort the timestamps by start time
        intervals = sorted(intervals, key=lambda x: x[0])

        # create a new list to store the combined timestamps
        new_intervals = []

        # take the first timestamp
        current_timestamp = intervals[0]

        # for each timestamp
        for interval in intervals[1:]:
            # if the current timestamp is less than min_time apart from the next timestamp
            if interval[0] - current_timestamp[1] <= combine_min_time:
                # combine the two timestamps
                current_timestamp[1] = interval[1]

            # if the current timestamp is more than min_time apart from the next timestamp
            else:
                # add the current timestamp to the new_timestamps list
                new_intervals.append(current_timestamp)

                # and set the current timestamp to the next timestamp
                current_timestamp = interval

        # add the last timestamp to the new_timestamps list
        new_intervals.append(current_timestamp)

        return new_intervals

    def combine_overlapping_intervals(self, intervals, additional_intervals=None):
        '''
        Given a list of timestamps in the format [[start_time, end_time], ...]
        return a list of timestamps with overlapping timestamps combined
        :param intervals:
        :param additional_intervals:
        :return:
        '''

        # if there are no intervals and no additional intervals, return None
        if (intervals is None or type(intervals) is bool) \
                and additional_intervals is None or type(additional_intervals) is bool:
            return None

        # if there are no intervals but there are additional intervals,
        # return the additional intervals
        if (intervals is None or type(intervals) is bool) \
                and additional_intervals is not None and type(additional_intervals) is not bool:
            return additional_intervals

        # sort the timestamps by start time
        if intervals is not None and type(intervals) is not bool:
            intervals = sorted(intervals, key=lambda x: x[0])

        # if there are additional intervals,
        # get the intersecting intervals
        if additional_intervals is not None and type(additional_intervals) is not bool:

            # sort the additional timestamps by start time
            additional_intervals = sorted(additional_intervals, key=lambda x: x[0])

            intersecting_intervals = []

            # get the intersecting intervals
            for interval in intervals:

                for additional_interval in additional_intervals:

                    if additional_interval[0] <= interval[1] and additional_interval[1] >= interval[0]:
                        intersecting_intervals.append(
                            [max(interval[0], additional_interval[0]), min(interval[1], additional_interval[1])])

            # redeclare the intervals as the intersecting intervals
            intervals = intersecting_intervals

        return intervals

    def pre_process_audio_segment(self, audio_segment, **kwargs):
        """
        Pre processes the audio segment before passing it to the whisper transcribe function
        :param audio_segment:
        :param kwargs:
        :return:
        """

        return audio_segment

    def split_segment_by_word_limits(self, segment, segment_word_limit: int = None,
                                     segment_character_limit: int = None):
        """
        Splits the segment into multiple segments by the given word limit or character limit.
        The word limit will be overridden by the character limit if both are specified.
        """

        if not segment_word_limit and not segment_character_limit:
            return segment

        if not isinstance(segment, dict):
            logger.warning('The segment is either empty or not a dictionary.'
                           'Cannot split segment by word or character limit.')
            return segment

        # if the segment contains no words, we can't perform the split
        # because we don't know the start and end times of the words
        if 'words' not in segment or not segment['words']:
            logger.warning('Segment does not contain words-level timings. '
                           'Cannot split segment by word or character limit.')
            return segment

        # we need to be aware that the segment might be split multiple times
        # so we need to keep track of the current segment index
        current_segment_index = 0

        # we need to keep track of the current segment text - this is what we use to check over and over again
        current_segment_text = segment['text']

        # we need to keep track of the remaining words in the segment
        current_segment_words = segment['words']

        # we need to keep track of the number of words in the segment
        # this might be used to determine the number of words to keep in the first part
        # and the number of words to keep in the second part
        current_segment_words_count = len(current_segment_words)

        # here we keep track of the segments that result after splitting
        resulting_segments = []

        # while the current segment text is longer than the character limit
        # or the current segment has more words than the word limit
        while (segment_character_limit and len(current_segment_text) > segment_character_limit) \
                or (segment_word_limit and current_segment_words_count > segment_word_limit):

            # CHARACTER LIMIT SPLIT
            if segment_character_limit:
                # split the current segment text into two parts
                # the first part is the first segment_character_limit characters
                # the second part is the rest of the characters
                # but make sure that you're not splitting a word
                # so look for the last space before the segment_character_limit
                # and split 1 character before that to include the space and preserve Whisper's formatting
                last_space_index = current_segment_text.rfind(' ', 0, segment_character_limit)

                # if there is no space before the segment_character_limit, try to find the space after the segment_character_limit
                if last_space_index == -1:
                    last_space_index = current_segment_text.find(' ', segment_character_limit)

                # if there is no space before or after the segment_character_limit, don't split the segment
                if last_space_index == -1:
                    break

            # OR WORD LIMIT SPLIT
            else:

                # we preserve the number of words according to the word limit by finding the relevant space index

                # does the segment start with a space?
                # if so, we need to skip the first occurence of the space
                if current_segment_text[0] == ' ':
                    skip = 1

                def find_nth(haystack, needle, n, skip=True):

                    if skip:
                        start = haystack.find(needle, 1)
                    else:
                        start = haystack.find(needle)

                    while start >= 0 and n > 1:
                        start = haystack.find(needle, start + 1)
                        n -= 1
                    return start

                last_space_index = find_nth(current_segment_text, ' ', segment_word_limit)

                # if there is no space after the word limit, don't split the segment
                if last_space_index == -1:
                    break

            # split the segment into two parts
            segment_first_part = current_segment_text[:last_space_index]
            segment_second_part = current_segment_text[last_space_index + 1:]

            # the words list is a list of dictionaries,
            # each dictionary containing the word and its start time, end time and probability
            # considering that the word list is ordered and the words have to have the same order in the resulting segments
            # and also that the words have the exact same length as the text in the segment
            # we can use the length of the first part to determine which words to keep in the first part
            # and which words to keep in the second part

            # keep the character length of the words in the first part
            first_part_words_character_length = 0
            first_part_words = []
            first_part_start = None
            first_part_end = None
            words_to_remove = []
            for word in current_segment_words:

                # if the character length of the words in the first part is longer than the first part
                # then we've reached the end of the first part
                # when calculating the length of the first part,
                # we need to add a space at the beginning to preserve Whisper's formatting
                if first_part_words_character_length + len(word['word']) > len(' ' + segment_first_part):
                    break

                # if the first part start is None, then set it to the current word start time
                if first_part_start is None:
                    first_part_start = word['start']

                first_part_words_character_length += len(word['word'])

                # keep the words in the first part
                first_part_words.append(word)

                # keep updating the first part end time
                first_part_end = word['end']

                # keep track of the words to remove
                # - we can't remove them directly here because we're iterating over the same words list
                words_to_remove.append(word)

            # remove the words that we've kept in the first part
            for word in words_to_remove:
                current_segment_words.remove(word)

            # create a new segment
            if segment_first_part != '':

                # add a space at the beginning to preserve Whisper's formatting
                if segment_first_part[0] != ' ':
                    segment_first_part = ' ' + segment_first_part

                new_segment = {
                    'text': segment_first_part,
                    'start': first_part_start if first_part_start is not None else segment['start'],
                    'end': first_part_end if first_part_end is not None else segment['end'],
                    'words': first_part_words,
                }

                # add the new segment to the resulting segments
                resulting_segments.append(new_segment)

            # set the current segment text to the second part
            current_segment_text = segment_second_part

            # increment the current segment index
            current_segment_index += 1

        # is there anything left in the current segment text?
        if current_segment_text:
            # create a new segment

            # add a space at the beginning to preserve Whisper's formatting
            # the space was most likely removed when splitting the segment
            if current_segment_text[0] != ' ':
                current_segment_text = ' ' + current_segment_text

            new_segment = {
                'text': current_segment_text,
                'start': current_segment_words[0]['start'] if current_segment_words else segment['start'],
                'end': current_segment_words[-1]['end'] if current_segment_words else segment['end'],
                'words': current_segment_words,
            }

            # add the new segment to the resulting segments
            resulting_segments.append(new_segment)

        # return the resulting segments
        return resulting_segments

    def split_segment_on_punctuation_marks(self, segment, punctuation_marks=['.', '!', '?', '…']):
        '''
        Splits a segment on punctuation marks and returns a list of segments, including their start and end times.
        '''

        # if the segment contains no words, we can't perform the split
        # because we don't know the start and end times of the words
        if 'words' not in segment or not segment['words']:
            logger.warning('The segment contains no word-level timings, so we can\'t split it on punctuation marks.')
            return segment

        # the resulting segments
        resulting_segments = []

        # the current segment text
        current_segment_text = segment['text']

        # the current segment words
        current_segment_words = segment['words']

        # convert the punctuation marks to a list if it's a string
        if isinstance(punctuation_marks, str):
            punctuation_marks = list(punctuation_marks)

        # the current segment index
        current_segment_index = 0

        # first, replace all instances of ... with a single …
        current_segment_text = current_segment_text.replace('...', '…')

        # while there are punctuation marks in the current segment text
        while any(punctuation_mark in current_segment_text for punctuation_mark in punctuation_marks):

            # find the first punctuation mark in the current segment text
            first_punctuation_mark_index = min(current_segment_text.find(punctuation_mark)
                                               for punctuation_mark in punctuation_marks if
                                               punctuation_mark in current_segment_text)

            # is the next character a punctuation mark?
            while first_punctuation_mark_index + 1 < len(current_segment_text) and \
                    current_segment_text[first_punctuation_mark_index + 1] in punctuation_marks:
                first_punctuation_mark_index += 1

            # split the segment into two parts, but keep the punctuation mark in the first part
            segment_first_part = current_segment_text[:first_punctuation_mark_index + 1]

            # the words list is a list of dictionaries,
            # each dictionary containing the word and its start time, end time and probability
            # considering that the word list is ordered
            # and the words have are in the same order in the resulting segments,
            # but also that the words have the exact same length as the text in the segment
            # we can use the length of the first part to determine which words to keep in the first part
            # and which words to keep in the second part

            # keep track of the character length of the words in the first part
            first_part_words_character_length = 0
            first_part_words = []

            first_part_start = None
            first_part_end = None
            words_to_remove = []

            # keep track of the start and end times of the first part
            for word in current_segment_words:

                # if the character length of the words in the first part is longer than the first part
                # then we've reached the end of the first part
                # when calculating the length of the first part,
                # we need to add a space at the beginning to preserve Whisper's formatting
                if first_part_words_character_length + len(word['word']) > len(' ' + segment_first_part):
                    break

                # if the first part start is None, it means that we just started working on the first part
                # so set it to the current word start time
                if first_part_start is None:
                    first_part_start = word['start']

                # add the word length, this should also include the space at the beginning,
                # considering that each word contains a space at the beginning when it comes from Whisper
                first_part_words_character_length += len(word['word'])

                # keep the words in the first part
                first_part_words.append(word)

                # keep updating the first part end time
                first_part_end = word['end']

                # keep track of the words to remove
                # - we can't remove them here directly because we're iterating over the same list
                words_to_remove.append(word)

            # remove the words from the current segment words
            for word in words_to_remove:
                current_segment_words.remove(word)

            # create a new segment
            if segment_first_part != '':

                # add a space at the beginning to preserve Whisper's formatting
                if segment_first_part[0] != ' ':
                    segment_first_part = ' ' + segment_first_part

                new_segment = {
                    'text': segment_first_part,
                    'start': first_part_start if first_part_start is not None else segment['start'],
                    'end': first_part_end if first_part_end is not None else segment['end'],
                    'words': first_part_words,
                }

                # add the new segment to the resulting segments
                resulting_segments.append(new_segment)

            # set the current segment text to the second part
            current_segment_text = current_segment_text[first_punctuation_mark_index + 1:]

            # increment the current segment index
            current_segment_index += 1

        # is there anything left in the current segment text?
        if current_segment_text:
            # create a new segment to hold the remaining text

            # add a space at the beginning to preserve Whisper's formatting
            if current_segment_text[0] != ' ':
                current_segment_text = ' ' + current_segment_text

            new_segment = {
                'text': current_segment_text,
                'start': current_segment_words[0]['start'] if current_segment_words else segment['start'],
                'end': current_segment_words[-1]['end'] if current_segment_words else segment['end'],
                'words': current_segment_words,
            }

            # add the segment with the remaining text to the resulting segments
            resulting_segments.append(new_segment)

        # return the resulting segments
        return resulting_segments

    def split_segments(self, segments: list, **kwargs):
        '''
        This splits transcription segments into smaller segments based on:
        - punctuation marks (if the split_on_punctuation_marks option is set)
        - the maximum number of characters per segment (if the max_characters_per_segment option is set)
        - the maximum number of words per segment (if the max_words_per_segment option is set)
        :param segments: the segments to split
        '''

        # if there are no 'words' in the first segment it means that Whisper hasn't returned any word timings
        # in this case, we can't split the segments
        if len(segments) == 0 or 'words' not in segments[0]:
            logger.debug('No word-level timings available, so we can\'t split the segments.')
            return segments

        # get the punctuation mark splitting option
        split_on_punctuation_marks = kwargs.get('split_on_punctuation_marks', False)

        # split the result on punctuation marks if the option is set
        if split_on_punctuation_marks:

            logger.debug('Splitting segments on pre-defined punctuation marks...')

            # get the custom punctuation marks from the config
            custom_punctuation_marks = self.stAI.get_app_setting('transcription_custom_punctuation_marks',
                                                                 default_if_none=['.', '!', '?', '…'])

            # the resulting segments
            new_segments = []

            # take each segment
            for segment in segments:
                # split the segment into multiple segments
                resulting_segment = self.split_segment_on_punctuation_marks(segment,
                                                                            punctuation_marks=custom_punctuation_marks)

                # add the resulting segments to the new segments list
                new_segments.extend(resulting_segment)

            # replace the segments in the result with the new segments
            segments = new_segments

        # get the segment word limit
        segment_word_limit = kwargs.get('max_words_per_segment', None)

        # get the segment character limit
        segment_character_limit = kwargs.get('max_chars_per_segment', None)

        # validate that the segment word limit is an integer
        if segment_word_limit is not None:
            try:
                segment_word_limit = int(segment_word_limit)
            except ValueError:
                segment_word_limit = None

        # validate that the segment character limit is an integer
        if segment_character_limit is not None:
            try:
                segment_character_limit = int(segment_character_limit)
            except ValueError:
                segment_character_limit = None

        # if there is a segment word limit or character limit
        # and the result is longer than the any of the limits
        # (the character limit takes precedence)
        # then split the result into multiple segments
        if segment_character_limit is not None or segment_word_limit is not None:

            logger.debug('Splitting segments on word/character limits...')

            # the resulting segments
            new_segments = []
            # take each segment in the result
            for segment in segments:
                # split the segment into multiple segments
                resulting_segment = self.split_segment_by_word_limits(segment, segment_word_limit,
                                                                      segment_character_limit)

                # add the resulting segments to the new segments list
                new_segments.extend(resulting_segment)

            # replace the segments in the result with the new segments
            segments = new_segments

        return segments

    def classify_segments(self, segments: list, labels: list,
                          min_confidence: int or list = 0.55, multi_label_pass: list = None, **kwargs):
        '''
        Classifies segments into different types using the transformers zero-shot-classification pipeline
        :param segments: the segments to classify
        :param labels: the labels to use for classification, if a list of lists is provided,
                        a multi-label classification is performed, taking into consideration each group of labels
        :param min_confidence: the minimum confidence for a classification to be considered valid,
                                if a list is provided, then the confidence is calculated for multi_label_pass label group
        :param multi_label_pass: a list of groups of labels that need to be passed together,
                                so that the segment stays in the result
        '''

        if segments is None or len(segments) == 0:
            logger.debug('No segments to classify.')
            return None

        # make sure that if a list of lists of labels is provided,
        # and also a list of minimum confidence values is provided,
        # then the number of confidence values matches the number of label groups
        # also don't allow a single label group and a list of confidence values
        if (isinstance(labels[0], list) and isinstance(min_confidence, list) and len(labels) != len(min_confidence)
            or (isinstance(labels[0], str) and isinstance(min_confidence, list))
        ):
            logger.error("The number of label groups doesn't match the number of minimum confidence values.")
            raise Exception("The number of label groups doesn't match the number of minimum confidence values.")

        if isinstance(labels[0], list) and len(labels) < len(multi_label_pass):
            logger.warn("The number of label groups is less than the number of multi-label-pass groups. "
                        "Disabling multi-label-pass.")
            multi_label_pass = None

        # using tensorflow but with another model,
        # because facebook/bart-large-mnli is not available in tensorflow
        # from transformers import TFAutoModelForSequenceClassification, AutoTokenizer
        # tokenizer = AutoTokenizer.from_pretrained('roberta-large-mnli')
        # model = TFAutoModelForSequenceClassification.from_pretrained('roberta-large-mnli')
        # classifier = pipeline('zero-shot-classification', model=model, tokenizer=tokenizer)

        # start classification process
        model_name = self.stAI.get_app_setting('text_classifier_model', default_if_none='facebook/bart-large-mnli')

        logger.debug('Loading text classifier model: {}'.format(model_name))
        # get the zero-shot-classification pipeline
        classifier = pipeline('zero-shot-classification',
                              model=model_name,
                              )

        logger.debug('Classifying segments using the following labels: {}'.format(labels))

        # go through each segment and classify it
        classified_segments = {}

        # use tqdm to show a progress bar while classifying segments
        with tqdm.tqdm(segments, desc='Classifying segments', total=len(segments)) as pbar:

            for i, segment in enumerate(segments):



                # skip segments that don't have any text or words
                if 'text' not in segment and 'words' not in segment:
                    logger.debug('Skipping segment classification because it doesn\'t have any text or words: {}'
                                 .format(segment))
                    continue

                # if the text is empty, try to get the text from the words
                if not segment['text'] or segment['text'].strip() == '':
                    segment['text'] = ' '.join([word['word'] for word in segment['words']])

                # if the text is still empty, skip the segment
                if not segment['text'] or segment['text'].strip() == '':
                    logger.debug('Skipping segment classification because it doesn\'t have any text: {}'
                                    .format(segment))
                    continue

                # classify the segment

                # if labels is a list of strings, do a normal classification
                if isinstance(labels, list) and isinstance(labels[0], str):
                    classification = classifier(segment['text'], labels)

                    # if the classification confidence is too low, skip the segment
                    if min_confidence and classification['scores'][0] < min_confidence:
                        logger.debug('Skipping segment classification because the confidence is too low {}: {}'
                                     .format(classification['scores'][0], segment))
                        continue

                    # add it to the corresponding list, but first make sure the label exists
                    if classification['labels'][0] not in classified_segments:
                        classified_segments[classification['labels'][0]] = []

                    classified_segments[classification['labels'][0]].append(segment)

                    # clear classification to free up memory
                    del classification

                # if labels is a list of lists, do a multi-label classification
                elif isinstance(labels, list) and isinstance(labels[0], list):

                    # reset the current_segment_passed_classification to True,
                    # until we find a label that doesn't pass
                    current_segment_passed_classification = True

                    # take each label groups, one by one and use them to classify the segment
                    for sub_labels in labels:

                        # if the segment didn't pass the classification for the previous label check, skip it
                        if not current_segment_passed_classification:
                            continue

                        # classify the segment using this label
                        classification = classifier(segment['text'], sub_labels)

                        # if the min_confidence is a list, use the index of the current label group
                        # to get the corresponding min_confidence value
                        if isinstance(min_confidence, list):
                            min_confidence = min_confidence[labels.index(sub_labels)]

                        # for a multi-label classification,
                        # we need to check if the confidence is high enough for each label
                        # so if it isn't, we skip the segment - which means that all other remaining labels
                        # will be skipped as well
                        if classification['scores'][0] < min_confidence:
                            current_segment_passed_classification = False
                            logger.debug('Skipping segment classification for the following segment '
                                         'because a confidence of {}'
                                         'is too low to classify it in any of the labels {}: \n{}\n\n'
                                         .format(classification['scores'][0], sub_labels, segment['text']))
                            continue

                        # add it to the corresponding list, but first make sure the label exists
                        if classification['labels'][0] not in classified_segments:
                            classified_segments[classification['labels'][0]] = []

                        classified_segments[classification['labels'][0]].append(segment)

                        # clear classification to free up memory
                        del classification

                else:
                    logger.error('Invalid labels for classification: {}'.format(labels))
                    continue

                # update progress bar - this should be done after each segment is classified
                # because the progress bar is based on the number of segments
                pbar.update(1)

                # get the percentage of progress
                progress = int(((i+1) / len(segments)) * 100)

                # if there's a queue_id, update the queue item with the progress and some output
                if kwargs.get('queue_id'):
                    self.processing_queue.update_queue_item(kwargs['queue_id'],
                                                            progress=progress, output='', save_to_file=False)

                    # cancel process if user requested it via queue
                    if self.processing_queue.cancel_if_canceled(queue_id=kwargs.get('queue_id')):
                        return None

        # if there are no segments to classify, return
        if not classified_segments:
            return None

        # if there are any multi-label passes, go through each segment and check if it's in the list of all the labels
        # but make sure that sufficient number of label groups were provided
        # - as a minimum check first, before matching the labels below
        if multi_label_pass and len(labels) >= len(multi_label_pass):

            classified_segments['_multi_label_pass_'] = []

            # take each label from the multi-label pass list and use it to intersect the classified segments
            for label in multi_label_pass:

                # is this label in the classified segments keys?
                if label not in classified_segments:
                    # if not, skip it
                    logger.warn("Label {} doesn't exist in classified segments: {}\n"
                                "Multi-label pass failed for all segments, since none of them have this label."
                                .format(label, classified_segments.keys()))
                    break

                # simply add the first label to the multi-label pass list
                # we're going to intersect the other labels with this one
                if classified_segments['_multi_label_pass_'] == []:
                    classified_segments['_multi_label_pass_'] = classified_segments[label]
                    continue

                # intersect the classified_segments['_multi_label_pass_'] with the current label
                classified_segments['_multi_label_pass_'] = [item for item in classified_segments['_multi_label_pass_']
                                                             if item in classified_segments[label]]
        
        logger.debug('Classification complete.')

        return classified_segments

    def group_questions(self, segments=None, transcription_file_path: str = None, group_name: str = "Questions",
                        **kwargs):
        """
        This uses the classify_segments() method to detect questions and add them to a transcription group
        :param segments: the segments to classify
        :param transcription_file_path: the path to the transcription json file
        :param group_name: the name of the group to save the questions in (default: Questions)
        :param kwargs: this is not needed, but makes sure that any additional arguments are ignored
        :return: the questions_group
        """

        # initialize the empty transcription data etc.
        transcription_data = None
        questions_group = None
        transcript_groups = {}

        # if no segments were provided, try to get them from the transcription file
        if not segments:

            transcription_data = self.get_transcription_file_data(transcription_file_path=transcription_file_path)

            if not transcription_data:
                logger.error('Unable to group questions - no segments provided and no transcription file found.')

                if kwargs.get('queue_id'):
                    self.processing_queue.update_status(kwargs['queue_id'], 'failed')

                return None

            segments = transcription_data['segments']

        # classify the segments as questions or statements
        # but use the existing transcription data if we have it
        classified_question_segments = self.classify_segments(
            segments,
            labels=[
                ['interrogative sentence', 'declarative sentence'],
                ['question', 'statement'],
                ['asking', 'telling'],
                ['ask', 'tell'],
            ],
            multi_label_pass=['interrogative sentence', 'question', 'asking', 'ask'],
            min_confidence=[0.5, 0.5, 0.7, 0.7],
            **kwargs
        )

        # cancel if the process was canceled
        if kwargs.get('queue_id'):
            if self.processing_queue.cancel_if_canceled(queue_id=kwargs.get('queue_id')):
                return None

        # if we have question segments, create a group with them
        # but save it later, after the transcription is saved
        # since this is a multi_label_pass classification, we're going to use the '_multi_label_pass_' key
        if isinstance(classified_question_segments, dict) \
                and '_multi_label_pass_' in classified_question_segments \
                and len(classified_question_segments['_multi_label_pass_']) > 0:

            # get all the current groups using get_all_transcript_groups
            transcript_groups = self.t_groups_obj.get_all_transcript_groups(
                # don't use the transcription data to force a reload of the groups in case they were updated externally
                # transcription_data=transcription_data,
                transcription_file_path=transcription_file_path
            )

            # make sure we're not overwriting an existing group
            n = 1
            while self.t_groups_obj.group_id_from_name(group_name) in transcript_groups:

                # remove any "_n" suffixes from the group name
                if group_name.endswith('_' + str(n)):
                    group_name = group_name[:-2]

                n += 1

                # now add the "_n" suffix
                group_name = group_name + '_' + str(n)

            questions_group = self.t_groups_obj.segments_to_groups(
                segments=classified_question_segments['_multi_label_pass_'],
                group_name=group_name
            )

        # if this was successful, save the questions group to the transcription json file
        if questions_group is not None:

            # we're only passing the questions group to the save_transcript_groups method
            # so this will only save the questions group and not touch any existing ones
            self.t_groups_obj.save_transcript_groups(transcription_file_path,
                                                     questions_group,
                                                     group_id=group_name)

        # if we have a queue_id, update the status to done
        if kwargs.get('queue_id', None):
            self.processing_queue.update_status(queue_id=kwargs.get('queue_id', None), status='done')

        # update all the observers that are listening for this transcription
        self.notify_observers('update_transcription_{}'.format(self.get_transcription_id(transcription_file_path)))

        # update all the observers that are listening for this transcription's groups
        self.notify_observers('update_transcription_groups_{}'
                              .format(self.get_transcription_id(transcription_file_path)))

        return questions_group

    def post_process_whisper_result(self, audio, result, **kwargs):
        """
        Post processes the result of a whisper transcribe call
        This should be applied for each segment in part to ensure that we're re-merging the entire result correctly
        :param audio:
        :param result:
        :return:
        """

        # don't do anything if there are no segments
        if not isinstance(result, dict) or 'segments' not in result:
            return result

        # split segments if necessary (by punctuation marks or by word/character limits)
        result['segments'] = self.split_segments(result['segments'], **kwargs)

        # get the prevent short gaps option (if any)
        prevent_short_gaps = kwargs.get('prevent_short_gaps', False)

        if prevent_short_gaps:
            try:
                prevent_short_gaps = float(prevent_short_gaps)
            except ValueError:
                prevent_short_gaps = False

        if prevent_short_gaps:
            logger.debug('Filling gaps shorter than {}s in the result...'.format(prevent_short_gaps))

        # do some housekeeping
        # go through each segment in the result
        previous_segment_end_time = None
        new_result_segments = []
        for n, segment in enumerate(result['segments']):

            # do not allow segments that are not dictionaries
            if not isinstance(segment, dict):
                logger.debug('Segment {} is not a dictionary: {}\nRemoving from results.'.format(n, segment))

                # remove the segment from the result
                result['segments'].remove(segment)

                # continue to the next segment
                continue

            # do not allow empty segments or segments that are not strings
            if 'text' not in segment or not isinstance(segment['text'], str) or segment['text'] == '':
                # remove the segment from the result
                result['segments'].remove(segment)

                # continue to the next segment
                continue

            # remove word timestamps from the result to avoid confusion,
            # until the word-based transcript editing is implemented
            if 'words' in segment and kwargs.get('post_remove_word_timestamps', False):
                del segment['words']

            # add the segment to the new result segments
            new_result_segments.append(segment)

            # if we're supposed to prevent short gaps between segments
            # and the previous segment ended less than 'prevent_short_gaps' seconds ago
            # do this
            if previous_segment_end_time is not None and isinstance(prevent_short_gaps, float):

                # get the time difference between the end of the previous segment and the start of this segment
                time_difference = segment['start'] - previous_segment_end_time

                # if the time difference is less than the prevent_short_gaps value
                if time_difference < prevent_short_gaps:
                    # set the end time of the previous segment to the start time of this segment
                    new_result_segments[-2]['end'] = segment['start']

            # if we made it so far it means that the segment will be included in the result,
            # so remember the end time of this segment
            previous_segment_end_time = segment['end']

        # replace the segments in the result with the new segments
        result['segments'] = new_result_segments

        return result

    def speaker_diarization(self, audio_path, add_speakers_to_segments):

        # WORK IN PROGRESS
        # print("Detecting speakers.")

        # from pyannote.audio import Pipeline
        # pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

        # apply pretrained pipeline
        # diarization = pipeline(audio_path)

        # print the result
        # for turn, _, speaker in diarization.itertracks(yield_label=True):
        #    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
        return False

    def whisper_transcribe_segments(self, audio_segments, task, next_segment_id, other_options, queue_id=None):
        """
        Transcribes only the passed audio segments
        and offsets the transcription segments start and end times

        Only returns the transcription segments
        """

        results = {'segments': []}
        result = None

        # this will be counted up for each segment to provide a unique id
        id_count = 0

        # the total duration of the audio is the sum of the duration of each audio segment
        # the duration of each audio segment is the end time minus the start time
        total_duration = sum([audio_segment[1] - audio_segment[0] for audio_segment in audio_segments])

        # transcribe each audio segment
        previous_progress = 0
        for audio_segment in audio_segments:

            if len(audio_segment) != 3:
                logger.warning('Audio segment must be a list of [start, end, audio]')
                continue

            # pre process the audio segment
            audio_segment = self.pre_process_audio_segment(audio_segment, **other_options)

            # only send to whisper the options that it knows
            decoding_options = self.whisper_options(**other_options.get('whisper_options', {}))

            # run whisper transcribe on the audio segment
            result = self.whisper_model.transcribe(audio_segment[2],
                                                   task=task,
                                                   verbose=True,
                                                   queue_id=queue_id,
                                                   toolkit_ops_obj=self,
                                                   total_duration=total_duration,
                                                   audio_segment_duration=audio_segment[1] - audio_segment[0],
                                                   previous_progress=previous_progress,
                                                   **decoding_options
                                                   )

            # remove word timestamps from final transcription until we implement word-based editing
            other_options['post_remove_word_timestamps'] = \
                other_options.get('post_remove_word_timestamps', True)

            # post process the result
            result = self.post_process_whisper_result(audio_segment[2], result, **other_options)

            # get the progress of the transcription so far,
            # so we can pass it to the next audio segment for the progress calculation
            previous_progress = self.transcription_progress(queue_id)

            # now process the result and add the original start time offset
            # to each transcript segment start and end times

            # if there are segments in the result
            # re-calibrate the start and end times of each segment according to the offset
            # and calculate the segment id
            if isinstance(result, dict) and 'segments' in result and result['segments']:

                # take each segment and add the offset to the start and end time
                for i, transcript_segment in enumerate(result['segments']):
                    transcript_segment['start'] += audio_segment[0]
                    transcript_segment['end'] += audio_segment[0]

                    # avoid end time being larger than the interval end time
                    # - there seems to be an issue in the whisper model:
                    #   https://github.com/openai/whisper/discussions/357
                    if transcript_segment['end'] > audio_segment[1]:
                        transcript_segment['end'] = audio_segment[1]

                    # also avoid start time being smaller than the interval start time
                    if transcript_segment['start'] < audio_segment[0]:
                        transcript_segment['start'] = audio_segment[0]

                    # if the segment contains a 'words' key,
                    # then add the offset to the start and end time of each word
                    if 'words' in transcript_segment:
                        for word in transcript_segment['words']:
                            word['start'] += audio_segment[0]
                            word['end'] += audio_segment[0]

                            # avoid end time being larger than the interval end time
                            if word['end'] > audio_segment[1]:
                                word['end'] = audio_segment[1]

                            # also avoid start time being smaller than the interval start time
                            if word['start'] < audio_segment[0]:
                                word['start'] = audio_segment[0]

                    transcript_segment['id'] = next_segment_id + id_count
                    id_count += 1

                    # update the segment in the result
                    # result['segments'][i] = transcript_segment

                    # add the transcription of the audio segment to the results list
                    results['segments'].append(transcript_segment)

        # copy the status from the result to the results (if any)
        # normally we should only get a status if the transcription was canceled or it failed
        if isinstance(result, dict) and 'status' in result:
            results['status'] = result['status']

        return results

    def exclude_segments_by_intervals(self, audio_array, time_intervals, excluded_time_intervals, sr):
        """
        Excludes certain audio segments from audio_array according to the excluded_time_intervals
        and returns a new audio_array with the excluded segments removed
        """

        # if there are exclusion time segments and time_intervals
        if excluded_time_intervals and type(excluded_time_intervals) == list and len(excluded_time_intervals) > 0 \
                and time_intervals and type(time_intervals) == list and len(time_intervals) > 0:

            # sort the excluded segments by start time
            excluded_time_intervals = \
                sorted(excluded_time_intervals, key=lambda x: x[0])

            # take each time segment
            for excluded_time_interval in excluded_time_intervals:

                # and check it against each of the time segments we selected for transcription
                for time_interval in time_intervals:

                    # if the exclusion is outside the current segment times
                    if excluded_time_interval[1] <= time_interval[0] \
                            or excluded_time_interval[0] >= time_interval[1]:
                        continue

                    # if the exclusion is exactly as the current segment times
                    elif time_interval[0] == excluded_time_interval[0] \
                            and time_interval[1] == excluded_time_interval[1]:

                        # simply remove the whole segment
                        time_intervals.remove(time_interval)

                    else:

                        # if the exclusion start time is equal to the segment start time
                        if excluded_time_interval[0] == time_interval[0]:

                            # cut out the beginning of the segment
                            # by using the end time of the exclusion as its start
                            time_interval[0] = excluded_time_interval[1]


                        # if the exclusion end time is equal to the segment end time
                        elif excluded_time_interval[1] == time_interval[1]:

                            # cut out the end of the segment
                            # by using the start time of the exclusion as its end
                            time_interval[1] = excluded_time_interval[0]


                        # if the exclusion is in the middle of the segment
                        elif excluded_time_interval[0] > time_interval[0] \
                                and excluded_time_interval[1] < time_interval[1]:

                            # remove the segment from the list
                            time_intervals.remove(time_interval)

                            # but then split it into two segments
                            # first the segment until the exclusion
                            time_intervals.append([time_interval[0], excluded_time_interval[0]])

                            # then the segment from the exclusion
                            time_intervals.append([excluded_time_interval[1], time_interval[1]])

            # sort the selection by start time
            time_intervals = sorted(time_intervals, key=lambda x: x[0])

        # now split the audio using the newly created intervals
        audio_segments, time_intervals = self.split_audio_by_intervals(audio_array, time_intervals, sr)

        return audio_segments, time_intervals

    def whisper_transcribe(self, name=None, audio_file_path=None, task=None,
                           target_dir=None, queue_id=None, return_path=False, **other_options) -> bool or str:
        """
        This prepares and transcribes audio using Whisper
        :param name:
        :param audio_file_path:
        :param task:
        :param target_dir:
        :param queue_id:
        :param return_path: if True, returns the path to the transcription file if successful
        :param other_options:
        :return:
        """

        # if no audio file path was passed, try to use the source file path if it was passed
        if audio_file_path is None and other_options.get('source_file_path', None) is not None:
            audio_file_path = other_options.get('source_file_path', None)

        # don't continue unless we have a queue_id
        if audio_file_path is None or not audio_file_path:
            logger.warning('No audio file path was passed to whisper_transcribe. Aborting.')

            # update the queue item status
            if queue_id is not None:
                self.processing_queue.update_queue_item(queue_id=queue_id, status='failed')

            return False

        # use the name of the file in case the name wasn't passed
        if name is None:
            name = os.path.basename(audio_file_path)

        # use the directory where the file is stored if another one wasn't passed
        if target_dir is None:
            target_dir = os.path.dirname(audio_file_path)

        # what is the name of the audio file
        audio_file_name = os.path.basename(audio_file_path)

        # if a timeline_name was sent, remember it for later
        timeline_name = None
        if 'timeline_name' in other_options:
            timeline_name = other_options['timeline_name']
            del other_options['timeline_name']

        # if a project_name was sent, remember it for later
        project_name = None
        if 'project_name' in other_options:
            project_name = other_options['project_name']
            del other_options['project_name']

        torch_device_changed = False
        if 'device' in other_options and self.torch_device != other_options['device']:
            torch_device_changed = True

        # select the device that was passed (if any)
        if 'device' in other_options:
            # select the new whisper device but take it through the torch device selection to make sure it's valid
            self.torch_device = self.torch_device_type_select(other_options['device'])
            del other_options['device']

        # load OpenAI Whisper model
        # and hold it loaded for future use (unless another model name was passed via other_whisper_options)
        if self.whisper_model is None \
                or ('model_name' in other_options
                    and self.whisper_model_name != other_options['model_name']) \
                or torch_device_changed:

            # update the status of the item in the queue
            self.processing_queue.update_queue_item(queue_id=queue_id, status='loading model')

            # use the model name that was passed in the call (if any)
            if 'model_name' in other_options and other_options['model_name']:
                self.whisper_model_name = other_options['model_name']

            # cancel transcription if user requested it
            if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
                return None

            # if the Whisper transformer model was never downloaded, log that we're downloading it
            model_downloaded_before = True
            if self.stAI.get_app_setting(setting_name='whisper_model_downloaded_{}'
                    .format(self.whisper_model_name),
                                         default_if_none=False
                                         ) is False:
                logger.warning('The whisper {} model may need to be downloaded and could take a while '
                               'depending on the Internet connection speed. '
                               .format(self.whisper_model_name)
                               )

                # update the status of the item in the transcription log
                self.processing_queue.update_queue_item(queue_id=queue_id, status='downloading model')

                model_downloaded_before = False

            # cancel transcription if user requested it
            if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
                return None

            logger.info('Loading Whisper {} model.'.format(self.whisper_model_name))
            try:
                self.whisper_model = whisper.load_model(self.whisper_model_name, device=self.torch_device)
            except Exception as e:
                logger.error('Error loading Whisper {} model: {}'.format(self.whisper_model_name, e))

                # update the status of the item in the transcription log
                self.processing_queue.update_queue_item(queue_id=queue_id, status='failed')

            # once the model has been loaded, we can note that in the app settings
            # this is a wat to keep track if the model has been downloaded or not
            # but it's not 100% reliable and we may need to find a better way to do this in the future
            if not model_downloaded_before:
                self.stAI.save_config(setting_name='whisper_model_downloaded_{}'.format(self.whisper_model_name),
                                      setting_value=True)

            # let the user know if the whisper model is multilingual or english-only
            logger.info('Selected Whisper model is {}.'.format(
                'multilingual' if self.whisper_model.is_multilingual else 'English-only'
            ))

        # cancel transcription if user requested it
        if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
            return None

        # load audio file as array using librosa
        # this should work for most audio formats (so ffmpeg might not be needed at all)
        audio_array, sr = librosa.load(audio_file_path, sr=16_000)

        # if the audio_array is longer than 10 minutes, notify the user that the process will take a while
        if len(audio_array) > 10 * 60 * 16_000:
            long_audio_msg = "The audio is long... This might take a while."
        else:
            long_audio_msg = ""

        # cancel transcription if user requested it
        if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
            return None

        # technically the transcription process starts here, so start a timer for statistics
        transcription_start_time = time.time()

        # clean up empty whisper options
        if 'whisper_options' in other_options:

            # remove empty language from whisper_options
            if 'language' in other_options['whisper_options'] \
                and (other_options['whisper_options']['language'] == ''
                     or other_options['whisper_options']['language'] is None):

                del other_options['whisper_options']['language']

            # remove empty initial prompt
            if 'initial_prompt' in other_options['whisper_options'] \
                    and (other_options['whisper_options']['initial_prompt'] == ''
                         or other_options['whisper_options']['initial_prompt'] is None):

                del other_options['whisper_options']['initial_prompt']

        # assume no time intervals
        time_intervals = None

        # TIME INTERVALS PRE-PROCESSING starts here

        # if pre_detect_speech is True, detect speech intervals in the audio
        if 'pre_detect_speech' in other_options:

            # detect speech intervals and save them in time_intervals
            if other_options['pre_detect_speech']:
                logger.info('Detecting speech intervals in the audio.')

                # update the status of the item in the transcription log
                self.processing_queue.update_queue_item(queue_id=queue_id, status='pre-detecting speech')

                logger.info('Pre-detecting speech intervals in the audio.')

                # perform speech detection
                time_intervals = self.get_speech_intervals(audio_array)

        # if time_intervals was passed from the request, take them into consideration
        if 'time_intervals' in other_options:

            # only take into consideration non boolean values
            if type(other_options['time_intervals']) is not bool:

                # if no time intervals were set before, just use the ones from the request
                if time_intervals is None:
                    time_intervals = other_options['time_intervals']
                else:
                    # intersect the time intervals from the request
                    # with the previously had time intervals (from speech for eg.)
                    time_intervals = \
                        self.combine_overlapping_intervals(other_options['time_intervals'], time_intervals)

        # split the audio into segments according to the time intervals
        # in case no time intervals were passed, this will just return one audio segment with the whole audio
        audio_segments, time_intervals = self.split_audio_by_intervals(audio_array, time_intervals, sr)

        # cancel transcription if user requested it
        if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
            return None

        # exclude time intervals that need to be excluded
        if 'excluded_time_intervals' in other_options:
            audio_segments, time_intervals = self.exclude_segments_by_intervals(
                audio_array, time_intervals, other_options['excluded_time_intervals'], sr=sr
            )

        # create an empty list to load existing transcription data (or to save the new data)
        transcription_data = {}

        existing_transcription = False

        # ignore the transcription file path if it's empty
        if 'transcription_file_path' in other_options \
            and other_options['transcription_file_path'] is None:

            del other_options['transcription_file_path']

        # load the transcription data from the file if a path was passed
        elif 'transcription_file_path' in other_options:

            if other_options['transcription_file_path'].strip() != '':
                transcription_file_path = other_options['transcription_file_path']

                # load the transcription data from the file
                transcription_data = self.get_transcription_file_data(transcription_file_path)

                # mark that we're using existing transcription data (re-transcribing)
                # and remember the name of the transcription file
                existing_transcription = transcription_file_path

                # change the status of the item in the transcription log to re-transcribing
                self.processing_queue.update_queue_item(queue_id=queue_id, status='re-transcribing')

            del other_options['transcription_file_path']

        # get the next id based on the largest id from transcription_data segments
        if type(transcription_data) == dict and 'segments' in transcription_data:
            next_segment_id = max([int(segment['id']) for segment in transcription_data['segments']]) + 1
        else:
            next_segment_id = 0

        # update the status of the item in the transcription log
        self.processing_queue.update_queue_item(queue_id=queue_id, status='transcribing')

        # let the user know the transcription process has started
        notification_msg = "Transcribing {}.\n{}".format(name, long_audio_msg)
        if self.is_UI_obj_available():
            self.toolkit_UI_obj.notify_via_os("Starting Transcription",
                                              notification_msg,
                                              debug_message="Transcribing {}. {}".format(name, long_audio_msg))
        else:
            logger.info(notification_msg)

        # last chance to cancel if user requested it
        # before the transcription process starts
        if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
            return None

        # initialize empty result
        result = None

        # transcribe the audio segments
        # (or just one audio segment with the whole audio if no time intervals were passed)
        try:
            result = self.whisper_transcribe_segments(audio_segments=audio_segments,
                                                      task=task,
                                                      next_segment_id=next_segment_id,
                                                      other_options=other_options,
                                                      queue_id=queue_id
                                                      )
        except Exception:
            logger.error('Error transcribing audio using Whisper.', exc_info=True)

            # update the status of the item in the transcription log
            self.processing_queue.update_queue_item(queue_id=queue_id, status='failed', progress='')

        # was the transcription canceled or failed?
        # if whisper returned None or a dict with status failed or canceled
        if result is None \
                or (type(result) is dict and 'status' in result
                    and (result['status'] == 'failed' or result['status'] == 'canceled')
        ):
            # copy the status from the result to the log status
            # or simply set it to failed if the result is None
            queue_status = result['status'] if type(result) is dict and 'status' in result else 'failed'

            self.processing_queue.update_queue_item(queue_id=queue_id, status=queue_status, progress='')

            return None

        # update the transcription data with the new segments
        # but first remove all the segments between the time intervals that were passed
        if type(transcription_data) is dict and 'segments' in transcription_data:

            # for each time interval, remove all the segments that are between the start and end of the interval
            for time_interval in time_intervals:

                # get the start and end of the time interval
                start_time = time_interval[0]
                end_time = time_interval[1]

                # remove all the segments that are between the start and end of the time interval
                transcription_data['segments'] = [segment for segment in transcription_data['segments'] if
                                                  segment['start'] < start_time or segment['end'] > end_time]

                # if we have segments in result, add them to the transcription data
                if type(result) is dict and 'segments' in result:
                    # add the new segments to the transcription data
                    transcription_data['segments'] += [segment for segment in result['segments']
                                                       if segment['start'] >= start_time
                                                       and segment['end'] <= end_time]

            # now make sure that the segments are sorted by start time
            transcription_data['segments'] = sorted(transcription_data['segments'], key=lambda k: k['start'])

        # perform speaker diarization if requested
        # self.speaker_diarization(audio_file_path)

        # let the user know that the speech was processed
        notification_msg = "Finished transcription for {} in {} seconds" \
            .format(name, round(time.time() - transcription_start_time))

        if self.is_UI_obj_available():
            self.toolkit_UI_obj.notify_via_os("Finished Transcription", notification_msg, notification_msg)
        else:
            logger.info(notification_msg)

        # update the status of the item in the transcription log
        self.processing_queue.update_queue_item(queue_id=queue_id, status='saving files')

        # WHAT HAPPENS FROM HERE

        # Once a transcription is completed, you should see 4 or 5 files:
        # - the original audio file used for transcription (usually WAV)
        # - if the file was rendered from resolve, a json file - which is kind of like a report card for what was
        #   rendered from where (see mots_resolve.py render())
        # - the resulting transcription.json file with the actual transcription
        # - the plain text transcript in TXT format - transcript.txt
        # - the transcript in SRT format, ready to be imported in Resolve (or other apps)
        #
        # Once these are written, the transcription.json file should be used to gather any further information saved
        # within the tool, therefore it's important to also mention the 3 other files within it (txt, srt, wav). But,
        # with this approach we need to keep in mind to always keep the other 3 files next to the transcription.json
        # to ensure that the files can migrate between different machines and the links won't break.
        #
        # Furthermore, the same file will be used to save any other information related to the transcription.)

        # if we're not updating an older transcription file
        if not existing_transcription or type(existing_transcription) is not str:

            # first determine if there's another transcription.json file with the same name
            # and keep adding numbers to it until the name is free
            file_name = audio_file_name
            file_num = 2
            while os.path.exists(os.path.join(target_dir, file_name + '.transcription.json')):
                file_name = audio_file_name + "_{}".format(file_num)
                file_num = file_num + 1

            # also create the transcription data dictionary
            transcription_data = result

            # add the timeline name to the transcription data, if there is one
            if timeline_name is not None:
                transcription_data['timeline_name'] = timeline_name

            # add the project name to the transcription data, if there is one
            if project_name is not None:
                transcription_data['project_name'] = project_name

        else:
            # for the file name we'll use the name of the existing transcription file,
            # but remove '.transcription.json' from the end
            file_name = os.path.basename(existing_transcription).replace('.transcription.json', '')

        # take the full text from the transcription segments since whisper might have given us a text
        # that is incomplete due to interval splitting
        # this also takes into account the segments that were passed before transcription
        #   (in case of re-transcriptions)
        transcription_data['text'] = ' '.join([segment['text'] for segment in transcription_data['segments']])

        txt_file_path = self.save_txt_from_transcription(file_name=file_name, target_dir=target_dir,
                                                         transcription_data=transcription_data)

        # only save the filename without the absolute path to the transcript json
        if txt_file_path:
            transcription_data['txt_file_path'] = os.path.basename(txt_file_path)

        # save the SRT file next to the transcription file
        srt_file_path = self.save_srt_from_transcription(file_name=file_name, target_dir=target_dir,
                                                         transcription_data=transcription_data)

        # only the basename is needed here too
        if srt_file_path:
            transcription_data['srt_file_path'] = os.path.basename(srt_file_path)

        # remember the audio_file_path this transcription is based on too
        transcription_data['audio_file_path'] = os.path.basename(audio_file_path)

        # don't forget to add the name of the transcription
        transcription_data['name'] = name

        # and some more info about the transription
        transcription_data['task'] = task
        transcription_data['model'] = self.whisper_model_name

        # add the transcription unique id
        transcription_data['transcription_id'] = queue_id

        # if the transcription data doesn't contain the fps, the timeline name or the start_tc,
        # try to get them from a render.json file
        # these files are saved by the render() function in mots_resolve.py
        if 'timeline_fps' not in transcription_data or transcription_data['timeline_fps'] == '' \
                or 'timeline_start_tc' not in transcription_data or transcription_data['timeline_start_tc'] == '' \
                or 'timeline_name' not in transcription_data or transcription_data['timeline_name'] == '':

            # the render.json file path should be next to the audio file
            # and will have the same name as the audio file, but with .json at the end
            render_json_file_path = os.path.join(os.path.dirname(audio_file_path), file_name + '.json')

            # if the render.json file exists, try to get the data from it
            if os.path.exists(render_json_file_path):
                with open(render_json_file_path, 'r') as render_json_file:
                    render_data = json.load(render_json_file)
                    if 'timeline_fps' not in transcription_data and 'fps' in render_data:
                        transcription_data['timeline_fps'] = render_data['fps']
                    if 'timeline_start_tc' not in transcription_data and 'timeline_start_tc' in render_data:
                        transcription_data['timeline_start_tc'] = render_data['timeline_start_tc']
                    if 'timeline_name' not in transcription_data and 'timeline_name' in render_data:
                        transcription_data['timeline_name'] = render_data['timeline_name']

                logger.debug('Getting timeline data from render json file: {}'.format(render_json_file_path))

            else:
                logger.debug('No render json file found at {}'.format(render_json_file_path))

        # save the transcription file with all the added data
        transcription_json_file_path = self.save_transcription_file(file_name=file_name, target_dir=target_dir,
                                                                    transcription_data=transcription_data)

        # cancel transcription if user requested it
        if self.processing_queue.cancel_if_canceled(queue_id=queue_id):
            return None

        # perform question grouping if requested
        # if 'group_questions' in other_options and other_options['group_questions']:
        #     logger.info('Grouping questions.')
        #     self.processing_queue.update_queue_item(queue_id=queue_id, status='grouping', progress='')
        #
        #     # detect and group questions
        #     self.group_questions(
        #         segments=result['segments'] if not existing_transcription else transcription_data['segments'],
        #         transcription_file_path=transcription_json_file_path
        #     )

        # if there's a project_name and a timeline_name
        # link the transcription to the project and timeline
        if project_name is not None and timeline_name is not None:
            self.link_transcription_to_timeline(transcription_file_path=transcription_json_file_path,
                                                project_name=project_name,
                                                timeline_name=timeline_name,
                                                link=True)

        # when done, change the status in the queue, clear the progress
        # and also add the file paths to the queue item
        self.processing_queue.update_queue_item(
            queue_id=queue_id,
            status='done',
            progress='',
            srt_file_path=transcription_data['srt_file_path'] if 'srt_file_path' in transcription_data else '',
            txt_file_path=transcription_data['txt_file_path'] if 'txt_file_path' in transcription_data else '',
            transcription_file_path=transcription_json_file_path
        )

        # todo: move this to the UI - maybe a monitor function that checks the queue window for events?
        # why not open the transcription in a transcription window if the UI is available?
        if self.is_UI_obj_available():
            self.toolkit_UI_obj.open_transcription_window(
                title=name,
                transcription_file_path=transcription_json_file_path,
                srt_file_path=transcription_data['srt_file_path']
                if 'srt_file_path' in transcription_data and transcription_data['srt_file_path'] else None
            )

        return True if not return_path else transcription_json_file_path

    def save_transcription_file(self, transcription_file_path=None, transcription_data=None,
                                file_name=None, target_dir=None, backup=None) -> str or bool:
        '''
        Saves the transcription file either to the transcription_file_path
        or to the "target_dir/name.transcription.json" path

        :param transcription_file_path:
        :param transcription_data:
        :param file_name: This is usually the audio file name
        :param target_dir:
        :param backup: If True, the existing transcription file will be backed up to a .backups folder
                        in the same directory as the transcription file. The backup string will be used as a suffix
                        to the backup file name
        :return: False or transcription_file_path
        '''

        # if no full path was passed
        if transcription_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                transcription_file_path = os.path.join(target_dir, file_name + '.transcription.json')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if transcription_file_path:

            # if backup_original is enabled, it will save a copy of the transcription file to
            # originals/[filename].backup.json (if one doesn't exist already)
            if backup and os.path.exists(transcription_file_path):

                import shutil

                # format the name of the backup file
                backup_transcription_file_path = \
                    os.path.splitext(os.path.basename(transcription_file_path))[0] + '.' + str(backup) + '.json'

                backups_dir = os.path.join(os.path.dirname(transcription_file_path), '.backups')

                # if the backups directory doesn't exist, create it
                if not os.path.exists(backups_dir):
                    os.mkdir(backups_dir)

                # copy the existing file to the backups directory
                # if it doesn't already exist
                if not os.path.exists(os.path.join(backups_dir, backup_transcription_file_path)):
                    shutil.copyfile(transcription_file_path,
                                    os.path.join(backups_dir, backup_transcription_file_path))

            # Finally,
            # save the whole whisper result in the transcription json file
            # don't question what is being passed, simply save everything
            with open(transcription_file_path, 'w', encoding='utf-8') as outfile:
                json.dump(transcription_data, outfile)

            return transcription_file_path

        return False

    @staticmethod
    def get_transcription_file_data(transcription_file_path):

        # make sure the transcription exists
        if not os.path.exists(transcription_file_path):
            logger.warning("Transcription file {} not found".format(transcription_file_path))
            return False

        # get the contents of the transcription file
        with codecs.open(transcription_file_path, 'r', 'utf-8-sig') as json_file:
            transcription_json = json.load(json_file)

        # make sure that it's a transcription file
        if 'segments' not in transcription_json:
            logger.warning(
                "The file {} is not a valid transcription file (segments missing)".format(transcription_file_path))
            return False

        # check if the transcription file contains word timings
        if len(transcription_json['segments']) > 0 and 'words' in transcription_json['segments'][0]:
            logger.debug("Word level timings detected in transcription file data.")

        return transcription_json

    @staticmethod
    def get_transcription_id(transcription_file_path):
        """
        We're using this to generate a unique ID for the transcription based on its file path
        """
        return hashlib.md5(transcription_file_path.encode('utf-8')).hexdigest()

    def get_transcription_audio_file_path(self, transcription_file_path, transcription_data=None):
        """
        Returns the audio file path from the transcription file
        """

        # we still need the transcription file path to get the absolute path of the audio file
        if not transcription_file_path:
            logger.error('No transcription file path was passed.')
            return None

        # get the transcription data first (if it wasn't passed)
        if not transcription_data:
            transcription_data = self.get_transcription_file_data(transcription_file_path)

        if transcription_data:

            if 'audio_file_path' in transcription_data:

                # if the path is not absolute, make it absolute, based on the transcription file path
                if not os.path.isabs(transcription_data['audio_file_path']):

                    # get the directory of the transcription file
                    transcription_file_dir = os.path.dirname(transcription_file_path)

                    # join the audio file path with the transcription file dir
                    audio_file_path = os.path.join(transcription_file_dir, transcription_data['audio_file_path'])

                    # if the audio file exists, return it
                    if os.path.exists(audio_file_path):
                        return audio_file_path

                    logger.error("Audio file path not found: {}".format(audio_file_path))
                    return None

            logger.error("Audio file path not found in transcription file: {}".format(transcription_file_path))
            return None

        # if we got here it means that the audio file path is not in the transcription file or cannot be found
        logger.error("Invalid transcription file: {}".format(transcription_file_path))
        return None

    def time_str_to_seconds(self, time_str: str) -> float:
        '''
        Converts 00:00:00.000 time formats to seconds.
        :param time_str: 00:00:00.000 (string)
        :return:
        '''

        # use regex to get the hours, minutes, seconds and milliseconds
        # from the time string
        time_regex = re.compile(r'(\d{2}):(\d{2}):(\d{2}).(\d)')
        time_match = time_regex.match(time_str)

        # if the time string matches the regex
        if time_match:

            # calculate the seconds
            seconds = int(time_match.group(1)) * 3600 + \
                      int(time_match.group(2)) * 60 + \
                      int(time_match.group(3)) + \
                      int(time_match.group(4)) / 1000

        # otherwise, throw an error
        else:
            exception = 'The passed time string {} is not formatted correctly.'.format(time_str)
            logger.error(exception)

            # throw exception
            raise ValueError(exception)

        return seconds

    def convert_srt_to_transcription_json(self, srt_file_path: str, transcription_file_path: str = None,
                                          overwrite: bool = False):
        '''
        Converts an srt file to a transcription json file, saves it in the same directory
         and returns the name of the transcription file.

        If it's impossible to convert or save the srt file, it will return None

        If overwrite is True, it will overwrite any existing transcription file from the same directory.

        :param srt_file_path:
        :param transcription_file_path:
        :param overwrite:
        :return:
        '''

        # make sure the srt file exists
        if not os.path.exists(srt_file_path):
            logger.warning("SRT file {} doesn't exist.".format(srt_file_path))
            return None

        # get the contents of the srt file
        with codecs.open(srt_file_path, 'r', 'utf-8-sig') as srt_file:
            srt_contents = srt_file.read()

        srt_segments = []
        full_text = ''

        # if properly formatted, the srt file should have 2 new lines between each subtitle
        # so go through all of them
        for line_string in srt_contents.split('\r\n'):

            if line_string != '':

                # if the line is a number, it's the subtitle number
                if line_string.isdigit():
                    idx = int(line_string)

                    # so create a new subtitle segment
                    srt_segments.append({'id': str(idx), 'start': 0.0, 'end': 0.0, 'text': ''})

                # if the line is not a number, it's either the time or the text
                else:
                    # if the line contains '-->', it's the time
                    if '-->' in line_string:
                        # split the line in the middle to get the start and end times
                        start_time, end_time = line_string.split('-->')

                        # add these to the last subtitle segment
                        srt_segments[-1]['start'] = self.time_str_to_seconds(start_time.strip())
                        srt_segments[-1]['end'] = self.time_str_to_seconds(end_time.strip())

                    # if the line doesn't contain '-->', it's the text
                    else:

                        # add the text to the last subtitle segment
                        # but also a white space if there's already a string inside the segment text
                        srt_segments[-1]['text'] += \
                            ' ' + line_string if len(srt_segments[-1]['text']) > 0 else line_string

                        # add the text to the full text
                        full_text += ' ' + line_string if len(full_text) > 0 else line_string

        # initialize the transcription_data for the transcription_file
        transcription_data = {'text': full_text,
                              'segments': srt_segments,
                              'task': 'convert_srt_to_transcription_json',
                              'audio_file_path': '',
                              'srt_file_path': os.path.basename(srt_file_path),
                              'name': os.path.splitext(os.path.basename(srt_file_path))[0]
                              }

        # if no transcription file path was passed, create one based on the srt file name
        if transcription_file_path is None:
            transcription_file_path = os.path.splitext(srt_file_path)[0] + '.transcription.json'

        if not overwrite and os.path.exists(transcription_file_path):
            logger.error("Transcription file {} already exists. Cannot overwite.".format(transcription_file_path))
            return None

        # if the transcription file already exists, log that we're overwriting it
        elif overwrite and os.path.exists(transcription_file_path):
            logger.info("Overwritting {} with transcription from SRT.".format(transcription_file_path))

        else:
            logger.info("Saving transcription from SRT to {}.".format(transcription_file_path))

        # save the full text to a text file
        transcription_txt_file_path = os.path.splitext(transcription_file_path)[0] + '.txt'
        self.save_txt_from_transcription(transcription_txt_file_path, transcription_data)

        # save the transcription data to the transcription file
        self.save_transcription_file(transcription_file_path, transcription_data)

        return transcription_file_path

    def process_transcription_data(self, transcription_segments=None, transcription_data=None):
        '''
        This takes the passed segments and puts them into a dict ready to be passed to a transcription file.

        It's important that if the contents of any transcription segment was edited, to see that reflected in
        other variables as well. It also adds the key 'modified' so we later know that the tokens might not
        correspond to the segment contents anymore.

        :param transcription_segments:
        :return:
        '''

        # take each transcription segment
        if transcription_segments is not None and transcription_segments and transcription_data is not None and 'segments' in transcription_data:

            # first empty the text variable
            transcription_data['text'] = ''

            for segment in transcription_segments:
                # take each segment and insert it into the text variable
                transcription_data['text'] = segment + ' '

            # make it known that this transcription was modified
            transcription_data['modified'] = time.time()

            return transcription_data

    def format_timestamp(self, seconds: float, always_include_hours: bool = False, decimal_marker: str = '.'):
        assert seconds >= 0, "non-negative timestamp expected"
        milliseconds = round(seconds * 1000.0)

        hours = milliseconds // 3_600_000
        milliseconds -= hours * 3_600_000

        minutes = milliseconds // 60_000
        milliseconds -= minutes * 60_000

        seconds = milliseconds // 1_000
        milliseconds -= seconds * 1_000

        hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
        return f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"

    def write_srt(self, transcript_segments: dict, srt_file_path: str):
        """
        Write the transcript segments to a file in SRT format.
        """

        with open(srt_file_path, "w", encoding="utf-8") as srt_file:
            i = 1
            for segment in transcript_segments:
                # write srt lines
                print(
                    f"{i}\n"
                    f"{self.format_timestamp(segment['start'], always_include_hours=True, decimal_marker=',')} --> "
                    f"{self.format_timestamp(segment['end'], always_include_hours=True, decimal_marker=',')}\n"
                    f"{segment['text'].strip().replace('-->', '->')}\n",
                    file=srt_file,
                    flush=True,
                )
                i += 1

    def write_txt(self, transcript_segments: dict, txt_file_path: str):
        """
        Write the transcript segments to a file in SRT format.
        Each segment is written on a new line.
        """

        with open(txt_file_path, "w", encoding="utf-8") as txt_file:
            for segment in transcript_segments:
                # write txt lines
                print(
                    f"{segment['text'].strip()}",
                    file=txt_file,
                    flush=True,
                )

    def write_avid_ds(self, transcript_segments: dict, avid_ds_file_path: str, timeline_fps, timeline_start_tc):
        """
        Write the transcript segments to a file in Avid DS format.
        """

        # this is an example format for Avid DS
        # @ This file written with StoryToolkitAI, version x.x.x
        #
        # <begin subtitles>
        #
        # 12:03:46:05 12:03:48:05
        # This is a test.
        #
        # 12:03:48:05 12:03:50:05
        # This is another test.
        #
        # <end subtitles>

        # convert the timeline_start_tc to a Timecode object
        timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

        def format_timecode_line(start_time, end_time, timeline_fps, timeline_start_tc):
            # convert the start to a timecode
            start_tc = Timecode(timeline_fps, start_seconds=start_time)

            # add the timeline_start_tc to the start_tc
            start_tc = start_tc + timeline_start_tc

            # convert the end to a timecode
            end_tc = Timecode(timeline_fps, start_seconds=end_time)

            # add the timeline_start_tc to the start_tc
            end_tc = end_tc + timeline_start_tc

            return f"{start_tc} {end_tc}"

        with open(avid_ds_file_path, "w", encoding="utf-8") as avid_ds_file:
            # write header
            print(
                f"@ This file written with StoryToolkitAI version {self.stAI.version}\n",
                file=avid_ds_file,
                flush=True
            )

            # write subtitle start
            print(
                f"<begin subtitles>\n",
                file=avid_ds_file,
                flush=True
            )

            # write subtitle lines
            for segment in transcript_segments:
                print(
                    f"{format_timecode_line(segment['start'], segment['end'], timeline_fps, timeline_start_tc)}\n"
                    f"{segment['text'].strip()}\n",
                    file=avid_ds_file,
                    flush=True,
                )

            # write subtitle end
            print(
                f"<end subtitles>",
                file=avid_ds_file,
                flush=True
            )

    def write_fusion_text_comp(self, transcript_segments: dict, comp_file_path: str, timeline_fps):
        '''
        Write the transcript segments into a Fusion Text+ comp file
        '''

        keyframes = []

        # take each transcription segment
        for segment in transcript_segments:

            # frame = int(segment["start"] * fps)

            # calculate frame based on segment start and timeline fps
            # we'll ignore the timeline_start_tc considering that we're in a comp file that starts at 0
            if segment["start"] != 0:
                keyframe_tc = Timecode(timeline_fps, start_seconds=segment["start"])
                frame = keyframe_tc.frames

            # if the segment starts at 0, we'll use frame 1 to form the timecode and frame 0 for the keyframe
            # this is because Timecode objects can't start at 0
            else:
                keyframe_tc = Timecode(timeline_fps, 1)
                frame = 0

            text = segment["text"].replace('"', '\\"')

            # create the segment keyframe
            keyframe = '[' + str(frame) + '] = { Value = Text { Value = "' + str(text) + '" } }'

            # if the next segment doesn't start exactly when this one ends, add a keyframe with an empty string
            # but only if this isn't the last segment
            if segment != transcript_segments[-1]:

                # get the next segment
                next_segment = transcript_segments[transcript_segments.index(segment) + 1]

                # if the next segment doesn't start exactly when this one ends, add a keyframe with an empty string
                if next_segment["start"] != segment["end"]:
                    # calculate frame based on segment end and timeline fps
                    # we'll ignore the timeline_start_tc considering that we're in a comp file that starts at 0
                    keyframe_tc = Timecode(timeline_fps, start_seconds=segment["end"])
                    frame = keyframe_tc.frames
                    keyframe += ',\n[' + str(frame) + '] = { Value = Text { Value = "" } }'

            keyframes.append(keyframe)

        # if there are no keyframes, return False
        if len(keyframes) == 0:
            return False

        # turn the keyframes into a string with newlines and indentation
        keyframes_str = ",\n            ".join(keyframes)

        # place the above keyframes in the fusion template
        fusion_template = '''
        {
            Tools = ordered() {
                TranscriptText = TextPlus {
                    Inputs = {
                        Width = Input { Value = 1920, },
                        Height = Input { Value = 1080, },
                        Font = Input { Value = "Open Sans", },
                        Style = Input { Value = "Bold", },
                        VerticalJustificationNew = Input { Value = 3, },
                        HorizontalJustificationNew = Input { Value = 3, },
                        StyledText = Input {
                            SourceOp = "TranscriptTextStyledText",
                            Source = "Value",
                        },
                    },
                    ViewInfo = OperatorInfo { Pos = { 311.26, 124.0282 } },
                },
                TranscriptTextStyledText = BezierSpline {
                    SplineColor = { Red = 237, Green = 142, Blue = 243 },
                    KeyFrames = {
                        ''' + keyframes_str + ''',
                    }
                },
                MergeText = Merge {
                    CtrlWZoom = false,
                    NameSet = true,
                    Inputs = {
                        Foreground = Input {
                            SourceOp = "TranscriptText",
                            Source = "Output",
                        },
                        PerformDepthMerge = Input { Value = 0, },
                    },
                    ViewInfo = OperatorInfo { Pos = { 311.26, 50.0282 } },
                },
                StoryToolkitAI_Transcript = Underlay {
                    CtrlWZoom = false,
                    NameSet = true,
                    Inputs = {
                        Comments = Input { Value = "Exported using StoryToolkitAI version ''' + self.stAI.version + '''", }
                    },
                    ViewInfo = UnderlayInfo {
                        Pos = { 307.152, 15.0243 },
                        Size = { 172, 164.121 }
                    },
                }
            },
            ActiveTool = "Text1"
        }
        '''

        # write the comp file
        with open(comp_file_path, "w", encoding="utf-8") as comp_file:
            print(
                f'{fusion_template}',
                file=comp_file,
                flush=True
            )

        # return the comp file path
        return comp_file_path

    def save_srt_from_transcription(self, srt_file_path=None, transcription_segments=None,
                                    file_name=None, target_dir=None, transcription_data=None):
        '''
        Saves an SRT file based on a transcription file.

        You can either pass the transcription segments or the full transcription data. When both are passed,
        the transcription_segments will be used.

        :param srt_file_path: The full path to the SRT file
        :param transcription_segments:
        :param file_name: The name of the SRT file
        :param target_dir:
        :param transcription_data:
        :return: False or srt_file_path
        '''

        # if no full path was passed
        if srt_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                srt_file_path = os.path.join(target_dir, file_name + '.srt')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if srt_file_path and srt_file_path != '':

            # if the transcription segments were not passed
            # try to find them in transcription_data (if that was passed too)
            if transcription_segments is None and transcription_data and 'segments' in transcription_data:
                transcription_segments = transcription_data['segments']

            # otherwise, stop the process
            else:
                logger.debug('No transcription segments were passed.')
                return False

            if transcription_segments:
                self.write_srt(transcription_segments, srt_file_path)
                return srt_file_path

        return False

    def save_txt_from_transcription(self, txt_file_path=None, transcription_text=None,
                                    file_name=None, target_dir=None, transcription_data=None):
        '''
        Saves an txt file based on the transcription file.

        You can either pass the transcription text or the full transcription data. When both are passed,
        the transcription_text will be used.

        :param txt_file_path:
        :param transcription_text:
        :param file_name:
        :param target_dir:
        :param transcription_data:
        :return: False or txt_file_path
        '''

        # if no full path was passed
        if txt_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                txt_file_path = os.path.join(target_dir, file_name + '.txt')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if txt_file_path and txt_file_path != '':

            # if the transcription segments were not passed
            # try to find them in transcription_data (if that was passed too)
            if transcription_text is None and transcription_data and 'text' in transcription_data:
                transcription_text = transcription_data['text']

            # otherwise, stop the process
            else:
                logger.debug('No transcription text was passed.')
                return False

            # save the text in the txt file
            if transcription_text:
                with open(txt_file_path, 'w', encoding="utf-8") as txt_outfile:
                    txt_outfile.write(transcription_text)

                return txt_file_path

        return False

    # TIMELINE METHODS

    def get_timeline_transcriptions(self, timeline_name=None, project_name=None):
        '''
        Gets a list of all the transcriptions associated with a timeline
        :param timeline_name:
        :param project_name:
        :return:
        '''
        if timeline_name is None:
            return None

        # get all the transcription files associated with the timeline
        # by requesting the timeline setting named 'transcription_files'
        timeline_transcription_files = self.stAI.get_timeline_setting(project_name=project_name,
                                                                      timeline_name=timeline_name,
                                                                      setting_key='transcription_files')

        return timeline_transcription_files

    def get_transcription_to_timeline_link(self, transcription_file_path=None, timeline_name=None, project_name=None):
        '''
        Checks if a transcription linked with a timeline but also returns all the transcription files
        associated with that timeline

        :param transcription_file_path:
        :param timeline_name:
        :param project_name:
        :return: bool, timeline_transcription_files
        '''
        if transcription_file_path is None or timeline_name is None:
            return None

        # get all the transcription files associated with the timeline
        timeline_transcription_files = self.get_timeline_transcriptions(timeline_name=timeline_name,
                                                                        project_name=project_name)

        # if the settings of our timeline were found
        if timeline_transcription_files and timeline_transcription_files is not None:

            # check if the transcription is linked to the timeline
            if transcription_file_path in timeline_transcription_files:
                return True, timeline_transcription_files
            # if it's not just say so
            else:
                return False, timeline_transcription_files

        # give None and an empty transcription list
        return None, []

    def link_transcription_to_timeline(self, transcription_file_path=None, timeline_name=None, link=None,
                                       project_name=None):
        '''
        Links transcription files to timelines.
        If the link parameter isn't passed, it first checks if the transcription is linked and then toggles the link
        If no timeline_name is passed, it tries to use the timeline of the currently opened timeline in Resolve

        :param transcription_file_path:
        :param timeline_name:
        :param link: If no link is passed, it will toggle the link
        :return:
        '''

        # abort if no transcript file was passed
        if transcription_file_path is None:
            logger.error('No transcript path was passed. Unable to link transcript to timeline.')
            return None

        # if no timeline name was passed
        if timeline_name is None:

            # try to get the timeline currently opened in Resolve
            # global current_timeline
            if NLE.current_timeline and NLE.current_timeline is not None and 'name' in NLE.current_timeline:

                # and use it as timeline name
                timeline_name = NLE.current_timeline['name']


            else:
                logger.error('No timeline was passed. Unable to link transcript to timeline.')
                return None

        # if no project was passed
        if project_name is None:

            # try to get the project opened in Resolve
            if NLE.current_project and NLE.current_project is not None:

                # use that as a project name
                project_name = NLE.current_project

            else:
                logger.error('No project name was passed. Unable to link transcript to timeline.')

        # check the if the transcript is currently linked with the transcription
        current_link, timeline_transcriptions = self.get_transcription_to_timeline_link(
            transcription_file_path=transcription_file_path,
            timeline_name=timeline_name, project_name=project_name)

        # if the link action wasn't passed, decide here whether to link or unlink
        # basically toggle between true or false by choosing the opposite of whether the current_link is true or false
        if link is None and current_link is True:
            link = False
        elif link is None and current_link is not None and current_link is False:
            link = True
        else:
            link = True

        # now create the link if we should
        if link:

            logger.info('Linking to current timeline: {}'.format(timeline_name))

            # but only create it if it isn't in there yet
            if transcription_file_path not in timeline_transcriptions:
                timeline_transcriptions.append(transcription_file_path)

        # or remove the link if we shouldn't
        else:
            logger.info('Unlinking from current timeline: {}'.format(timeline_name))

            # but only remove it if it is in there currently
            if transcription_file_path in timeline_transcriptions:
                timeline_transcriptions.remove(transcription_file_path)

        # if we made it so far, get all the project settings
        self.stAI.project_settings = self.stAI.get_project_settings(project_name=project_name)

        # if there isn't a timeline dict in the project settings, create one
        if 'timelines' not in self.stAI.project_settings:
            self.stAI.project_settings['timelines'] = {}

        # if there isn't a reference to this timeline in the timelines dict
        # add one, including the transcription files list
        if timeline_name not in self.stAI.project_settings['timelines']:
            self.stAI.project_settings['timelines'][timeline_name] = {'transcription_files': []}

        # overwrite the transcription file settings of the timeline
        # within the timelines project settings of this project
        self.stAI.project_settings['timelines'][timeline_name]['transcription_files'] \
            = timeline_transcriptions

        # print(json.dumps(self.stAI.project_settings, indent=4))

        self.stAI.save_project_settings(project_name=project_name,
                                        project_settings=self.stAI.project_settings)

        return link

    def is_UI_obj_available(self, toolkit_UI_obj=None):

        # if there's no toolkit_UI_obj in the object or one hasn't been passed, abort
        if toolkit_UI_obj is None and self.toolkit_UI_obj is None:
            return False
        # if there was a toolkit_UI_obj passed, update the one in the object
        elif toolkit_UI_obj is not None:
            self.toolkit_UI_obj = toolkit_UI_obj
            return True
        # if there simply is a self.toolkit_UI_obj just return True
        else:
            return True

    # RESOLVE SPECIFIC METHODS

    def resolve_disable(self):
        '''
        This function is used to disable the resolve API
        The polling thread will continue to run, but will not poll for data until the resolve API is re-enabled
        '''

        # set the resolve object to None
        self.resolve_api = None

        # set the disable resolve API flag to True
        self.disable_resolve_api = True

        # force the NLE object to None
        NLE.resolve = None
        NLE.reset_all()

        # trigger resolve changed
        self.on_resolve('resolve_changed')

    def resolve_enable(self):
        '''
        This function is used to enable the resolve API
        '''

        # initialize a resolve object
        if not self.resolve_api or self.resolve_api is None:
            self.resolve_api = MotsResolve(logger=logger)

        self.disable_resolve_api = False

        if not self.polling_resolve:
            logger.debug('Resolve polling thread not detected, starting one now')

            # start the resolve thread
            # with this, resolve should be constantly polled for data
            self.poll_resolve_thread()

    def calculate_sec_to_resolve_timecode(self, seconds=0):
        # global resolve
        if NLE.resolve:

            # poll resolve for some info
            # @todo avoid polling resolve for this info and use the existing current_timeline_fps
            #   and current_timeline_startTC
            resolve_data = self.resolve_api.get_resolve_data()

            # get the framerate of the current timeline
            timeline_fps = resolve_data['currentTimelineFPS']

            if timeline_fps is None:
                return False

            # get the start timecode of the current timeline
            timeline_start_tc = resolve_data['currentTimeline']['startTC']

            # initialize the timecode object for the start tc
            timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

            # only do timecode math if seconds > 0
            if seconds > 0:

                # init the timecode object based on the passed seconds
                tc_from_seconds = Timecode(timeline_fps, start_seconds=float(seconds))

                # calculate the new timecode
                new_timeline_tc = timeline_start_tc + tc_from_seconds

            # otherwise use the timeline start tc
            else:
                new_timeline_tc = timeline_start_tc

            return new_timeline_tc

        else:
            return False

    def transcription_has_timecode_data(self, transcription_data=None, transcription_file_path=None):
        '''
        This function checks if the passed transcription data or path has timecode data
        :param transcription_data: The transcription data to check
        :param transcription_file_path: The path to the transcription file to check
        :return: [timeline_fps, timeline_start_tc] if the transcription data has timecode data,
                False if it doesn't, None if the transcription data or path is invalid
        '''

        # if the transcription data isn't passed, try to get it from the path
        if transcription_data is None and transcription_file_path is not None:
            transcription_data = self.get_transcription_file_data(transcription_file_path=transcription_file_path)

        # if the transcription data is still None, return False
        if transcription_data is None:
            logger.debug('Transcription not found or invalid.')
            return None

        # if the transcription data has a timeline_fps and start_tc, return True
        if isinstance(transcription_data, dict) and \
                'timeline_fps' in transcription_data and 'timeline_start_tc' in transcription_data:
            return transcription_data['timeline_fps'], transcription_data['timeline_start_tc']

        # otherwise return False
        logger.debug('Transcription does not contain timeline_fps or timeline_start_tc')
        return False

    def convert_sec_to_transcription_timecode(self, seconds=0, transcription_data=None, transcription_file_path=None,
                                              offset_with_start_tc=True, return_timecode_data=False):
        '''
        This function converts the passed number of seconds to timecode,
        using the framerate and start_tc found in the transcription file/data

        :param seconds: The number of seconds to convert
        :param transcription_data: The transcription data to use (ignored if transcription_file_path is passed)
        :param transcription_file_path: The path to the transcription file to use
        :param offset_with_start_tc: Whether or not to offset the timecode with the transcription file's start_tc
        :param return_timecode_data: Whether or not to return the timecode data as well as the timecode string
        :return: The timecode string, a list with the timecode string and timecode data (timecode, fps, start_tc),
                False if the transcription data contains no timeline_fps,
                or None if something else went wrong
        '''

        # get the timecode data from the transcription
        timecode_data = self.transcription_has_timecode_data(transcription_data=transcription_data,
                                                             transcription_file_path=transcription_file_path)

        # if False or None was returned, pass them
        if timecode_data is False or timecode_data is None:
            return timecode_data

        if (isinstance(timecode_data, list) or isinstance(timecode_data, tuple)) and len(timecode_data) == 2:

            # use try for the timecode conversion,
            # in case the framerate or timeline_start_tc are invalid
            try:
                # get the framerate timecode_data
                timeline_fps = timecode_data[0]

                # convert the seconds to timecode
                timecode = Timecode(timeline_fps, start_seconds=float(seconds))

                # get the start timecode from the transcription file
                timeline_start_tc = Timecode(timeline_fps, timecode_data[1])

                # if we need to offset the timecode with the transcription file's start_tc
                if offset_with_start_tc:

                    # only offset if timecode is different than 00:00:00:00
                    if timeline_start_tc != '00:00:00:00':
                        # calculate the new timecode
                        timecode = timeline_start_tc + timecode

                # if we need to return the timecode data as well
                if return_timecode_data:
                    return timecode, timeline_fps, timeline_start_tc

                return timecode

            except:
                logger.debug('Something went wrong converting the seconds to timecode', exc_info=True)
                return None

        # if all fails, return None
        return None

    def convert_transcription_timecode_to_sec(self, timecode: str,
                                              transcription_data=None, transcription_file_path=None,
                                              offset_with_start_tc=True, return_timecode_data=False,
                                              timecode_data=None):
        '''
        This function converts the passed timecode to seconds,
        using the framerate and start_tc found in the transcription file/data

        :param timecode: The timecode to convert (must be a string)
        :param transcription_data: The transcription data to use (ignored if transcription_file_path is passed)
        :param transcription_file_path: The path to the transcription file to use
        :param offset_with_start_tc: Whether or not to offset the timecode with the transcription file's start_tc
        :param return_timecode_data: Whether or not to return the timecode data as well as the timecode string
        :return: The number of seconds, a list with the number of seconds and timecode data (seconds, fps, start_tc),
                False if the transcription data contains no timeline_fps, or None if something else went wrong
        '''

        # get the timecode data from the transcription
        if timecode_data is None:
            timecode_data = self.transcription_has_timecode_data(transcription_data=transcription_data,
                                                                 transcription_file_path=transcription_file_path)

        # if False or None was returned, pass them
        if timecode_data is False or timecode_data is None:
            return timecode_data

        if (isinstance(timecode_data, list) or isinstance(timecode_data, tuple)) and len(timecode_data) == 2:

            # stop if the timecode data tuple is useless
            if timecode_data == (None, None):
                return None

            seconds = None

            # use try for the timecode conversion,
            # in case the framerate or timeline_start_tc are invalid
            try:
                # get the framerate timecode_data
                timeline_fps = timecode_data[0]

                # initialize the timecode object
                timecode = Timecode(timeline_fps, timecode)

                # get the start timecode from the transcription file
                timeline_start_tc = timecode_data[1]

                # initialize the timecode object for the start tc
                timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

                # if we need to offset the timecode with the transcription file's start_tc
                if offset_with_start_tc:

                    # if the timecode is the same as the start timecode, return 0.0 to avoid errors
                    if timeline_start_tc == timecode:
                        seconds = 0

                    # only offset if timecode is different than 00:00:00:00
                    if timeline_start_tc != '00:00:00:00' and seconds is None:
                        # calculate the new timecode
                        timecode = timecode - timeline_start_tc

                # convert the timecode to seconds by dividing the frames by the framerate
                # if it hasn't been calculated yet
                if seconds is None:
                    seconds = float(timecode.frames) / float(timeline_fps)

                # if we need to return the timecode data as well
                if return_timecode_data:
                    return seconds, timeline_fps, timeline_start_tc

                return seconds

            except:
                logger.debug('Something went wrong converting the timecode to seconds', exc_info=True)
                return None

    def calculate_resolve_timecode_to_sec(self, timecode=None, frames=None, framerate=None, start_tc=None):
        '''
        Calculates the seconds from a timecode or frames based on the current timeline's framerate

        :param timecode: The timecode to calculate the seconds from
        :param frames: The number of frames to calculate the seconds from
        :param frame rate: The framerate of the timeline in FPS
        :param start_tc: The start timecode of the timeline
        :return:
        '''

        if NLE.resolve:

            # poll resolve for some info
            # @todo avoid polling resolve for this info and use the existing current_timeline_fps
            #   and current_timeline_startTC
            resolve_data = self.resolve_api.get_resolve_data()

            # get the framerate of the current timeline
            # either from Resolve...
            if 'currentTimelineFPS' in resolve_data:
                timeline_fps = resolve_data['currentTimelineFPS']
            # ...from the passed framerate
            elif framerate is not None:
                timeline_fps = framerate
            # ...or abort
            else:
                logger.debug('No timeline framerate found. Aborting.')
                return None

            # get the start timecode of the current timeline
            if 'currentTimeline' in resolve_data and 'startTC' in resolve_data['currentTimeline']:
                timeline_start_tc = resolve_data['currentTimeline']['startTC']
            elif start_tc is not None:
                timeline_start_tc = start_tc
            else:
                timeline_start_tc = '00:00:00:00'

            # initialize the timecode object for the start tc
            timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

            # if no timecode was passed, try to get it from the NLE object
            if timecode is None and frames is None:
                timecode = NLE.current_tc

            # calculate the timecode from the passed frames
            if frames is not None:
                timecode = Timecode(framerate=timeline_fps, frames=frames)

            # if we still don't have a timecode, abort and return None
            if timecode is None:
                logger.debug('No timecode was passed. Aborting.')
                return None

            # initialize the timecode object for the passed timecode
            tc = Timecode(timeline_fps, timecode)

            # calculate the difference between the start tc and the passed tc
            tc_diff = tc - timeline_start_tc

            # calculate the seconds from the timecode frames
            tc_diff_seconds = tc_diff.frames / timeline_fps

            # return the seconds which is the previous calculated difference
            return tc_diff_seconds

        else:
            return None

    def go_to_time(self, seconds=0):

        if NLE.resolve:
            new_timeline_tc = self.calculate_sec_to_resolve_timecode(seconds)

            # move playhead in resolve
            self.resolve_api.set_resolve_tc(str(new_timeline_tc))

    def save_markers_to_project_settings(self):
        '''
        Saves the markers of the current timeline to the project settings
        :return:
        '''

        if NLE.current_project is not None and NLE.current_project != '' \
                and NLE.current_timeline is not None and NLE.current_timeline != '' \
                and type(NLE.current_timeline) == dict and 'name' in NLE.current_timeline \
                and 'markers' in NLE.current_timeline:

            project_name = NLE.current_project
            timeline_name = NLE.current_timeline['name']
            markers = NLE.current_timeline['markers']

            #  get all the project settings
            self.stAI.project_settings = self.stAI.get_project_settings(project_name=project_name)

            # if there isn't a timeline dict in the project settings, create one
            if 'timelines' not in self.stAI.project_settings:
                self.stAI.project_settings['timelines'] = {}

            # if there isn't a reference to this timeline in the timelines dict
            # add one, including the markers list
            if timeline_name not in self.stAI.project_settings['timelines']:
                self.stAI.project_settings['timelines'][timeline_name] = {'markers': []}

            # overwrite the transcription file settings of the timeline
            # within the timelines project settings of this project
            self.stAI.project_settings['timelines'][timeline_name]['markers'] \
                = markers

            # print(json.dumps(self.stAI.project_settings, indent=4))

            self.stAI.save_project_settings(project_name=project_name,
                                            project_settings=self.stAI.project_settings)

    def on_resolve(self, event_name):
        '''
        Process resolve events
        :param event_name:
        :return:
        '''

        # FOR NOW WE WILL KEEP THE UI UPDATES HERE AS WELL

        # when resolve connects / re-connects
        if event_name == 'resolve_changed':

            if self.is_UI_obj_available():
                # update the main window
                self.toolkit_UI_obj.update_main_window()

                # sync all the synced transcription windows
                self.toolkit_UI_obj.update_all_transcription_windows()

                # update the resolve buttons in the menu
                self.toolkit_UI_obj.UI_menus.toggle_resolve_buttons()

        # when the timeline has changed
        elif event_name == 'timeline_changed':

            # global current_timeline

            if NLE.current_timeline is not None and NLE.current_timeline != '' \
                    and type(NLE.current_timeline) == dict and 'name' in NLE.current_timeline:

                # get the transcription_paths linked with this timeline
                timeline_transcription_file_paths = self.get_timeline_transcriptions(
                    timeline_name=NLE.current_timeline['name'],
                    project_name=NLE.current_project
                )

                # close all the transcript windows that aren't linked with this timeline
                if self.stAI.get_app_setting('close_transcripts_on_timeline_change'):
                    if self.toolkit_UI_obj is not None:
                        self.toolkit_UI_obj.close_inactive_transcription_windows(timeline_transcription_file_paths)

                # and open a transcript window for each of them
                if timeline_transcription_file_paths \
                        and timeline_transcription_file_paths is not None \
                        and self.toolkit_UI_obj is not None:
                    for transcription_file_path in timeline_transcription_file_paths:
                        self.toolkit_UI_obj.open_transcription_window(transcription_file_path=transcription_file_path)

        # when the playhead has moved
        elif event_name == 'tc_changed':
            if self.toolkit_UI_obj is not None:
                # sync all the synced transcription windows
                self.toolkit_UI_obj.sync_all_transcription_windows()

        # when the timeline markers have changed
        elif event_name == 'timeline_markers_changed':

            # save the markers to the project settings
            self.save_markers_to_project_settings()

    def resolve_exists(self):
        '''
        Checks if Resolve API is available and connected
        :return:
        '''

        # global resolve

        if NLE.resolve:
            return True
        else:
            return False

    def poll_resolve_thread(self):
        '''
        This keeps resolve polling in a separate thread
        '''

        # don't start this if another thread is already running
        if self.polling_resolve:
            logger.debug('Resolve polling thread already running')
            return

        # wrap poll_resolve_data into a thread
        poll_resolve_thread = Thread(target=self.poll_resolve_data)

        # stop the thread when the main thread stops
        poll_resolve_thread.daemon = True

        # start the thread
        poll_resolve_thread.start()

    def poll_resolve_data(self):
        '''
        Polls resolve and returns either the data passed from resolve, or False if any exceptions occurred
        :return:
        '''

        # don't start this if another thread is already running
        if self.polling_resolve:
            logger.debug('Resolve polling thread already running')
            return

        # do this continuously
        while True:

            # keep updating the resolve_poll_num
            NLE.resolve_poll_num += 1

            polling_start_time = time.time()

            # make sure everyone knows that this loop is still running
            # (and implicitly the thread too)
            self.polling_resolve = True

            # try to poll resolve
            try:

                # check if the resolve api is not disabled
                if self.disable_resolve_api:
                    logger.debug('Resolve API disabled. Aborting Resolve API polling until re-enabled.')
                    self.polling_resolve = False

                    # execute this one more time to make sure all variables are set correctly
                    self.resolve_disable()

                    return None

                # also, check if the API module is available on this machine
                if not self.resolve_api.api_module_available:
                    logger.debug('Resolve API module not available on this machine. '
                                 'Aborting Resolve API polling until StoryToolkitAI restart.')
                    self.polling_resolve = False
                    return None

                # actual polling happens here
                resolve_data = self.resolve_api.get_resolve_data(silent=True)

                # for all the NLE variables related with resolve data,
                #  check if the data has changed and if so, update the NLE variable
                #  but if the polled data does not contain the key, also set the NLE variable to None
                #  also, if the global variable is not None and the polled data doesn't contain the key,
                #  set the global variable to None
                # also, make sure you trigger the on_resolve event if the data has changed

                # RESOLVE OBJECT CHANGE
                # if the resolve object has changed (for eg. from None to an object)
                try:
                    if type(NLE.resolve) != type(resolve_data['resolve']):

                        logger.debug('Resolve object changed from {} to {}.'
                                     .format(type(NLE.resolve), type(resolve_data['resolve'])))

                        # set the resolve object to whatever it is now
                        NLE.resolve = resolve_data['resolve']

                        # trigger the resolve_changed event
                        self.on_resolve('resolve_changed')

                        # if the resolve object is now None,
                        # reset all and skip the rest of the polling
                        if NLE.resolve is None:
                            self.on_resolve('project_changed')
                            self.on_resolve('timeline_changed')

                            NLE.reset_all()
                except:
                    import traceback
                    logger.debug('Fail detected in resolve object change check.')
                    logger.debug(traceback.format_exc())
                    continue

                # RESOLVE TIMELINE NAME CHANGE
                # if the current project was already set and now it's no longer set in the polled data
                # or if the current project has changed
                try:
                    if (NLE.current_project is not None and 'currentProject' not in resolve_data) \
                            or NLE.current_project != resolve_data['currentProject']:
                        # logger.debug('Current project changed from {} to {}.'
                        #             .format(NLE.current_project, resolve_data['currentProject']))

                        # set the current project to whatever it is now
                        # but if the polled data doesn't contain the currentProject key, set it to None
                        NLE.current_project = resolve_data[
                            'currentProject'] if 'currentProject' in resolve_data else None

                        # trigger the project_changed event
                        self.on_resolve('project_changed')

                except:
                    import traceback
                    logger.debug('Fail detected in resolve project change check.')
                    logger.debug(traceback.format_exc())
                    continue

                # if the current timeline was already set and now it's no longer set in the polled data
                # or if the current timeline has changed
                try:
                    if (NLE.current_timeline is not None and 'currentTimeline' not in resolve_data) \
                            or NLE.current_timeline != resolve_data['currentTimeline']:

                        # logger.debug('Current timeline changed from {} to {}.'
                        #             .format(NLE.current_timeline, resolve_data['currentTimeline']))

                        # because we only want to trigger the timeline_changed event if the name of the timeline has changed
                        # but resolve_data['currentTimeline'] contains the entire timeline object,
                        # including markers and other data that may have changed,
                        # we need to focus on the name of the timeline

                        # but first, if the polled data doesn't contain the currentTimeline key
                        # yet the NLE.current_timeline was set before
                        if NLE.current_timeline is not None and 'currentTimeline' not in resolve_data:

                            # logger.debug('Current timeline changed from {} to None.'.format(NLE.current_timeline))

                            # set the current timeline to None
                            NLE.current_timeline = None

                            # and trigger the timeline_changed event
                            self.on_resolve('timeline_changed')

                        # if the polled data contains the currentTimeline key
                        elif 'currentTimeline' in resolve_data \
                                and (type(NLE.current_timeline) != type(resolve_data['currentTimeline']) \
                                     or ('name' in NLE.current_timeline and not 'name' in resolve_data[
                                    'currentTimeline']) \
                                     or ('name' in resolve_data[
                                    'currentTimeline'] and not 'name' in NLE.current_timeline) \
                                     or (NLE.current_timeline['name'] != resolve_data['currentTimeline']['name'])):

                            # logger.debug('Current timeline changed from {} to {}.'
                            #             .format(NLE.current_timeline, resolve_data['currentTimeline']))

                            # set the current timeline to whatever it is now
                            NLE.current_timeline = resolve_data['currentTimeline'] \
                                if 'currentTimeline' in resolve_data else None

                            # and trigger the timeline_changed event
                            self.on_resolve('timeline_changed')

                        # if the polled data contains the currentTimeline key, but the name of the timeline hasn't changed
                        else:
                            # set the current timeline to whatever it is now
                            # but don't trigger the timeline_changed event
                            NLE.current_timeline = resolve_data['currentTimeline'] \
                                if 'currentTimeline' in resolve_data else None

                except:
                    import traceback
                    logger.debug('Fail detected in resolve timeline change check.')
                    logger.debug(traceback.format_exc())
                    continue

                # did the markers change?
                # (this only matters if the current timeline is not None
                # and if the current timeline has markers)
                if resolve_data is not None and type(resolve_data) is dict \
                        and 'currentTimeline' in resolve_data \
                        and type(resolve_data['currentTimeline']) is dict \
                        and 'markers' in resolve_data['currentTimeline']:

                    # first compare the types
                    if type(NLE.current_timeline_markers) != type(resolve_data['currentTimeline']['markers']):
                        # if the types are different, then the markers have changed
                        self.on_resolve('timeline_markers_changed')

                        NLE.current_timeline_markers = resolve_data['currentTimeline']['markers']

                    # also do a key compare only for speed
                    elif set(NLE.current_timeline_markers.keys()) != set(
                            resolve_data['currentTimeline']['markers'].keys()):
                        # if the keys are different, then the markers have changed
                        self.on_resolve('timeline_markers_changed')

                        NLE.current_timeline_markers = resolve_data['currentTimeline']['markers']

                    # but if the marker keys are the same do a deeper compare
                    elif NLE.current_timeline_markers != resolve_data['currentTimeline']['markers']:
                        # if the keys are the same, but the values are different, then the markers have changed
                        self.on_resolve('timeline_markers_changed')

                        NLE.current_timeline_markers = resolve_data['currentTimeline']['markers']

                else:
                    NLE.current_timeline_markers = None

                #  updates the currentBin
                if (NLE.current_bin is not None and NLE.current_bin != '' and 'currentBin' not in resolve_data) \
                        or NLE.current_bin != resolve_data['currentBin']:
                    NLE.current_bin = resolve_data['currentBin'] if 'currentBin' in resolve_data else ''

                    self.on_resolve('bin_changed')
                    # logger.info("Current Bin: {}".format(NLE.current_bin))

                # update current playhead timecode
                if (NLE.current_tc is not None and 'currentTC' not in resolve_data) \
                        or NLE.current_tc != resolve_data['currentTC']:
                    NLE.current_tc = resolve_data['currentTC']
                    self.on_resolve('tc_changed')

                # update current playhead timecode
                if (NLE.current_timeline_fps is not None and 'currentTC' not in resolve_data) \
                        or NLE.current_timeline_fps != resolve_data['currentTimelineFPS']:
                    NLE.current_timeline_fps = resolve_data['currentTimelineFPS']
                    self.on_resolve('fps_changed')

                # was there a previous error?
                if NLE.resolve is not None and NLE.resolve_error > 0:
                    # first let the user know that the connection is back on
                    logger.warning("Resolve connection re-established.")

                    # reset the error counter
                    NLE.resolve_error = 0

                elif NLE.resolve is None:
                    NLE.resolve_error += 1

            # if an exception is thrown while trying to work with Resolve, don't crash, but continue to try to poll
            except:

                import traceback
                print(traceback.format_exc())

                # count the number of errors
                NLE.resolve_error += 1

                # resolve is now None in the global variable
                # resolve = None

                # return False

            # how often do we poll resolve?
            polling_interval = 500

            # if any errors occurred
            if NLE.resolve_error:

                # let the user know that there's an error, and throttle the polling_interval

                # after 15+ errors, deduce that Resolve will not be started this session, so stop polling
                if NLE.resolve_error > 15:
                    logger.warning("Resolve not reachable after 15 tries. "
                                   "Disabling Resolve API polling until tool restart.")

                    polling_interval = None

                # after 10+ tries, assume the user is no longer paying attention and reduce the frequency of tries
                elif NLE.resolve_error > 10:

                    # only show this error one more time
                    if NLE.resolve_error == 11:
                        logger.warning('Resolve is still not reachable. '
                                       'Now retrying every 15 seconds only a few more times.')

                    # and increase the polling interval to 30 seconds
                    polling_interval = 15000

                # if the error has been triggered more than 5 times, do this
                elif NLE.resolve_error > 5:

                    if NLE.resolve_error == 11:
                        logger.warning('Resolve is still not reachable. Now retrying every 5 seconds or so.')

                    # increase the polling interval to 5 seconds
                    polling_interval = 5000

                else:
                    if NLE.resolve_error == 1:
                        logger.warning('Resolve is not reachable. Retrying every few seconds.')

                    # increase the polling interval to 1 second
                    polling_interval = 1000

                # calculate the time that has passed since the polling started
                polling_time = time.time() - polling_start_time

                # if the polling time takes longer than 1 second, throttle the polling interval
                if polling_interval is not None and polling_time > 1:
                    polling_interval = polling_interval + polling_time

                # logger.debug('Polling time: {} seconds'.format(round(time.time() - polling_start_time), 2))

            if polling_interval is None:
                self.polling_resolve = False
                return False

            # take a short break before continuing the loop
            time.sleep(polling_interval / 1000)

    def resolve_check_timeline(self, resolve_data, toolkit_UI_obj):
        '''
        This checks if a timeline is available
        :param resolve:
        :return: bool
        '''

        # trigger warning if there is no current timeline
        if resolve_data['currentTimeline'] is None:
            toolkit_UI_obj.notify_via_messagebox(
                message='Timeline not available. Make sure that you\'ve opened a Timeline in Resolve.',
                type='warning')
            return False

        else:
            return True

    def execute_operation(self, operation, toolkit_UI_obj):
        if not operation or operation == '':
            return False

        stAI = self.stAI

        # get info from resolve for later
        resolve_data = self.resolve_api.get_resolve_data()

        # copy markers operation
        if operation == 'copy_markers_timeline_to_clip' or operation == 'copy_markers_clip_to_timeline':

            # set source and destination depending on the operation
            if operation == 'copy_markers_timeline_to_clip':
                source = 'timeline'
                destination = 'clip'

            elif operation == 'copy_markers_clip_to_timeline':
                source = 'clip'
                destination = 'timeline'

            # this else will never be triggered but let's leave it here for safety for now
            else:
                return False

            # trigger warning and stop if there is no current timeline
            if not self.resolve_check_timeline(resolve_data, toolkit_UI_obj):
                return False

            # trigger warning and stop if there are no bin clips
            if resolve_data['binClips'] is None:
                toolkit_UI_obj.notify_via_messagebox(
                    message='Bin clips not available. Make sure that a bin is opened in Resolve.\n\n'
                            'This doesn\'t work if multiple bins or smart bins are selected due to API.',
                    type='warning')
                return False

            # execute operation without asking for any prompts
            # this will delete the existing clip/timeline destination markers,
            # but the user can undo the operation from Resolve
            return self.resolve_api.copy_markers(source, destination,
                                                 resolve_data['currentTimeline']['name'],
                                                 resolve_data['currentTimeline']['name'],
                                                 True)

        # render marker operation
        elif operation == 'render_markers_to_stills' or operation == 'render_markers_to_clips':

            # ask user for marker color
            # or what the marker name starts with

            # but first make a list of all the available marker colors based on the timeline markers
            current_timeline_marker_colors = []
            if self.resolve_check_timeline(resolve_data, toolkit_UI_obj) and \
                    NLE.current_timeline and 'markers' in NLE.current_timeline:
                # take each marker from timeline and get its color
                # but also add a an empty string to the list to allow the user to render all markers
                current_timeline_marker_colors = [' '] + sorted(
                    list(set([NLE.current_timeline['markers'][marker]['color']
                              for marker in NLE.current_timeline['markers']])))

            # if no markers exist, cancel operation and let the user know that there are no markers to render
            marker_color = None
            starts_with = None
            if current_timeline_marker_colors:
                # marker_color = simpledialog.askstring(title="Markers Color",
                #                                      prompt="What color markers should we render?\n\n"
                #                                             "These are the marker colors on the current timeline:\n"
                #                                             + ", ".join(current_timeline_marker_colors))

                # create a list of widgets for the input dialogue
                input_widgets = [
                    {'name': 'starts_with', 'label': 'Starts With:', 'type': 'entry', 'default_value': ''},
                    {'name': 'color', 'label': 'Color:', 'type': 'option_menu', 'default_value': 'Blue',
                     'options': current_timeline_marker_colors}
                ]

                # then we call the ask_dialogue function
                user_input = self.toolkit_UI_obj.AskDialog(title='Markers to Render',
                                                           input_widgets=input_widgets,
                                                           parent=self.toolkit_UI_obj.root
                                                           ).value()

                # if the user didn't cancel the operation
                if user_input:
                    starts_with = user_input['starts_with'] if user_input['starts_with'] else None
                    marker_color = user_input['color'] if user_input['color'] != ' ' else None

            else:
                no_markers_alert = 'The timeline doesn\'t contain any markers'
                logger.warning(no_markers_alert)
                return False

            if not marker_color and not starts_with:
                logger.debug("User canceled Resolve render operation by mentioning which markers.")
                return False

            if marker_color and marker_color not in current_timeline_marker_colors:
                toolkit_UI_obj.notify_via_messagebox(title='Unavailable marker color',
                                                     message='The marker color you\'ve entered doesn\'t exist on the timeline.',
                                                     message_log="Aborting. User entered a marker color that doesn't exist on the timeline.",
                                                     type='error'
                                                     )

                return False

            render_target_dir = toolkit_UI_obj.ask_for_target_dir()

            if not render_target_dir or render_target_dir == '':
                logger.debug("User canceled Resolve render operation")
                return False

            if operation == 'render_markers_to_stills':
                stills = True
                render = True
                render_preset = "Still_TIFF"
            else:
                stills = False
                render = False
                render_preset = False

            self.resolve_api.render_markers(marker_color, render_target_dir, False, stills, render, render_preset,
                                            starts_with=starts_with)

        return False
