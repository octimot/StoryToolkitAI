
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

import whisper

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


def button_test():
    messagebox.showerror(message='This will work soon')
    print("Button pressed")



#operation_status = mots_resolve.copy_markers('timeline', 'clip', current_timeline['name'], data['form_data']['r_to'], data['form_data']['r_delete'])

# define a global target dir so we remember where we chose to save stuff last time when asked
# but start with the user's home directory
initial_target_dir = os.path.expanduser("~")

def ask_for_target_dir():
    global initial_target_dir

    # put the UI on top
    root.wm_attributes('-topmost', True)
    root.lift()

    # ask the user via os dialog where can we find the directory
    target_dir = filedialog.askdirectory(title="Where should we save the files?", initialdir=initial_target_dir)

    # what happens if the user cancels
    if not target_dir:
        return False

    # remember which directory the user selected for next time
    initial_target_dir = target_dir

    return target_dir

def ask_for_target_file():
    global initial_target_dir

    # put the UI on top
    root.wm_attributes('-topmost', True)
    root.lift()

    # ask the user via os dialog which file to use
    target_file = filedialog.askopenfilename(title="Choose a file", initialdir=initial_target_dir, filetypes=[("Audio files", ".mp4 .wav .mp3")], multiple=False)

    # what happens if the user cancels
    if not target_file:
        return False

    # remember what the user selected for next time
    initial_target_dir = os.path.dirname(target_file)

    return target_file



def transcribe(translate_to_english=False):
    """
    Renders the current timeline, transcribes it via OpenAI Whisper and saves it as an SRT file

    :param translate_to_english: bool
    :return:
    """

    # get info from resolve
    try:
        resolve_data = mots_resolve.get_resolve_data()
    # in case of exception still create a dict with an empty resolve object
    except:
        resolve_data = {'resolve': None}

    target_dir = ''

    # ask the user where to save the files
    while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
        print("Prompting user for render path.")
        target_dir = ask_for_target_dir()

        # cancel if the user presses cancel
        if not target_dir:
            print("User canceled transcription operation.")
            return False

    # render the audio from resolve, only if Resolve is available
    if resolve_data['resolve'] != None and 'currentTimeline' in resolve_data and resolve_data['currentTimeline'] != '':

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
            target_file = ask_for_target_file()

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
                         "To import the file into Resolve, go to the Media Bin where you want to import it" \
                         "and then press OK.".format(currentTimelineName)

        # wait for user ok before importing into resolve bin
        if messagebox.askokcancel(message=prompt_message,icon='info'):
            print("Importing SRT into Resolve Bin")
            mots_resolve.import_media(srt_path)
        else:
            print("Pressed cancel")

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


def start_thread(function):
    '''
    This starts the transcribe function in a different thread
    :return:
    '''

    # are we transcribing or translating?
    if function == 'transcribe':
        t1=Thread(target=transcribe, args=(False,))

    # if we are translating, pass the true argument to the transcribe function
    elif function == 'translate':
        t1=Thread(target=transcribe, args=(True,))
    else:
        return False

    # start the thread
    t1.start()


def execute_operation(operation):

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

        render_target_dir = ask_for_target_dir()

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

def poll_resolve_data():

    global current_project
    global current_timeline
    global current_tc
    global current_bin

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

        # re-schedule this function to poll every 500ms
        root.after(500, poll_resolve_data)


    # if an exception is thrown while trying to work with Resolve, don't crash, but continue to try to poll
    except:
        print("Resolve Error. Retrying in a few seconds. (" + str(time.time()).split('.')[0] + ")")
        resolve_error += 1

        # let the user know that there's an error
        # but if the error has been triggered more than 10 times, say this
        if resolve_error > 10:
            print('Resolve communication error. Try to reload the project in Resolve.')
            # increase the wait with 2 seconds
            time.sleep(2)

            # after 20+ tries, assume the user is no longer paying attention
            if resolve_error > 20:
                print("Resolve still out. Is anybody still paying attention?")

                # and increase the wait time by 7 seconds (total 10)
                time.sleep(7)
        else:
            print('Resolve Communication Error. Is your Resolve project open?')

        # pause and try again in a second
        time.sleep(1)


# leave version here, maybe add setuptools in the future
version = 0.15

if __name__ == '__main__':


    # initialize GUI
    root = tk.Tk()

    # set the window title
    root.title("StoryToolkitAI v{}".format(version))

    # set the window size
    root.geometry("350x340")

    frame = tk.Frame(root)
    frame.pack()

    #define the pixel size for buttons
    pixel = tk.PhotoImage(width=1, height=1)

    # draw buttons
    # @TODO implement all mots_resolve functions in the GUI

    #row 1
    button2 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Copy Timeline\nMarkers to Same Clip", command= lambda:execute_operation('copy_markers_timeline_to_clip'))
    button2.grid(row=1, column=1, padx=10, pady=10)

    button3 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Copy Clip Markers\nto Same Timeline", command= lambda:execute_operation('copy_markers_clip_to_timeline'))
    button3.grid(row=1, column=2, padx=10, pady=10)


    # row 2
    button5 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Render Markers\nto Stills", command= lambda:execute_operation('render_markers_to_stills'))
    button5.grid(row=2, column=1, padx=10, pady=10)

    button5 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Render Duration\nMarkers", command=button_test)
    button5.grid(row=2, column=2, padx=10, pady=10)

    # row 3
    #button5 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Transcribe\nDuration Markers", command=button_test)
    #button5.grid(row=3, column=1, padx=10, pady=10)

    button5 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Transcribe\nTimeline", command= lambda :start_thread('transcribe'))
    button5.grid(row=3, column=2, padx=10, pady=10)

    # row 4
    #button5 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Translate\nDuration Markers to English", command=button_test)
    #button5.grid(row=4, column=1, padx=10, pady=10)

    button7 = tk.Button(frame, image=pixel, width=140, height=50, compound="c", text="Translate\nTimeline to English", command= lambda :start_thread('translate'))
    button7.grid(row=4, column=2, padx=10, pady=10)




    resolve_marker_colors = {
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

    print("Starting GUI")

    # poll resolve after 100ms
    root.after(500, poll_resolve_data())

    root.mainloop()