
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
To install whisper on MacOS view brew and pip:

brew install rust
pip install git+https://github.com/openai/whisper.git

'''


def notify(title, text):
    """
    Uses OS specific tools to notify the user

    :param title:
    :param text:
    :return:
    """
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

#define a global target dir so we remember where we chose to save stuff last time when asked
initial_target_dir = ''

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

    # remember what the user selected for next time
    initial_target_dir = target_dir

    return target_dir


def transcribe(translate_to_english=True):
    """
    Renders the current timeline, transcribes it via OpenAI Whisper and saves it as an SRT file

    :param translate_to_english: bool
    :return:
    """

    # get info from resolve
    resolve_data = mots_resolve.get_resolve_data()

    currentTimelineName = resolve_data['currentTimeline']['name']

    target_dir = ''

    # ask the user where to save the files
    while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
        print("Prompting user for render path.")
        target_dir = ask_for_target_dir()

        # cancel if the user presses cancel
        if not target_dir:
            return False

    print("Saving into {}".format(target_dir))
    notify("Starting Render", "Starting Render in Resolve")

    # render the timeline in Resolve
    rendered_files = mots_resolve.render_timeline(target_dir, 'Audio Only', True, False, False, True)

    # load whisper
    model = whisper.load_model("medium")

    # process each audio file through whisper
    for audio_path in rendered_files:
        print("Processing {}".format(audio_path))
        notify("Starting Transcription", "Processing {}".format(audio_path))

        start_time = time.time()

        if translate_to_english:
            result = model.transcribe(audio_path, task='translate')
        else:
            result = model.transcribe(audio_path)

        # prepare a json file taking into consideration the name of the audio file
        transcription_json_file_path = os.path.join(target_dir, os.path.basename(audio_path) + 'transcription.json')

        print("Finished processing {} after {} seconds".format(audio_path, time.time() - start_time))
        notify("Finished Transcription", "Finished processing {} after {} seconds".format(audio_path, time.time() - start_time))

        # save the whole whisper result in the json file
        with open(transcription_json_file_path, 'w') as outfile:
            json.dump(result, outfile)

        # save SRT
        srt_path = os.path.join(target_dir, (os.path.basename(audio_path) + ".srt"))
        with open(srt_path, "w", encoding="utf-8") as srt:
            whisper.utils.write_srt(result["segments"], file=srt)

        # prompt user to import file into Resolve
        if messagebox.askokcancel(message="The subtitle for the timeline {} is finished.\n\nPlease open the Media Folder where you want to import it and after that press OK".format(currentTimelineName)):
            print("Importing SRT in Resolve")
            mediaPoolItem = mots_resolve.import_media(srt_path)
        else:
            print("Pressed cancel")



def transcribe_thread():
    t1=Thread(target=transcribe)
    t1.start()



if __name__ == '__main__':


    # initialize GUI
    root = tk.Tk()

    # set app icon
    root.iconbitmap(r'icon.ico')

    # set the window title
    root.title("StoryToolkitAI")

    # set the window size
    root.geometry("350x240")

    frame = tk.Frame(root)
    frame.pack()

    #define the pixel size for buttons
    pixel = tk.PhotoImage(width=1, height=1)

    # draw buttons
    # @TODO implement all mots_resolve functions in the GUI

    #row 1
    #button2 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Copy Timeline\nMarkers to Clip", command=button_test)
    #button2.grid(row=1, column=1, padx=10, pady=10)

    #button3 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Copy Clip Markers\nto Timeline", command=button_test)
    #button3.grid(row=1, column=2, padx=10, pady=10)


    # row 2
    #button5 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Render Markers\nto Stills", command=button_test)
    #button5.grid(row=2, column=1, padx=10, pady=10)

    #button5 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Render Duration\nMarkers", command=button_test)
    #button5.grid(row=2, column=2, padx=10, pady=10)

    # row 3
    #button5 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Transcribe\nDuration Markers", command=button_test)
    #button5.grid(row=3, column=1, padx=10, pady=10)

    button5 = tk.Button(frame, image=pixel, width=120, height=50, compound="c", text="Transcribe\nTimeline", command=transcribe_thread)
    button5.grid(row=3, column=2, padx=10, pady=10)




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

    root.mainloop()