import tkinter as tk
from tkinter import *
from tkinter import messagebox

import platform
import subprocess
import webbrowser

from storytoolkitai.core.logger import *
from storytoolkitai.core.toolkit_ops import NLE

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
            self.load_menu_for_main()

        # if this is any other window
        else:
            self.load_menu_for_other(window_id=self.current_window_id,
                                     window_type=self.toolkit_UI_obj.get_window_type(self.current_window_id))


        # also update the state of the keep on top menu item
        self.keep_on_top_state.set(self.toolkit_UI_obj.get_window_on_top_state(self.current_window_id))

    def load_menu_for_main(self):
        '''
        This function loads the menu bar considering that we're now in the main window.
        '''

        # disable show the keep on top menu item
        self.windowsmenu.entryconfig('Keep window on top', state=DISABLED)

        # disable the close window menu item
        self.windowsmenu.entryconfig('Close window', state=DISABLED)

        self.disable_menu_for_non_transcriptions()

    def load_menu_for_other(self, window_id=None, window_type=None):
        '''
        This function loads the menu bar considering that we're now in any other window except the main window.
        '''

        # enable the keep on top menu item
        self.windowsmenu.entryconfig('Keep window on top', state=NORMAL)

        # enable the close window menu item (if a close_action exists)
        # (if the window has a close_action, it means that it can be closed)
        if hasattr(self.toolkit_UI_obj.windows[window_id], 'close_action') \
            and self.toolkit_UI_obj.windows[window_id].close_action is not None:
            self.windowsmenu.entryconfig('Close window', state=NORMAL)

        # if the window doesn't have a close_action, disable the menu item
        else:
            self.windowsmenu.entryconfig('Close window', state=DISABLED)


        # EDIT MENU FUNCTIONS

        # enable find menu item if the window has a find function
        if hasattr(self.toolkit_UI_obj.windows[window_id], 'find') \
            and self.toolkit_UI_obj.windows[window_id].find is not None:

            self.editmenu.entryconfig('Find...', state=NORMAL, command=self.toolkit_UI_obj.windows[window_id].find)

        # enable select all menu item depending on the window type
        if window_type == 'transcription':
            self.load_menu_for_transcriptions(window_id)

        else:
            self.disable_menu_for_non_transcriptions()
            self.editmenu.entryconfig('Select All',
                                      state=NORMAL,
                                      command=lambda: self.pass_key_event(window_id, '<'+self.toolkit_UI_obj.ctrl_cmd_bind+'-a>'))

    def load_menu_for_transcriptions(self, window_id):

        # enable the advanced search menu items relevant for transcriptions
        self.searchmenu.entryconfig("Advanced Search in current transcript...", state=NORMAL,
                                    command=lambda:
                                    self.toolkit_UI_obj.open_advanced_search_window(
                                        transcription_window_id=window_id)
                                    )

        # enable this when group search is implemented
        # self.searchmenu.entryconfig("Advanced Search in current transcription...", state=NORMAL)

        # enable this for project search
        # self.searchmenu.entryconfig("Advanced Search in current project...", state=NORMAL)

        # if segments are selected, enable the menu items for segment selection
        self.toggle_menu_for_transcription_selections(window_id)

        # toggle the menu items for resolve related functions
        if NLE.is_connected() and NLE.current_timeline is not None:
            self.enable_menu_for_resolve_transcription(window_id)
        else:
            self.disable_menu_for_resolve_transcription()

    def toggle_menu_for_transcription_selections(self, window_id):

        # if segments are selected, enable the menu items for segment selection
        if self.toolkit_UI_obj.t_edit_obj.has_selected_segments(window_id):
            self.enable_menu_for_transcription_selections(window_id)

        # otherwise, disable them
        else:
            self.disable_menu_for_transcription_selections()

    def enable_menu_for_transcription_selections(self, window_id):
        '''
        This is used to enable the menu items
        that are only relevant for transcription windows,
        when a user has selected segments.
        '''

        self.editmenu.entryconfig('Select All',
                                  state=NORMAL,
                                  command=lambda window_id=window_id:
                                    self.toolkit_UI_obj.t_edit_obj.button_select_deselect_all(window_id)
                                  )

        self.editmenu.entryconfig("Copy to Clipboard with TC", state=NORMAL,
                                  command=lambda window_id=window_id:
                                  self.toolkit_UI_obj.t_edit_obj.button_copy_segments_to_clipboard(
                                      window_id,
                                      with_timecodes=True,
                                      per_line=True
                                      )
                                  )
        self.editmenu.entryconfig("Copy to Clipboard with Block TC", state=NORMAL,
                                  command=lambda window_id=window_id:
                                  self.toolkit_UI_obj.t_edit_obj.button_copy_segments_to_clipboard(
                                      window_id,
                                      with_timecodes=True
                                      )
                                  )

        self.editmenu.entryconfig("Add to Group", state=NORMAL,
                                  command=lambda window_id=window_id:
                                  self.toolkit_UI_obj.t_edit_obj.button_add_to_group(window_id=window_id, only_add=True)
        )


        self.editmenu.entryconfig("Re-transcribe", state=NORMAL,
                                  command=lambda window_id=window_id:
                                  self.toolkit_UI_obj.t_edit_obj.button_retranscribe(window_id=window_id)
                                  )

        #self.editmenu.entryconfig("Delete segment", state=NORMAL,
        #                          )

        self.assistantmenu.entryconfig("Send to Assistant", state=NORMAL,
                                       command=lambda window_id=window_id:
                                       self.toolkit_UI_obj.t_edit_obj.button_send_to_assistant(window_id=window_id,
                                                                                               with_timecodes=False)
                                       )
        self.assistantmenu.entryconfig("Send to Assistant with TC", state=NORMAL,
                                       command=lambda window_id=window_id:
                                        self.toolkit_UI_obj.t_edit_obj.button_send_to_assistant(window_id=window_id,
                                                                                                with_timecodes=True)
                                       )

        if not NLE.is_connected() or NLE.current_timeline is None:
            self.disable_menu_for_resolve_transcription_selections()
        else:
            self.enable_menu_for_resolve_transcription_selections(window_id)

    def disable_menu_for_transcription_selections(self):
        '''
        This is used to enable the menu items
        that are only relevant for transcription windows,
        when a user has selected segments.
        '''

        self.editmenu.entryconfig('Copy to Clipboard with TC', state=DISABLED)
        self.editmenu.entryconfig('Copy to Clipboard with Block TC', state=DISABLED)
        self.editmenu.entryconfig('Add to Group', state=DISABLED)
        self.editmenu.entryconfig('Re-transcribe', state=DISABLED)
        #self.editmenu.entryconfig('Delete segment', state=DISABLED)

        self.assistantmenu.entryconfig("Send to Assistant", state=DISABLED)
        self.assistantmenu.entryconfig("Send to Assistant with TC", state=DISABLED)

        self.disable_menu_for_resolve_transcription_selections()

    def disable_menu_for_resolve_transcription_selections(self):
        '''
        This is used to disable the menu items
        that are only relevant for transcription windows,
        when a user has not selected segments or Resolve is not connected.
        '''
        self.integrationsmenu.entryconfig("Quick Selection to Markers", command=self.donothing, state=DISABLED)
        self.integrationsmenu.entryconfig("Selection to Markers", command=self.donothing, state=DISABLED)

    def enable_menu_for_resolve_transcription_selections(self, window_id):
        '''
        This is used to enable the menu items
        that are only relevant for transcription windows,
        when a user has selected segments and Resolve is connected.
        '''

        self.integrationsmenu.entryconfig("Quick Selection to Markers", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj
                                          .button_segments_to_markers(window_id=window_id, prompt=False)
                                          )
        self.integrationsmenu.entryconfig("Selection to Markers", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj
                                          .button_segments_to_markers(window_id=window_id, prompt=True)
                                          )

    def enable_menu_for_resolve_transcription(self, window_id):
        '''
        This is used to enable the menu items
        that are only relevant for transcriptions
        when Resolve is connected.
        '''


        self.integrationsmenu.entryconfig("Markers to Segments", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj.button_markers_to_segments(window_id=window_id)
                                          )

        self.integrationsmenu.entryconfig("Move Playhead to Selection Start", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj.go_to_selected_time(window_id=window_id,
                                                                                             position='start')
                                          )
        self.integrationsmenu.entryconfig("Move Playhead to Selection End", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj.go_to_selected_time(window_id=window_id,
                                                                                             position='end')
                                          )

        self.integrationsmenu.entryconfig("Align Segment Start to Playhead", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj.align_line_to_playhead(
                                              window_id=window_id,
                                              position='start')
                                          )
        self.integrationsmenu.entryconfig("Align Segment End to Playhead", state=NORMAL,
                                          command=lambda window_id=window_id:
                                          self.toolkit_UI_obj.t_edit_obj.align_line_to_playhead(
                                              window_id=window_id,
                                              position='end')
                                          )

    def disable_menu_for_resolve_transcription(self):
        '''
        This is used to disable the menu items
        that are only relevant for transcriptions
        when Resolve is connected.
        '''
        self.integrationsmenu.entryconfig("Move Playhead to Selection Start", command=self.donothing, state=DISABLED)
        self.integrationsmenu.entryconfig("Move Playhead to Selection End", command=self.donothing, state=DISABLED)
        self.integrationsmenu.entryconfig("Align Segment Start to Playhead", state=DISABLED)
        self.integrationsmenu.entryconfig("Align Segment End to Playhead", state=DISABLED)

        self.integrationsmenu.entryconfig("Markers to Segments", state=DISABLED)

    def disable_menu_for_non_transcriptions(self):
        '''
        This is used to disable the menu items
        that are only relevant for transcriptions.
        '''
        # disable transcription selection menu items
        # (including ones that are relevant for selections with Resolve connected)
        self.disable_menu_for_transcription_selections()

        # disable transcription resolve menu items
        self.disable_menu_for_resolve_transcription()

        # disable other transcription menu items
        #self.searchmenu.entryconfig("Advanced Search in current transcription...", state=DISABLED)

        self.searchmenu.entryconfig("Advanced Search in current transcript...", state=DISABLED)
        #self.searchmenu.entryconfig("Advanced Search in current project...", state=DISABLED)



    def pass_key_event(self, window_id, key_event):
        '''
        This function passes a key event to the current window.
        '''

        if window_id is None or key_event is None or window_id not in self.toolkit_UI_obj.windows:
            return

        self.toolkit_UI_obj.windows[window_id].event_generate(key_event)

    def load_menubar(self):
        '''
        This loads all the items in the menu bar.
        Using update_current_window_references()
        we can then update the menu bar depending on which window is currently focused.
        '''

        # FILE MENU
        self.filemenu = Menu(self.main_menubar, tearoff=0)

        # add open transcription file menu item
        self.filemenu.add_command(label="Open transcription file...", command=self.toolkit_UI_obj.open_transcript)
        self.filemenu.add_separator()

        self.filemenu.add_command(label="Transcribe audio file...", command=self.transcribe_audio_files)
        self.filemenu.add_command(label="Translate audio file...", command=self.translate_audio_files)

        self.filemenu.add_separator()
        self.filemenu.add_command(label="Open configuration folder", command=self.open_userdata_dir)
        self.filemenu.add_command(label="Open last used folder", command=self.open_last_dir)

        self.main_menubar.add_cascade(label="File", menu=self.filemenu)


        # EDIT MENU
        self.editmenu = Menu(self.main_menubar, tearoff=0)

        self.editmenu.add_command(label="Find...", command=self.donothing,
                             accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+f")

        self.editmenu.add_command(label="Select All", command=self.donothing,
                             accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+a")

        self.editmenu.entryconfig('Find...', state=DISABLED)

        # EDIT - TRANSCRIPT related menu items
        # but disable all edit - transcript menu items
        # and let them be enabled when a transcript window is focused (see update_current_window_references())
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Copy to Clipboard with TC", command=self.donothing, state=DISABLED,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+Shift+c")
        self.editmenu.add_command(label="Copy to Clipboard with Block TC", command=self.donothing, state=DISABLED,
                                  accelerator="Shift+c")
        self.editmenu.add_command(label="Add to Group", command=self.donothing, state=DISABLED,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+g")
        self.editmenu.add_command(label="Re-transcribe", command=self.donothing, state=DISABLED,
                                  accelerator='t')
        #self.editmenu.add_command(label="Delete segment", command=self.donothing, state=DISABLED,
        #                          accelerator="BackSpace")

        # show the edit menu
        self.main_menubar.add_cascade(label="Edit", menu=self.editmenu)


        # ADVANCED SEARCH MENU
        self.searchmenu = Menu(self.main_menubar, tearoff=0)

        self.searchmenu.add_command(label="Advanced Search in files...",
                               command=lambda: self.toolkit_UI_obj.open_advanced_search_window())
        self.searchmenu.add_command(label="Advanced Search in folders...",
                               command= lambda: self.toolkit_UI_obj.open_advanced_search_window(select_dir=True))
        #searchmenu.add_command(label="Search entire project...",
        #                       command=self.toolkit_UI_obj.open_advanced_search_window)

        # ADVANCED SEARCH - TRANSCRIPT related menu items
        # but disabled for now
        # let them be enabled when a transcript window is focused (see update_current_window_references())
        self.searchmenu.add_separator()
        #self.searchmenu.add_command(label="Advanced Search in current project...", command=self.donothing,
        #                            state=DISABLED)
        #self.searchmenu.add_command(label="Advanced Search in current transcription...", command=self.donothing,
        #                            state=DISABLED)
        self.searchmenu.add_command(label="Advanced Search in current transcript...", command=self.donothing,
                                    state=DISABLED)

        self.main_menubar.add_cascade(label="Search", menu=self.searchmenu)

        # ASSISTANT MENU
        self.assistantmenu = Menu(self.main_menubar, tearoff=0)
        self.assistantmenu.add_command(label="Open Assistant...", command=self.toolkit_UI_obj.open_assistant_window)

        # ASSISTANT - TRANSCRIPT related menu items
        self.assistantmenu.add_separator()
        self.assistantmenu.add_command(label="Send to Assistant", command=self.donothing, state=DISABLED,
                                  accelerator='o')
        self.assistantmenu.add_command(label="Send to Assistant with TC", command=self.donothing, state=DISABLED,
                                  accelerator="Shift+o")

        self.main_menubar.add_cascade(label="Assistant", menu=self.assistantmenu)

        # INTEGRATIONS MENU
        self.integrationsmenu = Menu(self.main_menubar, tearoff=0)

        # add a title in the menu
        self.integrationsmenu.add_command(label="Connect to Resolve API",
                                     command=self.toolkit_UI_obj.on_connect_resolve_api_press)
        self.integrationsmenu.add_command(label="Disable Resolve API",
                                     command=self.toolkit_UI_obj.on_disable_resolve_api_press)

        # INTEGRATIONS - TRANSCRIPT related menu items
        self.integrationsmenu.add_separator()
        self.integrationsmenu.add_command(label="Quick Selection to Markers", command=self.donothing, state=DISABLED,
                                          accelerator="m")
        self.integrationsmenu.add_command(label="Selection to Markers", command=self.donothing, state=DISABLED,
                                          accelerator="Shift+m")
        self.integrationsmenu.add_command(label="Markers to Segments", command=self.donothing, state=DISABLED,
                                          accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+m")
        self.integrationsmenu.add_command(label="Move Playhead to Selection Start", command=self.donothing, state=DISABLED,
                                          accelerator=';')
        self.integrationsmenu.add_command(label="Move Playhead to Selection End", command=self.donothing, state=DISABLED,
                                          accelerator="'")
        self.integrationsmenu.add_command(label="Align Segment Start to Playhead", command=self.donothing, state=DISABLED,
                                          accelerator=':')
        self.integrationsmenu.add_command(label="Align Segment End to Playhead", command=self.donothing, state=DISABLED,
                                          accelerator='"')

        # determine the state of the two menu items depending whether Resolve API is disabled or not
        if not self.toolkit_ops_obj.disable_resolve_api:
            self.integrationsmenu.entryconfig("Connect to Resolve API", state="disabled")
            self.integrationsmenu.entryconfig("Disable Resolve API", state="normal")
        else:
            self.integrationsmenu.entryconfig("Connect to Resolve API", state="normal")
            self.integrationsmenu.entryconfig("Disable Resolve API", state="disabled")

        self.main_menubar.add_cascade(label="Integrations", menu=self.integrationsmenu)


        # ADD WINDOWS MENU
        self.windowsmenu = Menu(self.main_menubar, tearoff=0)

        # add a keep main on top menu item
        self.windowsmenu.add_checkbutton(label="Keep main window on top",
                                    variable=self.keep_main_window_on_top_state,
                                    command=self.keep_main_window_on_top)

        # add a keep on top menu item
        self.windowsmenu.add_checkbutton(label="Keep window on top",
                                    variable=self.keep_on_top_state,
                                    command=self.keep_current_window_on_top)

        # add a close window menu item
        self.windowsmenu.add_command(label="Close window",
                                command=self.close_current_window,
                                accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+Shift+W")

        # add open groups menu item
        self.windowsmenu.add_separator()
        self.windowsmenu.add_command(label="Open Transcript Groups", command=self.donothing,
                                     state="disabled", accelerator="Shift+G")

        # add cascade
        self.main_menubar.add_cascade(label="Window", menu=self.windowsmenu)

        # HELP MENU
        self.helpmenu = Menu(self.main_menubar, tearoff=0)

        # if this is not on MacOS, add the about button in the menu
        if platform.system() != 'Darwin':

            # helpmenu.add_separator()
            self.filemenu.add_command(label="Preferences...", command=self.app_items_obj.open_preferences_window)
            # filemenu.add_command(label="Quit", command=lambda: self.toolkit_UI_obj.on_exit())

            self.helpmenu.add_command(label="About", command=self.about_dialog)
            self.helpmenu.add_separator()

        # otherwise show stuff in MacOS specific menu places
        # see https://tkdocs.com/tutorial/menus.html#platformmenus
        else:

            # change the link in the about dialogue
            self.toolkit_UI_obj.root.createcommand('tkAboutDialog', self.app_items_obj.open_about_window)
            self.toolkit_UI_obj.root.createcommand('tk::mac::ShowPreferences',
                                                   self.app_items_obj.open_preferences_window)
            # self.toolkit_UI_obj.root.createcommand('tkPreferencesDialog', self.app_items_obj.open_about_window)

            # also bind to the cmd+q key combination
            self.toolkit_UI_obj.root.createcommand("tk::mac::Quit", lambda: self.toolkit_UI_obj.on_exit())

            system_menu = tk.Menu(self.main_menubar, name='apple')
            # system_menu.add_command(command=lambda: self.w.call('tk::mac::standardAboutPanel'))
            # system_menu.add_command(command=lambda: self.updater.checkForUpdates())

            # system_menu.entryconfigure(0, label="About")
            system_menu.entryconfigure(1, label="Check for Updates...")
            # self.main_menubar.add_cascade(menu=system_menu)

            self.helpmenu.add_command(label="Go to project page", command=self.open_project_page)

        self.main_menubar.add_cascade(label="Help", menu=self.helpmenu)
        self.helpmenu.add_command(label="Features info", command=self.open_features_info)
        self.helpmenu.add_command(label="Report an issue", command=self.open_issue)
        self.helpmenu.add_command(label="Made by mots", command=self.open_mots)

        self.toolkit_UI_obj.root.config(menu=self.main_menubar)

        # this is probably initialized in the main window,
        # but do a first update nevertheless
        self.update_current_window_references()

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

    def close_current_window(self):

        if self.current_window_id is None:
            logger.debug('Unable to determine current window id.')
            return

        # close the window
        self.toolkit_UI_obj.windows[self.current_window_id].close_action()

    def transcribe_audio_files(self):

        self.toolkit_ops_obj.prepare_transcription_file(
            toolkit_UI_obj=self.toolkit_UI_obj, task='transcribe', select_files=True)

    def translate_audio_files(self):

        self.toolkit_ops_obj.prepare_transcription_file(
            toolkit_UI_obj=self.toolkit_UI_obj, task='translate', select_files=True)

    def donothing(self):
        return

    def open_last_dir(self):

        if self.stAI.initial_target_dir is None or not os.path.exists(self.stAI.initial_target_dir):
            # notify the user
            messagebox.showinfo("No last folder to open", "No last folder to open.")

            logger.debug('No last folder to open.')
            return

        # if we're on a Mac, open the user data dir in Finder
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', self.stAI.initial_target_dir])

        # if we're on Windows, open the user data dir in Explorer
        elif platform.system() == 'Windows':
            subprocess.call(['explorer', self.stAI.initial_target_dir])

        # if we're on Linux, open the user data dir in the file manager
        elif platform.system() == 'Linux':
            subprocess.call(['xdg-open', self.stAI.initial_target_dir])

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