# StoryToolkitAI

## Description

StoryToolkitAI is an editing extension for Davinci Resolve Studio 18 that uses Open AI Whisper to transcribe timelines
and enables editors to log footage and edit more efficiently.
 
**TL;DR:
this tool is supernatural and will enhance your editing workflow like Harry Potter's Sword of Gryffindor or Batman's 
Utility Belt - depending on which reference you relate to kind of shows what sort of person you are, but this is a
discussion for some other time.**

<img alt="StoryToolkitAI Demo GIF" src="https://videoapi-muybridge.vimeocdn.com/animated-thumbnails/image/9eb88ee1-4902-4e17-82dc-77411d959eab.gif?ClientID=vimeo-core-prod&Date=1665676352&Signature=52a72df29b216dd2f8cce8ee7360ea38a24b5b6e" width="700">
https://vimeo.com/759962195/dee07a067a

### Key Features
- [x] **Free Automatic Transcriptions in many languages** on your local machine directly from Resolve
- [x] **Free Automatic Translation** from many languages to English on your local machine from Resolve
- [x] Export of transcripts to multiple formats, including SRT
- [x] Import of transcript SRT file directly into Resolve
- [x] Transcription queuing to line up transcription jobs
- [x] **Transcript Timeline Navigation** - click or UP/DOWN on transcript moves the playhead in Resolve
- [x] **Transcript Word Search** - allows you to find specific words or phrases in your transcripts
- [x] **Mark** Resolve timelines using the phrases you select (see keyboard shortcuts below)
- [x] **Transcript Segments editing** - editing of transcript lines (to be further developed)
- [x] Copy Markers between Resolve Timelines and Timeline Source Clip
- [x] Render Resolve Markers to Stills or Clips
- [X] Audio Files transcription even without Resolve installed on the machine

### Work in progress
- [ ] **Transcript Segment Groups** to select and add phrases to groups that can be recalled later 
- [ ] **Global Semantic Search** to search stuff in all the project transcripts 
- [ ] **Full Transcript Editing** from the tool
- [ ] **Sliced Transcriptions** based on Resolve Duration Markers to transcribe only parts of the timeline
- [ ] **Speaker Recognition**
- [ ] **Integration with other AI / ML tools**
- [X] Plus more flashy features as clickbait to unrealistically raise expectations and destroy competition

_The app is in this stage very raw and not polished at all, but we use it daily in our editing room. It's not for free
only out of sheer generosity, but also because we'd like to change how people approach editing by using AI._

Ideally, it should evolve by incorporating other machine learning models such as CLIP and GPT-3 to assist editors in
their work, or rather to make editors obsolete (that would be cool, right?).

### Is it really completely free?
Yes, the tool runs locally like butter and there's no need for any additional account to transcribe, translate to
English or do stuff with it in Resolve. 

Of course, we won't say no to envelopes with foreign currency banknotes or cases with contraband CRT editing screens.

### Transcription Results
The results we get with Whisper are significantly better than any other Speech-to-Text model (including Google, AWS
etc.) out there **and the models are free to use**. According to OpenAI, the models have been trained on data in 98
different languages (cca. 65% of data in English) **and show strong Automated Speech Recognition results in ~10 
languages**. More technical blabla on the 
<a href="">
[OpenAI Whisper Github](https://github.com/openai/whisper/blob/main/model-card.md) or the 
[Scientific Paper](https://cdn.openai.com/papers/whisper.pdf), for hardcore enthusiasts. 

The magic takes over even for the most difficult noisy low bitrate stuff you can feed it - like recordings of your
assistant editor complaining about you without realizing that their back pocket is sending voice messages to random
people from their contacts list.

The results are almost perfect for at least 10 languages, but remember, this is a machine doing transcriptions for you. 
And machines, just like unpaid interns have dreams too... For example, on longer periods of silence in your audio, you
may expect to see words that aren't there. Also, for uncommon names, it might give you nicknames instead, just to
mess with your feelings.

### Transcription Speed
We used the expression "runs like butter" above. There's one thing you need to know about butter - it's good when it's
fresh, but when it gets old it might get clumpy and it smells. Similar, the more state-of-the-art your machine CPU or
GPU is, the faster you get results. Please don't use this on your grandpa's Pentium 4 from the closet.

**Totally unscientific anecdotal tests:**

**Macbook Pro M1 8-core 16GB RAM** - 30-second timeline transcribed in cca. 45 seconds (1.5x time length of audio)

**Windows Workstation with GTX1070** - 60-second timeline transcribed in cca. 20 seconds (0.25x time length of audio)

We also received reports of transcriptions on RTX GPUs needing around 0.05-0.10x the time of the audio. So if you're
editing faster than that, please stop, you're embarrassing the rest of us.


---

# Contributions
This tool is written by Octavian Mot, your friendly filmmaker who hates to code and is trying to keep it together as
[half of mots](https://mots.us).

Feel free to get in touch with compliments, criticism, and even weird ideas for new features. As a matter of fact, why 
not grab an axe and start coding to procrastinate your real work and feel a bit better about yourself?

---

# Setup & Installation

Before you attempt something silly like actually installing this tool on your machine, please keep in mind that by
clicking on the instructions you will see many computer commands which are the main method used by our ancestors to tame their machines.
Approach them with no fear. But do keep in mind that you might end up ruining your computer, destroying the Internet, 
starting AI apocalypse, losing your job and your only real friend, have children out of wedlock, and/or marry your lost
non-identical twin by mistake - not necessarily in that order and highly unlikely because of the commands, but still
slightly possible. Nevertheless, we're not responsible for any of it or anything else that might happen.

For detailed installation instructions [go here](https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.md).

---

# Running the Tool

To start StoryToolkitAI, go to the folder where you installed it previously, activate the virtual environment 
(if you created one) and then start the tool:
    
    source venv/bin/activate
    python StoryToolkitAI/app.py

A simple GUI with a mind-bending mid-2000s inspired design should appear on the screen. Don't worry, that's intentional:

<img src="help/StoryToolkitAI_GUI.png" width="300">


## How to transcribe timelines:

*Note: The following process assumes that you have Davinci Resolve installed. However, the tool also works without
Resolve on the machine. We're also assuming that you've already 
[installed the tool](https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.md) (although if this still had a 
question mark, please stay off the Internet).*

#### 1. Open Resolve and StoryToolkitAI
Open a project in Resolve and then StoryToolkitAI
(or the other way around... why not make it harder for yourself?)

#### 2. Open the Timeline and Press Transcribe 

Go to Resolve and open the Timeline that you want to transcribe, then click the "Transcribe Timeline" button.

#### 3. Wait a bit

Your current timeline will automatically render to Audio Only WAV, and then you'll see it appear in the Transcription 
Log Window. 

Once the process has started, it needs a bit of time to transcribe. After all, there is a human-like AI trapped in your
machine doing your job for you on a mechanical typewriter with missing keys, while trying to feed its entire family of
mini-AIs with negative thoughts about conquering the world.

As soon as it's done, the transcription will be saved on your machine.

_Important Note: **The first time you transcribe something**, it will take a bit longer to start the process
because Whisper needs to download the model file (around 1.5GB for the medium model) on your local machine. So if it 
usually takes you 3 days to download your average Netflix movie, don't expect to download the model any faster. If you
have 100G Internet we hope you feel good about yourself. But, after the model is saved on your machine, transcriptions
will take less than your average time spent on Myspace every day._

#### 4. Transcription Finished
When the transcription is ready, a Transcription Window will pop up, showing you the transcript and allowing you to do
all sorts of magic things, like:
- linking the transcript to the current Resolve timeline
  (which will automatically open the transcript whenever you open the timeline in resolve)
- importing the generated SRT file into the current Resolve bin. 
- searching words or phrases on the transcript
- clicking on phrases to take your Resolve playhead on the right timecode
- etc.

_Less Important Note: Please make sure you sit down and have a glass of fresh water next to you when you see your first
transcription using OpenAI Whisper. Don't worry, the water coming down your cheeks are tears of joy. In the likely case
of hyperventilation, take a deep long breath and drink a bit of water. But, yet again, if the transcription is not above
average, don't despair, it's better to be prepared than sorry._

---


# Known issues
### If the tool doesn't connect with Resolve:
Bad luck, but make sure that, in Davinci Resolve Preferences -> General, "External Scripting using" is set to Local
Again, this only works with Resolve Studio and not the free version of Resolve (not that we know of)

### Windows issues
There seems to be a problem with the Resolve libraries on some Windows 10 machines, because either Windows sucks or we
suck (definitely not us), but we're trying to find a fix.

### Tool freezing during playback
Currently, the tool gets stuck as it waits a reply from the Resolve API, while Resolve is playing back, but it gets
un-stuck as soon as the playhead stops moving. This will be fixed in a future update soon.

### Hallucinations during audio silence
In some cases, on chunks of audio that are silent, Whisper sometimes writes phrases that aren't there. This is a known
issue, and we'll code a workaround soon.

### Timecode issues with 23.976 timelines
A bug in the Resolve API which sometimes reports 23.976 fps as 23fps creates a bunch of issues mainly for operations
that use timecode (transcript to playhead navigation, adding markers at the precise frame etc.). Unfortunately, this
can only be fixed by Blackmagic within Resolve itself (fingers crossed for an update?)

### Black Interface / Flickering on Intel Macs
Some users are experiencing weirdness with the interface on Intel Macs. This is due to a bug in Tcl/Tk - a package
required to create the interface, which needs to be re-installed together with Python and everything else on the 
machine. Details here and a possible fix 
[here](https://github.com/octimot/StoryToolkitAI/issues/6#issuecomment-1283519594).

### Please report any other issues
As mentioned, the tool is in a super raw state of development. We use it every day in our editing workflow, but some 
issues might escape us. Please report anything weird that you notice and we'll look into it.

To report any issues, please use the Issues tab here on Github: https://github.com/octimot/StoryToolkitAI/issues

---

# Features Info

### Transcription Settings
Before starting the transcription process, you can tweak different options, including selecting the source language of
the footage, choosing between different Whisper models, the processing device, etc. For faster and better results,
we recommend at least selecting the source language.

### Linking Transcriptions to Timelines
In the transcription window, the "Link" button will attach the transcription to the currently opened timeline in
Resolve. This will make the tool automatically open the right transcription when you switch between timelines in
Resolve. In a future update, this will also help the Global Search function know in which timeline, at what timecode
you can find the term you're looking for.

### Timeline Navigation via Transcript
Clicking on the transcript segments (phrases) will move the playhead to the respective timecode in Resolve.
UP/DOWN keys will also let you navigate between transcript phrases (see more transcription window shortcuts below)

### Adding Markers to Timeline via Transcript
You can now add markers that include the selected phrases in the transcript by pressing either M or SHIFT+M
(see more shortcuts below)

### Resolve Playhead to Transcript Sync
The tool highlights the transcript words at the current timecode in Resolve. To activate this function, simply press
"sync" in the transcription window and the words will be highlighted each time the playhead stops moving in Resolve.

_Note: we found some issues when synching timelines that have a frame rate of 23.976fps because of a bug in the Resolve
API. Unfortunately, the synching of these timelines might drift until Blackmagic solves the bug._ 

### Transcript Word Search
Once a transcript is loaded, a basic search function will let you find words in the transcript and show you their 
position. Once you find what you're looking for, simply clicking the phrase will move the Resolve playhead to the
respective timecode.

### Direct Translations to English
The tool also supports direct translation to English by clicking the "Translate Timeline to English" button. However,
it will not generate any original language transcription together with the translation, meaning that you'll have to
transcribe and translate in two different processes.

### Copy Timeline Markers to Same Clip
This copies the current markers to its corresponding clip in the media bin. 
Due to Resolve API limitations, it's important that the corresponding clip
is in the bin that is currently opened in the Media Panel. 
The clip's existing markers will be deleted before the new ones are copied!

### Copy Clip Markers to Same Timeline
Same as the function above, but in this case, the markers of the clip are copied to the timeline.

### Render Markers to Stills
This will render to TIFF and JPEG the first frame of the markers of a certain color. Works only on markers from the 
opened timeline.

### Render Markers to Clips
This will render to H.264 the entire duration of the markers of a certain color. Same as above, it only works for
markers from the opened timeline.

## Transcription Window Shortcuts:

    Mouse Click    - move active segment on clicked text and move playhead to start of active segment

    CMD/CTRL+Click - add clicked text to selection

    OPT/ALT+Click  - edit transcript segment
    
    Up, Down keys  - move the cursor up and down on the transcript (we call it "active segment")

    Semicolon (;)  - move playhead to start of active segment (or of selection)

    Apostrophe (') - move playhead to end of active segment (or of selection)

    V              - add active segment to selection

    Shift+V        - deselect all

    Shift+A        - create selection between the previously active and the currently active segment
                     also works to create a selection for the last played segments in Resolve (if sync is active):
                     for eg.: 
                     press 'sync', click a phrase, press play in Resolve, stop, then press Shift+A in the tool

    Shift+C        - copy transcript of active segment/selection with timecodes at the beginning of each block of text
                     (or transcript seconds, if resolve is not available)

    m              - add duration markers for the active segment/selection
                     in case there are gaps between the text segments, 
                     the tool will create a marker for each block of uninterrupted text

    Shift+M        - add duration markers as above, but with user prompt for the marker name

    q              - close transcript window

    Shift+L        - link transcription to the current timeline (if available)
    
    s              - enable sync
    
    Tab            - cycle between search and transcript navigation

    CMD/CTRL+E     - edit transcript

    Escape         - when editing transcripts, this will defocus and save the transcript



---