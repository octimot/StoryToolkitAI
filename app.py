
import os
import platform
import time
import json
# import sys

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from tkinter import *

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


def notify(title, text, debug_message):
    """
    Uses OS specific tools to notify the user

    :param title:
    :param text:
    :return:
    """

    # print to console first
    print(debug_message)

    # notify the user depending on which platform they're on
    if platform.system() == 'Darwin':  # macOS
        os.system("""
                                                osascript -e 'display notification "{}" with title "{}"'
                                                """.format(text, title))

    # no solution yet for other platforms
    elif platform.system() == 'Windows':  # Windows
        return
    else:  # linux variants
        return


# define a global target dir so we remember where we chose to save stuff last time when asked
# but start with the user's home directory
initial_target_dir = os.path.expanduser("~")




class toolkit_UI:
    '''
    This handles all the GUI operations mainly using tkinter
    '''
    def __init__(self, info_message=False):

        # initialize tkinter as the main GUI
        self.root = tk.Tk()

        # show any info messages
        if info_message:
            messagebox.showinfo(title='Update available', message=info_message)

        # this should hold all the existing GUI windows, except the root
        self.windows = {}

        # any frames stored here in the future will be considered visible
        self.main_window_visible_frames = []

        # create the main window
        self.create_main_window()

        self.resolve_marker_colors = {}
        self.resolve_theme_colors = {}

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

    class main_window:
        pass

    class other_windows:
        pass

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

        # set the window title
        self.root.title("StoryToolkitAI v{}".format(stAI.__version__))

        # set the window size
        #self.root.geometry("350x440")

        # create the frame that will hold the resolve buttons
        self.main_window.resolve_buttons_frame = tk.Frame(self.root)

        # create the frame that will hold the other buttons
        self.main_window.other_buttons_frame = tk.Frame(self.root)

        # define the pixel size for buttons
        pixel = tk.PhotoImage(width=1, height=1)

        # draw buttons

        # label1 = tk.Label(frame, text="Resolve Operations", anchor='w')
        # label1.grid(row=0, column=1, sticky='w', padx=10, pady=10)

        # resolve buttons frame row 1
        self.main_window.button1 = tk.Button(self.main_window.resolve_buttons_frame, image=pixel, width=140, height=50, compound="c",
                            text="Copy Timeline\nMarkers to Same Clip",
                            command=lambda: execute_operation('copy_markers_timeline_to_clip', self))
        self.main_window.button1.grid(row=1, column=1, padx=10, pady=10)

        self.main_window.button2 = tk.Button(self.main_window.resolve_buttons_frame, image=pixel, width=140, height=50, compound="c",
                            text="Copy Clip Markers\nto Same Timeline",
                            command=lambda: execute_operation('copy_markers_clip_to_timeline', self))
        self.main_window.button2.grid(row=1, column=2, padx=10, pady=10)

        # resolve buttons frame row 2
        self.main_window.button3 = tk.Button(self.main_window.resolve_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Render Markers\nto Stills",
                            command=lambda: execute_operation('render_markers_to_stills', self))
        self.main_window.button3.grid(row=2, column=1, padx=10, pady=10)

        self.main_window.button4 = tk.Button(self.main_window.resolve_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Render Duration\nMarkers",
                            command=lambda: execute_operation('render_markers_to_clip', self))
        self.main_window.button4.grid(row=2, column=2, padx=10, pady=10)

        # Other Frame Row 1
        self.main_window.button5 = tk.Button(self.main_window.other_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Transcribe\nTimeline",
                            command=lambda: start_thread('transcribe', self))
        self.main_window.button5.grid(row=1, column=1, padx=10, pady=10)

        self.main_window.button6 = tk.Button(self.main_window.other_buttons_frame, image=pixel, width=140, height=50, compound="c",
                            text="Translate\nTimeline to English", command=lambda: start_thread('translate', self))
        self.main_window.button6.grid(row=1, column=2, padx=10, pady=10)

        #self.main_window.link2 = Label(self.main_window.other_buttons_frame, text="project home", font=("Courier", 8), fg='#1F1F1F', cursor="hand2", anchor='s')
        #self.main_window.link2.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky='s')
        #self.main_window.link2.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/octimot/StoryToolkitAI"))

        # Other Frame row 2 (disabled for now)
        #self.main_window.button7 = tk.Button(self.main_window.other_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Transcribe\nDuration Markers")
        # self.main_window.button7.grid(row=4, column=1, padx=10, pady=10)
        #self.main_window.button8 = tk.Button(self.main_window.other_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Translate\nDuration Markers to English")
        # self.main_window.button8.grid(row=4, column=1, padx=10, pady=10)


        #self.main_window.button_test = tk.Button(self.main_window.other_buttons_frame, image=pixel, width=140, height=50, compound="c", text="Test",
        #                        command=lambda: self.update_main_window())
        #self.main_window.button_test.grid(row=5, column=2, padx=10, pady=10)



        # Make the window resizable false
        self.root.resizable(False, False)

        # poll resolve after 500ms
        self.root.after(500, poll_resolve_data(self))

        # refresh main window after 500 ms
        self.root.after(500, self.update_main_window())

        print("Starting StoryToolkitAI GUI")
        self.root.mainloop()

        return

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

    def ask_for_target_dir(self):
        global initial_target_dir

        # put the UI on top
        self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog where can we find the directory
        target_dir = filedialog.askdirectory(title="Where should we save the files?", initialdir=initial_target_dir)

        # what happens if the user cancels
        if not target_dir:
            return False

        # remember which directory the user selected for next time
        initial_target_dir = target_dir

        return target_dir

    def ask_for_target_file(self):
        global initial_target_dir

        # put the UI on top
        self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog which file to use
        target_file = filedialog.askopenfilename(title="Choose a file", initialdir=initial_target_dir,
                                                 filetypes=[("Audio files", ".mp4 .wav .mp3")], multiple=False)

        # what happens if the user cancels
        if not target_file:
            return False

        # remember what the user selected for next time
        initial_target_dir = os.path.dirname(target_file)

        return target_file


def transcribe(translate_to_english=False, toolkit_UI_obj = None):
    """
    Renders the current timeline, transcribes it via OpenAI Whisper and saves it as an SRT file

    :param translate_to_english: bool
    :return:
    """

    # we need to have a toolkit_UI_obj passed, otherwise there's no way to prompt the user
    if toolkit_UI_obj is None:
        return False

    # get info from resolve
    try:
        resolve_data = mots_resolve.get_resolve_data()
    # in case of exception still create a dict with an empty resolve object
    except:
        resolve_data = {'resolve': None}

    target_dir = ''

    # render the audio from resolve, only if Resolve is available
    if resolve_data['resolve'] != None and 'currentTimeline' in resolve_data and resolve_data['currentTimeline'] != '':

        # ask the user where to save the files
        while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
            print("Prompting user for render path.")
            target_dir = toolkit_UI_obj.ask_for_target_dir()

            # cancel if the user presses cancel
            if not target_dir:
                print("User canceled transcription operation.")
                return False

        # get the current timeline from Resolve
        currentTimelineName = resolve_data['currentTimeline']['name']

        # let the user know that we're starting the render
        notify("Starting Render", "Starting Render in Resolve", "Saving into {} and starting render.".format(target_dir))

        # use transcription_WAV render preset if it exists
        # transcription_WAV is an Audio only custom render preset that renders Linear PCM codec in a Wave format instead
        # of Quicktime mp4; this is just to work with wav files instead of mp4 to improve compatibility.
        if 'transcription_WAV' in resolve_data['renderPresets']:
            render_preset = 'transcription_WAV'
        else:
            render_preset = 'Audio Only'


        # render the timeline in Resolve
        rendered_files = mots_resolve.render_timeline(target_dir, render_preset, True, False, False, True)

    # if resolve is not available
    else:

        # ask the user if they want to simply transcribe a file from the drive
        if messagebox.askyesno(message='A Resolve Timeline is not available.\n\n'
                                       'Do you want to transcribe an existing audio file?'):

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


    # load OpenAI Whisper
    # we're using the medium model for better accuracy vs. time it takes to process
    # if in doubt use the large model but that will need more time
    model = whisper.load_model("medium")

    # process each audio file through whisper
    for audio_path in rendered_files:

        notification_msg = "Processing {}.\nThis will take a while depending on your CPU/GPU. " \
                           "Do not exit the app until it finished or you will have to start all over."\
            .format(audio_path)
        notify("Starting Transcription", notification_msg, notification_msg)

        start_time = time.time()

        if translate_to_english:
            result = model.transcribe(audio_path, task='translate')
        else:
            result = model.transcribe(audio_path)

        # let the user know that the speech was processed
        notification_msg = "Finished processing {} after {} seconds".format(audio_path, round(time.time() - start_time))
        notify("Finished Transcription", notification_msg, notification_msg)

        # prepare a json file taking into consideration the name of the audio file
        transcription_json_file_path = os.path.join(target_dir, os.path.basename(audio_path) + '.transcription.json')

        # save the whole whisper result in the json file to previously selected target_dir
        with open(transcription_json_file_path, 'w', encoding='utf-8') as outfile:
            json.dump(result, outfile)

        # save the full transcript in text format too
        transcription_txt_file_path = os.path.join(target_dir, os.path.basename(audio_path) + '.transcription.txt')

        # save the whole whisper result in the json file to previously selected target_dir
        with open(transcription_txt_file_path, 'w', encoding="utf-8") as txt_outfile:
            txt_outfile.write(result['text'])

        # save SRT file to previously selected target_dir
        srt_path = os.path.join(target_dir, (os.path.basename(audio_path) + ".srt"))
        with open(srt_path, "w", encoding="utf-8") as srt:
            whisper.utils.write_srt(result["segments"], file=srt)

        # prompt user to import file into Resolve
        prompt_message = "The subtitles for {} are ready.\n\n" \
                         "To import the file into Resolve, go to the Media Bin where you want to import it " \
                         "and then press OK.".format(currentTimelineName)

        # wait for user ok before importing into resolve bin
        if messagebox.askokcancel(message=prompt_message,icon='info'):
            print("Importing SRT into Resolve Bin")
            mots_resolve.import_media(srt_path)
        else:
            print("Pressed cancel. Aborting SRT import into Resolve.")


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

        # execute operation without asking for any prompts
        # this will delete the existing clip/timeline destination markers,
        # but the user can undo the operation from Resolve
        return mots_resolve.copy_markers(source, destination,
                                         resolve_data['currentTimeline']['name'],
                                         resolve_data['currentTimeline']['name'],
                                         True)

    # render marker operation
    elif operation == 'render_markers_to_stills' or operation == 'render_markers_to_clips':

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

            # ask user for render preset or asign one
            # @todo

        # ask user for marker color
        # @todo only ask the colors that exist in the source markers
        # if no markers exist, cancel operation and let the user know that there are no markers to render
        marker_color = simpledialog.askstring(title="Markers Color", prompt="What color markers should we render?\n"
                               "Blue, Cyan, Green, Yellow, Red, Pink, "
                               "Purple, Fuchsia, Rose, Lavender, Sky, Mint, Lemon, Sand, Cocoa, Cream?")

        if not marker_color:
            print("User canceled render operation.")
            return False

        # verify if it's the right color
        # @todo

        mots_resolve.render_markers(marker_color, render_target_dir, False,
                                                           stills, render, render_preset)


    return False


current_project = ''
current_timeline = ''
current_tc = '00:00:00:00'
current_bin = ''
resolve_error = 0
resolve = None


def poll_resolve_data(toolkit_UI_obj):

    global current_project
    global current_timeline
    global current_tc
    global current_bin
    global resolve

    global resolve_error

    # try to poll resolve
    try:
        resolve_data = mots_resolve.get_resolve_data()

        if(current_project != resolve_data['currentProject']):
            current_project = resolve_data['currentProject']
            print('Current Project: {}'.format(current_project))

        if(current_timeline != resolve_data['currentTimeline']):
            current_timeline = resolve_data['currentTimeline']
            print("Current Timeline: {}".format(current_timeline))

        #  updates the currentBin
        if(current_bin != resolve_data['currentBin']):
            current_bin = resolve_data['currentBin']
            print("Current Bin: {}".format(current_bin))

        # update the global resolve variable with the resolve object
        resolve = resolve_data['resolve']

        # was there a previous error?
        if resolve_error > 0:
            # first let the user know that the connection is back on
            print("Resolve connection re-established.")

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
            print('Resolve still out. Is anybody still paying attention? Retrying in 10 seconds. '
                    'Error count: {}'.format(resolve_error))

            # and increase the wait time by 10 seconds

            # re-schedule this function to poll after 10 seconds
            toolkit_UI_obj.root.after(10000, lambda: poll_resolve_data(toolkit_UI_obj))

        # if the error has been triggered more than 10 times, say this
        elif resolve_error > 10:
            print('Resolve communication error. Try to reload the project in Resolve. Retrying in 2 seconds. '
                  'Error count: {}'.format(resolve_error))
            # increase the wait with 2 seconds

            # re-schedule this function to poll after 10 seconds
            toolkit_UI_obj.root.after(2000, lambda: poll_resolve_data(toolkit_UI_obj))

        else:
            print('Resolve Communication Error. Is your Resolve project open? '
                        'Error count: {}'.format(resolve_error))

            # re-schedule this function to poll after 1 second
            toolkit_UI_obj.root.after(1000, lambda: poll_resolve_data(toolkit_UI_obj))

        resolve = None


class StoryToolkitAI:
    def __init__(self):
        # import version.py - this holds the version stored locally
        import version

        # keep the version in memory
        self.__version__ = version.__version__

        print("Running StoryToolkit version {}".format(self.__version__))

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

            # if there's a number larger online, return true
            if int(online_version[n]) > int(local_version[n]):
                return True, online_version_raw

            # continue the search if there's no version mismatch
            if int(online_version[n]) == int(local_version[n]):
                continue
            break

        # return false (and the online version) if the local and the online versions match
        return False, online_version_raw


if __name__ == '__main__':

    # init StoryToolkitAI
    stAI = StoryToolkitAI()

    # check if a new version of the app exists
    [update_exists, online_version] = stAI.check_update()

    # and let the user know if a new version of the app was detected
    info_message = False
    if update_exists:
        info_message = '\nA new version ({}) of StoryToolkitAI is available.\n Use git pull or manually download it from\n https://github.com/octimot/StoryToolkitAI \n'.format(online_version)
        print(info_message)

    # use CUDA if available
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Using device:', device)


    # initialize GUI
    app_UI = toolkit_UI(info_message)
