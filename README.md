# StoryToolkitAI

## Description

StoryToolkitAI is an editing extension for Davinci Resolve Studio 18. 

Among other things, it transcribes timelines directly from Resolve by rendering to Audio Only (mp4/wav) and then passing
the rendered file to OpenAI Whisper, a state-of-the-art speech recognition model. 
 
**TL;DR:
this tool is supernatural and will enhance your editing workflow like Harry Potter's Sword of Gryffindor or Batman's 
Utility Belt - depending which reference you relate to kind of shows what sort of person you are, but this is a
discussion for some other time.**

### Key Features
- [x] **Free Automatic Transcriptions in many languages** on your local machine directly from Resolve
- [x] **Free Automatic Translation** from many languages to English on your local machine from Resolve
- [x] Export of transcripts to multiple formats, including SRT
- [x] Import of transcript SRT file directly into Resolve
- [x] Transcription queuing which allows 
- [x] **Transcript Timeline Navigation** - simply click on a phrase and it takes the Resolve Playhead at the right timecode 
- [x] **Transcript Word Search** - allows you to find specific words or phrases in your transcripts
- [x] Copy Markers between Resolve Timelines and Timeline Source Clip
- [x] Render Resolve Markers to Stills or Clips
- [X] Audio Files transcription even without Resolve installed on the machine

### Work in progress
- [ ] **Mark In / Mark Out** directly from the tool to Resolve
- [ ] **Advanced Transcriptions** with more user input, like source language and selection
- [ ] **Global Search** to find words or phrases in project transcripts 
- [ ] **Transcript Editing** from the tool
- [ ] **Sliced Transcriptions** based on Resolve Duration Markers to transcribe only parts of the timeline
- [ ] **Speaker Recognition**
- [ ] **Integration with other AI / ML tools**
- [ ] Plus more flashy features as clickbait to unrealistically raise expectations and destroy competition

_The app is in this stage very raw and not polished at all, but we use it daily in our editing room. So we simply wanted
to make it for free for anyone to use. It's not only out of sheer generosity, but also because we'd like to
change how people approach editing by using AI. And yes, definitely as a bow to our new CPU-for-brains overlords. When
dirty stuff hits the fan and they take over, who do you think they'll spare first? Us slaves or you anti-AI 
"machine-can-t-be-artists" rebels?_

Ideally, it should evolve by incorporating other machine learning models such as CLIP and GPT-3 to assist editors in
their work, or rather to make them obsolete (that would be cool, right?).

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

The sorcery takes over even for the most difficult noisy low bitrate stuff you can feed it - like recordings of your
assistant editor with them complain about industry wages while Ubering people around in a noisy 98 Prius as a third job, 
without realizing that they're sending accidental whatsapp voice messages from their non-uber phone in their back pocket.
Seriously, be fair and pay folks what they're worth. If not, that day when you realize that you've just been replaced
completely by AI editors is really coming to get you.

Yes, this is a machine that is doing transcriptions for you. It's advanced AI sorcery indeed, but don't panic  if it
starts hallucinating if you feed it audio with long periods of silence. Misfires do happen, but there are smart people
(kind of) working on it. Not us, of course, it's the OpenAI Whisper people, but thanks for the compliment!

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

Feel free to get in touch with compliments or why not grab an ax and contribute with ideas or code to procrastinate your
real work and feel a bit better about yourself?

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
usually takes you 3 days do download your average Netflix movie, don't expect to download the model any faster. If you
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

### Windows issues
There seems to be a problem with the Resolve libraries on some Windows 10 machines, because either Windows sucks or we
suck (definitely not us), but we're trying to find a fix.

### Please report any other issues
As mentioned, the tool is in a super raw state of development. We use it everyday in our editing workflow, but some 
issues might escape us. To make sure that it works for the community, please report anything weird that you notice.

To report any issues, please use the Issues tab here on Github: https://github.com/octimot/StoryToolkitAI/issues

---

# Features Info

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

### Timeline Navigation via Transcript
For now, clicking on the transcript segments (phrases) will simply move the playhead to the respective timecode.

### Transcript Word Search
Once a transcript is loaded, a basic search function will let you find words in the transcript and show you their 
position. Once you find what you're looking for, simply clicking the phrase will move the Resolve playhead to the
respective timecode.


---