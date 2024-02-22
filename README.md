# StoryToolkitAI

## Description

**StoryToolkitAI is a film editing tool that tries to understand your footage and helps you edit more efficiently with the assistance of AI.**

It transcribes, indexes scenes, helps you search through your footage, automatically selects and creates stories using large language models, like OpenAI GPT-4,
which you can then import into your editing software via EDL or XML.

The tool works locally on your machine, independent of any other editing software, but it also integrates with DaVinci Resolve Studio 18.

<img alt="StoryToolkitAI Interface" src="help/storytoolkitai_v0.19.0.png" width="750">

## Key Features
- [x] **Full video indexing and search** ([How-To](https://www.youtube.com/watch?v=UDwOvBqS1X8))
- [x] **Free Automatic Transcriptions** on your local machine
- [x] **Free Automatic Translation** to English on your local machine
- [x] **OpenAI GPT and ollama compatibility** - talk to AI about your content, or generate new ideas
- [x] **Search Content** intuitively without having to type in exact words
- [X] **Story Editor** - write screenplays containing your transcripts and export them for editing (EDL/XML/Fountain) (v. 0.20.1+)
- [X] **Translate transcripts** to other languages using OpenAI GPT (v. 0.22.0+)
- [X] **Ask AI to create Stories and Selections** based on your footage using OpenAI GPT (v. 0.22.0+)
- [X] **Automatic Speaker Detection** in transcripts (v. 0.23.0+)
- [X] **Project File Management** for more intuitive workflows and easier search
- [X] Automatic Question detection in transcripts
- [X] Transcript Groups - group transcript lines into whatever you need to find them easier
- [x] Multi-format export of transcripts, including SRT, TXT, AVID DS and as Fusion Text node
- [X] Import of **existing SRT files** 
- [X] Easy copy of timecoded transcript text to clipboard etc.

### Resolve Studio Integrations
- [x] **Mark and Navigate Resolve Timelines via Transcript**, plus other handy Resolve-only features
- [x] **Advanced Search** of Resolve timeline markers using AI
- [x] Copy Resolve timeline markers to transcript and vice-versa for advanced search
- [x] Direct import of subtitles into Resolve bin

### Planned Features
- [ ] **Automatic Topic Classification** to help you discover ideas in your transcripts
- [ ] **Use of local/custom LLM models**
- [ ] **Integration with other AI tools**
- [ ] **Integration with other software / standalone players**
- [X] Plus more flashy features as clickbait to unrealistically raise expectations and destroy competition

_Some of the above features are only available in the non-standalone version of the tool, but they will be available
in the standalone version in the next release._

For detailed features info, go [here](https://github.com/octimot/StoryToolkitAI/blob/main/FEATURES.md).

# Download, Setup & Installation

To download the latest standalone release, see [the releases page](https://github.com/octimot/StoryToolkitAI/releases).

However, the standalone releases will most likely always be behind the git version, 
so, if you're comfortable with the terminal / command line and want to always have access to the newest features, 
we recommend that you try to install the tool from source.

For detailed installation instructions
[go here](https://github.com/octimot/StoryToolkitAI/blob/main/INSTALLATION.md).

## Is it really free?
Yes, the tool runs locally and there's no need for any additional account to transcribe, index video or search.
These features will always be free as long as your machine supports them without external services. 

The only feature that now requires external services is the Assistant which relies on OpenAI API or storytoolkit.ai API.

We rely on the support of our [Patreon members](https://www.patreon.com/StoryToolkitAI)!
If you want to support development and get access to new features earlier, check out our [Patreon page](https://www.patreon.com/StoryToolkitAI).

---

## About data privacy
By the way, if you feel that your content is sensitive or subject to privacy laws, no worries: 
the tool does not send anything that you don't want to the Internet, it only uses your local machine to transcribe and 
translate your audio.

Currently, the only features that send data from your machine to the Internet are:
- The StoryToolkitAI API Key check to storytoolkit.ai (only when entered in the Settings Window)
- The Assistant, to OpenAI or storytoolkit.ai (only contexts and messages that you select and send).

The tool also checks for updates on every start.

---

# Code
This tool is coded by Octavian Mot, your unfriendly filmmaker who hates to code and tries to keep it together as
[half of mots](https://mots.us). Our team uses it daily in our editing room which allows us to update it with
features that we need and think will be useful to others.

But, keep in mind that the tool is still being actively developed, raw and unpolished.

Feel free to get in touch with criticism, or weird ideas for new features. 

The tool would be useless without using the following open source projects:
- [OpenAI Whisper](https://openai.com/blog/whisper/)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI ChatGPT](https://openai.com/blog/chat-gpt/)
- [pyannote.audio](https://github.com/pyannote/pyannote-audio/)
- [speechbrain](https://github.com/speechbrain/speechbrain)
- [spaCy](https://spacy.io/)
- [CustomTkinter](https://customtkinter.tomschimansky.com/)
- and many other packages listed in [requirements.txt](https://github.com/octimot/StoryToolkitAI/blob/main/requirements.txt)

## Code contributions are welcome!

Please open an issue with what you're trying to solve first and let's discuss it there.

---

# Known issues and Troubleshooting

For troubleshooting and possible solutions to known issues, [see the known issues section here](FEATURES.md#known-issues)
or [do a quick search in the Issues tab](https://github.com/octimot/StoryToolkitAI/issues?q=) 

Please report any problems directly in the Issues tab, here on Github: https://github.com/octimot/StoryToolkitAI/issues

---
