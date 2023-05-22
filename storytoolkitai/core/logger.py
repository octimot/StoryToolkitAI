import sys
import os
import logging
import logging.handlers as handlers

from storytoolkitai import APP_LOG_FILE

class Style():
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

# START LOGGER CONFIGURATION

# System call so that Windows enables console colors
os.system("")

# logger colors + style
class Logger_ConsoleFormatter(logging.Formatter):
    # format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
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
logger_console_handler.setFormatter(Logger_ConsoleFormatter())

# add logger_console_handler to logger
logger.addHandler(logger_console_handler)

## Here we define our file formatter
# format the file logging
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s (%(filename)s:%(lineno)d)")

# create file handler and set level to debug (we want to log everything in the file)
logger_file_handler = handlers.RotatingFileHandler(APP_LOG_FILE, maxBytes=1000000, backupCount=3)
logger_file_handler.setFormatter(file_formatter)
logger_file_handler.setLevel(logging.DEBUG)

# add file handler to logger
logger.addHandler(logger_file_handler)