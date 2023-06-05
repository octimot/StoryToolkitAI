# the sole purpose of this file is to have backwards compatibility with the old way of starting the app
# this will be removed soon!

# use the __main__.py in storytoolkitai to start the app
from storytoolkitai.__main__ import main

# import logger
from storytoolkitai.core.logger import logger

import time

if __name__ == '__main__':

    logger.warning('You are using the old way of starting StoryToolkitAI.\n'
                   'This method will be removed very soon.\n'
                   'Please see new instructions here: \n'
                   'https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.md#running-the-non-standalone-tool\n'
                   'Starting tool in 5 seconds.\n')

    time.sleep(10)
    main()