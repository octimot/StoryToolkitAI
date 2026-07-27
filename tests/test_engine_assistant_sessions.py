from copy import deepcopy

import pytest

from storytoolkitai.core.engine import (
    AssistantSession,
    StoryToolkitEngine,
)


class FakeAssistant:
    """
    Minimal private assistant implementation used by engine tests.
    """

    next_id = 1

    def __init__(
        self,
        model_provider,
        model_name,
    ):
        self.model_provider = model_provider
        self.model_name = model_name
        self.model_description = '{} description'.format(
            model_name
        )
        self._assistant_id = 'assistant-{}'.format(
            FakeAssistant.next_id
        )
        FakeAssistant.next_id += 1

        self._tokens_used = {
            model_name: [0, 0],
        }
        self.context = None
        self.chat_history = [
            {
                'role': 'system',
                'content': 'System',
            }
        ]
        self._last_assistant_message_idx = None
        self.available_models = {
            model_provider: {
                model_name: {
                    'description': self.model_description,
                }
            }
        }

    @property
    def assistant_id(self):
        return self._assistant_id

    @property
    def tokens_used(self):
        return self._tokens_used

    @property
    def last_assistant_message_idx(self):
        return self._last_assistant_message_idx

    def add_context(self, context):
        self.context = context
        self.chat_history.append(
            {
                'role': 'user',
                'content': context,
            }
        )
        return True

    def set_system(self, system_message):
        self.chat_history[0] = {
            'role': 'system',
            'content': system_message,
        }
        return True

    def calculate_history_tokens(self):
        return 42

    def reset(self):
        self.chat_history = [
            self.chat_history[0],
        ]
        return True

    def send_query(self, prompt, settings, **kwargs):
        self.chat_history.append(
            {
                'role': 'user',
                'content': prompt,
            }
        )
        self.chat_history.append(
            {
                'role': 'assistant',
                'content': 'Reply',
            }
        )
        self._last_assistant_message_idx = (
            len(self.chat_history) - 1
        )

        return 'Reply', deepcopy(self.chat_history)


@pytest.fixture(autouse=True)
def reset_fake_assistant_ids():
    FakeAssistant.next_id = 1


class FakeToolkitOps:
    """
    Assistant-related ToolkitOps surface used by StoryToolkitEngine tests.
    """

    def __init__(self):
        self.created_assistants = []

    @staticmethod
    def get_assistant_default_system_message():
        return 'Default assistant system message'

    @staticmethod
    def get_assistant_providers():
        return [
            'Provider',
            'Local',
        ]

    @staticmethod
    def get_assistant_models(
        provider=None,
        refresh_provider=False,
    ):
        if provider is None:
            return []

        return [
            'model-one',
            'model-two',
        ]

    def create_assistant(
        self,
        model_provider,
        model_name,
        **assistant_options,
    ):
        assistant = FakeAssistant(
            model_provider=model_provider,
            model_name=model_name,
        )

        self.created_assistants.append(
            {
                'assistant': assistant,
                'options': deepcopy(assistant_options),
            }
        )

        return assistant

    @staticmethod
    def copy_assistant_context_and_chat(
        source_assistant,
        target_assistant,
    ):
        target_assistant.context = deepcopy(
            source_assistant.context
        )
        target_assistant.chat_history = deepcopy(
            source_assistant.chat_history
        )
        target_assistant._tokens_used = deepcopy(
            source_assistant._tokens_used
        )
        target_assistant._last_assistant_message_idx = (
            source_assistant._last_assistant_message_idx
        )

        return True

    @staticmethod
    def parse_assistant_response(assistant_response):
        if assistant_response == '{"answer": true}':
            return {
                'answer': True,
            }

        return None


def test_assistant_metadata_is_returned_as_detached_data():
    engine = StoryToolkitEngine(FakeToolkitOps())

    providers = engine.get_assistant_providers()
    providers.append('Changed')

    models = engine.get_assistant_models(
        provider='Provider',
        refresh_provider=True,
    )
    models.append('Changed')

    assert engine.get_assistant_providers() == [
        'Provider',
        'Local',
    ]
    assert engine.get_assistant_models(
        provider='Provider',
        refresh_provider=True,
    ) == [
        'model-one',
        'model-two',
    ]


def test_create_assistant_returns_public_session():
    engine = StoryToolkitEngine(FakeToolkitOps())

    session = engine.create_assistant(
        model_provider='Provider',
        model_name='model-one',
    )

    assert isinstance(session, AssistantSession)
    assert session.session_id == 'assistant-1'
    assert session.model_provider == 'Provider'
    assert session.model_name == 'model-one'
    assert session.model_description == 'model-one description'
    assert not hasattr(session, 'assistant_id')


def test_replace_assistant_preserves_session_and_history():
    engine = StoryToolkitEngine(FakeToolkitOps())

    session = engine.create_assistant(
        model_provider='Provider',
        model_name='model-one',
    )
    session.add_context('Transcript')
    session.send_query(
        'Question',
        {},
    )

    original_session_id = session.session_id

    replacement = engine.replace_assistant(
        session_id=session.session_id,
        model_provider='Provider',
        model_name='model-two',
        strict=True,
    )

    assert replacement is not None
    assert replacement.session_id == original_session_id
    assert replacement.model_name == 'model-two'
    assert replacement.context == 'Transcript'
    assert replacement.chat_history_length == 4

    # the original public handle resolves the replacement too
    assert session.model_name == 'model-two'


def test_chat_history_is_mutated_through_session_methods():
    engine = StoryToolkitEngine(FakeToolkitOps())
    session = engine.create_assistant(
        model_provider='Provider',
        model_name='model-one',
    )

    assert session.insert_chat_history(
        index=1,
        item={
            'role': 'user',
            'content': 'Inserted',
        },
    ) is True
    assert session.chat_history_length == 2

    removed = session.pop_chat_history(index=1)

    assert removed == {
        'role': 'user',
        'content': 'Inserted',
    }
    assert session.chat_history_length == 1


def test_close_assistant_removes_private_implementation():
    engine = StoryToolkitEngine(FakeToolkitOps())
    session = engine.create_assistant(
        model_provider='Provider',
        model_name='model-one',
    )

    assert engine.close_assistant(session.session_id) is True
    assert engine.close_assistant(session.session_id) is False

    with pytest.raises(KeyError):
        _ = session.model_name


def test_parse_assistant_response_uses_processing_helper():
    engine = StoryToolkitEngine(FakeToolkitOps())

    assert engine.parse_assistant_response(
        '{"answer": true}'
    ) == {
        'answer': True,
    }
    assert engine.parse_assistant_response('not json') is None
