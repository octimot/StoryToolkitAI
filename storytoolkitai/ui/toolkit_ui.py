import platform
import subprocess
import webbrowser

from requests import get
import time
import re
import hashlib

from timecode import Timecode

from storytoolkitai.core.logger import *
from storytoolkitai import USER_DATA_PATH, OLD_USER_DATA_PATH, APP_CONFIG_FILE_NAME, initial_target_dir

from storytoolkitai.core.toolkit_ops import *

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, font
from tkinter import *

from whisper import available_models as whisper_available_models

from .menu import UImenus

class toolkit_UI:
    '''
    This handles all the GUI operations mainly using tkinter
    '''

    class TranscriptEdit:
        '''
        All the functions available in the transcript window should be part of this class
        '''

        def __init__(self, toolkit_UI_obj=None):

            # keep a reference to the toolkit_UI object here
            self.toolkit_UI_obj = toolkit_UI_obj

            # keep a reference to the StoryToolkitAI object here
            self.stAI = toolkit_UI_obj.stAI

            # keep a reference to the toolkit_ops_obj object here
            self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj

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
            # here, they are simply ordered in their line orders, where the segment_index is line_no-1:
            #               self.transcript_segments[window_id][segment_index] = segment_dict
            # the segment_index is not the segment_id mentioned below!
            self.transcript_segments = {}

            # we need this to have a reference between
            # the line number of a segment within the transcript and the id of that segment in the transcription file
            # so the dict should look like: self.transcript_segments_ids[window_id][segment_line_no] = segment_id
            # the segment_id is not the segment_index mentioned above!
            self.transcript_segments_ids = {}

            # save other data from the transcription file for each window here
            self.transcription_data = {}

            # save transcription groups of each transcription window here
            self.transcript_groups = {}

            # save the selected groups of each transcription window here
            # (multiple selections allowed)
            self.selected_groups = {}

            # all the selected transcript segments of each window
            # the selected segments dict will use the text element line number as an index, for eg:
            # self.selected_segments[window_id][line] = transcript_segment
            self.selected_segments = {}

            # to keep track of the modified transcripts
            self.transcript_modified = {}

            # the active_segment stores the text line number of each window to keep track where
            # the cursor is currently on the transcript
            self.active_segment = {}

            # when changed, active segments line numbers move to last_active_segment
            self.last_active_segment = {}

            # the current timecode of each window
            self.current_window_tc = {}

            # this keeps track of which transcription window is in sync with the resolve playhead
            self.sync_with_playhead = {}

        def link_to_timeline_button(self, button: tk.Button = None, transcription_file_path: str = None,
                                    link=None, timeline_name: str = None, window_id: str = None):

            if transcription_file_path is None and window_id is None:
                logger.debug('No transcription file path or window id provided')
                return None

            # if no transcription file path was provided, try to get it from the window id
            if transcription_file_path is None and window_id is not None \
                    and window_id in self.transcription_file_paths:
                transcription_file_path = self.transcription_file_paths[window_id]

            # if no window id was passed, get it from the transcription file path
            if window_id is None and transcription_file_path is not None:
                # this is stored in the self.transcription_file_paths dict, where the key is the window id
                # and the value is the transcription file path
                for key, value in self.transcription_file_paths.items():
                    if value == transcription_file_path:
                        window_id = key
                        break

            # if no button was passed, try to get it from the window
            if button is None or button is not tk.Button:
                button = self.toolkit_UI_obj.windows[window_id].nametowidget('footer_frame.link_button')

            link_result = self.toolkit_ops_obj.link_transcription_to_timeline(
                transcription_file_path=transcription_file_path,
                link=link, timeline_name=timeline_name)

            # make the UI link (or unlink) the transcript to the timeline
            if link_result and link_result is not None:

                # check if the data in the transcription file is valid
                if window_id is not None and window_id in self.transcript_segments:
                    transcription_data = self.transcription_data[window_id]

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

            if window_id is None:
                return False

            self.sync_with_playhead_update(window_id, sync)

            # update the transcript window GUI
            self.toolkit_UI_obj.update_transcription_window(window_id)

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
            This also tags the search results in the text element
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
            if event.keysym in ['Up', 'Down', 'v', 'V', 'A', 'i', 'o', 'O', 'm', 'M', 'C', 'q', 's', 'L',
                                'g', 'G', 'BackSpace', 't', 'a',
                                'apostrophe', 'semicolon', 'colon', 'quotedbl']:
                self.segment_actions(event, **attributes)

        def transcription_window_mouse(self, event=None, **attributes):
            '''
            What to do with mouse presses on transcription windows?
            :param event:
            :param attributes:
            :return:
            '''

            # print(event.state)
            # for now simply pass the event to the segment actions
            self.segment_actions(event, mouse=True, **attributes)

        def segment_actions(self, event=None, text_element=None, window_id=None,
                            special_key=None, mouse=False, status_label=None):
            '''
            Handles the key and mouse presses in relation with transcript segments (lines)
            :return:
            '''

            if text_element is None or window_id is None:
                return False

            # if special_key is not None:
            #     print(special_key)

            # HERE ARE SOME USEFUL SHORTCUTS FOR THE TRANSCRIPTION WINDOW:
            # see the shortcuts in the README file

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

                # if cmd was also pressed
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

            # CMD+A key events (select all)
            if event.keysym == 'a' and special_key == 'cmd':
                # get the number of segments in the transcript
                num_segments = len(self.transcript_segments[window_id])

                # create a list containing all the segment numbers
                segment_list = list(range(1, num_segments + 1))

                # select all segments by passing all the line numbers
                self.segment_to_selection(window_id, text_element, segment_list)

                return 'break'

            # Shift+A key events
            if event.keysym == 'A':

                # first, try to see if there is a text selection
                selection = text_element.tag_ranges("sel")

                # if there is a selection
                if len(selection) > 0:

                    # get the first and last segment numbers of the selection
                    start_segment = int(str(selection[0]).split(".")[0])
                    max_segment = int(str(selection[1]).split(".")[0])

                    # clear the selection
                    text_element.tag_delete("sel")

                else:

                    # select all segments between the active_segment and the last_active_segment
                    start_segment = self.last_active_segment[window_id]
                    max_segment = self.active_segment[window_id]

                # make sure that we're counting in the right direction
                if start_segment > max_segment:
                    start_segment, max_segment = max_segment, start_segment

                # first clear the entire selection
                self.clear_selection(window_id, text_element)

                # then take each segment, starting with the lowest and select them
                n = start_segment
                while n <= max_segment:
                    self.segment_to_selection(window_id, text_element, n)
                    n = n + 1

            # Shift+C key event (copy segments with timecodes to clipboard)
            if event.keysym == 'C':

                # is control also pressed?
                if special_key == 'cmd':
                    # copy segment with timecodes
                    # self.copy_segment_timecodes(window_id, text_element, line)
                    text, _, _, _ \
                        = self.get_segments_or_selection(window_id, split_by='line',
                                                         add_to_clipboard=True, add_time_column=True)

                else:
                    # copy the text content to clipboard
                    self.get_segments_or_selection(window_id, add_to_clipboard=True, split_by='index')

            # m key event (quick add duration markers)
            # and Shift+M key event (add duration markers with name input)
            # CMD/CTRL+M key event (select all segments between markers)
            if event.keysym == 'm' or event.keysym == 'M':

                # this only works if resolve is connected
                if self.toolkit_ops_obj.resolve_exists() and 'name' in NLE.current_timeline:

                    # select segments based on current timeline markers
                    # (from Resolve to tool)
                    if special_key == 'cmd':

                        # first, see if there are any markers on the timeline
                        if 'markers' not in NLE.current_timeline:
                            return

                        # get the marker colors from all the markers in the current_timeline['markers'] dict
                        marker_colors = [' '] + sorted(list(set([NLE.current_timeline['markers'][marker]['color']
                                                                 for marker in NLE.current_timeline['markers']])))

                        # create a list of widgets for the input dialogue
                        input_widgets = [
                            {'name': 'starts_with', 'label': 'Starts With:', 'type': 'entry', 'default_value': ''},
                            {'name': 'color', 'label': 'Color:', 'type': 'option_menu', 'default_value': 'Blue',
                             'options': marker_colors}
                        ]

                        # then we call the ask_dialogue function
                        user_input = self.toolkit_UI_obj.AskDialog(title='Markers to Selection',
                                                                   input_widgets=input_widgets,
                                                                   parent=self.toolkit_UI_obj.windows[window_id]
                                                                   ).value()

                        # if the user didn't cancel add the group
                        if user_input != None:

                            # get the user input
                            starts_with = user_input['starts_with']
                            color = user_input['color']

                            selected_markers = {}

                            # go through the markers on the timeline
                            for marker in NLE.current_timeline['markers']:

                                # if the marker starts with the text the user entered (if not empty)
                                # and the marker color matches the color the user selected (if not empty)
                                if (starts_with == ''
                                    or NLE.current_timeline['markers'][marker]['name'].startswith(starts_with)) \
                                        and (color == ' ' or NLE.current_timeline['markers'][marker]['color'] == color):
                                    # add the marker to the marker_groups dictionary
                                    selected_markers[marker] = NLE.current_timeline['markers'][marker]

                            # if there are markers in the selection
                            if len(selected_markers) > 0:

                                time_intervals = []

                                # add them to the transcript group, based on their start time and duration
                                # the start time (marker) and duration are in frames
                                for marker in selected_markers:
                                    # convert the frames to seconds
                                    start_time = int(marker) / NLE.current_timeline_fps
                                    duration = int(
                                        NLE.current_timeline['markers'][marker]['duration']) / NLE.current_timeline_fps
                                    end_time = start_time + duration

                                    # add the time interval to the list of time intervals
                                    time_intervals.append({'start': start_time, 'end': end_time})

                                # the transcript segments:

                                # convert the time intervals to segments
                                segment_list = \
                                    self.toolkit_ops_obj \
                                        .time_intervals_to_transcript_segments(time_intervals=time_intervals,
                                                                               segments=self.transcript_segments[
                                                                                   window_id],
                                                                               )
                                # now select the segments
                                self.segment_to_selection(window_id, text_element, segment_list)

                    # otherwise (if cmd wasn't pressed)
                    # add segment based markers
                    # (from tool to Resolve)
                    else:

                        # first get the selected (or active) text from the transcript
                        # this should return a list of all the text chunks, the full text
                        #   and the start and end times of the entire text
                        text, full_text, start_sec, end_sec = \
                            self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                                           split_by='index', timecodes=True)

                        # now, take care of the marker name
                        marker_name = False
                        marker_color = self.stAI.get_app_setting('default_marker_color', default_if_none='Blue')

                        # if Shift+M was pressed, prompt the user for the marker name
                        if event.keysym == 'M':

                            # create a list of widgets for the input dialogue
                            input_widgets = [
                                {'name': 'name', 'label': 'Name:', 'type': 'entry', 'default_value': ''},
                                {'name': 'color', 'label': 'Color:', 'type': 'option_menu',
                                 'default_value': self.stAI.get_app_setting('default_marker_color',
                                                                            default_if_none='Blue'),
                                 'options': self.toolkit_UI_obj.resolve_marker_colors.keys()}
                            ]

                            # then we call the ask_dialogue function
                            user_input = self.toolkit_UI_obj.AskDialog(title='Add Markers from Selection',
                                                                       input_widgets=input_widgets,
                                                                       parent=self.toolkit_UI_obj.windows[window_id]
                                                                       ).value()

                            # if the user didn't cancel add the group
                            if user_input == None:
                                return False

                            marker_name = user_input['name']
                            marker_color = user_input['color']

                            # if the user pressed cancel, return
                            if not marker_name or marker_name == '':
                                return False

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
                            marker_duration_tc = end_tc - start_tc

                            # in Resolve, marker indexes are the number of frames from the beginning of the timeline
                            # so in order to get the marker index, we need to subtract the timeline_start_tc from start_tc

                            # but only if the start_tc is larger than the timeline_start_tc so we don't get a
                            # Timecode class error
                            if start_tc > timeline_start_tc:
                                start_tc_zero = start_tc - timeline_start_tc
                                marker_index = start_tc_zero.frames

                            # if not consider that we are at frame 1
                            else:
                                marker_index = 1

                            # check if there's another marker at the exact same index
                            index_blocked = True
                            while index_blocked:

                                if 'markers' in NLE.current_timeline and marker_index in NLE.current_timeline['markers']:

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
                                        start_tc.frames = start_tc.frames + 1
                                        marker_index = marker_index + 1

                                        # but this means that the duration should be one frame shorter
                                        marker_duration_tc.frames = marker_duration_tc.frames - 1
                                    else:
                                        return False

                                else:
                                    index_blocked = False

                            marker_data = {}
                            marker_data[marker_index] = {}

                            # the name of the marker
                            marker_data[marker_index]['name'] = marker_name

                            # choose the marker color from Resolve
                            marker_data[marker_index]['color'] = marker_color

                            # add the text to the marker data
                            marker_data[marker_index]['note'] = text_chunk['text']

                            # the marker duration needs to be in frames
                            marker_data[marker_index]['duration'] = marker_duration_tc.frames

                            # no need for custom data
                            marker_data[marker_index]['customData'] = ''

                            # pass the marker add request to resolve
                            self.toolkit_ops_obj.resolve_api.add_timeline_markers(NLE.current_timeline['name'],
                                                                                  marker_data,
                                                                                  False)

            # q key event (close transcription window)
            if event.keysym == 'q':
                # close transcription window
                self.toolkit_UI_obj.destroy_transcription_window(window_id)

            # Shift+L key event (link current timeline to this transcription)
            if event.keysym == 'L':
                # link transcription to file
                # self.toolkit_ops_obj.link_transcription_to_timeline(self.transcription_file_paths[window_id])
                self.link_to_timeline_button(window_id=window_id)

            # s key event (sync transcript cursor with playhead)
            if event.keysym == 's':
                # self.sync_with_playhead_update(window_id=window_id)
                self.sync_with_playhead_button(window_id=window_id)

            # CMD+G and CMD+SHIFT+G key events
            # (group selected - adds new group or updates segments of existing group)
            if (event.keysym == 'g' or event.keysym == 'G') and special_key == 'cmd':

                # if a group is selected, just update it
                if window_id in self.selected_groups and len(self.selected_groups[window_id]) == 1:

                    # use the selected group id
                    group_id = self.selected_groups[window_id][0]

                    # if the user pressed CMD+G, replace the current segments with the selected ones
                    if event.keysym == 'g':

                        # update group
                        self.toolkit_UI_obj.on_group_update_press(t_window_id=window_id,
                                                                  t_group_window_id=window_id + '_transcript_groups',
                                                                  group_id=group_id)

                        logger.debug('Segments added to group {}.'.format(group_id))

                    # if the user pressed CMD+SHIFT+G,
                    # add selected segments to the group, without removing any existing one
                    elif event.keysym == 'G':

                        # add selected segments to the group, but keep the name and the notes
                        self.group_selected(window_id=window_id, group_name=group_id, add=True,
                                            keep_name=True, keep_notes=True)

                        logger.debug('Only new segments added to group {}.'.format(group_id))

                        # update group
                        # self.toolkit_UI_obj.on_group_update_press(t_window_id=window_id,
                        #                                           t_group_window_id=window_id+'_transcript_groups',
                        #                                           group_id=group_id)

                # otherwise create a new group
                else:
                    if self.group_selected(window_id=window_id):
                        logger.info('Group added')


            # SHIFT+G opens group window
            elif event.keysym == 'G':
                self.toolkit_UI_obj.open_transcript_groups_window(transcription_window_id=window_id)

            # colon key event (align current line start to playhead)
            if event.keysym == 'colon':
                self.align_line_to_playhead(window_id=window_id, line_index=line, position='start')

            # double quote key event (align current line end to playhead)
            if event.keysym == 'quotedbl':
                self.align_line_to_playhead(window_id=window_id, line_index=line, position='end')

            # 't' key event (re-transcribe selected segments)
            if event.keysym == 't':

                # first get the selected (or active) text from the transcript
                text, full_text, start_sec, end_sec = \
                    self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                                   split_by='index', timecodes=True, allow_active_segment=False)

                # now turn the text blocks into time intervals
                time_intervals = ''
                retranscribe = False
                ask_message = "Do you want to re-transcribe the entire transcript?"
                if text is not None and text and len(text) > 0:

                    # get all the time intervals based on the text blocks
                    for text_block in text:
                        time_intervals = time_intervals + "{}-{}\n".format(text_block['start'], text_block['end'])

                    ask_message = "Do you want to re-transcribe the selected segments?"

                # ask the user if they want to re-transcribe
                retranscribe = messagebox.askyesno(title='Re-transcribe',
                                                   message=ask_message)

                # if the user cancels re-transcribe or no segments were selected, cancel
                if not retranscribe:
                    return False

                # and start the transcription config process
                self.toolkit_ops_obj \
                    .prepare_transcription_file(toolkit_UI_obj=self.toolkit_UI_obj,
                                                task='transcribe',
                                                retranscribe=self.transcription_file_paths[window_id],
                                                time_intervals=time_intervals)

                # close the transcription window
                # @todo (temporary solution until we work on a better way to update transcription windows
                self.toolkit_UI_obj.destroy_transcription_window(window_id)

                # remove the selection references too
                # self.clear_selection(window_id=window_id)

            # 'o' key sends active segment as context to the Assistant window
            # Shift+O also includes a time column
            if event.keysym == 'o' or event.keysym == 'O':

                # Shift+O includes a time column
                if event.keysym == 'O':
                    text, full_text, _, _ \
                        = self.get_segments_or_selection(window_id, split_by='line', add_time_column=True)

                else:
                    text, full_text, _, _ \
                        = self.get_segments_or_selection(window_id, split_by='line',
                                                         add_time_column=False, timecodes=False)

                self.toolkit_UI_obj.open_assistant_window(assistant_window_id='assistant',
                                                          transcript_text=full_text.strip())

            # BackSpace key event (delete selected)
            if event.keysym == 'BackSpace':
                self.delete_line(window_id=window_id, text_element=text_element,
                                 line_no=line, status_label=status_label)

        def delete_line(self, window_id, text_element, line_no, status_label):
            '''
            Deletes a specific line of text from the transcript and saves the file
            :param window_id:
            :param text_element:
            :param line_index:
            :return:
            '''

            # WORK IN PROGRESS

            if line_no > len(self.transcript_segments[window_id]):
                return False

            # ask the user if they are sure
            if messagebox.askyesno(title='Delete line',
                                   message='Are you sure you want to delete this line?'):
                # get the line
                tkinter_line_index = '{}.0'.format(line_no), '{}.0'.format(int(line_no) + 1).split(' ')

                # enable editing on the text element
                text_element.config(state=NORMAL)

                # delete the line - doesn't work!
                # remove the line from the text widget
                text_element.delete(tkinter_line_index[0], tkinter_line_index[1])

                # disable editing on the text element
                text_element.config(state=DISABLED)

                # calculate the segment index
                segment_index = int(line_no) - 1

                # remove the line from the text list
                self.transcript_segments[window_id].pop(segment_index)

                # mark the transcript as modified
                self.set_transcript_modified(window_id=window_id, modified=True)

                # save the transcript
                save_status = self.save_transcript(window_id=window_id, text=False, skip_verification=True)

                # let the user know what happened via the status label
                self.update_status_label_after_save(status_label=status_label, save_status=save_status)

                return True

            return False

        def align_line_to_playhead(self, window_id, line_index, position=None):
            """
            Aligns a transcript line to the playhead (only works if Resolve is connected)
            by setting the start time or end time of the line to the playhead position.

            :param window_id: the window id
            :param line_index: the segment index
            :param position: the position to align to (the start or the end of the segment)
            :return: None
            """

            if position is None:
                logger.error('No position specified for align_line_to_playhead()')
                return False

            if NLE.is_connected() is None:
                logger.error('Resolve is not connected.')
                return False

            move_playhead = messagebox.askokcancel(title='Move playhead',
                                                   message='Move the Resolve playhead exactly '
                                                           'where you want to align the {} of this segment, '
                                                           'then press OK to align.'.format(position)
                                                   )

            if not move_playhead:
                logger.debug('User cancelled segment alignment.')
                return False

            # convert the current_tc to seconds
            current_tc_sec = self.toolkit_ops_obj.calculate_resolve_timecode_to_sec()

            # check if we actually have a timecode
            if current_tc_sec is None:
                self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                          message='Cannot align to playhead: '
                                                                  'Resolve playhead timecode not available.',
                                                          type='error')
                return False

            # convert line_index to segment_index (not segment_id!)
            segment_index = line_index - 1

            # stop if the segment index is not in the transcript segments
            if segment_index > len(self.transcript_segments[window_id]) - 1:
                logger.error('Cannot align line to playhead: no segment index found.')
                return False

            # get the segment data
            segment_data = self.transcript_segments[window_id][segment_index]

            # replace the start or end time with the current_tc_sec
            if position == 'start':
                segment_data['start'] = current_tc_sec
            elif position == 'end':
                segment_data['end'] = current_tc_sec

            # return False if no position was specified
            # (will probably never reach this since we're checking it above)
            else:
                logger.error('No position specified for align_line_to_playhead()')
                return False

            # check if the start time is after the end time
            # and throw an error and cancel if it is
            if segment_data['start'] >= segment_data['end']:
                self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                          message='Cannot align to playhead: '
                                                                  'Start time is after end time.',
                                                          type='error')
                return False

            # check if the start time is before the previous segment end time
            # and throw an error and cancel if it is
            if segment_index > 0:
                if segment_data['start'] < self.transcript_segments[window_id][segment_index - 1]['end']:
                    self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                              message='Cannot align to playhead: '
                                                                      'Start time is before previous segment\'s end time.',
                                                              type='error')
                    return False

            # check if the end time is after the next segment start time
            # and throw an error and cancel if it is
            if segment_index < len(self.transcript_segments[window_id]) - 1:
                if segment_data['end'] > self.transcript_segments[window_id][segment_index + 1]['start']:
                    self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                              message='Cannot align to playhead: '
                                                                      'End time is after next segment\'s start time.',
                                                              type='error')
                    return False

            # update the transcript segments
            self.transcript_segments[window_id][segment_index] = segment_data

            # mark the transcript as modified
            self.set_transcript_modified(window_id=window_id, modified=True)

            # save the transcript
            self.save_transcript(window_id=window_id, text=False, skip_verification=True)

            return True

        def get_segments_or_selection(self, window_id, add_to_clipboard=False, split_by=None, timecodes=True,
                                      allow_active_segment=True, add_time_column=False):
            '''
            Used to extract the text from either the active segment or from the selection
            Will return the text, and the start and end times

            If the split_by parameter is 'index', the text will be split into blocks of text that
            are next to each other in the main transcript_segments[window_id] list.

            If the split_by parameter is 'time', the text will be split into blocks of text that
            have no time gaps between them.

            If timecodes is true, the return will also include the text blocks' start and end timecodes
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

                if type(timeline_start_tc) is Timecode:
                    timeline_fps = timeline_start_tc.framerate

                # try to get the start timecode, fps and timeline name from the transcription data dict
                if not timeline_start_tc and window_id in self.transcription_data:

                    logger.debug('Timeline timecode not available, trying transcription data instead')

                    timeline_start_tc = self.transcription_data[window_id]['timeline_start_tc'] \
                        if 'timeline_start_tc' in self.transcription_data[window_id] else None

                    timeline_fps = self.transcription_data[window_id]['timeline_fps'] \
                        if 'timeline_fps' in self.transcription_data[window_id] else None

                    # convert the timeline_start_tc to a Timecode object but only if the fps is also known
                    if timeline_start_tc is not None and timeline_fps is not None:
                        timeline_start_tc = Timecode(timeline_fps, timeline_start_tc)
                    else:
                        timeline_start_tc = None
                        logger.debug('Timeline timecode not available in transcription data either')

                # if no timecode was received it probably means Resolve is disconnected so disable timecodes
                if not timeline_start_tc or timeline_start_tc is None:
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

                    # split each blocks of text that are next to each other in the main transcript_segments[window_id] list
                    if split_by == 'index':

                        # assign a value if this is the first transcript_segment_index of this iteration
                        if prev_transcript_segment_index is None:
                            prev_transcript_segment_index = transcript_segment_index

                        # if the segment is not right after the previous segment that we processed
                        # it means that there are other segments between them which haven't been selected
                        elif prev_transcript_segment_index + 1 != transcript_segment_index:
                            current_chunk_num = current_chunk_num + 1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text + '\n[...]\n'

                    # split into blocks of text that have no time gaps between them
                    if split_by == 'time':

                        # assign the end time of the first selected segment
                        if prev_segment_end_time is None:
                            prev_segment_end_time = selected_segment['end']

                        # if the start time of the current segment
                        # doesn't match with the end time of the previous segment
                        elif selected_segment['start'] != prev_segment_end_time:
                            current_chunk_num = current_chunk_num + 1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text + '\n[...]\n'

                    # add the current segment text to the current text chunk
                    text[current_chunk_num]['text'] = \
                        text[current_chunk_num]['text'] + '\n' + selected_segment['text'].strip() \
                            if 'text' in text[current_chunk_num] else selected_segment['text']

                    # add the start time to the current text block
                    # but only for the first segment of this text block
                    # and we determine that by checking if the start time is not already set
                    if 'start' not in text[current_chunk_num]:
                        text[current_chunk_num]['start'] = selected_segment['start']

                        # also calculate the start timecode of this text chunk (only if Resolve available)
                        # the end timecode isn't needed at this point, so no sense in wasting resources
                        text[current_chunk_num]['start_tc'] = None
                        if timecodes:

                            # init the segment start timecode object
                            # but only if the start seconds are larger than 0
                            if float(selected_segment['start']) > 0:
                                segment_start_timecode = Timecode(timeline_fps,
                                                                  start_seconds=selected_segment['start'])

                                # factor in the timeline start tc and use it for this chunk
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc + segment_start_timecode)

                            # otherwise use the timeline_start_timecode
                            else:
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc)

                            # add it to the beginning of the text
                            text[current_chunk_num]['text'] = \
                                text[current_chunk_num]['start_tc'] + ':\n' + text[current_chunk_num]['text'].strip()

                            # add it to the full text body
                            # but only if we're not adding a time column later
                            if not add_time_column:
                                full_text = full_text + '\n' + text[current_chunk_num]['start_tc'] + ':\n'

                    # add the end time of the current text chunk
                    text[current_chunk_num]['end'] = selected_segment['end']

                    # add the time to the full text, if this was requested
                    if add_time_column:
                        # use timecode or seconds depending on the timecodes parameter
                        time_column = text[current_chunk_num]['start_tc'] \
                            if timecodes else '{:.2f}'.format(text[current_chunk_num]['start'])

                        full_text = '{}{}\t'.format(full_text, str(time_column))

                    # add the segment text to the full text variable
                    full_text = (full_text + selected_segment['text'].strip() + '\n')

                    # remember the index for the next iteration
                    prev_transcript_segment_index = transcript_segment_index

                    # split the text by each line, no matter if they're next to each other or not
                    if split_by == 'line':
                        current_chunk_num = current_chunk_num + 1
                        text.append({})



            # if there are no selected segments on this window
            # get the text of the active segment
            else:
                # if active segments are not allowed
                if not allow_active_segment:
                    return None, None, None, None

                # if there is no active_segment for the window
                if window_id not in self.active_segment:
                    # create one
                    self.active_segment[window_id] = 1

                # get the line number from the active segment
                line = self.active_segment[window_id]

                # we need to convert the line number to the segment_index used in the transcript_segments list
                segment_index = line - 1

                # add the time in front of the text
                # if add_time_column:
                #    full_text = str(self.transcript_segments[window_id][segment_index]['start']) + '\t'

                # get the text form the active segment
                full_text = self.transcript_segments[window_id][segment_index]['text'].strip()

                # get the start and end times from the active segment
                start_sec = self.transcript_segments[window_id][segment_index]['start']
                end_sec = self.transcript_segments[window_id][segment_index]['end']

                # add this to the return list
                text = [{'text': full_text.strip(), 'start': start_sec, 'end': end_sec, 'start_tc': None}]

                if NLE.is_connected() and timecodes:
                    start_seconds = start_sec if int(start_sec) > 0 else 0.01
                    start_tc = None

                    # init the segment start timecode object
                    # but only if the start seconds are larger than 0
                    if start_sec > 0:
                        segment_start_timecode = Timecode(timeline_fps, start_seconds=start_sec)

                        # factor in the timeline start tc and use it for this chunk
                        start_tc = str(timeline_start_tc + segment_start_timecode)

                    # otherwise use the timeline_start_timecode
                    else:
                        start_tc = str(timeline_start_tc)

                    # add it at the beginning of the text body
                    full_text = start_tc + ':\n' + full_text

                    # add this to the return list
                    text = [{'text': full_text.strip(), 'start': start_sec, 'end': end_sec, 'start_tc': start_tc}]

            # remove the last empty text chunk
            if 'text' not in text[-1]:
                text.pop()

            if add_to_clipboard:
                self.root.clipboard_clear()
                self.root.clipboard_append(full_text.strip())
                logger.debug('Copied segments to clipboard')

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
                segment_index = line - 1

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

            # update the transcription window
            self.toolkit_UI_obj.update_transcription_window(window_id=window_id)

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

        def get_transcription_window_text_element(self, window_id=None):

            if window_id is None:
                logger.error('No window id was passed.')
                return None

            # search through all the elements in the window until we find the transcript text element
            for child in self.toolkit_UI_obj.windows[window_id].winfo_children():

                # go another level deeper, since we are expecting the transcript text element to be inside a frame
                if len(child.winfo_children()) > 0:
                    for child2 in child.winfo_children():
                        if child2.winfo_name() == 'transcript_text':
                            return child2

            # if we get here, we didn't find the transcript text element
            return None

        def set_active_segment(self, window_id=None, text_element=None, line=None, line_calc=None):

            # if no text element is passed,
            # try to get the transcript text element from the window with the window_id
            if text_element is None and self.toolkit_UI_obj is not None and window_id is not None \
                    and window_id in self.toolkit_UI_obj.windows:
                text_element = self.get_transcription_window_text_element(window_id=window_id)

            # if no text element is found, return
            if text_element is None:
                return False

            # remove any active segment tags
            text_element.tag_delete('l_active')

            # count the number of lines in the text
            text_num_lines = len(self.transcript_segments[window_id])

            # initialize the active segment number
            self.active_segment[window_id] = self.get_active_segment(window_id)

            # interpret the line number correctly
            # by passing line_calc, we can add that to the current line number
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

            if window_id is None:
                return False

            self.selected_segments[window_id] = {}

            self.selected_segments[window_id].clear()

            if text_element is None:
                text_element = self.get_transcription_window_text_element(window_id=window_id)

            if text_element is not None:
                text_element.tag_delete("l_selected")

        def segment_to_selection(self, window_id=None, text_element=None, line: int or list = None):
            '''
            This either adds or removes a segment to a selection,
            depending if it's already in the selection or not

            If line is a list, it will add all the lines in the list to the selection and remove the rest

            :param window_id:
            :param text_element:
            :param line: Either the line no. or a list of line numbers
                        (if a list is passed, it will only add and not remove)
                        (if a list of segments is passed, it will get each segment's line number)
            :return:
            '''

            # if no text element is passed,
            # try to get the transcript text element from the window with the window_id
            if text_element is None and self.toolkit_UI_obj is not None and window_id is not None \
                    and window_id in self.toolkit_UI_obj.windows:
                text_element = self.get_transcription_window_text_element(window_id=window_id)

            if window_id is None or text_element is None or line is None:
                return False

            # if there is no selected_segments dict for the current window, create one
            if window_id not in self.selected_segments:
                self.selected_segments[window_id] = {}

            # if a list of lines was passed, add all the lines to the selection
            if type(line) is list:

                # first clear the selection
                self.clear_selection(window_id=window_id, text_element=text_element)

                # select all the lines in the list
                for line_num in line:

                    # if a list of segments was passed (if they are dicts)
                    # we need to convert them to line numbers
                    if type(line_num) is dict:
                        # get the line number from the segment
                        line_num = self.segment_id_to_line(window_id=window_id, segment_id=line_num['id'])

                    # convert the line number to segment_index
                    segment_index = line_num - 1

                    self.selected_segments[window_id][line_num] = self.transcript_segments[window_id][segment_index]

                    # tag the text on the text element
                    text_element.tag_add("l_selected", "{}.0".format(line_num), "{}.end+1c".format(line_num))

                    # raise the tag so we can see it above other tags
                    text_element.tag_raise("l_selected")

                    # color the tag accordingly
                    text_element.tag_config('l_selected', foreground='blue',
                                            background=self.toolkit_UI_obj.resolve_theme_colors['superblack'])

                return True

            # if a single line was passed, add or remove it from the selection
            else:

                # convert the line number to segment_index
                segment_index = line - 1

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
                return int(max_id) + 1

            # if all fails return None
            return None

        def group_selected(self, window_id: str, group_name: str = None, add: bool = False, **kwargs) -> bool:
            '''
            This adds the selected segments to a group based on their start and end times
            :param window_id:
            :param group_name: If this is passed, we're just adding the selected segments to the group
            :param add: If this is True, we're adding the selected segments to the group,
                        if it's False, we're keeping only what is selected in the group
            :return:
            '''

            # group_name = 'another test group'
            # group_notes = 'some test notes'

            # this will not be preserved if this is an add operation
            group_notes = kwargs.get('group_notes', '')

            # if we have some selected segments, group them
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:

                # if no group name is available, ask the user for one
                if group_name is None:
                    # ask the user for a group name
                    group_name = simpledialog.askstring('Group name', 'Group name:')

                    # if the user didn't enter anything or canceled, abort
                    if not group_name:
                        return False

                # get the path of the window transcription file based on the window id
                if window_id in self.transcription_file_paths:
                    transcription_file_path = self.transcription_file_paths[window_id]
                else:
                    return False

                # get the existing groups
                if window_id in self.transcript_groups:
                    transcript_groups = self.transcript_groups[window_id]

                else:
                    transcript_groups = {}

                # the segments we pass for grouping need to be in a list format
                segments_for_group = list(self.selected_segments[window_id].values())

                # lowercase all dictionary keys for non-case sensitive comparison
                transcript_groups_lower = {k.lower(): v for k, v in transcript_groups.items()}

                # if this is an add operation and
                # if the group name was passed and it exists in the groups of this transcription,
                # add the selected segments to that group instead of creating a new one
                # (so keep the old segments in the group too)
                if add is True and group_name is not None and group_name.lower() in transcript_groups_lower \
                        and len(transcript_groups[group_name]) > 0 \
                        and 'time_intervals' in transcript_groups[group_name] \
                        and len(transcript_groups[group_name]['time_intervals']) > 0:

                    # keep the notes if they exist and we're supposed to keep them
                    if 'notes' in transcript_groups[group_name] and kwargs.get('keep_notes', False):
                        group_notes = transcript_groups[group_name]['notes']

                    # keep the name if we're supposed to keep it
                    if kwargs.get('keep_name', False):
                        group_name = transcript_groups[group_name]['name']

                    # but we first need to get the existing segments in the group
                    # by going through the time intervals of the group and getting the corresponding segments
                    existing_group_segments = \
                        self.toolkit_ops_obj.time_intervals_to_transcript_segments(
                            transcript_groups[group_name]['time_intervals'],
                            self.transcript_segments[window_id]
                        )

                    if existing_group_segments is not None:
                        # then we add the new segments to the existing ones
                        # don't worry if there are duplicates, the save function will take care of that
                        segments_for_group += existing_group_segments

                    logger.debug('Adding segments to group: {}'.format(group_name))

                # but if this is not an add operation, yet the group exists in the groups of this transcription
                # make sure the user understands that we're overwriting the existing group
                # BTW to simplify things we're now using the lower case version of the group name as a group_id
                elif add is False and group_name is not None and group_name.strip().lower() in transcript_groups_lower:

                    # ask the user if they're sure they want to overwrite the existing group
                    overwrite = messagebox.askyesno(message='Group already exists\nDo you want to overwrite it?\n\n'
                                                            'This will also empty the group notes.')

                    # if the user didn't confirm, abort
                    if not overwrite:
                        return False

                    logger.debug('Overwriting group: {}'.format(group_name))

                else:
                    logger.debug('Creating new group: {}'.format(group_name))

                # save the segments to the transcription file
                save_return = self.toolkit_ops_obj.t_groups_obj \
                    .save_segments_as_group_in_transcription_file(
                    transcription_file_path=transcription_file_path,
                    segments=segments_for_group,
                    group_name=group_name,
                    group_notes=group_notes,
                    existing_transcript_groups=transcript_groups,
                    overwrite_existing=True
                )

                if type(save_return) is dict:

                    # initialize the empty group if it doesn't exist
                    if window_id not in self.transcript_groups:
                        self.transcript_groups[window_id] = {}

                    # if the returned value is a dictionary, it means that the window groups have been updated
                    # so we need to update the groups of this window
                    self.transcript_groups[window_id] = save_return

                else:
                    logger.debug('Something may have went wrong while saving the group to the transcription file')
                    return False

                # update the list of groups in the transcript groups window
                self.toolkit_UI_obj.update_transcript_groups_window(t_window_id=window_id)

                return True

        def delete_group(self, t_window_id: str, group_id: str, no_confirmation: bool = False, **kwargs) -> bool:
            '''
            This deletes a group from the transcription file
            and updates the transcription groups window (optional, only if t_group_window_id, groups_listbox are passed)

            :param t_window_id: The transcription window id
            :param group_id:
            :param no_confirmation: If this is True, we're not asking the user for confirmation
            :return:
            '''

            # get the path of the window transcription file based on the window id
            if t_window_id in self.transcription_file_paths:
                transcription_file_path = self.transcription_file_paths[t_window_id]
            else:
                logger.debug('Could not find transcription file path for window id: {}'.format(t_window_id))
                return False

            # get the existing groups
            if t_window_id in self.transcript_groups:
                transcript_groups = self.transcript_groups[t_window_id]

            else:
                transcript_groups = {}
                return True

            # check the group id
            if group_id is None or group_id.strip() == '':
                logger.debug('No group id was passed')
                return False

            # if the group id exists in the groups of this transcription
            if group_id in transcript_groups:

                group_name = transcript_groups[group_id]['name']

                # ask the user if they're sure they want to delete the group
                if not no_confirmation:
                    delete = messagebox.askyesno(message=
                                                 'Are you sure you want to delete '
                                                 'the group "{}"?'.format(group_name))

                    # if the user didn't confirm, abort
                    if not delete:
                        return False

                # remove the group from the groups dictionary
                del transcript_groups[group_id]

                # save the groups to the transcription file
                save_return = self.toolkit_ops_obj.t_groups_obj \
                    .save_transcript_groups(transcription_file_path=transcription_file_path,
                                            transcript_groups=transcript_groups)

                # if the returned value is a dictionary, it means that the window groups have been updated
                if type(save_return) is dict:

                    # update the window with the returned transcript groups
                    self.transcript_groups[t_window_id] = save_return

                    # if the selected group is no longer in the groups of this window
                    # make sure it's also not selected anymore
                    if t_window_id in self.selected_groups \
                            and group_id in self.selected_groups[t_window_id]:
                        # remove the group from the selected groups
                        self.selected_groups[t_window_id].remove(group_id)

                    # update the transcript groups window, if the right arguments were passed:
                    # the kwargs should contain the transcript groups window id and the groups listbox
                    if 't_group_window_id' in kwargs and 'groups_listbox' in kwargs:
                        self.toolkit_UI_obj.update_transcript_groups_window(t_window_id=t_window_id, **kwargs)

                    return True

                else:
                    logger.debug('Something may have went wrong while saving the groups to the transcription file')
                    return False

        def on_press_add_segment(self, event, window_id=None, text=None):
            '''
            This adds a new segment to the transcript
            :param event: the event that triggered this function
            :param window_id: the window id
            :param text: the text element
            :return:
            '''

            if window_id is None or text is None:
                return False

            # get the cursor position where the event was triggered (key was pressed)
            # and the last character of the line
            line, char, last_char = self.get_current_segment_chars(text=text)

            # print('Pos: {}.{}; Last: {}'.format(line, char, last_char))

            # initialize the new_line dict
            new_line = {}

            # the end time of the new line is the end of the current line
            new_line['end'] = self.transcript_segments[window_id][int(line) - 1]['end']

            # get the text that is supposed to go on the next line
            new_line['text'] = text.get(INSERT, "{}.end".format(line))

            # the id of the new line is the next available id in the transcript
            new_line['id'] = self.next_segment_id(window_id=window_id)

            # keep in mind the minimum and maximum split times
            split_time_seconds_min = self.transcript_segments[window_id][int(line) - 1]['start']
            split_time_seconds_max = self.transcript_segments[window_id][int(line) - 1]['end']

            # if resolve is connected, get the timecode from resolve
            if NLE.is_connected():

                # ask the user to move the playhead in Resolve to where the split should happen via info dialog
                move_playhead = messagebox.askokcancel(title='Move playhead',
                                                       message='Move the Resolve playhead exactly '
                                                               'where the new segment starts, '
                                                               'then press OK to split.'
                                                       )

                if not move_playhead:
                    logger.debug('User cancelled segment split.')
                    return 'break'

                # convert the current resolve timecode to seconds
                split_time_seconds = self.toolkit_ops_obj.calculate_resolve_timecode_to_sec()

            # if resolve isn't connected, ask the user to enter the timecode manually
            else:

                # ask the user to enter the timecode manually
                split_time_seconds = simpledialog.askstring(
                    parent=self.toolkit_UI_obj.windows[window_id],
                    title='Where to split?',
                    prompt='At what time should we split this segment?\n\n'
                           'Enter a value between {} and {}:\n'
                    .format(split_time_seconds_min,
                            split_time_seconds_max),
                    initialvalue=split_time_seconds_min)

            # if the user didn't specify the split time
            if not split_time_seconds:
                # cancel
                return 'break'

            if float(split_time_seconds) >= float(split_time_seconds_max):
                self.toolkit_UI_obj.notify_via_messagebox(title='Time Value Error',
                                                          message="The {} time is larger "
                                                                  "than the end time of "
                                                                  "the segment you're splitting. Try again.".
                                                          format('playhead' if NLE.is_connected() else 'entered'),
                                                          type='warning')
                return 'break'

            if float(split_time_seconds) <= float(split_time_seconds_min):
                self.toolkit_UI_obj.notify_via_messagebox(title='Time Value Error',
                                                          message="The {} time is smaller "
                                                                  "than the start time of "
                                                                  "the segment you're splitting. Try again.".
                                                          format('playhead' if NLE.is_connected() else 'entered'),
                                                          type='warning')

                return 'break'

            # the split time becomes the start time of the new line
            new_line['start'] = split_time_seconds

            # and also the end of the previous line
            self.transcript_segments[window_id][int(line) - 1]['end'] = split_time_seconds

            # add the element to the transcript segments right after the current line
            self.transcript_segments[window_id].insert(int(line), new_line)

            # remove the text after the split from the current line
            text.delete("{}.{}".format(line, char), "{}.end".format(line))

            # re-insert the text after the last character of the current line, but also add a line break
            text.insert("{}.end+1c".format(line), new_line['text'] + '\n')

            # remap the line numbers to segment ids for this window
            self.remap_lines_to_segment_ids(window_id=window_id, text=text)

            # prevent RETURN key from adding another line break in the text
            return 'break'

        def remap_lines_to_segment_ids(self, window_id, text):

            if window_id is None or text is None:
                return False

            # get all the lines of this text widget
            text_lines = text.get('1.0', END).splitlines()

            # reset self.transcript_segments_ids[window_id]
            self.transcript_segments_ids[window_id] = {}

            if len(text_lines) > 0:

                # go through all the lines and re check segment ids
                for line_no, line in enumerate(text_lines):

                    # the last line of the text widget is always empty, so avoid that
                    if line_no < len(self.transcript_segments[window_id]):
                        # print(line_no, line)

                        # get the segment id for this line directly from the transcript segments dict
                        # that we updated earlier during the split
                        line_segment_id = self.transcript_segments[window_id][line_no]['id']

                        # remap the line no to segment ids for this window
                        self.transcript_segments_ids[window_id][line_no] = line_segment_id

            return True

        def edit_transcript(self, window_id=None, text=None, status_label=None):

            if window_id is None or text is None:
                return False

            text.focus()

            # enable typing mode to disable some shortcuts
            self.set_typing_in_window(window_id=window_id, typing=True)

            # enable transcript_editing for this window
            self.set_transcript_editing(window_id=window_id, editing=True)

            text.bind('<Return>', lambda e: self.on_press_add_segment(e, window_id, text))

            # ESCAPE key defocuses transcript (and implicitly saves the transcript, see below)
            text.bind('<Escape>', lambda e: self.defocus_transcript(text=text))

            # text focusout saves transcript
            text.bind('<FocusOut>', lambda e: self.on_press_save_transcript(e, window_id, text,
                                                                            status_label=status_label))

            # BACKSPACE key at first line character merges the current and the previous segment
            text.bind('<BackSpace>', lambda e:
            self.on_press_merge_segments(e, window_id=window_id, text=text, merge='previous'))

            # DELETE key at last line character merges the current and the next segment
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

        def set_transcript_modified(self, window_id=None, modified=True):
            '''
            This function sets the transcript_modified flag for the given window
            :param window_id:
            :param modified:
            :return:
            '''

            if window_id is None:
                return False

            self.transcript_modified[window_id] = modified

        def get_transcript_modified(self, window_id):
            '''
            This function returns the transcript_modified flag for the given window
            :param window_id:
            :return:
            '''

            if window_id in self.transcript_modified:
                return self.transcript_modified[window_id]
            else:
                return False

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
            if char not in ['0', last_char] \
                    or (char == '0' and merge != 'previous') \
                    or (char == last_char and merge != 'next'):
                return

            # if we are at the beginning of the line
            # and the merge direction is 'prev'
            if char == '0' and merge == 'previous':

                # get the previous segment
                previous_segment = self.transcript_segments[window_id][int(line) - 2]

                # get the current segment
                current_segment = self.transcript_segments[window_id][int(line) - 1]

                # merge the current segment with the previous one
                previous_segment['end'] = current_segment['end']
                previous_segment['text'] = previous_segment['text'] + '' + current_segment['text'].lstrip()

                if 'tokens' in current_segment and 'tokens' in previous_segment:
                    previous_segment['tokens'] = previous_segment['tokens'] + current_segment['tokens']

                # signal that the transcript segments has been modified
                previous_segment['merged'] = True

                # remove the line break from the previous line
                text.delete("{}.end".format(int(line) - 1), "{}.end+1c".format(int(line) - 1))

                # update the previous segment in the list
                self.transcript_segments[window_id][int(line) - 2] = previous_segment

                # remove the current segment from the list (the list starts with index 0)
                self.transcript_segments[window_id].pop(int(line) - 1)

                # remap self.transcript_segments_ids
                self.remap_lines_to_segment_ids(window_id=window_id, text=text)

                # update the transcript_modified flag
                self.set_transcript_modified(window_id=window_id, modified=True)

                # we're done, prevent the event from propagating and deleting any characters
                return 'break'

            # if we are at the end of the line
            # and the merge direction is 'next'
            if char == last_char and merge == 'next':

                # get the current segment
                current_segment = self.transcript_segments[window_id][int(line) - 1]

                # get the next segment
                next_segment = self.transcript_segments[window_id][int(line)]

                # merge the current segment with the next one
                current_segment['end'] = next_segment['end']
                current_segment['text'] = current_segment['text'] + '' + next_segment['text'].lstrip()

                if 'tokens' in current_segment and 'tokens' in next_segment:
                    current_segment['tokens'] = current_segment['tokens'] + next_segment['tokens']

                # signal that the transcript segments have been modified
                current_segment['merged'] = True

                # remove the line break from current line
                text.delete('{}.end'.format(line), '{}.end+1c'.format(line))

                # remove the next segment from the list (the list starts with index 0)
                self.transcript_segments[window_id].pop(int(line))

                # remap self.transcript_segments_ids
                self.remap_lines_to_segment_ids(window_id=window_id, text=text)

                # update the transcript_modified flag
                self.set_transcript_modified(window_id=window_id, modified=True)

                # we're done
                return 'break'

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
            self.update_status_label_after_save(status_label=status_label, save_status=save_status)

        def update_status_label_after_save(self, save_status, status_label):

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

        def save_transcript(self, window_id=None, text=None, skip_verification=False):
            '''
            This function saves the transcript to the file

            :param window_id:
            :param text:
            :param skip_verification: if this is True, the function will not verify
                                        if the transcript has been modified and ignore the new text
                                        (useful for non-text updates, like start/end time changes etc.)
            :return:
            '''

            if window_id is None or text is None:
                logger.debug('No window id or text provided.')
                return False

            # make sure that we know the path to this transcription file
            if not window_id in self.transcription_file_paths:
                return 'fail'

            # get the path of the transcription file
            transcription_file_path = self.transcription_file_paths[window_id]

            # get the contents of the transcription file
            old_transcription_file_data = \
                self.toolkit_ops_obj.get_transcription_file_data(transcription_file_path=transcription_file_path)

            # does the transcription file contain word level timings?
            word_level_timings = False
            if len(old_transcription_file_data['segments']) > 0 and 'words' in old_transcription_file_data['segments'][
                0]:
                word_level_timings = True

            # only verify if skip_verification is False or the text is False
            if not skip_verification or text is not False:

                # compare the edited lines with the existing transcript lines
                text_lines = text.get('1.0', END).splitlines()

                segment_no = 0
                full_text = ''

                # find out if the transcript has been modified
                modified = self.get_transcript_modified(window_id=window_id)

                # but even if the transcript has not been modified,
                # we still need to check if the transcript has been edited
                while segment_no < len(text_lines) - 1:

                    # add the segment text to a full text variable in case we need it later
                    full_text = full_text + ' ' + text_lines[segment_no]

                    # if any change to the text was found
                    if text_lines[segment_no].strip() != self.transcript_segments[window_id][segment_no][
                        'text'].strip():
                        # overwrite the segment text with the new text
                        self.transcript_segments[window_id][segment_no]['text'] = text_lines[segment_no].strip() + ' '

                        # it means that we have to save the new file
                        modified = True

                    segment_no = segment_no + 1

            # make sure to no longer use the text below if skip_verification is True
            else:
                text = False
                modified = True
                full_text = None

            # if the transcript has been modified (changes detected above or simply modified flag is True)
            if modified:

                modified_transcription_file_data = old_transcription_file_data

                # replace the segments in the transcription file
                modified_transcription_file_data['segments'] = self.transcript_segments[window_id]

                if text is not False:
                    # replace the full text in the trancription file
                    modified_transcription_file_data['text'] = full_text

                # add the last modified key
                modified_transcription_file_data['last_modified'] = str(time.time()).split('.')[0]

                # the directory where the transcription file is
                transcription_file_dir = os.path.dirname(transcription_file_path)

                # now save the txt file
                # if there is no txt file associated with this transcription
                if 'txt_file_path' not in modified_transcription_file_data \
                        or modified_transcription_file_data['txt_file_path'] == '':

                    txt_file_name = os.path.basename(transcription_file_path).replace('.transcription.json', '.txt')

                else:
                    txt_file_name = modified_transcription_file_data['txt_file_path']

                if txt_file_name is not None and txt_file_name != '':
                    # the txt file should be in the same directory as the transcription file
                    txt_file_path = os.path.join(transcription_file_dir, txt_file_name)

                    # add the file to the transcription file data
                    modified_transcription_file_data['txt_file_path'] = txt_file_name

                    # save the txt file
                    self.toolkit_ops_obj.save_txt_from_transcription(
                        txt_file_path=txt_file_path,
                        transcription_data=modified_transcription_file_data
                    )

                # now save the srt file
                srt_file_name = None

                # if there is no srt file associated with this transcription
                if 'srt_file_path' not in modified_transcription_file_data \
                        or modified_transcription_file_data['srt_file_path'] == '':

                    # ask the user if they want to create an srt file
                    create_srt = messagebox.askyesno('Create SRT file?',
                                                     'An SRT file doesn\'t exist for this transcription.\n'
                                                     'Do you want to create one?')

                    # if the user wants to create an srt file
                    if create_srt:
                        # the name of the srt file is based on the name of the transcription file
                        srt_file_name = os.path.basename(transcription_file_path).replace('.transcription.json', '.srt')

                else:
                    srt_file_name = modified_transcription_file_data['srt_file_path']

                if srt_file_name is not None and srt_file_name != '':
                    # the srt file should be in the same directory as the transcription file
                    srt_file_path = os.path.join(transcription_file_dir, srt_file_name)

                    # add the file to the transcription file data
                    modified_transcription_file_data['srt_file_path'] = srt_file_name

                    # save the srt file
                    self.toolkit_ops_obj.save_srt_from_transcription(
                        srt_file_path=srt_file_path,
                        transcription_data=modified_transcription_file_data
                    )

                # finally, save the transcription file
                self.toolkit_ops_obj.save_transcription_file(transcription_file_path=transcription_file_path,
                                                             transcription_data=modified_transcription_file_data,
                                                             backup='backup')

                return True

            # returning false means that no changes were made
            return False

    class AppItemsUI:

        def __init__(self, toolkit_UI_obj):

            if toolkit_UI_obj is None:
                logger.error('No toolkit_UI_obj provided for AppItemsUI.')
                raise Exception('No toolkit_UI_obj provided.')

            # declare the UI, ops and app objects for easier access
            self.toolkit_UI_obj = toolkit_UI_obj
            self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj
            self.stAI = toolkit_UI_obj.stAI
            self.UI_menus = UImenus

            # the root window inherited from the toolkit_UI_obj
            self.root = toolkit_UI_obj.root

            return

        def open_preferences_window(self):
            '''
            Opens the preferences window.
            :return:
            '''

            # create a window for the transcription settings if one doesn't already exist
            if pref_window := self.toolkit_UI_obj.create_or_open_window(parent_element=self.root,
                                                                        window_id='preferences',
                                                                        title='Preferences', resizable=True,
                                                                        return_window=True):

                form_grid_and_paddings = {**self.toolkit_UI_obj.input_grid_settings,
                                          **self.toolkit_UI_obj.form_paddings}

                label_settings = self.toolkit_UI_obj.label_settings
                if 'width' in label_settings:
                    del label_settings['width']

                entry_settings = self.toolkit_UI_obj.entry_settings
                entry_settings_quarter = self.toolkit_UI_obj.entry_settings_quarter

                # the settings for the heading labels
                h1_font = {'font': self.toolkit_UI_obj.default_font_h1, 'justify': 'center',
                           'pady': self.toolkit_UI_obj.form_paddings['pady']}

                pref_form_frame = tk.Frame(pref_window)
                pref_form_frame.pack()

                # these are the app settings that can be changed

                # take all the customizable app settings and create a variable for each one

                console_font_size_var \
                    = tk.IntVar(pref_form_frame,
                                value=self.stAI.get_app_setting('console_font_size', default_if_none=13))

                show_welcome_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('show_welcome', default_if_none=True))

                api_token_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('api_token', default_if_none=''))

                openai_api_key_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('openai_api_key', default_if_none=''))

                disable_resolve_api_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('disable_resolve_api', default_if_none=False))
                default_marker_color_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('default_marker_color', default_if_none='Blue'))

                open_transcript_groups_window_on_open_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('show_welcome', default_if_none=True))

                close_transcripts_on_timeline_change_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('close_transcripts_on_timeline_change',
                                                                    default_if_none=True))

                whisper_model_name_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('whisper_model_name', default_if_none='medium'))

                whisper_device_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('whisper_device', default_if_none='auto'))

                transcription_default_language_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('transcription_default_language',
                                                                   default_if_none=''))

                transcription_pre_detect_speech_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('transcription_pre_detect_speech',
                                                                    default_if_none=True))

                transcription_word_timestamps_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('transcription_word_timestamps',
                                                                    default_if_none=True))

                transcription_max_chars_per_segment_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('transcription_max_chars_per_segment',
                                                                   default_if_none=''))

                transcription_max_words_per_segment_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('transcription_max_words_per_segment',
                                                                   default_if_none=''))

                transcription_split_on_punctuation_marks_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('transcription_split_on_punctuation_marks',
                                                                   default_if_none=False))

                transcription_prevent_short_gaps_var \
                    = tk.StringVar(pref_form_frame,
                                      value=self.stAI.get_app_setting('transcription_prevent_short_gaps',
                                                                        default_if_none=''))

                transcription_render_preset_var \
                    = tk.StringVar(pref_form_frame,
                                   value=self.stAI.get_app_setting('transcription_render_preset',
                                                                   default_if_none='transcription_WAV'))

                transcript_font_size_var \
                    = tk.IntVar(pref_form_frame,
                                value=self.stAI.get_app_setting('transcript_font_size', default_if_none=15))

                transcripts_always_on_top_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('transcripts_always_on_top', default_if_none=False))

                transcripts_skip_settings_var \
                    = tk.BooleanVar(pref_form_frame,
                                    value=self.stAI.get_app_setting('transcripts_skip_settings', default_if_none=False))

                # ffmpeg_path_var\
                #    = tk.StringVar(pref_form_frame,
                #                    value=self.stAI.get_app_setting('ffmpeg_path', default_if_none=''))

                # now create the form for all of the above settings
                # general settings
                tk.Label(pref_form_frame, text='General Settings', **h1_font).grid(row=0, column=0, columnspan=2,
                                                                                   **form_grid_and_paddings)

                # the font size for the console
                tk.Label(pref_form_frame, text='Console Font Size', **label_settings).grid(row=2, column=0,
                                                                                           **form_grid_and_paddings)
                console_font_size_input = tk.Entry(pref_form_frame, textvariable=console_font_size_var,
                                                   **entry_settings_quarter)
                console_font_size_input.grid(row=2, column=1, **form_grid_and_paddings)

                # show the welcome window on startup
                tk.Label(pref_form_frame, text='Show Welcome Window', **label_settings).grid(row=3, column=0,
                                                                                             **form_grid_and_paddings)
                show_welcome_input = tk.Checkbutton(pref_form_frame, variable=show_welcome_var)
                show_welcome_input.grid(row=3, column=1, **form_grid_and_paddings)

                # the show window can only be updated if the user has a valid API token
                if not self.stAI.api_token_valid:
                    show_welcome_input.config(state='disabled')
                else:
                    show_welcome_input.config(state='normal')

                # api token
                tk.Label(pref_form_frame, text='StoryToolkitAI API Token', **label_settings).grid(row=4, column=0,
                                                                                                  **form_grid_and_paddings)
                api_token_input = tk.Entry(pref_form_frame, textvariable=api_token_var, **entry_settings)
                api_token_input.grid(row=4, column=1, **form_grid_and_paddings)

                # OpenAI API key
                tk.Label(pref_form_frame, text='OpenAI API Key', **label_settings).grid(row=5, column=0,
                                                                                        **form_grid_and_paddings)
                openai_api_key_input = tk.Entry(pref_form_frame, show="*", textvariable=openai_api_key_var,
                                                **entry_settings)
                openai_api_key_input.grid(row=5, column=1, **form_grid_and_paddings)

                # Integrations
                tk.Label(pref_form_frame, text='Integrations', **h1_font).grid(row=14, column=0, columnspan=2,
                                                                               **form_grid_and_paddings)

                # disable the resolve API
                tk.Label(pref_form_frame, text='Disable Resolve API', **label_settings).grid(row=15, column=0,
                                                                                             **form_grid_and_paddings)
                disable_resolve_api_input = tk.Checkbutton(pref_form_frame, variable=disable_resolve_api_var)
                disable_resolve_api_input.grid(row=15, column=1, **form_grid_and_paddings)

                # auto open the transcript groups window on timeline open
                tk.Label(pref_form_frame, text='Open Linked Transcripts', **label_settings).grid(row=16, column=0,
                                                                                                 **form_grid_and_paddings)
                open_transcript_groups_window_on_open_input = tk.Checkbutton(pref_form_frame,
                                                                             variable=open_transcript_groups_window_on_open_var)
                open_transcript_groups_window_on_open_input.grid(row=16, column=1, **form_grid_and_paddings)

                # close transcripts on timeline change
                tk.Label(pref_form_frame, text='Close Transcripts on Timeline Change', **label_settings).grid(row=17,
                                                                                                              column=0,
                                                                                                              **form_grid_and_paddings)
                close_transcripts_on_timeline_change_input = tk.Checkbutton(pref_form_frame,
                                                                            variable=close_transcripts_on_timeline_change_var)
                close_transcripts_on_timeline_change_input.grid(row=17, column=1, **form_grid_and_paddings)

                # the default marker color
                tk.Label(pref_form_frame, text='Default Marker Color', **label_settings).grid(row=18, column=0,
                                                                                              **form_grid_and_paddings)

                # the dropdown for the default marker color
                default_marker_color_input = tk.OptionMenu(pref_form_frame,
                                                           default_marker_color_var,
                                                           *self.toolkit_UI_obj.resolve_marker_colors)
                default_marker_color_input.grid(row=18, column=1, **form_grid_and_paddings)

                # the render preset for transcriptions
                tk.Label(pref_form_frame, text='Transcription Render Preset', **label_settings).grid(row=19, column=0,
                                                                                                     **form_grid_and_paddings)
                transcription_render_preset_input = tk.Entry(pref_form_frame,
                                                             textvariable=transcription_render_preset_var,
                                                             **entry_settings)
                transcription_render_preset_input.grid(row=19, column=1, **form_grid_and_paddings)

                # transcriptions
                tk.Label(pref_form_frame, text='Transcriptions', **h1_font).grid(row=21, column=0, columnspan=2,
                                                                                 **form_grid_and_paddings)

                # the whisper model name
                tk.Label(pref_form_frame, text='Whisper Model', **label_settings).grid(row=22, column=0,
                                                                                       **form_grid_and_paddings)
                whisper_model_name_input = tk.OptionMenu(pref_form_frame, whisper_model_name_var,
                                                         *whisper_available_models())
                whisper_model_name_input.grid(row=22, column=1, **form_grid_and_paddings)

                # the whisper device
                tk.Label(pref_form_frame, text='Whisper Device', **label_settings).grid(row=23, column=0,
                                                                                        **form_grid_and_paddings)
                whisper_device_input = tk.OptionMenu(pref_form_frame, whisper_device_var,
                                                     *self.toolkit_ops_obj.get_torch_available_devices())
                whisper_device_input.grid(row=23, column=1, **form_grid_and_paddings)

                # the default language for transcriptions
                # first get the list of languages, but also add an empty string to the list
                available_languages = [''] + self.toolkit_ops_obj.get_whisper_available_languages()

                tk.Label(pref_form_frame, text='Default Language', **label_settings).grid(row=24, column=0,
                                                                                          **form_grid_and_paddings)
                transcription_default_language_input = tk.OptionMenu(pref_form_frame,
                                                                     transcription_default_language_var,
                                                                     *available_languages)
                transcription_default_language_input.grid(row=24, column=1, **form_grid_and_paddings)

                # pre-detect speech
                tk.Label(pref_form_frame, text='Pre-Detect Speech', **label_settings).grid(row=25, column=0,
                                                                                           **form_grid_and_paddings)
                transcription_pre_detect_speech_input = tk.Checkbutton(pref_form_frame,
                                                                       variable=transcription_pre_detect_speech_var)
                transcription_pre_detect_speech_input.grid(row=25, column=1, **form_grid_and_paddings)

                # word timestamps (use "increased time precision" for now)
                tk.Label(pref_form_frame, text='Increased Time Precision', **label_settings).grid(row=26, column=0,
                                                                                                  **form_grid_and_paddings)
                transcription_word_timestamps_input = tk.Checkbutton(pref_form_frame,
                                                                     variable=transcription_word_timestamps_var)
                transcription_word_timestamps_input.grid(row=26, column=1, **form_grid_and_paddings)

                # max characters per line
                tk.Label(pref_form_frame, text='Max. Characters Per Line', **label_settings).grid(row=27, column=0,
                                                                                                  **form_grid_and_paddings)
                max_chars_per_segment_input = tk.Entry(pref_form_frame,
                                                       textvariable=transcription_max_chars_per_segment_var,
                                                       **entry_settings_quarter)
                max_chars_per_segment_input.grid(row=27, column=1, **form_grid_and_paddings)

                # only allow integers
                max_chars_per_segment_input.config(validate="key",
                                                   validatecommand=
                                                   (max_chars_per_segment_input.register(
                                                       self.toolkit_UI_obj.only_allow_integers), '%P'))

                # max characters per line
                tk.Label(pref_form_frame, text='Max. Words Per Line', **label_settings).grid(row=28, column=0,
                                                                                             **form_grid_and_paddings)
                max_words_per_segment_input = tk.Entry(pref_form_frame,
                                                       textvariable=transcription_max_words_per_segment_var,
                                                       **entry_settings_quarter)
                max_words_per_segment_input.grid(row=28, column=1, **form_grid_and_paddings)

                # only allow integers
                max_words_per_segment_input.config(validate="key",
                                                   validatecommand=
                                                   (max_words_per_segment_input.register(
                                                       self.toolkit_UI_obj.only_allow_integers), '%P'))

                # split on punctuation
                tk.Label(pref_form_frame, text='Split On Punctuation', **label_settings).grid(row=29, column=0,
                                                                                              **form_grid_and_paddings)
                split_on_punctuation_marks_input = tk.Checkbutton(pref_form_frame,
                                                                  variable=transcription_split_on_punctuation_marks_var)
                split_on_punctuation_marks_input.grid(row=29, column=1, **form_grid_and_paddings)

                # prevent short gaps between segments
                tk.Label(pref_form_frame, text='Prevent Gaps Shorter Than', **label_settings)\
                    .grid(row=30, column=0, **form_grid_and_paddings)
                prevent_short_gaps_input = tk.Entry(pref_form_frame, textvariable=transcription_prevent_short_gaps_var,
                                                    **entry_settings_quarter)
                prevent_short_gaps_input.grid(row=30, column=1, **form_grid_and_paddings)

                # only allow floats
                prevent_short_gaps_input.config(validate="key",
                                                validatecommand=
                                                (prevent_short_gaps_input.register(
                                                    self.toolkit_UI_obj.only_allow_floats), '%P'))

                # the transcript font size
                tk.Label(pref_form_frame, text='Transcript Font Size', **label_settings).grid(row=31, column=0,
                                                                                              **form_grid_and_paddings)
                transcript_font_size_input = tk.Entry(pref_form_frame, textvariable=transcript_font_size_var,
                                                      **entry_settings_quarter)
                transcript_font_size_input.grid(row=31, column=1, **form_grid_and_paddings)

                # transcripts always on top
                tk.Label(pref_form_frame, text='Transcript Always On Top', **label_settings).grid(row=32, column=0,
                                                                                                  **form_grid_and_paddings)
                transcripts_always_on_top_input = tk.Checkbutton(pref_form_frame,
                                                                 variable=transcripts_always_on_top_var)
                transcripts_always_on_top_input.grid(row=32, column=1, **form_grid_and_paddings)

                # skip transcription settings
                tk.Label(pref_form_frame, text='Skip Transcription Settings', **label_settings).grid(row=33, column=0,
                                                                                                     **form_grid_and_paddings)
                transcripts_skip_settings_input = tk.Checkbutton(pref_form_frame,
                                                                 variable=transcripts_skip_settings_var)
                transcripts_skip_settings_input.grid(row=33, column=1, **form_grid_and_paddings)

                # ffmpeg path
                # tk.Label(pref_form_frame, text='FFmpeg Path', **label_settings).grid(row=14, column=0, **form_grid_and_paddings)
                # ffmpeg_path_input = tk.Entry(pref_form_frame, textvariable=ffmpeg_path_var, **entry_settings)
                # ffmpeg_path_input.grid(row=14, column=1, **form_grid_and_paddings)

                # SAVE BUTTON

                # keep track of all the input variables above
                input_variables = {
                    'default_marker_color': default_marker_color_var,
                    'console_font_size': console_font_size_var,
                    'show_welcome': show_welcome_var,
                    'api_token': api_token_var,
                    'openai_api_key': openai_api_key_var,
                    'disable_resolve_api': disable_resolve_api_var,
                    'open_transcript_groups_window_on_open': open_transcript_groups_window_on_open_var,
                    'close_transcripts_on_timeline_change': close_transcripts_on_timeline_change_var,
                    'whisper_model_name': whisper_model_name_var,
                    'whisper_device': whisper_device_var,
                    'transcription_default_language': transcription_default_language_var,
                    'transcription_pre_detect_speech': transcription_pre_detect_speech_var,
                    'transcription_word_timestamps': transcription_word_timestamps_var,
                    'transcription_max_chars_per_segment': transcription_max_chars_per_segment_var,
                    'transcription_max_words_per_segment': transcription_max_words_per_segment_var,
                    'transcription_split_on_punctuation_marks': transcription_split_on_punctuation_marks_var,
                    'transcription_prevent_short_gaps': transcription_prevent_short_gaps_var,
                    'transcription_render_preset': transcription_render_preset_var,
                    'transcript_font_size': transcript_font_size_var,
                    'transcripts_always_on_top': transcripts_always_on_top_var,
                    'transcripts_skip_settings': transcripts_skip_settings_var,
                    # 'ffmpeg_path': ffmpeg_path_var
                }

                Label(pref_form_frame, text="", **label_settings).grid(row=50, column=0, **form_grid_and_paddings)
                start_button = tk.Button(pref_form_frame, text='Save')
                start_button.grid(row=40, column=1, **form_grid_and_paddings)
                start_button.config(command=lambda: self.save_preferences(input_variables))

        def save_preferences(self, input_variables: dict) -> bool:
            '''
            Save the preferences stored in the input_variables to the app config file
            :param input_variables:
            :return:
            '''

            # if the user has entered a new API token, check if it's valid
            if input_variables['api_token'].get() != '' \
                    and input_variables['api_token'].get() != self.stAI.config['api_token']:

                if not self.stAI.check_api_token(input_variables['api_token'].get()):
                    self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error', message='Invalid API token.')
                    return False

            # save all the variables to the config file
            for key, value in input_variables.items():
                self.stAI.config[key] = value.get()

            # save the config file
            if self.stAI.save_config():

                # close the window
                self.toolkit_UI_obj.destroy_window_(self.toolkit_UI_obj.windows, 'preferences')

                # let the user know it worked
                self.toolkit_UI_obj.notify_via_messagebox(type='info', title='Preferences Saved',
                                                          message='Preferences saved successfully.\n\n'
                                                                  'Please restart StoryToolkitAI for the new settings '
                                                                  'to take full effect.',
                                                          message_log='Preferences saved, need restart for full effect')

                return True

            else:
                self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error',
                                                          message='Preferences could not be saved.\n'
                                                                  'Check log for details.',
                                                          message_log='Preferences could not be saved')

                return False

        def open_about_window(self):
            '''
            Open the about window
            :return:
            '''

            # open the about window

            # create a window for the transcription log if one doesn't already exist
            if about_window := self.toolkit_UI_obj.create_or_open_window(parent_element=self.root,
                                                                         window_id='about',
                                                                         title='About StoryToolkitAI', resizable=False,
                                                                         return_window=True):
                # the text justify
                justify = {'justify': tk.LEFT}

                # create a frame for the about window
                about_frame = Frame(about_window)
                about_frame.pack(**self.toolkit_UI_obj.paddings)

                # add the app name text
                app_name = 'StoryToolkitAI version ' + self.stAI.version

                # create the app name heading
                app_name_label = Label(about_frame, text=app_name, font=self.toolkit_UI_obj.default_font_h1, **justify)
                app_name_label.grid(column=1, row=1, sticky='w')

                # the made by frame
                made_by_frame = Frame(about_frame)
                made_by_frame.grid(column=1, row=2, sticky='w')

                # create the made by label
                made_by_label = Label(made_by_frame, text='made by', font=self.toolkit_UI_obj.default_font, **justify)
                made_by_label.pack(side=tk.LEFT)

                # create the mots link label
                mots_label = Label(made_by_frame, text='mots', font=self.toolkit_UI_obj.default_font_link, **justify)
                mots_label.pack(side=tk.LEFT)

                # make the made by text clickable
                mots_label.bind('<Button-1>', self.UI_menus.open_mots)

                # the project page frame
                project_page_frame = Frame(about_frame)
                project_page_frame.grid(column=1, row=3, sticky='w', pady=self.toolkit_UI_obj.paddings['pady'])

                # add the project page label
                project_page_label = Label(project_page_frame, text='Project page:',
                                           font=self.toolkit_UI_obj.default_font, **justify)
                project_page_label.pack(side=tk.LEFT)

                # create the project page link label
                project_page_link_label = Label(project_page_frame, text='github.com/octimot/StoryToolkitAI',
                                                font=self.toolkit_UI_obj.default_font_link, **justify)
                project_page_link_label.pack(side=tk.LEFT)

                # make the project page text clickable
                project_page_link_label.bind('<Button-1>', self.UI_menus.open_project_page)

                # add license info
                license_info_label = Label(about_frame, text='For third party software and license information\n'
                                                             'see the project page.',
                                           font=self.toolkit_UI_obj.default_font, **justify)
                license_info_label.grid(column=1, row=4, sticky='w')

                return True

            return

    def __init__(self, toolkit_ops_obj=None, stAI=None, **other_options):

        # make a reference to toolkit ops obj
        self.toolkit_ops_obj = toolkit_ops_obj

        # make a reference to StoryToolkitAI obj
        self.stAI = stAI

        # initialize tkinter as the main GUI
        self.root = tk.Tk()

        # what happens when the user tries to close the main window
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        # add icon
        try:
            photo = tk.PhotoImage(file='UI/StoryToolkitAI.png')
            self.root.wm_iconphoto(False, photo)

            # set bar icon for windows
            if sys.platform == 'win32':
                self.root.iconbitmap('UI/StoryToolkitAI.ico')

        except:
            logger.debug('Could not load StoryToolkitAI icon.')

        # initialize app items object
        self.app_items_obj = self.AppItemsUI(toolkit_UI_obj=self)

        # load menu object
        self.UI_menus = UImenus(toolkit_UI_obj=self)

        logger.debug('Running with TK {}'.format(self.root.call("info", "patchlevel")))

        # initialize transcript edit object
        self.t_edit_obj = self.TranscriptEdit(toolkit_UI_obj=self)

        # alert the user if ffmpeg isn't installed
        if 'ffmpeg_status' in other_options and not other_options['ffmpeg_status']:
            self.notify_via_messagebox(title='FFMPEG not found',
                                       message='FFMPEG was not found on this machine.\n'
                                               'Please follow the installation instructions or StoryToolkitAI will '
                                               'not work correctly.',
                                       type='error'
                                       )

        # show welcome message, if it wasn't muted via configs
        # if self.stAI.get_app_setting('show_welcome', default_if_none=True):
        #    self.open_welcome_window()

        # keep all the window references here to find them easy by window_id
        self.windows = {}

        # use this to keep the text_windows
        # this doesn't apply only to windows opened with the open_text_window method, but can be used for any window
        # that has a text widget which needs to be accessed externally
        # the format is {window_id: {text: str, text_widget: Text etc., find_window: str etc.}
        self.text_windows = {}

        # this is used to keep a reference to all the windows that have find functionality
        # the format is {find_window_id: {parent_window_id: str, find_text: str, find_text_widget: Text etc.}}
        self.find_windows = {}

        # find results indexes stored here
        # we're making it a dict so that we can store result indexes for each window individually
        self.find_result_indexes = {}

        # when searching for text, you may want the user to cycle through the results, so this keep track
        # keeps track on which search result is the user currently on (in each transcript window)
        self.find_result_pos = {}

        # to keep track of what is being searched on each window
        self.find_strings = {}

        # this holds a prompt history for the windows that support it
        # the format is {window_id: [prompt1, prompt2, prompt3, etc.]}
        self.window_prompts = {}

        # this holds the index of the current prompt in the prompt history
        self.window_prompts_index = {}

        # this holds all the assistent windows
        self.assistant_windows = {}

        # currently focused window
        self.current_focused_window = None

        # what to call before exiting the app
        self.before_exit = None

        # set some UI styling here
        self.paddings = {'padx': 10, 'pady': 10}
        self.form_paddings = {'padx': 10, 'pady': 5}
        self.button_size = {'width': 150, 'height': 50}
        self.list_paddings = {'padx': 3, 'pady': 3}
        self.label_settings = {'anchor': 'e', 'width': 20}
        self.input_grid_settings = {'sticky': 'w'}
        self.entry_settings = {'width': 30}
        self.entry_settings_half = {'width': 20}
        self.entry_settings_quarter = {'width': 8}

        self.dialog_paddings = {'padx': 0, 'pady': 0}
        self.dialog_entry_settings = {'width': 30}

        # scrollbars
        self.scrollbar_settings = {'width': 10}

        # the font size ratio
        if sys.platform == "darwin":
            font_size_ratio = 1.30
        else:
            font_size_ratio = 0.7

        # we're calculating the size based on the screen size
        screen_width, screen_height = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        font_size_ratio *= (screen_width if screen_width > screen_height else screen_height) / 1920

        # set platform independent transcript font
        self.transcript_font = font.Font()

        # first - find out if there is any "courier" font installed
        # and select one of the versions
        available_fonts = font.families()
        if 'Courier' in available_fonts:
            self.transcript_font.configure(family='Courier')
        elif 'Courier New' in available_fonts:
            self.transcript_font.configure(family='Courier New')
        else:
            logger.debug('No "Courier" font found. Using default fixed font.')
            self.transcript_font = font.nametofont(name='TkFixedFont')

        # get transcript font size
        transcript_font_size = self.stAI.get_app_setting('transcript_font_size', default_if_none=15)

        # set the transcript font size based on the font ratio
        self.transcript_font.configure(size=int(transcript_font_size * font_size_ratio))

        # self.transcript_font.configure(size=16)

        # get console font size
        console_font_size = self.stAI.get_app_setting('console_font_size', default_if_none=13)

        # set the platform independent fixed font (for console)
        self.console_font = font.nametofont(name='TkFixedFont')
        self.console_font.configure(size=int(console_font_size * font_size_ratio))

        # set the default font size
        default_font_size = 13
        default_font_size_after_ratio = int(default_font_size * font_size_ratio)

        self.default_font_size_after_ratio = default_font_size_after_ratio

        # set the platform independent default font
        self.default_font = tk.font.Font(font=font.nametofont(name='TkDefaultFont'))
        self.default_font.configure(size=default_font_size_after_ratio)

        # set the platform independent default link font
        self.default_font_link = tk.font.Font(font=self.default_font)
        self.default_font_link.configure(size=default_font_size_after_ratio, underline=True)

        # set the platform independent default font for headings
        self.default_font_h1 = font.nametofont(name='TkHeadingFont')
        self.default_font_h1.configure(size=int(default_font_size_after_ratio + 3))

        # set the platform independent default font for headings
        self.default_font_h2 = font.nametofont(name='TkHeadingFont')
        self.default_font_h2.configure(size=int(default_font_size_after_ratio + 2))

        # set the platform independent default font for headings
        self.default_font_h3 = font.nametofont(name='TkHeadingFont')
        self.default_font_h3.configure(size=int(default_font_size_after_ratio + 1))

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

        # other colors
        self.theme_colors = {
            'blue': '#1E90FF',
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

        # handling of api token validity
        if not self.stAI.api_token_valid:

            def before_exit(event=None):

                support_page_url = 'https://storytoolkit.ai/support'

                # check if a support page is available
                try:
                    support_page = get(support_page_url, timeout=2)

                    # if the support page is not available
                    if support_page.status_code != 200:
                        return

                except Exception as e:
                    return

                support = messagebox.askyesno("One more thing!",
                                              "StoryToolkitAI is completely free and open source.\n\n "
                                              "If you find it useful, "
                                              "we need your help to speed up development. \n\n"
                                              "Would you like to support the project?")
                if support:
                    webbrowser.open(support_page_url)

            # redefine the on exit function
            self.before_exit = before_exit

        # show the update available message if any
        if self.stAI.update_available and self.stAI.update_available is not None:

            # the url to the releases page
            release_url = 'https://github.com/octimot/StoryToolkitAI/releases/latest'

            goto_projectpage = False

            update_window_id = 'update_available'

            # if there is a new version available
            # the user will see a different update message
            # depending if they're using the standalone version or not
            if self.stAI.standalone:
                warn_message = 'A new standalone version of StoryToolkitAI is available.'

                # add the question to the pop up message box
                messagebox_message = warn_message + ' \n\nDo you want to open the release page?\n'

                changelog_instructions = 'Open the [release page]({}) to download it.\n\n'.format(release_url)

                # prepare some action buttons for the text window
                action_buttons = [{'text': 'Open release page', 'command': lambda: webbrowser.open(release_url)}]

            # for the non-standalone version
            else:
                warn_message = 'A new version of StoryToolkitAI is available.\n\n' \
                               'Use git pull to update.\n '

                changelog_instructions = 'Maybe update now before getting back to work?\n' + \
                                         'Quit the tool and use `git pull` to update.\n\n' \
 \
                    # prepare some action buttons for the text window
                action_buttons = [{'text': 'Quit to update', 'command': lambda: sys.exit()}]

            # read the CHANGELOG.md file from github
            changelog_file = get('https://raw.githubusercontent.com/octimot/StoryToolkitAI/master/CHANGELOG.md')

            # if the request was successful
            if changelog_file.status_code == 200:

                import packaging

                # get the changelog text
                changelog_text = changelog_file.text
                changelog_new_versions = '# A new update is waiting!\n' + \
                                         changelog_instructions

                changelog_new_versions_info = ''

                # split the changelog into versions
                # the changelog is in a markdown format
                changelog_versions = dict()
                for version_full in changelog_text.split('\n## '):

                    # split the version into the version string and the text
                    version_str, text = version_full.split('\n', 1)

                    version_no_and_date = version_str.split('] - ')

                    if len(version_no_and_date) == 2:
                        version_no = version_no_and_date[0].strip('[')
                        version_date = version_no_and_date[1].strip()

                        # add the version to the dictionary
                        changelog_versions[version_no] = {'date': version_date, 'text': text.strip()}

                # get the current installed version
                current_version = self.stAI.version

                # show the changelog for all versions newer than the current installed version
                for version_no, version_info in changelog_versions.items():

                    version_date = version_info['date']
                    text = version_info['text']

                    # remove any double newlines from the text
                    text = text.replace('\n\n', '\n')

                    # if we reached the current version, stop
                    # this doesn't behave well if the version number is x.x.x.x vs x.x.x
                    if packaging.version.parse(version_no) <= packaging.version.parse(current_version):
                        break

                    changelog_new_versions_info += f'\n## {version_no}\n\n{text}\n'

                # add the changelog to the message
                if changelog_new_versions_info != '':
                    changelog_new_versions += '# What\'s new?\n' + changelog_new_versions_info

                # add the skip and later buttons to the action buttons
                action_buttons.append({'text': 'Skip this version',
                                       'command': lambda: self.ignore_update(
                                           version_to_ignore=self.stAI.online_version,
                                           window_id=update_window_id),
                                       'side': tk.RIGHT,
                                       'anchor': 'e'
                                       })
                action_buttons.append({'text': 'Later', 'command': lambda: self.destroy_text_window(update_window_id),
                                       'side': tk.RIGHT, 'anchor': 'e'})

                # open the CHANGELOG.md file from github in a text window
                update_window_id = self.open_text_window(title='New Update',
                                                         window_id=update_window_id,
                                                         initial_text=changelog_new_versions,
                                                         action_buttons=action_buttons)

                # format the text
                self.text_window_format_md(update_window_id)

            # if the changelog file is not available
            # show a simple message popup
            else:

                if self.stAI.standalone:
                    # notify the user and ask whether to open the release website or not
                    goto_projectpage = messagebox.askyesno(title="Update available",
                                                           message=messagebox_message)

                else:
                    messagebox.showinfo(title="Update available",
                                        message=warn_message)

            # notify the user via console
            logger.warning(warn_message)

            # open the browser and go to the release_url
            if goto_projectpage:
                webbrowser.open(release_url)

        # open the transcription log window if something is up in the transcription queue
        if self.toolkit_ops_obj.transcription_queue_current_name:
            self.open_transcription_log_window()

    def only_allow_integers(self, value):
        '''
        Validation function for the entry widget.
        '''
        if value.isdigit():
            return True
        elif value == "":
            return True
        else:
            return False

    def only_allow_floats(self, value):
        '''
        Validation function for the entry widget.
        '''

        if value == "":
            return True

        try:
            float(value)
            return True
        except ValueError:
            return False

    def ignore_update(self, version_to_ignore=None, window_id=None):
        '''
        This function is called when the user clicks the "Skip this version" button in the update window.
        :param version_to_ignore:
        :param window_id:
        :return:
        '''

        # confirm the action
        if not messagebox.askyesno(title="Skip update", message="Are you sure you want to skip this update?\n\n"
                                                                "You will only be notified again when a new update "
                                                                "is available."):
            return False

        # if the window id is specified
        if window_id is not None:
            # destroy the window
            self.destroy_text_window(window_id)

        # if the version to ignore is not specified
        if version_to_ignore is None:
            return False

        # add the version_to_ignore to the config file
        self.stAI.config['ignore_update'] = version_to_ignore

        # save the config file
        self.stAI.save_config()

    class main_window:
        pass

    def on_exit(self):
        '''
        This function is usually called when the user closes the main window or exits the program via the menu.
        -- work in progress --
        :return:
        '''

        # check if there are any items left in the queue
        # if there are, ask the user if they want to quit anyway

        if (self.toolkit_ops_obj.transcription_queue is not None and len(self.toolkit_ops_obj.transcription_queue) > 0) \
                or (self.toolkit_ops_obj.transcription_queue_current_name is not None \
                    and self.toolkit_ops_obj.transcription_queue_current_name != ''):

            quit_anyway = messagebox.askyesno(title="Are you sure?",
                                              message="We're still transcribing. Quit anyway?")

            # if the user doesn't want to quit anyway, return
            if not quit_anyway:
                return

        # if a before_exit function is defined, call it
        if self.before_exit is not None:
            self.before_exit()

        # close the main window
        self.root.destroy()

        # and finally, exit the program
        sys.exit()

    def create_or_open_window(self, parent_element: tk.Toplevel or tk = None, window_id: str = None,
                              title: str = None, resizable: bool = False,
                              close_action=None,
                              open_multiple: bool = False, return_window: bool = False) \
            -> tk.Toplevel or str or bool:
        '''
        This function creates a new window or opens an existing one based on the window_id.
        :param parent_element:
        :param window_id:
        :param title:
        :param resizable:
        :param close_action: The function to call when the window is being closed
        :param open_multiple: Allows to open multiple windows of the same type
                             (but adds the timestamp to the window_id for differentiations)
        :param return_window: If false, it just returns the window_id. If true, it returns the window object.
        :return: The window_id, the window object if return_window is True, or False if the window already exists
        '''

        # if the window is already opened somewhere, do this
        # (but only if open_multiple is False)
        # if this function throws an error make sure that, if the window was previously opened and closed,
        # it the window_id reference was removed from the self.windows dictionary in the destroy/close function!
        if window_id in self.windows and not open_multiple:

            # bring the window to the top
            # self.windows[window_id].attributes('-topmost', 1)
            # self.windows[window_id].attributes('-topmost', 0)
            self.windows[window_id].lift()

            # then focus on it
            self.windows[window_id].focus_set()

            # but return false since we're not creating it
            return False

        else:

            # if the window exists, but we want to have multiple instances of it
            # use the current time as a unique suffix to the window_id
            if window_id in self.windows and open_multiple:
                window_id = window_id + "_" + str(time.time())

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

            # what happens when the user focuses on this window
            self.windows[window_id].bind("<FocusIn>", lambda event: self._focused_window(window_id))

            # return the window_id or the window object
            if return_window:
                return self.windows[window_id]
            else:
                return window_id

    def _focused_window(self, window_id):
        '''
        This function is called when a window is focused
        :param window_id:
        :return:
        '''

        # if the previous focus trigger was on the same window, ignore
        if self.current_focused_window == window_id:
            return

        # change the focused window variable
        self.current_focused_window = window_id

        # logger.debug("Window focused: " + window_id)

    def hide_main_window_frame(self, frame_name):
        '''
        Used to hide main window frames, but only if they're not invisible already
        :param frame_name:
        :return:
        '''

        # only attempt to remove the frame from the main window if it's known to be visible
        if frame_name in self.windows['main'].main_window_visible_frames:
            # first remove it from the view
            self.windows['main'].__dict__[frame_name].pack_forget()

            # then remove if from the visible frames list
            self.windows['main'].main_window_visible_frames.remove(frame_name)

            return True

        return False

    def show_main_window_frame(self, frame_name):
        '''
        Used to show main window frames, but only if they're not visible already
        :param frame_name:
        :return:
        '''

        # only attempt to show the frame from the main window if it's known not to be visible
        if frame_name not in self.windows['main'].main_window_visible_frames:
            # first show it
            self.windows['main'].__dict__[frame_name].pack()

            # then add it to the visible frames list
            self.windows['main'].main_window_visible_frames.append(frame_name)

            return True

        return False

    def update_main_window(self):
        '''
        Updates the main window GUI
        :return:
        '''

        # if resolve isn't connected or if there's a communication error
        if not NLE.is_connected():
            # hide resolve related buttons
            self.hide_main_window_frame('resolve_buttons_frame')

            # update the names of the transcribe buttons
            self.windows['main'].button5.config(text='Transcribe\nAudio')
            self.windows['main'].button6.config(text='Translate\nAudio to English')

            # if resolve is connected and the resolve buttons are not visible
        else:
            # show resolve buttons
            if self.show_main_window_frame('resolve_buttons_frame'):
                # but hide other buttons so we can place them back below the resolve buttons frame
                self.hide_main_window_frame('other_buttons_frame')

            # update the names of the transcribe buttons
            self.windows['main'].button5.config(text='Transcribe\nTimeline')
            self.windows['main'].button6.config(text='Translate\nTimeline to English')

        # now show the other buttons too if they're not visible already
        self.show_main_window_frame('other_buttons_frame')
        self.show_main_window_frame('footer_frame')

        return

    def create_main_window(self):
        '''
        Creates the main GUI window using Tkinter
        :return:
        '''

        # set the main window title
        self.root.title("StoryToolkitAI v{}".format(self.stAI.__version__))

        # temporary width and height for the main window
        self.root.config(width=1, height=1)

        # create a reference main window
        self.windows['main'] = self.root

        # any frames stored here in the future will be considered visible
        self.windows['main'].main_window_visible_frames = []

        # retrieve toolkit_ops object
        toolkit_ops_obj = self.toolkit_ops_obj

        # set the window size
        # self.root.geometry("350x440")

        # create the frame that will hold the resolve buttons
        self.windows['main'].resolve_buttons_frame = tk.Frame(self.root)

        # create the frame that will hold the other buttons
        self.windows['main'].other_buttons_frame = tk.Frame(self.root)

        # add footer frame
        self.windows['main'].footer_frame = tk.Frame(self.root)

        # draw buttons

        # label1 = tk.Label(frame, text="Resolve Operations", anchor='w')
        # label1.grid(row=0, column=1, sticky='w', padx=10, pady=10)

        # resolve buttons frame row 1
        self.windows['main'].button1 = tk.Button(self.windows['main'].resolve_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Copy Timeline\nMarkers to Same Clip",
                                                 command=lambda: self.toolkit_ops_obj.execute_operation(
                                                     'copy_markers_timeline_to_clip', self))
        self.windows['main'].button1.grid(row=1, column=1, **self.paddings)

        self.windows['main'].button2 = tk.Button(self.windows['main'].resolve_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Copy Clip Markers\nto Same Timeline",
                                                 command=lambda: self.toolkit_ops_obj.execute_operation(
                                                     'copy_markers_clip_to_timeline', self))
        self.windows['main'].button2.grid(row=1, column=2, **self.paddings)

        # resolve buttons frame row 2
        self.windows['main'].button3 = tk.Button(self.windows['main'].resolve_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size, text="Render Markers\nto Stills",
                                                 command=lambda: self.toolkit_ops_obj.execute_operation(
                                                     'render_markers_to_stills', self))
        self.windows['main'].button3.grid(row=2, column=1, **self.paddings)

        self.windows['main'].button4 = tk.Button(self.windows['main'].resolve_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size, text="Render Markers\nto Clips",
                                                 command=lambda: self.toolkit_ops_obj.execute_operation(
                                                     'render_markers_to_clips', self))
        self.windows['main'].button4.grid(row=2, column=2, **self.paddings)

        # Other Frame Row 1
        self.windows['main'].button5 = tk.Button(self.windows['main'].other_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size, text="Transcribe\nTimeline",
                                                 command=lambda: self.toolkit_ops_obj.prepare_transcription_file(
                                                     toolkit_UI_obj=self))
        # add the shift+click binding to the button
        # this forces the user to select the files manually
        self.windows['main'].button5.bind('<Shift-Button-1>',
                                          lambda event: toolkit_ops_obj.prepare_transcription_file(
                                              toolkit_UI_obj=self, select_files=True))
        self.windows['main'].button5.grid(row=1, column=1, **self.paddings)

        self.windows['main'].button6 = tk.Button(self.windows['main'].other_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Translate\nTimeline to English",
                                                 command=lambda: self.toolkit_ops_obj.prepare_transcription_file(
                                                     toolkit_UI_obj=self, task='translate'))
        # add the shift+click binding to the button
        # this forces the user to select the files manually
        self.windows['main'].button6.bind('<Shift-Button-1>',
                                          lambda event: toolkit_ops_obj.prepare_transcription_file(
                                              toolkit_UI_obj=self, task='translate', select_files=True))

        self.windows['main'].button6.grid(row=1, column=2, **self.paddings)

        self.windows['main'].button7 = tk.Button(self.windows['main'].other_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Open\nTranscript", command=lambda: self.open_transcript())
        self.windows['main'].button7.grid(row=2, column=1, **self.paddings)

        self.windows['main'].button8 = tk.Button(self.windows['main'].other_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Open\nTranscription Log",
                                                 command=lambda: self.open_transcription_log_window())
        self.windows['main'].button8.grid(row=2, column=2, **self.paddings)

        # THE ADVANCED SEARCH BUTTON
        self.windows['main'].button9 = tk.Button(self.windows['main'].other_buttons_frame,
                                                 **self.blank_img_button_settings,
                                                 **self.button_size,
                                                 text="Advanced\n Search", command=lambda:
            self.open_advanced_search_window())
        # add the shift+click binding to the button
        self.windows['main'].button9.bind('<Shift-Button-1>',
                                          lambda event: self.open_advanced_search_window(select_dir=True))

        self.windows['main'].button9.grid(row=3, column=1, **self.paddings)

        # THE ASSISTANT BUTTON
        self.windows['main'].button10 = tk.Button(self.windows['main'].other_buttons_frame,
                                                  **self.blank_img_button_settings,
                                                  **self.button_size,
                                                  text="Assistant",
                                                  command=lambda: self.open_assistant_window())

        self.windows['main'].button10.grid(row=3, column=2, **self.paddings)

        # THE CONSOLE BUTTON
        # self.windows['main'].button10 = tk.Button(self.windows['main'].other_buttons_frame, **self.blank_img_button_settings,
        #                                        **self.button_size,
        #                                        text="Console", command=lambda:
        #                                                    self.open_text_window(title="Console", initial_text="hello",
        #                                                                          can_find=True,
        #                                                                          user_prompt=True,
        #                                                                          prompt_prefix="> ")
        #                                      )
        #
        # self.windows['main'].button10.grid(row=3, column=2, **self.paddings)

        # Make the window resizable false
        self.root.resizable(False, False)

        # update the window after it's been created
        self.root.after(500, self.update_main_window())

        logger.info("Starting StoryToolkitAI GUI")

        # when the window is focused or clicked on
        self.windows['main'].bind("<FocusIn>", lambda event: self._focused_window('main'))
        self.windows['main'].bind("<Button-1>", lambda event: self._focused_window('main'))
        self.windows['main'].bind("<Button-2>", lambda event: self._focused_window('main'))
        self.windows['main'].bind("<Button-3>", lambda event: self._focused_window('main'))

        # add key bindings to the main window
        # key t for the transcription window
        self.windows['main'].bind("t", lambda event: self.toolkit_ops_obj.prepare_transcription_file(
            toolkit_UI_obj=self))

        # load menubar items
        self.UI_menus.load_menubar()

        # load Tk mainloop
        self.root.mainloop()

        return

    def _text_window_entry(self, window_id, event, **kwargs):
        '''
        This function is called when the user presses any key in the text window text field
        :param window_id:
        :return:
        '''

        # get the current number of lines in the text widget
        lines = self.text_windows[window_id]['text_widget'].index('end-1c')

        # on which line is the cursor?
        cursor_pos = self.text_windows[window_id]['text_widget'].index('insert')

        # up/down for prompt history
        # the prompt history is saved in self.window_prompts[window_id]
        # when searching through the prompt history, we use self.window_prompts_index[window_id]
        # to keep track which prompt we are on
        if event.keysym in ['Up', 'Down']:

            # first move the cursor to the end of the last line
            self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

            # also scroll to the end of the last line
            self.text_windows[window_id]['text_widget'].see('end-1c')

            # if the prompt history is empty, do nothing
            if window_id not in self.window_prompts or len(self.window_prompts[window_id]) == 0:
                return 'break'

            if window_id not in self.window_prompts_index:
                self.window_prompts_index[window_id] = -1

            # if the prompt history is not empty
            else:
                # if the key is up
                if event.keysym == 'Down':
                    # if the prompt history index is not at the end of the list
                    if self.window_prompts_index[window_id] < len(self.window_prompts[window_id]) - 1:
                        # increase the prompt history index
                        self.window_prompts_index[window_id] += 1
                    else:
                        # if the prompt history index is at the end of the list
                        # set the prompt history index to -1
                        # this means that the prompt history index is not on any prompt
                        self.window_prompts_index[window_id] = -1

                # if the key is down
                elif event.keysym == 'Up':
                    # if the prompt history index is not at the beginning of the list
                    if self.window_prompts_index[window_id] == -1:
                        # set the prompt history index to the last index in the list
                        self.window_prompts_index[window_id] = len(self.window_prompts[window_id]) - 1

                    else:
                        # decrease the prompt history index
                        self.window_prompts_index[window_id] -= 1

                # if the prompt history index is -1
                if self.window_prompts_index[window_id] == -1:
                    # set the prompt to an empty string
                    prompt = ''

                # if the prompt history index is not -1
                else:
                    # get the prompt from the prompt history
                    prompt = self.window_prompts[window_id][self.window_prompts_index[window_id]]

                # first, clear the last line
                self.text_windows[window_id]['text_widget'].delete('end-1c linestart', 'end-1c lineend')

                # set the prompt in the text widget
                # but also add the prompt prefix if there is one
                self.text_windows[window_id]['text_widget'] \
                    .insert('end-1c', self.text_windows[window_id]['prompt_prefix'] + prompt)

            return 'break'

        # if the cursor is not past the last line, only allow arrow keys
        if int(cursor_pos.split('.')[0]) < int(lines.split('.')[0]):

            # do not allow backspace
            # but move the cursor to the end of the last line
            if event.keysym == 'BackSpace':
                # first move the cursor to the end of the last line
                self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                self.text_windows[window_id]['text_widget'].see('end-1c')

                return 'break'

            # if the key is an left-right arrow key, return 'normal'
            elif event.keysym in ['Left', 'Right']:
                return 'normal'

            # if the key is not an arrow key, move the cursor to the end of the last line
            else:
                # first move the cursor to the end of the last line
                self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                self.text_windows[window_id]['text_widget'].see('end-1c')

                # then return normal so that the key is processed as it should be
                return 'normal'

        else:

            # if the cursor is not past the prefix, move it to the end of the prefix
            if int(cursor_pos.split('.')[1]) < len(self.text_windows[window_id]['prompt_prefix']):
                # first move the cursor to the end of the last line
                self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                self.text_windows[window_id]['text_widget'].see('end-1c')

                return 'break'

            # if the key is Return, get the text and call the command
            if event.keysym == 'Return':

                # get the command entered by the user
                prompt = self.text_windows[window_id]['text_widget'].get('end-1c linestart', 'end-1c lineend')

                # remove the command prefix from the beginning of the command if it was given
                if kwargs.get('prompt_prefix', ''):
                    prompt = prompt.replace(kwargs.get('prompt_prefix', ''), '', 1)

                # add two new lines
                self.text_windows[window_id]['text_widget'].insert('end', '\n\n')

                # also pass the prompt prefix if it was given
                self._text_window_prompts(prompt=prompt, window_id=window_id, **kwargs)

                # scroll to the end of the last line
                # but only if the window still exists
                # - this is disabled since it should be handled within _text_window_prompts() (i.e. by each command)
                # if window_id in self.text_windows:
                #    self.text_windows[window_id]['text_widget'].see('end-1c')

                return 'break'

            # do not allow backspace past the first character + length of the prompt prefix of the last line
            elif event.keysym == 'BackSpace':

                last_line = (self.text_windows[window_id]['text_widget'].index('end-1c linestart')).split('.')[0]

                # get the length of prompt_prefix
                prompt_prefix_length = len(kwargs.get('prompt_prefix', ''))

                if self.text_windows[window_id]['text_widget'].index('insert') \
                        == str(last_line) + '.' + str(prompt_prefix_length):
                    return 'break'

        return

    def _text_window_prompts(self, prompt, window_id=None, **kwargs):
        '''
        This function calls prompts from the text window.
        :return:
        '''

        response = None

        # first, add the prompt to the prompt history
        if window_id not in self.window_prompts:
            self.window_prompts[window_id] = [prompt]
        else:
            self.window_prompts[window_id].append(prompt)

        # reset the prompt history index
        self.window_prompts_index[window_id] = -1

        if kwargs.get('prompt_callback', ''):
            response = kwargs.get('prompt_callback', '')(prompt, **kwargs.get('prompt_callback_kwargs', {}))

        # if no command execution function is given, resort to the default commands
        else:

            if prompt == 'exit' or prompt == 'quit' or prompt == 'close':
                self.destroy_text_window(window_id=window_id)

            else:
                response = 'Ignoring "{}". Command unknown.'.format(prompt)
                logger.debug(response)

        # output the reply to the text window, if a window_id is given
        if window_id and response:
            self._text_window_update(window_id=window_id, text=response, prompt_prefix=kwargs.get('prompt_prefix', ''))

    def _text_window_update(self, window_id, text, **kwargs):
        '''
        This function updates the text in the text window, but keeps the command line at the bottom if it exists
        :param window_id:
        :param text:
        :param args:
        :return:
        '''

        prompt_prefix = self.text_windows[window_id]['prompt_prefix'] \
            if 'prompt_prefix' in self.text_windows[window_id] else None

        user_prompt = self.text_windows[window_id]['user_prompt'] \
            if 'user_prompt' in self.text_windows[window_id] else None

        # if user input is enabled and user_input prefix exists, move the cursor to the beginning of the last line
        linestart = ''
        if user_prompt and prompt_prefix:
            self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c linestart')

            # also use the linestart variable for the color change below
            linestart = ' linestart'

        # first get the current insert position
        insert_pos = self.text_windows[window_id]['text_widget'].index('insert')

        self.text_windows[window_id]['text_widget'].insert('insert', text + '\n\n')

        # now change the color of the last entry to supernormal (almost white)
        self.text_windows[window_id]['text_widget'].tag_add('reply', insert_pos, 'end-1c' + linestart)
        self.text_windows[window_id]['text_widget'].tag_config('reply',
                                                               foreground=self.resolve_theme_colors['supernormal'])

        # if user input is enabled and a prefix is given, make sure we have it at the beginning of the last line
        if user_prompt and prompt_prefix:

            # only add it if it is not already there
            if not self.text_windows[window_id]['text_widget'].get('end-1c linestart', 'end-1c lineend') \
                    .startswith(prompt_prefix):
                self.text_windows[window_id]['text_widget'].insert('end-1c linestart', prompt_prefix)

        # and move the insert position right at the end
        self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

        # also scroll to the end of the last line (or to whatever scroll_to was sent)
        self.text_windows[window_id]['text_widget'].see(kwargs.get('scroll_to', 'end-1c'))

    def open_text_window(self, window_id=None, title: str = 'Console', initial_text: str = None,
                         can_find: bool = False, user_prompt: bool = False, prompt_prefix: str = None,
                         prompt_callback: callable = None, prompt_callback_kwargs: dict = None,
                         action_buttons: list = None, **kwargs):
        '''
        This window is to display any kind of text in a scrollable window.
        But is also capable of receiving commands from the user (optional)

        This can be used for displaying the license info, or the readme, reading text files,
        welcome messages, the actual stdout etc.

        It will also contain a text input field for the user to enter prompts (optional)
        Plus, the option to have a child find window (optional)

        :param window_id: The id of the window. If not given, it will be generated from the title
        :param title: The title of the window
        :param initial_text: The initial text to display in the window
        :param can_find: If True, a find window will be available on CTRL+F
        :param user_prompt: If True, the user will be able to enter prompts in the window
        :param prompt_prefix: What appears before the user prompt, so the user knows it is a prompt
        :param prompt_callback: A function to call when the user enters a prompt
        :param prompt_callback_kwargs: A dict of kwargs to pass to the prompt_callback function. We will always pass the
                                        window_id, the prompt_prefix and the prompt as kwargs
        :param action_buttons: A list of action buttons to add to the window. Each button is a dict with the following
                                keys: text, command
        :return:
        '''

        # if no window id is given, use the title without spaces plus the time hash
        if not window_id:
            window_id = title.replace(' ', '_').replace('.', '') + str(time.time()).replace('.', '')

        close_action = kwargs.get('close_action', lambda window_id=window_id: self.destroy_text_window(window_id))

        # open the text window
        if self.create_or_open_window(parent_element=self.root, window_id=window_id, title=title, resizable=True,
                                      close_action=close_action,
                                      open_multiple=kwargs.get('open_multiple', True)
                                      ):

            # create menu bar
            # window_menu = tk.Menu(self.windows[window_id])
            # self.windows[window_id].config(menu=window_menu)

            # create the file menu
            # file_menu = tk.Menu(window_menu, tearoff=0)
            # window_menu.add_cascade(label='File ', menu=file_menu)

            # add the save as option
            # file_menu.add_command(label='Save as...', command=lambda: self.save_text_window_as(window_id=window_id))

            # create an entry in the text_windows dict
            self.text_windows[window_id] = {'text': initial_text}

            # add the user prompt prefix to the text windows dict if it was given
            if user_prompt:
                self.text_windows[window_id]['user_prompt'] = user_prompt
                self.text_windows[window_id]['prompt_prefix'] = prompt_prefix

            # add the CTRL+F behavior to the text window
            if can_find:
                # if the user presses CTRL/CMD+F, open the find window
                self.windows[window_id].bind('<' + self.ctrl_cmd_bind + '-f>',
                                             lambda event:
                                             self.open_find_replace_window(
                                                 parent_window_id=window_id,
                                                 title="Find in {}".format(title)
                                             )
                                             )

            # THE MAIN TEXT ELEMENT
            # create a frame for the text element
            text_form_frame = tk.Frame(self.windows[window_id], name='text_form_frame')
            text_form_frame.pack(expand=True, fill='both')

            # create the text widget
            # set up the text element where we'll add the actual transcript
            text = Text(text_form_frame, name='window_text',
                        font=(self.console_font),
                        width=kwargs.get('window_width', 45),
                        height=kwargs.get('window_height', 30),
                        padx=5, pady=5, wrap=tk.WORD,
                        background=self.resolve_theme_colors['black'],
                        foreground=self.resolve_theme_colors['normal'])

            # add a scrollbar to the text element
            scrollbar = Scrollbar(text_form_frame, orient="vertical", **self.scrollbar_settings)
            scrollbar.config(command=text.yview)
            scrollbar.pack(side=tk.RIGHT, fill='y', pady=5)

            # configure the text element to use the scrollbar
            text.config(yscrollcommand=scrollbar.set)

            # add the initial text to the text element
            if initial_text:
                text.insert(tk.END, initial_text + '\n\n')

            # change the color of text to supernormal (almost white)
            text.tag_add('reply', '1.0', 'end-1c')
            text.tag_config('reply', foreground=self.resolve_theme_colors['supernormal'])

            # set the top, in-between and bottom text spacing
            text.config(spacing1=0, spacing2=0.2, spacing3=5)

            # then show the text element
            text.pack(anchor='w', expand=True, fill='both')

            # if the user can enter text, enable the text field and process any input
            if user_prompt:

                # if a command prefix is given, add it to the text element
                if prompt_prefix:
                    text.insert(tk.END, prompt_prefix)

                # any keypress in the text element will call the _text_window_entry function
                text.bind('<KeyPress>',
                          lambda event:
                          self._text_window_entry(window_id=window_id, event=event,
                                                  prompt_prefix=prompt_prefix,
                                                  prompt_callback=prompt_callback,
                                                  prompt_callback_kwargs=prompt_callback_kwargs,
                                                  **kwargs))

                # focus on the text element
                text.focus_set()

            # otherwise, disable the text field
            else:
                text.config(state=tk.DISABLED)

            # if action buttons are given, add them to the window
            if action_buttons:

                # create a frame for the action buttons
                action_buttons_frame = tk.Frame(self.windows[window_id], name='action_buttons_frame')
                action_buttons_frame.pack(side=tk.BOTTOM, fill='x', pady=5)

                # add the action buttons to the frame
                for button in action_buttons:
                    # create the button
                    action_button = tk.Button(action_buttons_frame, text=button['text'],
                                              command=button['command'])

                    # add the button to the frame
                    action_button.pack(side=button['side'] if 'side' in button else tk.LEFT,
                                       anchor=button['anchor'] if 'anchor' in button else tk.W,
                                       **self.paddings)

            # add the text widget to the text_windows dict
            self.text_windows[window_id]['text_widget'] = text

            # add the window to the text_windows dict
            self.text_windows[window_id]['window'] = self.windows[window_id]

        return window_id

    def text_window_format_md(self, window_id: str, text_widget: Text = None):
        '''
        This function will format markdown text in a text window.
        It will add url links and do header formatting
        :param window_id:
        :param text_widget:
        :return:
        '''

        # if no text widget is given, get it from the text_windows dict
        if not text_widget:
            text_widget = self.text_windows[window_id]['text_widget']

        # get the text from the text widget
        text = text_widget.get('1.0', tk.END)

        # change the font to default_font
        text_widget.config(font=(self.default_font))

        # if the text is empty, return
        if not text:
            return

        # get the initial text widget state
        initial_state = text_widget.cget('state')

        # make widget writeable
        text_widget.config(state=tk.NORMAL)

        # take each line of text and format it
        lines = text.split('\n')

        # clear the text widget
        text_widget.delete('1.0', tk.END)

        for line in lines:

            md = False

            # FORMAT HEADERS
            if line.strip().startswith('#'):
                # get the number of # signs
                num_hashes = len(line.split(' ')[0])

                # header type
                header_type = 'h{}'.format(num_hashes)

                # get the header text
                header_text = line.split('# ')[1]

                # get current insert position
                start_index = text_widget.index(tk.INSERT)

                # replace the line with the header text
                text_widget.insert(tk.INSERT, header_text)

                # add the header tag
                text_widget.tag_add(header_type, start_index, tk.INSERT)

                md = True

            # FORMAT URLS
            if re.search(r'\[.*\]\(.*\)', line):

                # get the url and it's url text, the format is [url text](url)
                # but remember that they are always together but they might be between other text
                # also there might be more than one url in the line
                # so we need to find all the urls and their text
                urls = re.findall(r'\[.*\]\(.*\)', line)

                n = 0
                for url_md in urls:
                    # use regex to get the url text
                    url_text = re.findall(r'\[(.*)\]', url_md)[0]
                    url = re.findall(r'\((.*)\)', url_md)[0]

                    # get the text before the url
                    text_before_url = line.split(url_md)[0]

                    # insert the text before the url
                    text_widget.insert(tk.INSERT, text_before_url)

                    # remove the text before the url from the line
                    line = line.replace(text_before_url, '')

                    # remove the url from the line
                    line = line.replace(url_md, '')

                    # get current insert position for the url_text
                    start_index = text_widget.index(tk.INSERT)

                    text_widget.insert(tk.INSERT, url_text)

                    # add the url tags
                    text_widget.tag_add('url-color', start_index, tk.INSERT)
                    text_widget.tag_add('url-' + str(start_index), start_index, tk.INSERT)

                    # on click, open the url in the default browser
                    text_widget.tag_bind('url-' + str(start_index), '<Button-1>',
                                         lambda event, url=url: webbrowser.open(url))

                # finally, insert the rest of the line
                text_widget.insert(tk.INSERT, line)

                md = True

            if not md:
                text_widget.insert(tk.INSERT, line)

            # add a new line
            text_widget.insert(tk.INSERT, '\n')

        # turn the text widget back to its initial state
        text_widget.config(state=initial_state)

        # set the color of the text to supernormal (almost white)
        text_widget.config(foreground=self.resolve_theme_colors['supernormal'])

        # set the headers font
        text_widget.tag_config('h1', font=(self.default_font_h1, int(self.default_font_size_after_ratio * 1.5)),
                               foreground=self.resolve_theme_colors['white'])
        text_widget.tag_config('h2', font=(self.default_font_h2, int(self.default_font_size_after_ratio * 1.25)),
                               foreground=self.resolve_theme_colors['white'])
        text_widget.tag_config('h3', font=(self.default_font_h3, int(self.default_font_size_after_ratio * 1.1)),
                               foreground=self.resolve_theme_colors['white'])

        # add a bit of space between the headers and the text
        text_widget.tag_config('h1', spacing1=10)
        text_widget.tag_config('h2', spacing1=10)
        text_widget.tag_config('h3', spacing1=10)

        # change the color of the version number
        text_widget.tag_config('version', foreground=self.resolve_theme_colors['white'])

        # change the font of the code blocks into console font
        text_widget.tag_config('code3', font=(self.console_font), foreground=self.resolve_theme_colors['normal'])

        # change the color of the url
        text_widget.tag_config('url-color', foreground=self.theme_colors['blue'])

        text_widget.tag_bind('url-color', '<Enter>', lambda event: text_widget.config(cursor='hand2'))
        text_widget.tag_bind('url-color', '<Leave>', lambda event: text_widget.config(cursor=''))

    def open_find_replace_window(self, window_id=None, title: str = 'Find and Replace',
                                 parent_window_id: str = None, text_widget=None,
                                 replace_field: bool = False, find_text: str = None, replace_text: str = None,
                                 post_replace_action: str = None, post_replace_action_args: list = None
                                 ):
        '''
        This window is used to find (and replace) text in a text widget of another window
        '''

        if not parent_window_id and not text_widget:
            logger.error('Aborting. Unable to open find and replace window without a parent window.')
            return False

        # always use the parent in the window id if no window id is given
        if not window_id:
            window_id = 'find_' + parent_window_id.replace(' ', '_').replace('.', '')

        # open the find and replace window
        if self.create_or_open_window(parent_element=self.root, window_id=window_id, title=title,
                                      close_action=lambda window_id=window_id:
                                      self.destroy_find_replace_window(window_id, parent_window_id=parent_window_id)):

            # add the window to the find_windows dict, and also include the parent window id
            self.find_windows[window_id] = {'parent_window_id': parent_window_id}

            # add the window to the text_windows dict, in case we need to reference it from the parent window
            self.text_windows[parent_window_id]['find_window_id'] = window_id

            # create a frame for the find input
            find_frame = tk.Frame(self.windows[window_id], name='find_frame')
            find_frame.pack(pady=5, padx=5, expand=True, fill='both')

            # create a label for the find input
            find_label = tk.Label(find_frame, text='Find:', name='find_label')
            find_label.pack(side=tk.LEFT, padx=5)

            # create the find input
            find_str = tk.StringVar()
            find_input = tk.Entry(find_frame, textvariable=find_str, name='find_input')
            find_input.pack(side=tk.LEFT, padx=5, expand=True, fill='x')

            parent_text_widget = self.text_windows[parent_window_id]['text_widget']

            # if the user presses a key in the find input,
            # call the _find_text_in_widget function
            find_str.trace("w", lambda name, index, mode, find_str=find_str, parent_window_id=parent_window_id:
            self._find_text_in_widget(find_str, parent_window_id, text_widget=parent_text_widget))

            # return key cycles through the results
            find_input.bind('<Return>',
                            lambda e, parent_text_widget=parent_text_widget, parent_window_id=parent_window_id:
                            self._cycle_through_find_results(text_widget=parent_text_widget,
                                                             window_id=parent_window_id))

            # escape key closes the window
            find_input.bind('<Escape>', lambda e, window_id=window_id: self.destroy_find_replace_window(window_id))

            # focus on the find input
            find_input.focus_set()

            # if a find text is given, add it to the find input
            if find_text:
                find_input.insert(0, find_text)

            # todo: add replace field when needed
            if replace_field:
                # create a frame for the replace input
                replace_frame = tk.Frame(self.windows[window_id], name='replace_frame')
                replace_frame.pack(expand=True, fill='both')

                # create a label for the replace input
                replace_label = tk.Label(replace_frame, text='Replace:', name='replace_label')
                replace_label.pack(side=tk.LEFT, padx=5)

                # create the replace input
                replace_input = tk.Entry(replace_frame, name='replace_input')
                replace_input.pack(side=tk.LEFT, padx=5, expand=True, fill='x')

                # if a replace text is given, add it to the replace input
                if replace_text:
                    replace_input.insert(0, replace_text)

                replace_button = tk.Button(replace_frame, text='Replace', name='replace_button',
                                           command=lambda: self._replace_text_in_widget(window_id=window_id,
                                                                                        text_widget=text_widget,
                                                                                        post_replace_action=post_replace_action,
                                                                                        post_replace_action_args=post_replace_action_args))
                replace_button.pack(side=tk.LEFT, padx=5)

            # create a footer frame that holds stuff on the bottom of the window
            footer_frame = tk.Frame(self.windows[window_id], name='footer_frame')
            footer_frame.pack(expand=True, fill='both')

            # add a status label to the footer frame
            status_label = Label(footer_frame, name='status_label',
                                 text="", anchor='w', foreground=self.resolve_theme_colors['normal'])
            status_label.pack(side=tk.LEFT, **self.paddings)

            # add the status label to the find_windows dict so we can update it later
            self.find_windows[window_id]['status_label'] = status_label

    def _find_text_in_widget(self, search_str: str = None, window_id: str = None, text_widget: tk.Text = None):
        '''
        This function finds and highlights found matches in a text widget

        :param search_str: the string to search for
        :param window_id: the id of the window that contains the text widget
        :param text_widget: the text widget to search in

        :return:
        '''

        if search_str is None or text_widget is None or window_id is None:
            logger.error('Aborting. Unable to find text in widget without a search string, text widget, and window id.')
            return False

        # remove tag 'found' from index 1 to END
        text_widget.tag_remove('found', '1.0', END)

        # remove tag 'current_result_tag' from index 1 to END
        text_widget.tag_remove('current_result_tag', '1.0', END)

        # reset the search result indexes and the result position
        self.find_result_indexes[window_id] = []
        self.find_result_pos[window_id] = 0

        # get the search string as the user is typing
        search_str = self.find_strings[window_id] = search_str.get()

        if search_str:
            idx = '1.0'

            self.find_strings[window_id] = search_str

            # do not search if the search string shorter than 3 characters
            if len(search_str) > 2:

                while 1:

                    # searches for desired string from index 1
                    idx = text_widget.search(search_str, idx, nocase=True, stopindex=END)

                    # stop the loop when we run out of results (indexes)
                    if not idx:
                        break

                    # store each index
                    self.find_result_indexes[window_id].append(idx)

                    # last index sum of current index and
                    # length of text
                    lastidx = '%s+%dc' % (idx, len(search_str))

                    # add the found tag at idx
                    text_widget.tag_add('found', idx, lastidx)
                    idx = lastidx

                #  take the viewer to the first occurrence
                if self.find_result_indexes[window_id] and len(self.find_result_indexes[window_id]) > 0 \
                        and self.find_result_indexes[window_id][0] != '':
                    text_widget.see(self.find_result_indexes[window_id][0])

                    # and visually tag the results
                    self._tag_find_results(text_widget, self.find_result_indexes[window_id][0], window_id)

                # mark located string with red
                text_widget.tag_config('found', foreground=self.resolve_theme_colors['red'])

                # update the status label in the find window
                if 'find_window_id' in self.text_windows[window_id]:
                    find_window_id = self.text_windows[window_id]['find_window_id']
                    self.find_windows[find_window_id]['status_label'] \
                        .config(text=f'{len(self.find_result_indexes[window_id])} results found')

            # update the status label in the find window
            elif 'find_window_id' in self.text_windows[window_id]:
                find_window_id = self.text_windows[window_id]['find_window_id']
                self.find_windows[find_window_id]['status_label'] \
                    .config(text='')

    def _tag_find_results(self, text_widget: tk.Text = None, text_index: str = None, window_id: str = None):
        '''
        Another handy function that tags the search results directly on the transcript inside the transcript window
        This is also used to show on which of the search results is the user right now according to search_result_pos
        :param text_element:
        :param text_index:
        :param window_id:
        :return:
        '''
        if text_widget is None:
            return False

        # remove previous position tags
        text_widget.tag_delete('find_result_tag')

        if not text_index or text_index == '' or text_index is None or window_id is None:
            return False

        # add tag to show the user on which result position we are now
        # the tag starts at the text_index and ends according to the length of the search string
        text_widget.tag_add('find_result_tag', text_index, text_index + '+'
                            + str(len(self.find_strings[window_id])) + 'c')

        # the result tag has a white background and a red foreground
        text_widget.tag_config('find_result_tag', background=self.resolve_theme_colors['white'],
                               foreground=self.resolve_theme_colors['red'])

    def _cycle_through_find_results(self, text_widget: tk.Text = None, window_id: str = None):

        if text_widget is not None or window_id is not None \
                or self.find_result_indexes[window_id] or self.find_result_indexes[window_id][0] != '':

            # if we have no results, return
            if window_id not in self.find_result_indexes \
                    or not self.find_result_indexes[window_id]:
                return False

            # get the current search result position
            current_pos = self.find_result_pos[window_id]

            # as long as we're not going over the number of results
            if current_pos < len(self.find_result_indexes[window_id]) - 1:

                # add 1 to the current result position
                current_pos = self.find_result_pos[window_id] = current_pos + 1

                # this is the index of the current result position
                text_index = self.find_result_indexes[window_id][current_pos]

                # go to the next search result
                text_widget.see(text_index)

            # otherwise go back to start
            else:
                current_pos = self.find_result_pos[window_id] = 0

                # this is the index of the current result position
                text_index = self.find_result_indexes[window_id][current_pos]

                # go to the next search result
                text_widget.see(self.find_result_indexes[window_id][current_pos])

            # visually tag the results
            self._tag_find_results(text_widget, text_index, window_id)

    def open_text_file(self, file_path: str = None, window_id: str = None, tag_text=None, **kwargs):
        '''
        This opens a text file in a new (or existing) text window
        :param file_path:
        :param window_id:
        :return:
        '''

        # first check if the file exists
        if file_path is None or not os.path.isfile(file_path):
            logger.error('Aborting. Unable to open text file. File path is invalid.')
            return False

        # now load the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f'Unable to open text file. Error: {e}')
            return False

        # now open the text window
        self.open_text_window(initial_text=file_content, window_id=window_id, can_find=True, **kwargs)

        # if we have a tag_text, tag the text in the window
        if tag_text is not None and window_id in self.text_windows:

            # get the text widget
            text_widget = self.text_windows[window_id]['text_widget']

            # remove existing tags
            text_widget.tag_delete('find_result_tag')

            tag_index = text_widget.search(tag_text, 1.0, nocase=True, stopindex=END)

            # if we have a tag_index, tag the text
            if tag_index != -1:
                # tag the text
                text_widget.tag_add('find_result_tag', f'{tag_index}', f'{tag_index} + {len(tag_text)}c')

                # configure the tag
                text_widget.tag_config('find_result_tag', foreground=self.resolve_theme_colors['red'])

                # scroll to the tag
                text_widget.see(f'{tag_index}')

    class AskDialog(tk.Toplevel):
        '''
        This is a simple dialogue window that asks the user for input before continuing with the task
        But it also halts the execution of the main window until the user closes the dialogue window
        When the user closes the dialogue window, it will return the user input to the main window
        '''

        def __init__(self, parent, title, input_widgets, **kwargs):
            tk.Toplevel.__init__(self, parent)

            self.parent = parent
            self.title(title)

            # the transient function is used to make the window transient to the parent window
            # which means that the window will appear on top of the parent window
            # If the parent is not viewable, don't make the child transient, or else it
            # would be opened withdrawn
            if parent is not None and parent.winfo_viewable():
                self.transient(parent)

            # this is the dictionary that will hold the user input
            self.return_value = {}
            self.cancel_return = None

            # add the widgets
            self._add_widgets(input_widgets, **kwargs)

            # no resizing after this
            self.resizable(False, False)

            # do not allow clicking on other windows, including the parent window
            self.grab_set()

            # center the window
            self.center_window()

            # if the user tries to defocus out of the window, do not allow it
            # self.bind("<FocusOut>", lambda e: self.focus_set())

            self.protocol("WM_DELETE_WINDOW", self.cancel)

            # wait for the user to close the window
            self.wait_window(self)

        def _add_widgets(self, input_widgets, **kwargs):
            '''
            This adds the widgets to the window, depending what was passed to the class.
            We work with pairs of label+entry widgets, each having a name which we will use in the return dictionary.
            :param kwargs:
            :return:
            '''

            have_input_widgets = False
            row = 0

            # create a frame for the input widgets
            input_frame = tk.Frame(self)

            # take all the entry widgets and add them to the window
            for widget in input_widgets:

                # get the widget name
                widget_name = widget['name']

                # get the widget label
                widget_label = widget['label']

                # get the widget default value
                widget_default_value = widget['default_value']

                # add the label
                label = tk.Label(input_frame, text=widget_label)

                input_widget = None
                input_value = None

                row = row + 1

                # add the input widget, depending on the type
                # entry widget
                if widget['type'] == 'entry':
                    input_value = StringVar(input_frame, widget_default_value)
                    input_widget = tk.Entry(input_frame, textvariable=input_value)

                # selection widget
                elif widget['type'] == 'option_menu' and 'options' in widget:
                    input_value = StringVar(input_frame, widget_default_value)
                    input_widget = tk.OptionMenu(input_frame, input_value, *widget['options'])
                    input_widget.config(takefocus=True)

                # checkbox widget
                elif widget['type'] == 'checkbutton':
                    input_value = BooleanVar(input_frame, widget_default_value)
                    input_widget = tk.Checkbutton(input_frame, variable=input_value)

                # text widget
                elif widget['type'] == 'text':
                    input_value = StringVar(input_frame, widget_default_value)
                    input_widget = tk.Text(input_frame, height=5, width=30)
                    input_widget.insert(1.0, widget_default_value)

                # listbox widget
                elif widget['type'] == 'listbox':
                    input_value = StringVar(input_frame, widget_default_value)
                    input_widget = tk.Listbox(input_frame, height=5, width=30,
                                              selectmode=widget['selectmode'] if 'selectmode' in widget else 'single')
                    input_widget.insert(1.0, widget_default_value)

                # spinbox widget
                elif widget['type'] == 'spinbox':
                    input_value = IntVar(input_frame, widget_default_value)
                    input_widget = tk.Spinbox(input_frame, from_=widget['from'], to=widget['to'],
                                              textvariable=input_value)

                # if we don't have a valid widget, skip
                if input_widget is None:
                    continue

                # if we reached this point, we have a valid widget
                have_input_widgets = True

                # add the widget to the window
                label.grid(row=row, column=0, sticky='e', padx=5, pady=5)
                input_widget.grid(row=row, column=1, sticky='w', padx=5, pady=5)

                # add the widget to the user_input dictionary
                self.return_value[widget_name] = input_value

            # if we have no input widgets, return
            if not have_input_widgets:
                logger.error('No input widgets were added to the Ask Dialogue window. Aborting.')
                return None

            # pack the input frame
            input_frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

            buttons_frame = tk.Frame(self)

            # add the OK button
            w = tk.Button(buttons_frame, text="OK", width=10, command=self.ok, takefocus=True)
            w.pack(side=LEFT, padx=5, pady=5)
            self.bind("<Return>", self.ok)

            # if we have a cancel_action, add the Cancel button
            if 'cancel_return' in kwargs:
                w = tk.Button(buttons_frame, text="Cancel", width=10, command=self.cancel, takefocus=True)
                w.pack(side=LEFT, padx=5, pady=5)

                # add the cancel action
                self.cancel_return = kwargs['cancel_return']

                # enable the escape key to cancel the window
                self.bind("<Escape>", self.cancel)

            # pack the buttons frame
            buttons_frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        def center_window(self):

            # get the window size
            window_width = self.winfo_reqwidth()
            window_height = self.winfo_reqheight()

            # get the screen size
            screen_width = self.parent.winfo_screenwidth()
            screen_height = self.parent.winfo_screenheight()

            # calculate the position of the window
            x = (screen_width / 2) - (window_width / 2)
            y = (screen_height / 2) - (window_height / 2)

            # set the position of the window
            self.geometry('+%d+%d' % (x, y))

        def ok(self, event=None):
            '''
            This is the action that happens when the user clicks the OK button
            :return:
            '''

            # take the user input and return it
            self.return_value = {k: v.get() for k, v in self.return_value.items()}

            # destroy the window
            self.destroy()

        def cancel(self, event=None):
            '''
            This is the action that happens when the user clicks the Cancel button
            :return:
            '''

            self.return_value = None

            # execute the cancel action if it's callable
            if self.cancel_return is not None and callable(self.cancel_return):
                self.cancel_return()

            # if it's not callable, just return the cancel_return value
            elif self.cancel_return is not None:
                self.return_value = self.cancel_return

            # if it's None, return None
            else:
                self.return_value = None

            # destroy the window
            self.destroy()

        def value(self):
            return self.return_value

    def open_transcription_settings_window(self, title="Transcription Settings",
                                           audio_file_path=None, name=None, task=None, unique_id=None,
                                           transcription_file_path=False, time_intervals=None,
                                           excluded_time_intervals=None, **kwargs):

        if self.toolkit_ops_obj is None or audio_file_path is None or unique_id is None:
            logger.error('Aborting. Unable to open transcription settings window.')
            return False

        # assign a unique_id for this window depending on the queue unique_id
        ts_window_id = 'ts-' + unique_id

        # what happens when the window is closed
        close_action = lambda ts_window_id=ts_window_id, unique_id=unique_id: \
            self.destroy_transcription_settings_window(ts_window_id, unique_id)

        # create a window for the transcription settings if one doesn't already exist
        if self.create_or_open_window(parent_element=self.root, window_id=ts_window_id, title=title,
                                      resizable=True, close_action=close_action):

            self.toolkit_ops_obj.update_transcription_log(unique_id=unique_id, **{'status': 'waiting user'})

            # place the window on top for a moment so that the user sees that he has to interact
            self.windows[ts_window_id].wm_attributes('-topmost', True)
            self.windows[ts_window_id].wm_attributes('-topmost', False)
            self.windows[ts_window_id].lift()

            ts_form_frame = tk.Frame(self.windows[ts_window_id])
            ts_form_frame.pack()

            # escape key closes the window
            self.windows[ts_window_id].bind('<Escape>', lambda event: close_action())

            # File items start here

            # TRANSCRIPTION FILE PATH (hidden) - for re-transcriptions only
            if transcription_file_path:
                transcription_file_path_var = StringVar(ts_form_frame, str(transcription_file_path))
            else:
                transcription_file_path_var = StringVar(ts_form_frame, '')

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
            available_languages = self.toolkit_ops_obj.get_whisper_available_languages()

            default_language = self.stAI.get_app_setting('transcription_default_language', default_if_none='')

            language_var = StringVar(ts_form_frame, default_language)
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
            model_input = OptionMenu(ts_form_frame, model_var, *whisper_available_models())
            model_input.grid(row=5, column=2, **self.input_grid_settings, **self.form_paddings)

            # DEVICE DROPDOWN
            Label(ts_form_frame, text="Device", **self.label_settings).grid(row=6, column=1,
                                                                            **self.input_grid_settings,
                                                                            **self.form_paddings)

            available_devices = self.toolkit_ops_obj.get_torch_available_devices()

            # the default selected value will be the whisper_device app setting
            device_selected = self.stAI.get_app_setting('whisper_device', default_if_none='auto')
            device_var = StringVar(ts_form_frame, value=device_selected)

            device_input = OptionMenu(ts_form_frame, device_var, *available_devices)
            device_input.grid(row=6, column=2, **self.input_grid_settings, **self.form_paddings)

            # PRE-DETECT SPEACH
            Label(ts_form_frame, text="Pre-Detect Speech", **self.label_settings).grid(row=7, column=1,
                                                                                       **self.input_grid_settings,
                                                                                       **self.form_paddings)
            pre_detect_speech_var = tk.BooleanVar(ts_form_frame,
                                                  value=self.stAI.get_app_setting('transcription_pre_detect_speech',
                                                                                  default_if_none=True))

            pre_detect_speech_input = tk.Checkbutton(ts_form_frame, variable=pre_detect_speech_var)
            pre_detect_speech_input.grid(row=7, column=2, **self.input_grid_settings, **self.form_paddings)

            # WORD TIMESTAMPS
            # (USE "INCREASED TIME PRECISION" FOR NOW TO AVOID CONFUSION)
            Label(ts_form_frame, text="Increased Time Precision", **self.label_settings).grid(row=8, column=1,
                                                                                              **self.input_grid_settings,
                                                                                              **self.form_paddings)
            word_timestamps_var = tk.BooleanVar(ts_form_frame,
                                                value=self.stAI.get_app_setting('transcription_word_timestamps',
                                                                                default_if_none=True))

            word_timestamps_input = tk.Checkbutton(ts_form_frame, variable=word_timestamps_var)
            word_timestamps_input.grid(row=8, column=2, **self.input_grid_settings, **self.form_paddings)

            # MAX CHARACTERS PER SEGMENT
            max_chars_per_segment_label = Label(ts_form_frame, text="Max. Characters Per Line", **self.label_settings)
            max_chars_per_segment_label.grid(row=9, column=1, **self.input_grid_settings, **self.form_paddings)
            max_chars_per_segment_var = tk.StringVar(ts_form_frame,
                                                     value=self.stAI.get_app_setting(
                                                         'transcription_max_chars_per_segment',
                                                         default_if_none=''))

            max_chars_per_segment_input = tk.Entry(ts_form_frame, textvariable=max_chars_per_segment_var,
                                                   **self.entry_settings_quarter)
            max_chars_per_segment_input.grid(row=9, column=2, **self.input_grid_settings, **self.form_paddings)

            # only allow integers
            max_chars_per_segment_input.config(validate="key",
                                               validatecommand=
                                               (max_chars_per_segment_input.register(
                                                   self.only_allow_integers), '%P'))

            # MAX WORDS PER SEGMENT
            max_words_per_segment_label = Label(ts_form_frame, text="Max. Words Per Line", **self.label_settings)
            max_words_per_segment_label.grid(row=10, column=1, **self.input_grid_settings, **self.form_paddings)

            max_words_per_segment_var = tk.StringVar(ts_form_frame,
                                                     value=self.stAI.get_app_setting(
                                                         'transcription_max_words_per_segment',
                                                         default_if_none=''))

            max_words_per_segment_input = tk.Entry(ts_form_frame, textvariable=max_words_per_segment_var,
                                                   **self.entry_settings_quarter)
            max_words_per_segment_input.grid(row=10, column=2, **self.input_grid_settings, **self.form_paddings)

            # only allow integers
            max_words_per_segment_input.config(validate="key",
                                               validatecommand=
                                               (max_chars_per_segment_input.register(
                                                   self.only_allow_integers), '%P'))

            # SPLIT ON PUNCTUATION MARKS
            split_on_punctuation_marks_label = Label(ts_form_frame, text="Split On Punctuation", **self.label_settings)
            split_on_punctuation_marks_label.grid(row=11, column=1, **self.input_grid_settings, **self.form_paddings)

            split_on_punctuation_marks_var = tk.BooleanVar(ts_form_frame,
                                                           value=self.stAI.get_app_setting(
                                                               'transcription_split_on_punctuation_marks',
                                                               default_if_none=False))

            split_on_punctuation_marks_input = tk.Checkbutton(ts_form_frame, variable=split_on_punctuation_marks_var)
            split_on_punctuation_marks_input.grid(row=11, column=2, **self.input_grid_settings, **self.form_paddings)

            # PREVENT GAPS SHORTER THAN
            prevent_short_gaps_label = Label(ts_form_frame, text="Prevent Gaps Shorter Than", **self.label_settings)
            prevent_short_gaps_label.grid(row=12, column=1, **self.input_grid_settings, **self.form_paddings)

            prevent_short_gaps_var = tk.StringVar(ts_form_frame,
                                                            value=self.stAI.get_app_setting(
                                                                'transcription_prevent_short_gaps',
                                                                default_if_none=''))
            prevent_short_gaps_input = tk.Entry(ts_form_frame, textvariable=prevent_short_gaps_var,
                                                         **self.entry_settings_quarter)
            prevent_short_gaps_input.grid(row=12, column=2, **self.input_grid_settings, **self.form_paddings)

            # only allow floats
            prevent_short_gaps_input.config(validate="key",
                                                    validatecommand=
                                                    (prevent_short_gaps_input.register(
                                                        self.only_allow_floats), '%P'))

            # if word_timestamps_var is False, hide the max words per segment input
            # but check on every change of the word_timestamps_var
            def update_max_per_segment_inputs_visibility():
                if word_timestamps_var.get():
                    max_words_per_segment_input.grid()
                    max_chars_per_segment_input.grid()
                    max_words_per_segment_label.grid()
                    max_chars_per_segment_label.grid()
                    split_on_punctuation_marks_input.grid()
                    split_on_punctuation_marks_label.grid()
                else:
                    max_words_per_segment_input.grid_remove()
                    max_chars_per_segment_input.grid_remove()
                    max_words_per_segment_label.grid_remove()
                    max_chars_per_segment_label.grid_remove()
                    split_on_punctuation_marks_input.grid_remove()
                    split_on_punctuation_marks_label.grid_remove()

            word_timestamps_var.trace('w', lambda *args: update_max_per_segment_inputs_visibility())
            update_max_per_segment_inputs_visibility()

            # INITIAL PROMPT INPUT
            Label(ts_form_frame, text="Initial Prompt", **self.label_settings).grid(row=20, column=1,
                                                                                    sticky='nw',
                                                                                    # **self.input_grid_settings,
                                                                                    **self.form_paddings)
            # prompt_var = StringVar(ts_form_frame)
            prompt_input = Text(ts_form_frame, wrap=tk.WORD, height=4, **self.entry_settings)
            prompt_input.grid(row=20, column=2, **self.input_grid_settings, **self.form_paddings)
            prompt_input.insert(END, " - How are you?\n - I'm fine, thank you.")

            # TIME INTERVALS INPUT
            Label(ts_form_frame, text="Time Intervals", **self.label_settings).grid(row=30, column=1,
                                                                                    sticky='nw',
                                                                                    # **self.input_grid_settings,
                                                                                    **self.form_paddings)

            time_intervals_input = Text(ts_form_frame, wrap=tk.WORD, height=4, **self.entry_settings)
            time_intervals_input.grid(row=30, column=2, **self.input_grid_settings, **self.form_paddings)
            time_intervals_input.insert(END, str(time_intervals) if time_intervals is not None else '')

            # EXCLUDE TIME INTERVALS INPUT
            Label(ts_form_frame, text="Exclude Time Intervals", **self.label_settings).grid(row=31, column=1,
                                                                                            sticky='nw',
                                                                                            # **self.input_grid_settings,
                                                                                            **self.form_paddings)

            excluded_time_intervals_input = Text(ts_form_frame, wrap=tk.WORD, height=4, **self.entry_settings)
            excluded_time_intervals_input.grid(row=31, column=2, **self.input_grid_settings, **self.form_paddings)
            excluded_time_intervals_input.insert(END,
                                                 str(excluded_time_intervals) \
                                                     if excluded_time_intervals is not None else '')

            # START BUTTON

            # add all the settings entered by the use into a nice dictionary
            # transcription_config = dict(name=name_input.get(), language='English', beam_size=5, best_of=5)

            Label(ts_form_frame, text="", **self.label_settings).grid(row=50, column=1,
                                                                      **self.input_grid_settings, **self.paddings)
            start_button = Button(ts_form_frame, text='Start')
            start_button.grid(row=50, column=2, **self.input_grid_settings, **self.paddings)
            start_button.config(command=lambda audio_file_path=audio_file_path,
                                               transcription_file_path_var=transcription_file_path_var,
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
                                            initial_prompt=prompt_input.get(1.0, END),
                                            pre_detect_speech=pre_detect_speech_var.get(),
                                            word_timestamps=word_timestamps_var.get(),
                                            max_chars_per_segment=max_chars_per_segment_var.get(),
                                            max_words_per_segment=max_words_per_segment_var.get(),
                                            split_on_punctuation_marks=split_on_punctuation_marks_var.get(),
                                            prevent_short_gaps=prevent_short_gaps_var.get(),
                                            time_intervals=time_intervals_input.get(1.0, END),
                                            excluded_time_intervals=excluded_time_intervals_input.get(1.0, END),
                                            transcription_file_path=transcription_file_path_var.get()
                                            )
                                )

            # if skip settings was passed, just start the transcription
            if kwargs.get('skip_settings', False):
                self.start_transcription_button(ts_window_id,
                                                audio_file_path=audio_file_path,
                                                unique_id=unique_id,
                                                language=language_var.get(),
                                                task=task_var.get(),
                                                name=name_var.get(),
                                                model=model_var.get(),
                                                device=device_var.get(),
                                                initial_prompt=prompt_input.get(1.0, END),
                                                pre_detect_speech=pre_detect_speech_var.get(),
                                                word_timestamps=word_timestamps_var.get(),
                                                max_chars_per_segment=max_chars_per_segment_var.get(),
                                                max_words_per_segment=max_words_per_segment_var.get(),
                                                split_on_punctuation_marks=split_on_punctuation_marks_var.get(),
                                                prevent_short_gaps=prevent_short_gaps_var.get(),
                                                time_intervals=time_intervals_input.get(1.0, END),
                                                excluded_time_intervals=excluded_time_intervals_input.get(1.0, END),
                                                transcription_file_path=transcription_file_path_var.get()
                                                )

    def convert_text_to_time_intervals(self, text):
        time_intervals = []

        # split the text into lines
        lines = text.splitlines()

        # for each line
        for line in lines:
            # split the line into two parts, separated by a dash
            parts = line.split('-')

            # if there are two parts
            if len(parts) == 2:
                # remove any spaces
                start = parts[0].strip()
                end = parts[1].strip()

                # convert the start and end times to seconds
                start_seconds = self.convert_time_to_seconds(start)
                end_seconds = self.convert_time_to_seconds(end)

                # if both start and end times are valid
                if start_seconds is not None and end_seconds is not None:
                    # add the time interval to the list
                    time_intervals.append([start_seconds, end_seconds])

                else:
                    # otherwise, show an error message
                    messagebox.showerror("Error", "Invalid time interval: " + line)
                    return False

        if time_intervals == []:
            return True

        return time_intervals

    def convert_time_to_seconds(self, time, fps=None):

        # the text is a string with lines like this:
        # 0:00:00:00 - 0:00:00:00
        # or like this:
        # 0:00:00.000 - 0:00:01.000
        # or like this:
        # 0,0 - 0,01
        # or like this:
        # 0.0 - 0.01

        # if the format is 0:00:00.000 or 0:00:00:00
        if ':' in time:

            time_array = time.split(':')

            # if the format is 0:00:00:00 - assume a timecode was passed
            if len(time_array) == 4:

                if fps is not None:
                    # if the format is 0:00:00:00
                    # convert the time to seconds
                    return int(time_array[0]) * 3600 + int(time_array[1]) * 60 + int(time_array[2]) + \
                        int(time_array[3]) / fps

                else:
                    logger.error('The time format is 0:00:00:00, but the fps is not specified.')

            elif len(time_array) == 3:
                # hours, minutes, seconds
                return int(time_array[0]) * 3600 + int(time_array[1]) * 60 + float(time_array[2])

            elif len(time_array) == 2:
                # minutes, seconds
                return int(time_array[0]) * 60 + float(time_array[1])

            elif len(time_array) == 1:
                # seconds
                return float(time_array[0])

            else:
                return 0

        # if the format is 0,0
        elif ',' in time:
            return float(time.replace(',', '.'))

        # if the format is 0.0
        elif '.' in time:
            return float(time)

        elif time.isnumeric():
            return int(time)

        else:
            logger.error('The time format is not recognized.')
            return None

    def start_transcription_button(self, transcription_settings_window_id=None, **transcription_config):
        '''
        This sends the transcription to the transcription queue via toolkit_ops object,
        but also closes the trancription window forever
        :param transcription_settings_window_id:
        :param transcription_config:
        :return:
        '''

        # validate the transcription settings
        transcription_config['time_intervals'] = \
            self.convert_text_to_time_intervals(transcription_config['time_intervals'])

        if not transcription_config['time_intervals']:
            return False

        # validate the transcription settings
        transcription_config['excluded_time_intervals'] = \
            self.convert_text_to_time_intervals(transcription_config['excluded_time_intervals'])

        if not transcription_config['excluded_time_intervals']:
            return False

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

    def destroy_transcription_window(self, window_id):

        # close any associated find windows and remove the reference from the text windows
        if window_id in self.text_windows:
            if 'find_window_id' in self.text_windows[window_id]:
                find_window_id = self.text_windows[window_id]['find_window_id']

                # call the default destroy window function to destroy the find window
                self.destroy_find_replace_window(window_id=find_window_id)

            # completely remove the reference from the text windows
            del self.text_windows[window_id]

        # destroy the associated search window (if it exists)
        # - in the future, if were to have multiple search windows, we will need to do it differently
        if window_id + '_search' in self.windows:
            self.destroy_window_(self.windows, window_id=window_id + '_search')

        # also destroy the associated groups window (if it exists)
        # - in the future, if were to have multiple search windows, we will need to do it differently
        if window_id + '_transcript_groups' in self.windows:
            self.destroy_transcript_groups_window(window_id=window_id + '_transcript_groups')

        # remove the transcription segments from the transcription_segments dict
        if window_id in self.t_edit_obj.transcript_segments:
            del self.t_edit_obj.transcript_segments[window_id]

        # remove all the ids from the transcription_segments dict
        if window_id in self.t_edit_obj.transcript_segments_ids:
            del self.t_edit_obj.transcript_segments_ids[window_id]

        # remove all other references to the transcription window
        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.typing[window_id]

        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.transcript_editing[window_id]

        if window_id in self.t_edit_obj.transcription_file_paths:
            del self.t_edit_obj.transcription_file_paths[window_id]

        if window_id in self.t_edit_obj.transcription_data:
            del self.t_edit_obj.transcription_data[window_id]

        if window_id in self.t_edit_obj.transcript_groups:
            del self.t_edit_obj.transcript_groups[window_id]

        if window_id in self.t_edit_obj.selected_groups:
            del self.t_edit_obj.selected_groups[window_id]

        if window_id in self.t_edit_obj.selected_segments:
            del self.t_edit_obj.selected_segments[window_id]

        if window_id in self.t_edit_obj.transcript_modified:
            del self.t_edit_obj.transcript_modified[window_id]

        if window_id in self.t_edit_obj.active_segment:
            del self.t_edit_obj.active_segment[window_id]

        if window_id in self.t_edit_obj.last_active_segment:
            del self.t_edit_obj.last_active_segment[window_id]

        if window_id in self.t_edit_obj.current_window_tc:
            del self.t_edit_obj.current_window_tc[window_id]

        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.sync_with_playhead[window_id]

        # call the default destroy window function
        self.destroy_window_(parent_element=self.windows, window_id=window_id)

    def destroy_text_window(self, window_id):
        '''
        This function destroys a text window
        :param window_id:
        :return:
        '''

        # close any find windows
        if 'find_window_id' in self.text_windows[window_id]:
            find_window_id = self.text_windows[window_id]['find_window_id']

            # call the default destroy window function to destroy the find window
            self.destroy_find_replace_window(window_id=find_window_id)

        # clear the text windows dict
        if window_id in self.text_windows:
            del self.text_windows[window_id]

        # call the default destroy window function
        self.destroy_window_(parent_element=self.windows, window_id=window_id)

    def destroy_find_replace_window(self, window_id, parent_window_id=None):
        '''
        This function destroys a find text window
        :param window_id:
        :return:
        '''

        # if no parent window id is specified, try to find it
        if parent_window_id is None:
            if window_id in self.find_windows and 'parent_window_id' in self.find_windows[window_id]:
                parent_window_id = self.find_windows[window_id]['parent_window_id']

        # clear the find_window element in the text windows dict
        if 'find_window_id' in self.text_windows[parent_window_id]:
            del self.text_windows[parent_window_id]['find_window_id']

            # clear any find results from main text window

            if self.text_windows[parent_window_id]['text_widget'] is not None:
                self.text_windows[parent_window_id]['text_widget'].tag_delete('find_result_tag')
                self.text_windows[parent_window_id]['text_widget'].tag_delete('found')

        # clear the find windows dict
        if window_id in self.find_windows:
            del self.find_windows[window_id]

        # call the default destroy window function
        self.destroy_window_(parent_element=self.windows, window_id=window_id)

    def destroy_window_(self, parent_element, window_id):
        '''
        This makes sure that the window reference is deleted when a user closes a window
        :param parent_element:
        :param window_id:
        :return:
        '''
        # first destroy the window
        parent_element[window_id].destroy()

        logger.debug('Closing window: ' + window_id)

        # then remove its reference
        del parent_element[window_id]

    def open_transcript(self, **options):
        '''
        This prompts the user to open a transcript file and then opens it a transcript window
        :return:
        '''

        # did we ever save a target dir for this project?
        last_target_dir = None
        if NLE.is_connected() and NLE.current_project is not None:
            last_target_dir = self.stAI.get_project_setting(project_name=NLE.current_project, setting_key='last_target_dir')

        # ask user which transcript to open
        transcription_json_file_path = self.ask_for_target_file(filetypes=[("Json files", "json srt")],
                                                                target_dir=last_target_dir)

        # abort if user cancels
        if not transcription_json_file_path:
            return False

        # if resolve is connected, save the directory where the file is as a last last target dir
        if NLE.is_connected() and transcription_json_file_path and os.path.exists(transcription_json_file_path):
            self.stAI.save_project_setting(project_name=NLE.current_project,
                                           setting_key='last_target_dir',
                                           setting_value=os.path.dirname(transcription_json_file_path))

        # if this is an srt file, but a .transcription.json file exists in the same directory,
        # ask the user if they want to open the .transcription.json file instead
        if transcription_json_file_path.endswith('.srt') \
                and os.path.exists(transcription_json_file_path.replace('.srt', '.transcription.json')):

            # ask user
            if messagebox.askyesno(title="Open Transcript",
                                   message='The file you selected is an SRT file, '
                                           'but a transcription.json file with the exact name '
                                           'exists in the same folder.\n\n'
                                           'Do you want to open the transcription.json file instead?'
                                           '\n\n'
                                           'If you answer NO, the transcription.json will be '
                                           'overwritten with the content of the SRT file.'
                                           ''):
                # change the file path
                transcription_json_file_path = transcription_json_file_path.replace('.srt', '.transcription.json')

        # if this is an srt file, ask the user if they want to convert it to json
        if transcription_json_file_path.endswith('.srt'):

            convert_from_srt = messagebox.askyesno(title="Convert SRT?",
                                                   message='Do you want to convert this SRT file '
                                                           'to a transcription file?')

            # if the user wants to convert the srt file to json
            if convert_from_srt:
                # convert the srt file to json
                # (it will overwrite any existing transcription.json with the same name in the same directory)
                transcription_json_file_path \
                    = self.toolkit_ops_obj.convert_srt_to_transcription_json(
                    srt_file_path=transcription_json_file_path,
                    overwrite=True
                )

        # if the file is not a json file, abort
        if not transcription_json_file_path.endswith('.json'):
            self.notify_via_messagebox(title='Not a transcription',
                                       message='The file \n{}\nis not a transcription file.'
                                       .format(os.path.basename(transcription_json_file_path)),
                                       message_log='The file {} is not a transcription file.',
                                       type='error')
            return False

        # open the transcript in a transcript window

        # why not open the transcript in a transcription window?
        self.open_transcription_window(transcription_file_path=transcription_json_file_path, **options)

    def open_transcription_window(self, title=None, transcription_file_path=None, srt_file_path=None,
                                  select_line_no=None, add_to_selection=None):

        if self.toolkit_ops_obj is None:
            logger.error('Cannot open transcription window. A toolkit operations object is needed to continue.')
            return False

        # Note: most of the transcription window functions are stored in the TranscriptEdit class

        # only continue if the transcription path was passed and the file exists
        if transcription_file_path is None or os.path.exists(transcription_file_path) is False:
            logger.error('The transcription file {} cannot be found.'.format(transcription_file_path))
            return False

        # now read the transcription file contents
        transcription_json = \
            self.toolkit_ops_obj.get_transcription_file_data(transcription_file_path=transcription_file_path)

        if not transcription_json:
            logger.warning('Invalid transcription file {}.'.format(transcription_file_path))
            return False

        # if no srt_file_path was passed
        if srt_file_path is None:

            # try to use the file path in the transcription json
            if isinstance(transcription_json, dict) and 'srt_file_path' in transcription_json:
                srt_file_path = transcription_json['srt_file_path']

        # try to see if we have a srt path or not
        if srt_file_path is not None:

            # if not we're dealing with an absolute path
            if not os.path.isabs(srt_file_path):
                # assume that the srt is in the same directory as the transcription
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

        # ask user if they want to add timeline info to the transcription file (if they were not recorded)
        # (but only if ask_for_timeline_info is True in the app settings)
        # if self.stAI.get_app_setting(setting_name='ask_for_timeline_info', default_if_none=False) is True:
        #
        #    # if the transcription file does not containe the timeline fps
        #    if 'timeline_fps' not in transcription_json:
        #         # ask the user if they want to add timeline info to the transcription file
        #         if timeline_fps := simpledialog.askstring(title='Add fps to transcription data?',
        #                                   prompt="The transcription file does not contain timeline fps info.\n"
        #                                          "If you want to add it, please enter the fps value here.\n"
        #                                   ):
        #             print(timeline_fps)

        # create a window for the transcript if one doesn't already exist
        if self.create_or_open_window(parent_element=self.root, window_id=t_window_id, title=title, resizable=True,
                                      close_action=lambda t_window_id=t_window_id: \
                                              self.destroy_transcription_window(t_window_id)
                                      ):

            # add the path to the transcription_file_paths dict in case we need it later
            self.t_edit_obj.transcription_file_paths[t_window_id] = transcription_file_path

            # initialize the transcript_segments_ids for this window
            self.t_edit_obj.transcript_segments_ids[t_window_id] = {}

            # add the transcript groups to the transcript_groups dict
            if 'transcript_groups' in transcription_json:

                self.t_edit_obj.transcript_groups[t_window_id] = transcription_json['transcript_groups']

                # if the transcript groups are not empty
                if transcription_json['transcript_groups']:

                    # open the transcript groups window
                    if self.stAI.get_app_setting(setting_name='open_transcript_groups_window_on_open',
                                                 default_if_none=False) is True:
                        self.open_transcript_groups_window(transcription_window_id=t_window_id,
                                                           transcription_name=title)

            else:
                self.t_edit_obj.transcript_groups[t_window_id] = {}

            # create a header frame to hold stuff above the transcript text
            header_frame = tk.Frame(self.windows[t_window_id], name='header_frame')
            header_frame.place(anchor='nw', relwidth=1)

            # THE MAIN TEXT ELEMENT
            # create a frame for the text element
            text_form_frame = tk.Frame(self.windows[t_window_id], name='text_form_frame')
            text_form_frame.pack(pady=50, expand=True, fill='both')

            # does the json file actually contain transcript segments generated by whisper?
            if 'segments' in transcription_json:

                # add everything except the segments and the text to the self.t_edit_obj.transcription_data dict
                self.t_edit_obj.transcription_data[t_window_id] = \
                    {k: v for k, v in transcription_json.items() if k != 'segments' and k != 'text'}

                # set up the text element where we'll add the actual transcript
                text = Text(text_form_frame, name='transcript_text',
                            font=(self.transcript_font), width=45, height=30, padx=5, pady=5, wrap=tk.WORD,
                            background=self.resolve_theme_colors['black'],
                            foreground=self.resolve_theme_colors['normal'])

                # add a scrollbar to the text element
                scrollbar = Scrollbar(text_form_frame, orient="vertical", **self.scrollbar_settings)
                scrollbar.config(command=text.yview)
                scrollbar.pack(side=tk.RIGHT, fill='y', pady=5)

                # configure the text element to use the scrollbar
                text.config(yscrollcommand=scrollbar.set)

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
                    line = line + 1

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

                        # for now, just add 2 new lines after each segment:
                        text.insert(END, '\n')

                # make the text read only
                # and take into consideration the longest segment to adjust the width of the window
                if longest_segment_num_char > 60:
                    longest_segment_num_char = 60
                text.config(state=DISABLED, width=longest_segment_num_char)

                # add undo/redo
                # this will not work for splitting/merging lines
                # text.config(undo=True)

                # set the top, in-between and bottom text spacing
                text.config(spacing1=0, spacing2=0.2, spacing3=5)

                # then show the text element
                text.pack(anchor='w', expand=True, fill='both')

                # create a footer frame that holds stuff on the bottom of the transcript window
                footer_frame = tk.Frame(self.windows[t_window_id], name='footer_frame')
                footer_frame.place(relwidth=1, anchor='sw', rely=1)

                # add a status label to print out current transcription status
                status_label = Label(footer_frame, name='status_label',
                                     text="", anchor='w', foreground=self.resolve_theme_colors['normal'])
                status_label.pack(side=tk.LEFT, **self.paddings)

                # bind shift click events to the text
                # text.bind("<Shift-Button-1>", lambda e:
                #         self.t_edit_obj.select_text_lines(event=e, text_element=text, window_id=t_window_id))

                select_options = {'window_id': t_window_id, 'text_element': text, 'status_label': status_label}

                # bind all key presses to transcription window actions
                self.windows[t_window_id].bind("<KeyPress>",
                                               lambda e:
                                               self.t_edit_obj.transcription_window_keypress(event=e,
                                                                                             **select_options))

                # bind CMD/CTRL + key presses to transcription window actions
                self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-KeyPress>",
                                               lambda e:
                                               self.t_edit_obj.transcription_window_keypress(event=e, special_key='cmd',
                                                                                             **select_options))

                # bind all mouse clicks on text
                text.bind("<Button-1>", lambda e,
                                               select_options=select_options:
                self.t_edit_obj.transcription_window_mouse(e,
                                                           **select_options))

                # bind CMD/CTRL + mouse Clicks to text
                text.bind("<" + self.ctrl_cmd_bind + "-Button-1>",
                          lambda e, select_options=select_options:
                          self.t_edit_obj.transcription_window_mouse(e,
                                                                     special_key='cmd',
                                                                     **select_options))

                # bind ALT/OPT + mouse Click to edit transcript
                text.bind("<" + self.alt_bind + "-Button-1>",
                          lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id, text=text,
                                                                    status_label=status_label)
                          )

                # bind CMD/CTRL + e to edit transcript
                self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-e>",
                                               lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id,
                                                                                         text=text,
                                                                                         status_label=status_label)
                                               )

                # FIND BUTTON

                find_button = tk.Button(header_frame, text='Find', name='find_replace_button',
                                        command=lambda:
                                        self.open_find_replace_window(parent_window_id=t_window_id,
                                                                      title="Find in {}".format(title)
                                                                      ))

                find_button.pack(side=tk.LEFT, **self.paddings)

                # bind CMD/CTRL + f to open find and replace window
                self.windows[t_window_id].bind("<" + self.ctrl_cmd_bind + "-f>", lambda e:
                self.open_find_replace_window(parent_window_id=t_window_id,
                                              title="Find in {}".format(title)
                                              ))

                # ADVANCED SEARCH
                # this button will open a new window with advanced search options
                advanced_search_button = tk.Button(header_frame, text='Advanced Search', name='advanced_search_button',
                                                   command=lambda:
                                                   self.open_advanced_search_window(transcription_window_id=t_window_id,
                                                                                    search_file_path= \
                                                                                        transcription_file_path))

                advanced_search_button.pack(side=tk.LEFT, **self.paddings)

                # GROUPS BUTTON
                groups_button = tk.Button(header_frame, text='Groups', name='groups_button',
                                          command=lambda:
                                          self.open_transcript_groups_window(transcription_window_id=t_window_id)
                                          )
                groups_button.pack(side=tk.LEFT, **self.paddings)

                # KEEP ON TOP BUTTON
                on_top_button = tk.Button(header_frame, name='on_top_button', text="Keep on top", takefocus=False)
                # add the command function here
                on_top_button.config(command=lambda on_top_button=on_top_button, t_window_id=t_window_id:
                self.window_on_top_button(button=on_top_button, window_id=t_window_id)
                                     )
                on_top_button.pack(side=tk.RIGHT, **self.paddings, anchor='e')

                # keep the transcript window on top or not according to the config
                # and also update the initial text on the respective button
                self.window_on_top_button(button=on_top_button,
                                          window_id=t_window_id,
                                          on_top=self.stAI.get_app_setting('transcripts_always_on_top',
                                                                      default_if_none=False)
                                          )

                # IMPORT SRT BUTTON
                if srt_file_path:
                    import_srt_button = tk.Button(footer_frame,
                                                  name='import_srt_button',
                                                  text="Import SRT into Bin",
                                                  takefocus=False,
                                                  command=lambda:
                                                  self.toolkit_ops_obj.resolve_api.import_media(srt_file_path)
                                                  )
                    import_srt_button.pack(side=tk.RIGHT, **self.paddings, anchor='e')

                else:
                    import_srt_button = None

                # SYNC BUTTON

                sync_button = tk.Button(header_frame, name='sync_button', takefocus=False)
                sync_button.config(command=lambda sync_button=sync_button, window_id=t_window_id:
                self.t_edit_obj.sync_with_playhead_button(
                    button=sync_button,
                    window_id=t_window_id)
                                   )

                # LINK TO TIMELINE BUTTON

                # is this transcript linked to the current timeline?

                # prepare an empty link button for now, and only show it when/if resolve starts
                link_button = tk.Button(footer_frame, name='link_button')
                link_button.config(command=lambda link_button=link_button,
                                                  transcription_file_path=transcription_file_path:
                self.t_edit_obj.link_to_timeline_button(
                    button=link_button,
                    transcription_file_path=transcription_file_path)
                                   )

                # start update the transcription window with some stuff
                # here we send the update transcription window function a few items that need to be updated
                self.windows[t_window_id].after(100, lambda link_button=link_button,
                                                            t_window_id=t_window_id,
                                                            transcription_file_path=transcription_file_path:
                self.update_transcription_window(window_id=t_window_id,
                                                 link_button=link_button,
                                                 sync_button=sync_button,
                                                 import_srt_button=import_srt_button,
                                                 transcription_file_path=transcription_file_path,
                                                 text=text)
                                                )

                # add this window to the list of text windows
                self.text_windows[t_window_id] = {'text_widget': text}

            # if no transcript was found in the json file, alert the user
            else:
                not_a_transcription_message = 'The file {} isn\'t a transcript.'.format(
                    os.path.basename(transcription_file_path))

                self.notify_via_messagebox(title='Not a transcript file',
                                           message=not_a_transcription_message,
                                           type='warning'
                                           )
                self.destroy_window_(self.windows, t_window_id)

        # if the transcription window already exists,
        # we won't know the window id since it's not passed
        else:
            # so update all the windows just to make sure that all the elements are in the right state
            self.update_all_transcription_windows()


        # if select_line_no was passed
        if select_line_no is not None:
            # select the line in the text widget
            self.t_edit_obj.set_active_segment(window_id=t_window_id, line=select_line_no)

        # if add_to_selection was passed
        if add_to_selection is not None and add_to_selection and type(add_to_selection) is list:

            # go through all the add_to_selection items
            for selection_line_no in add_to_selection:
                # and add them to the selection

                # select the line in the text widget
                self.t_edit_obj.segment_to_selection(window_id=t_window_id, line=selection_line_no)

    def update_transcription_window(self, window_id, update_all: bool = True, **update_attr):
        '''
        Auto-updates a transcription window GUI

        :param window_id:
        :param update_all: If this is True, try to update all the GUI elements of the window
                            by using their hard-coded, even if they were not passed in the update_attr dict.
        :param update_attr:
        :return:
        '''

        # if the update_all attribute is True
        # try to get the following GUI elements from the window, if they were not passed in the update_attr dict
        # so we update them later in the function
        if update_all:

            # if the transcription file path was not sent
            if 'transcription_file_path' not in update_attr \
                    and window_id in self.t_edit_obj.transcription_file_paths:
                # try to get it from the window
                update_attr['transcription_file_path'] = self.t_edit_obj.transcription_file_paths[window_id]

            # if the link button was not passed or is not tkinter button
            if 'link_button' not in update_attr or type(update_attr['link_button']) is not tk.Button:
                # so get the link button from the window by using the hard-coded name
                update_attr['link_button'] \
                    = self.windows[window_id].nametowidget('footer_frame.link_button')

            # if the sync button was not passed or is not tkinter button
            if 'sync_button' not in update_attr or type(update_attr['link_button']) is not tk.Button:
                # so get the link button from the window by using the hard-coded name
                update_attr['sync_button'] \
                    = self.windows[window_id].nametowidget('header_frame.sync_button')

            # if the import srt button was not passed or is not tkinter button
            if 'import_srt_button' not in update_attr or type(update_attr['import_srt_button']) is not tk.Button:
                # so get the import srt button from the window by using the hard-coded name
                update_attr['import_srt_button'] \
                    = self.windows[window_id].nametowidget('footer_frame.import_srt_button')

            # if the text item was not passed or is not tkinter text
            if 'text' not in update_attr or type(update_attr['text']) is not tk.Text:
                # so get the link button from the window by using the hard-coded name
                update_attr['text'] \
                    = self.windows[window_id].nametowidget('text_form_frame.transcript_text')

        # if NLE is connected and there is a current timeline
        if NLE.is_connected() and NLE.current_timeline is not None:

            # if we still don't have a transcription file path by now,
            # assume there is no link between the window and the resolve timeline
            # although that might be very weird, so warn the user
            if 'transcription_file_path' not in update_attr:
                logger.warning('No transcription file path found for window {}'.format(window_id))
                link = False
            else:
                # is there a link between the transcription and the resolve timeline?
                link, _ = self.toolkit_ops_obj.get_transcription_to_timeline_link(
                    transcription_file_path=update_attr['transcription_file_path'],
                    timeline_name=NLE.current_timeline['name'],
                    project_name=NLE.current_project)

            # update the import srt button if it was passed in the call
            if update_attr.get('import_srt_button', None) is not None:

                # update the import srt button on the transcription window
                update_attr['import_srt_button'].pack(side=tk.RIGHT, **self.paddings, anchor='e')

            # update the link button text if it was passed in the call
            if update_attr.get('link_button', None) is not None:

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
            if update_attr.get('sync_button', None) is not None:

                if self.t_edit_obj.sync_with_playhead[window_id]:
                    sync_button_text = "Don't sync"
                else:
                    sync_button_text = "Sync"

                # update the sync button on the transcription window
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
                    and self.t_edit_obj.current_window_tc[window_id] != NLE.current_tc:
                update_attr = self.sync_current_tc_to_transcript(window_id=window_id, **update_attr)

        # hide some stuff if resolve isn't connected
        else:
            # @TODO: check why this doesn't happen when resolve is closed - why do the buttons still stay in the window?

            if update_attr.get('import_srt_button', None) is not None:
                update_attr['import_srt_button'].pack_forget()

            if update_attr.get('link_button', None) is not None:
                update_attr['link_button'].pack_forget()

            if update_attr.get('sync_button', None) is not None:
                update_attr['sync_button'].pack_forget()

    def sync_current_tc_to_transcript(self, window_id, **update_attr):

        # if no text was passed, get it from the window
        if 'text' not in update_attr or type(update_attr['text']) is not tk.Text:
            # so get the link button from the window by using the hard-coded name
            update_attr['text'] \
                = self.windows[window_id].nametowidget('text_form_frame.transcript_text')

        # how many segments / lines does the transcript on this window contain?
        max_lines = len(self.t_edit_obj.transcript_segments[window_id])

        # initialize the timecode object for the current_tc
        current_tc_obj = Timecode(NLE.current_timeline_fps, NLE.current_tc)

        # initialize the timecode object for the timeline start_tc
        timeline_start_tc_obj = Timecode(NLE.current_timeline_fps, NLE.current_timeline['startTC'])

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
                    < float(self.t_edit_obj.transcript_segments[window_id][num]['end']) - 0.01:
                line = num + 1

                # set the line as the active segment on the timeline
                self.t_edit_obj.set_active_segment(window_id, update_attr['text'], line)

            num = num + 1

        update_attr['text'].tag_config('current_time', foreground=self.resolve_theme_colors['white'])

        # highlight current line on transcript
        # update_attr['text'].tag_add('current_time')

        # now remember that we did the update for the current timecode
        self.t_edit_obj.current_window_tc[window_id] = NLE.current_tc

        return update_attr

    def sync_all_transcription_windows(self):

        # loop through all the open windows
        for window_id in self.windows:

            # check if it needs to be synced with the playhead
            if window_id in self.t_edit_obj.sync_with_playhead \
                    and self.t_edit_obj.sync_with_playhead[window_id]:
                # and if it does, sync it
                self.sync_current_tc_to_transcript(window_id)

    def update_all_transcription_windows(self):

        # loop through all the open windows
        for window_id in self.windows:

            # if the window is a transcription window
            if window_id in self.t_edit_obj.transcript_segments:
                # update the window
                self.update_transcription_window(window_id)

    def close_inactive_transcription_windows(self, timeline_transcription_file_paths=None):
        '''
        Closes all transcription windows that are not in the timeline_transcription_file_paths list
        (or all of them if no list is passed)
        :param timeline_transcription_file_paths: list of transcription file paths
        :return: None
        '''

        # get all transcription windows from the self.t_edit_obj.transcription_file_paths
        transcription_windows = self.t_edit_obj.transcription_file_paths.keys()

        # loop through all transcription windows
        for transcription_window in transcription_windows:

            # if the transcription window is not in the timeline_transcription_file_paths
            if timeline_transcription_file_paths is None \
                    or timeline_transcription_file_paths == [] \
                    or self.t_edit_obj.transcription_file_paths[transcription_window] \
                    not in timeline_transcription_file_paths:

                # if the transcription window is open
                if transcription_window in self.windows:
                    # close the window
                    self.destroy_transcription_window(transcription_window)

    def update_transcription_log_window(self):

        # don't do anything if the transcription log window doesn't exist
        if 't_log' not in self.windows:
            logger.debug('No transcription log window exists.')
            return

        # first destroy anything that the window might have held
        list = self.windows['t_log'].winfo_children()
        for l in list:
            l.destroy()

        # if there is no transcription log
        if not self.toolkit_ops_obj.transcription_log:
            # just add a label to the window
            tk.Label(self.windows['t_log'], text='Transcription log empty.', **self.paddings).pack()


        # only do this if the transcription window exists
        # and if the log exists
        elif self.toolkit_ops_obj.transcription_log:

            # create a canvas to hold all the log items in the window
            log_canvas = tk.Canvas(self.windows['t_log'], borderwidth=0)

            # create a frame for the log items
            log_frame = tk.Frame(log_canvas)

            # create a scrollbar to use with the canvas
            scrollbar = Scrollbar(self.windows['t_log'], command=log_canvas.yview, **self.scrollbar_settings)

            # attach the scrollbar to the log_canvas
            log_canvas.config(yscrollcommand=scrollbar.set)

            # add the scrollbar to the window
            scrollbar.pack(side=RIGHT, fill=Y)

            # add the canvas to the window
            log_canvas.pack(side=LEFT, fill=BOTH, expand=True)

            # show the frame in the canvas
            log_canvas.create_window((4, 4), window=log_frame, anchor="nw")

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

                progress = ''
                if 'progress' in t_item and t_item['progress'] and t_item['progress'] != '':

                    # prevent weirdness with progress values over 100%
                    if int(t_item['progress']) > 100:
                        t_item['progress'] = 100

                    progress = ' (' + str(t_item['progress']) + '%)'

                label_status = Label(log_frame, text=t_item['status'] + progress, anchor='w', width=15)
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

    def open_transcription_log_window(self):

        # create a window for the transcription log if one doesn't already exist
        if self.create_or_open_window(parent_element=self.root,
                                      window_id='t_log', title='Transcription Log', resizable=True):
            # and then call the update function to fill the window up
            self.update_transcription_log_window()

            return True

    def open_advanced_search_window(self, transcription_window_id=None, search_file_path=None,
                                    select_dir=False, **kwargs):

        if self.toolkit_ops_obj is None or self.toolkit_ops_obj.t_search_obj is None:
            logger.error('Cannot open advanced search window. A ToolkitSearch object is needed to continue.')
            return False

        # initialize a new search item
        search_item = self.toolkit_ops_obj.SearchItem(toolkit_ops_obj=self.toolkit_ops_obj)

        # declare the empty list of search file paths
        search_file_paths = []

        # check if a searchable file path was passed and if it exists
        if search_file_path is not None and not os.path.exists(search_file_path):
            logger.error('The file {} cannot be found.'.format(search_file_path))
            return False

        # if a transcription window id was passed, get the transcription file path from it
        # and use it as the search file path
        elif search_file_path is None and transcription_window_id is not None:
            search_file_path = self.t_edit_obj.transcription_file_paths[transcription_window_id]

        # if we still don't have a searchable file path (or paths),
        # ask the user to manually select the files
        if search_file_path is None and not search_file_paths:

            if NLE.is_connected():
                initial_dir = self.stAI.get_project_setting(project_name=NLE.current_project,
                                                            setting_key='last_target_dir')

            else:
                initial_dir = '~'

            # if select_dir is true, allow the user to select a directory
            if select_dir:
                # ask the user to select a directory with searchable files
                selected_file_path = filedialog.askdirectory(initialdir=initial_dir,
                                                             title='Select a folder to search')

            else:
                # ask the user to select the searchable files to use in the search corpus
                selected_file_path \
                    = filedialog.askopenfilenames(initialdir=initial_dir,
                                                  title='Select files to use in the search',
                                                  filetypes=[('Transcription files', '*.json'),
                                                             ('Text files', '*.txt'),
                                                             ('Pickle files', '*.pkl')])

            # if resolve is connected, save the last target dir
            if NLE.is_connected() and search_file_paths \
                    and type(search_file_paths) is list and os.path.exists(search_file_paths[0]):
                self.stAI.save_project_setting(project_name=NLE.current_project,
                                               setting_key='last_target_dir',
                                               setting_value=os.path.dirname(search_file_paths[0]))

            # process the selected paths and return only the files that are valid
            # this works for both a single file path and a directory (depending what the user selected above)
            search_file_paths = search_item.process_file_paths(selected_file_path)

            if not search_file_paths:
                logger.info('No files were selected for search. Aborting.')
                return False

        # if the call included a search file path just add it to the list
        elif search_file_path is not None and os.path.exists(search_file_path):
            search_file_paths = [search_file_path]

        # if the call included a transcription window
        # init the search window id, the title and the parent element
        if transcription_window_id is not None and search_file_path is not None:

            # read transcription data from transcription file
            # this is only used for the title of the search window
            # the loading of the search data is done later in the process
            transcription_data = self.toolkit_ops_obj.get_transcription_file_data(search_file_path)

            # get the name of the transcription
            if transcription_data and type(transcription_data) is dict and 'name' in transcription_data:
                title_name = transcription_data['name']
            else:
                title_name = os.path.basename(search_file_path).split('.transcription.json')[0]

            search_window_id = transcription_window_id + '_search'
            search_window_title = 'Search - {}'.format(title_name)
            search_window_parent = self.windows[transcription_window_id]

            # don't open multiple search widows for the same transcription window
            open_multiple = False

            # the transcription_file_paths has only one element
            search_file_paths = [search_file_path]

        # if there is no transcription window id or a search_file_path
        else:

            # if the user selected a directory, use the directory name as the title
            if select_dir and os.path.isdir(selected_file_path):
                search_window_title_ext = ' - ' + os.path.basename(selected_file_path)

            elif search_file_paths and (type(search_file_paths) is list or type(search_file_paths) is tuple):

                search_window_title_ext = ' - ' + os.path.basename(search_file_paths[0])

                # if there are multiple files, sho that there are others
                if len(search_file_paths) > 1:
                    search_window_title_ext += ' + others'

            search_window_id = 'adv_search_' + str(time.time())
            search_window_title = 'Search' + search_window_title_ext
            search_window_parent = self.root

            # this allows us to open multiple search windows at the same time
            open_multiple = True

        # search_kwargs = {'search_item': search_file_paths, 'search_id': search_window_id}

        # prepare the search item
        search_item.search_id = search_window_id
        search_item.search_file_paths = search_file_paths

        # open a new console search window
        self.open_text_window(window_id=search_window_id,
                              title=search_window_title,
                              can_find=True,
                              user_prompt=True,
                              close_action=lambda search_window_id=search_window_id:
                              self.destroy_advanced_search_window(search_window_id),
                              prompt_prefix='SEARCH > ',
                              prompt_callback=self.advanced_search,
                              prompt_callback_kwargs={'search_item': search_item,
                                                      'search_window_id': search_window_id})

        # add text to the search window
        # self._text_window_update(search_window_id, 'Reading {} file{}.'
        #                         .format(len(search_file_paths), 's' if len(search_file_paths) > 1 else ''))

        # now prepare the search corpus
        # (everything happens within the search item, that's why we don't really need to return anything)
        # if the search corpus was prepared successfully, update the search window
        if search_item.prepare_search_corpus():

            search_file_list = ''

            # prepare a list with all the files
            for search_file_path in search_item.search_file_paths:
                search_file_list = search_file_list + os.path.basename(search_file_path) + '\n'

            search_file_list = search_file_list.strip()

            # add the list of files to the search window
            self._text_window_update(search_window_id, 'Loaded {} {}:'
                                     .format(len(search_item.search_file_paths),
                                             'file' if len(search_item.search_file_paths) == 1 else 'files'))
            self._text_window_update(search_window_id, search_file_list)

            if len(search_item.search_corpus) < 1000:
                self._text_window_update(search_window_id, 'Ready for search. Type [help] if you need help.')
            else:
                self._text_window_update(search_window_id, 'Large search corpus detected. '
                                                           'The first search will take longer.\n\n'
                                                           'Ready for search. Type [help] if you need help.')

        else:
            self._text_window_update(search_window_id, 'Search corpus could not be prepared.')

    def advanced_search(self, prompt, search_item, search_window_id):
        '''
        This is the callback function for the advanced search window.
        It calls the search function of the search item and passes the prompt as the search query.
        Then it updates the search window with the results.

        :param prompt:
        :return:
        '''

        # is the user asking for help?
        if prompt.lower() == '[help]':

            help_reply = 'Simply enter a search term and press enter.\n' \
                         'For eg.: about life events\n\n' \
                         'If you want to restrict the number of results, just add [n] to the beginning of the query.\n' \
                         'For eg.: [10] about life events\n\n' \
                         'If you want to perform multiple searches in the same time, use the | character to split the search terms\n' \
                         'For eg.: about life events | about family\n\n' \
                         'If you want to change the model, use [model:<model_name>]\n' \
                         'For eg.: [model:distiluse-base-multilingual-cased-v1]\n\n' \
                         'See list of models here: https://www.sbert.net/docs/pretrained_models.html\n'

            # use this to make sure we have a new prompt prefix for the next search
            self._text_window_update(search_window_id, help_reply)
            return

        # if the user sent either [model] or [model:<model_name>] as the prompt
        elif prompt.lower().startswith('[model') and prompt.lower().endswith(']'):

            # if the model contains a colon, it means that the user wants to load a new model
            if prompt.lower() != '[model]' and ':' in prompt.lower():

                # if a model was passed (eg.: [model:en_core_web_sm]), load it
                # using regex to extract the model name
                model_name = re.search(r'\[model:(.*?)\]', prompt.lower()).group(1)

                if model_name.strip() != '':

                    # let the user know that we are loading the model
                    self._text_window_update(search_window_id, 'Loading model {}...'.format(model_name))

                    # load the model
                    try:
                        search_item.load_model(model_name=model_name)
                    except:
                        self._text_window_update(search_window_id, 'Could not load model {}.'.format(model_name))
                        return

            if search_item.model_name:
                self._text_window_update(search_window_id, 'Using model {}'.format(search_item.model_name))
            else:
                self._text_window_update(search_window_id, 'No model loaded.\n'
                                                           'Perform a search first to load the default model.\n'
                                                           'Or load a model with the [model:<model_name>] command and it will be used '
                                                           'for all the searches in this window.')
            return

        # is the user trying to quit?
        elif prompt.lower() == '[quit]':
            self.destroy_advanced_search_window(search_window_id)
            return

        # remember when we started the search
        start_search_time = time.time()

        search_results, max_results = search_item.search(query=prompt)

        # get the search window text element
        results_text_element = self.text_windows[search_window_id]['text_widget']

        # how long did the search take?
        total_search_time = time.time() - start_search_time

        # now add the search results to the search results window
        if len(search_results) > 0:

            # add text to the search window
            # self._text_window_update(search_window_id + '_B', 'Searched in files...')

            # reset the previous search_term
            result_search_term = ''

            for result in search_results:

                # if we've changed the search term, add a new header
                if result['search_term'] != result_search_term:
                    result_search_term = result['search_term']

                    # add the search term header
                    results_text_element.insert(tk.END, 'Searching for: "' + result_search_term + '"\n')
                    results_text_element.insert(tk.END, '--------------------------------------\n')
                    results_text_element.insert(tk.END, 'Top {} closest phrases:\n\n'.format(max_results))

                # remember the current insert position
                current_insert_position = results_text_element.index(tk.INSERT)

                # shorten the result text if it's longer than 200 characters, but don't cut off words
                if len(result['text']) < 200:
                    text_result = result['text']
                else:
                    text_result = result['text'][:200].rsplit(' ', 1)[0] + '...'

                # add the result text
                results_text_element.insert(tk.END, str(text_result).strip() + '\n')

                # color it in blue
                results_text_element.tag_add('white', current_insert_position, tk.INSERT)
                results_text_element.tag_config('white', foreground=self.resolve_theme_colors['supernormal'])

                # add score to the result
                results_text_element.insert(tk.END, ' -- Score: {:.4f}\n'.format(result['score']))

                # if the type is a transcription
                if result['type'] == 'transcription':
                    # add the transcription file path and segment index to the result
                    results_text_element.insert(tk.END, ' -- Transcript: {}\n'
                                                .format(os.path.basename(result['transcription_file_path'])))
                    results_text_element.insert(tk.END, ' -- Line {} (second {:.2f}) \n'
                                                .format(result['segment_index'], result['transcript_time']))

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, tk.INSERT)

                    # add the transcription file path and segment index to the tag
                    # so we can use it to open the transcription window with the transcription file and jump to the segment
                    results_text_element.tag_bind(tag_name, '<Button-1>',
                                                  lambda event,
                                                         transcription_file_path=result['transcription_file_path'],
                                                         line_no=result['line_no']:
                                                  self.open_transcription_window(
                                                      transcription_file_path=transcription_file_path,
                                                      select_line_no=line_no))

                    # bind mouse clicks press events on the results text box
                    # bind CMD/CTRL + mouse Clicks to text
                    results_text_element.tag_bind(tag_name, "<" + self.ctrl_cmd_bind + "-Button-1>",
                                                  lambda event,
                                                         transcription_file_path=result['transcription_file_path'],
                                                         line_no=result['line_no'],
                                                         all_lines=result['all_lines']:
                                                  self.open_transcription_window(
                                                      transcription_file_path=transcription_file_path,
                                                      select_line_no=line_no,
                                                      add_to_selection=all_lines)
                                                  )

                # if the type is a transcription
                elif result['type'] == 'text':
                    # add the transcription file path and segment index to the result
                    results_text_element.insert(tk.END, ' -- File: {}\n'
                                                .format(os.path.basename(result['file_path'])))

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, tk.INSERT)

                    # hash the file path so we can use it as a window id
                    file_path_hash = hashlib.md5(result['file_path'].encode('utf-8')).hexdigest()

                    # get the file basename so we can use it as a window title
                    file_basename = os.path.basename(result['file_path'])

                    # if the user clicks on the result
                    # open the file in the default program (must work for Windows, Mac and Linux)
                    results_text_element.tag_bind(tag_name, '<Button-1>',
                                                  lambda event,
                                                         file_path=result['file_path'],
                                                         result_text=result['text'],
                                                         file_path_hash=file_path_hash,
                                                         file_basename=file_basename:
                                                  self.open_text_file(file_path=file_path,
                                                                      window_id="text_" + file_path_hash,
                                                                      title=file_basename,
                                                                      tag_text=result_text))

                # if the type is a marker
                elif result['type'] == 'marker':

                    # add the project name
                    results_text_element.insert(tk.END, ' -- Project: {}\n'.format(result['project']))

                    # add the timeline name
                    results_text_element.insert(tk.END, ' -- Timeline: {}\n'.format(result['timeline']))

                    # add the timeline name
                    results_text_element.insert(tk.END, ' -- Frame: {}\n'.format(result['marker_index']))
                    # results_text_element.insert(tk.END, ' -- Source: Timeline Marker\n')


                else:
                    # mention that the result source is unknown
                    results_text_element.insert(tk.END, ' -- Source: Unknown\n')

                # add a new line
                results_text_element.insert(tk.END, '\n')

            # update the results text element
            results_text_element.insert(tk.END, '--------------------------------------\n')
            results_text_element.insert(tk.END, 'Search took {:.2f} seconds\n'.format(total_search_time))

            # use this to make sure we have a new prompt prefix for the next search
            self._text_window_update(search_window_id, 'Ready for new search.')

    def open_assistant_window(self, assistant_window_id: str = None,
                              transcript_text: str = None
                              ):

        if self.toolkit_ops_obj is None:
            logger.error('Cannot open advanced search window. A ToolkitOps object is needed to continue.')
            return False

        # open a new console assistant window
        assistant_window_id = 'assistant'
        assistant_window_title = 'Assistant'

        # create an entry for the assistant window (if one does not exist)
        if assistant_window_id not in self.assistant_windows:
            self.assistant_windows[assistant_window_id] = {}

        # initialize an assistant item
        if 'assistant_item' not in self.assistant_windows[assistant_window_id]:
            self.assistant_windows[assistant_window_id]['assistant_item'] = \
                self.toolkit_ops_obj.AssistantGPT(toolkit_ops_obj=self.toolkit_ops_obj)

        # but use a simpler reference here
        assistant_item = self.assistant_windows[assistant_window_id]['assistant_item']

        # set the transcript text
        received_context = False
        if transcript_text is not None:
            transcript_text = "TRANSCRIPT\n\n{}\n\nEND".format(transcript_text)
            assistant_item.add_context(context=transcript_text)

            received_context = True

        # does this window already exist?
        window_existed = False
        if assistant_window_id in self.windows:
            window_existed = True

        # open a new console search window
        self.open_text_window(window_id=assistant_window_id,
                              title=assistant_window_title,
                              can_find=True,
                              user_prompt=True,
                              close_action=lambda assistant_window_id=assistant_window_id:
                              self.destroy_assistant_window(assistant_window_id),
                              prompt_prefix='U > ',
                              prompt_callback=self.assistant_query,
                              prompt_callback_kwargs={
                                  'assistant_item': assistant_item,
                                  'assistant_window_id': assistant_window_id
                              },
                              window_width=60,
                              open_multiple=False
                              )

        # show the initial message if the window didn't exist before
        if not window_existed:
            initial_info = 'Your requests might be billed by OpenAI.\n' + \
                           'Type [help] or just ask a question.'

            self._text_window_update(assistant_window_id, initial_info)

        if received_context:
            self._text_window_update(assistant_window_id, 'Added transcript items as context.')

    def assistant_query(self, prompt, assistant_window_id: str, assistant_item=None):

        if assistant_item is None:
            # use the assistant item from the assistant window
            if assistant_window_id in self.assistant_windows:
                assistant_item = self.assistant_windows[assistant_window_id]['assistant_item']

            if assistant_item is None:
                logger.error('Cannot run assistant query. No assistant item found.')
                return False

        # is the user asking for help?
        if prompt.lower() == '[help]':

            help_reply = "StoryToolkitAI Assistant uses gpt-3.5-turbo.\n" \
                         "You might be billed by OpenAI around $0.002 for every 1000 tokens. " \
                         "See openai https://openai.com/pricing for more info. \n\n" \
                         "Every time you ask something, the OpenAI will receive the entire conversation. " \
                         "The longer the conversation, the more tokens you are using on each request.\n" \
                         "Use [usage] to keep track of your usage in this Assistant window.\n\n" \
                         "Use [calc] to get the minimum number of tokens you're sending with each request.\n\n" \
                         "Use [reset] to reset the conversation, while preserving any contexts. " \
                         "This will make the Assistant forget the entire conversation," \
                         "but also reduce the tokens you're sending to OpenAI.\n" \
                         "Use [resetall] to reset the conversation and any context. " \
                         "But also reduce the amount of information you're sending on each request.\n\n" \
                         "Use [context] to see the context text.\n\n" \
                         "Use [exit] to exit the Assistant.\n\n" \
                         "Now, just ask something..."

            # use this to make sure we have a new prompt prefix for the next search
            self._text_window_update(assistant_window_id, help_reply)
            return

        # if the user is asking for usage
        elif prompt.lower() == '[usage]' or prompt.lower() == '[calc]':

            if prompt.lower() == '[calc]':
                num_tokens = assistant_item.calculate_history()
                calc_reply = "The stored conversation, including context totals cca. {} tokens.\n".format(num_tokens)
                calc_reply += "That's probably ${:.6f}\n" \
                              "(might not be accurate, check OpenAI pricing)\n" \
                    .format(num_tokens * assistant_item.price / 1000)
                calc_reply += "This is the minimum amount of tokens you send on each request, " \
                              "plus your message, unless you reset."
                self._text_window_update(assistant_window_id, calc_reply)

            usage_reply = "You have used {} tokens in this Assistant window.\n".format(assistant_item.usage)
            usage_reply += "That's probably ${:.6f}\n" \
                           "(might not be accurate, check OpenAI pricing)" \
                .format(assistant_item.usage * assistant_item.price / 1000)
            self._text_window_update(assistant_window_id, usage_reply)
            return

        elif prompt.lower() == '[reset]':
            assistant_item.reset()
            self._text_window_update(assistant_window_id, 'Conversation reset. Context preserved.')
            return

        elif prompt.lower() == '[resetall]':
            assistant_item.reset()
            assistant_item.add_context(context='')
            self._text_window_update(assistant_window_id, 'Conversation reset. Context removed.')
            return

        elif prompt.lower() == '[context]':
            if assistant_item.context is None:
                self._text_window_update(assistant_window_id, 'No context used for this conversation.')

            else:
                self._text_window_update(assistant_window_id,
                                         "The context used for this conversation is:\n\n{}\n"
                                         .format(assistant_item.context))

            return

        # is the user trying to quit?
        elif prompt.lower() == '[quit]':
            self.destroy_assistant_window(assistant_window_id)
            return

        # get the assistant response
        assistant_response = assistant_item.send_query(prompt)

        # update the assistant window
        self._text_window_update(assistant_window_id, "A > " + assistant_response)

        # update the assistant window prompt
        # self._text_window_update_prompt(assistant_window_id, ' > ')

    def destroy_assistant_window(self, assistant_window_id: str):
        '''
        Destroys the assistant window
        '''

        # remove assistant window from the assistant windows dict
        if assistant_window_id in self.assistant_windows:
            del self.assistant_windows[assistant_window_id]

        # destroy the assistant window
        self.destroy_text_window(assistant_window_id)

    def _get_group_id_from_listbox(self, groups_listbox: tk.Listbox) -> str:
        '''
        Returns the group id of the selected group in the groups listbox

        :param groups_listbox:
        :return:
        '''

        return groups_listbox.get(tk.ANCHOR).strip().lower()

    def _get_selected_group_id(self, t_window_id: str = None, groups_listbox: tk.Listbox = None) \
            -> str or bool or None:
        '''
        Returns the group id of the selected group either from the selected groups dict or from in the group listbox
        :param t_window_id: the id of the transcription window (optional, if groups_listbox is not None)
        :param groups_listbox: the listbox with the groups (optional, if t_window_id is not None)
        :return: group id
        '''

        # this gets the currently selected group id
        # one thing to note is that in the listbox, we are using the group name
        # so this means that we are basically using the group name as a group id (after lowercasing it)
        # this is fine for now, but if things become more complex
        # we need to develop a mapping between the currently selected list item and the group id
        if t_window_id is not None:

            if t_window_id not in self.t_edit_obj.selected_groups:
                logger.error('No group is selected in transcription window {}'.format(t_window_id))
                return None

            if self.t_edit_obj.selected_groups[t_window_id] is None \
                    or len(self.t_edit_obj.selected_groups[t_window_id]) == 0:
                return None

            # get the selected group id from the selected groups dict
            group_id = self.t_edit_obj.selected_groups[t_window_id][0]

        elif groups_listbox is not None:
            # get the selected group id from the listbox
            group_id = self._get_group_id_from_listbox(groups_listbox)

        else:
            logger.error('No transcription window id or groups listbox was provided. Aborting.')
            return False

        return group_id.strip().lower()

    def on_group_update_press(self, t_window_id: str, t_group_window_id: str, group_id: str = None,
                              groups_listbox: tk.Listbox = None):
        '''
        Do stuff and update the group data in the transcription file,
        but only with the update_only_data (everything else will be left untouched in the group dict)
        :param t_window_id:
        :param t_group_window_id:
        :param group_id:
        :param groups_listbox:
        :return:
        '''

        # get the fields from the group window
        # (we're only need the group notes, and we'll update the time intervals based on the selected segments later)
        form_update_data = self._get_form_data(t_group_window_id, inputs=['group_notes'])

        # set the update data correctly
        # (we're using group_notes as an input name, but need notes for the dict)
        update_data = {'notes': form_update_data['group_notes'].strip()}

        # if group_id is None, get it from the listbox
        if group_id is None and groups_listbox is not None:

            # this gets the currently selected group id based on the selected group name
            group_id = self._get_selected_group_id(t_window_id=t_window_id)

            if group_id is None or not group_id:
                logger.debug('No group is selected in transcription window {}'.format(t_window_id))
                return False

        elif group_id is None and groups_listbox is None:
            logger.debug('No group id or group listbox was not provided')
            return False

        # get the current group data from the group window dict
        if t_window_id in self.t_edit_obj.transcript_groups \
                and group_id in self.t_edit_obj.transcript_groups[t_window_id]:

            # get the current group data
            group_data = self.t_edit_obj.transcript_groups[t_window_id][group_id]

            # update the current group data with the update_data
            group_data.update(update_data)

            # get the selected segments for the group
            segments_for_group = list(self.t_edit_obj.selected_segments[t_window_id].values())

            # get the transcription file path from the window transcription paths dict
            if t_window_id in self.t_edit_obj.transcription_file_paths:

                transcription_file_path = self.t_edit_obj.transcription_file_paths[t_window_id]

                # save the group data to the transcription file
                # save_return = self.toolkit_ops_obj.t_groups_obj\
                #                .save_transcript_groups(transcription_file_path=transcription_file_path,
                #                                         transcript_groups=group_update_data,
                #                                         group_id=group_id)

                # save the segments to the transcription file
                save_return = self.toolkit_ops_obj.t_groups_obj \
                    .save_segments_as_group_in_transcription_file(
                    transcription_file_path=transcription_file_path,
                    segments=segments_for_group,
                    group_name=group_data['name'],
                    group_notes=group_data['notes'],
                    existing_transcript_groups=self.t_edit_obj.transcript_groups[t_window_id],
                    overwrite_existing=True)

                if not save_return:
                    logger.error('Could not save group {} data to transcription file {}'
                                 .format(group_id, transcription_file_path))
                    return False

                else:
                    logger.debug('Group {} data updated in transcription file {}'
                                 .format(group_id, transcription_file_path))

                    # replace the group data in the window dict with the updated data
                    self.t_edit_obj.transcript_groups[t_window_id] = save_return

                    logger.info('Group updated')

                return save_return

            else:
                logger.error('No transcription file path was found for the current window id')

        return False

    def on_group_delete_press(self, t_window_id: str, t_group_window_id: str, group_id: str = None,
                              groups_listbox: tk.Listbox = None):
        '''
        Do stuff when the delete group button is pressed:
        this will delete the group from the transcription data
        and update the transcription groups window with the remaining groups

        :param t_window_id:
        :param t_group_window_id:
        :param group_id:
        :param groups_listbox:
        :return:
        '''

        # if group_id is None, get it from the listbox
        if group_id is None and groups_listbox is not None:

            group_id = self._get_selected_group_id(t_window_id=t_window_id)

        else:
            logger.debug('No group id or group listbox was provided')
            return False

        # delete the group from the transcription data
        # (by passing the transcription window id and the group id we're also updating the group window)
        self.t_edit_obj.delete_group(t_window_id, group_id,
                                     t_group_window_id=t_group_window_id, groups_listbox=groups_listbox)

    def on_group_press(self, e, t_window_id: str, t_group_window_id: str, group_id: str = None,
                       groups_listbox: tk.Listbox = None):
        '''
        Do stuff when the user presses a group somewhere
        :param t_window_id:
        :param t_group_window_id:
        :param group_id: The group id (optional, if group_listbox is not None)
        :param groups_listbox: The tk element that contains the groups (optional, if group_id is not None)
        :return:
        '''

        # if group_id is None, get it from the listbox
        if group_id is None and groups_listbox is not None:

            group_id = self._get_group_id_from_listbox(groups_listbox=groups_listbox)

        else:
            logger.debug('No group id or group listbox was provided')
            return False

        # if the group id matches the group id in the selected group
        # it means that we are clicking on a group that was already selected
        # so, deselect the group and all the segments from the window
        if t_window_id in self.t_edit_obj.selected_groups \
                and group_id in self.t_edit_obj.selected_groups[t_window_id]:

            # empty the selected groups
            self.t_edit_obj.selected_groups[t_window_id] = []

            # clear the selected segments
            self.t_edit_obj.clear_selection(t_window_id)

            # clear the selection in the listbox
            groups_listbox.selection_clear(0, tk.END)

            # update the group window
            self.update_transcript_group_form(t_window_id, t_group_window_id, group_id=None)

            # hide the group_details_frame
            self._hide_group_details_frame(t_group_window_id)

        # otherwise it means that we want to select a group
        else:

            # create the selected groups for the transcription window if it doesn't exist
            if t_window_id not in self.t_edit_obj.selected_groups:
                self.t_edit_obj.selected_groups[t_window_id] = []

            # empty the selected groups (deactivate when multiple groups can be selected)
            self.t_edit_obj.selected_groups[t_window_id] = []

            # add the group to the currently selected groups
            self.t_edit_obj.selected_groups[t_window_id].append(group_id)

            # select the segments in the transcription window
            self.select_group_segments(t_window_id, group_id)

            # update the group window
            self.update_transcript_group_form(t_window_id, t_group_window_id, group_id)

            # show the group_details_frame
            self._show_group_details_frame(t_group_window_id)

        return True

    def select_group_segments(self, t_window_id: str, group_id: str, text_element: tk.Text = None):
        '''
        Select the segments in the transcription window according to the time_intervals in the group data
        :param t_window_id:
        :param group_id:
        :param text_element: The text element to select the segments in (optional)
        :return:
        '''

        # get the transcription group data
        # if it exists in the dict
        if t_window_id in self.t_edit_obj.transcript_groups \
                and group_id in self.t_edit_obj.transcript_groups[t_window_id]:

            group_data = self.t_edit_obj.transcript_groups[t_window_id][group_id]

            # get the time intervals
            if 'time_intervals' in group_data:
                time_intervals = group_data['time_intervals']

                # get the transcript segments
                if t_window_id in self.t_edit_obj.transcript_segments:
                    transcript_segments = self.t_edit_obj.transcript_segments[t_window_id]

                    # convert the time intervals to segments
                    group_segments = \
                        self.toolkit_ops_obj.time_intervals_to_transcript_segments(time_intervals, transcript_segments)

                    # if no text element was provided, get it from the transcription window
                    if text_element is None:
                        text_element = self.t_edit_obj.get_transcription_window_text_element(t_window_id)

                        # now clear the selection
                        self.t_edit_obj.clear_selection(t_window_id)

                        group_lines = []

                        # go through the segments and get their line numbers
                        for segment in group_segments:
                            # get the line number
                            group_lines.append(self.t_edit_obj.segment_id_to_line(t_window_id, segment['id']))

                        # and select the segments
                        self.t_edit_obj.segment_to_selection(t_window_id, text_element=text_element, line=group_lines)

                        return True

        # if the above fails, just return False
        return False

    def update_transcript_group_form(self, t_window_id: str, t_group_window_id: str, group_id: str or None):
        '''
        This updates the transcript group form with the data stored in the transcript_groups dict
        :param t_window_id: the id of the transcription window (needed to get the groups data)
        :param t_group_window_id: the id of the group window
        :param group_id: the id of the group to pull data from
        :return:
        '''

        # initialize the group data that dict that will be pass to the populate function
        update_group_data = {'group_notes': ''}

        # get the transcription group data
        # if it exists in the dict
        if group_id is not None and \
                t_window_id in self.t_edit_obj.transcript_groups \
                and group_id in self.t_edit_obj.transcript_groups[t_window_id]:
            # get the group data
            group_data = self.t_edit_obj.transcript_groups[t_window_id][group_id]

            # use the group data to populate the group form (just the notes here)
            update_group_data = {'group_notes': group_data['notes']}

        # populate the transcription group form
        self._populate_form_data(window_id=t_group_window_id, form_data=update_group_data)

    def _get_form_data(self, window_id: str, inputs: list = None) -> dict or bool:
        '''
        This gets the data from the form fields
        :param window_id:
        :param fields: The fields to get the data from (optional)
        :return: A dict with the data from the form fields
        '''

        # keep track of the elements that we have found
        found_inputs = []

        # keep track of the data that we have found
        form_data = {}

        for key in inputs:
            form_data[key] = None

        # the window needs to be registered in the windows dict
        if window_id not in self.windows:
            logger.error('The window id provided was not found in the windows dict')
            return False

        # search through all the elements in the window until we find the elements that we need
        # but since we are expecting the forms to be inside a frame, we'll only look at the second level
        for child in self.windows[window_id].winfo_children():

            # go another level deeper, since we are expecting the forms to be inside a frame
            if len(child.winfo_children()) > 0:

                for child2 in child.winfo_children():

                    # if the child2 name is in the form_input_names dict
                    if child2.winfo_name() in inputs:

                        # add the input to the found inputs list
                        found_inputs.append(child2.winfo_name())

                        # get the tkinter value of the element depending on the type
                        if child2.winfo_class() == 'Entry':

                            # get the value of the entry
                            form_data[child2.winfo_name()] = child2.get()

                        elif child2.winfo_class() == 'Text':

                            # get the whole value of the text input
                            form_data[child2.winfo_name()] = child2.get(0.0, tk.END)

                        else:
                            # this is to let us know that we need to create a procedure for this input type
                            logger.error('The tkinter input type {} for {} is not supported'
                                         .format(child2.winfo_class(), child2.winfo_name()))

        # if we didn't find all the inputs, log it
        if len(found_inputs) != len(form_data):
            logger.debug('Not all requested form inputs were not found in the window')

        return form_data

    def _populate_form_data(self, window_id, form_data):
        '''
        This populates the form data in the form with the data provided

        It will automatically search for the elements in the window and if the elements are found, it will populate them

        form_data needs to be a dict with the element names as keys and the values used to populate the elements

        :param window_id:
        :param form_data:
        :return:
        '''

        # initialize empty inputs until we find them
        form_input_names = {}

        # keep track of the elements that we have found
        all_inputs = list(form_data.keys())
        found_inputs = []

        for key in form_data:
            form_input_names[key] = None

        # the window needs to be registered in the windows dict
        if window_id not in self.windows:
            logger.error('The window id provided was not found in the windows dict')
            return False

        # search through all the elements in the window until we find the elements that we need
        # but since we are expecting the forms to be inside a frame, we'll only look at the second level
        for child in self.windows[window_id].winfo_children():

            # go another level deeper, since we are expecting the forms to be inside a frame
            if len(child.winfo_children()) > 0:

                for child2 in child.winfo_children():

                    # if the child2 name is in the form_input_names dict
                    if child2.winfo_name() in form_input_names:
                        form_input_names[key] = child2

                        # add the input to the found inputs list
                        found_inputs.append(child2.winfo_name())

                        # update the input based on the tkinter input type
                        if child2.winfo_class() == 'Entry':

                            # clear the input
                            child2.delete(0, tk.END)

                            # then populate it with the data
                            form_input_names[key].insert(0.0, form_data[key])

                        elif child2.winfo_class() == 'Text':

                            # clear the text input
                            form_input_names[key].delete(0.0, tk.END)

                            # then populate it with the data
                            form_input_names[key].insert(0.0, form_data[key])

                        else:
                            # this is to let us know that we need to create a procedure for this input type
                            logger.error('The tkinter input type {} for {} is not supported'
                                         .format(child2.winfo_class(), child2.winfo_name()))

        # if we didn't find all the inputs
        if len(found_inputs) != len(all_inputs):
            # get the inputs that we didn't find
            missing_inputs = list(set(all_inputs) - set(found_inputs))

            # log the missing inputs
            # this is to let us know that maybe we need to name the inputs in the form so they're found
            # this could also happen if, for instance, the input is not in the window frame
            logger.error('The following inputs were not found while updating window {}: {}'
                         .format(window_id, missing_inputs))

    def update_transcript_groups_window(self, t_window_id: str, t_group_window_id: str = None,
                                        groups_listbox: tk.Listbox = None):

        # if the group window id is not provided, assume this:
        if t_group_window_id is None:
            t_group_window_id = t_window_id + '_transcript_groups'

        # we'll definitely need the groups notes input
        group_details_frame = None

        # we need a valid groups window id to continue
        if t_group_window_id not in self.windows:
            return False

        # search through all the elements in the window until we find some elements that we might need
        for child in self.windows[t_group_window_id].winfo_children():

            # go another level deeper, since we are expecting the forms to be inside a frame
            if len(child.winfo_children()) > 0:

                for child2 in child.winfo_children():

                    # if no groups listbox was provided remember but we found one, remember it
                    if child2.winfo_name() == 'groups_listbox' \
                            and groups_listbox is None and t_group_window_id in self.windows:
                        groups_listbox = child2

                        # if we found the group notes input, break out from this loop
                        break

            if child.winfo_name() == 'group_details_frame':
                group_details_frame = child

        # if we haven't found the groups notes input or groups listbox, return False
        if group_details_frame is None or groups_listbox is None:
            return False

        # clear the listbox
        groups_listbox.delete(0, tk.END)

        # get the groups data
        if t_window_id in self.t_edit_obj.transcript_groups:
            groups_data = self.t_edit_obj.transcript_groups[t_window_id]

            # create a list with all the group names from the group data
            # the group names are inside the group data dict
            # and sort them alphabetically
            group_names = sorted([group_data['name'] for group_id, group_data in groups_data.items()])

            # then add the transcript groups to the listbox
            for group_name in group_names:
                groups_listbox.insert(END, group_name)

        # clear all the group form inputs
        # but only if no group or more than a group is selected
        if t_window_id not in self.t_edit_obj.selected_groups \
                or len(self.t_edit_obj.selected_groups[t_window_id]) != 1:

            update_group_data = {'group_notes': ''}

            # populate the transcription group form
            self._populate_form_data(window_id=t_group_window_id, form_data=update_group_data)

            self._hide_group_details_frame(t_group_window_id, group_details_frame)

        elif t_window_id in self.t_edit_obj.selected_groups \
                and len(self.t_edit_obj.selected_groups[t_window_id]) == 1:

            self._show_group_details_frame(t_group_window_id, group_details_frame)

        # now, if there are any selected groups for this window
        if t_window_id in self.t_edit_obj.selected_groups:

            # select the groups in the listbox
            for group_name in self.t_edit_obj.selected_groups[t_window_id]:
                groups_listbox.selection_set(group_names.index(group_name))

                # select the segments in the transcription window
                # - if multiple groups are selected, this will select the segments from the last group
                # - so if we want to implement the multi-group selection in the future, we'll need to change this!
                self.select_group_segments(t_window_id, group_name)

        return True

    def _get_group_details_frame(self, t_group_window_id: str):

        # we need a valid groups window id to continue
        if t_group_window_id not in self.windows:
            return False

        # search through all the elements in the window until we find some elements that we might need
        for child in self.windows[t_group_window_id].winfo_children():

            if child.winfo_name() == 'group_details_frame':
                return child

    def _show_group_details_frame(self, t_group_window_id: str, group_details_frame: tk.Frame = None):

        if group_details_frame is None:
            group_details_frame = self._get_group_details_frame(t_group_window_id)

        # or show the group notes label and text input
        group_details_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.X, **self.paddings, anchor=tk.S)

    def _hide_group_details_frame(self, t_group_window_id: str, group_details_frame: tk.Frame = None):

        if group_details_frame is None:
            group_details_frame = self._get_group_details_frame(t_group_window_id)

        # now hide the group notes label and text input
        group_details_frame.pack_forget()

    def destroy_transcript_groups_window(self, window_id: str = None):

        # call the default destroy window function
        self.destroy_window_(parent_element=self.windows, window_id=window_id)

    def destroy_advanced_search_window(self, window_id: str = None):

        logger.debug('Deleting caches of search window {}'.format(window_id))

        # first remove the caches associated with the advanced search window
        if window_id in self.toolkit_ops_obj.t_search_obj.search_corpuses:
            del self.toolkit_ops_obj.t_search_obj.search_corpuses[window_id]

        if window_id in self.toolkit_ops_obj.t_search_obj.search_embeddings:
            del self.toolkit_ops_obj.t_search_obj.search_embeddings[window_id]

        # call the default destroy window function
        self.destroy_text_window(window_id=window_id)

    def open_transcript_groups_window(self, transcription_window_id, transcription_name=None):

        # the transcript groups window id
        transcript_groups_window_id = '{}_transcript_groups'.format(transcription_window_id)

        # the transcript groups window title
        if transcription_name:
            transcript_groups_window_title = 'Groups - {}'.format(transcription_name)
        else:
            transcript_groups_window_title = 'Groups'

        # create a window for the transcript groups if one doesn't already exist
        if self.create_or_open_window(parent_element=self.windows[transcription_window_id],
                                      window_id=transcript_groups_window_id,
                                      title=transcript_groups_window_title, resizable=True,
                                      close_action=
                                      lambda: self.destroy_transcript_groups_window(transcript_groups_window_id)
                                      ):

            # the current transcript groups window object
            current_transcript_groups_window = self.windows[transcript_groups_window_id]

            # use the transcript groups stored in the transcription window
            if transcription_window_id in self.t_edit_obj.transcript_groups:

                transcript_groups = self.t_edit_obj.transcript_groups[transcription_window_id]

            # if they don't exist, create an empty dict
            else:
                self.t_edit_obj.transcript_groups[transcription_window_id] = {}
                transcript_groups = {}

            elements_width = 30

            # add the frame to hold the transcript groups
            transcript_groups_frame = tk.Frame(self.windows[transcript_groups_window_id])
            transcript_groups_frame.pack(expand=True, fill=tk.BOTH, **self.paddings)

            # add a listbox that holds all the transcript groups
            groups_listbox = Listbox(transcript_groups_frame, name="groups_listbox",
                                     width=elements_width, height=10, selectmode='single', exportselection=False)
            groups_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

            # add a scrollbar to the listbox
            scrollbar = Scrollbar(transcript_groups_frame, orient="vertical", **self.scrollbar_settings)
            scrollbar.config(command=groups_listbox.yview)
            scrollbar.pack(side=tk.RIGHT, fill='y')

            # configure the listbox to use the scrollbar
            groups_listbox.config(yscrollcommand=scrollbar.set)

            # add a frame to hold the transcript group details under the listbox
            transcript_group_details_frame = tk.Frame(current_transcript_groups_window, name='group_details_frame')

            # do not pack the frame yet, it will be packed when a group is selected (in the update function)
            # transcript_group_details_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.X, **self.paddings, anchor=tk.S)

            # inside the transcript group details frame, add the inputs
            # for the transcript group name, notes and some buttons

            # the transcript group notes text box
            Label(transcript_group_details_frame, text="Group Notes:", anchor='nw') \
                .pack(side=tk.TOP, expand=True, fill=tk.X)
            transcript_group_notes = tk.StringVar()
            transcript_group_notes_input = Text(transcript_group_details_frame, name='group_notes',
                                                width=elements_width, height=5, wrap=tk.WORD)
            transcript_group_notes_input.pack(side=tk.TOP, expand=True, fill=tk.X, anchor='nw')

            # update the transcript group notes variable when the text box is changed
            # transcript_group_notes_input.bind('<KeyRelease>', lambda e: transcript

            # add a frame to hold the buttons
            transcript_group_buttons_frame = tk.Frame(transcript_group_details_frame)
            transcript_group_buttons_frame.pack(side=tk.TOP, expand=True, fill=tk.X)

            # the transcript group update button
            transcript_group_update = tk.Button(transcript_group_buttons_frame, text='Save',
                                                command=lambda

                                                    transcription_window_id=transcription_window_id,
                                                    transcript_groups_window_id=transcript_groups_window_id,
                                                    group_notes=transcript_group_notes_input.get(0.0, tk.END),
                                                    groups_listbox=groups_listbox:
                                                self.on_group_update_press(
                                                    transcription_window_id,
                                                    transcript_groups_window_id,
                                                    groups_listbox=groups_listbox
                                                ))
            transcript_group_update.pack(side=tk.LEFT)

            # the transcript group delete button
            transcript_group_delete = tk.Button(transcript_group_buttons_frame, text="Delete",
                                                command=lambda
                                                    transcription_window_id=transcription_window_id,
                                                    transcript_groups_window_id=transcript_groups_window_id,
                                                    groups_listbox=groups_listbox:
                                                self.on_group_delete_press(transcription_window_id,
                                                                           transcript_groups_window_id,
                                                                           groups_listbox=groups_listbox))
            transcript_group_delete.pack(side=tk.RIGHT)

            # when a user selects a transcript group from the listbox, update the transcript group details
            groups_listbox.bind('<<ListboxSelect>>',
                                lambda e,
                                       transcription_window_id=transcription_window_id,
                                       transcript_groups_window_id=transcript_groups_window_id,
                                       groups_listbox=groups_listbox:
                                self.on_group_press(e, t_window_id=transcription_window_id,
                                                    t_group_window_id=transcript_groups_window_id,
                                                    groups_listbox=groups_listbox))

            # place the transcript groups window on top of the transcription window
            self.windows[transcript_groups_window_id].attributes('-topmost', 'true')
            self.windows[transcript_groups_window_id].attributes('-topmost', 'false')
            self.windows[transcript_groups_window_id].lift()

            # and then call the update function to fill the groups listbox up
            self.update_transcript_groups_window(t_window_id=transcription_window_id,
                                                 t_group_window_id=transcript_groups_window_id,
                                                 groups_listbox=groups_listbox)

    def open_file_in_os(self, file_path):
        '''
        Opens any file in the default program for the OS (works for Windows, Mac and Linux)
        :param file_path:
        :return:
        '''

        # if the file exists
        if os.path.exists(file_path):
            # open the file in the default program
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', file_path], close_fds=True)
            else:
                try:
                    subprocess.Popen(['xdg-open', file_path])
                except OSError:
                    logger.error('Please open the file manually on your system: {}'.format(file_path))
        else:
            # otherwise, show an error
            messagebox.showerror('Error', 'File not found: {}'.format(file_path))

    def ask_for_target_dir(self, title=None, target_dir=None):

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

    def ask_for_target_file(self, filetypes=[("Audio files", ".mov .mp4 .wav .mp3")], target_dir=None, multiple=False):
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
            logger.error(message_log)

        elif type == 'info':
            messagebox.showinfo(message=message, **options)
            logger.info(message_log)

        elif type == 'warning':
            messagebox.showwarning(message=message, **options)
            logger.warning(message_log)

        # if no type was passed, just log the message
        else:
            logger.debug(message_log)

def run_gui(toolkit_ops_obj, stAI):

    # initialize GUI
    app_UI = toolkit_UI(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    # connect app UI to operations object
    toolkit_ops_obj.toolkit_UI_obj = app_UI

    # create the main window
    app_UI.create_main_window()
