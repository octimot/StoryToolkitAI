# StoryToolkitAI Installation Instructions

[Click here to the main project page](https://github.com/octimot/StoryToolkitAI)

## Installing the Standalone version
If you don't want to get your hands dirty with terminal commands, check if there is a release available for your 
platform [here](https://github.com/octimot/StoryToolkitAI/releases).

We do, however, recommend doing your best to install the git version of the tool using the instructions
below. This would allow you to get the latest features and bug fixes as soon as they are released.

### StoryToolkitAI is free but we need your help

The development of Storytoolkit AI depends highly on the support we get from our Patreon community, so
[please consider supporting the development](https://www.patreon.com/StoryToolkitAI) if you find this tool useful
in your work.

---

## Installing the tool from source (GIT version)

### Quick Info before we start

#### Caution
If you want to try to install from source, please keep in mind that you might end up ruining your computer, 
destroying the Internet, starting AI apocalypse, losing your job, and/or marry your lost non-identical twin by mistake - 
not necessarily in that order and highly unlikely as a result of trying to install this, but still slightly possible. 

Nevertheless, we're not responsible for any of it or anything else that might happen. In a low-chance worst-case 
scenario, some stuff might not work at all on your computer, and you'll need pro help to fix them back.

#### Requirements

Our installations are on MacOS 12.6+, MacOS 14.4.1+ running on M1, and Windows 10 machines in our editing room, 
but the scripts should run fine on other CPUs and GPUs. 
For both production and development we're mostly using Python 3.10.11, but slowly migrating to 3.11.

_Note: The tool worked fine on Python 3.9, but some packages are now optimized for Python 3.10 and Python 3.11 
Python 3.9 support will no longer be possible in the very near future._

**The Resolve API integration only works on Resolve Studio 18 (not on the free version, and certainly not earlier 
versions).**

#### For Patrons 

_If you have access to the early-updates private repo and don't know how to clone or pull from it, 
message us on Patreon and we'll help you make it work._

## Mac OS

#### 0. Open Terminal

Using Finder, go to the Folder where you want to install StoryToolkitAI.
Right-click on it and select "New Terminal at Folder". 

Once a terminal window opens, go through the following steps.

#### 1. Homebrew will make your life easier:

Install Homebrew, if you don't have it already, by running this command in the terminal:

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

In case Homebrew installation fails, please check [this page](https://docs.brew.sh/Common-Issues) for troubleshooting.

The most common reason why brew installations fail is because Xcode Command Line Tools isn't installed. 
So, install that using `xcode-select --install`.

#### 2. You'll need Python 3.10, Python Tkinter, Git, FFMPEG and Rust:

    brew install python@3.10
    brew install python-tk@3.10
    brew install git
    brew install ffmpeg
    brew install rust

_Note: we're slowly migrating to Python 3.11, so please keep an eye on the requirements in the future. 
If you're feeling brave, you can try installing Python 3.11 instead of 3.10 by modifying the above and below commands._

#### 3. Download StoryToolkitAI:

Download from GitHub using this command:

    git clone https://github.com/octimot/StoryToolkitAI.git

This should download the app in the folder that you chose.

#### 4. Set up a virtual environment
Create a virtual environment to install all the packages the tool needs in isolation from the rest of your system:

    python3.10 -m venv venv

Right now, your installation folder should contain 2 other folders, and the tree should look like this:

    YOUR_INSTALLATION_FOLDER
    +- StoryToolkitAI
    +- venv

#### 5. Install all the stuff the tool requires:
To install the requirements inside the virtual environment, run:

    source venv/bin/activate
    pip install -r StoryToolkitAI/requirements.txt

_Note: If something fails during the installation of the OpenAI Whisper package, please read the setup instructions [here](https://github.com/openai/whisper?tab=readme-ov-file#setup)._

_Note 2: The `source` command above activates your virtual environment. Make sure you're installing everything inside
the virtual environment, by checking if your prompt line starts with `(venv)` before everything else._

##### CUDA support for Mac
In the unlikely situation where you have an NVIDIA CUDA GPU on your Mac, see the CUDA instructions in the Windows section below to enable CUDA support.

#### That's it!
You should now be able to start the tool using this command, from your installation folder:

    venv/bin/python StoryToolkitAI/storytoolkitai

_Note: Unless you know how virtual environments work, make sure you **always** issue the above command from your installation folder,
otherwise the tool will not work._
    
## Windows

#### 0. Open Command Prompt
First, create the folder where you want to install StoryToolkitAI. 
Then, open the Command Prompt and navigate to that folder - with Windows Explorer open in the installation folder,
type in `cmd` in the location bar above then press Enter, and your Command Prompt should start directly in the
installation folder.

#### 1. Download and install Python
Download the latest Python 3.10 version from [the official Python website](https://www.python.org/downloads/).

_Note: Do not use the Python installers available from the Windows Store. Only use other Python installers / versions
if you know what you're doing._

_Note 2: we're slowly migrating to Python 3.11, so please keep an eye on the requirements in the future. 
If you're feeling brave, you can try use 3.11 instead of 3.10 below._

Then simply install it on your machine using the default settings.

To check if you installed the right version, open the Command Prompt and run:

    py --version

Something like `Python 3.10.11` should appear. Anything else besides 3.10.X means that you're in uncharted
territories! If that is the case, we recommend uninstalling all Python versions (if you don't need them of course)
and reinstalling Python 3.10.

Make sure you have `virtualenv` installed by running:

    py -3.10 -m pip install virtualenv

#### 2. Download and install GIT for Windows

Download it from [here](https://git-scm.com/download/win) and then install it.

#### 3. Download and install FFMPEG via Chocolatey
The simplest way to install FFMPEG on windows is to use a package manager like [Choco](https://chocolatey.org/install), 
but feel free to skip this step if you already have FFMPEG or if you know of a better way to install it.

Open PowerShell as Admin, and run:

    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

If you're running into issues please read the [Choco installation guide](https://chocolatey.org/install).

Once Choco is installed, you can install FFMPEG using this command:

    choco install ffmpeg

#### 4. Download StoryToolkitAI:

Open the Command Prompt and navigate to the folder where you want to install StoryToolkitAI. Then run:

    git clone https://github.com/octimot/StoryToolkitAI.git

#### 5. Set up a virtual environment
Create a virtual environment to install all the packages the tool needs in isolation from the rest of your system:

    py -3.10 -m virtualenv venv

Right now, your installation folder should contain 2 other folders, and the tree should look like this:
    
    YOUR_INSTALLATION_FOLDER
    +- StoryToolkitAI
    +- venv

#### 6. Install all the stuff the tool requires:
To install the requirements inside the virtual environment, run:

    venv\Scripts\activate.bat
    pip install -r StoryToolkitAI\requirements.txt

##### CUDA support
If you are running the tool on a machine with an NVIDIA CUDA GPU, make sure you install Torch with CUDA:
    
    pip uninstall torch torchaudio torchvision
    pip cache purge
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu118

_Note: If Resolve Studio is not turned on or not available, the transcription and translation functions will work on 
normal wav files too. Simply press the transcribe or translate buttons and follow the process._

#### That's it!
You should now be able to start the tool using this command, from your installation folder:

    venv\Scripts\python StoryToolkitAI\storytoolkitai

_Note: Unless you know how virtual environments work, make sure you **always** issue the above command from your installation folder,
otherwise the tool will not work._

## Running the git version

The below instructions assume you've already opened Terminal or Command Prompt and navigated to your installation folder.
If you want to run the tool from a different folder and you know what you're doing, make sure you change the below paths accordingly.

### On windows:
From your installation folder:

    venv\Scripts\python StoryToolkitAI\storytoolkitai

### On Mac OS:
From your installation folder:

    venv/bin/python StoryToolkitAI/storytoolkitai

The tool should pop up now on the screen

<img src="help/storytoolkitai_v0.19.0.png" width="600">

## Updates on the git version of the tool
The tool should be able to auto-update itself if you're running the git version and choosing to install the update.

To update the tool manually, simply pull the latest changes from the repository. 
For this, you need to go inside the StoryToolkitAI folder from your installation folder (`YOUR_INSTALLATION_FOLDER/StoryToolkitAI`) and run:

    git pull

## Feedback

Feedback regarding these instructions is very welcome and might help others! 

Please let us know if you have any issues or suggestions for improvement via the 
[issues page](https://github.com/octimot/StoryToolkitAI/issues).
