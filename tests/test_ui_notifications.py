from storytoolkitai.ui.notifications import (
    NotificationMessage,
    NotificationService,
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
