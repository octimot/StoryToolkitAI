import sys
import os
import logging
import logging.handlers as handlers

from storytoolkitai import APP_LOG_FILE


class Style:
    BOLD = '\33[1m'
    ITALIC = '\33[3m'
    UNDERLINE = '\33[4m'
    BLINK = '\33[5m'
    BLINK2 = '\33[6m'
    SELECTED = '\33[7m'

    GREY = '\33[20m'
    RED = '\33[91m'
    GREEN = '\33[92m'
    YELLOW = '\33[93m'
    BLUE = '\33[94m'
    VIOLET = '\33[95m'
    CYAN = '\33[96m'
    WHITE = '\33[97m'

    ENDC = '\033[0m'


# System call so that Windows enables console colors
os.system("")


# logger colors + style
class LoggerConsoleFormatter(logging.Formatter):
    format = '%(levelname)s: %(message)s'

    FORMATS = {
        logging.DEBUG: Style.BLUE + format + Style.ENDC,
        logging.INFO: Style.GREY + format + Style.ENDC,
        logging.WARNING: Style.YELLOW + format + Style.ENDC,
        logging.ERROR: Style.RED + format + Style.ENDC,
        logging.CRITICAL: Style.RED + Style.BOLD + format + Style.ENDC
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# use this custom logger class to trace back where a logger.error was called from
# (activate below)
# custom Logger class with overridden error method
class CustomTracerLogger(logging.getLoggerClass()):
    def error(self, msg, *args, **kwargs):

        # where are we executing from?
        import inspect
        frame = inspect.currentframe()
        stack_trace = inspect.getouterframes(frame, 2)

        # reverse the stack_trace
        stack_trace.reverse()

        print('Tracing next error:')
        for stack_item in stack_trace:

            # get the file name and line number
            file_name = stack_item[1]
            line_number = stack_item[2]

            # if this is the previous to last item in the stack trace, add a check here message
            check_here = ' <--- error logging called here' if stack_item == stack_trace[-2] else ''

            # add the file name and line number to the log message
            print(f'    {file_name}:{line_number}{check_here}')

        super().error(msg, *args, **kwargs)


# set CustomTracerLogger as the default logger class
# logging.setLoggerClass(CustomTracerLogger)


# enable logger
logger = logging.getLogger('StAI')

# set the maximum log level for the text logger
logger.setLevel(logging.DEBUG)

# create console handler and set level to info
logger_console_handler = logging.StreamHandler()

# if --debug was used in the command line arguments, use the DEBUG logging level for the console
# otherwise use INFO level
logger_console_handler.setLevel(logging.INFO if '--debug' not in sys.argv else logging.DEBUG)

# add console formatter to ch
logger_console_handler.setFormatter(LoggerConsoleFormatter())

# add logger_console_handler to logger
logger.addHandler(logger_console_handler)

# Here we define our file formatter
# format the file logging
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s (%(filename)s:%(lineno)d)")

# create file handler and set level to debug (we want to log everything in the file)
logger_file_handler = handlers.RotatingFileHandler(APP_LOG_FILE, maxBytes=1000000, backupCount=3)
logger_file_handler.setFormatter(file_formatter)
logger_file_handler.setLevel(logging.DEBUG)

# add file handler to logger
logger.addHandler(logger_file_handler)
