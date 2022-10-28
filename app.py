import os
import platform
import threading
import time
import json
import sys
import subprocess

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter import *

import hashlib
import codecs

import logging
import logging.handlers as handlers

from threading import *

import mots_resolve

import torch
import whisper

from timecode import Timecode

import webbrowser

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

    #format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
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

# if --debug was used in the command line arguments, use the DEBUG logging level
# otherwise use INFO level
logger.setLevel(logging.INFO if '--debug' not in sys.argv else logging.DEBUG)

# create console handler and set level to info
logger_console_handler = logging.StreamHandler()
logger_console_handler.setLevel(logging.DEBUG)

# add console formatter to ch
logger_console_handler.setFormatter(Logger_ConsoleFormatter())

# add logger_console_handler to logger
logger.addHandler(logger_console_handler)

## Here we define our file formatter
# format the file logging
file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s: %(message)s (%(filename)s:%(lineno)d)")

# create file handler and set level to debug
logger_file_handler = handlers.RotatingFileHandler(APP_LOG_FILE, maxBytes=1000000, backupCount=3)
logger_file_handler.setFormatter(file_formatter)
logger_file_handler.setLevel(logging.DEBUG)

# add file handler to logger
logger.addHandler(logger_file_handler)


# signal the start of the session in the log by adding some info about the machine
logger.debug('\n--------------\n'
             'Platform: {} {}\n Platform version: {}\n OS: {} \n running Python {}'
             '\n--------------'.format(
    platform.system(), platform.release(),
    platform.version(),
    ' '.join(map(str, platform.win32_ver()+platform.mac_ver())),
    '.'.join(map(str, sys.version_info))))


# this makes sure that the user has all the required packages installed
try:
    # get the path of app.py
    file_path = os.path.realpath(__file__)

    # check if all the requirements are met
    import pkg_resources
    pkg_resources.require(open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), mode='r'))

    logger.debug('All package requirements met.')

except:

    # let the user know that the packages are wrong
    import traceback
    traceback_str = traceback.format_exc()

    logger.error(traceback_str)

    # get the relative path of the requirements file
    requirements_rel_path = os.path.relpath(os.path.join(os.path.dirname(__file__), 'requirements.txt'))

    requirements_warning_msg = ('\n'
          'Some of the packages required to run StoryToolkitAI are missing from your Python environment.\n'
          'Please run pip install -r {} '
          'to make sure that the right versions of the required packages are installed or StoryToolkitAI will not '
          'run properly.\n\n'
          'If you are running the standalone version of the app, please report this error to the developers together '
                                'with the log file found at: {}\n'
          .format(requirements_rel_path, APP_LOG_FILE))

    logger.error(requirements_warning_msg)

    # keep this message in the console for a bit
    time.sleep(5)


class toolkit_UI:
    '''
    This handles all the GUI operations mainly using tkinter
    '''

    class TranscriptEdit:
        '''
        All the functions available in the transcript window should be part of this class
        '''

        def __init__(self, stAI=None, toolkit_UI_obj=None, toolkit_ops_obj=None):

            # keep a reference to the StoryToolkitAI object here
            self.stAI = stAI

            # keep a reference to the toolkit_UI object here
            self.toolkit_UI_obj = toolkit_UI_obj

            # keep a reference to the toolkit_ops_obj object here
            self.toolkit_ops_obj = toolkit_ops_obj

            self.root = toolkit_UI_obj.root

            # search results indexes stored here
            # we're making it a dict so that we can store result indexes for each window individually
            self.search_result_indexes = {}

            # when searching for text, you may want the user to cycle through the results, so this keep track
            # keeps track on which search result is the user currently on (in each transcript window)
            self.search_result_pos = {}

            # to keep track of what is being searched on each window
            self.search_strings = {}

            # to stop certain events while typing,
            # we keep track if we have typing going on in any of the windows
            self.typing = {}

            # to know in which windows is the user editing transcripts
            self.transcript_editing = {}

            # to know which window works with which transcription_file_path
            self.transcription_file_paths = {}

            # to store the transcript segments of each window,
            # including their start + end times and who knows what else?!
            # here, they are simply ordered in their line orders, where the index is line_no-1:
            #               self.transcript_segments[window_id][index] = segment_dict
            self.transcript_segments = {}

            # we need this to have a reference between
            # the line number of a segment within the transcript and the id of that segment in the transcription file
            # so the dict should look like: self.transcript_segments_ids[window_id][segment_line_no] = segment_id
            self.transcript_segments_ids = {}

            # all the selected transcript segments of each window
            # the selected segments dict will use the text element line number as an index, for eg:
            # self.selected_segments[window_id][line] = transcript_segment
            self.selected_segments = {}

            # the active_segment stores the text line number of each window to keep track where
            # the cursor is currently on the transcript
            self.active_segment = {}

            # when changed, active segments line numbers move to last_active_segment
            self.last_active_segment = {}

            # the current timecode of each window
            self.current_window_tc = {}

            # this keeps track of which transcription window is in sync with the resolve playhead
            self.sync_with_playhead = {}


        def link_to_timeline_button(self, button=None, transcription_file_path=None,
                                    link=None, timeline_name=None):

            if transcription_file_path is None:
                return None

            link_result = self.toolkit_ops_obj.link_transcription_to_timeline(
                transcription_file_path=transcription_file_path,
                link=link, timeline_name=timeline_name)

            # make the UI link (or unlink) the transcript to the timeline
            if link_result and link_result is not None:

                # if the reply is true, it means that the transcript is linked
                # therefore the button needs to read the opposite action
                button.config(text="Unlink from Timeline")
                return True
            elif not link_result and link_result is not None:
                # and the opposite if transcript is not linked
                button.config(text="Link to Timeline")
                return False

            # if the link result is None
            # don't change anything to the button
            else:
                return

        def sync_with_playhead_button(self, button=None, window_id=None, sync=None):

            if button is None or window_id is None:
                return False

            self.sync_with_playhead_update(window_id, sync)

            return sync

        def sync_with_playhead_update(self, window_id, sync=None):

            if window_id not in self.sync_with_playhead:
                self.sync_with_playhead[window_id] = False

            # if no sync variable was passed, toggle the current sync state
            if sync is None:
                sync = not self.sync_with_playhead[window_id]

            self.sync_with_playhead[window_id] = sync

            return sync

        def set_typing_in_window(self, event=None, window_id=None, typing=None):

            if window_id is None:
                return None

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.typing:
                self.typing[window_id] = False

            # if typing was passed, assign it
            if typing is not None:
                self.typing[window_id] = typing

            # return the status of the typing
            return self.typing[window_id]

        def get_typing_in_window(self, window_id):

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.typing:
                self.typing[window_id] = False

            return self.typing[window_id]

        def set_transcript_editing(self, event=None, window_id=None, editing=None):

            if window_id is None:
                return None

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.transcript_editing:
                self.transcript_editing[window_id] = False

            # if typing was passed, assign it
            if editing is not None:
                self.transcript_editing[window_id] = editing

            # return the status of the typing
            return self.transcript_editing[window_id]

        def get_transcript_editing_in_window(self, window_id):

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.transcript_editing:
                self.transcript_editing[window_id] = False

            return self.transcript_editing[window_id]

        def search_text(self, search_str=None, text_element=None, window_id=None):
            '''
            Used to search for text inside tkinter text objects
            This also tags the search results
            :return:
            '''

            if search_str is None or text_element is None or window_id is None:
                return False

            # remove tag 'found' from index 1 to END
            text_element.tag_remove('found', '1.0', END)

            # remove tag 'current_result_tag' from index 1 to END
            text_element.tag_remove('current_result_tag', '1.0', END)

            # reset the search result indexes and the result position
            self.search_result_indexes[window_id] = []
            self.search_result_pos[window_id] = 0

            # get the search string as the user is typing
            search_str = self.search_strings[window_id] = search_str.get()

            if search_str:
                idx = '1.0'

                self.search_strings[window_id] = search_str

                while 1:
                    # searches for desired string from index 1
                    idx = text_element.search(search_str, idx, nocase=True, stopindex=END)

                    # stop the loop when we run out of results (indexes)
                    if not idx:
                        break

                    # store each index
                    self.search_result_indexes[window_id].append(idx)

                    # last index sum of current index and
                    # length of text
                    lastidx = '%s+%dc' % (idx, len(search_str))

                    # add the found tag at idx
                    text_element.tag_add('found', idx, lastidx)
                    idx = lastidx

                #  take the viewer to the first occurrence
                if self.search_result_indexes[window_id] and len(self.search_result_indexes[window_id]) > 0 \
                        and self.search_result_indexes[window_id][0] != '':
                    text_element.see(self.search_result_indexes[window_id][0])

                    # and visually tag the results
                    self.tag_results(text_element, self.search_result_indexes[window_id][0], window_id)

                # mark located string with red
                text_element.tag_config('found', foreground=self.toolkit_UI_obj.resolve_theme_colors['red'])

        def tag_results(self, text_element, text_index, window_id):
            '''
            Another handy function that tags the search results directly on the transcript inside the transcript window
            This is also used to show on which of the search results is the user right now according to search_result_pos
            :param text_element:
            :param text_index:
            :param window_id:
            :return:
            '''
            if text_element is None:
                return False

            # remove previous position tags
            text_element.tag_delete('current_result_tag')

            if not text_index or text_index == '' or text_index is None or window_id is None:
                return False

            # add tag to show the user on which result position we are now
            # the tag starts at the text_index and ends according to the length of the search string
            text_element.tag_add('current_result_tag', text_index, text_index + '+'
                                 + str(len(self.search_strings[window_id])) + 'c')

            # the result tag has a white background and a red foreground
            text_element.tag_config('current_result_tag', background=self.toolkit_UI_obj.resolve_theme_colors['white'],
                                    foreground=self.toolkit_UI_obj.resolve_theme_colors['red'])

        def cycle_through_results(self, text_element=None, window_id=None):

            if text_element is not None or window_id is not None \
                    or self.search_result_indexes[window_id] or self.search_result_indexes[window_id][0] != '':

                # get the current search result position
                current_pos = self.search_result_pos[window_id]

                # as long as we're not going over the number of results
                if current_pos < len(self.search_result_indexes[window_id]) - 1:

                    # add 1 to the current result position
                    current_pos = self.search_result_pos[window_id] = current_pos + 1

                    # this is the index of the current result position
                    text_index = self.search_result_indexes[window_id][current_pos]

                    # go to the next search result
                    text_element.see(text_index)

                # otherwise go back to start
                else:
                    current_pos = self.search_result_pos[window_id] = 0

                    # this is the index of the current result position
                    text_index = self.search_result_indexes[window_id][current_pos]

                    # go to the next search result
                    text_element.see(self.search_result_indexes[window_id][current_pos])

            # visually tag the results
            self.tag_results(text_element, text_index, window_id)

        def get_line_char_from_click(self, event, text_element=None):

            index = text_element.index("@%s,%s" % (event.x, event.y))
            line, char = index.split(".")

            return line, char

        def transcription_window_keypress(self, event=None, **attributes):
            '''
            What to do with the keypresses on transcription windows?
            :param attributes:
            :return:
            '''

            if self.get_typing_in_window(attributes['window_id']):
                return

            # for now, simply pass to select text lines if it matches one of these keys
            if event.keysym in ['Up', 'Down', 'v', 'V', 'A', 'i', 'o', 'm', 'M', 'C', 'q', 's', 'L',
                                'g',
                                'apostrophe', 'semicolon']:
                self.segment_actions(event, **attributes)

        def transcription_window_mouse(self, event=None, **attributes):
            '''
            What to do with mouse presses on transcription windows?
            :param event:
            :param attributes:
            :return:
            '''

            #print(event.state)
            # for now simply pass the event to the segment actions
            self.segment_actions(event, mouse=True, **attributes)

        def segment_actions(self, event=None, text_element=None, window_id=None, special_key=None, mouse=False):
            '''
            Handles the key and mouse presses in relation with transcript segments (lines)
            :return:
            '''

            if text_element is None or window_id is None:
                return False

            #if special_key is not None:
            #     print(special_key)

            # HERE ARE SOME USEFUL SHORTCUTS FOR THE TRANSCRIPTION WINDOW:
            #
            # MOUSE
            # Click          - move active segment on clicked text and move playhead to start of active segment
            # CMD/CTRL+Click - add clicked text to selection
            #
            # KEYS
            # Up, Down keys  - move the cursor up and down on the transcript (we call it "active segment")
            # Semicolon      - move playhead to start of active segment/selection
            # Apostrophe     - move playhead to end of active segment/selection
            # V              - add active segment to selection
            # Shift+V        - deselect all
            # Shift+A        - create selection between the previously active and the currently active segment
            #                   also works to create a selection for the last played segments (if sync is active)
            # Shift+C        - copy transcript of active segment/selection with timecodes at the beginning
            #                  of each block of text (or transcript seconds, if resolve is not available)
            # m              - add duration markers for the active segment/selection
            #                  in case there are gaps between the text segments,
            #                  the tool will create a marker for each block of uninterrupted text
            # Shift+M        - add duration markers as above, but with user prompt for the marker name
            # q              - close transcript window
            # Shift+L        - link transcription to the current timeline (if available)
            # s              - enable sync
            # Tab            - cycle between search and transcript navigation


             # initialize the active segment number
            self.active_segment[window_id] = self.get_active_segment(window_id, 1)

            # PRE- CURSOR MOVE EVENTS:
            # below we have the events that should happen prior to moving the cursor

            # UP key events
            if event.keysym == 'Up':

                # move cursor (active segment) on the previous segment on the transcript
                self.set_active_segment(window_id, text_element, line_calc=-1)

            # DOWN key events
            elif event.keysym == 'Down':

                # move cursor (active segment) on the next segment on the transcript
                self.set_active_segment(window_id, text_element, line_calc=1)

            # APOSTROPHE key events
            elif event.keysym == 'apostrophe':
                # go_to_time end time of the last selected segment
                self.go_to_selected_time(window_id=window_id, position='end')

            # SEMICOLON key events
            elif event.keysym == 'semicolon':
                # go_to_time start time of the first selected segment
                self.go_to_selected_time(window_id=window_id, position='start')


            # on mouse presses
            if mouse:

                # first get the line and char numbers based text under the click event
                index = text_element.index("@%s,%s" % (event.x, event.y))
                line_str, char_str = index.split(".")

                # make the clicked segment into active segment
                self.set_active_segment(window_id, text_element, int(line_str))

                # and move playhead to that time
                self.go_to_selected_time(window_id, 'start', ignore_selection=True)

                # if shift was also pressed
                if special_key == 'cmd':

                    # add clicked segment to selection
                    self.segment_to_selection(window_id, text_element, int(line_str))

            # what is the currently selected line number again?
            line = self.get_active_segment(window_id)

            # POST- CURSOR MOVE EVENTS
            # these are the events that might require the new line and segment numbers

            # v key events
            if event.keysym == 'v':

                # add/remove active segment to selection
                # if it's not in the selection
                self.segment_to_selection(window_id, text_element, line)

            # Shift+V key events
            if event.keysym == 'V':
                # clear selection
                self.clear_selection(window_id, text_element)

            # Shift+A key events
            if event.keysym == 'A':

                # select all segments between the active_segment and the last_active_segment

                # first, get the lowest index between the active and the last active segments
                if self.active_segment[window_id] >= self.last_active_segment[window_id]:
                    start_segment = self.last_active_segment[window_id]
                    max_segment = self.active_segment[window_id]
                else:
                    max_segment = self.last_active_segment[window_id]
                    start_segment = self.active_segment[window_id]

                # first clear the entire selection
                self.clear_selection(window_id, text_element)

                # then take each segment, starting with the lowest and select them
                n = start_segment
                while n <= max_segment:
                    self.segment_to_selection(window_id, text_element, n)
                    n = n+1

            # Shift+C key event
            if event.keysym == 'C':
                # copy the text content to clipboard
                self.get_segments_or_selection(window_id, add_to_clipboard=True, split_by='index')


            # m key event
            if event.keysym == 'm' or event.keysym == 'M':

                #print('Special Key:', special_key)

                # add segment based markers

                global resolve
                global current_timeline

                # this only works if resolve is connected
                if resolve and 'name' in current_timeline:

                    # first get the selected (or active) text from the transcript
                    # this should return a list of all the text chunks, the full text
                    #   and the start and end times of the entire text
                    text, full_text, start_sec, end_sec = \
                        self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                                       split_by='index', timecodes=True)

                    # now, take care of the marker name
                    marker_name = False

                    # if Shift+M was pressed, prompt the user for the marker name
                    if event.keysym == 'M':

                        # @todo this doesn't show up on top of everything else if other windows have 'keep on top'
                        marker_name = simpledialog.askstring(title="Markers Name", prompt="Marker Name:")

                    # if we still don't have a marker name
                    if not marker_name or marker_name == '':
                        # use a generic name which the user will most likely change afterwards
                        marker_name = 'Transcript Marker'

                    # calculate the start timecode of the timeline (simply use second 0 for the conversion)
                    # we will use this to calculate the text_chunk durations
                    timeline_start_tc = self.toolkit_ops_obj.calculate_sec_to_resolve_timecode(0)

                    # now take all the text chunks
                    for text_chunk in text:

                        # calculate the end timecodes for each text chunk
                        end_tc = self.toolkit_ops_obj.calculate_sec_to_resolve_timecode(text_chunk['end'])

                        # get the start_tc from the text_chunk but place it back into a Timecode object
                        # using the timeline framerate
                        start_tc = Timecode(timeline_start_tc.framerate, text_chunk['start_tc'])

                        # and subtract the end timecode from the start_tc of the text_chunk
                        # to get the marker duration (still timecode object for now)
                        # the start_tc of the text_chunk should be already in the text list
                        marker_duration_tc = end_tc-start_tc

                        # in Resolve, marker indexes are the number of frames from the beginning of the timeline
                        # so in order to get the marker index, we need to subtract the timeline_start_tc from start_tc

                        # but only if the start_tc is larger than the timeline_start_tc so we don't get a
                        # Timecode class error
                        if start_tc > timeline_start_tc:
                            start_tc_zero = start_tc-timeline_start_tc
                            marker_index = start_tc_zero.frames

                        # if not consider that we are at frame 1
                        else:
                            marker_index = 1

                        # check if there's another marker at the exact same index
                        index_blocked = True
                        while index_blocked:

                            if 'markers' in current_timeline and marker_index in current_timeline['markers']:

                                # give up if the duration is under a frame:
                                if marker_duration_tc.frames <= 1:
                                    self.notify_via_messagebox(title='Cannot add marker',
                                                               message='Not enough space to add marker on timeline.',
                                                               type='warning'
                                                               )
                                    return False

                                # notify the user that the index is blocked by another marker
                                add_frame = messagebox.askyesno(title='Cannot add marker',
                                                    message="Another marker exists at {}.\n\n"
                                                            "Do you want to place the new marker one frame later?"
                                                                .format(start_tc))

                                # if the user wants to move this marker one frame to the right, be it
                                if add_frame:
                                    start_tc.frames = start_tc.frames+1
                                    marker_index = marker_index+1

                                    # but this means that the duration should be one frame shorter
                                    marker_duration_tc.frames = marker_duration_tc.frames-1
                                else:
                                    return False

                            else:
                                index_blocked = False

                        marker_data = {}
                        marker_data[marker_index] = {}

                        # the name of the marker
                        marker_data[marker_index]['name'] = marker_name

                        # choose the marker color from Resolve
                        marker_data[marker_index]['color'] = self.stAI.get_app_setting('default_marker_color',
                                                                                         default_if_none='Blue')

                        # add the text to the marker data
                        marker_data[marker_index]['note'] = text_chunk['text']

                        # the marker duration needs to be in frames
                        marker_data[marker_index]['duration'] = marker_duration_tc.frames

                        # no need for custom data
                        marker_data[marker_index]['customData'] = ''

                        # pass the marker add request to resolve
                        mots_resolve.add_timeline_markers(current_timeline['name'], marker_data, False)

            # q key event
            if event.keysym == 'q':
                # close transcription window
                self.toolkit_UI_obj.destroy_window_(self.toolkit_UI_obj.windows, window_id=window_id)

            # Shift+L key event
            if event.keysym == 'L':
                # link transcription to file
                print('linking')
                self.toolkit_ops_obj.link_transcription_to_timeline(self.transcription_file_paths[window_id])

            # s key event
            if event.keysym == 's':
                self.sync_with_playhead_update(window_id=window_id)

            # g key event
            if event.keysym == 'g':
                self.group_selected(window_id=window_id)

        def get_segments_or_selection(self, window_id, add_to_clipboard=False, split_by=None, timecodes=True):
            '''
            Used to extract the text from either the active segment or from the selection
            Will return the text, and the start and end times

            If the split_by parameter is 'index', the text will be split into chunks of text that
            are next to each other in the main transcript_segments[window_id] list.

            If the split_by parameter is 'time', the text will be split into chunks of text that
            have no time gaps between them.

            If timecodes is true, the return will also include the text chunks start and end timecodes
            (if Resolve is available)

            If add_to_clipboard is True, the function copies the full_text to the clipboard

            :param window_id:
            :param add_to_clipboard:
            :param split_by: None, 'index' or 'time'
            :param timecodes
            :return:
            '''

            # the full text string
            full_text = ''

            # the return text list
            text = [{}]

            # the start and end times of the entire selection
            start_sec = None
            end_sec = None

            # get the start timecode from Resolve
            if timecodes:
                timeline_start_tc = self.toolkit_ops_obj.calculate_sec_to_resolve_timecode(0)

                # if no timecode was received it probably means Resolve is disconnected so disable timecodes
                if not timeline_start_tc:
                    timecodes = False

            # if we have some selected segments, use their start and end times
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:

                start_segment = None
                end_segment = None
                start_sec = 0
                end_sec = 0

                from operator import itemgetter

                # first sort the selected segments by start time
                # (but we are losing the line numbers which are normally in the dict keys!)
                sorted_selected_segments = sorted(self.selected_segments[window_id].values(), key=itemgetter('start'))

                # use this later to see where the selected_segment is in the original transcript
                transcript_segment_index = 0
                prev_transcript_segment_index = None
                prev_segment_end_time = None

                # keep track of text chunks in case the split by parameter was passed
                current_chunk_num = 0

                # add each text
                for selected_segment in sorted_selected_segments:

                    # see where this selected_segment is in the original transcript
                    transcript_segment_index = self.transcript_segments[window_id].index(selected_segment)

                    if split_by == 'index':

                        # assign a value if this is the first transcript_segment_index of this iteration
                        if prev_transcript_segment_index is None:
                            prev_transcript_segment_index = transcript_segment_index

                        # if the segment is not right after the previous segment that we processed
                        # it means that there are other segments between them which haven't been selected
                        elif prev_transcript_segment_index+1 != transcript_segment_index:
                            current_chunk_num = current_chunk_num+1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text+'\n[...]\n'

                    if split_by == 'time':

                        # assign the end time of the first selected segment
                        if prev_segment_end_time is None:
                            prev_segment_end_time = selected_segment['end']

                        # if the start time of the current segment
                        # doesn't match with the end time of the previous segment
                        elif selected_segment['start'] != prev_segment_end_time:
                            current_chunk_num = current_chunk_num+1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text+'\n[...]\n'

                    # add the current segment text to the current text chunk
                    text[current_chunk_num]['text'] = \
                        text[current_chunk_num]['text']+'\n'+selected_segment['text'].strip() \
                        if 'text' in text[current_chunk_num] else selected_segment['text']

                    # add the start time to the current text chunk
                    # but only for the first segment of this text chunk
                    if 'start' not in text[current_chunk_num]:
                        text[current_chunk_num]['start'] = selected_segment['start']

                        # also calculate the start timecode of this text chunk (only if Resolve available)
                        # the end timecode isn't needed at this point, so no sense in wasting resources
                        if timecodes:

                            # init the segment start timecode object
                            # but only if the start seconds are larger than 0
                            if selected_segment['start'] > 0:
                                segment_start_timecode = Timecode(timeline_start_tc.framerate,
                                                                  start_seconds=selected_segment['start'])

                                # factor in the timeline start tc and use it for this chunk
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc+segment_start_timecode)

                            # otherwise use the timeline_start_timecode
                            else:
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc)

                            # add it to the beginning of the text
                            text[current_chunk_num]['text'] = \
                                text[current_chunk_num]['start_tc']+':\n'+text[current_chunk_num]['text'].strip()

                            # add it to the full text body
                            full_text = full_text+'\n'+text[current_chunk_num]['start_tc']+':\n'

                    # add the end time of the current text chunk
                    text[current_chunk_num]['end'] = selected_segment['end']

                    # add the segment text to the full text variable
                    full_text = (full_text+selected_segment['text'].strip()+'\n')

                    # remember the index for the next iteration
                    prev_transcript_segment_index = transcript_segment_index

            # if there are no selected segments on this window
            # get the text of the active segment
            else:
                # if there is no active_segment for the window, create one
                if window_id not in self.active_segment:
                    self.active_segment[window_id] = 1

                # get the line number from the active segment
                line = self.active_segment[window_id]

                # we need to convert the line number to the segment_index used in the transcript_segments list
                segment_index = line - 1

                # get the text form the active segment
                full_text = self.transcript_segments[window_id][segment_index]['text'].strip()

                # get the start and end times from the active segment
                start_sec = self.transcript_segments[window_id][segment_index]['start']
                end_sec = self.transcript_segments[window_id][segment_index]['end']

                if timecodes:
                    start_seconds = start_sec if int(start_sec) > 0 else 0.01

                    # init the segment start timecode object
                    # but only if the start seconds are larger than 0
                    if start_sec > 0:
                        segment_start_timecode = Timecode(timeline_start_tc.framerate, start_seconds=start_sec)

                        # factor in the timeline start tc and use it for this chunk
                        start_tc = str(timeline_start_tc + segment_start_timecode)

                    # otherwise use the timeline_start_timecode
                    else:
                        start_tc = str(timeline_start_tc)

                    # add it to the full text body
                    full_text = start_tc+':\n'+full_text

                # add this to the return list
                text = [{'text': full_text.strip(), 'start': start_sec, 'end': end_sec, 'start_tc': start_tc}]

            if add_to_clipboard:
                self.root.clipboard_clear()
                self.root.clipboard_append(full_text.strip())

            # now get the start_sec and the end_sec for the whole text
            start_sec = text[0]['start']
            end_sec = text[-1]['end']

            return text, full_text, start_sec, end_sec

        def go_to_selected_time(self, window_id=None, position=None, ignore_selection=False):

            # if we have some selected segments, use their start and end times
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0 \
                    and not ignore_selection:

                start_sec = None
                end_sec = None

                # go though all the selected_segments and get the lowest start time and the highest end time
                for segment_index in self.selected_segments[window_id]:

                    # get the start time of the earliest selected segment
                    if start_sec is None or self.selected_segments[window_id][segment_index]['start'] < start_sec:
                        start_sec = self.selected_segments[window_id][segment_index]['start']

                    # get the end time of the latest selected segment
                    if end_sec is None or self.selected_segments[window_id][segment_index]['end'] > end_sec:
                        end_sec = self.selected_segments[window_id][segment_index]['end']


            # otherwise use the active segment start and end times
            else:

                # if there is no active_segment for the window, create one
                if window_id not in self.active_segment:
                    self.active_segment[window_id] = 1

                # get the line number from the active segment
                line = self.active_segment[window_id]

                # we need to convert the line number to the segment_index used in the transcript_segments list
                segment_index = line-1

                # get the start and end times from the active segment
                start_sec = self.transcript_segments[window_id][segment_index]['start']
                end_sec = self.transcript_segments[window_id][segment_index]['end']


            # decide where to go depending on which position requested
            if position == 'end':
                seconds = end_sec
            else:
                seconds = start_sec

            # move playhead to seconds
            self.toolkit_ops_obj.go_to_time(seconds=seconds)

        def get_active_segment(self, window_id=None, initial_value=0):
            '''
            This returns the active segment number for the window with the window_id
            :param window_id:
            :return:
            '''
            # if there is no active_segment for the window, create one
            # this will help us keep track of where we are with the cursor
            if window_id not in self.active_segment:
                # but start with 0, considering that it will be re-calculated below
                self.active_segment[window_id] = initial_value

            # same as above for the last_active_segment
            if window_id not in self.last_active_segment:
                # but start with 0, considering that it will be re-calculated below
                self.last_active_segment[window_id] = initial_value

            return self.active_segment[window_id]

        def set_active_segment(self, window_id=None, text_element=None, line=None, line_calc=None):

            # remove any active segment tags
            text_element.tag_delete('l_active')

            # count the number of lines in the text
            text_num_lines = len(self.transcript_segments[window_id])

            # initialize the active segment number
            self.active_segment[window_id] = self.get_active_segment(window_id)

            # interpret the line number correctly
            if line is None and line_calc:
                line = self.active_segment[window_id] + line_calc

            # remove the active segment if no line or line_calc was passed
            if line is None and line_calc is None:
                del self.active_segment[window_id]
                return False

            # if passed line is lower than 1, go to the end of the transcript
            if line < 1:
                line = text_num_lines

            # if the line is larger than the number of lines, go to the beginning of the transcript
            elif line > text_num_lines:
                line = 1

            # first copy the active segment line number to the last active segment line number
            self.last_active_segment[window_id] = self.active_segment[window_id]

            # then update the active segment
            self.active_segment[window_id] = line

            # now tag the active segment
            text_element.tag_add("l_active", "{}.0".format(line), "{}.end+1c".format(line))
            # text_element.tag_config('l_active', foreground=self.toolkit_UI_obj.resolve_theme_colors['white'])

            # add some nice colors
            text_element.tag_config('l_active', foreground=self.toolkit_UI_obj.resolve_theme_colors['superblack'],
                                    background=self.toolkit_UI_obj.resolve_theme_colors['normal'])

            # also scroll the text element to the line
            text_element.see(str(line) + ".0")

        def clear_selection(self, window_id=None, text_element=None):
            '''
            This clears the segment selection for the said window
            :param window_id:
            :return:
            '''

            if window_id is None or text_element is None:
                return False

            self.selected_segments[window_id] = {}

            self.selected_segments[window_id].clear()

            text_element.tag_delete("l_selected")

        def segment_to_selection(self, window_id=None, text_element=None, line=None):
            '''
            This either adds or removes a segment to a selection,
            depending if it's already in the selection or not

            :param window_id:
            :param text_element:
            :param line:
            :return:
            '''

            if window_id is None or text_element is None or line is None:
                return False

            # if there is no selected_segments dict for the current window, create one
            if window_id not in self.selected_segments:
                self.selected_segments[window_id] = {}

            # convert the line number to segment_index
            segment_index = line-1

            # if the segment is not in the transcript segments dict
            if line in self.selected_segments[window_id]:
                # remove it
                del self.selected_segments[window_id][line]

                # remove the tag on the text in the text element
                text_element.tag_remove("l_selected", "{}.0".format(line), "{}.end+1c".format(line))

            # otherwise add it
            else:
                self.selected_segments[window_id][line] = self.transcript_segments[window_id][segment_index]

                # tag the text on the text element
                text_element.tag_add("l_selected", "{}.0".format(line), "{}.end+1c".format(line))

                # raise the tag so we can see it above other tags
                text_element.tag_raise("l_selected")

                # color the tag accordingly
                text_element.tag_config('l_selected', foreground='blue',
                                        background=self.toolkit_UI_obj.resolve_theme_colors['superblack'])

            return True

        def segment_line_to_id(self, window_id, line):

            # is there a reference to this current window id?
            # normally this should have been created during the opening of the transcription window
            if window_id in self.transcript_segments_ids:

                # is there a reference to the line number?
                if line in self.transcript_segments_ids[window_id]:

                    # then return the stored segment id
                    return self.transcript_segments_ids[window_id][line]

            # if all fails return None
            return None

        def segment_id_to_line(self, window_id, segment_id):

            # is there a reference to this current window id?
            # normally this should have been created during the opening of the transcription window
            if window_id in self.transcript_segments_ids:

                # go through all the ids and return the line number
                try:
                    line = list(self.transcript_segments_ids[window_id].keys()) \
                                [list(self.transcript_segments_ids[window_id].values()).index(segment_id)]

                    # if the line was found, return it
                    return line

                # if the line wasn't found return None
                except ValueError:
                    return None


            # if all fails return None
            return None

        def next_segment_id(self, window_id):
            # is there a reference to this current window id?
            # normally this should have been created during the opening of the transcription window
            if window_id in self.transcript_segments_ids:

                # go through all the ids and calculate the highest
                max_id = 0
                for line_id in self.transcript_segments_ids[window_id]:
                    if max_id < self.transcript_segments_ids[window_id][line_id]:
                        max_id = self.transcript_segments_ids[window_id][line_id]

                # if the line was found, return it
                return int(max_id)+1

            # if all fails return None
            return None

        def group_selected(self, window_id):

            # WORK IN PROGRESS

            #print(self.transcript_segments_ids[window_id])

            #print(self.segment_id_to_line(window_id, 20))

            # if we have some selected segments, group them
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:

                # take all the segments and add them to the group
                for selected_segment in self.selected_segments[window_id]:

                    # @todo add segment id to group
                    print(self.selected_segments[window_id][selected_segment])

                    # save group contents to transcription json file

        def on_press_add_segment(self, event, window_id=None, text=None):

            if window_id is None or text is None:
                return False

            # WORK IN PROGRESS

            print(event)

            # get the cursor position where the event was triggered (key was pressed)
            # and the last character of the line
            line, char, last_char = self.get_current_segment_chars(text=text)

            print('Pos: {}.{}; Last: {}'.format(line, char, last_char))

            # prevent RETURN key from adding another line break in the text
            return 'break'


            # initialize the new_line dict
            new_line = {}

            # the end time of the new line is the end of the current line
            new_line['end'] = self.transcript_segments[window_id][int(line)-1]['end']

            # get the text that is supposed to go on the next line
            new_line['text'] = text.get(INSERT, "{}.end+1c".format(line))

            # the id of the new line is the next available id in the transcript
            new_line['id'] = self.next_segment_id(window_id=window_id)

            print(new_line)

            # ask user at what time to split the segment
            # split_time = simpledialog.askstring(title='Where to split?',
            #                                     prompt='At what time should we split this segment?',
            #                                     initialvalue=self.transcript_segments[window_id][int(line)-1]['start'])

            split_time = (int(self.transcript_segments[window_id][int(line)-1]['end']) \
                         -int(self.transcript_segments[window_id][int(line)-1]['start']))/2

            split_time = int(self.transcript_segments[window_id][int(line)-1]['start']) + split_time

            # if the user didn't specify the split time
            if not split_time:
                # cancel
                return 'break'

            if float(split_time) >= float(self.transcript_segments[window_id][int(line)-1]['end']):

                self.toolkit_UI_obj.notify_via_messagebox(title='Split time too large',
                                                          message='The time you entered goes over the end time of '
                                                                  'the current segment.', type='warning')
                return 'break'

            # the split time becomes the start time of the new line
            new_line['start'] = split_time

            # and also the end of the previous line
            self.transcript_segments[window_id][int(line)-1]['end'] = split_time

            # add the element to the transcript segments right after the current line
            self.transcript_segments[window_id].insert(int(line), new_line)

            # insert the new line in the text element
            text.insert('{}.{}'.format(line, char), 'test\n')

            #text.insert(INSERT, text.get('0.0', "{}.end+1c".format(line)))

            # prevent RETURN key from adding another line break in the text
            return 'break'

        def edit_transcript(self, window_id=None, text=None, status_label=None):

            if window_id is None or text is None:
                return False

            text.focus()

            # enable typing mode to disable some shortcuts
            self.set_typing_in_window(window_id=window_id, typing=True)

            # enable transcript_editing for this window
            self.set_transcript_editing(window_id=window_id, editing=True)

            # todo RETURN key splits the segment at cursor according to Resolve playhead position
            text.bind('<Return>', lambda e: self.on_press_add_segment(e, window_id, text))

            # ESCAPE key defocuses transcript (and implicitly saves the transcript, see below)
            text.bind('<Escape>', lambda e: self.defocus_transcript(text=text))

            # text focusout saves transcript
            text.bind('<FocusOut>', lambda e: self.on_press_save_transcript(e, window_id, text,
                                                                          status_label=status_label))

            # todo BACKSPACE key at first line character merges the current and the previous segment
            text.bind('<BackSpace>', lambda e:
                    self.on_press_merge_segments(e, window_id=window_id, text=text, merge='previous'))

            # todo DELETE key at last line character merges the current and the next segment
            text.bind('<Delete>', lambda e:
                    self.on_press_merge_segments(e, window_id=window_id, text=text, merge='next'))

            if status_label is not None:
                status_label.config(text='Not saved.', foreground=self.toolkit_UI_obj.resolve_theme_colors['red'])

            text.config(state=NORMAL)

        def unbind_editing_keys(self, text):
            '''
            This function unbinds all the keys used for editing the transcription
            :return:
            '''

            text.unbind('<Return>')
            text.unbind('<Escape>')
            text.unbind('<BackSpace>')
            text.unbind('<Delete>')

        def get_current_segment_chars(self, text):

            # get the position of the cursor
            line, char = text.index(INSERT).split('.')

            # get the index of the last character of the line where the cursor is
            _, last_char = text.index("{}.end".format(line)).split('.')

            return line, char, last_char

        def on_press_merge_segments(self, event, window_id, text, merge=None):
            '''
            This function checks whether the cursor is at the beginning or at the end of the line and
            it merges the current transcript segment either with the previous or with the next segment

            :param event:
            :param window_id:
            :param text:
            :return:
            '''

            if window_id is None or text is None:
                return False

            if merge not in ['previous', 'next']:
                logger.error('Merge direction not specified.')
                return 'break'

            # get the cursor position where the event was triggered (key was pressed)
            # and the last character of the line
            line, char, last_char = self.get_current_segment_chars(text=text)

            # ignore if we are not at the beginning nor at the end of the current line
            # or if the direction of the merge doesn't match the character number
            if char not in ['0', last_char]\
                or (char == '0' and merge != 'previous')\
                or (char == last_char and merge != 'next'):
                return

            # if we are at the beginning of the line
            # and the merge direction is 'prev'
            if char == '0' and merge != 'previous':

                return 'break'
                #print('TODO: Merge previous')

            # if we are at the end of the line
            # and the merge direction is 'next'
            if char == last_char and merge != 'next':

                return 'break'
                #print('TODO: Merge next')

            return 'break'

        def defocus_transcript(self, text):

            # defocus from transcript text
            tk_transcription_window = text.winfo_toplevel()
            tk_transcription_window.focus()

        def on_press_save_transcript(self, event, window_id, text, status_label=None):

            if window_id is None or text is None:
                return False

            # disable text editing again
            text.config(state=DISABLED)

            # unbind all the editing keys
            self.unbind_editing_keys(text)

            # deactivate typing and editing for this window
            self.set_typing_in_window(window_id=window_id, typing=False)
            self.set_transcript_editing(window_id=window_id, editing=False)

            # save the transcript
            save_status = self.save_transcript(window_id=window_id, text=text)

            # let the user know what happened via the status label
            if save_status is True:

                # show the user that the transcript was saved
                if status_label is not None:
                    status_label.config(text='Saved.',
                                        foreground=self.toolkit_UI_obj.resolve_theme_colors['normal'])


            # in case anything went wrong while saving,
            # let the user know about it
            elif save_status == 'fail':
                if status_label is not None:
                    status_label.config(text='Save Failed.',
                                        foreground=self.toolkit_UI_obj.resolve_theme_colors['red'])

            # in case the save status is False
            # assume that nothing needed saving
            else:
                if status_label is not None:
                    status_label.config(text='Nothing changed.',
                                        foreground=self.toolkit_UI_obj.resolve_theme_colors['normal'])

        def save_transcript(self, window_id=None, text=None):

            if window_id is None or text is None:
                return False

            # make sure that we know the path to this transcription file
            if not window_id in self.transcription_file_paths:
                return 'fail'

            # get the path of the transcription file
            transcription_file_path = self.transcription_file_paths[window_id]

            # get the contents of the transcription file
            old_transcription_file_data = \
                self.toolkit_ops_obj.get_transcription_file_data(transcription_file_path=transcription_file_path)

            # compare the edited lines with the existing transcript lines
            text_lines = text.get('1.0', END).splitlines()

            segment_no = 0
            changes_exist = False
            full_text = ''
            while segment_no < len(text_lines)-1:

                # add the segment text to a full text variable in case we need it later
                full_text = full_text+' '+text_lines[segment_no]

                # if any change to the text was found
                if text_lines[segment_no].strip() != self.transcript_segments[window_id][segment_no]['text'].strip():
                    #print('Modified line {}'.format(segment_no+1))
                    #print(text_lines[segment_no].strip())
                    #print(self.transcript_segments[window_id][segment_no])

                    # overwrite the segment text with the new text
                    self.transcript_segments[window_id][segment_no]['text'] = text_lines[segment_no].strip()+' '

                    # it means that we have to save the new file
                    changes_exist = True

                segment_no = segment_no + 1

            # if changes were detected on any of the lines
            if changes_exist:
                #print(json.dumps(old_transcription_file_data, indent=4))

                modified_transcription_file_data = old_transcription_file_data

                # replace the segments in the transcription file
                modified_transcription_file_data['segments'] = self.transcript_segments[window_id]

                # replace the full text in the trancription file
                modified_transcription_file_data['text'] = full_text

                # add the last modified key
                modified_transcription_file_data['last_modified'] = str(time.time()).split('.')[0]

                # save the new transcription
                self.toolkit_ops_obj.save_transcription_file(transcription_file_path=transcription_file_path,
                                                             transcription_data=modified_transcription_file_data,
                                                             backup='backup')

                # the directory where the transcription file is
                transcription_file_dir = os.path.dirname(transcription_file_path)

                # if this transcription has an associated txt file, update it:
                if 'txt_file_path' in modified_transcription_file_data:

                    # assume that it's in the same folder as the transcription file
                    txt_file_path = os.path.join(transcription_file_dir,
                                                 modified_transcription_file_data['txt_file_path'])

                    self.toolkit_ops_obj.save_txt_from_transcription(txt_file_path=txt_file_path,
                                                                 transcription_data=modified_transcription_file_data)

                # if this transcription has an associated srt file, update it
                if 'srt_file_path' in modified_transcription_file_data:

                    # assume that it's in the same folder as the transcription file
                    srt_file_path = os.path.join(transcription_file_dir,
                                                 modified_transcription_file_data['srt_file_path'])

                    self.toolkit_ops_obj.save_srt_from_transcription(srt_file_path=srt_file_path,
                                                                 transcription_data=modified_transcription_file_data)

                return True

            # returning false means that no changes were made
            return False

    def __init__(self, toolkit_ops_obj=None, stAI=None, **other_options):

        # make a reference to toolkit ops obj
        self.toolkit_ops_obj = toolkit_ops_obj

        # make a reference to StoryToolkitAI obj
        self.stAI = stAI

        # initialize tkinter as the main GUI
        self.root = tk.Tk()

        logger.debug('Running with TK {}'.format(self.root.call("info", "patchlevel")))

        # set the main window title
        self.root.title("StoryToolkitAI v{}".format(stAI.__version__))

        # temporary width and height for the main window
        self.root.config(width=1, height=1)

        # initialize transcript edit object
        self.t_edit_obj = self.TranscriptEdit(stAI=self.stAI, toolkit_UI_obj=self, toolkit_ops_obj=self.toolkit_ops_obj)

        # show the update available message if any
        if 'update_available' in other_options and other_options['update_available'] is not None:

            # the url to the releases page
            release_url = 'https://github.com/octimot/StoryToolkitAI/releases/latest'

            # the update warning message the user will see
            warn_message = '\nA newer version of StoryToolkitAI is available.\n\n ' \
                           'Use git pull or download it from\n ' \
                           '{}'.format(release_url)

            # notify the user via console
            logger.warning(warn_message)

            # add the question to the pop up message box
            warn_message = warn_message+' \n\n Do you want to open the release page?'

            # notify the user and ask whether to open the release website or not
            goto_projectpage = messagebox.askyesno(title="Update available",
                                                  message=warn_message)

            # open the browser and go to the release_url
            if goto_projectpage:
                webbrowser.open(release_url)

        # alert the user if ffmpeg isn't installed
        if 'ffmpeg_status' in other_options and not other_options['ffmpeg_status']:

            self.notify_via_messagebox(title='FFMPEG not found',
                                       message='FFMPEG was not found on this machine.\n'
                                               'Please follow the installation instructions or StoryToolkitAI will '
                                               'not work correctly.',
                                       type='error'
                                       )

        # keep all the window references here to find them easy by window_id
        self.windows = {}

        # set some UI styling here
        self.paddings = {'padx': 10, 'pady': 10}
        self.form_paddings = {'padx': 10, 'pady': 5}
        self.button_size = {'width': 150, 'height': 50}
        self.list_paddings = {'padx': 3, 'pady': 3}
        self.label_settings = {'anchor': 'e', 'width': 15}
        self.input_grid_settings = {'sticky': 'w'}
        self.entry_settings = {'width': 30}
        self.entry_settings_half = {'width': 20}

        # define the pixel size for buttons
        pixel = tk.PhotoImage(width=1, height=1)

        self.blank_img_button_settings = {'image': pixel, 'compound': 'c'}

        # these are the marker colors used in Resolve
        self.resolve_marker_colors = {
            "Blue": "#0000FF",
            "Cyan": "#00CED0",
            "Green": "#00AD00",
            "Yellow": "#F09D00",
            "Red": "#E12401",
            "Pink": "#FF44C8",
            "Purple": "#9013FE",
            "Fuchsia": "#C02E6F",
            "Rose": "#FFA1B9",
            "Lavender": "#A193C8",
            "Sky": "#92E2FD",
            "Mint": "#72DB00",
            "Lemon": "#DCE95A",
            "Sand": "#C4915E",
            "Cocoa": "#6E5143",
            "Cream": "#F5EBE1"
        }

        # these are the theme colors used in Resolve
        self.resolve_theme_colors = {
            'white': '#ffffff',
            'supernormal': '#C2C2C2',
            'normal': '#929292',
            'black': '#1F1F1F',
            'superblack': '#000000',
            'dark': '#282828',
            'red': '#E64B3D'
        }

        # CMD or CTRL?
        # use CMD for Mac
        if platform.system() == 'Darwin':
            self.ctrl_cmd_bind = "Command"
            self.alt_bind = "Mod2"
        # use CTRL for Windows
        else:
            self.ctrl_cmd_bind = "Control"
            self.alt_bind = "Alt"

        # use this variable to remember if the user said it's ok that resolve is not available to continue a process
        self.no_resolve_ok = False

    class main_window:
        pass

    def _create_or_open_window(self, parent_element=None, window_id=None, title=None, resizable=False,
                               close_action=None):

        # if the window is already opened somewhere, do this
        if window_id in self.windows:

            # bring the window to the top
            # self.windows[window_id].attributes('-topmost', 1)
            # self.windows[window_id].attributes('-topmost', 0)
            self.windows[window_id].lift()

            # then focus on it
            self.windows[window_id].focus_set()

            # but return false since we're not creating it
            return False

        else:
            # create a new window
            if parent_element is None:
                parent_element = self.root

            self.windows[window_id] = Toplevel(parent_element)

            # bring the transcription window to top
            # self.windows[window_id].attributes('-topmost', 'true')

            # set the window title
            self.windows[window_id].title(title)

            # is it resizable?
            if not resizable:
                self.windows[window_id].resizable(False, False)

            # use the default destroy_window function in case something else wasn't passed
            if close_action is None:
                close_action = lambda: self.destroy_window_(self.windows, window_id)

            # what happens when the user closes this window
            self.windows[window_id].protocol("WM_DELETE_WINDOW", close_action)

            return True

    def hide_main_window_frame(self, frame_name):
        '''
        Used to hide main window frames, but only if they're not invisible already
        :param frame_name:
        :return:
        '''

        # only attempt to remove the frame from the main window if it's known to be visible
        if frame_name in self.main_window_visible_frames:
            # first remove it from the view
            self.main_window.__dict__[frame_name].pack_forget()

            # then remove if from the visible frames list
            self.main_window_visible_frames.remove(frame_name)

            return True

        return False

    def show_main_window_frame(self, frame_name):
        '''
        Used to show main window frames, but only if they're not visible already
        :param frame_name:
        :return:
        '''

        # only attempt to show the frame from the main window if it's known not to be visible
        if frame_name not in self.main_window_visible_frames:
            # first show it
            self.main_window.__dict__[frame_name].pack()

            # then add it to the visible frames list
            self.main_window_visible_frames.append(frame_name)

            return True

        return False

    def update_main_window(self):
        '''
        Updates the main window GUI
        :return:
        '''

        # handle resolve related UI stuff
        global resolve

        # if resolve isn't connected or if there's a communication error
        if resolve is None:
            # hide resolve related buttons
            self.hide_main_window_frame('resolve_buttons_frame')

            # update the names of the transcribe buttons
            self.main_window.button5.config(text='Transcribe\nAudio')
            self.main_window.button6.config(text='Translate\nAudio to English')

            # if resolve is connected and the resolve buttons are not visible
        else:
            # show resolve buttons
            if self.show_main_window_frame('resolve_buttons_frame'):
                # but hide other buttons so we can place them back below the resolve buttons frame
                self.hide_main_window_frame('other_buttons_frame')

            # update the names of the transcribe buttons
            self.main_window.button5.config(text='Transcribe\nTimeline')
            self.main_window.button6.config(text='Translate\nTimeline to English')

        # now show the other buttons too if they're not visible already
        self.show_main_window_frame('other_buttons_frame')

        return

    def create_main_window(self):
        '''
        Creates the main GUI window using Tkinter
        :return:
        '''

        # any frames stored here in the future will be considered visible
        self.main_window_visible_frames = []

        # retrieve toolkit_ops object
        toolkit_ops_obj = self.toolkit_ops_obj

        # set the window size
        # self.root.geometry("350x440")

        # create the frame that will hold the resolve buttons
        self.main_window.resolve_buttons_frame = tk.Frame(self.root)

        # create the frame that will hold the other buttons
        self.main_window.other_buttons_frame = tk.Frame(self.root)

        # draw buttons

        # label1 = tk.Label(frame, text="Resolve Operations", anchor='w')
        # label1.grid(row=0, column=1, sticky='w', padx=10, pady=10)

        # resolve buttons frame row 1
        self.main_window.button1 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size,
                                             text="Copy Timeline\nMarkers to Same Clip",
                                             command=lambda: execute_operation('copy_markers_timeline_to_clip', self))
        self.main_window.button1.grid(row=1, column=1, **self.paddings)

        self.main_window.button2 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size,
                                             text="Copy Clip Markers\nto Same Timeline",
                                             command=lambda: execute_operation('copy_markers_clip_to_timeline', self))
        self.main_window.button2.grid(row=1, column=2, **self.paddings)

        # resolve buttons frame row 2
        self.main_window.button3 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size, text="Render Markers\nto Stills",
                                             command=lambda: execute_operation('render_markers_to_stills', self))
        self.main_window.button3.grid(row=2, column=1, **self.paddings)

        self.main_window.button4 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size, text="Render Markers\nto Clips",
                                             command=lambda: execute_operation('render_markers_to_clips', self))
        self.main_window.button4.grid(row=2, column=2, **self.paddings)

        # Other Frame Row 1
        self.main_window.button5 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size, text="Transcribe\nTimeline",
                                             command=lambda: toolkit_ops_obj.prepare_transcription_file(
                                                 toolkit_UI_obj=self))
        self.main_window.button5.grid(row=1, column=1, **self.paddings)

        self.main_window.button6 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size,
                                             text="Translate\nTimeline to English",
                                             command=lambda: toolkit_ops_obj.prepare_transcription_file(
                                                 toolkit_UI_obj=self, task='translate'))
        self.main_window.button6.grid(row=1, column=2, **self.paddings)

        self.main_window.button7 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size,
                                             text="Open\nTranscript", command=lambda: self.open_transcript())
        self.main_window.button7.grid(row=2, column=1, **self.paddings)

        self.main_window.button8 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings,
                                             **self.button_size,
                                             text="Open\nTranscription Log",
                                             command=lambda: self.open_transcription_log_window())
        self.main_window.button8.grid(row=2, column=2, **self.paddings)

        # self.main_window.link2 = Label(self.main_window.other_buttons_frame, text="project home", font=("Courier", 8), fg='#1F1F1F', cursor="hand2", anchor='s')
        # self.main_window.link2.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky='s')
        # self.main_window.link2.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/octimot/StoryToolkitAI"))

        # Other Frame row 2 (disabled for now)
        # self.main_window.button7 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Transcribe\nDuration Markers")
        # self.main_window.button7.grid(row=4, column=1, **self.paddings)
        # self.main_window.button8 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Translate\nDuration Markers to English")
        # self.main_window.button8.grid(row=4, column=1, **self.paddings)

        # self.main_window.button_test = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Test",
        #                        command=lambda: self.open_transcription_window())
        # self.main_window.button_test.grid(row=5, column=2, **self.paddings)

        # Make the window resizable false
        self.root.resizable(False, False)

        # update the window after it's been created
        self.root.after(500, self.update_main_window())

        logger.info("Starting StoryToolkitAI GUI")
        self.root.mainloop()

        return

    def open_transcription_settings_window(self, title="Transcription Settings",
                                           audio_file_path=None, name=None, task=None, unique_id=None):

        if self.toolkit_ops_obj is None or audio_file_path is None or unique_id is None:
            logger.error('Aborting. Unable to open transcription settings window.')
            return False

        # assign a unique_id for this window depending on the queue unique_id
        ts_window_id = 'ts-' + unique_id

        # what happens when the window is closed
        close_action = lambda ts_window_id=ts_window_id, unique_id=unique_id: \
            self.destroy_transcription_settings_window(ts_window_id, unique_id)

        # create a window for the transcription settings if one doesn't already exist
        if self._create_or_open_window(parent_element=self.root, window_id=ts_window_id, title=title,
                                       resizable=True, close_action=close_action):

            self.toolkit_ops_obj.update_transcription_log(unique_id=unique_id, **{'status': 'waiting user'})

            # place the window on top for a moment so that the user sees that he has to interact
            self.windows[ts_window_id].wm_attributes('-topmost', True)
            self.windows[ts_window_id].wm_attributes('-topmost', False)
            self.windows[ts_window_id].lift()

            ts_form_frame = tk.Frame(self.windows[ts_window_id])
            ts_form_frame.pack()

            # File items start here

            # NAME INPUT
            Label(ts_form_frame, text="Name", **self.label_settings).grid(row=1, column=1,
                                                                          **self.input_grid_settings,
                                                                          **self.form_paddings)
            name_var = StringVar(ts_form_frame)
            name_input = Entry(ts_form_frame, textvariable=name_var, **self.entry_settings)
            name_input.grid(row=1, column=2, **self.input_grid_settings, **self.form_paddings)
            name_input.insert(0, name)

            # FILE INPUT (disabled)
            Label(ts_form_frame, text="File", **self.label_settings).grid(row=2, column=1,
                                                                          **self.input_grid_settings,
                                                                          **self.form_paddings)

            file_path_var = StringVar(ts_form_frame)
            file_path_input = Entry(ts_form_frame, textvariable=file_path_var, **self.entry_settings)
            file_path_input.grid(row=2, column=2, **self.input_grid_settings, **self.form_paddings)
            file_path_input.insert(END, os.path.basename(audio_file_path))
            file_path_input.config(state=DISABLED)

            # SOURCE LANGUAGE INPUT
            Label(ts_form_frame, text="Source Language", **self.label_settings).grid(row=3, column=1,
                                                                                     **self.input_grid_settings,
                                                                                     **self.form_paddings)

            # try to get the languages from tokenizer
            # @todo is there a better way to do this using whisper functions?
            from whisper import tokenizer
            available_languages = tokenizer.LANGUAGES.values()

            if not available_languages or available_languages is None:
                available_languages = []

            language_var = StringVar(ts_form_frame)
            available_languages = sorted(available_languages)
            language_input = OptionMenu(ts_form_frame, language_var, *available_languages)
            language_input.grid(row=3, column=2, **self.input_grid_settings, **self.form_paddings)

            # TASK DROPDOWN

            # hold the selected task in this variable
            Label(ts_form_frame, text="Task", **self.label_settings).grid(row=4, column=1,
                                                                          **self.input_grid_settings,
                                                                          **self.form_paddings)

            if task is None:
                task = 'transcribe'

            task_var = StringVar(ts_form_frame, value=task)
            available_tasks = ['transcribe', 'translate', 'transcribe+translate']
            task_input = OptionMenu(ts_form_frame, task_var, *available_tasks)
            task_input.grid(row=4, column=2, **self.input_grid_settings, **self.form_paddings)

            # MODEL DROPDOWN
            # as options, use the list of whisper.avialable_models()
            # the selected value will be the whisper_model_name app setting
            Label(ts_form_frame, text="Transcription Model", **self.label_settings).grid(row=5, column=1,
                                                                                         **self.input_grid_settings,
                                                                                         **self.form_paddings)

            model_selected = self.stAI.get_app_setting('whisper_model_name', default_if_none='medium')
            model_var = StringVar(ts_form_frame, model_selected)
            model_input = OptionMenu(ts_form_frame, model_var, *whisper.available_models())
            model_input.grid(row=5, column=2, **self.input_grid_settings, **self.form_paddings)

            # DEVICE DROPDOWN
            Label(ts_form_frame, text="Device", **self.label_settings).grid(row=6, column=1,
                                                                            **self.input_grid_settings,
                                                                            **self.form_paddings)

            # prepare a list of available devices
            available_devices = ['auto', 'cpu']

            # and add cuda to the available devices, if it is available
            if torch.cuda.is_available():
                available_devices.append('CUDA')

            # the default selected value will be the whisper_device app setting
            device_selected = self.stAI.get_app_setting('whisper_device', default_if_none='auto')
            device_var = StringVar(ts_form_frame, value=device_selected)

            device_input = OptionMenu(ts_form_frame, device_var, *available_devices)
            device_input.grid(row=6, column=2, **self.input_grid_settings, **self.form_paddings)

            # INITIAL PROMPT INPUT
            Label(ts_form_frame, text="Initial Prompt", **self.label_settings).grid(row=7, column=1,
                                                                            sticky='nw',
                                                                          #**self.input_grid_settings,
                                                                          **self.form_paddings)
            #prompt_var = StringVar(ts_form_frame)
            prompt_input = Text(ts_form_frame, wrap=tk.WORD, height=4, **self.entry_settings)
            prompt_input.grid(row=7, column=2, **self.input_grid_settings, **self.form_paddings)
            prompt_input.insert(END, " - How are you?\n - I'm fine, thank you.")

            # START BUTTON

            # add all the settings entered by the use into a nice dictionary
            transcription_config = dict(name=name_input.get(), language='English', beam_size=5, best_of=5)

            Label(ts_form_frame, text="", **self.label_settings).grid(row=10, column=1,
                                                                      **self.input_grid_settings, **self.paddings)
            start_button = Button(ts_form_frame, text='Start')
            start_button.grid(row=10, column=2, **self.input_grid_settings, **self.paddings)
            start_button.config(command=lambda audio_file_path=audio_file_path,
                                               unique_id=unique_id,
                                               ts_window_id=ts_window_id:
            self.start_transcription_button(ts_window_id,
                                            audio_file_path=audio_file_path,
                                            unique_id=unique_id,
                                            language=language_var.get(),
                                            task=task_var.get(),
                                            name=name_var.get(),
                                            model=model_var.get(),
                                            device=device_var.get(),
                                            initial_prompt=prompt_input.get(1.0, END)
                                            )
                                )

    def start_transcription_button(self, transcription_settings_window_id=None, **transcription_config):
        '''
        This sends the transcription to the transcription queue via toolkit_ops object,
        but also closes the trancription window forever
        :param transcription_settings_window_id:
        :param transcription_config:
        :return:
        '''

        # send transcription to queue
        self.toolkit_ops_obj.add_to_transcription_queue(**transcription_config)

        # destroy transcription config window
        self.destroy_window_(self.windows, window_id=transcription_settings_window_id)

    def destroy_transcription_settings_window(self, window_id, unique_id, parent_element=None):

        if (messagebox.askyesno(title="Cancel Transcription",
                                message='Are you sure you want to cancel this transcription?')):

            # assume the window is references in the windows dict
            if parent_element is None:
                parent_element = self.windows

            self.toolkit_ops_obj.update_transcription_log(unique_id=unique_id, status='canceled')

            # call the default destroy window function
            self.destroy_window_(parent_element=self.windows, window_id=window_id)

        return False

    def destroy_window_(self, parent_element, window_id):
        '''
        This makes sure that the window reference is deleted when a user closes a window
        :param parent_element:
        :param window_id:
        :return:
        '''
        # first destroy the window
        parent_element[window_id].destroy()

        # then remove its reference
        del parent_element[window_id]

    def open_transcript(self, **options):
        '''
        This prompts the user to open a transcript file and then opens it a transcript window
        :return:
        '''

        # did we ever save a target dir for this project?
        last_target_dir = None
        if resolve and current_project is not None:
            last_target_dir = self.stAI.get_project_setting(project_name=current_project, setting_key='last_target_dir')

        # ask user which transcript to open
        transcription_json_file_path = self.ask_for_target_file(filetypes=[("Json files", "json")],
                                                                target_dir=last_target_dir)

        # abort if user cancels
        if not transcription_json_file_path:
            return False

        # why not open the transcript in a transcription window?
        self.open_transcription_window(transcription_file_path=transcription_json_file_path, **options)

    def open_transcription_window(self, title=None, transcription_file_path=None, srt_file_path=None):

        if self.toolkit_ops_obj is None:
            logger.error('Cannot open transcription window. A toolkit operations object is needed to continue.')
            return False

        # Note: most of the transcription window functions are stored in the TranscriptEdit class

        # only continue if the transcription path was passed and the file exists
        if transcription_file_path is None or os.path.exists(transcription_file_path) is False:
            logger.error('The transcription file {} doesn\'t exist'.format(transcription_file_path))
            return False

        # now read the transcription file contents
        transcription_json = \
            self.toolkit_ops_obj.get_transcription_file_data(transcription_file_path=transcription_file_path)

        # if no srt_file_path was passed
        if srt_file_path is None:

            # try to use the file path in the transcription json
            if 'srt_file_path' in transcription_json:
                srt_file_path = transcription_json['srt_file_path']

        # try to see if we have a srt path or not
        if srt_file_path is not None:

            # if not we're dealing with an absolute path
            if not os.path.isabs(srt_file_path):
                # assume that the srt is in the same folder as the transcription
                srt_file_path = os.path.join(os.path.dirname(transcription_file_path), srt_file_path)

        # hash the url and use it as a unique id for the transcription window
        t_window_id = hashlib.md5(transcription_file_path.encode('utf-8')).hexdigest()

        # use the transcription file name without the extension as a window title if a title wasn't passed
        if title is None:

            # use the name in the transcription json for the window title
            if 'name' in transcription_json:
                title = transcription_json['name']
            # if there is no name in the transcription json, simply use the name of the file
            else:
                title = os.path.splitext(os.path.basename(transcription_file_path))[0]

        # create a window for the transcript if one doesn't already exist
        if self._create_or_open_window(parent_element=self.root, window_id=t_window_id, title=title, resizable=True):

            # add the path to the transcription_file_paths dict in case we need it later
            self.t_edit_obj.transcription_file_paths[t_window_id] = transcription_file_path

            # initialize the transcript_segments_ids for this window
            self.t_edit_obj.transcript_segments_ids[t_window_id] = {}

            # create a header frame to hold stuff above the transcript text
            header_frame = tk.Frame(self.windows[t_window_id])
            header_frame.place(anchor='nw', relwidth=1)

            # THE MAIN TEXT ELEMENT
            # create a frame for the text element
            text_form_frame = tk.Frame(self.windows[t_window_id])
            text_form_frame.pack(pady=50, expand=True, fill='both')

            # does the json file actually contain transcript segments generated by whisper?
            if 'segments' in transcription_json:

                # set up the text element where we'll add the actual transcript
                text = Text(text_form_frame, font=('Courier', 16), width=45, height=30, padx=5, pady=5, wrap=tk.WORD,
                                                    background=self.resolve_theme_colors['black'],
                                                    foreground=self.resolve_theme_colors['normal'])

                # we'll need to count segments soon
                segment_count = 0

                # use this to calculate the longest segment (but don't accept anything under 30)
                longest_segment_num_char = 40

                # initialize the segments list for later use
                # this should contain all the segments in the order they appear
                self.t_edit_obj.transcript_segments[t_window_id] = []

                # initialize line numbers
                line = 0

                # take each transcript segment
                for t_segment in transcription_json['segments']:

                    # start counting the lines
                    line = line+1

                    # add a reference for its id
                    if 'id' in t_segment:
                        self.t_edit_obj.transcript_segments_ids[t_window_id][line] = t_segment['id']
                    # throw an error otherwise, it might be a problem on the long run
                    else:
                        logger.error('Line {} in {} doesn\'t have an id.'.format(line, transcription_file_path))

                    # if there is a text element, simply insert it in the window
                    if 'text' in t_segment:

                        # count the segments
                        segment_count = segment_count + 1

                        # add the current segment to the segments list
                        self.t_edit_obj.transcript_segments[t_window_id].append(t_segment)

                        # get the text index before inserting the new segment
                        # (where the segment will start)
                        new_segment_start = text.index(INSERT)

                        # insert the text
                        text.insert(END, t_segment['text'].strip() + ' ')

                        # if this is the longest segment, keep that in mind
                        if len(t_segment['text']) > longest_segment_num_char:
                            longest_segment_num_char = len(t_segment['text'])

                        # get the text index of the last character of the new segment
                        new_segment_end = text.index("end-1c")

                        # keep in mind the segment start and end times of each segment
                        segment_start_time = t_segment['start']
                        end_start_time = t_segment['start']

                        # this works if we're aiming to move away from line based start_end times
                        #tag_id = 'segment-' + str(segment_count)
                        #text.tag_add(tag_id, new_segment_start, new_segment_end)
                        #text.tag_config(tag_id)
                        #text.tag_bind(tag_id, "<Button-1>", lambda e,
                        #                                           segment_start_time=segment_start_time:
                        #                            toolkit_ops_obj.go_to_time(segment_start_time))

                        # bind CMD/CTRL+click events to the text:
                        # on click, select text
                        # text.tag_bind(tag_id, "<"+self.ctrl_cmd_bind+"-Button-1>", lambda e, line_id=line_id,t_window_id=t_window_id:
                        #    self.t_edit_obj.select_text_lines(event=e, text_element=text,
                        #                                      window_id=t_window_id, line_id=line_id)
                        #              )

                        # for now, just add 2 new lines after each segment:
                        text.insert(END, '\n')

                # make the text read only
                # and take into consideration the longest segment to adjust the width of the window
                if longest_segment_num_char > 60:
                    longest_segment_num_char = 60
                text.config(state=DISABLED, width=longest_segment_num_char)

                # add undo/redo
                text.config(undo=True)

                # set the top, in-between and bottom text spacing
                text.config(spacing1=0, spacing2=0.2, spacing3=5)

                # then show the text element
                text.pack(anchor='w', expand=True, fill='both')

                # create a footer frame that holds stuff on the bottom of the transcript window
                footer_frame = tk.Frame(self.windows[t_window_id])
                footer_frame.place(relwidth=1, anchor='sw', rely=1)

                # add a status label to print out current transcription status
                status_label = Label(footer_frame, text="", anchor='w', foreground=self.resolve_theme_colors['normal'])
                status_label.pack(side=tk.LEFT, **self.paddings)


                # bind shift click events to the text
                # text.bind("<Shift-Button-1>", lambda e:
                #         self.t_edit_obj.select_text_lines(event=e, text_element=text, window_id=t_window_id))

                select_options = {'window_id': t_window_id, 'text_element': text}

                # bind all key presses to transcription window actions
                self.windows[t_window_id].bind("<KeyPress>",
                                               lambda e:
                                               self.t_edit_obj.transcription_window_keypress(event=e,
                                                                                             **select_options))

                # bind CMD/CTRL + key presses to transcription window actions
                # self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-KeyPress>",
                #                               lambda e:
                #                               self.t_edit_obj.transcription_window_keypress(event=e, special_key='cmd'
                #                                                                             **select_options))

                # bind all mouse clicks on text
                text.bind("<Button-1>", lambda e,
                                               select_options=select_options:
                                                    self.t_edit_obj.transcription_window_mouse(e,
                                                                                               **select_options))

                # bind CMD/CTRL + mouse Clicks to text
                text.bind("<"+self.ctrl_cmd_bind+"-Button-1>",
                          lambda e, select_options=select_options:
                            self.t_edit_obj.transcription_window_mouse(e,
                                                                       special_key='cmd',
                                                                       **select_options))


                # bind ALT/OPT + mouse Click to edit transcript
                text.bind("<"+self.alt_bind+"-Button-1>",
                          lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id, text=text,
                                                                    status_label=status_label)
                          )

                # bind CMD/CTRL + e to edit transcript
                self.windows[t_window_id].bind("<"+self.ctrl_cmd_bind+"-e>",
                          lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id, text=text,
                                                                    status_label=status_label)
                          )

                # bind the FocusOut of the text so that we save the new text when done
                # text.bind("<FocusOut>", lambda e: self.t_edit_obj.save_transcript(window_id=t_window_id, text=text))

                #self.windows[t_window_id].bind("<Shift-Up>", lambda e: self.t_edit_obj.select_text_lines(e, special_key='Shift', **select_options))
                #self.windows[t_window_id].bind("<Shift-Down>", lambda e: self.t_edit_obj.select_text_lines(e, special_key='Shift', **select_options))
                # self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-Up>", lambda e: self.t_edit_obj.select_text_lines(e, special_key=self.ctrl_cmd_bind, **select_options))
                # self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-Down>", lambda e: self.t_edit_obj.select_text_lines(e, special_key=self.ctrl_cmd_bind, **select_options))


                # b_test = tk.Button(footer_frame, text='Search', command=lambda: search(),
                #                font=20, bg='white').grid(row=1, column=3, sticky='w', **self.paddings)

                # THE SEARCH FIELD
                # first the label
                Label(header_frame, text="Find:", anchor='w').pack(side=tk.LEFT, **self.paddings)

                # then the search text entry
                # first the string variable that "monitors" what's being typed in the input
                search_str = tk.StringVar()

                # the search input
                search_input = Entry(header_frame, textvariable=search_str)

                # and a callback for when the search_str is changed
                search_str.trace("w", lambda name, index, mode, search_str=search_str, text=text,
                                             t_window_id=t_window_id:
                self.t_edit_obj.search_text(search_str=search_str,
                                            text_element=text, window_id=t_window_id))

                search_input.pack(side=tk.LEFT, **self.paddings)

                search_input.bind('<Return>', lambda e, text=text, t_window_id=t_window_id:
                                self.t_edit_obj.cycle_through_results(text_element=text, window_id=t_window_id))

                search_input.bind('<FocusIn>', lambda e, t_window_id=t_window_id:
                                            self.t_edit_obj.set_typing_in_window(e, t_window_id, typing=True))
                search_input.bind('<FocusOut>', lambda e, t_window_id=t_window_id:
                                            self.t_edit_obj.set_typing_in_window(e, t_window_id, typing=False))

                # KEEP ON TOP BUTTON
                on_top_button = tk.Button(header_frame, text="Keep on top", takefocus=False)
                # add the command function here
                on_top_button.config(command=lambda on_top_button=on_top_button, t_window_id=t_window_id:
                                            self.window_on_top_button(button=on_top_button, window_id=t_window_id)
                                                                 )
                on_top_button.pack(side=tk.RIGHT, **self.paddings, anchor='e')

                # keep the transcript window on top or not according to the config
                # and also update the initial text on the respective button
                self.window_on_top_button(button=on_top_button,
                                          window_id=t_window_id,
                                          on_top=stAI.get_app_setting('transcripts_always_on_top',
                                                                      default_if_none=False)
                                          )

                # IMPORT SRT BUTTON
                if srt_file_path:
                    import_srt_button = tk.Button(footer_frame,
                                                  text="Import SRT into Bin",
                                                  takefocus=False,
                                                  command=lambda: mots_resolve.import_media(srt_file_path)
                                                  )
                    import_srt_button.pack(side=tk.RIGHT, **self.paddings, anchor='e')


                # SYNC BUTTON

                sync_button = tk.Button(header_frame, takefocus=False)
                sync_button.config(command=lambda sync_button=sync_button, window_id=t_window_id:
                                                self.t_edit_obj.sync_with_playhead_button(
                                                    button=sync_button,
                                                    window_id=t_window_id)
                                                                   )

                # LINK TO TIMELINE BUTTON

                # is this transcript linked to the current timeline?
                global current_timeline
                global current_project

                # prepare an empty link button for now, and only show it when/if resolve starts
                link_button = tk.Button(footer_frame)
                link_button.config(command=lambda link_button=link_button,
                                                  transcription_file_path=transcription_file_path:
                                            self.t_edit_obj.link_to_timeline_button(
                                                button=link_button,
                                                transcription_file_path=transcription_file_path)
                                                               )

                # RE-TRANSCRIBE BUTTON

                # only show this button if we have the original audio file path
                # if 'audio_file_path' in transcription_json:
                #
                #     audio_file_path = transcription_json['audio_file_path']
                #
                #     print(audio_file_path)
                #     print(os.path.join(os.path.dirname(transcription_file_path), audio_file_path))
                #
                #
                #     # but that file is usually stored next to the transcription file
                #     # so check if the audio file is in the same directory as the transcription file
                #     if os.path.exists(os.path.join(os.path.dirname(transcription_file_path), audio_file_path)) :
                #
                #         transcribe_button = tk.Button(footer_frame, text="Re-Transcribe",)
                #         transcribe_button.config(command=lambda audio_file_path=audio_file_path,title=title:
                #                                         self.open_transcription_settings_window(
                #                                             audio_file_path=audio_file_path,
                #                                             name=title
                #                                         )
                #                        )
                #         transcribe_button.pack(side=tk.LEFT, **self.paddings, anchor='e')

                # MARK IN BUTTON
                # mark_in_button = Button(footer_frame, text='Mark In')
                # mark_in_button.pack(side=tk.LEFT, **self.paddings)
                # mark_in_button.config(command= lambda text=text, t_window_id=t_window_id:
                #                  self.toolkit_ops_obj.mark_in(window_id=t_window_id))

                # MARK OUT BUTTON
                # mark_out_button = Button(footer_frame, text='Mark Out')
                # mark_out_button.pack(side=tk.LEFT, **self.paddings)
                # mark_out_button.config(command= lambda text=text, t_window_id=t_window_id:
                #                  self.toolkit_ops_obj.mark_out(window_id=t_window_id))

                # prepare a label to use to send errors to the user
                # error_label = Label(footer_frame, text="", anchor='w').grid(row=2, column=1, sticky='w', **self.paddings)

                # start the transcription window self-updating process
                # here we send the update transcription window function a few items that need to be updated
                self.windows[t_window_id].after(500, lambda link_button=link_button,
                                                            t_window_id=t_window_id,
                                                            transcription_file_path=transcription_file_path:
                    self.update_transcription_window(window_id=t_window_id,
                                                     link_button=link_button,
                                                     sync_button=sync_button,
                                                     transcription_file_path=transcription_file_path,
                                                     text=text)
                                                )



            # if no transcript was found in the json file, alert the user
            else:
                not_a_transcription_message = 'The file {} isn\'t a transcript.'.format(
                    os.path.basename(transcription_file_path))

                self.notify_via_messagebox(title='Not a transcript file',
                                           message=not_a_transcription_message,
                                           type='warning'
                                           )
                self.destroy_window_(self.windows, t_window_id)

    def update_transcription_window(self, window_id, **update_attr):
        '''
        Auto-updates a transcription window and then calls itself again after a few seconds.
        :param window_id:
        :param update_attr:
        :return:
        '''

        # check if the current timeline is still linked to this transcription window
        global current_timeline
        global current_project
        global resolve
        global current_tc
        global current_timeline_fps

        # only check if resolve is connected
        if resolve:

            # is there a link between the transcription and the resolve timeline?
            link, _ = self.toolkit_ops_obj.get_transcription_to_timeline_link(
                transcription_file_path=update_attr['transcription_file_path'],
                timeline_name=current_timeline['name'],
                project_name=current_project)

            # update the link button text if it was passed in the call
            if 'link_button' in update_attr:

                # the link button text depends on the above link
                if link:
                    link_button_text = 'Unlink from Timeline'
                    # update_attr['error_label'].config(text='')
                else:
                    link_button_text = 'Link to Timeline'

                    # if there's no link, let the user know
                    # update_attr['error_label'].config(text='Timeline mismatch')

                # update the link button on the transcription window
                update_attr['link_button'].config(text=link_button_text)
                update_attr['link_button'].pack(side=tk.RIGHT, **self.paddings, anchor='e')

            if window_id not in self.t_edit_obj.sync_with_playhead:
                self.t_edit_obj.sync_with_playhead[window_id] = False

            # update the sync button if it was passed in the call
            if 'sync_button' in update_attr:
                if self.t_edit_obj.sync_with_playhead[window_id]:
                    sync_button_text = "Don't sync"
                else:
                    sync_button_text = "Sync"

                # update the link button on the transcription window
                update_attr['sync_button'].config(text=sync_button_text)
                update_attr['sync_button'].pack(side=tk.RIGHT, **self.paddings, anchor='e')

            # how many segments / lines does the transcript on this window contain?
            max_lines = len(self.t_edit_obj.transcript_segments[window_id])

            # create the current_window_tc reference if it doesn't exist
            if window_id not in self.t_edit_obj.current_window_tc:
                self.t_edit_obj.current_window_tc[window_id] = ''

            # HOW WE CONVERT THE RESOLVE PLAYHEAD TIMECODE TO TRANSCRIPT LINES

            # only do this if the sync is on for this window
            # and if the timecode in resolve has changed compared to last time
            if self.t_edit_obj.sync_with_playhead[window_id] \
                and self.t_edit_obj.current_window_tc[window_id] != current_tc:

                # initialize the timecode object for the current_tc
                current_tc_obj = Timecode(current_timeline_fps, current_tc)

                # initialize the timecode object for the timeline start_tc
                timeline_start_tc_obj = Timecode(current_timeline_fps, current_timeline['startTC'])

                # subtract the two timecodes to get the corresponding transcript seconds
                if current_tc_obj > timeline_start_tc_obj:
                    transcript_tc = current_tc_obj - timeline_start_tc_obj

                    # so we can now convert the current tc into seconds
                    transcript_sec = transcript_tc.float

                # but if the current_tc_obj is at 0 or less
                else:
                    transcript_sec = 0

                # remove the current_time segment first
                update_attr['text'].tag_delete('current_time')

                # find out on which text segment we are now
                num = 0
                line = 1
                while num < max_lines:

                    # if the transcript timecode in seconds is between the start and the end of this line
                    if float(self.t_edit_obj.transcript_segments[window_id][num]['start']) <= transcript_sec \
                            < float(self.t_edit_obj.transcript_segments[window_id][num]['end'])-0.01:
                        line = num + 1

                        # set the line as the active segment on the timeline
                        self.t_edit_obj.set_active_segment(window_id, update_attr['text'], line)

                    num = num + 1

                update_attr['text'].tag_config('current_time', foreground=self.resolve_theme_colors['white'])

                # highlight current line on transcript
                # update_attr['text'].tag_add('current_time')

                # now remember that we did the update for the current timecode
                self.t_edit_obj.current_window_tc[window_id] = current_tc


        # hide some stuff if resolve isn't connected
        else:
            update_attr['link_button'].grid_forget()
            update_attr['sync_button'].grid_forget()

        # update again after 500ms
        # @todo remove the auto-update and place the call where is needed to prevent constant redrawing of stuff
        self.windows[window_id].after(500, lambda window_id=window_id, update_attr=update_attr:
                self.update_transcription_window(window_id, **update_attr))

    def update_transcription_log_window(self):

        # only do this if the transcription window exists
        # and if the log exists
        if self.toolkit_ops_obj.transcription_log and 't_log' in self.windows:

            # first destroy anything that the window might have held
            list = self.windows['t_log'].winfo_children()
            for l in list:
                l.destroy()

            # create a canvas to hold all the log items in the window
            log_canvas = tk.Canvas(self.windows['t_log'], borderwidth=0)

            # create a frame for the log items
            log_frame = tk.Frame(log_canvas)

            # create a scrollbar to use with the canvas
            scrollbar = Scrollbar(self.windows['t_log'], command=log_canvas.yview)

            # attach the scrollbar to the log_canvas
            log_canvas.config(yscrollcommand=scrollbar.set)

            # add the scrollbar to the window
            scrollbar.pack(side=RIGHT, fill=Y)

            # add the canvas to the window
            log_canvas.pack(side=LEFT, fill=BOTH, expand=True)

            # show the frame in the canvas
            log_canvas.create_window((4,4), window=log_frame, anchor="nw")

            # make scroll region adjust each time the canvas changes in size
            # and also adjust the width according to the frame inside it
            log_frame.bind("<Configure>", lambda event, log_canvas=log_canvas:
                                                log_canvas.configure(scrollregion=log_canvas.bbox("all"),
                                                                     width=event.width
                                                                     ))

            # populate the log frame with the transcription items from the transcription log
            num = 0
            for t_item_id, t_item in self.toolkit_ops_obj.transcription_log.items():

                num = num + 1

                if 'name' not in t_item:
                    t_item['name'] = 'Unknown'

                label_name = Label(log_frame, text=t_item['name'], anchor='w', width=40)
                label_name.grid(row=num, column=1, **self.list_paddings, sticky='w')

                if 'status' not in t_item:
                    t_item['status'] = ''

                label_status = Label(log_frame, text=t_item['status'], anchor='w', width=15)
                label_status.grid(row=num, column=2, **self.list_paddings, sticky='w')

                # make the label clickable as soon as we have a file path for it in the log
                if 'json_file_path' in t_item and t_item['json_file_path'] != '':
                    # first assign variables to pass it easily to lambda
                    json_file_path = t_item['json_file_path']
                    name = t_item['name']

                    # now bind the button event
                    # the lambda needs all this code to "freeze" the current state of the variables
                    # otherwise it's going to only use the last value of the variable in the for loop
                    # for eg. instead of having 3 different value for the variable "name",
                    # lambda will only use the last value in the for loop
                    label_name.bind("<Button-1>",
                                    lambda e,
                                           json_file_path=json_file_path,
                                           name=name:
                                    self.open_transcription_window(title=name,
                                                                   transcription_file_path=json_file_path)
                                    )
                    label_status.bind("<Button-1>",
                                      lambda e,
                                             json_file_path=json_file_path,
                                             name=name:
                                      self.open_transcription_window(title=name,
                                                                     transcription_file_path=json_file_path)
                                      )

    def open_transcription_log_window(self):

        # create a window for the transcription log if one doesn't already exist
        if (self._create_or_open_window(parent_element=self.root,
                                        window_id='t_log', title='Transcription Log', resizable=True)):
            # and then call the update function to fill the window up
            self.update_transcription_log_window()

            return True

    def ask_for_target_dir(self, title=None, target_dir=None):

        # use the global initial_target_dir
        global initial_target_dir

        # if an initial target dir was passed
        if target_dir is not None:
            # assign it as the initial_target_dir
            initial_target_dir = target_dir

        # put the UI on top
        # self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog where can we find the directory
        if title == None:
            title = "Where should we save the files?"
        target_dir = filedialog.askdirectory(title=title, initialdir=initial_target_dir)

        # what happens if the user cancels
        if not target_dir:
            return False

        # remember which directory the user selected for next time
        initial_target_dir = target_dir

        return target_dir

    def ask_for_target_file(self, filetypes=[("Audio files", ".mp4 .wav .mp3")], target_dir=None, multiple=False):
        global initial_target_dir

        # if an initial target_dir was passed
        if target_dir is not None:
            # assign it as the initial_target_dir
            initial_target_dir = target_dir

        # put the UI on top
        # self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog which file to use
        if not multiple:
            target_file = filedialog.askopenfilename(title="Choose a file", initialdir=initial_target_dir,
                                                     filetypes=filetypes)
        else:
            target_file = filedialog.askopenfilenames(title="Choose the files", initialdir=initial_target_dir,
                                                     filetypes=filetypes)

        # what happens if the user cancels
        if not target_file:
            return False

        # remember what the user selected for next time
        initial_target_dir = os.path.dirname(target_file if isinstance(target_file, str) else target_file[0])

        return target_file

    def window_on_top(self, window_id=None, on_top=None):

        if window_id is not None:

            # does the window exist?
            if window_id in self.windows:

                # keep the window on top if on_top is true
                if on_top is not None and on_top:
                    self.windows[window_id].wm_attributes("-topmost", 1)
                    return True
                # don't keep the window on top if on top is false
                elif on_top is not None:
                    self.windows[window_id].wm_attributes("-topmost", 0)
                    return False
                # if the on top variable wasn't passed
                else:
                    # toggle between on and off
                    topmost = self.windows[window_id].wm_attributes("-topmost")
                    self.windows[window_id].wm_attributes("-topmost", not topmost)

                    # and return the current state
                    return self.windows[window_id].wm_attributes("-topmost")

    def window_on_top_button(self, button=None, window_id=None, on_top=None):

        # ask the UI to keep (or not) the window with this window_id on_top
        if self.window_on_top(window_id=window_id, on_top=on_top):

            # if the reply is true, it means that the window will be kept on top
            # therefore the button needs to read the opposite action
            button.config(text="Don't keep on top")
            return True
        else:
            # and the opposite if the window will not be kept on top
            button.config(text="Keep on top")
            return False

    def notify_via_os(self, title, text, debug_message):
        """
        Uses OS specific tools to notify the user

        :param title:
        :param text:
        :param debug_message:
        :return:
        """

        # log and print to console first
        logger.info(debug_message)

        # notify the user depending on which platform they're on
        if platform.system() == 'Darwin':  # macOS
            os.system("""
                                                    osascript -e 'display notification "{}" with title "{}"'
                                                    """.format(text, title))

        # @todo OS notifications on other platforms
        elif platform.system() == 'Windows':  # Windows
            return
        else:  # linux variants
            return

    def notify_via_messagebox(self, type='info', message_log=None, message=None, **options):

        if message_log is None:
            message_log = message

        # alert the user using the messagebox according to the type
        # and log the message
        if type == 'error':
            messagebox.showerror(message=message, **options)
            logger.error(message)

        elif type == 'info':
            messagebox.showinfo(message=message, **options)
            logger.info(message)

        elif type == 'warning':
            messagebox.showwarning(message=message, **options)
            logger.warning(message)


class ToolkitOps:

    def __init__(self, stAI=None):

        # this will be used to store all the transcripts that are ready to be transcribed
        self.transcription_queue = {}

        # keep a reference to the StoryToolkitAI object here if one was passed
        self.stAI = stAI

        # transcription queue thread - this will be useful when trying to figure out
        # if there's any transcription thread active or not
        self.transcription_queue_thread = None

        # use these attributes for the transcription items (both queue and log)
        # this will be useful in case we need to add additional attributes to the transcription items
        # so that we don't have to update every single function that is using the transcription items
        self.transcription_item_attr = ['name', 'audio_file_path', 'translate', 'info', 'status',
                                        'json_file_path', 'srt_file_path', 'txt_file_path']

        # transcription log - this keeps a track of all the transcriptions
        self.transcription_log = {}

        # this is used to get fast the name of what is being transcribed currently
        self.transcription_queue_current_name = None

        # declare this as none for now so we know it exists
        self.toolkit_UI_obj = None

        # use this to store the whisper model later
        self.whisper_model = None

        # load the whisper model from the config
        # we're recommending the medium model for better accuracy vs. time it takes to process
        # if in doubt use the large model but that will need more time
        self.whisper_model_name = self.stAI.get_app_setting(setting_name='whisper_model_name', default_if_none='medium')

        # get the whisper device setting
        # currently, the setting may be cuda, cpu or auto
        self.whisper_device = stAI.get_app_setting('whisper_device', 'auto')

        self.whisper_device = self.whisper_device_select(self.whisper_device)

        # start the resolve thread
        # with this, resolve should be constantly polled for data
        self.poll_resolve_thread()

        # toolkit_UI_obj.create_transcription_settings_window()
        # time.sleep(120)
        # return

    def whisper_device_select(self, device):
        '''
        A standardized way of selecting the right whisper device
        :param device:
        :return:
        '''

        # if the whisper device is set to cuda
        if self.whisper_device in ['cuda', 'CUDA', 'gpu', 'GPU']:
            # use CUDA if available
            if torch.cuda.is_available():
                self.whisper_device = device = torch.device('cuda')
            # or let the user know that cuda is not available and switch to cpu
            else:
                logger.error('CUDA not available. Switching to cpu.')
                self.whisper_device = device = torch.device('cpu')
        # if the whisper device is set to cpu
        elif self.whisper_device in ['cpu', 'CPU']:
            self.whisper_device = device = torch.device('cpu')
        # any other setting, defaults to automatic selection
        else:
            # use CUDA if available
            self.whisper_device = device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        logger.info('Using {} for Torch / Whisper.'.format(device))

        return self.whisper_device

    def prepare_transcription_file(self, toolkit_UI_obj=None, task=None, unique_id=None):
        '''
        This asks the user where to save the transcribed files,
         it choses between transcribing an existing timeline (and first starting the render process)
         and then passes the file to the transcription config

        :param toolkit_UI_obj:
        :param task:
        :param audio_file:
        :return: bool
        '''

        # check if there's a UI object available
        if not self.is_UI_obj_available(toolkit_UI_obj):
            return False

        # get info from resolve
        try:
            resolve_data = mots_resolve.get_resolve_data()
        # in case of exception still create a dict with an empty resolve object
        except:
            resolve_data = {'resolve': None}

        # set an empty target directory for future use
        target_dir = ''

        # if Resolve is available and the user has an open timeline, render the timeline to an audio file
        if resolve_data['resolve'] != None and 'currentTimeline' in resolve_data and \
                resolve_data['currentTimeline'] != '' and resolve_data['currentTimeline'] is not None:

            # reset any potential yes that the user might have said when asked to continue without resolve
            toolkit_UI_obj.no_resolve_ok = False

            # did we ever save a target dir for this project?
            last_target_dir = self.stAI.get_project_setting(project_name=current_project, setting_key='last_target_dir')

            # ask the user where to save the files
            while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
                logger.info("Prompting user for render path.")
                target_dir = toolkit_UI_obj.ask_for_target_dir(target_dir=last_target_dir)

                # remember this target_dir for the next time we're working on this project
                # (but only if it was selected by the user)
                if target_dir and target_dir != last_target_dir:
                    self.stAI.save_project_setting(project_name=current_project,
                                                   setting_key='last_target_dir', setting_value=target_dir)

                # cancel if the user presses cancel
                if not target_dir:
                    logger.info("User canceled transcription operation.")
                    return False

            # get the current timeline from Resolve
            currentTimelineName = resolve_data['currentTimeline']['name']

            # generate a unique id to keep track of this file in the queue and transcription log
            if unique_id is None:
                unique_id = self._generate_transcription_unique_id(name=currentTimelineName)

            # update the transcription log
            # @todo this doesn't work - maybe due to resolve API taking over,
            #   so we should try to move it to another thread?
            self.add_to_transcription_log(unique_id=unique_id, name=currentTimelineName, status='rendering')

            # use transcription_WAV render preset if it exists
            # transcription_WAV is an Audio only custom render preset that renders Linear PCM codec in a Wave format instead
            # of Quicktime mp4; this is just to work with wav files instead of mp4 to improve compatibility.
            if 'transcription_WAV' in resolve_data['renderPresets']:
                render_preset = 'transcription_WAV'
            else:
                render_preset = 'Audio Only'

            # let the user know that we're starting the render
            toolkit_UI_obj.notify_via_os("Starting Render", "Starting Render in Resolve",
                                         "Saving into {} and starting render.".format(target_dir))

            # render the timeline in Resolve
            rendered_files = mots_resolve.render_timeline(target_dir, render_preset, True, False, False, True)

            # now open up the transcription settings window
            for rendered_file in rendered_files:
                self.start_transcription_config(audio_file_path=rendered_file,
                                                name=currentTimelineName,
                                                task=task, unique_id=unique_id)

        # if resolve is not available
        else:

            # ask the user if they want to simply transcribe a file from the drive
            if toolkit_UI_obj.no_resolve_ok \
                    or messagebox.askyesno(message='A Resolve Timeline is not available.\n\n'
                                                    'Do you want to transcribe existing audio files instead?'):

                # remember that the user said it's ok to continue without resolve
                toolkit_UI_obj.no_resolve_ok = True

                # ask the user for the target files
                target_files = toolkit_UI_obj.ask_for_target_file(multiple=True)

                # add it to the transcription list
                if target_files:

                    for target_file in target_files:

                        # the file name also becomes currentTimelineName for future use
                        file_name = os.path.basename(target_file)

                        # a unique id is also useful to keep track
                        unique_id = self._generate_transcription_unique_id(name=file_name)

                        # now open up the transcription settings window
                        self.start_transcription_config(audio_file_path=target_file,
                                                        name=file_name,
                                                        task=task, unique_id=unique_id)

                    return True

                # or close the process if the user canceled
                else:
                    return False

            # close the process if the user doesn't want to transcribe an existing file
            else:
                return False

    def start_transcription_config(self, audio_file_path=None, name=None, task=None, unique_id=None):
        '''
        Opens up a modal to allow the user to configure and start the transcription process for each file
        :return:
        '''

        # check if there's a UI object available
        if not self.is_UI_obj_available():
            return False

        # open up the transcription settings window via Toolkit_UI
        return self.toolkit_UI_obj.open_transcription_settings_window(title="Transcription Settings: " + name,
                                                                      name=name,
                                                                      audio_file_path=audio_file_path, task=task,
                                                                      unique_id=unique_id)

    def add_to_transcription_log(self, unique_id=None, **attribute):
        '''
        This adds items to the transcription log and opens the transcription log window
        :param toolkit_UI_obj:
        :param unique_id:
        :param attribute:
        :return:
        '''
        # if a unique id was passed, add the file to the log
        if unique_id:

            # then simply update the item by passing everything to the update function
            self.update_transcription_log(unique_id, **attribute)

            # finally open or focus the transcription log window
            self.toolkit_UI_obj.open_transcription_log_window()

            return True

        else:
            logger.warning('Missing unique id when trying to add item to transcription log.')
            return False

    def update_transcription_log(self, unique_id=None, **attributes):
        '''
        Updates items in the transcription log (or adds them if necessary)
        The items are identified by unique_id and only the passed attributes will be updated
        :param unique_id:
        :param options:
        :return:
        '''
        if unique_id:

            # add the item to the transcription log if it's not already in there
            if unique_id not in self.transcription_log:
                self.transcription_log[unique_id] = {}

        # the transcription log items will contain things like
        # name, status, audio_file_path etc.
        # these attributes are set using the self.transcription_item_attr variable

        # use the passed attribute to populate the transcription log entry
        if attributes:
            for attribute in attributes:
                # but only use said option if it was mentioned in the transcription_item_attr
                if attribute in self.transcription_item_attr:
                    # populate the transcription log
                    self.transcription_log[unique_id][attribute] = attributes[attribute]

        # whenever the transcription log is update, make sure you update the window too
        self.toolkit_UI_obj.update_transcription_log_window()

    def add_to_transcription_queue(self, toolkit_UI_obj=None, task=None, audio_file_path=None,
                                   name=None, language=None, model=None, device=None,
                                   unique_id=None, initial_prompt=None):
        '''
        Adds files to the transcription queue and then pings the queue in case it's sleeping.
        It also adds the files to the transcription log
        :param toolkit_UI_obj:
        :param translate:
        :param audio_file_path:
        :param name:
        :return:
        '''

        # check if there's a UI object available
        if not self.is_UI_obj_available(toolkit_UI_obj):
            return False

        # select the transcribe task automatically if neither transcribe or translate was passed
        if task is None or task not in ['transcribe', 'translate', 'transcribe+translate']:
            task = 'transcribe'

        # if it's a regular transcribe or translate task
        if task in ['transcribe', 'translate']:

            # just do that task
            tasks = [task]

        # if the user is asking for a transcribe+translate
        elif task == 'transcribe+translate':
            # add both tasks
            tasks = ['transcribe', 'translate']

        # we will never get to this, but let's have it
        else:
            return False

        # to count tasks we need an int
        task_num = 0

        # add all the above tasks to the queue
        for c_task in tasks:

            task_num = task_num+1

            # generate a unique id if one hasn't been passed
            if unique_id is None:
                next_queue_id = self._generate_transcription_unique_id(name=name)
            else:

                # if a unique id was passed, only use it for the first task
                next_queue_id = unique_id

                # then reset it
                unique_id = None

            # add numbering to names, but starting with the second task
            if task_num > 1:
                c_name = name + ' ' + str(task_num)
            else:
                c_name = name

            # add to transcription queue if we at least know the path and the name of the timeline/file
            if next_queue_id and audio_file_path and os.path.exists(audio_file_path) and name:

                file_dict = {'name': c_name, 'audio_file_path': audio_file_path, 'task': c_task,
                             'language': language, 'model': model, 'device': device,
                             'initial_prompt': initial_prompt,
                             'status': 'waiting', 'info': None}

                # add to transcription queue
                self.transcription_queue[next_queue_id] = file_dict

                # add the file to the transcription log too (the add function will check if it's already there)
                self.add_to_transcription_log(unique_id=next_queue_id, **file_dict)

                # now ping the transcription queue in case it's sleeping
                self.ping_transcription_queue()

            else:
                logger.error('Missing parameters to add file to transcription queue')
                return False

            # throttle for a bit to avoid unique id unique id collisions
            time.sleep(0.01)

        return True


    def _generate_transcription_unique_id(self, name=None):
        if name:
            return name + '-' + str(int(time.time()))
        else:
            return str(int(time.time()))

    def ping_transcription_queue(self):
        '''
        Checks if there are files waiting in the transcription queue and starts the transcription queue thread,
        if there isn't a thread already running
        :return:
        '''

        # if there are files in the queue
        if self.transcription_queue:
            # logger.info('Files waiting in queue for transcription:\n {} \n'.format(self.transcription_queue))

            # check if there's an active transcription thread
            if self.transcription_queue_thread is not None:
                logger.info('Currently transcribing: {}'.format(self.transcription_queue_current_name))

            # if there's no active transcription thread, start it
            else:
                # take the first file in the queue:
                next_queue_id = list(self.transcription_queue.keys())[0]

                # update the status of the item in the transcription log
                self.update_transcription_log(unique_id=next_queue_id, **{'status': 'preparing'})

                # and now start the transcription thread with it
                self.transcription_queue_thread = Thread(target=self.transcribe_from_queue,
                                                         args=(next_queue_id,)
                                                         )
                self.transcription_queue_thread.start()

                # delete this file from the queue
                del self.transcription_queue[next_queue_id]

            return True

        # if there are no more files left in the queue, stop until something pings it again
        else:
            logger.info('Transcription queue empty. Going to sleep.')
            return False

    def transcribe_from_queue(self, queue_id):

        # check if there's a UI object available
        if not self.is_UI_obj_available():
            return False

        # get file info from queue
        name, audio_file_path, task, language, model, device, initial_prompt, info \
            = self.get_queue_file_info(queue_id)

        logger.info("Starting to transcribe {}".format(name))

        # make the name of the file that is currently being processed public
        self.transcription_queue_current_name = name

        import traceback

        # try the transcription
        try:
            self.whisper_transcribe(audio_file_path=audio_file_path, task=task, name=name,
                                    queue_id=queue_id, language=language, model=model, initial_prompt=initial_prompt,
                                    device=device)

        # in case the transcription process crashes
        except Exception:
            # show error
            logger.error(traceback.format_exc())
            # update the status of the item in the transcription log
            self.update_transcription_log(unique_id=queue_id, **{'status': 'failed'})

        # reset the transcription thread and name:
        self.transcription_queue_current_name = None
        self.transcription_queue_thread = None

        # then ping the queue again
        self.ping_transcription_queue()

        return False

    def get_queue_file_info(self, queue_id):
        '''
        Returns the file info stored in a queue given the correct queue_id
        :param queue_id:
        :return: list or False
        '''
        if self.transcription_queue and queue_id in self.transcription_queue:
            queue_file = self.transcription_queue[queue_id]
            return [queue_file['name'], queue_file['audio_file_path'], queue_file['task'],
                    queue_file['language'], queue_file['model'], queue_file['device'],
                    queue_file['initial_prompt'],
                    queue_file['info']]

        return False

    def whisper_transcribe(self, name=None, audio_file_path=None, task=None,
                           target_dir=None, queue_id=None, **other_whisper_options):

        # check if there's a UI object available
        if not self.is_UI_obj_available():
            return False

        # don't continue unless we have a queue_id
        if audio_file_path is None or not audio_file_path:
            return False

        # use the name of the file in case the name wasn't passed
        if name is None:
            name = os.path.basename(audio_file_path)

        # save the directory where the file is stored if it wasn't passed
        if target_dir is None:
            target_dir = os.path.dirname(audio_file_path)

        audio_file_name = os.path.basename(audio_file_path)

        # select the device that was passed (if any)
        if 'device' in other_whisper_options:
            # select the new whisper device
            self.whisper_device = self.whisper_device_select(other_whisper_options['device'])
            del other_whisper_options['device']

        # load OpenAI Whisper
        # and hold on to it for future use (unless another model was passed via other_whisper_options)
        if self.whisper_model is None \
                or ('model' in other_whisper_options and self.whisper_model_name != other_whisper_options['model']):

            # update the status of the item in the transcription log
            self.update_transcription_log(unique_id=queue_id, **{'status': 'loading model'})

            # use the model that was passed in the call (if any)
            if 'model' in other_whisper_options and other_whisper_options['model']:
                self.whisper_model_name = other_whisper_options['model']

            logger.info('Loading Whisper {} model.'.format(self.whisper_model_name))
            self.whisper_model = whisper.load_model(self.whisper_model_name)

            # let the user know if the whisper model is multilingual or english-only
            logger.info('Selected Whisper model is {}.'.format(
                'multilingual' if self.whisper_model.is_multilingual else 'English-only'
            ))

        # delete the model reference so we don't pass it again in the transcribe function below
        if 'model' in other_whisper_options:
            del other_whisper_options['model']

        # update the status of the item in the transcription log
        self.update_transcription_log(unique_id=queue_id, **{'status': 'transcribing'})

        notification_msg = "Transcribing {}.\nThis may take a while.".format(name)
        self.toolkit_UI_obj.notify_via_os("Starting Transcription", notification_msg, notification_msg)

        start_time = time.time()

        # remove empty language
        if 'language' in other_whisper_options and other_whisper_options['language'] == '':
            del other_whisper_options['language']

        # remove empty initial prompt
        if 'initial_prompt' in other_whisper_options and other_whisper_options['initial_prompt'] == '':
            del other_whisper_options['initial_prompt']

        result = self.whisper_model.transcribe(audio_file_path,
                                               task=task, verbose=True, **other_whisper_options)

        # self.speaker_diarization(audio_file_path)


        # let the user know that the speech was processed
        notification_msg = "Finished transcription for {} in {} seconds".format(name,
                                                                                round(time.time() - start_time))
        self.toolkit_UI_obj.notify_via_os("Finished Transcription", notification_msg, notification_msg)

        # update the status of the item in the transcription log
        self.update_transcription_log(unique_id=queue_id, **{'status': 'saving files'})

        # WHAT HAPPENS FROM HERE

        # Once a transcription is completed, you should see 4 or 5 files:
        # - the original audio file used for transcription (usually WAV)
        # - if the file was rendered from resolve, a json file - which is kind of like a report card for what was
        #   rendered from where (see mots_resolve.py render())
        # - the resulting transcription.json file with the actual transcription
        # - the plain text transcript in TXT format - transcript.txt
        # - the transcript in SRT format, ready to be imported in Resolve (or other apps)
        #
        # Once these are written, the transcription.json file should be used to gather any further information saved
        # within the tool, therefore it's important to also mention the 3 other files within it (txt, srt, wav). But,
        # with this approach we need to keep in mind to always keep the other 3 files next to the transcription.json
        # to ensure that the files can migrate between different machines and the links won't break.
        #
        # Furthermore, the same file will be used to save any other information related to the transcription.)

        # first determine if there's another transcription.json file with the same name
        # and keep adding numbers to it until the name is free
        file_name = audio_file_name
        file_num = 2
        while os.path.exists(os.path.join(target_dir, file_name + '.transcription.json')):
            file_name = audio_file_name + "_{}".format(file_num)
            file_num = file_num+1

        txt_file_path = self.save_txt_from_transcription(file_name=file_name, target_dir=target_dir,
                                                         transcription_data=result)

        # only save the filename without the absolute path to the transcript json
        result['txt_file_path'] = os.path.basename(txt_file_path)

        # save the SRT file next to the transcription file
        srt_file_path = self.save_srt_from_transcription(file_name=file_name, target_dir=target_dir,
                                                         transcription_data=result)

        # only the basename is needed here too
        result['srt_file_path'] = os.path.basename(srt_file_path)

        # remember the audio_file_path this transcription is based on too
        result['audio_file_path'] = os.path.basename(audio_file_path)

        # don't forget to add the name of the transcription
        result['name'] = name

        # and some more info about the transription
        result['task'] = task
        result['model'] = self.whisper_model_name

        # save the transcription file with all the added file paths
        transcription_json_file_path = self.save_transcription_file(file_name=file_name, target_dir=target_dir,
                                                                    transcription_data=result)

        # when done, change the status in the transcription log
        # and also add the file paths to the transcription log
        self.update_transcription_log(unique_id=queue_id, status='done',
                                      srt_file_path=result['srt_file_path'], txt_file_path=result['txt_file_path'],
                                      json_file_path=transcription_json_file_path)

        # why not open the transcription in a transcription window?
        self.toolkit_UI_obj.open_transcription_window(title=name,
                                                      transcription_file_path=transcription_json_file_path,
                                                      srt_file_path=srt_file_path)

        return True

    def save_transcription_file(self, transcription_file_path=None, transcription_data=None,
                                file_name=None, target_dir=None, backup=None):
        '''
        Saves the transcription file either to the transcription_file_path
        or to the "target_dir/name.transcription.json" path

        :param transcription_file_path:
        :param transcription_data:
        :param name:
        :param target_dir:
        :return: False or transcription_file_path
        '''

        # if no full path was passed
        if transcription_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                transcription_file_path = os.path.join(target_dir, file_name + '.transcription.json')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if transcription_file_path:

            # if backup_original is enabled, it will save a copy of the transcription file to
            # originals/[filename].backup.json (if one doesn't exist already)
            if backup and os.path.exists(transcription_file_path):

                import shutil

                # format the name of the backup file
                backup_transcription_file_path = \
                    os.path.splitext(os.path.basename(transcription_file_path))[0]+'.'+str(backup)+'.json'

                backups_folder = os.path.join(os.path.dirname(transcription_file_path), '.backups')

                # if the backups folder doesn't exist, create it
                if not os.path.exists(backups_folder):
                    os.mkdir(backups_folder)

                # copy the existing file to the backups folder
                # if it doesn't already exist
                if not os.path.exists(os.path.join(backups_folder, backup_transcription_file_path)):
                    shutil.copyfile(transcription_file_path,
                                    os.path.join(backups_folder, backup_transcription_file_path))

            # Finally,
            # save the whole whisper result in the transcription json file
            # don't question what is being passed, simply save everything
            with open(transcription_file_path, 'w', encoding='utf-8') as outfile:
                json.dump(transcription_data, outfile)

            return transcription_file_path


        return False

    def get_transcription_file_data(self, transcription_file_path):

        # make sure the transcription exists
        if not os.path.exists(transcription_file_path):
            logger.warning('Transcription file {} doesn\'t exist.'.format(transcription_file_path))
            return False

        # get the contents of the transcription file
        with codecs.open(transcription_file_path, 'r', 'utf-8-sig') as json_file:
            transcription_json = json.load(json_file)

        return transcription_json

    def process_transcription_data(self, transcription_segments=None, transcription_data=None):
        '''
        This takes the passed segments and puts them into a dict ready to be passed to a transcription file.

        It's important that if the contents of any transcription segment was edited, to see that reflected in
        other variables as well. It also adds the key 'modified' so we later know that the tokens might not
        correspond to the segment contents anymore.

        :param transcription_segments:
        :return:
        '''

        # take each transcription segment
        if transcription_segments is not None and transcription_segments and transcription_data is not None and 'segments' in transcription_data:

            # first empty the text variable
            transcription_data['text'] = ''

            for segment in transcription_segments:
                print(segment)

                # take each segment and insert it into the text variable
                transcription_data['text'] = segment + ' '

            # make it known that this transcription was modified
            transcription_data['modified'] = time.time()

            return transcription_data

    def save_srt_from_transcription(self, srt_file_path=None, transcription_segments=None,
                                    file_name=None, target_dir=None, transcription_data=None):
        '''
        Saves an SRT file next to the transcription file.

        You can either pass the transcription segments or the full transcription data. When both are passed,
        the transcription_segments will be used.

        :param srt_file_path:
        :param transcription_segments:
        :param name:
        :param target_dir:
        :param transcription_data:
        :return: False or srt_file_path
        '''

        # if no full path was passed
        if srt_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                srt_file_path = os.path.join(target_dir, file_name + '.srt')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if srt_file_path:

            # if the transcription segments were not passed
            # try to find them in transcription_data (if that was passed too)
            if transcription_segments is None and transcription_data and 'segments' in transcription_data:
                transcription_segments = transcription_data['segments']

            # otherwise, stop the process
            else:
                return False

            if transcription_segments:
                with open(srt_file_path, "w", encoding="utf-8") as srt:
                    whisper.utils.write_srt(transcription_segments, file=srt)

                return srt_file_path

        return False

    def save_txt_from_transcription(self, txt_file_path=None, transcription_text=None,
                                    file_name=None, target_dir=None, transcription_data=None):
        '''
        Saves an txt file next to the transcription file.

        You can either pass the transcription text or the full transcription data. When both are passed,
        the transcription_text will be used.

        :param txt_file_path:
        :param transcription_text:
        :param file_name:
        :param target_dir:
        :param transcription_data:
        :return: False or txt_file_path
        '''

        # if no full path was passed
        if txt_file_path is None:

            # try to use the name and target dir attributes
            if file_name is not None and target_dir is not None:
                # the path should contain the name and the target dir, but end with transcription.json
                txt_file_path = os.path.join(target_dir, file_name + '.txt')

            # if the name and target_dir were not passed, throw an error
            else:
                logger.error('No transcription file path, name or target dir were passed.')
                return False

        if txt_file_path:

            # if the transcription segments were not passed
            # try to find them in transcription_data (if that was passed too)
            if transcription_text is None and transcription_data and 'text' in transcription_data:
                transcription_text = transcription_data['text']

            # otherwise, stop the process
            else:
                return False

            # save the text in the txt file
            if transcription_text:
                with open(txt_file_path, 'w', encoding="utf-8") as txt_outfile:
                    txt_outfile.write(transcription_text)

                return txt_file_path

        return False

    def get_timeline_transcriptions(self, timeline_name=None, project_name=None):
        '''
        Gets a list of all the transcriptions associated with a timeline
        :param timeline_name:
        :param project_name:
        :return:
        '''
        if timeline_name is None:
            return None

        # get all the transcription files associated with the timeline
        # by requesting the timeline setting named 'transcription_files'
        timeline_transcription_files = self.stAI.get_timeline_setting(project_name=project_name,
                                                                      timeline_name=timeline_name,
                                                                      setting_key='transcription_files')

        return timeline_transcription_files

    def get_transcription_to_timeline_link(self, transcription_file_path=None, timeline_name=None, project_name=None):
        '''
        Checks if a transcription linked with a timeline but also returns all the transcription files
        associated with that timeline

        :param transcription_file_path:
        :param timeline_name:
        :param project_name:
        :return: bool, timeline_transcription_files
        '''
        if transcription_file_path is None or timeline_name is None:
            return None

        # get all the transcription files associated with the timeline
        timeline_transcription_files = self.get_timeline_transcriptions(timeline_name=timeline_name,
                                                                        project_name=project_name)

        # if the settings of our timeline were found
        if timeline_transcription_files and timeline_transcription_files is not None:

            # check if the transcription is linked to the timeline
            if transcription_file_path in timeline_transcription_files:
                return True, timeline_transcription_files
            # if it's not just say so
            else:
                return False, timeline_transcription_files

        # give None and an empty transcription list
        return None, []

    def link_transcription_to_timeline(self, transcription_file_path=None, timeline_name=None, link=None,
                                       project_name=None):
        '''
        Links transcription files to timelines.
        If the link parameter isn't passed, it first checks if the transcription is linked and then toggles the link
        If no timeline_name is passed, it tries to use the timeline of the currently opened timeline in Resolve

        :param transcription_file_path:
        :param timeline_name:
        :param link:
        :return:
        '''

        # abort if no transcript file was passed
        if transcription_file_path is None:
            logger.error('No transcript path was passed. Unable to link transcript to timeline.')
            return None

        # if no timeline name was passed
        if timeline_name is None:

            # try to get the timeline currently opened in Resolve
            global current_timeline
            if current_timeline and current_timeline is not None and 'name' in current_timeline:

                # and use it as timeline name
                timeline_name = current_timeline['name']


            else:
                logger.error('No timeline was passed. Unable to link transcript to timeline.')
                return None

        # if no project was passed
        if project_name is None:

            # try to get the project opened in Resolve
            global current_project
            if current_project and current_project is not None:

                # use that as a project name
                project_name = current_project

            else:
                logger.error('No project name was passed. Unable to link transcript to timeline.')

        # check the if the transcript is currently linked with the transcription
        current_link, timeline_transcriptions = self.get_transcription_to_timeline_link(
            transcription_file_path=transcription_file_path,
            timeline_name=timeline_name, project_name=project_name)

        # if the link action wasn't passed, decide here whether to link or unlink
        # basically toggle between true or false by choosing the opposite of whether the current_link is true or false
        if link is None and current_link is True:
            link = False
        elif link is None and current_link is not None and current_link is False:
            link = True
        else:
            link = True

        # now create the link if we should
        if link:

            logger.info('Linking to current timeline: {}'.format(timeline_name))

            # but only create it if it isn't in there yet
            if transcription_file_path not in timeline_transcriptions:
                timeline_transcriptions.append(transcription_file_path)

        # or remove the link if we shouldn't
        else:
            logger.info('Unlinking from current timeline: {}'.format(timeline_name))

            # but only remove it if it is in there currently
            if transcription_file_path in timeline_transcriptions:
                timeline_transcriptions.remove(transcription_file_path)

        # if we made it so far, get all the project settings
        self.stAI.project_settings = self.stAI.get_project_settings(project_name=project_name)

        # if there isn't a timeline dict in the project settings, create one
        if 'timelines' not in self.stAI.project_settings:
            self.stAI.project_settings['timelines'] = {}

        # if there isn't a reference to this timeline in the timelines dict
        # add one, including the transcription files list
        if timeline_name not in self.stAI.project_settings['timelines']:
            self.stAI.project_settings['timelines'][timeline_name] = {'transcription_files': []}

        # overwrite the transcription file settings of the timeline
        # within the timelines project settings of this project
        self.stAI.project_settings['timelines'][timeline_name]['transcription_files'] \
            = timeline_transcriptions

        # print(json.dumps(self.stAI.project_settings, indent=4))

        self.stAI.save_project_settings(project_name=project_name,
                                        project_settings=self.stAI.project_settings)

        return link

    def is_UI_obj_available(self, toolkit_UI_obj=None):

        # if there's no toolkit_UI_obj in the object or one hasn't been passed, abort
        if toolkit_UI_obj is None and self.toolkit_UI_obj is None:
            logger.error('No GUI available. Aborting.')
            return False
        # if there was a toolkit_UI_obj passed, update the one in the object
        elif toolkit_UI_obj is not None:
            self.toolkit_UI_obj = toolkit_UI_obj
            return True
        # if there simply is a self.toolkit_UI_obj just return True
        else:
            return True

    def calculate_sec_to_resolve_timecode(self, seconds=0):
        global resolve
        if resolve:

            # poll resolve for some info
            resolve_data = mots_resolve.get_resolve_data()

            # get the framerate of the current timeline
            timeline_fps = resolve_data['currentTimelineFPS']

            # get the start timecode of the current timeline
            timeline_start_tc = resolve_data['currentTimeline']['startTC']

            # initialize the timecode object for the start tc
            timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)

            # only do timecode math if seconds > 0
            if seconds > 0:

                # init the timecode object based on the passed seconds
                tc_from_seconds = Timecode(timeline_fps, start_seconds=float(seconds))

                # calculate the new timecode
                new_timeline_tc = timeline_start_tc + tc_from_seconds

            # otherwise use the timeline start tc
            else:
                new_timeline_tc = timeline_start_tc

            return new_timeline_tc

        else:
            return False

    def go_to_time(self, seconds=0):

        if resolve:

            new_timeline_tc = self.calculate_sec_to_resolve_timecode(seconds)

            # move playhead in resolve
            mots_resolve.set_resolve_tc(str(new_timeline_tc))

    def on_resolve(self, event_name):
        '''
        Process resolve events
        :param event_name:
        :return:
        '''

        # FOR NOW WE WILL KEEP THE UI UPDATES HERE AS WELL

        # print(event_name)

        # when resolve connects / re-connects
        if event_name == 'resolve_changed':

            # update the main window
            if self.is_UI_obj_available():
                self.toolkit_UI_obj.update_main_window()

        # when the timeline has changed
        elif event_name == 'timeline_changed':

            global current_timeline

            if current_timeline is not None:
                # get the transcription_paths linked with this timeline
                timeline_transcription_file_paths = self.get_timeline_transcriptions(
                    timeline_name=current_timeline['name'],
                    project_name=current_project
                )

                # and open a transcript window for each of them
                if timeline_transcription_file_paths:
                    for transcription_file_path in timeline_transcription_file_paths:
                        self.toolkit_UI_obj.open_transcription_window(transcription_file_path=transcription_file_path)


    def poll_resolve_thread(self):
        '''
        This keeps resolve polling in a separate thread
        '''

        # wrap poll_resolve_data into a thread
        poll_resolve_thread = Thread(target=self.poll_resolve_data)

        # stop the thread when the main thread stops
        poll_resolve_thread.daemon = True

        # start the thread
        poll_resolve_thread.start()

    def poll_resolve_data(self):
        '''
        Polls resolve and returns either the data passed from resolve, or False if any exceptions occurred
        :return:
        '''

        global current_project
        global current_timeline
        global current_tc
        global current_bin
        global current_timeline_fps
        global resolve

        global resolve_error

        # do this continuously
        while True:

            # try to poll resolve
            try:
                resolve_data = mots_resolve.get_resolve_data(silent=True)

                #print(resolve)
                #print(resolve_data['resolve'])

                if type(resolve) != type(resolve_data['resolve']):
                    # update the global resolve variable with the resolve object
                    resolve = resolve_data['resolve']
                    self.on_resolve('resolve_changed')

                if current_project != resolve_data['currentProject']:
                    current_project = resolve_data['currentProject']
                    self.on_resolve('project_changed')
                    # logger.info('Current Project: {}'.format(current_project))

                if current_timeline != resolve_data['currentTimeline']:
                    current_timeline = resolve_data['currentTimeline']
                    self.on_resolve('timeline_changed')
                    # self.on_resolve_timeline_changed()
                    # logger.info("Current Timeline: {}".format(current_timeline))

                #  updates the currentBin
                if current_bin != resolve_data['currentBin']:
                    current_bin = resolve_data['currentBin']
                    self.on_resolve('bin_changed')
                    # logger.info("Current Bin: {}".format(current_bin))

                # update current playhead timecode
                if current_tc != resolve_data['currentTC']:
                    current_tc = resolve_data['currentTC']
                    self.on_resolve('tc_changed')

                # update current playhead timecode
                if current_timeline_fps != resolve_data['currentTimelineFPS']:
                    current_timeline_fps = resolve_data['currentTimelineFPS']
                    self.on_resolve('fps_changed')

                # was there a previous error?
                if resolve is not None and resolve_error > 0:
                    # first let the user know that the connection is back on
                    logger.warning("Resolve connection re-established.")

                    # reset the error counter since the Resolve API worked fine
                    resolve_error = 0

                elif resolve is None:
                    resolve_error += 1

                #return resolve_data

            # if an exception is thrown while trying to work with Resolve, don't crash, but continue to try to poll
            except:

                import traceback
                print(traceback.format_exc())

                # count the number of errors
                resolve_error += 1

                # resolve is now None in the global variable
                # resolve = None

                #return False

            # how often do we poll resolve?
            polling_interval = 500

            # if any errors occurred
            if resolve_error:

                # let the user know that there's an error, and throttle the polling_interval

                # after 20+ tries, assume the user is no longer paying attention and reduce the frequency of tries
                if resolve_error > 20:

                    # only show this error one more time
                    if resolve_error == 21:
                        logger.error('Resolve is still not reachable. '
                                            'Muting errors. Now retrying every 30 seconds. ')

                    # and increase the polling interval to 30 seconds
                    polling_interval = 30000

                # if the error has been triggered more than 10 times, say this
                elif resolve_error > 10:

                    if resolve_error == 11:
                        logger.warning('Resolve is still not reachable. Now retrying every 5 seconds.')

                    # increase the polling interval to 5 seconds
                    polling_interval = 5000

                else:
                    if resolve_error == 1:
                        logger.warning('Resolve is not reachable.')

                    # increase the polling interval to 1 second
                    polling_interval = 1000

            # take a short break before continuing the loop
            time.sleep(polling_interval/1000)

    def speaker_diarization(audio_path):
        # work in progress, but whisper vs. pyannote dependencies collide (huggingface-hub)
        # print("Detecting speakers.")

        # from pyannote.audio import Pipeline
        # pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

        # apply pretrained pipeline
        # diarization = pipeline(audio_path)

        # print the result
        # for turn, _, speaker in diarization.itertracks(yield_label=True):
        #    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
        return False


def resolve_check_timeline(resolve_data, toolkit_UI_obj):
    '''
    This checks if a timeline is available and returns bool
    :param resolve:
    :return:
    '''

    # trigger warning if there is no current timeline
    if resolve_data['currentTimeline'] is None:
        toolkit_UI_obj.notify_via_messagebox(
            message='Timeline not available. Make sure that you\'ve opened a Timeline in Resolve.',
            type='warning')
        return False

    else:
        return True


def execute_operation(operation, toolkit_UI_obj):
    if not operation or operation == '':
        return False

    global stAI

    # get info from resolve for later
    resolve_data = mots_resolve.get_resolve_data()

    # copy markers operation
    if operation == 'copy_markers_timeline_to_clip' or operation == 'copy_markers_clip_to_timeline':

        # set source and destination depending on the operation
        if operation == 'copy_markers_timeline_to_clip':
            source = 'timeline'
            destination = 'clip'

        elif operation == 'copy_markers_clip_to_timeline':
            source = 'clip'
            destination = 'timeline'

        # this else will never be triggered but let's leave it here for safety for now
        else:
            return False

        # trigger warning and stop if there is no current timeline
        if not resolve_check_timeline(resolve_data, toolkit_UI_obj):
            return False

        # trigger warning and stop if there are no bin clips
        if resolve_data['binClips'] is None:
            toolkit_UI_obj.notify_via_messagebox(
                message='Bin clips not available. Make sure that a bin is opened in Resolve.\n\n'
                        'This doesn\'t work if multiple bins or smart bins are selected due to API.',
                type='warning')
            return False

        # execute operation without asking for any prompts
        # this will delete the existing clip/timeline destination markers,
        # but the user can undo the operation from Resolve
        return mots_resolve.copy_markers(source, destination,
                                         resolve_data['currentTimeline']['name'],
                                         resolve_data['currentTimeline']['name'],
                                         True)

    # render marker operation
    elif operation == 'render_markers_to_stills' or operation == 'render_markers_to_clips':

        # ask user for marker color

        # but first make a list of all the available marker colors based on the timeline markers
        current_timeline_marker_colors = []
        if resolve_check_timeline(resolve_data, toolkit_UI_obj) and \
                current_timeline and 'markers' in current_timeline:

            # take each marker from timeline and get its color
            for marker in current_timeline['markers']:

                # only append the marker to the list if it wasn't added already
                if current_timeline['markers'][marker]['color'] not in current_timeline_marker_colors:
                    current_timeline_marker_colors.append(current_timeline['markers'][marker]['color'])

        # if no markers exist, cancel operation and let the user know that there are no markers to render
        if current_timeline_marker_colors:
            marker_color = simpledialog.askstring(title="Markers Color",
                                                  prompt="What color markers should we render?\n\n"
                                                         "These are the marker colors on the current timeline:\n"
                                                         + ", ".join(current_timeline_marker_colors))
        else:
            no_markers_alert = 'The timeline doesn\'t contain any markers'
            logger.warning(no_markers_alert)
            return False

        if not marker_color:
            #print("User canceled render operation.")
            return False

        if marker_color not in current_timeline_marker_colors:
            toolkit_UI_obj.notify_via_messagebox(title='Unavailable marker color',
                                                 message='The marker color you\'ve entered doesn\'t exist on the timeline.',
                                                 message_log="Aborting. User entered a marker color that doesn't exist on the timeline.",
                                                 type='error'
                                                 )

            return False

        render_target_dir = toolkit_UI_obj.ask_for_target_dir()

        if not render_target_dir or render_target_dir == '':
            #print("User canceled render operation.")
            return False

        if operation == 'render_markers_to_stills':
            stills = True
            render = True
            render_preset = "Still_TIFF"
        else:
            stills = False
            render = False

            # @todo ask user for render preset or assign one
            render_preset = False

        mots_resolve.render_markers(marker_color, render_target_dir, False,
                                    stills, render, render_preset)

    return False


current_project = ''
current_timeline = ''
current_tc = '00:00:00:00'
current_timeline_fps = ''
current_bin = ''
resolve_error = 0
resolve = None


class StoryToolkitAI:
    def __init__(self):
        # import version.py - this holds the version stored locally
        import version

        # keep the version in memory
        self.__version__ = version.__version__

        # this is where all the user files should be stored
        # if it's not absolute, make sure it's relative to the app.py script location
        # to make it easier for the users to find it
        # (and to prevent paths relative to possible virtual environment paths)
        if not os.path.isabs(USER_DATA_PATH):
            self.user_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), USER_DATA_PATH)
        else:
            self.user_data_path = USER_DATA_PATH

        # the config file should be in the user data folder
        self.config_file_path = os.path.join(self.user_data_path, APP_CONFIG_FILE_NAME)

        # create a config variable
        self.config = {}

        # the projects directory is always inside the user_data_path
        # this is where we will store all the stuff related to specific projects
        self.projects_dir_path = os.path.join(self.user_data_path, 'projects')

        # create a project settings variable
        self.project_settings = {}

        logger.info(Style.BOLD+Style.UNDERLINE+"Running StoryToolkitAI version {}".format(self.__version__))

    def user_data_dir_exists(self, create_if_not=True):
        '''
        Checks if the user data dir exists and creates one if asked to
        :param create_if_not:
        :return:
        '''

        # if the directory doesn't exist
        if not os.path.exists(self.user_data_path):
            logger.warning('User data directory {} doesn\'t exist.'
                           .format(os.path.abspath(self.user_data_path)))

            if create_if_not:
                logger.warning('Creating user data directory.')

                # and create the whole path to it if it doesn't
                os.makedirs(self.user_data_path)

                # for users of versions prior to 0.16.14, the user data folder was at OLD_USER_DATA_PATH
                # so make sure we copy everything from the old path to the new folder
                old_user_data_path_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), OLD_USER_DATA_PATH)

                # we first check if the old_user_data_path_abs exists
                if os.path.exists(old_user_data_path_abs):
                    import shutil
                    from datetime import date
                    import platform

                    logger.warning('Old user data directory found.\n\n')

                    # let the user know that we are moving the files
                    move_user_data_path_msg = \
                                    'Starting with version 0.16.14, '\
                                    'the user data directory on {} has moved to {}.\n'\
                                    'This means that any existing configuration and project ' \
                                    'settings files will be copied there.\n'\
                                    'If the files are at the new location, feel free to delete {}\n' \
                                    .format(platform.node(),
                                            self.user_data_path, old_user_data_path_abs, old_user_data_path_abs)

                    logger.warning(move_user_data_path_msg)

                    logger.warning('Copying user data files to new location.')

                    # copy all the contents of the OLD_USER_DATA_PATH to the new path
                    for item in os.listdir(old_user_data_path_abs):
                        s = os.path.join(old_user_data_path_abs, item)
                        d = os.path.join(self.user_data_path, item)

                        logger.warning((' - {}'.format(item)))

                        if os.path.isdir(s):
                            shutil.copytree(s, d, False, None)
                        else:
                            shutil.copy2(s, d)

                    logger.warning('Finished copying user data files to {}'.format(self.user_data_path))

                    # reload the config file
                    self.config = self.get_config()

                    # leave a readme file in the OLD_USER_DATA_PATH so that the user knows that stuff was moved
                    with open(os.path.join(old_user_data_path_abs, 'README.txt'), 'a') as f:
                        f.write('\n'+str(date.today())+'\n')
                        f.write(move_user_data_path_msg)


            else:
                return False

        return True

    def project_dir_exists(self, project_settings_path=None, create_if_not=True):

        if project_settings_path is None:
            return False

        # if the directory doesn't exist
        if not os.path.exists(os.path.dirname(project_settings_path)):
            logger.warning('Project settings directory {} doesn\'t exist.'
                           .format(os.path.abspath(os.path.dirname(project_settings_path))))

            if create_if_not:
                logger.warning('Creating project settings directory.')

                # and create the whole path to it if it doesn't
                os.makedirs(os.path.dirname(project_settings_path))

            else:
                return False

        return True

    def get_app_setting(self, setting_name=None, default_if_none=None):
        '''
        Returns a specific app setting or None if it doesn't exist
        If default if none is passed, the app will also save the setting to the config for future use
        :param setting_name:
        :param default_if_none:
        :return:
        '''

        if setting_name is None or not setting_name or setting_name == '':
            logger.error('No setting was passed.')
            return False

        # get the app config
        self.config = self.get_config()

        # look for the requested setting
        if setting_name in self.config:

            # and return it
            return self.config[setting_name]

        # if the requested setting doesn't exist in the config
        # but a default was passed
        elif default_if_none is not None and default_if_none != '':

            logger.info('Config setting {} saved as {} '.format(setting_name, default_if_none))

            # save the default to the config
            self.save_config(setting_name=setting_name, setting_value=default_if_none)

            # and then return the default
            return default_if_none

        # otherwise simple return none
        else:
            return None

    def save_config(self, setting_name=None, setting_value=None):
        '''
        Saves a setting to the app configuration file
        :param config_key:
        :param config_value:
        :return:
        '''

        if setting_name is None or not setting_name or setting_name == '' or setting_value is None:
            logger.error('No setting that we could save to the config file was passed.')
            return False

        # get existing configuration
        self.config = self.get_config()

        # save or overwrite the passed setting the config json
        self.config[setting_name] = setting_value

        # before writing the configuration to the config file
        # check if the user data folder exists (and create it if not)
        self.user_data_dir_exists(create_if_not=True)

        # then write the config to the config json
        with open(self.config_file_path, 'w') as outfile:
            json.dump(self.config, outfile, indent=3)

        logger.info('Updated config file {} with {} data.'
                       .format(os.path.abspath(self.config_file_path), setting_name))

        # and return the config back to the user
        return self.config

    def get_config(self):
        '''
        Gets the app configuration from the config file (if one exists)
        :return:
        '''

        # read the config file if it exists
        if os.path.exists(self.config_file_path):

            # read the app config
            with open(self.config_file_path, 'r') as json_file:
                self.config = json.load(json_file)

            # and return the config
            return self.config

        # if the config file doesn't exist, return an empty dict
        else:
            return {}

    def _project_settings_path(self, project_name=None):

        # the full path to the project settings file
        if project_name is not None and project_name != '':
            return os.path.join(self.projects_dir_path, project_name, 'project.json')

    def get_project_settings(self, project_name=None):
        '''
        Gets the settings of a specific project
        :return:
        '''

        if project_name is None:
            logger.error('Unable to get project settings if no project name was passed.')

        # the full path to the project settings file
        project_settings_path = self._project_settings_path(project_name=project_name)

        # read the project settings file if it exists
        if os.path.exists(project_settings_path):

            # read the project settings from the project.json
            with open(project_settings_path, 'r') as json_file:
                self.project_settings = json.load(json_file)

            # and return the project settings
            return self.project_settings

        # if the project settings file doesn't exist, return an empty dict
        else:
            return {}

    def save_project_settings(self, project_name=None, project_settings=None):
        '''
        Saves the settings of a specific project.
        This will OVERWRITE any existing project settings so make sure you include the whole project settings dictionary
        in the call!
        :param project_name:
        :return:
        '''

        if project_name is None or project_name == '' or project_settings is None:
            logger.error('Insufficient data. Unable to save project settings.')
            return False

        # the full path to the project settings file
        project_settings_path = self._project_settings_path(project_name=project_name)

        # before writing the project settings
        # check if the project directory exists (and create it if not)
        if (self.project_dir_exists(project_settings_path=project_settings_path, create_if_not=True)):
            # but make sure it also contains the correct project name
            project_settings['name'] = project_name

            # then overwrite the settings to the project settings json
            with open(project_settings_path, 'w') as outfile:
                json.dump(project_settings, outfile, indent=3)

            logger.info('Updated project settings file {}.'
                           .format(os.path.abspath(project_settings_path)))

            # and return the config back to the user
            return project_settings

        return False

    def get_project_setting(self, project_name=None, setting_key=None):

        # get all the project settings first
        self.project_settings = self.get_project_settings(project_name=project_name)

        if self.project_settings:

            # is there a setting_key in the project settings
            if setting_key in self.project_settings:
                # then return the setting value
                return self.project_settings[setting_key]

        # if the setting key wasn't found
        return None

    def save_project_setting(self, project_name=None, setting_key=None, setting_value=None):
        '''
        Saves only a specific project setting, by getting the saved project settings and only overwriting
        the setting that was passed (setting_key)
        :param project_name:
        :param setting_key:
        :param setting_value:
        :return:
        '''

        if project_name is None or project_name == '' or setting_key is None:
            logger.error('Insufficient data. Unable to save project setting.')
            return False

        # get the current project settings
        self.project_settings = self.get_project_settings(project_name=project_name)

        # convert None values to False
        if setting_value is None:
            setting_value = False

        # only overwrite the passed setting_key
        self.project_settings[setting_key] = setting_value

        # now save them to file
        self.save_project_settings(project_name=project_name, project_settings=self.project_settings)

        return True

    def get_timeline_setting(self, project_name=None, timeline_name=None, setting_key=None):
        '''
        This gets a specific timeline setting from the project.json by looking into the timelines dictionary
        :param project_name:
        :param timeline_name:
        :param setting_key:
        :return:
        '''

        # get all the project settings first
        self.project_settings = self.get_project_settings(project_name=project_name)

        if self.project_settings:

            # is there a timeline dictionary?
            # is there a reference regarding the passed timeline?
            # is there a reference regarding the passed setting key?
            if 'timelines' in self.project_settings \
                    and timeline_name in self.project_settings['timelines'] \
                    and setting_key in self.project_settings['timelines'][timeline_name]:
                # then return the setting value
                return self.project_settings['timelines'][timeline_name][setting_key]

        # if the setting key, or any of the stuff above wasn't found
        return None

    def check_update(self):
        '''
        This checks if there's a new version of the app on GitHub and returns True if it is and the version number
        :return: [bool, str online_version]
        '''
        from requests import get
        version_request = "https://raw.githubusercontent.com/octimot/StoryToolkitAI/main/version.py"

        # retrieve the latest version number from github
        try:
            r = get(version_request, verify=True)

            # extract the actual version number from the string
            online_version_raw = r.text.split('"')[1]

        # show exception if it fails, but don't crash
        except Exception as e:
            logger.warning('Unable to check the latest version of StoryToolkitAI: {}. '
                           'Is your Internet connection working?'.format(e))

            # return False - no update available and None instead of an online version number
            return False, None

        # get the numbers in the version string
        local_version = self.__version__.split(".")
        online_version = online_version_raw.split(".")

        # take each number in the version string and compare it with the local numbers
        for n in range(len(online_version)):

            # only test for the first 3 numbers in the version string
            if n < 3:
                # if there's a number larger online, return true
                if int(online_version[n]) > int(local_version[n]):
                    return True, online_version_raw

                # continue the search if there's no version mismatch
                if int(online_version[n]) == int(local_version[n]):
                    continue
                break

        # return false (and the online version) if the local and the online versions match
        return False, online_version_raw

    def check_ffmpeg(self):

        # check if ffmpeg is installed

        try:
            # get the FFMPEG_BINARY variable or try the ffmpeg command if not
            ffmpeg_binary = os.getenv('FFMPEG_BINARY', 'ffmpeg')
            cmd = [
                ffmpeg_binary]

            # check if ffmpeg answers the call
            exit_code = subprocess.call(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # if it does, just return true
            return True

        except FileNotFoundError:
            # if the ffmpeg binary wasn't found, we presume that ffmpeg is not installed on the machine
            return False


if __name__ == '__main__':

    # keep a global StoryToolkitAI object for now
    global stAI

    # init StoryToolkitAI object
    stAI = StoryToolkitAI()

    # check if a new version of the app exists
    [update_exists, online_version] = stAI.check_update()

    # check if ffmpeg is installed
    ffmpeg_status = stAI.check_ffmpeg()

    # if an update exists, let the user know about it
    update_available = None
    if update_exists:
        update_available = online_version

    # initialize operations object
    toolkit_ops_obj = ToolkitOps(stAI=stAI)

    # initialize GUI
    app_UI = toolkit_UI(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI,
                        update_available=update_available,
                        ffmpeg_status=ffmpeg_status)

    # connect app UI to operations object
    toolkit_ops_obj.toolkit_UI_obj = app_UI

    # create the main window
    app_UI.create_main_window()