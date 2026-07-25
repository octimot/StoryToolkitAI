import subprocess
from typing import Optional

from pydantic import BaseModel

from storytoolkitai.core.logger import logger


MACOS_NOTIFICATION_SCRIPT = """\
on run argv
    display notification (item 1 of argv) with title (item 2 of argv)
end run
"""


def build_macos_notification_command(title, message) -> list[str]:
    """
    Build an osascript command without adding notification text to its source.

    ``--`` ends option parsing so leading hyphens in either value are handled
    as notification content.
    """

    return [
        'osascript',
        '-e',
        MACOS_NOTIFICATION_SCRIPT,
        '--',
        str(message),
        str(title),
    ]


def notify_via_macos(title, message) -> None:
    """Present a native macOS notification without invoking a shell."""

    subprocess.run(
        build_macos_notification_command(title, message),
        check=False,
    )


class NotificationMessage(BaseModel):
    # what gets logged
    message: str

    # what gets displayed
    display_message: str

    # the log level
    level: str

    # whether to include exception info in the log
    exc_info: Optional[bool] = None


class NotificationService:
    """dispatch notifications to one or more UI receivers"""

    # define the known UI receiver types
    RECEIVER_TYPES = ['window']

    def __init__(
        self,
        message=None,
        *,
        display_message=None,
        level='info',
        exc_info=None,
    ):
        # initialize the message batch
        self.batch = []

        # add the initial message when one was supplied
        if message:
            self.add_message(
                message,
                display_message=display_message,
                level=level,
                exc_info=exc_info,
            )

        # a display message cannot exist without a log message
        elif display_message:
            raise ValueError(
                'display_message passed to NotificationService '
                'without a message.'
            )

        # keep the registered UI receivers
        self.receivers = {}

    def add_message(
        self,
        message,
        *,
        display_message=None,
        level='info',
        exc_info=None,
    ) -> 'NotificationService':
        # use the log message for display when no alternative was passed
        self.batch.append(
            NotificationMessage(
                message=message,
                display_message=display_message or message,
                level=level,
                exc_info=exc_info,
            )
        )

        return self

    def to(
        self,
        receiver_type,
        receiver_reference,
    ) -> 'NotificationService':
        """add a UI receiver for the current message batch"""

        if receiver_type not in self.RECEIVER_TYPES:
            raise ValueError(
                'Notification receiver type: {} not in list of known '
                'types: {}'.format(
                    receiver_type,
                    self.RECEIVER_TYPES,
                )
            )

        if receiver_type not in self.receivers:
            self.receivers[receiver_type] = []

        # receivers expose a receive_notification method
        self.receivers[receiver_type].append(receiver_reference)

        return self

    def _process_message(
        self,
        notification_message: NotificationMessage,
    ) -> bool:
        """log and dispatch one UI notification"""

        try:
            if notification_message.level == 'error':
                logger.error(
                    notification_message.message,
                    exc_info=notification_message.exc_info,
                )

            elif notification_message.level == 'warning':
                logger.warning(
                    notification_message.message,
                    exc_info=notification_message.exc_info,
                )

            elif notification_message.level == 'debug':
                logger.debug(
                    notification_message.message,
                    exc_info=notification_message.exc_info,
                )

            else:
                logger.info(
                    notification_message.message,
                    exc_info=notification_message.exc_info,
                )

            # dispatch the message to each registered UI receiver
            for receiver_list in self.receivers.values():
                for receiver in receiver_list:
                    receiver.receive_notification(notification_message)

        except Exception as error:
            logger.error(
                'Error processing notification message: {}'.format(error)
            )
            logger.debug('Error:', exc_info=True)

            return False

        return True

    def push(self) -> 'NotificationService':
        """process all queued UI notifications in order"""

        try:
            for notification_message in self.batch:
                self._process_message(notification_message)

        except Exception as error:
            logger.error(
                'Error processing notification messages: {}'.format(error)
            )
            logger.debug('Error:', exc_info=True)

        return self
