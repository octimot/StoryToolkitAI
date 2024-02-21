import tkinter as tk
from tkinter import *
from tkinter import messagebox

import platform
import subprocess
import webbrowser

from storytoolkitai import USER_DATA_PATH
from storytoolkitai.core.logger import *
from storytoolkitai.core.toolkit_ops.toolkit_ops import NLE

from customtkinter import AppearanceModeTracker
from customtkinter import ThemeManager

from tkinter import font
import ctypes


class UImenus:

    def __init__(self, toolkit_UI_obj, parent=None):

        # declare the main objects
        self.toolkit_UI_obj = toolkit_UI_obj
        self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj
        self.stAI = toolkit_UI_obj.stAI

        self.app_items_obj = toolkit_UI_obj.app_items_obj

        # this is the main window
        self.root = self.toolkit_UI_obj.root

        if parent is None:
            parent = self.root

        self.parent = parent

        # this is the main menubar (it's been declared in the main UI class to clear it before init)
        self.menubar = Menu(parent)

        # reset it for now so we don't see weird menus before it is populated
        parent.config(menu=self.menubar)

        # keep track of the current window id
        self.current_window_id = None
        self.current_window_type = None
        self.current_window = None

        # create a variable to store the keep_on_top state of the current window
        self.keep_on_top_state = BooleanVar()

        # set the initial state to False
        self.keep_on_top_state.set(False)

        # keep track if the main window is kept on top
        self.keep_main_window_on_top_state = BooleanVar()

        # set the initial state to whatever the config says
        self.keep_main_window_on_top_state.set(self.root.attributes('-topmost'))

        self.file_browser_name = self.toolkit_UI_obj.file_browser_name

        # the font sizes for the menu bar
        if platform.system() == 'Windows':
            self._menu_font = self._set_scalable_menu_font(parent)
            self._menu_ui = {'font': self._menu_font}
        else:
            self._menu_ui = {}

        self._loaded = False

    def _set_scalable_menu_font(self, parent):
        """
        This function sets the font for the menu bar.
        """

        menu_font = font.nametofont("TkMenuFont")
        base_font_size = menu_font.actual()["size"]

        # Retrieve the DPI scale factor
        user32 = ctypes.windll.user32
        self._scale_factor = user32.GetDpiForWindow(self.root.winfo_id()) / 96

        # Set the base font size and apply the scaling factor
        if parent == self.root:
            scaled_font_size = int(base_font_size * self._scale_factor)
        else:
            scaled_font_size = base_font_size

        # Create and configure the font
        menu_font = font.nametofont("TkMenuFont")
        menu_font.configure(size=scaled_font_size)

        return menu_font

    def update_current_window_references(self):

        # do not execute this if the menu is not loaded
        if not self._loaded:
            return

        # set the window id
        self.current_window_id = \
            self.toolkit_UI_obj.current_focused_window if self.parent == self.root else self.parent.window_id

        self.current_window = self.toolkit_UI_obj.get_window_by_id(self.current_window_id)

        # set the window type
        self.current_window_type = self.toolkit_UI_obj.get_window_type(self.current_window_id)

        # stop here if we don't have a window id
        if self.current_window_id is None:
            logger.debug('No window id found. Not updating the menu bar.')
            return

    def pass_key_event(self, window_id, key_event):
        '''
        This function passes a key event to the current window.
        '''

        if window_id is None or key_event is None or window_id not in self.toolkit_UI_obj.windows:
            return

        self.toolkit_UI_obj.windows[window_id].event_generate(key_event)

    def load_menubar(self):
        """
        This loads all the items in the menu bar.

        After the menu bar is loaded, we're going to use postcommand to enable or disable menu items
        depending on the window that is focused / selection etc.

        """

        # FILE MENU
        self._load_file_menu()

        # EDIT MENU
        self._load_edit_menu()

        # ADVANCED SEARCH MENU
        self._load_search_menu()

        # ASSISTANT MENU
        self._load_assistant_menu()

        # INTEGRATIONS MENU
        self._load_integrations_menu()

        # ADD WINDOW MENU
        self._load_window_menu()

        # HELP MENU
        self._load_help_menu()

        # add the menu bar to the root window
        self.parent.config(menu=self.menubar)

        # set the loaded flag to True
        self._loaded = True

    def _load_file_menu(self):
        """
        Loads the file menu
        """

        self.filemenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

        # add story file menu items
        self.filemenu.add_command(label="New project...",
                                  command=self.toolkit_UI_obj.create_new_project)
        self.filemenu.add_command(label="Import project...",
                                  command=self.toolkit_UI_obj.import_project)
        self.filemenu.add_command(label="Export current project...",
                                  command=self.toolkit_UI_obj.export_project)
        self.filemenu.add_command(label="Close current project",
                                  command=self.toolkit_UI_obj.close_project)

        self.filemenu.add_separator()

        # add story file menu items
        self.filemenu.add_command(label="New story...",
                                  command=self.toolkit_UI_obj.open_new_story_editor_window)
        self.filemenu.add_command(label="Open story file...",
                                  command=self.toolkit_UI_obj.open_story_editor_window)

        self.filemenu.add_separator()

        # add open transcription file menu item
        self.filemenu.add_command(label="Open transcription file...", command=self.toolkit_UI_obj.open_transcript)
        self.filemenu.add_separator()

        self.filemenu.add_command(label="Ingest files...", command=self.ingest_files)
        self.filemenu.add_command(label="Ingest directory...", command=self.ingest_directory)
        self.filemenu.add_separator()

        self.filemenu.add_command(label="Transcribe audio files...", command=self.transcribe_audio_files)
        self.filemenu.add_command(label="Translate audio files...", command=self.translate_audio_files)

        # FILE MENU - export items
        self.filemenu.add_separator()

        self.filemenu.add_command(label='Export story as text or Fountain...', state=DISABLED)
        self.filemenu.add_command(label='Export story as EDL or FCP7XML...', state=DISABLED)
        # self.filemenu.add_command(label='Export story as PDF...', state=DISABLED)

        self.filemenu.add_separator()
        # add Export as... menu item, but keep it disabled until a relevant window is focused
        self.filemenu.add_command(label="Export transcript as SRT or text...", state=DISABLED,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+Shift+s")

        # add Export as AVID/Fusion etc. menu items, but keep them disabled until a relevant window is focused
        self.filemenu.add_command(label="Export transcript as AVID DS...", state=DISABLED)
        self.filemenu.add_command(label="Export transcript as Fusion Text...", state=DISABLED)

        # FILE MENU - project linking
        self.filemenu.add_separator()

        self.filemenu.add_command(
            label="Link file to project...",
            command=self.toolkit_UI_obj.button_link_file_to_project,
            state=DISABLED
        )

        # for linking / unlinking items to projects,
        # we need to refer by the numeric index of the menu items so we can change the label
        self.filemenu.add_command(label="Link transcription to project", command=self.donothing, state=DISABLED)
        link_transcription_project_index = self.filemenu.index('end')

        self.filemenu.add_command(label="Link story to project", command=self.donothing, state=DISABLED)
        link_story_project_index = self.filemenu.index('end')

        # self.filemenu.add_command(label="Link file to project", command=self.donothing, state=DISABLED)
        # link_file_project_index = self.filemenu.index('end')

        # FILE MENU - other app related items
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Show file in " + self.file_browser_name, command=self.donothing)
        self.filemenu.add_command(label="Open configuration folder", command=self.open_userdata_dir)
        self.filemenu.add_command(label="Open last used folder", command=self.open_last_dir)

        self.menubar.add_cascade(label="File", menu=self.filemenu)

        def toggle_file_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            # disable the "Show file in ..." for now
            self.filemenu.entryconfig("Show file in " + self.file_browser_name, state=DISABLED)

            if self.toolkit_UI_obj.current_project is None:
                self.filemenu.entryconfig('Export current project...', state=DISABLED)
                self.filemenu.entryconfig('Close current project', state=DISABLED)
                self.filemenu.entryconfig('Link file to project...', state=DISABLED)
            else:
                self.filemenu.entryconfig('Export current project...', state=NORMAL)
                self.filemenu.entryconfig('Close current project', state=NORMAL)
                self.filemenu.entryconfig('Link file to project...', state=NORMAL)

            if self.current_window_type == 'transcription':

                # enable the Export as SRT menu item
                self.filemenu.entryconfig('Export transcript as SRT or text...', state=NORMAL,
                                          command=lambda: self.toolkit_UI_obj.t_edit_obj.button_export_as(
                                              self.current_window_id)
                                          )

                self.filemenu.entryconfig('Export transcript as AVID DS...', state=NORMAL,
                                          command=lambda: self.toolkit_UI_obj.t_edit_obj.button_export_as_avid_ds(
                                              self.current_window_id)
                                          )

                self.filemenu.entryconfig('Export transcript as Fusion Text...', state=NORMAL,
                                          command=lambda:
                                          self.toolkit_UI_obj.t_edit_obj.button_export_as_fusion_text_comp(
                                              self.current_window_id)
                                          )

                transcription_file_path = \
                    self.toolkit_UI_obj.t_edit_obj.get_window_transcription(self.current_window_id) \
                        .transcription_file_path

                # if we're in a project and the transcription is not linked to the project
                if self.toolkit_UI_obj.current_project:

                    transcription_linked_to_project = \
                        self.toolkit_UI_obj.current_project.is_linked_to_project(
                            object_type='transcription',
                            file_path=transcription_file_path
                        )

                    self.filemenu.entryconfig(
                        link_transcription_project_index,
                        label="Link transcription to project"
                        if not transcription_linked_to_project
                        else "Unlink transcription from project",
                        state=NORMAL,
                        command=lambda:
                        self.toolkit_UI_obj.button_set_file_link_to_project(
                            object_type='transcription',
                            file_path=transcription_file_path,
                            link=not transcription_linked_to_project
                        )
                    )

                self.filemenu.entryconfig(
                    "Show file in " + self.file_browser_name, state=NORMAL,
                    command=lambda: self.open_file_dir(transcription_file_path)
                )

            # if this is not a transcription window, disable the non-relevant menu items
            else:
                self.filemenu.entryconfig('Export transcript as SRT or text...', state=DISABLED)
                self.filemenu.entryconfig('Export transcript as AVID DS...', state=DISABLED)
                self.filemenu.entryconfig('Export transcript as Fusion Text...', state=DISABLED)
                self.filemenu.entryconfig(link_transcription_project_index,
                                          label="Link transcription to project", state=DISABLED)

            if self.current_window_type == 'story_editor':

                # enable the Export as TXT menu item
                self.filemenu.entryconfig('Export story as text or Fountain...', state=NORMAL,
                                          command=lambda: self.toolkit_UI_obj.StoryEdit.button_export_as_text(
                                              window_id=self.current_window_id, toolkit_UI_obj=self.toolkit_UI_obj)
                                          )

                # enable the Export as EDL or FCP7XML menu item
                self.filemenu.entryconfig('Export story as EDL or FCP7XML...', state=NORMAL,
                                          command=lambda: self.toolkit_UI_obj.StoryEdit.button_export_as_timeline(
                                              window_id=self.current_window_id, toolkit_UI_obj=self.toolkit_UI_obj)
                                          )

                if self.toolkit_UI_obj.current_project:

                    story_linked_to_project = \
                        self.toolkit_UI_obj.current_project.is_linked_to_project(
                            object_type='story',
                            file_path=self.current_window.story.story_file_path
                        )

                    self.filemenu.entryconfig(
                        link_story_project_index,
                        label="Link story to project" if not story_linked_to_project else "Unlink story from project",
                        state=NORMAL,
                        command=lambda:
                        self.toolkit_UI_obj.button_set_file_link_to_project(
                            object_type='story',
                            file_path=self.current_window.story.story_file_path,
                            link=not story_linked_to_project
                        )
                    )

                self.filemenu.entryconfig(
                    "Show file in " + self.file_browser_name, state=NORMAL,
                    command=lambda: self.open_file_dir(self.current_window.story.story_file_path)
                )

            else:
                self.filemenu.entryconfig('Export story as text or Fountain...', state=DISABLED)
                self.filemenu.entryconfig('Export story as EDL or FCP7XML...', state=DISABLED)
                self.filemenu.entryconfig(link_story_project_index,
                                          label='Link story to project', state=DISABLED)

        # add a postcommand to the file menu to enable/disable menu items depending on the current window
        self.filemenu.configure(postcommand=toggle_file_menu_items)

    def _load_edit_menu(self):
        """
        Loads the edit menu
        """

        self.editmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

        self.editmenu.add_command(label="Find...", command=self.donothing,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+f")

        self.editmenu.add_command(label="Select All", command=self.donothing,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+a")

        self.editmenu.add_command(label="Copy", command=self.donothing,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+c")

        self.editmenu.entryconfig('Find...', state=DISABLED)

        # EDIT - TRANSCRIPT related menu items
        # but disable all edit - transcript menu items
        # and let them be enabled when a transcript window is focused
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Copy to Clipboard with TC", command=self.donothing, state=DISABLED,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+Shift+c")
        self.editmenu.add_command(label="Copy to Clipboard with Block TC", command=self.donothing, state=DISABLED,
                                  accelerator="Shift+c")
        self.editmenu.add_command(label="Add to Group", command=self.donothing, state=DISABLED,
                                  accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+g")
        self.editmenu.add_command(label="Re-transcribe...", command=self.donothing, state=DISABLED,
                                  accelerator='t')
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Go to timecode...", command=self.donothing, state=DISABLED,
                                  accelerator='=')
        # self.editmenu.add_command(label="Delete segment", command=self.donothing, state=DISABLED,
        #                          accelerator="BackSpace")
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Detect speakers...", command=self.donothing, state=DISABLED)
        self.editmenu.add_command(label="Group questions...", command=self.donothing, state=DISABLED)
        self.editmenu.add_separator()
        self.editmenu.add_command(label="Transcription settings...", command=self.donothing, state=DISABLED)

        # show the edit menu
        self.menubar.add_cascade(label="Edit", menu=self.editmenu)

        def toggle_edit_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            # get the window
            window = self.toolkit_UI_obj.get_window_by_id(self.current_window_id)

            # enable find menu item if the window has a find function
            if window is not None \
                    and hasattr(window, 'find') \
                    and window.find is not None:

                self.editmenu.entryconfig(
                    'Find...', state=NORMAL, command=window.find)

            # disable the find menu item if the window has no find function
            else:
                self.editmenu.entryconfig('Find...', command=self.donothing, state=DISABLED)

            # toggle stuff depending on the current window type
            if self.current_window_type == 'transcription':

                if hasattr(window, 'text_widget'):
                    self._copy_menu_item_if_selection_exists(text_widget=window.text_widget)

                self.editmenu.entryconfig("Go to timecode...", state=NORMAL,
                                          command=lambda:
                                          self.toolkit_UI_obj.t_edit_obj.button_go_to_timecode(
                                              window_id=self.current_window_id)
                                          )
                self.editmenu.entryconfig('Detect speakers...', state=NORMAL,
                                          command=lambda:
                                          self.toolkit_UI_obj.t_edit_obj.button_detect_speakers(self.current_window_id,
                                                                                                ignore_selection=True)
                                          )

                # enable the group questions menu item
                self.editmenu.entryconfig('Group questions...', state=NORMAL,
                                          command=lambda:
                                          self.toolkit_UI_obj.t_edit_obj.button_group_questions(self.current_window_id)
                                          )

                self.editmenu.entryconfig(
                    'Transcription settings...', state=NORMAL,
                    command=lambda: self.toolkit_UI_obj.open_transcription_settings(
                        parent_window_id=self.current_window_id
                    )
                )

                self.editmenu.entryconfig('Select All',
                                          state=NORMAL,
                                          command=lambda:
                                          self.toolkit_UI_obj.t_edit_obj.button_select_deselect_all(
                                              self.current_window_id)
                                          )

                # if this transcription has selected segments enable the relevant menu items
                if self.toolkit_UI_obj.t_edit_obj.has_selected_segments(self.current_window_id):

                    self.editmenu.entryconfig("Copy to Clipboard with TC", state=NORMAL,
                                              command=lambda:
                                              self.toolkit_UI_obj.t_edit_obj.button_copy_segments_to_clipboard(
                                                  self.current_window_id,
                                                  with_timecodes=True,
                                                  per_line=True)
                                              )
                    self.editmenu.entryconfig("Copy to Clipboard with Block TC", state=NORMAL,
                                              command=lambda:
                                              self.toolkit_UI_obj.t_edit_obj.button_copy_segments_to_clipboard(
                                                  self.current_window_id,
                                                  with_timecodes=True)
                                              )

                    self.editmenu.entryconfig("Add to Group", state=NORMAL,
                                              command=lambda:
                                              self.toolkit_UI_obj.t_edit_obj.button_add_to_new_group(
                                                  window_id=self.current_window_id, only_add=True)
                                              )

                    self.editmenu.entryconfig("Re-transcribe...", state=NORMAL,
                                              command=lambda:
                                              self.toolkit_UI_obj.t_edit_obj.button_retranscribe(
                                                  window_id=self.current_window_id)
                                              )

                # if no segments are selected in this transcription just disable the irrelevant items
                else:
                    self.editmenu.entryconfig("Copy to Clipboard with TC", state=DISABLED)
                    self.editmenu.entryconfig("Copy to Clipboard with Block TC", state=DISABLED)
                    self.editmenu.entryconfig("Add to Group", state=DISABLED)
                    self.editmenu.entryconfig("Re-transcribe...", state=DISABLED)

            # toggle stuff for non-transcription windows
            else:

                # if the window has a text widget
                if hasattr(window, 'text_widget'):
                    self.editmenu.entryconfig(
                        'Select All',
                        state=NORMAL,
                        command=lambda: self.pass_key_event(
                            self.current_window_id, '<' + self.toolkit_UI_obj.ctrl_cmd_bind + '-a>')
                    )
                    self._copy_menu_item_if_selection_exists(text_widget=window.text_widget)

                else:
                    self.editmenu.entryconfig('Select All', state=DISABLED)
                    self.editmenu.entryconfig('Copy', state=DISABLED)

                # disable transcription related menu items
                self.editmenu.entryconfig("Go to timecode...", state=DISABLED)
                self.editmenu.entryconfig("Detect speakers...", state=DISABLED)
                self.editmenu.entryconfig("Group questions...", state=DISABLED)
                self.editmenu.entryconfig("Transcription settings...", state=DISABLED)
                self.editmenu.entryconfig('Copy to Clipboard with TC', state=DISABLED)
                self.editmenu.entryconfig('Copy to Clipboard with Block TC', state=DISABLED)
                self.editmenu.entryconfig('Add to Group', state=DISABLED)
                self.editmenu.entryconfig('Re-transcribe...', state=DISABLED)

        # add a postcommand to the edit menu to enable/disable menu items depending on the current window
        self.editmenu.configure(postcommand=toggle_edit_menu_items)

    def _load_search_menu(self):
        """
        Create the search menu
        """

        self.searchmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

        self.searchmenu.add_command(label="Advanced Search in current project...", command=self.donothing, state=DISABLED)
        self.searchmenu.add_command(label="Advanced Search in files...",
                                    command=lambda: self.toolkit_UI_obj.open_advanced_search_window())
        self.searchmenu.add_command(label="Advanced Search in folders...",
                                    command=lambda: self.toolkit_UI_obj.open_advanced_search_window(select_dir=True))
        # searchmenu.add_command(label="Search entire project...",
        #                       command=self.toolkit_UI_obj.open_advanced_search_window)

        self.searchmenu.add_separator()
        self.searchmenu.add_command(label="Change search model...", command=self.donothing, state=DISABLED)
        self.searchmenu.add_command(label="List files used for search...", command=self.donothing, state=DISABLED)

        # ADVANCED SEARCH - TRANSCRIPT related menu items
        # but disabled for now
        # let them be enabled when a transcript window is focused)
        self.searchmenu.add_separator()
        # self.searchmenu.add_command(label="Advanced Search in current project...", command=self.donothing,
        #                            state=DISABLED)
        # self.searchmenu.add_command(label="Advanced Search in current transcription...", command=self.donothing,
        #                            state=DISABLED)
        self.searchmenu.add_command(label="Advanced Search in current transcription...", command=self.donothing,
                                    state=DISABLED)

        self.menubar.add_cascade(label="Search", menu=self.searchmenu)

        def toggle_search_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            if self.toolkit_UI_obj.current_project:
                self.searchmenu.entryconfig(
                    "Advanced Search in current project...",
                    command=lambda:
                    self.toolkit_UI_obj.open_advanced_search_window(project=self.toolkit_UI_obj.current_project),
                    state=NORMAL
                )
            else:
                self.searchmenu.entryconfig(
                    "Advanced Search in current project...",
                    state=DISABLED
                )

            if self.current_window_type == 'transcription':
                self.searchmenu.entryconfig("Advanced Search in current transcription...", state=NORMAL,
                                            command=lambda:
                                            self.toolkit_UI_obj.open_advanced_search_window(
                                                transcription_window_id=self.current_window_id)
                                            )
            else:
                self.searchmenu.entryconfig("Advanced Search in current transcription...", state=DISABLED)

            if self.current_window_type == 'search':
                self.searchmenu.entryconfig("Change search model...", state=NORMAL,
                                            command= lambda: self.toolkit_UI_obj.button_search_change_model(
                                                self.current_window_id))
                self.searchmenu.entryconfig("List files used for search...",  state=NORMAL,
                                            command= lambda: self.toolkit_UI_obj.button_search_list_files(
                                                self.current_window_id))
            else:
                self.searchmenu.entryconfig("Change search model...", command=self.donothing, state=DISABLED)
                self.searchmenu.entryconfig("List files used for search...", command=self.donothing, state=DISABLED)

        # add a postcommand to the search menu to enable/disable menu items depending on the current window
        self.searchmenu.configure(postcommand=toggle_search_menu_items)

    def _load_assistant_menu(self):
        """
        Create the assistant menu
        """

        self.assistantmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)
        self.assistantmenu.add_command(label="Open Assistant...", command=self.toolkit_UI_obj.open_assistant_window)

        # ASSISTANT - TRANSCRIPT related menu items
        self.assistantmenu.add_separator()
        self.assistantmenu.add_command(label="Send to Assistant", command=self.donothing, state=DISABLED,
                                       accelerator='o')
        self.assistantmenu.add_command(label="Send to Assistant with TC", command=self.donothing, state=DISABLED,
                                       accelerator="Shift+o")

        # ASSISTANT WINDOW stuff
        self.assistantmenu.add_separator()
        self.assistantmenu.add_command(label="Current Assistant Settings...", command=self.donothing, state=DISABLED)

        self.menubar.add_cascade(label="Assistant", menu=self.assistantmenu)

        def toggle_assistant_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            # if this is a transcription window enable the relevant menu items
            if self.current_window_type == 'transcription':

                self.assistantmenu.entryconfig("Send to Assistant", state=NORMAL,
                                               command=lambda:
                                               self.toolkit_UI_obj.t_edit_obj.button_send_to_assistant(
                                                   window_id=self.current_window_id,
                                                   with_timecodes=False)
                                               )
                self.assistantmenu.entryconfig("Send to Assistant with TC", state=NORMAL,
                                               command=lambda:
                                               self.toolkit_UI_obj.t_edit_obj.button_send_to_assistant(
                                                   window_id=self.current_window_id,
                                                   with_timecodes=True)
                                               )
            else:
                self.assistantmenu.entryconfig("Send to Assistant", state=DISABLED)
                self.assistantmenu.entryconfig("Send to Assistant with TC", state=DISABLED)

            if self.current_window_type == 'assistant':
                self.assistantmenu.entryconfig("Current Assistant Settings...", state=NORMAL,
                                               command=lambda:
                                               self.toolkit_UI_obj.open_assistant_window_settings(
                                                   assistant_window_id=self.current_window_id)
                                               )
            else:
                self.assistantmenu.entryconfig("Current Assistant Settings...", state=DISABLED)

        # add a postcommand to the assistant menu to enable/disable menu items depending on the current window
        self.assistantmenu.configure(postcommand=toggle_assistant_menu_items)

    def _load_integrations_menu(self):
        """
        Create the integrations menu
        """

        self.integrationsmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

        # add a title in the menu
        self.integrationsmenu.add_command(
            label="Connect to Resolve API", command=self.toolkit_UI_obj.on_connect_resolve_api_press)
        self.integrationsmenu.add_command(
            label="Disable Resolve API", command=self.toolkit_UI_obj.on_disable_resolve_api_press)

        # INTEGRATIONS - GENERAL RESOLVE menu items
        self.integrationsmenu.add_separator()
        self.integrationsmenu.add_command(
            label="Render and Transcribe Timeline", command=self.donothing, state=DISABLED)
        self.integrationsmenu.add_command(
            label="Render and Translate Timeline", command=self.donothing, state=DISABLED)
        self.integrationsmenu.add_command(
            label="Copy Timeline Markers to Timeline Bin Clip", command=self.donothing, state=DISABLED)
        self.integrationsmenu.add_command(
            label="Copy Timeline Bin Clip Markers to Timeline", command=self.donothing, state=DISABLED)
        self.integrationsmenu.add_command(
            label="Render Markers to Clips", command=self.donothing, state=DISABLED)
        self.integrationsmenu.add_command(
            label="Render Markers to Stills", command=self.donothing, state=DISABLED)

        # INTEGRATIONS - TRANSCRIPT related menu items
        self.integrationsmenu.add_separator()
        self.integrationsmenu.add_command(
            label="Quick Selection to Markers", command=self.donothing, state=DISABLED, accelerator="m")
        self.integrationsmenu.add_command(
            label="Selection to Markers", command=self.donothing, state=DISABLED, accelerator="Shift+m")
        self.integrationsmenu.add_command(
            label="Markers to Segments", command=self.donothing, state=DISABLED,
            accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+m")
        self.integrationsmenu.add_command(
            label="Move Playhead to Selection Start", command=self.donothing, state=DISABLED, accelerator=';')
        self.integrationsmenu.add_command(
            label="Move Playhead to Selection End", command=self.donothing, state=DISABLED, accelerator="'")
        self.integrationsmenu.add_command(
            label="Align Segment Start to Playhead", command=self.donothing, state=DISABLED, accelerator=':')
        self.integrationsmenu.add_command(
            label="Align Segment End to Playhead", command=self.donothing, state=DISABLED, accelerator='"')

        self.menubar.add_cascade(label="Integrations", menu=self.integrationsmenu)

        def toggle_integrations_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            if not NLE.is_connected():
                self.integrationsmenu.entryconfig("Connect to Resolve API", state=NORMAL)
                self.integrationsmenu.entryconfig("Disable Resolve API", state=DISABLED)

            else:
                self.integrationsmenu.entryconfig("Connect to Resolve API", state=DISABLED)
                self.integrationsmenu.entryconfig("Disable Resolve API", state=NORMAL)

            # toggle the menu items for general resolve related functions
            if NLE.is_connected() and NLE.current_timeline is not None:
                self.integrationsmenu.entryconfig("Render and Transcribe Timeline",
                                                  command=self.toolkit_UI_obj.button_nle_transcribe_timeline,
                                                  state=NORMAL)
                self.integrationsmenu.entryconfig("Render and Translate Timeline",
                                                  command=lambda:
                                                  self.toolkit_UI_obj.button_nle_transcribe_timeline(
                                                      transcription_task='translate'),
                                                  state=NORMAL)
                self.integrationsmenu.entryconfig(
                    "Copy Timeline Markers to Timeline Bin Clip",
                    command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                        'copy_markers_timeline_to_clip', self.toolkit_UI_obj),
                    state=NORMAL)
                self.integrationsmenu.entryconfig(
                    "Copy Timeline Bin Clip Markers to Timeline",
                    command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                        'copy_markers_clip_to_timeline', self.toolkit_UI_obj),
                    state=NORMAL)
                self.integrationsmenu.entryconfig(
                    "Render Markers to Stills",
                    command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                        'render_markers_to_stills', self.toolkit_UI_obj),
                    state=NORMAL)
                self.integrationsmenu.entryconfig(
                    "Render Markers to Clips",
                    command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                        'render_markers_to_clips', self.toolkit_UI_obj),
                    state=NORMAL)

            else:
                self.integrationsmenu.entryconfig("Render and Transcribe Timeline", command=self.donothing,
                                                  state=DISABLED)
                self.integrationsmenu.entryconfig("Render and Translate Timeline", command=self.donothing,
                                                  state=DISABLED)
                self.integrationsmenu.entryconfig("Copy Timeline Markers to Timeline Bin Clip",
                                                  command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig("Copy Timeline Bin Clip Markers to Timeline",
                                                  command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig("Render Markers to Clips",
                                                  command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig("Render Markers to Stills",
                                                  command=self.donothing, state=DISABLED)

            # if this is a transcription window enable the relevant menu items
            if self.current_window_type == 'transcription' \
                    and NLE.is_connected() and NLE.current_timeline is not None:
                self.integrationsmenu.entryconfig("Markers to Segments", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.button_markers_to_segments(
                                                      window_id=self.current_window_id)
                                                  )

                self.integrationsmenu.entryconfig("Move Playhead to Selection Start", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.go_to_selected_time(
                                                      window_id=self.current_window_id,
                                                      position='start')
                                                  )
                self.integrationsmenu.entryconfig("Move Playhead to Selection End", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.go_to_selected_time(
                                                      window_id=self.current_window_id,
                                                      position='end')
                                                  )

                self.integrationsmenu.entryconfig("Align Segment Start to Playhead", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.align_line_to_playhead(
                                                      window_id=self.current_window_id,
                                                      position='start')
                                                  )
                self.integrationsmenu.entryconfig("Align Segment End to Playhead", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.align_line_to_playhead(
                                                      window_id=self.current_window_id,
                                                      position='end')
                                                  )

            else:
                self.integrationsmenu.entryconfig(
                    "Move Playhead to Selection Start", command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig(
                    "Move Playhead to Selection End", command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig(
                    "Align Segment Start to Playhead", state=DISABLED)
                self.integrationsmenu.entryconfig(
                    "Align Segment End to Playhead", state=DISABLED)
                self.integrationsmenu.entryconfig(
                    "Markers to Segments", state=DISABLED)

            # if this is a transcription window
            # and there are selected segments enable the relevant menu items
            if self.current_window_type == 'transcription' \
                    and self.toolkit_UI_obj.t_edit_obj.has_selected_segments(window_id=self.current_window_id) \
                    and NLE.is_connected() and NLE.current_timeline is not None:

                self.integrationsmenu.entryconfig("Quick Selection to Markers", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.button_segments_to_markers(
                                                      window_id=self.current_window_id, prompt=False)
                                                  )
                self.integrationsmenu.entryconfig("Selection to Markers", state=NORMAL,
                                                  command=lambda:
                                                  self.toolkit_UI_obj.t_edit_obj.button_segments_to_markers(
                                                      window_id=self.current_window_id, prompt=True)
                                                  )

            else:
                self.integrationsmenu.entryconfig(
                    "Quick Selection to Markers", command=self.donothing, state=DISABLED)
                self.integrationsmenu.entryconfig(
                    "Selection to Markers", command=self.donothing, state=DISABLED)

        # add a postcommand to the integrations menu to enable/disable menu items depending on the current window
        self.integrationsmenu.configure(postcommand=toggle_integrations_menu_items)

    def _load_window_menu(self):

        self.windowsmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

        # add a keep main on top menu item
        self.windowsmenu.add_checkbutton(label="Keep main window on top",
                                    variable=self.keep_main_window_on_top_state,
                                    command=self.keep_main_window_on_top)

        # add a keep on top menu item
        self.windowsmenu.add_checkbutton(
            label="Keep window on top",
            variable=self.keep_on_top_state,
            command=self.keep_current_window_on_top)

        # add a close window menu item
        self.windowsmenu.add_command(
            label="Close window",
            command=self.close_current_window,
            accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+Shift+W")

        # add open groups menu item
        # self.windowsmenu.add_separator()
        # self.windowsmenu.add_command(label="Open Transcript Groups", command=self.donothing,
        #                              state="disabled", accelerator="Shift+G")

        # add cascade
        self.menubar.add_cascade(label="Window", menu=self.windowsmenu)

        def toggle_window_menu_items():

            # make sure we know which window is focused etc.
            self.update_current_window_references()

            if self.current_window_type == 'main':
                # disable show the keep on top menu item
                self.windowsmenu.entryconfig('Keep window on top', state=DISABLED)

                # disable the close window menu item
                self.windowsmenu.entryconfig('Close window', state=DISABLED)

            else:
                # enable show the keep on top menu item
                self.windowsmenu.entryconfig('Keep window on top', state=NORMAL)

                # get the window object
                window = self.toolkit_UI_obj.get_window_by_id(self.current_window_id)

                # enable the close window menu item (if a close_action exists)
                # (if the window has a close_action, it means that it can be closed)
                if hasattr(window, 'close_action') \
                        and window.close_action is not None:
                    self.windowsmenu.entryconfig('Close window', state=NORMAL)

                # if the window doesn't have a close_action, disable the menu item
                else:
                    self.windowsmenu.entryconfig('Close window', state=DISABLED)

            # also update the state of the keep on top menu item
            # which will reflect the keep on top state of the current window
            self.keep_on_top_state.set(
                self.toolkit_UI_obj.get_window_on_top_state(self.current_window_id)
                if self.toolkit_UI_obj.get_window_on_top_state(self.current_window_id) is not None
                else False)

        # add a postcommand to the window menu to enable/disable menu items depending on the current window
        self.windowsmenu.configure(postcommand=toggle_window_menu_items)

    def _load_help_menu(self):
        """
        Load the help menu
        """

        self.helpmenu = Menu(self.menubar, tearoff=0, **self._menu_ui)

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

            system_menu = tk.Menu(self.menubar, name='apple')
            # system_menu.add_command(command=lambda: self.w.call('tk::mac::standardAboutPanel'))
            # system_menu.add_command(command=lambda: self.updater.checkForUpdates())

            # system_menu.entryconfigure(0, label="About")
            system_menu.entryconfigure(1, label="Check for Updates...")
            # self.menubar.add_cascade(menu=system_menu)

            self.helpmenu.add_command(label="Go to project page", command=self.open_project_page)

        self.menubar.add_cascade(label="Help", menu=self.helpmenu)
        self.helpmenu.add_command(label="Features info", command=self.open_features_info)
        self.helpmenu.add_command(label="Report an issue", command=self.open_issue)
        self.helpmenu.add_command(label="Made by mots", command=self.open_mots)

    def _copy_menu_item_if_selection_exists(self, text_widget):

        # if there is a selection, enable the copy menu item
        if text_widget.tag_ranges("sel"):
            self.editmenu.entryconfig(
                'Copy',
                state=NORMAL,
                command=lambda: text_widget.event_generate("<<Copy>>"))

        else:
            self.editmenu.entryconfig("Copy", state=DISABLED)

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

    def ingest_files(self):
        self.toolkit_UI_obj.button_ingest()

    def ingest_directory(self):
        self.toolkit_UI_obj.button_ingest(select_dir=True)

    def transcribe_audio_files(self):
        self.toolkit_UI_obj.button_ingest(video_indexing_enabled=False)

    def translate_audio_files(self):
        self.toolkit_UI_obj.button_ingest(transcription_task='translate', video_indexing_enabled=False)

    @staticmethod
    def donothing():
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
            subprocess.call(['explorer', os.path.normpath(self.stAI.initial_target_dir)])

        # if we're on Linux, open the user data dir in the file manager
        elif platform.system() == 'Linux':
            subprocess.call(['xdg-open', self.stAI.initial_target_dir])

    def open_userdata_dir(self):
        # if we're on a Mac, open the user data dir in Finder
        if platform.system() == 'Darwin':
            subprocess.call(['open', '-R', USER_DATA_PATH])

        # if we're on Windows, open the user data dir in Explorer
        elif platform.system() == 'Windows':
            subprocess.call(['explorer', USER_DATA_PATH])

        # if we're on Linux, open the user data dir in the file manager
        elif platform.system() == 'Linux':
            subprocess.call(['xdg-open', USER_DATA_PATH])

    def open_file_dir(self, file_path):
        """
        This takes the user to the directory of the file in question using the OS file manager.
        """
        self.toolkit_UI_obj.open_file_dir(file_path)

    @staticmethod
    def open_project_page(*args, **kwargs):
        webbrowser.open_new("http://storytoolkit.ai")
        return

    @staticmethod
    def open_features_info(*args, **kwargs):
        webbrowser.open_new("https://github.com/octimot/StoryToolkitAI/blob/main/FEATURES.md")
        return

    @staticmethod
    def open_issue(*args, **kwargs):
        webbrowser.open_new("https://github.com/octimot/StoryToolkitAI/issues")
        return

    def about_dialog(self):
        self.app_items_obj.open_about_window()

    @staticmethod
    def open_mots(*args, **kwargs):
        webbrowser.open_new("https://mots.us")
        return
