import openai
import tiktoken

from storytoolkitai.core.logger import logger


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

        # get the model from the kwargs or from the config file if not passed
        self.model_name = kwargs.get(
            'model_name',
            self.stAI.get_app_setting('assistant_model', default_if_none='gpt-3.5-turbo')
        )

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
