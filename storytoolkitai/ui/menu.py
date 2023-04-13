import tkinter as tk
from tkinter import *

import platform
import subprocess
import webbrowser

from storytoolkitai.core.logger import *

class UImenus:

    def __init__(self, toolkit_UI_obj):

        # declare the main objects
        self.toolkit_UI_obj = toolkit_UI_obj
        self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj
        self.stAI = toolkit_UI_obj.stAI

        self.app_items_obj = toolkit_UI_obj.app_items_obj

        # this is the main window
        self.root = self.toolkit_UI_obj.root

        # this is the main menubar (it's been declared in the main UI class to clear it before init)
        self.main_menubar = Menu(self.root)

        # reset it for now so we don't see weird menus before it is populated
        self.toolkit_UI_obj.root.config(menu=self.main_menubar)

        # keep track of the current window id
        self.current_window_id = None

        # create a variable to store the keep_on_top state of the current window
        self.keep_on_top_state = BooleanVar()

        # set the initial state to False
        self.keep_on_top_state.set(False)

        # keep track if the main window is kept on top
        self.keep_main_window_on_top_state = BooleanVar()

        # set the initial state to whatever the config says
        self.keep_main_window_on_top_state.set(self.root.attributes('-topmost'))

    def update_current_window_references(self):

        # for Windows, we use the self.last_focused_window,
        # considering that the menu bar is part of the main window
        # and whenever we click on the menu bar, the main window is focused
        if platform.system() == "Windows":
            self.current_window_id = self.toolkit_UI_obj.last_focused_window

        # for macOS, we use the self.current_focused_window variable
        elif platform.system() == 'Darwin':
            self.current_window_id = self.toolkit_UI_obj.current_focused_window

        # we should also check for Linux at some point...
        else:
            self.current_window_id = None

        # stop here if we don't have a window id
        if self.current_window_id is None:
            logger.debug('No window id found. Not updating the menu bar.')
            return

        # if this is the main window
        if self.current_window_id == 'main':

            # do not show the keep on top menu item
            self.main_menubar.windowsmenu.entryconfig('Keep window on top', state=DISABLED)

        # if this is any other window
        else:
            # show the keep on top menu item
            self.main_menubar.windowsmenu.entryconfig('Keep window on top', state=NORMAL)


        # also update the state of the keep on top menu item
        self.keep_on_top_state.set(self.toolkit_UI_obj.get_window_on_top_state(self.current_window_id))


    def load_menubar(self):

        # FILE MENU
        filemenu = Menu(self.main_menubar, tearoff=0)

        # add open transcription file menu item
        filemenu.add_command(label="Open transcription file...", command=self.toolkit_UI_obj.open_transcript)
        filemenu.add_separator()

        filemenu.add_command(label="Transcribe audio file...", command=self.transcribe_audio_files)
        filemenu.add_command(label="Translate audio file...", command=self.translate_audio_files)

        filemenu.add_separator()
        filemenu.add_command(label="Open configuration folder", command=self.open_userdata_dir)
        #filemenu.add_command(label="Open last folder", command=self.open_last_dir)

        self.main_menubar.add_cascade(label="File", menu=filemenu)

        # ADVANCED SEARCH MENU
        searchmenu = Menu(self.main_menubar, tearoff=0)


        #searchmenu.add_command(label="Search current transcription...", command=lambda: self.toolkit_UI_obj.open_advanced_search_window())

        #searchmenu.add_separator()
        searchmenu.add_command(label="Advanced Search in files...",
                               command=lambda: self.toolkit_UI_obj.open_advanced_search_window())
        searchmenu.add_command(label="Advanced Search in folders...",
                               command= lambda: self.toolkit_UI_obj.open_advanced_search_window(select_dir=True))
        #searchmenu.add_command(label="Search entire project...",
        #                       command=self.toolkit_UI_obj.open_advanced_search_window)

        self.main_menubar.add_cascade(label="Search", menu=searchmenu)

        # ASSISTANT MENU
        assistantmenu = Menu(self.main_menubar, tearoff=0)
        assistantmenu.add_command(label="Open Assistant...", command=self.toolkit_UI_obj.open_assistant_window)
        self.main_menubar.add_cascade(label="Assistant", menu=assistantmenu)

        # INTEGRATIONS MENU
        self.main_menubar.integrationsmenu = integrationsmenu = Menu(self.main_menubar, tearoff=0)

        # add a title in the menu
        integrationsmenu.add_command(label="Connect to Resolve API",
                                     command=self.toolkit_UI_obj.on_connect_resolve_api_press)
        integrationsmenu.add_command(label="Disable Resolve API",
                                     command=self.toolkit_UI_obj.on_disable_resolve_api_press)

        # determine the state of the two menu items depending whether Resolve API is disabled or not
        if not self.toolkit_ops_obj.disable_resolve_api:
            integrationsmenu.entryconfig("Connect to Resolve API", state="disabled")
            integrationsmenu.entryconfig("Disable Resolve API", state="normal")
        else:
            integrationsmenu.entryconfig("Connect to Resolve API", state="normal")
            integrationsmenu.entryconfig("Disable Resolve API", state="disabled")

        self.main_menubar.add_cascade(label="Integrations", menu=integrationsmenu)


        # ADD WINDOWS MENU
        self.main_menubar.windowsmenu = windowsmenu = Menu(self.main_menubar, tearoff=0)

        # add a keep main on top menu item
        windowsmenu.add_checkbutton(label="Keep main window on top",
                                    variable=self.keep_main_window_on_top_state,
                                    command=self.keep_main_window_on_top)

        # add a keep on top menu item
        windowsmenu.add_checkbutton(label="Keep window on top",
                                    variable=self.keep_on_top_state,
                                    command=self.keep_current_window_on_top)

        # add cascade
        self.main_menubar.add_cascade(label="Window", menu=windowsmenu)

        # HELP MENU
        helpmenu = Menu(self.main_menubar, tearoff=0)

        # if this is not on MacOS, add the about button in the menu
        if platform.system() != 'Darwin':

            # helpmenu.add_separator()
            filemenu.add_command(label="Preferences...", command=self.app_items_obj.open_preferences_window)
            # filemenu.add_command(label="Quit", command=lambda: self.toolkit_UI_obj.on_exit())

            helpmenu.add_command(label="About", command=self.about_dialog)
            helpmenu.add_separator()

        # otherwise show stuff in MacOS specific menu places
        else:

            # change the link in the about dialogue
            self.toolkit_UI_obj.root.createcommand('tkAboutDialog', self.app_items_obj.open_about_window)
            self.toolkit_UI_obj.root.createcommand('tk::mac::ShowPreferences',
                                                   self.app_items_obj.open_preferences_window)
            # self.toolkit_UI_obj.root.createcommand('tkPreferencesDialog', self.app_items_obj.open_about_window)

            # also bind to the cmd+q key combination
            self.toolkit_UI_obj.root.createcommand("tk::mac::Quit", lambda: self.toolkit_UI_obj.on_exit())

            # see https://tkdocs.com/tutorial/menus.html#platformmenus
            # menubar = Menu(self.toolkit_UI_obj.root)
            # appmenu = Menu(menubar, name='apple')
            # menubar.add_cascade(menu=appmenu)
            # appmenu.add_command(label='About My Application')
            # appmenu.add_separator()

            system_menu = tk.Menu(self.main_menubar, name='apple')
            # system_menu.add_command(command=lambda: self.w.call('tk::mac::standardAboutPanel'))
            # system_menu.add_command(command=lambda: self.updater.checkForUpdates())

            # system_menu.entryconfigure(0, label="About")
            system_menu.entryconfigure(1, label="Check for Updates...")
            # self.main_menubar.add_cascade(menu=system_menu)

            helpmenu.add_command(label="Go to project page", command=self.open_project_page)

        self.main_menubar.add_cascade(label="Help", menu=helpmenu)
        helpmenu.add_command(label="Features info", command=self.open_features_info)
        helpmenu.add_command(label="Report an issue", command=self.open_issue)
        helpmenu.add_command(label="Made by mots", command=self.open_mots)

        self.toolkit_UI_obj.root.config(menu=self.main_menubar)

    def keep_current_window_on_top(self):

        if self.current_window_id is None:
            logger.debug('Unable to determine current window id.')
            return

        # simply toggle the state of the window using the window_on_top function
        keep_on_top = self.toolkit_UI_obj.window_on_top(self.current_window_id)

        # and update the checkbutton state
        self.keep_on_top_state.set(keep_on_top)

    def keep_main_window_on_top(self):

        # toggle the state of the main window using the window_on_top function
        keep_on_top = self.toolkit_UI_obj.window_on_top('main')

        # and update the checkbutton state
        self.keep_main_window_on_top_state.set(keep_on_top)


    def transcribe_audio_files(self):

        self.toolkit_ops_obj.prepare_transcription_file(
            toolkit_UI_obj=self.toolkit_UI_obj, task='transcribe', select_files=True)

    def translate_audio_files(self):

        self.toolkit_ops_obj.prepare_transcription_file(
            toolkit_UI_obj=self.toolkit_UI_obj, task='translate', select_files=True)

    def donothing(self):
        return

    def open_last_dir(self):

        global initial_target_dir

        # if we're on a Mac, open the user data dir in Finder
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', initial_target_dir])

        # if we're on Windows, open the user data dir in Explorer
        elif platform.system() == 'Windows':
            subprocess.call(['explorer', initial_target_dir])

        # if we're on Linux, open the user data dir in the file manager
        elif platform.system() == 'Linux':
            subprocess.call(['xdg-open', initial_target_dir])

    def open_userdata_dir(self):
        # if we're on a Mac, open the user data dir in Finder
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', self.stAI.user_data_path])

        # if we're on Windows, open the user data dir in Explorer
        elif platform.system() == 'Windows':
            subprocess.call(['explorer', self.stAI.user_data_path])

        # if we're on Linux, open the user data dir in the file manager
        elif platform.system() == 'Linux':
            subprocess.call(['xdg-open', self.stAI.user_data_path])

    def open_project_page(self):
        webbrowser.open_new("http://storytoolkit.ai")
        return

    def open_features_info(self):
        webbrowser.open_new("https://github.com/octimot/StoryToolkitAI/blob/main/FEATURES.md")
        return

    def open_issue(self):
        webbrowser.open_new("https://github.com/octimot/StoryToolkitAI/issues")
        return

    def about_dialog(self):
        self.app_items_obj.open_about_window()

    def open_mots(self):
        webbrowser.open_new("https://mots.us")
        return