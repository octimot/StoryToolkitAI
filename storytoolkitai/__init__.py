import os

# define a global target dir so we remember where we chose to save stuff last time when asked
# but start with the user's home directory
user_home_dir = os.path.expanduser("~")
initial_target_dir = user_home_dir

# this is where we used to store the user data prior to version 0.16.14
# but we need to have a more universal approach, so we'll move this to
# the home directory of the user which is platform dependent (see below)
OLD_USER_DATA_PATH = 'userdata'

# this is where StoryToolkitAI stores the config files
# including project.json files and others
# on Mac, this is usually /Users/[username]/StoryToolkitAI
# on Windows, it's normally C:\Users\[username]\StoryToolkitAI
# on Linux, it's probably /home/[username]/StoryToolkitAI
USER_DATA_PATH = os.path.join(user_home_dir, 'StoryToolkitAI')

# create user data path if it doesn't exist
if not os.path.exists(USER_DATA_PATH):
    os.makedirs(USER_DATA_PATH)

# this is where we store the app configuration
APP_CONFIG_FILE_NAME = 'config.json'

# the location of the log file
APP_LOG_FILE = os.path.join(USER_DATA_PATH, 'app.log')


