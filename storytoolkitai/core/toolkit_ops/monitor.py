import threading
import time


class Monitor:
    """
    Monitors for condition to be met and fires done function when it is.

    We can also initiate it without a condition and a done callback,
    and the monitor will wait until they exist and they're callable, or until it reaches the timeout.
    """

    def __init__(self, done: callable = None, condition: callable = None, timer: int = None):

        self._done = done
        self._condition = condition
        self.timer = timer
        self.monitoring = False

        # if the done function doesn't exist after this timeout, throw an exception
        self.done_exists_timeout = 2

        # if the condition function doesn't exist after this timeout, throw an exception
        self.condition_exists_timeout = 2

        # keep track of when the monitor was initialized
        self._monitor_initialized_at = time.time()

        self.monitor_thread = threading.Thread(target=self.start_monitoring)
        self.monitor_thread.start()

    def start_monitoring(self):
        """
        Monitor for condition to be met and fire done function when it is.
        """

        # if the condition is not callable (i.e. a function), then sleep for 1 second and try again
        if not callable(self._condition):

            # check if we didn't reach the callable timeout
            # (the time we wait for the monitor to know its callable "condition" function)
            if time.time() - self._monitor_initialized_at > self.condition_exists_timeout:
                raise Exception('The condition function for monitor {} is not callable after {} seconds. '
                                'Killing monitor.'
                                .format(self, self.condition_exists_timeout))

            time.sleep(1)
            self.start_monitoring()
            return

        # wait until the condition is met
        while not self._condition():

            self.monitoring = True

            # sleep for 1 second or the specified timer
            time.sleep(self.timer if self.timer and isinstance(self.timer, int) else 1)

        # wait until the done function is callable
        while not callable(self._done):

            # check if we didn't reach the done_exists timeout
            # (the time we wait for the monitor to know its callable "done" function)
            if time.time() - self._monitor_initialized_at > self.done_exists_timeout:
                raise Exception('The done function for monitor {} is not callable after {} seconds. '
                                'Killing monitor.'
                                .format(self, self.done_exists_timeout))

            time.sleep(1)

        self._done()

    def add_done_callback(self, done: callable):
        """
        Add a done callback to the monitor.
        """

        self._done = done

    def add_condition_callback(self, condition: callable):
        """
        Add a condition callback to the monitor.
        """

        self._condition = condition
