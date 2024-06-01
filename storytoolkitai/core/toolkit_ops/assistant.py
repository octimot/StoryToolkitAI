import openai
import tiktoken
import hashlib
import time
from openai import OpenAI
import json
import os
import copy
import requests
from pydantic import BaseModel, root_validator
from typing import Optional

from storytoolkitai.core.logger import logger
from storytoolkitai import USER_DATA_PATH


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


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class AssistantResponse(BaseModel):
    completion: Optional[str] = None
    usage: Optional[UsageInfo] = None
    error: Optional[str] = None
    error_code: Optional[int] = None

    @root_validator
    def check_completion_or_error(cls, values):
        """
        This makes sure that we either have a completion or an error
        """
        completion, error = values.get('completion'), values.get('error')
        if not completion and not error:
            raise ValueError('Either completion or error must be provided')
        return values


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

        # get the API key from the kwargs or config
        self.api_key \
            = kwargs.get('api_key', self.stAI.get_app_setting(setting_name='openai_api_key', default_if_none=None))

        self.base_url = kwargs.get('base_url', None)

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

    def calculate_history_tokens(self, messages=None, model=None):
        """
        This calculates the amount of tokens used by the assistant on each query
        taking into consideration the current chat_history (but without the new query itself)
        based on https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        """

        if model is None:
            model = self.model_name

        if messages is None:
            messages = self.chat_history

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.warning("Model name not found when calculating tokens. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")

        if model in {
            "gpt-3.5-turbo-0613",
            "gpt-3.5-turbo-16k-0613",
            "gpt-4-0314",
            "gpt-4-32k-0314",
            "gpt-4-0613",
            "gpt-4-32k-0613",
        }:
            tokens_per_message = 3
            tokens_per_name = 1

        elif model == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted

        elif "gpt-3.5-turbo" in model:
            logger.warning("Calculating tokens assuming gpt-3.5-turbo-0613, but gpt-3.5-turbo may update over time. ")
            return self.calculate_history_tokens(messages, model="gpt-3.5-turbo-0613")

        elif "gpt-4" in model:
            logger.warning("Calculating tokens assuming gpt-4-0613, but gpt-4 may update over time. ")
            return self.calculate_history_tokens(messages, model="gpt-4-0613")

        else:
            logger.error("Cannot accurately calculate tokens for model {}. Returning None.".format(model))
            return None

        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>

        return num_tokens

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

    def _request(self, chat_history, settings=None, **kwargs):

        # make sure that the settings are a dict
        if settings is None:
            settings = dict()

        # now send the query to the assistant
        try:

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

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

            result = ''
            for choice in response.choices:
                result += choice.message.content

                # add the result to the chat history
                if kwargs.get('save_to_history', True):
                    self.chat_history.append({"role": "assistant", "content": result})

                    # keep track of the index of the last assistant message
                    self._last_assistant_message_idx = len(self.chat_history) - 1

            # add the usage
            self.add_usage(tokens_in=response.usage.completion_tokens, tokens_out=response.usage.prompt_tokens)

            # wrap the response in an AssistantResponse object
            # so we can process it correctly
            return AssistantResponse(
                completion=result,
                usage=response.usage,
                error=None,
                error_code=None
            ), chat_history

        except openai.AuthenticationError as e:

            error = 'OpenAI API key is invalid. Please check your key in the preferences window ' \
                    'or in the additional_llm_models.json file.'

            logger.error(error)

            return AssistantResponse(
                error=error,
                error_code=401
            ), chat_history

        except Exception as e:
            logger.debug('Error sending query to ChatGPT: ', exc_info=True)

            error = str(e) + "There seems to be a problem with the connection to OpenAI. " \
                             "Please check the logs or try again later."

            return AssistantResponse(
                error=error
            ), chat_history

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

        # make the actual request
        result, chat_history = self._request(
            chat_history=chat_history, settings=settings, save_to_history=save_to_history)

        # reset the context
        context_reset()

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


class StModelSettings(BaseModel):
    temperature: int = 1
    max_length: int = 256
    top_p: int = 1
    frequency_penalty: int = 0
    presence_penalty: int = 0
    timeout: int = 30


class StAssistantRequest(BaseModel):
    messages: list
    model: str
    settings: StModelSettings


class StAssistant(ChatGPT):

    def __init__(self, model_provider, model_name, **kwargs):

        super().__init__(model_provider=model_provider, model_name=model_name, **kwargs)

        # get the API key from the kwargs or the config
        self.api_key \
            = kwargs.get('api_key', self.stAI.get_app_setting(setting_name='stai_api_key', default_if_none=None))

        # use the base_url from the config if it exists or the default one
        self.base_url = kwargs.get('base_url', 'https://api.storytoolkit.ai')

    def calculate_history_tokens(self, messages=None, model=None):

        if model is None:
            model = self.model_name

        # map the storytoolkit.ai models to their OpenAI counterparts for the token calculation
        model_map = {
            'roy-4t': 'gpt-4-1106-preview',
            'george-4': 'gpt-4',
            'sergei-3.5': 'gpt-3.5-turbo-1106'
        }

        # get the mapped model or just use the model name if there is no mapping
        mapped_model = model_map.get(model, None) or model

        return super().calculate_history_tokens(messages=messages, model=mapped_model)

    def _request(self, chat_history, settings=None, **kwargs):

        # now send the query to the assistant
        try:

            headers = {'auth-key': self.api_key}

            data = StAssistantRequest(
                model=self.model_name,
                messages=chat_history,
                settings=StModelSettings(
                    temperature=settings.get('temperature', 1),
                    max_length=settings.get('max_length', 256),
                    top_p=settings.get('top_p', 1),
                    frequency_penalty=settings.get('frequency_penalty', 0),
                    presence_penalty=settings.get('presence_penalty', 0),
                    timeout=settings.get('timeout', 30),
                )
            ).dict()

            api_response = requests.post(
                self.base_url + '/assistant', json=data, headers=headers, timeout=settings.get('timeout', 30))

            if api_response.status_code == 403:
                logger.warning('Invalid Assistant authentication key: {}'.format(api_response.text))
                raise Exception('Invalid authentication key.')

            elif api_response.status_code == 422:
                raise Exception('Invalid request data.')

            elif api_response.status_code == 429:
                logger.warning('Reached Assistant credit limit: {}'.format(api_response.text))
                raise Exception('Not enough credits.')

            elif api_response.status_code == 500:
                raise Exception('Internal server error.')

            elif api_response.status_code == 404:
                logger.warning('Not found Assistant: {}'.format(api_response.text))
                raise Exception('{}'.format(json.loads(api_response.text).get('detail', 'Not found')))

            elif api_response.status_code != 200:
                logger.warning('Unknown Assistant error: {}'.format(api_response.text))
                raise Exception('Unknown error.')

            # parse the response
            response = AssistantResponse.parse_obj((api_response.json()))

            if kwargs.get('save_to_history', True):

                self.chat_history.append({"role": "assistant", "content": response.completion})

                # keep track of the index of the last assistant message
                self._last_assistant_message_idx = len(self.chat_history) - 1

            # add the result to the chat history
            self.add_usage(tokens_in=response.usage.completion_tokens, tokens_out=response.usage.prompt_tokens)

            # wrap the response in an AssistantResponse object
            # so we can process it correctly
            return AssistantResponse(
                completion=response.completion,
                usage=response.usage
            ), chat_history

        except requests.exceptions.Timeout:
            error = 'Request to storytoolkit.ai timed out.'
            logger.error(error)
            return AssistantResponse(
                completion=None,
                usage=None,
                error=error,
                error_code=500
            ), chat_history

        except requests.exceptions.ConnectionError:
            error = 'Connection error. Could not connect to storytoolkit.ai.'
            logger.error(error, exc_info=True)
            return AssistantResponse(
                completion=None,
                usage=None,
                error=error
            ), chat_history

        except Exception as e:
            logger.error('Error sending query to storytoolkit.ai: ', exc_info=True)
            error = "There seems to be a problem with the connection to storytoolkit.ai. " \
                    "Please check the logs or try again later."

            error += '\n\nAPI response: {}'.format(e)

            return AssistantResponse(
                error=error
            ), chat_history


class AssistantUtils:

    @staticmethod
    def assistant_handler(toolkit_ops_obj, model_provider, model_name, **kwargs):
        """
        This is the handler function for the assistant class and is used to instantiate the correct assistant class
        depending on the model provider and model name
        """

        # do not allow empty model provider or model name
        if model_provider is None or model_name is None or model_provider.strip() == '' or model_name.strip() == '':
            logger.error('Could not find assistant handler for model "{}" from provider "{}".'
                         .format(model_name, model_provider))
            return None

        try:

            if model_provider not in AssistantUtils.assistant_available_providers():
                raise KeyError

            # check if the model is in the available models from the provider
            provider_models = AssistantUtils.assistant_available_models(provider=model_provider)

            # if the model name is not in the available models
            if model_name not in provider_models:

                logger.warning('Could not find assistant handler for model {} from provider {}.')

                # try to get one that starts with the model name
                # (for eg. gpt-3.5-turbo-0613 if user asks for gpt-3.5-turbo)
                for available_model in provider_models:
                    if available_model.startswith(model_name):
                        model_name = available_model
                        logger.warning('Selected model {} from the provider.'.format(model_name))
                        break

                # if we still couldn't find the model, then just use the first available model from the provider
                if model_name not in provider_models:
                    model_name = provider_models[0]
                    logger.warning('Selected first available model from the provider: {}')

            # load the assistant class
            toolkit_assistant = LLM_AVAILABLE_MODELS[model_provider][model_name].get('handler', None)

            # use the base_url from the config if it exists
            if LLM_AVAILABLE_MODELS[model_provider][model_name].get('base_url', None):
                kwargs['base_url'] = LLM_AVAILABLE_MODELS[model_provider][model_name]['base_url']

            # use the api_key from the config if it exists
            if LLM_AVAILABLE_MODELS[model_provider][model_name].get('api_key', None):
                kwargs['api_key'] = LLM_AVAILABLE_MODELS[model_provider][model_name]['api_key']

            # use the system_message from the config if it exists
            if LLM_AVAILABLE_MODELS[model_provider][model_name].get('system_message', None):
                kwargs['system_message'] = LLM_AVAILABLE_MODELS[model_provider][model_name]['system_message']

            if isinstance(toolkit_assistant, str):
                # if the handler is a string, try to use it as a class name
                toolkit_assistant = globals().get(toolkit_assistant, None)

            if toolkit_assistant is None:
                logger.error('Could not find assistant handler for model {} from provider {}.'
                             .format(model_name, model_provider))
                return None

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

            # select the first provider if the provider is not in the available models
            if provider not in LLM_AVAILABLE_MODELS:
                provider = list(LLM_AVAILABLE_MODELS.keys())[0]

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
        'gpt-4o-2024-05-13': {
            'description': 'GPT-4o',
            'price': {'input': 0.005, 'output': 0.015, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 128000,
            'training_cutoff': '2023-10',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4-turbo-2024-04-09': {
            'description': 'GPT-4 Turbo with Vision',
            'price': {'input': 0.01, 'output': 0.03, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 128000,
            'training_cutoff': '2023-12',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4-0125-preview': {
            'description': 'GPT-4 Turbo (0125 preview)',
            'price': {'input': 0.01, 'output': 0.03, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 128000,
            'training_cutoff': '2023-12',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4-1106-preview': {
            'description': 'GPT-4 Turbo (1106 preview)',
            'price': {'input': 0.01, 'output': 0.03, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 128000,
            'training_cutoff': '2023-04',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4': {
            'description': 'GPT-4',
            'price': {'input': 0.03, 'output': 0.06, 'currency': 'USD'},
            'token_limit': 8192,
            'context_window': 8192,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-4-32k': {
            'description': 'GPT-4 32k',
            'price': {'input': 0.06, 'output': 0.12, 'currency': 'USD'},
            'token_limit': 32768,
            'context_window': 32768,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-3.5-turbo-0125': {
            'description': 'GPT-3.5 Turbo (0125)',
            'price': {'input': 0.0005, 'output': 0.0015, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 16385,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-3.5-turbo-1106': {
            'description': 'GPT-3.5 Turbo (1106)',
            'price': {'input': 0.001, 'output': 0.002, 'currency': 'USD'},
            'token_limit': 4096,
            'context_window': 16385,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
        'gpt-3.5-turbo-16k-0613': {
            'description': 'GPT-3.5 Turbo 16k (0613)',
            'price': {'input': 0.0030, 'output': 0.0040, 'currency': 'USD'},
            'token_limit': 16385,
            'context_window': 16385,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://openai.com/pricing/',
            'handler': ChatGPT
        },
    },
    'storytoolkit.ai': {
        'roy-4t': {
            'description': 'Roy-4t',
            'price': {'input': None, 'output': None, 'currency': 'credits'},
            'token_limit': 16385,
            'training_cutoff': '2021-09',
            'pricing_info': 'https://storytoolkit.ai/',
            'handler': StAssistant
        },
        'george-4': {
            'description': 'George-4',
            'price': {'input': None, 'output': None, 'currency': 'credits'},
            'token_limit': 16385,
            'training_cutoff': '2023-04',
            'pricing_info': 'https://storytoolkit.ai/',
            'handler': StAssistant
        },
        'sergei-3.5': {
            'description': 'Sergei-3.5',
            'price': {'input': None, 'output': None, 'currency': 'credits'},
            'token_limit': 16385,
            'training_cutoff': '2023-04',
            'pricing_info': 'https://storytoolkit.ai/',
            'handler': StAssistant
        },
    }
}


# load additional LLM models from the llm_models.json file in USER_DATA_PATH
# if it exists
llm_models_file = os.path.join(USER_DATA_PATH, 'additional_llm_models.json')

if os.path.exists(llm_models_file):
    with open(llm_models_file, 'r') as f:
        llm_models = json.load(f)

    # add the additional models to the LLM_AVAILABLE_MODELS
    # take each provider and add the models to the existing ones
    # or add them to a new provider if it doesn't exist
    for provider, models in llm_models.items():
        if provider in LLM_AVAILABLE_MODELS:
            LLM_AVAILABLE_MODELS[provider].update(models)
        else:
            LLM_AVAILABLE_MODELS[provider] = models

    logger.debug('Loaded additional LLM models from {}'.format(llm_models_file))
