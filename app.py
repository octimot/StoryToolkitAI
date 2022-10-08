
import os
import platform
import time
import json
# import sys

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter import *

import hashlib
import codecs

from threading import *

import mots_resolve

import torch
import whisper

import webbrowser

'''
To install whisper on MacOS use brew and pip:

brew install rust
pip install git+https://github.com/openai/whisper.git

'''


# define a global target dir so we remember where we chose to save stuff last time when asked
# but start with the user's home directory
initial_target_dir = os.path.expanduser("~")

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

            # search results indexes stored here
            # we're making it a dict so that we can store result indexes for each window individually
            self.search_result_indexes = {}

            # when searching for text, you may want the user to cycle through the results, so this keep track
            # keeps track on which search result is the user currently on (in each transcript window)
            self.search_result_pos = {}

            # to keep track of what is being searched on each window
            self.search_strings = {}

            # to store the transcript segments of each window,
            # including their start + end times and who knows what else?!
            self.transcript_segments = {}

            # selected transcript segments of each window including their start and end times
            self.selected_segments = {}

        def assign_to_timeline(self):
            '''
            Used to assign the transcript to the current opened timeline in Resolve via StoryToolkitAI object
            :return:
            '''

            # @todo
            #if self.stAI is not None:
            #    self.stAI.save_project_settings()


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
                if current_pos < len(self.search_result_indexes[window_id])-1:

                    # add 1 to the current result position
                    current_pos = self.search_result_pos[window_id] = current_pos+1

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

        def select_text_lines(self, event, text_element=None, window_id=None):
            '''
            Used to trigger events when user clicks on the transcript text
            :return:
            '''

            if text_element is None or window_id is None:
                return False

            index = text_element.index("@%s,%s" % (event.x, event.y))
            line, char = index.split(".")
            text_element.tag_add("l_selected", "{}.0".format(line), "{}.end+1c".format(line))
            text_element.tag_config('l_selected', background=self.toolkit_UI_obj.resolve_theme_colors['superblack'])

            #print("you clicked line %s" % line)
            #print(self.transcript_segments[window_id][int(line)-1])



    def __init__(self, toolkit_ops_obj=None, stAI=None, warn_message=None):

        # make a reference to toolkit ops obj
        self.toolkit_ops_obj = toolkit_ops_obj

        # make a reference to StoryToolkitAI obj
        self.stAI = stAI

        # initialize tkinter as the main GUI
        self.root = tk.Tk()

        # initialize transcript edit object
        self.t_edit_obj = self.TranscriptEdit(stAI=self.stAI, toolkit_UI_obj=self, toolkit_ops_obj=self.toolkit_ops_obj)

        # show any info messages
        if warn_message is not None:
            self.notify_via_messagebox(title='Update available',
                                                 message=warn_message,
                                                 type='warn'
                                                 )

        # keep all the window references here to find them easy by window_id
        self.windows = {}

        # set some UI styling here
        self.paddings = {'padx': 10, 'pady': 10}
        self.button_size = {'width': 150, 'height': 50}
        self.list_paddings = {'padx':3, 'pady': 3}


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

        # use this variable to remember if the user said it's ok that resolve is not available to continue a process
        self.no_resolve_ok = False

        # create the main window
        self.create_main_window()

    class main_window:
        pass

    def _create_or_open_window(self, parent_element=None, window_id=None, title=None, resizable=False):

        # if the window is already opened somewhere, do this
        if window_id in self.windows:

            # bring the window to the top
            # self.windows[window_id].attributes('-topmost', 1)
            # self.windows[window_id].attributes('-topmost', 0)
            self.windows[window_id].lift()

            # then focus on it
            self.windows[window_id].focus_set()

        else:

            # create a new window
            self.windows[window_id] = Toplevel(self.root)

            # bring the transcription window to top
            #self.windows[window_id].attributes('-topmost', 'true')

            # set the window title
            self.windows[window_id].title(title)

            # is it resizable?
            if not resizable:
                self.windows[window_id].resizable(False, False)

            # what happens when the user closes this window
            self.windows[window_id].protocol("WM_DELETE_WINDOW", lambda: self.destroy_window_(self.windows, window_id))

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

        # if resolve is connected and the resolve buttons are not visible
        else:
            # show resolve buttons
            if self.show_main_window_frame('resolve_buttons_frame'):
                # but hide other buttons so we can place them back below the resolve buttons frame
                self.hide_main_window_frame('other_buttons_frame')

        # now show the other buttons too if they're not visible already
        self.show_main_window_frame('other_buttons_frame')

        # refresh main window after 500 ms
        #self.root.after(1500, self.show_button())

        return

    def create_main_window(self):
        '''
        Creates the main GUI window using Tkinter
        :return:
        '''

        # any frames stored here in the future will be considered visible
        self.main_window_visible_frames = []

        # set the window title
        self.root.title("StoryToolkitAI v{}".format(stAI.__version__))

        # retrieve toolkit_obs object
        toolkit_ops_obj = self.toolkit_ops_obj

        # set the window size
        #self.root.geometry("350x440")

        # create the frame that will hold the resolve buttons
        self.main_window.resolve_buttons_frame = tk.Frame(self.root)

        # create the frame that will hold the other buttons
        self.main_window.other_buttons_frame = tk.Frame(self.root)

        # draw buttons

        # label1 = tk.Label(frame, text="Resolve Operations", anchor='w')
        # label1.grid(row=0, column=1, sticky='w', padx=10, pady=10)

        # resolve buttons frame row 1
        self.main_window.button1 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Copy Timeline\nMarkers to Same Clip",
                            command=lambda: execute_operation('copy_markers_timeline_to_clip', self))
        self.main_window.button1.grid(row=1, column=1, **self.paddings)

        self.main_window.button2 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Copy Clip Markers\nto Same Timeline",
                            command=lambda: execute_operation('copy_markers_clip_to_timeline', self))
        self.main_window.button2.grid(row=1, column=2, **self.paddings)

        # resolve buttons frame row 2
        self.main_window.button3 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Render Markers\nto Stills",
                            command=lambda: execute_operation('render_markers_to_stills', self))
        self.main_window.button3.grid(row=2, column=1, **self.paddings)

        self.main_window.button4 = tk.Button(self.main_window.resolve_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Render Markers\nto Clips",
                            command=lambda: execute_operation('render_markers_to_clips', self))
        self.main_window.button4.grid(row=2, column=2, **self.paddings)

        # Other Frame Row 1
        self.main_window.button5 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Transcribe\nTimeline",
                            command=lambda: toolkit_ops_obj.prepare_transcription_file(toolkit_UI_obj=self))
        self.main_window.button5.grid(row=1, column=1, **self.paddings)

        self.main_window.button6 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Translate\nTimeline to English", command=lambda: toolkit_ops_obj.prepare_transcription_file(toolkit_UI_obj=self, translate=True))
        self.main_window.button6.grid(row=1, column=2, **self.paddings)

        self.main_window.button7 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Open\nTranscript", command=lambda: self.open_transcript())
        self.main_window.button7.grid(row=2, column=1, **self.paddings)

        self.main_window.button8 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Open\nTranscription Log", command=lambda: self.open_transcription_log_window())
        self.main_window.button8.grid(row=2, column=2, **self.paddings)

        #self.main_window.link2 = Label(self.main_window.other_buttons_frame, text="project home", font=("Courier", 8), fg='#1F1F1F', cursor="hand2", anchor='s')
        #self.main_window.link2.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky='s')
        #self.main_window.link2.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/octimot/StoryToolkitAI"))

        # Other Frame row 2 (disabled for now)
        #self.main_window.button7 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Transcribe\nDuration Markers")
        # self.main_window.button7.grid(row=4, column=1, **self.paddings)
        #self.main_window.button8 = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Translate\nDuration Markers to English")
        # self.main_window.button8.grid(row=4, column=1, **self.paddings)


        #self.main_window.button_test = tk.Button(self.main_window.other_buttons_frame, **self.blank_img_button_settings, **self.button_size, text="Test",
        #                        command=lambda: self.open_transcription_window())
        #self.main_window.button_test.grid(row=5, column=2, **self.paddings)



        # Make the window resizable false
        self.root.resizable(False, False)

        # poll resolve after 500ms
        self.root.after(500, poll_resolve_data(self))

        # refresh main window after 500 ms
        self.root.after(500, self.update_main_window())

        print("Starting StoryToolkitAI GUI")
        self.root.mainloop()

        return

    def create_transcription_settings_window(self, title="Transcription Settings",
                                             audio_file_path=None, name=None, translate=None):

        if self.toolkit_ops_obj is None:
            print('Aborting. A toolkit operations object is needed to continue.')
            return False

        # WORK IN PROGRESS

        print(audio_file_path)

        self.transcription_settings_window = Toplevel(self.root)

        #self.transcription_settings_window.attributes('-topmost', 'true')

        self.transcription_settings_window.title(title)

        self.transcription_settings_window.resizable(False, False)

        file_form_frame = tk.Frame(self.transcription_settings_window)
        file_form_frame.pack()

        # File items start here

        # Name
        Label(file_form_frame, text="Timeline name", anchor='w').grid(row=1, column=1, sticky='w', **self.paddings)
        entry_name = Entry(file_form_frame)
        entry_name.grid(row=1, column=2, sticky='w', **self.paddings)
        entry_name.insert(0, name)


        # File path
        Label(file_form_frame, text="File path", anchor='w').grid(row=2, column=1, sticky='w', **self.paddings)
        entry_file_path = Entry(file_form_frame)
        entry_file_path.grid(row=2, column=2, sticky='w', **self.paddings)
        entry_file_path.insert(END, audio_file_path)


        # Translate?
        Label(file_form_frame, text="Translate", anchor='w').grid(row=3, column=1, sticky='w', **self.paddings)
        entry_translate = OptionMenu(master=file_form_frame, variable=translate, values={'True': 'x', 'False':'y'})
        entry_translate.grid(row=3, column=2, sticky='w', **self.paddings)




        # Transcription config items start here

        t_form_frame = tk.Frame(self.transcription_settings_window)
        t_form_frame.pack()

        # A Label widget to show in toplevel
        Label(t_form_frame, text="Transcription Model").grid(row=1, column=1, **self.paddings)

        # A dropdown with showing all the available whisper models
        self.selected_model = StringVar(t_form_frame)
        self.selected_model.set("medium")
        OptionMenu(t_form_frame, self.selected_model, *whisper.available_models()).grid(row=1, column=2, **self.paddings)

        #tokenizer.py Tokenizer LANGUAGES contains all the language list-  how to get it?

        # start transcription button
        self.start_button = tk.Button(t_form_frame, **self.blank_img_button_settings, **self.button_size,
                            text="Start",
                            command=lambda: toolkit_ops_obj.option_changed())
        self.start_button.grid(row=2, column=1, **self.paddings)

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

        # ask user which transcript to open
        transcription_json_file_path = self.ask_for_target_file(filetypes=[("Json files", "json")])

        # abort if user cancels
        if not transcription_json_file_path:
            return False

        # why not open the transcript in a transcription window?
        self.open_transcription_window(transcription_file_path=transcription_json_file_path, **options)

    def open_transcription_window(self, title=None, transcription_file_path=None, srt_file_path=None):

        if self.toolkit_ops_obj is None:
            self.stAI.log_print('Cannot open transcription window. A toolkit operations object is needed to continue.',
                                'error')
            return False

        # Note: most of the transcription window functions are stored in the TranscriptEdit class

        # only continue if the transcription path was passed and the file exists
        if transcription_file_path is None or os.path.exists(transcription_file_path) is False:
            return False

        # hash the url and use it as a unique id for the transcription window
        t_window_id = hashlib.md5(transcription_file_path.encode('utf-8')).hexdigest()

        # use the transcription file name without the extension as a window title title if a title wasn't passed
        if title is None:
            title = os.path.splitext(os.path.basename(transcription_file_path))[0]

        # create a window for the transcript if one doesn't already exist
        if(self._create_or_open_window(parent_element=self.root, window_id=t_window_id, title=title, resizable=True)):

            # create a header frame to hold stuff above the transcript text
            header_frame = tk.Frame(self.windows[t_window_id])
            header_frame.place(anchor='nw', relwidth=1)

            # THE MAIN TEXT ELEMENT
            # create a frame for the text element
            text_form_frame = tk.Frame(self.windows[t_window_id])
            text_form_frame.pack(pady=50)

            # check if the transcription json exists
            if os.path.exists(transcription_file_path):
                # now read the transcription
                with codecs.open(transcription_file_path, 'r', 'utf-8-sig') as json_file:
                    transcription_json = json.load(json_file)

            # does the json file actually contain transcript segments generated by whisper?
            if 'segments' in transcription_json:

                # set up the text element where we'll add the actual transcript
                text = Text(text_form_frame, font=('Courier', 16), width=45, height=30, padx=5, pady=5, wrap=tk.WORD)

                # we'll need to count segments soon
                segment_count = 0

                # use this to calculate the longest segment (but don't accept anything under 30)
                longest_segment_num_char = 30

                # initialize the segments list for later use
                # this should contain all the segments in the order they appear
                self.t_edit_obj.transcript_segments[t_window_id] = []

                # take each transcript segment
                for t_segment in transcription_json['segments']:

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
                        text.insert(END, t_segment['text'].strip()+' ')

                        # if this is the longest segment, keep that in mind
                        if len(t_segment['text']) > longest_segment_num_char:
                            longest_segment_num_char = len(t_segment['text'])

                        # get the text index of the last character of the new segment
                        new_segment_end = text.index("end-1c")

                        # keep in mind the segment start and end times of each segment
                        segment_start_time = t_segment['start']
                        end_start_time = t_segment['start']

                        # this works if we're aiming to move away from line based start_end times
                        # @todo move this to a more generalized approach, like the shift binding below
                        #   and get the start and end times of each segment via self.t_edit_obj.transcript_segments
                        tag_id = 'segment-'+str(segment_count)
                        text.tag_add(tag_id, new_segment_start, new_segment_end)
                        text.tag_config(tag_id)
                        text.tag_bind(tag_id, "<Button-1>", lambda e, segment_start_time=segment_start_time: toolkit_ops_obj.go_to_time(segment_start_time))

                        # for now, just add 2 new lines after each segment:
                        text.insert(END, '\n')

                # make the text read only
                # and take into consideration the longest segment to adjust the width of the window
                text.config(state=DISABLED, width=longest_segment_num_char)

                # set the top, in-between and bottom text spacing
                text.config(spacing1=0, spacing2=0.2, spacing3=5)



                # bind CMD+click events to the text:
                # on click, move playhead
                #if platform.system() == 'Darwin':
                #    text.bind("<Command-Button-1>", lambda e:
                #            self.t_edit_obj.select_text_lines(event=e, text_element=text, window_id=t_window_id))
                #else:
                #    text.bind("<Control-Button-1>", lambda e:
                #        self.t_edit_obj.select_text_lines(event=e, text_element=text, window_id=t_window_id))

                # bind shift click events to the text
                #text.bind("<Shift-Button-1>", lambda e:
                #        self.t_edit_obj.select_text_lines(event=e, text_element=text, window_id=t_window_id))

                # then show the text element
                text.pack()

                # create a footer frame that holds stuff on the bottom of the transcript window
                footer_frame = tk.Frame(self.windows[t_window_id])
                footer_frame.place(relwidth=1, anchor='sw', rely=1)

                #b_test = tk.Button(footer_frame, text='Search', command=lambda: search(),
                #               font=20, bg='white').grid(row=1, column=3, sticky='w', **self.paddings)

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

                # the find button
                # not really necessary due to <Return> bind above
                #find_button = Button(header_frame, text='Find')
                #find_button.pack(side=tk.LEFT, **self.paddings)
                #find_button.config(command= lambda text=text, t_window_id=t_window_id:
                #                  self.t_edit_obj.cycle_through_results(text_element=text, window_id=t_window_id))

                # KEEP ON TOP BUTTON
                on_top_button = tk.Button(header_frame, text="Keep on top")
                # add the command function here
                on_top_button.config(command= lambda on_top_button=on_top_button, t_window_id=t_window_id:
                                                self.window_on_top_button(button=on_top_button, window_id=t_window_id)
                                            )
                on_top_button.pack(side=tk.RIGHT, **self.paddings, anchor='e')

                # keep the transcript window on top or not according to the config
                # and also update the initial text on the respective button
                self.window_on_top_button(button=on_top_button,
                                          window_id=t_window_id,
                                          on_top=stAI.get_app_setting('transcripts_always_on_top', default_if_none=True)
                                          )



                # IMPORT SRT BUTTON
                if srt_file_path:
                    import_srt_button = tk.Button(footer_frame,
                                                  text="Import SRT into Bin",
                                                  command=lambda: mots_resolve.import_media(srt_file_path)
                                                  )
                    import_srt_button.grid(row=1, column=3, sticky='w', **self.paddings)



            # if no transcript was found in the json file, alert the user
            else:
                not_a_transcription_message = 'The file {} isn\'t a transcript.'.format(os.path.basename(transcription_file_path))

                self.notify_via_messagebox(title='Not a transcript file',
                                           message=not_a_transcription_message,
                                           type='warn'
                                           )
                self.destroy_window_(self.windows, t_window_id)

    def update_transcription_log_window(self):

        # only do this if the transcription window exists
        # and if the log exists
        if self.toolkit_ops_obj.transcription_log and 't_log' in self.windows:

            # first destroy anything that the window might have held
            list = self.windows['t_log'].pack_slaves()
            for l in list:
                l.destroy()

            # create a frame to hold all the log items in the window
            log_frame = tk.Frame(self.windows['t_log'])
            log_frame.pack()

            # show all the transcription items in the transcription log
            num = 0
            for t_item_id, t_item in self.toolkit_ops_obj.transcription_log.items():

                num = num + 1

                if 'name' not in t_item:
                    t_item['name'] = 'Unknown'

                label_name = Label(log_frame, text=t_item['name'], anchor='w', width=35)
                label_name.grid(row=num, column=1, **self.list_paddings, sticky='w')

                if 'status' not in t_item:
                    t_item['status'] = ''

                label_status = Label(log_frame, text=t_item['status'], anchor='w', width=15)
                label_status.grid(row=num, column=2, **self.list_paddings, sticky='w')

                # make the label clickable as soon as we have a file path for it in the log
                if 'json_file_path' in t_item and 'srt_file_path' in t_item\
                        and t_item['json_file_path'] != '' and t_item['srt_file_path'] != '':

                    # first assign variables to pass it easily to lambda
                    json_file_path = t_item['json_file_path']
                    srt_file_path = t_item['srt_file_path']
                    name = t_item['name']

                    # now bind the button event
                    # the lambda needs all this code to "freeze" the current state of the variables
                    # otherwise it's going to only use the last value of the variable in the for loop
                    # for eg. instead of having 3 different value for the variable "name",
                    # lambda will only use the last value in the for loop
                    label_name.bind("<Button-1>",
                                    lambda e,
                                           json_file_path=json_file_path,
                                           srt_file_path=srt_file_path,
                                           name=name:
                                        self.open_transcription_window(title=name,
                                                                       transcription_file_path=json_file_path,
                                                                       srt_file_path=srt_file_path)
                                    )
                    label_status.bind("<Button-1>",
                                    lambda e,
                                           json_file_path=json_file_path,
                                           srt_file_path=srt_file_path,
                                           name=name:
                                        self.open_transcription_window(title=name,
                                                                       transcription_file_path=json_file_path,
                                                                       srt_file_path=srt_file_path)
                                      )

    def open_transcription_log_window(self):

        # create a window for the transcription log if one doesn't already exist
        if(self._create_or_open_window(parent_element=self.root,
                                       window_id='t_log', title='Transcription Log', resizable=True)):

            # and then call the update function to fill the window up
            self.update_transcription_log_window()

            return True

    def open_new_window(self, title=None):

        # Toplevel object which will
        # be treated as a new window
        newWindow = Toplevel(self.root)

        # sets the title of the
        # Toplevel widget
        newWindow.title(title)

        # sets the geometry of toplevel
        newWindow.geometry("200x200")

        # A Label widget to show in toplevel
        Label(newWindow,
              text="This is a new window").pack()

        # Dropdown 1
        variable = StringVar(newWindow)
        variable.set("one")  # default value

        w = OptionMenu(newWindow, variable, "one", "two", "three").pack()

        # Dropdown 2
        variable2 = StringVar(newWindow)
        variable2.set("one")  # default value

        w2 = OptionMenu(newWindow, variable2, "one", "two", "three").pack()

    def ask_for_target_dir(self, title=None):
        global initial_target_dir

        # put the UI on top
        #self.root.wm_attributes('-topmost', True)
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

    def ask_for_target_file(self, filetypes=[("Audio files", ".mp4 .wav .mp3")]):
        global initial_target_dir

        # put the UI on top
        #self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog which file to use
        target_file = filedialog.askopenfilename(title="Choose a file", initialdir=initial_target_dir,
                                                 filetypes=filetypes, multiple=False)

        # what happens if the user cancels
        if not target_file:
            return False

        # remember what the user selected for next time
        initial_target_dir = os.path.dirname(target_file)

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
        :return:
        """

        # log and print to console first
        self.stAI.log_print(debug_message)

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

        # first print and log the message
        self.stAI.log_print(message_log)

        # alert the user using the messagebox according to the type
        if type == 'error':
            messagebox.showerror(message=message, **options)

        elif type == 'info':
            messagebox.showinfo(message=message, **options)

        elif type == 'warn':
            messagebox.showwarning(message=message, **options)



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

        # if the whisper device is set to cuda
        if self.whisper_device in ['cuda', 'CUDA', 'gpu', 'GPU']:
            # use CUDA if available
            if torch.cuda.is_available():
                device = torch.device('cuda')
            # or let the user know that cuda is not available and switch to cpu
            else:
                stAI.log_print('CUDA not available. Switching to cpu.', 'error')
                device = torch.device('cpu')
        # if the whisper device is set to cpu
        elif self.whisper_device in ['cpu', 'CPU']:
            device = torch.device('cpu')
        # any other setting, defaults to automatic selection
        else:
            # use CUDA if available
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        stAI.log_print('Using {} for torch processing.'.format(device), 'info')

        # toolkit_UI_obj.create_transcription_settings_window()
        # time.sleep(120)
        # return

    def prepare_transcription_file(self, toolkit_UI_obj=None, translate=False, unique_id=None):
        '''
        This asks the user where to save the transcribed files,
         it choses between transcribing an existing timeline (and first starting the render process)
         and then passes the file to the transcription queue

        :param toolkit_UI_obj:
        :param translate:
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
        if resolve_data['resolve'] != None and 'currentTimeline' in resolve_data and resolve_data[
            'currentTimeline'] != '':

            # reset any potential yes that the user might have said when asked to continue without resolve
            toolkit_UI_obj.no_resolve_ok = False

            # ask the user where to save the files
            while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
                self.stAI.log_print("Prompting user for render path.")
                target_dir = toolkit_UI_obj.ask_for_target_dir()

                # cancel if the user presses cancel
                if not target_dir:
                    self.stAI.log_print("User canceled transcription operation.")
                    return False

            # get the current timeline from Resolve
            currentTimelineName = resolve_data['currentTimeline']['name']

            # generate a unique id to keep track of this file in the queue and transcription log
            if unique_id == None:
                unique_id = self._generate_transcription_unique_id(name=currentTimelineName)

            # update the transcription log
            # @todo this doesn't seem to work
            self.add_to_transcription_log(unique_id=unique_id, **{'name': currentTimelineName, 'status': 'rendering'})

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

        # if resolve is not available
        else:

            # ask the user if they want to simply transcribe a file from the drive
            if toolkit_UI_obj.no_resolve_ok or messagebox.askyesno(message='A Resolve Timeline is not available.\n\n'
                                           'Do you want to transcribe an existing audio file instead?'):

                # remember that the user said it's ok to continue without resolve
                toolkit_UI_obj.no_resolve_ok = True

                # create a list of files that will be passed later for transcription
                rendered_files = []

                # ask the user for the target file
                target_file = toolkit_UI_obj.ask_for_target_file()

                # add it to the transcription list
                if target_file:
                    rendered_files.append(target_file)

                    # the file name also becomes currentTimelineName for future use
                    currentTimelineName = os.path.basename(target_file)

                # or close the process if the user canceled
                else:
                    return False

            # close the process if the user doesn't want to transcribe an existing file
            else:
                return False

        # the rendered files list should contain either the file rendered in resolve or the selected audio file
        # so add that to the transcription queue together with the name of the timeline
        return self.start_transcription_config(audio_file_path=rendered_files[0],
                                               name=currentTimelineName,
                                               translate=translate, unique_id=unique_id)

    def start_transcription_config(self, audio_file_path=None, name=None, translate=None, unique_id=None):
        '''
        Opens up a modal to allow the user to configure and start the transcription process for each file
        :return:
        '''

        # check if there's a UI object available
        if not self.is_UI_obj_available():
            return False

        # @todo the purpose of this is to get more input from the user regarding the transcription process
        #   before it starts
        #print('Opening transcription settings window')
        #self.toolkit_UI_obj.create_transcription_settings_window(audio_file_path=audio_file_path,
        #                                                         name=name,
        #                                                         translate=translate
        #                                                         )

        return self.add_to_transcription_queue(audio_file_path=audio_file_path, translate=translate, name=name,
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
            self.stAI.log_print('Missing unique id when trying to add item to transcription log.')
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

    def add_to_transcription_queue(self, toolkit_UI_obj=None, translate=False, audio_file_path=None,
                                   name=None, unique_id=None):
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

        # generate a unique id if one hasn't been passed
        if unique_id is None:
            next_queue_id = self._generate_transcription_unique_id(name=name)
        else:
            next_queue_id = unique_id

        # add to transcription queue if we at least know the path and the name of the timeline/file
        if next_queue_id and audio_file_path and os.path.exists(audio_file_path) and name:

            file_dict = {'name': name, 'audio_file_path': audio_file_path, 'translate': translate,
                         'info': None, 'status': 'waiting'}

            # add to transcription queue
            self.transcription_queue[next_queue_id] = file_dict

            # add the file to the transcription log too (the add function will check if it's already there)
            self.add_to_transcription_log(unique_id=next_queue_id, **file_dict)

            # now ping the transcription queue in case it's sleeping
            self.ping_transcription_queue()

            return True
        else:
            self.stAI.log_print('Missing parameters to add file to transcription queue', 'error')
            return False

    def _generate_transcription_unique_id(self, name=None):
        if name:
            return name+'-'+str(int(time.time()))
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
            #self.stAI.log_print('Files waiting in queue for transcription:\n {} \n'.format(self.transcription_queue))

            # check if there's an active transcription thread
            if self.transcription_queue_thread is not None:
                self.stAI.log_print('Currently transcribing: {}'.format(self.transcription_queue_current_name))

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
            self.stAI.log_print('Transcription queue empty. Going to sleep.')
            return False

    def transcribe_from_queue(self, queue_id):

        # check if there's a UI object available
        if not self.is_UI_obj_available():
            return False

        # get file info from queue
        name, audio_file_path, translate, info = self.get_queue_file_info(queue_id)

        self.stAI.log_print("Starting to transcribe {}".format(name))

        # make the name of the file that is currently being processed public
        self.transcription_queue_current_name = name

        # transcribe
        self.whisper_transcribe(audio_file_path=audio_file_path, translate=translate, name=name, queue_id=queue_id)

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
            return [queue_file['name'], queue_file['audio_file_path'],
                    queue_file['translate'], queue_file['info']]

        return False

    def whisper_transcribe(self, name=None, audio_file_path=None, translate=False, target_dir=None, queue_id=None):

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

        # load OpenAI Whisper
        # and hold on to it for future use
        if self.whisper_model == None:
            self.stAI.log_print('Loading whisper {} model.'.format(self.whisper_model_name), 'info')
            self.whisper_model = whisper.load_model(self.whisper_model_name)

        # update the status of the item in the transcription log
        self.update_transcription_log(unique_id=queue_id, **{'status': 'transcribing'})

        notification_msg = "Transcribing {}.\nThis will take a while.".format(name)
        self.toolkit_UI_obj.notify_via_os("Starting Transcription", notification_msg, notification_msg)

        start_time = time.time()

        # if translate is true, translate to english
        if translate:
            result = self.whisper_model.transcribe(audio_file_path, task='translate')
        else:
            result = self.whisper_model.transcribe(audio_file_path)

        # let the user know that the speech was processed
        notification_msg = "Finished transcription for {} in {} seconds".format(name,
                                                                                round(time.time() - start_time))
        self.toolkit_UI_obj.notify_via_os("Finished Transcription", notification_msg, notification_msg)

        # update the status of the item in the transcription log
        self.update_transcription_log(unique_id=queue_id, **{'status': 'saving files'})

        # prepare a json file taking into consideration the name of the audio file
        transcription_json_file_path = os.path.join(target_dir, audio_file_name + '.transcription.json')

        # save the whole whisper result in the json file to previously selected target_dir
        with open(transcription_json_file_path, 'w', encoding='utf-8') as outfile:
            json.dump(result, outfile)

        # save the full transcript in text format too
        transcription_txt_file_path = os.path.join(target_dir, audio_file_name + '.transcription.txt')

        # save the whole whisper result in the json file to previously selected target_dir
        with open(transcription_txt_file_path, 'w', encoding="utf-8") as txt_outfile:
            txt_outfile.write(result['text'])

        # save SRT file to previously selected target_dir
        srt_path = os.path.join(target_dir, audio_file_name + ".srt")
        with open(srt_path, "w", encoding="utf-8") as srt:
            whisper.utils.write_srt(result["segments"], file=srt)

        # when done, change the status in the log
        # and also add the file paths to the log
        self.update_transcription_log(unique_id=queue_id, status='done',
                                      srt_file_path=srt_path, txt_file_path=transcription_txt_file_path,
                                      json_file_path=transcription_json_file_path)

        print(self.transcription_log[queue_id])

        # why not open the transcription in a transcription window?
        self.toolkit_UI_obj.open_transcription_window(title=name,
                                                      transcription_file_path=transcription_json_file_path,
                                                      srt_file_path=srt_path)

        return True

    def import_SRT_prompt(self, srt_path=None, name=None):
        '''
        This asks user to go to the timeline in Resolve and press ok to import the SRT from srt_path
        :param srt_path:
        :return:
        '''

        # don't continue if the srt path and the name are not known
        if srt_path is None or name is None:
            return False

        # get the srt filename for later use
        srt_filename = os.path.basename(srt_path)

        prompt_message = "The subtitles for {} are ready.\n\n" \
                         "To import the file into Resolve, open the Media Bin " \
                         "and then press OK.".format(name)

        # let the user know that the srt file doesn't exist
        if not os.path.exists(srt_path):
            self.stAI.log_print('Aborting import. {} doesn\'t exist.'.format(srt_path))
            return False

        # wait for user ok before importing into resolve bin
        if messagebox.askokcancel(message=prompt_message, icon='info'):
            self.stAI.log_print("Importing SRT into Resolve Bin.")
            mots_resolve.import_media(srt_path)
            return True
        else:
            self.stAI.log_print("Pressed cancel. Aborting import of {} into Resolve.".format(srt_filename))

        return False

    def is_UI_obj_available(self, toolkit_UI_obj=None):

        # if there's no toolkit_UI_obj in the object or one hasn't been passed, abort
        if toolkit_UI_obj is None and self.toolkit_UI_obj is None:
            print('No GUI available. Aborting.')
            return False
        # if there was a toolkit_UI_obj passed, update the one in the object
        elif toolkit_UI_obj is not None:
            self.toolkit_UI_obj = toolkit_UI_obj
            return True
        # if there is simply a self.toolkit_UI_obj just return True
        else:
            return True

    def go_to_time(self, seconds=0):

        from timecode import Timecode

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

        # move playhead in resolve
        mots_resolve.set_resolve_tc(str(new_timeline_tc))



def speaker_diarization(audio_path):

    # work in progress, but whisper vs. pyannote dependencies collide (huggingface-hub)
    #print("Detecting speakers.")

    from pyannote.audio import Pipeline
    #pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

    # apply pretrained pipeline
    #diarization = pipeline(audio_path)

    # print the result
    #for turn, _, speaker in diarization.itertracks(yield_label=True):
    #    print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")
    return False


def start_thread(function, toolkit_UI_obj):
    '''
    This starts the transcribe function in a different thread
    :return:
    '''

    # are we transcribing or translating?
    if function == 'transcribe':
        t1=Thread(target=transcribe, args=(False,toolkit_UI_obj))

    # if we are translating, pass the true argument to the transcribe function
    elif function == 'translate':
        t1=Thread(target=transcribe, args=(True,toolkit_UI_obj))
    else:
        return False

    # start the thread
    t1.start()


def execute_operation(operation, toolkit_UI_obj):

    if not operation or operation == '':
        return False

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

        # trigger warning if there is no current timeline
        if resolve_data['currentTimeline'] is None:
            print('Timeline not available. Make sure that you\'ve opened a Timeline in Resolve.')
            return False

        # @todo trigger error if the timeline is not opened or the clip is not available in the bin
        #   otherwise exception is thrown by Resolve API

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
        if current_timeline and 'markers' in current_timeline:

            # take each marker from timeline and get its color
            for marker in current_timeline['markers']:

                # only append the marker to the list if it wasn't added already
                if current_timeline['markers'][marker]['color'] not in current_timeline_marker_colors:
                    current_timeline_marker_colors.append(current_timeline['markers'][marker]['color'])

        # if no markers exist, cancel operation and let the user know that there are no markers to render
        if current_timeline_marker_colors:
            marker_color = simpledialog.askstring(title="Markers Color", prompt="What color markers should we render?\n\n"
                                                                    "These are the marker colors on the current timeline:\n"
                                                                    +", ".join(current_timeline_marker_colors))
        else:
            no_markers_alert = 'The timeline doesn\'t contain any markers'
            print(no_markers_alert)
            return False

        if not marker_color:
            print("User canceled render operation.")
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
            print("User canceled render operation.")
            return False

        if operation =='render_markers_to_stills':
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
current_bin = ''
resolve_error = 0
resolve = None


def poll_resolve_data(toolkit_UI_obj=None):

    global current_project
    global current_timeline
    global current_tc
    global current_bin
    global resolve

    global resolve_error

    global stAI

    # try to poll resolve
    try:
        resolve_data = mots_resolve.get_resolve_data()

        if(current_project != resolve_data['currentProject']):
            current_project = resolve_data['currentProject']
            stAI.log_print('Current Project: {}'.format(current_project))

        if(current_timeline != resolve_data['currentTimeline']):
            current_timeline = resolve_data['currentTimeline']
            stAI.log_print("Current Timeline: {}".format(current_timeline))

        #  updates the currentBin
        if(current_bin != resolve_data['currentBin']):
            current_bin = resolve_data['currentBin']
            stAI.log_print("Current Bin: {}".format(current_bin))

        # update the global resolve variable with the resolve object
        resolve = resolve_data['resolve']

        # was there a previous error?
        if resolve_error > 0:
            # first let the user know that the connection is back on
            stAI.log_print("Resolve connection re-established.", 'warn')

            # reset the error counter since the Resolve API worked fine
            resolve_error = 0

            # refresh main window - @todo move this in its own object asap
            toolkit_UI_obj.update_main_window()

        # re-schedule this function to poll every 500ms
        toolkit_UI_obj.root.after(500, lambda: poll_resolve_data(toolkit_UI_obj))


    # if an exception is thrown while trying to work with Resolve, don't crash, but continue to try to poll
    except:

        # count the number of errors
        resolve_error += 1

        if resolve_error == 1:
            # set the resolve object to None to make it known that its not available
            resolve = None

            # refresh main window - @todo move this in its own object asap
            toolkit_UI_obj.update_main_window()

        # let the user know that there's an error, but at different intervals:

        # after 20+ tries, assume the user is no longer paying attention and reduce the frequency of tries
        if resolve_error > 20:
            stAI.log_print('Resolve is still out. Retrying every 30 seconds. '
                    'Error count: {}'.format(resolve_error), 'error')

            # and increase the wait time by 30 seconds

            # re-schedule this function to poll after 30 seconds
            toolkit_UI_obj.root.after(30000, lambda: poll_resolve_data(toolkit_UI_obj))

        # if the error has been triggered more than 10 times, say this
        elif resolve_error > 10:

            if resolve_error == 11:
                stAI.log_print('Resolve communication error. Try to reload the project in Resolve. '
                               'Retrying every 2 seconds.'
                      'Error count: {}'.format(resolve_error), 'warn')

            # re-schedule this function to poll after 2 seconds
            toolkit_UI_obj.root.after(2000, lambda: poll_resolve_data(toolkit_UI_obj))

        else:
            stAI.log_print('Resolve Communication Error. Is your Resolve project open? '
                        'Error count: {}'.format(resolve_error))

            # re-schedule this function to poll after 1 second
            toolkit_UI_obj.root.after(1000, lambda: poll_resolve_data(toolkit_UI_obj))

        # resolve is now None in the global variable
        resolve = None

        return False

# this is the path to the user data folder
USER_DATA_PATH = 'userdata'

# this is where we store the app configuration
APP_CONFIG_FILE_NAME = 'config.json'

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

        print("Running StoryToolkit version {}".format(self.__version__))

    class bcolors:
        '''
        This is useful for outputting colored stuff to the terminal
        '''
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def get_app_setting(self, setting_name=None, default_if_none=None):
        '''
        Returns a specific app setting or None if it doesn't exist
        If default if none is passed, the app will also save the setting to the config for future use
        :param setting_name:
        :param default_if_none:
        :return:
        '''

        if setting_name is None or not setting_name or setting_name == '':
            self.log_print('No setting was passed.', 'error')
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

            print('Config setting {} saved as {} '.format(setting_name, default_if_none))

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
            self.log_print('No setting that we could save to the config file was passed.', 'error')
            return False

        # get existing configuration
        self.config = self.get_config()

        # save or overwrite the passed setting the config json
        self.config[setting_name] = setting_value

        # before writing the configuration to the config file
        # check if the user data folder exists
        if not os.path.exists(self.user_data_path):
            self.log_print('User data folder doesn\'t exist. Creating one at {}'
                           .format(os.path.abspath(self.user_data_path)), 'warn')

            # and create the whole path to it if it doesn't
            os.makedirs(self.user_data_path)

        # then write the config to the config json
        with open(self.config_file_path, 'w') as outfile:
            json.dump(self.config, outfile)

        self.log_print('Updated config file {} with {} data.'
                       .format(os.path.abspath(self.config_file_path), setting_name), 'info')

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

    def get_project_setting(self):
        return


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
            print('Unable to check the latest version of StoryToolkitAI: {}. Is your Internet connection working?'.format(e))

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

    def log_print(self, message, type=None):
        # @todo log file
        # all the messages passed through here should be logged to a file

        # @todo use type (warn, error, info) to decide whether to show message or not
        #   also read the verbosity parameter from a config file

        #  for now assume high verbosity
        #  (info shows all, warn shows warnings and errors only, error shows only errors)
        verbose = 'info'

        # for now, if the user doesn't pass a type, assume it's info
        if type == None:
            type = 'info'

        # add colors to the message, depending on its type
        if type == 'warn':
            message = self.bcolors.WARNING + message + self.bcolors.ENDC
        elif type == 'error':
            message = self.bcolors.FAIL + message + self.bcolors.ENDC

        # show all messages if the verbosity is set to info
        if verbose == 'info' and type in ['info', 'warn', 'error']:
            print(message)

        # show only warnings and errors if verbosity is warn
        elif verbose == 'warn' and type in ['warn', 'error']:
            print(message)

        # show only errors if verbosity is set to error
        elif verbose == 'error' and type == 'error':
            print(message)




if __name__ == '__main__':

    # keep a global StoryToolkitAI object for now
    global stAI

    # init StoryToolkitAI object
    stAI = StoryToolkitAI()

    # check if a new version of the app exists
    [update_exists, online_version] = stAI.check_update()

    # and prepare the info message to let the user know that there's a new version of the app available
    warn_message = None
    if update_exists:
        warn_message = '\nA new version ({}) of StoryToolkitAI is available.\n Use git pull or manually download it from\n https://github.com/octimot/StoryToolkitAI \n'.format(online_version)

    # initialize operations object
    toolkit_ops_obj = ToolkitOps(stAI=stAI)

    # initialize GUI
    app_UI = toolkit_UI(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI, warn_message=warn_message)
