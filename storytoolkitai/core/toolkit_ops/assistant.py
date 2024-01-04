import openai
import tiktoken
import hashlib
import time
from openai import OpenAI
import json
import copy

from storytoolkitai.core.logger import logger


class ToolkitAssistant:
    """
    This is the main class for the assistant
    """

    def __init__(self, toolkit_ops_obj):
        # load the toolkit ops object
        self.toolkit_ops_obj = toolkit_ops_obj

        # load the stAI object
        self.stAI = self.toolkit_ops_obj.stAI

        # load the toolkit UI object
        self.toolkit_UI_obj = self.toolkit_ops_obj.toolkit_UI_obj

    @staticmethod
    def copy_context_and_chat(assistant_from, assistant_to):
        """
        This function is used to copy the context and chat history from one assistant to another
        """

        # first, copy the context
        assistant_to.add_context(assistant_from.context)

        # then copy the chat history
        assistant_to.chat_history = copy.deepcopy(assistant_from.chat_history)


class ChatGPT(ToolkitAssistant):
    """
    This is a class that is used to create an OpenAI GPT-based assistant
    It should be instantiated for each assistant and then used to pass queries
    and results between UI and whatever assistant model / API we're using
    """

    def __init__(self, model_provider, model_name, **kwargs):

        super().__init__(toolkit_ops_obj=kwargs.get('toolkit_ops_obj', None))

        # save the model provider for internal use
        self.model_provider = model_provider

        # get the model from the kwargs or from the config file if not passed
        self.model_name = model_name

        # generate a unique ID for the assistant
        self._assistant_id = hashlib.md5((str(self.model_name) + str(time.time)).encode('utf-8')).hexdigest()

        # store the number of tokens used for the assistant
        # this is a list containing the in and out tokens [in, out]
        self._tokens_used = [0, 0]

        # the price per 1000 tokens
        # this should be a list containing the price for in and out tokens and the currency
        # for eg: [0.01, 0.03, 'USD']
        self._model_price = self.model_price

        # start the chat history, if none was passed, then start with an empty list
        self.chat_history = list() if kwargs.get('chat_history', None) is None else kwargs.get('chat_history', None)

        # the system initial system message will be set either from the kwargs or from the config
        # this will be used even when the user resets the assistant
        self.initial_system_message = kwargs.get('system_message', DEFAULT_SYSTEM_MESSAGE)

        # set the system message (will be added to the chat history too)
        self.set_system(self.initial_system_message)

        # to keep track of the context
        self.context = kwargs.get('context', None)

        # and the index of the context in the chat history
        self.context_idx = None

        # keep track of the index of the last assistant message in the chat history
        self._last_assistant_message_idx = None

        if self.context is not None:
            # add the context to the chat history
            self.add_context(self.context)

        # get the API key from the config
        self.api_key \
            = self.stAI.get_app_setting(setting_name='openai_api_key', default_if_none=None)

    def reset(self):
        """
        This function is used to reset the assistant, by clearing the chat history,
        then adding the initial system and the context (if it exists)
        """

        # just reset the chat history to the initial system message
        self.chat_history = [{"role": "system", "content": self.initial_system_message}]

        # also re-add the context if it exists
        if self.context is not None:
            self.context_idx = len(self.chat_history)

            # add the context to the chat history
            self.chat_history.append({"role": "user", "content": self.context})

    def set_system(self, system_message):

        # check so that the initial system message is not empty
        if not system_message:

            # just return false if the initial system message is empty
            logger.error('Could not change system message - no message was passed.')
            return False

        # first, make sure this is the first message in the chat history
        # by removing any other system messages
        system_message_idx = []
        for i, message in enumerate(self.chat_history):

            # if the role is system, then we've found the system message
            if message['role'] == 'system':

                # remember the index of the system message
                # we can't do it here since we're iterating over the list
                system_message_idx.append(i)

        # if we found any system messages, remove them
        if system_message_idx:
            for i in system_message_idx:
                self.chat_history.pop(i)

        # and now re-add the new system message on top
        self.chat_history.insert(0, {"role": "system", "content": system_message})

        return True

    def add_context(self, context):
        """
        This function is used to add context to the assistant by introducing a message with the context string,
        right after the initial system message
        """

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
            # find the system message in the chat history so that we can add the context right after it
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

    def delete_context(self):

        # just remove any context that might exist
        if self.context is not None and self.context_idx is not None:
            # remove the context from the chat history
            self.chat_history.pop(self.context_idx)

            # remember that we've removed the context
            self.context = None
            self.context_idx = None

            logger.debug('Removed context from the chat history.')

    def calculate_history_tokens(self):
        """
        This calculates the amount of tokens used by the assistant
        on each query taken into consideration the current chat_history (but without the query itself)
        """

        # use tiktoken to calculate the number of tokens used by the assistant
        # encoding = tiktoken.get_encoding("cl100k_base")
        encoding = tiktoken.encoding_for_model(self.model_name)

        # turn the chat history into a string take the 'content' field from each message
        chat_history_str = ' '.join([message['content'] for message in self.chat_history])

        # the number of tokens used for the chat history
        tokens = len(encoding.encode(chat_history_str))

        return tokens

    def add_usage(self, *, tokens_in=0, tokens_out=0):
        """
        This function is used to add usage to the assistant totals so that we can keep track of the total usage
        since the tool was started.
        :param tokens_in: the number of tokens used for the prompt (or input tokens)
        :param tokens_out: the number of tokens used for the completion (or output tokens)
        """

        # add the usage for the current assistant item
        self._tokens_used[0] += tokens_in
        self._tokens_used[1] += tokens_out

        # but also keep track of the total usage of this model since the tool was started
        # we use the assistant id but also the model name and provider
        # so that we can calculate the usage correctly per model type

        # tokens in
        self.stAI.update_statistics(
            'assistant_usage__{}__{}_in'.format(self.model_provider, self.model_name),
            self._tokens_used[0]
        )

        # tokens out
        self.stAI.update_statistics(
            'assistant_usage__{}__{}_out'.format(self.model_provider, self.model_name),
            self._tokens_used[1]
        )

        # print(self.stAI.statistics)

    def send_query(self, content, settings=None, temp_context=None, save_to_history=True):
        """
        This function is used to send a query to the assistant
        :param content: the content of the query
        :param settings: the settings for the query
        :param temp_context: a temporary context that will be used for this query only (and then discarded)
        :param save_to_history: if True, the query will be saved to the assistant chat history
        """

        # the query should always contain the role and the content
        # the role should be either user, system or assistant
        # in this case, since we're sending a query, the role should be user

        # make sure that the settings are a dict
        if settings is None:
            settings = dict()

        # set an empty function for the context reset
        def context_reset():
            return

        # if the temp_context was set, we're going to use it to replace the existing context, but only for this query
        if temp_context is not None:

            # save the current context
            current_context = self.context

            # set the context reset function
            def context_reset():
                # reset the context
                self.delete_context()
                if current_context:
                    self.add_context(current_context)

            # add the temp context
            self.add_context(temp_context)

        query = {"role": "user", "content": content}

        # create the chat history if it doesn't exist
        if self.chat_history is None:
            self.chat_history = list()

        # create a copy of the chat history so that we can send it to the assistant without affecting the original
        chat_history = copy.deepcopy(self.chat_history)

        # add the query to the function chat history
        chat_history.append(query)

        # add the query to the assistant chat history (but only if it's not empty)
        if save_to_history:
            self.chat_history.append(query)

        # now send the query to the assistant
        try:

            client = OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model=self.model_name,
                messages=chat_history,
                temperature=settings.get('temperature', 1),
                max_tokens=settings.get('max_length', 256),
                top_p=settings.get('top_p', 1),
                frequency_penalty=settings.get('frequency_penalty', 0),
                presence_penalty=settings.get('presence_penalty', 0),
                timeout=settings.get('timeout', 30),
            )

            # reset the context
            context_reset()

        except openai.AuthenticationError as e:

            error_message = 'OpenAI API key might invalid. Please check your OpenAI Key in the preferences window.'

            logger.debug('OpenAI API key is invalid. Please check your key in the preferences window.')

            # reset the context
            context_reset()

            return error_message, chat_history

        except Exception as e:
            logger.debug('Error sending query to ChatGPT: ', exc_info=True)

            context_reset()

            return str(e) + "\nI'm sorry, I'm having trouble connecting to OpenAI right now. " \
                            "Please check the logs or try again later.", chat_history

        result = ''

        for choice in response.choices:
            result += choice.message.content

            # add the result to the chat history
            if save_to_history:
                self.chat_history.append({"role": "assistant", "content": result})

                # keep track of the index of the last assistant message
                self._last_assistant_message_idx = len(self.chat_history) - 1

        # add the usage
        self.add_usage(tokens_in=response.usage.completion_tokens, tokens_out=response.usage.prompt_tokens)

        return result, chat_history

    @property
    def last_assistant_message_idx(self):
        return self._last_assistant_message_idx

    @property
    def model_description(self):
        """
        This function returns the description of the model which should be the human readable name
        """

        try:
            return LLM_AVAILABLE_MODELS[self.model_provider][self.model_name]['description']

        except KeyError:
            return '{} (unknown model)'.format(self.model_name)

    @property
    def model_price(self):

        try:
            price = self.info['price']

            # the price should be a dict with input, output and currency
            self._model_price = price['input'], price['output'], price['currency']
            return self._model_price

        except TypeError:
            # if the price is not a dict, then it's probably None
            # and it's probably already been logged in the info function
            return None

        except KeyError:
            logger.warning('Price for model {} unavailable or incomplete.'.format(self.model_name))
            return None

    @property
    def tokens_used(self):
        """
        This will return a list containing [tokens_in, tokens_out]
        in = input = prompt tokens
        out = output = completion tokens
        """
        return self._tokens_used

    @property
    def assistant_id(self):
        return self._assistant_id

    @property
    def info(self):
        try:
            return LLM_AVAILABLE_MODELS[self.model_provider][self.model_name]
        except KeyError:
            logger.warning('Info for model {} unavailable or incomplete.'.format(self.model_name))
            return None

    @property
    def available_models(self):
        return LLM_AVAILABLE_MODELS


class AssistantUtils:

    @staticmethod
    def assistant_handler(toolkit_ops_obj, model_provider, model_name, **kwargs):
        """
        This is the handler function for the assistant class and is used to instantiate the correct assistant class
        depending on the model provider and model name
        """

        try:

            # load the assistant class
            toolkit_assistant = LLM_AVAILABLE_MODELS[model_provider][model_name]['handler']

            # instantiate the assistant class and return it
            return toolkit_assistant(toolkit_ops_obj=toolkit_ops_obj,
                                     model_provider=model_provider,
                                     model_name=model_name,
                                     **kwargs)

        except KeyError:
            logger.error('Could not find assistant handler for model {} from provider {}.'
                         .format(model_name, model_provider))
            return None

    @staticmethod
    def assistant_available_models(provider=None):
        """
        This function returns the available assistant models for a given provider
        """

        if provider is not None:
            return list(LLM_AVAILABLE_MODELS[provider].keys())
        else:
            return []

    @staticmethod
    def assistant_available_providers():
        """
        This function returns the available assistant providers
        """

        return list(LLM_AVAILABLE_MODELS.keys())

    @staticmethod
    def parse_response_to_dict(assistant_response):
        """
        This trims the response and tries to parse it as a json
        """

        # do an initial blank space strip
        assistant_response = assistant_response.strip()

        # if the response starts with ``` or ```json and ends with ```
        if assistant_response.startswith('```json') and assistant_response.endswith('```'):
            # Remove the first occurrence of ```json and the last occurrence of ```
            assistant_response = assistant_response.replace('```json', '', 1)
            assistant_response = assistant_response[::-1].replace('```'[::-1], '', 1)[::-1]

        elif assistant_response.startswith('```') and assistant_response.endswith('```'):
            # Remove the first and last occurrence of ```
            assistant_response = assistant_response.replace('```', '', 1)
            assistant_response = assistant_response[::-1].replace('```'[::-1], '', 1)[::-1]

        # now try to parse it as a proper json
        try:
            assistant_response_dict = json.loads(assistant_response)
            return assistant_response_dict

        # if it's not a valid json, just continue
        except json.JSONDecodeError:
            logger.warning('The assistant response is not a valid json string.')
            return None

        except Exception as e:
            logger.error('Error while parsing the assistant response as json.', exc_info=True)
            return None


DEFAULT_SYSTEM_MESSAGE = ('You are an assistant film editor.\n'
                          'You are to provide succinct answers based strictly on the data presented in the current '
                          'conversation.\n'
                          'Important: if the answer is not found in the provided data '
                          'or current conversation, explicitly mention within your reply '
                          'that the answer is based on your own knowledge '
                          'and "not on the information provided".'
                          )

LLM_AVAILABLE_MODELS = {
    'OpenAI': {
        'gpt-4-1106-preview': {
            'description': 'GPT-4 Turbo (1106 preview)',
            'price': {'input': 0.01, 'output': 0.03, 'currency': 'USD'},
            'token_limit': 4096,
            'training_cutoff': '2023-04',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4': {
            'description': 'GPT-4',
            'price': {'input': 0.03, 'output': 0.06, 'currency': 'USD'},
            'token_limit': 8192,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-3.5-turbo-1106': {
            'description': 'GPT-3.5 Turbo 1106',
            'price': {'input': 0.001, 'output': 0.002, 'currency': 'USD'},
            'token_limit': 16385,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        }
    }
}