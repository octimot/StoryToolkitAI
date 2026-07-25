from unittest.mock import patch

from storytoolkitai.ui.notifications import (
    MACOS_NOTIFICATION_SCRIPT,
    NotificationMessage,
    NotificationService,
    build_macos_notification_command,
    notify_via_macos,
)


class NotificationReceiver:
    def __init__(self):
        self.messages = []

    def receive_notification(self, message):
        self.messages.append(message)


def test_notification_service_dispatches_to_ui_receiver() -> None:
    receiver = NotificationReceiver()

    NotificationService(
        'internal warning',
        display_message='Visible warning',
        level='warning',
    ).to(
        'window',
        receiver,
    ).push()

    assert receiver.messages == [
        NotificationMessage(
            message='internal warning',
            display_message='Visible warning',
            level='warning',
            exc_info=None,
        )
    ]


def test_notification_service_rejects_unknown_receiver_type() -> None:
    receiver = NotificationReceiver()
    notification = NotificationService('message')

    try:
        notification.to('unknown', receiver)
    except ValueError as error:
        assert 'unknown' in str(error)
    else:
        raise AssertionError('Expected ValueError')


def test_macos_notification_command_passes_text_as_arguments() -> None:
    title = 'Title "double" and \'single\' \\ slash\n新しい 🚀; $(touch nope)'
    message = '-Message "double" and \'single\' \\ slash\nRésumé; `touch nope`'

    command = build_macos_notification_command(title, message)

    assert command == [
        'osascript',
        '-e',
        MACOS_NOTIFICATION_SCRIPT,
        '--',
        message,
        title,
    ]
    assert title not in MACOS_NOTIFICATION_SCRIPT
    assert message not in MACOS_NOTIFICATION_SCRIPT


def test_notify_via_macos_executes_argument_list_without_shell() -> None:
    with patch(
        'storytoolkitai.ui.notifications.subprocess.run'
    ) as run:
        notify_via_macos('A "quoted" title', "filename's\nsecond line")

    run.assert_called_once_with(
        build_macos_notification_command(
            'A "quoted" title',
            "filename's\nsecond line",
        ),
        check=False,
    )
