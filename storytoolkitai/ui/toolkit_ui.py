import json

from storytoolkitai.core.toolkit_ops.toolkit_ops import *

import copy
import os.path
import platform
import subprocess
import webbrowser
import sys
import random

from requests import get
import time
import re
import hashlib

from typing import Union, List

from timecode import Timecode

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

from tkinter import filedialog, simpledialog, messagebox, font

from whisper import available_models as whisper_available_models

from .menu import UImenus


class toolkit_UI():
    """
    This handles all the GUI operations mainly using tkinter
    """

    # THEME

    # define StoryToolkit theme colors here
    # (the customtkinter theme colors are defined in the theme file)
    theme_colors = dict()
    theme_colors['black'] = '#1F1F1F'
    theme_colors['supernormal'] = '#C2C2C2',
    theme_colors['white'] = '#ffffff'
    theme_colors['highlight'] = theme_colors['white']
    theme_colors['normal'] = '#929292'
    theme_colors['superblack'] = '#000000'
    theme_colors['dark'] = '#282828'
    theme_colors['darker'] = '#242424'    # lighter than black, but darker than dark
    theme_colors['blue'] = '#1E90FF'
    theme_colors['red'] = '#800020'
    theme_colors['bright_red'] = '#FF160C'
    theme_colors['resolve_red'] = '#E64B3D'
    theme_colors['error'] = theme_colors['red']
    theme_colors['error_text'] = theme_colors['red']
    theme_colors['selected_blue_text'] = ctk.ThemeManager.theme["CTkSegmentedButton"]["text_color"][1]
    theme_colors['selected_blue_bg'] = ctk.ThemeManager.theme["CTkButton"]["hover_color"][1]

    theme_colors['meta_text'] = '#5D5D5D'

    # UI paddings and other settings
    ctk_full_window_frame_paddings = {'padx': 20, 'pady': 20}
    ctk_frame_paddings = {'padx': 5, 'pady': 5}
    ctk_form_paddings_ext = {'padx': 10, 'pady': 5}
    ctk_form_entry_paddings = {'padx': 10, 'pady': 10}
    ctk_frame_transparent = {'fg_color': 'transparent'}
    ctk_form_entry_settings = {'width': 120}
    ctk_form_slider_settings = {'width': 60}
    ctk_form_entry_settings_double = {'width': 240}
    ctk_form_entry_settings_half = {'width': ctk_form_entry_settings['width'] / 2}
    ctk_form_entry_settings_quarter = {'width': ctk_form_entry_settings['width'] / 4}
    ctk_form_textbox = {'width': 240, 'height': 100}
    ctk_form_paddings = {'padx': 10, 'pady': 5}
    ctk_form_label_settings = {'width': 170, 'anchor': 'w'}
    ctk_frame_label_settings = {
        **{'fg_color': ctk.ThemeManager.theme["CTkScrollableFrame"]["label_fg_color"], 'anchor': 'w'},
        **ctk_frame_paddings
    }

    ctk_button_size = {'width': 200, 'height': 45}

    ctk_list_item = {'fg_color': ctk.ThemeManager.theme["CTkScrollableFrame"]["label_fg_color"]}

    ctk_full_textbox_paddings = {'padx': 15, 'pady': 15}
    ctk_full_textbox_frame_paddings = {'padx': (10, 0), 'pady': 5}

    ctk_side_frame_button_paddings = {'padx': 10, 'pady': 10}
    ctk_side_frame_button_size = {'width': 200}
    ctk_side_label_settings = {'width': 100, 'anchor': 'w'}
    ctk_side_label_paddings = {'padx': 10, 'pady': (2, 6)}
    ctk_side_switch_settings = {'width': 50}
    ctk_fake_listbox_label_paddings = {'padx': 5, 'pady': 0}
    ctk_fake_listbox_paddings = {'padx': 5, 'pady': 0}

    ctk_popup_frame_paddings = {'padx': 5, 'pady': 5}
    ctk_popup_input_paddings = {'padx': 5}
    ctk_askdialog_input_size = {'width': 200}
    ctk_askdialog_input_int_size = {'width': 50}
    ctk_askdialog_frame_paddings = {'padx': 10, 'pady': 10}
    ctk_askdialog_input_paddings = {'padx': 10, 'pady': 10}
    ctk_list_paddings = {'padx': 3, 'pady': 3}

    ctk_footer_button_paddings = {'padx': 10, 'pady': 10}
    ctk_footer_status_paddings = {'padx': 10, 'pady': (5, 10)}
    ctk_secondary_button_paddings = ctk_footer_button_paddings

    ctk_selected_color = ctk.ThemeManager.theme["CTkSegmentedButton"]["selected_color"]
    ctk_unselected_color = 'transparent'

    ctk_main_paddings = {'padx': 10, 'pady': 10}

    # these are the marker colors used in Resolve
    resolve_marker_colors = MotsResolve.RESOLVE_MARKER_COLORS

    class AppItemsUI:
        """
        This contains the Preferences and About windows.
        """

        def __init__(self, toolkit_UI_obj):

            if toolkit_UI_obj is None:
                logger.error('No toolkit_UI_obj provided for AppItemsUI.')
                raise Exception('No toolkit_UI_obj provided.')

            # declare the UI, ops and app objects for easier access
            self.toolkit_UI_obj = toolkit_UI_obj
            self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj
            self.stAI = toolkit_UI_obj.stAI
            self.UI_menus = UImenus

            # the root window inherited from the toolkit_UI_obj
            self.root = toolkit_UI_obj.root

            return

        def open_preferences_window(self, **kwargs):
            """
            Opens the preferences window.
            :return:
            """

            # create a window for the preferences if one doesn't already exist
            if window_id := self.toolkit_UI_obj.create_or_open_window(parent_element=self.root,
                                                                      window_id='preferences',
                                                                      title='Preferences', resizable=(False, True),
                                                                      type='preferences'):
                # get the window
                pref_window = self.toolkit_UI_obj.windows[window_id]

                # UI - escape key closes the window
                # pref_window.bind('<Escape>', lambda event: close_ingest_window())

                # UI - create the top frame
                top_frame = ctk.CTkFrame(pref_window)

                # UI - create the middle frame (it's a tab view)
                middle_frame = ctk.CTkTabview(pref_window)

                # UI - create the bottom frame
                bottom_frame = ctk.CTkFrame(pref_window, **toolkit_UI.ctk_frame_transparent)

                # UI - middle and bottom frames
                middle_frame.grid(row=1, column=0, sticky="nsew", **toolkit_UI.ctk_frame_paddings)
                bottom_frame.grid(row=2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

                # UI - grid configure the middle frame so that it expands with the window
                pref_window.grid_rowconfigure(1, weight=1)

                # UI - the columns should expand with the window
                pref_window.grid_columnconfigure(0, weight=1, minsize=500)

                # TOP FRAME ELEMENTS
                # these will be added a few lines below

                # MIDDLE FRAME ELEMENTS

                # UI - add the audio and video tabs
                general_tab = middle_frame.add('General')
                integrations_tab = middle_frame.add('Integrations')
                ingest_tab = middle_frame.add('Ingest')
                search_tab = middle_frame.add('Search')
                assistant_tab = middle_frame.add('Assistant')

                # UI - add the scrollable frames for each tab
                general_tab_scrollable_frame = ctk.CTkScrollableFrame(general_tab,
                                                                      **toolkit_UI.ctk_frame_transparent)
                general_tab_scrollable_frame.pack(fill='both', expand=True)

                ingest_tab_scrollable_frame = ctk.CTkScrollableFrame(ingest_tab,
                                                                     **toolkit_UI.ctk_frame_transparent)
                ingest_tab_scrollable_frame.pack(fill='both', expand=True)

                integrations_tab_scrollable_frame = ctk.CTkScrollableFrame(integrations_tab,
                                                                           **toolkit_UI.ctk_frame_transparent)
                integrations_tab_scrollable_frame.pack(fill='both', expand=True)
                search_tab_scrollable_frame = ctk.CTkScrollableFrame(search_tab,
                                                                     **toolkit_UI.ctk_frame_transparent)
                search_tab_scrollable_frame.pack(fill='both', expand=True)
                assistant_tab_scrollable_frame = ctk.CTkScrollableFrame(assistant_tab,
                                                                        **toolkit_UI.ctk_frame_transparent)
                assistant_tab_scrollable_frame.pack(fill='both', expand=True)

                # UI - set the visibility on the General tab
                middle_frame.set('General')
                middle_frame.columnconfigure(0, weight=1)

                # UI - create another frame for the buttons
                buttons_frame = ctk.CTkFrame(bottom_frame, **toolkit_UI.ctk_frame_transparent)

                # UI - create the start button
                save_button = ctk.CTkButton(buttons_frame, text='Save')

                # UI - create the cancel button
                cancel_button = ctk.CTkButton(buttons_frame, text='Cancel')

                # UI - add the start button, the cancel button
                buttons_frame.grid(row=0, column=0, sticky="w", **toolkit_UI.ctk_frame_paddings)

                # UI - the buttons should be next to each other, so we'll use a pack layout
                save_button.pack(side='left', **toolkit_UI.ctk_footer_button_paddings)
                cancel_button.pack(side='left', **toolkit_UI.ctk_footer_button_paddings)

                # add the buttons to the kwargs so we can pass them to future functions
                kwargs['save_button'] = save_button
                kwargs['cancel_button'] = cancel_button

                # GENERAL PREFERENCES
                # add the general preferences form elements
                general_prefs_form_vars = self.add_general_prefs_form_elements(
                    general_tab_scrollable_frame)

                # INGEST PREFERENCES
                # add the audio ingest form elements (but without the time intervals)
                audio_form_vars = self.toolkit_UI_obj.add_ingest_audio_form_elements(
                    ingest_tab_scrollable_frame, show_time_intervals=False, show_custom_punctuation_marks=True)

                # add the video ingest form elements (but without the time intervals)
                video_form_vars = self.toolkit_UI_obj.add_ingest_video_form_elements(
                    ingest_tab_scrollable_frame)

                # add the analysis form elements
                analysis_form_vars = self.toolkit_UI_obj.add_analysis_form_elements(
                    ingest_tab_scrollable_frame)

                # add the other ingest form elements
                other_ingest_form_vars = self.add_other_ingest_prefs(
                    ingest_tab_scrollable_frame)

                # INTEGRATIONS PREFERENCES
                # add the integrations form elements
                integrations_form_vars = self.add_integrations_prefs(
                    integrations_tab_scrollable_frame)

                # SEARCH PREFERENCES
                search_form_vars = self.add_search_prefs(
                    search_tab_scrollable_frame)

                # ASSISTANT PREFERENCES
                assistant_form_vars = self.add_assistant_prefs(
                    assistant_tab_scrollable_frame)

                # create the giant dictionary that contains all the form variables
                form_vars = {**general_prefs_form_vars,
                             **audio_form_vars, **video_form_vars, **analysis_form_vars,
                             **other_ingest_form_vars, **integrations_form_vars, **search_form_vars,
                             **assistant_form_vars}

                # UI - start button command
                # at this point, the kwargs should also contain the ingest_window_id
                save_button.configure(
                    command=lambda:
                    self.save_preferences(input_variables=form_vars)
                )

                # UI - cancel button command
                cancel_button.configure(
                    command=lambda:
                    self.toolkit_UI_obj.destroy_window_(window_id=window_id)
                )

                # UI - configure the bottom columns and rows so that the elements expand with the window
                bottom_frame.columnconfigure(0, weight=1)
                bottom_frame.columnconfigure(1, weight=1)
                bottom_frame.rowconfigure(1, weight=1)
                bottom_frame.rowconfigure(2, weight=1)

                # UI - add a minimum height to the window
                pref_window.minsize(500, 700
                if pref_window.winfo_screenheight() > 700 else pref_window.winfo_screenheight())

                # UI- add a maximum height to the window (to prevent it from being bigger than the screen)
                pref_window.maxsize(600, pref_window.winfo_screenheight())

        def add_general_prefs_form_elements(self, parent: tk.Widget, **kwargs) -> dict or None:
            """
            This function adds the form elements for the general preferences tab
            """

            # create the frames
            general_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)
            api_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)

            # create labels for the frames (and style them according to the theme)
            general_prefs_label = ctk.CTkLabel(parent, text='General Preferences',
                                               **toolkit_UI.ctk_frame_label_settings)
            api_label = ctk.CTkLabel(parent, text='StoryToolkit API', **toolkit_UI.ctk_frame_label_settings)

            # we're going to create the form_vars dict to store all the variables
            # we will use this dict at the end of the function to gather all the created tk variables
            form_vars = {}

            # get the last grid row for the parent
            l_row = parent.grid_size()[1]

            # add the labels and frames to the parent
            general_prefs_label.grid(row=l_row + 1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            general_prefs_frame.grid(row=l_row + 2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            api_label.grid(row=l_row + 3, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            api_frame.grid(row=l_row + 4, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # make the column expandable
            parent.columnconfigure(0, weight=1)
            general_prefs_frame.columnconfigure(1, weight=1)
            api_frame.columnconfigure(1, weight=1)

            # CONSOLE FONT SIZE
            # get the console font size setting from the app settings
            console_font_size = \
                kwargs.get('console_font_size', None) \
                    if kwargs.get('console_font_size', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('console_font_size', default_if_none=13)

            # create the console font size variable, label and input
            form_vars['console_font_size_var'] = \
                console_font_size_var = tk.IntVar(general_prefs_frame, value=console_font_size)
            console_font_size_label = ctk.CTkLabel(general_prefs_frame, text='Console Font Size',
                                                   **toolkit_UI.ctk_form_label_settings)
            console_font_size_input = ctk.CTkEntry(general_prefs_frame,
                                                   textvariable=console_font_size_var,
                                                   **toolkit_UI.ctk_form_entry_settings_half)

            # TRANSCRIPT FONT SIZE
            # get the transcript font size setting from the app settings
            transcript_font_size = \
                kwargs.get('transcript_font_size', None) \
                    if kwargs.get('transcript_font_size', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('transcript_font_size', default_if_none=15)

            # create the variable, label and input
            form_vars['transcript_font_size_var'] = \
                transcript_font_size_var = tk.IntVar(general_prefs_frame, value=transcript_font_size)
            transcript_font_size_label = ctk.CTkLabel(general_prefs_frame, text='Transcript Font Size',
                                                      **toolkit_UI.ctk_form_label_settings)
            transcript_font_size_input = ctk.CTkEntry(general_prefs_frame,
                                                      textvariable=transcript_font_size_var,
                                                      **toolkit_UI.ctk_form_entry_settings_half)

            # SHOW WELCOME WINDOW
            # get the show welcome setting from the app settings
            show_welcome = \
                kwargs.get('show_welcome', None) \
                    if kwargs.get('show_welcome', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('show_welcome', default_if_none=True)

            # create the show welcome variable, label and input
            form_vars['show_welcome_var'] = \
                show_welcome_var = tk.BooleanVar(general_prefs_frame, value=show_welcome)
            show_welcome_label = ctk.CTkLabel(general_prefs_frame, text='Show Welcome Window',
                                              **toolkit_UI.ctk_form_label_settings)
            show_welcome_input = ctk.CTkSwitch(general_prefs_frame,
                                               variable=show_welcome_var,
                                               text='',
                                               **toolkit_UI.ctk_form_entry_settings)

            # TRANSCRIPTS ALWAYS ON TOP
            # get the transcripts_always_on_top setting from the app settings
            transcripts_always_on_top = \
                kwargs.get('transcripts_always_on_top', None) \
                    if kwargs.get('transcripts_always_on_top', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('transcripts_always_on_top', default_if_none=False)

            # create the transcripts_always_on_top variable, label and input
            form_vars['transcripts_always_on_top_var'] = \
                transcripts_always_on_top_var = tk.BooleanVar(general_prefs_frame, value=transcripts_always_on_top)
            transcripts_always_on_top_label = ctk.CTkLabel(general_prefs_frame, text='Transcripts Always on Top',
                                                           **toolkit_UI.ctk_form_label_settings)
            transcripts_always_on_top_input = ctk.CTkSwitch(general_prefs_frame,
                                                            variable=transcripts_always_on_top_var,
                                                            text='',
                                                            **toolkit_UI.ctk_form_entry_settings)

            # STORYTOOLKIT API KEY
            # get the api key from the app settings
            stai_api_key = \
                kwargs.get('stai_api_key', None) \
                    if kwargs.get('stai_api_key', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('stai_api_key', default_if_none=None)

            # create the api key variable, label and input
            form_vars['stai_api_key_var'] = \
                stai_api_key_var = tk.StringVar(api_frame, value=stai_api_key if stai_api_key else '')
            stai_api_key_label = ctk.CTkLabel(api_frame, text='StoryToolkit API Key',
                                           **toolkit_UI.ctk_form_label_settings)
            stai_api_key_input = ctk.CTkEntry(api_frame, show="*",
                                           textvariable=stai_api_key_var,
                                           **toolkit_UI.ctk_form_entry_settings_double)

            # Adding all the elemente to the grid

            # GENERAL PREFERENCES FRAME GRID
            console_font_size_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            console_font_size_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcript_font_size_label.grid(row=2, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcript_font_size_input.grid(row=2, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            show_welcome_label.grid(row=3, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            show_welcome_input.grid(row=3, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcripts_always_on_top_label.grid(row=4, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcripts_always_on_top_input.grid(row=4, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            # STORYTOOLKIT API FRAME GRID
            stai_api_key_label.grid(row=0, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            stai_api_key_input.grid(row=0, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            return form_vars

        def add_other_ingest_prefs(self, parent: tk.Widget, **kwargs) -> dict or None:
            """
            This function adds the other ingest preferences to the ingest preferences frame
            """

            # create the frames
            other_ingest_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)

            # create labels for the frames (and style them according to the theme)
            other_ingest_prefs_label = ctk.CTkLabel(parent, text='Other', **toolkit_UI.ctk_frame_label_settings)

            # we're going to create the form_vars dict to store all the variables
            # we will use this dict at the end of the function to gather all the created tk variables
            form_vars = {}

            # get the last grid row for the parent
            l_row = parent.grid_size()[1]

            # add the labels and frames to the parent
            other_ingest_prefs_label.grid(row=l_row + 1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            other_ingest_prefs_frame.grid(row=l_row + 2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # make the column expandable
            parent.columnconfigure(0, weight=1)
            other_ingest_prefs_frame.columnconfigure(1, weight=1)

            # INGEST SKIP SETTINGS
            ingest_skip_settings = kwargs.get('ingest_skip_settings', None) if kwargs.get(
                'ingest_skip_settings', None) is not None else self.toolkit_UI_obj.stAI.get_app_setting(
                'ingest_skip_settings',
                default_if_none=False)
            form_vars['ingest_skip_settings_var'] \
                = ingest_skip_settings_var = tk.BooleanVar(other_ingest_prefs_frame,
                                                                value=ingest_skip_settings)

            ingest_skip_settings_label = ctk.CTkLabel(other_ingest_prefs_frame, text='Skip Ingest Window',
                                                           **toolkit_UI.ctk_form_label_settings)
            ingest_skip_settings_input = ctk.CTkSwitch(other_ingest_prefs_frame,
                                                            variable=ingest_skip_settings_var,
                                                            text='', **toolkit_UI.ctk_form_entry_settings)

            # INGEST MAX FILES
            prevent_gaps_shorter_than = kwargs.get('ingest_file_limit', None) \
                if kwargs.get('ingest_file_limit', None) is not None \
                else self.toolkit_UI_obj.stAI.get_app_setting('ingest_file_limit', default_if_none=30)

            form_vars['ingest_file_limit_var'] = \
                ingest_file_limit_var = tk.StringVar(other_ingest_prefs_frame,
                                                     value=prevent_gaps_shorter_than)
            ingest_file_limit_label = ctk.CTkLabel(other_ingest_prefs_frame, text='Ingest Maximum',
                                                   **toolkit_UI.ctk_form_label_settings)

            ingest_file_limit_frame = ctk.CTkFrame(other_ingest_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            ingest_file_limit_input = ctk.CTkEntry(ingest_file_limit_frame,
                                                   textvariable=ingest_file_limit_var,
                                                   **toolkit_UI.ctk_form_entry_settings_half)
            ingest_file_limit_unit_label = ctk.CTkLabel(ingest_file_limit_frame, text='files per ingest')
            ingest_file_limit_input.pack(side=ctk.LEFT)
            ingest_file_limit_unit_label.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)

            # only allow floats in the prevent_gaps_shorter_than_input
            ingest_file_limit_input.configure(
                validate="key",
                validatecommand=(ingest_file_limit_input.register(self.toolkit_UI_obj.only_allow_integers), '%P')
            )

            # ADD ELEMENTS TO GRID
            ingest_skip_settings_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            ingest_skip_settings_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            ingest_file_limit_label.grid(row=2, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            ingest_file_limit_frame.grid(row=2, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            return form_vars

        def add_integrations_prefs(self, parent: tk.Widget, **kwargs) -> dict or None:
            """
            This function adds the integrations preferences to the ingest preferences frame
            """

            # create the frames
            resolve_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)

            # create labels for the frames (and style them according to the theme)
            resolve_prefs_label = ctk.CTkLabel(parent, text='DaVinci Resolve Studio',
                                               **toolkit_UI.ctk_frame_label_settings)

            # we're going to create the form_vars dict to store all the variables
            # we will use this dict at the end of the function to gather all the created tk variables
            form_vars = {}

            # get the last grid row for the parent
            l_row = parent.grid_size()[1]

            # add the labels and frames to the parent
            resolve_prefs_label.grid(row=l_row + 1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            resolve_prefs_frame.grid(row=l_row + 2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # make the column expandable
            parent.columnconfigure(0, weight=1)
            resolve_prefs_frame.columnconfigure(1, weight=1)

            # DISABLE RESOLVE API
            disable_resolve_api = \
                kwargs.get('disable_resolve_api', None) \
                    if kwargs.get('disable_resolve_api', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('disable_resolve_api', default_if_none=False)

            form_vars['disable_resolve_api_var'] = \
                disable_resolve_api_var = tk.BooleanVar(resolve_prefs_frame, value=disable_resolve_api)
            disable_resolve_api_label = ctk.CTkLabel(resolve_prefs_frame, text='Disable Resolve API',
                                                     **toolkit_UI.ctk_form_label_settings)
            disable_resolve_api_input = ctk.CTkSwitch(resolve_prefs_frame,
                                                      variable=disable_resolve_api_var,
                                                      text='',
                                                      **toolkit_UI.ctk_form_entry_settings)

            # OPEN TRANSCRIPTS ON TIMELINE CHANGE
            open_transcripts_on_timeline_change = \
                kwargs.get('open_transcripts_on_timeline_change', None) \
                    if kwargs.get('open_transcripts_on_timeline_change', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('open_transcripts_on_timeline_change',
                                                                  default_if_none=True)

            form_vars['open_transcripts_on_timeline_change_var'] = \
                open_transcripts_on_timeline_change_var = tk.BooleanVar(resolve_prefs_frame,
                                                                        value=open_transcripts_on_timeline_change)
            open_transcripts_on_timeline_change_label = ctk.CTkLabel(resolve_prefs_frame,
                                                                     text='Open Transcripts on Timeline',
                                                                     **toolkit_UI.ctk_form_label_settings)
            open_transcripts_on_timeline_change_input = ctk.CTkSwitch(resolve_prefs_frame,
                                                                      variable=open_transcripts_on_timeline_change_var,
                                                                      text='',
                                                                      **toolkit_UI.ctk_form_entry_settings)

            # CLOSE TRANSCRIPTS ON TIMELINE CHANGE
            close_transcripts_on_timeline_change = \
                kwargs.get('close_transcripts_on_timeline_change', None) \
                    if kwargs.get('close_transcripts_on_timeline_change', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('close_transcripts_on_timeline_change',
                                                                  default_if_none=True)

            form_vars['close_transcripts_on_timeline_change_var'] = \
                close_transcripts_on_timeline_change_var = tk.BooleanVar(resolve_prefs_frame,
                                                                         value=close_transcripts_on_timeline_change)
            close_transcripts_on_timeline_change_label = ctk.CTkLabel(resolve_prefs_frame,
                                                                      text='Close Transcripts on Timeline',
                                                                      **toolkit_UI.ctk_form_label_settings)
            close_transcripts_on_timeline_change_input = ctk.CTkSwitch(resolve_prefs_frame,
                                                                       variable=close_transcripts_on_timeline_change_var,
                                                                       text='',
                                                                       **toolkit_UI.ctk_form_entry_settings)

            # DEFAULT MARKER COLOR
            default_marker_color = \
                kwargs.get('default_marker_color', None) \
                    if kwargs.get('default_marker_color', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('default_marker_color', default_if_none='Blue')

            form_vars['default_marker_color_var'] = \
                default_marker_color_var = tk.StringVar(resolve_prefs_frame, value=default_marker_color)
            default_marker_color_label = ctk.CTkLabel(resolve_prefs_frame, text='Default Marker Color',
                                                      **toolkit_UI.ctk_form_label_settings)
            default_marker_color_input = ctk.CTkOptionMenu(resolve_prefs_frame,
                                                           variable=default_marker_color_var,
                                                           values=list(
                                                               self.toolkit_UI_obj.resolve_marker_colors.keys()),
                                                           **toolkit_UI.ctk_form_entry_settings)
            # TRANSCRIPTION RENDER PRESET
            transcription_render_preset = \
                kwargs.get('transcription_render_preset', None) \
                    if kwargs.get('transcription_render_preset', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('transcription_render_preset',
                                                                  default_if_none='transcription_WAV')

            form_vars['transcription_render_preset_var'] = \
                transcription_render_preset_var = tk.StringVar(resolve_prefs_frame, value=transcription_render_preset)
            transcription_render_preset_label = ctk.CTkLabel(resolve_prefs_frame, text='Transcription Render Preset',
                                                             **toolkit_UI.ctk_form_label_settings)
            transcription_render_preset_input = ctk.CTkEntry(resolve_prefs_frame,
                                                             textvariable=transcription_render_preset_var,
                                                             **toolkit_UI.ctk_form_entry_settings_double)
            # INGEST RENDER PRESET
            ingest_render_preset = \
                kwargs.get('ingest_render_preset', None) \
                    if kwargs.get('ingest_render_preset', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('ingest_render_preset', default_if_none='ingest_MP4')

            form_vars['ingest_render_preset_var'] = \
                ingest_render_preset_var = tk.StringVar(resolve_prefs_frame, value=ingest_render_preset)
            ingest_render_preset_label = ctk.CTkLabel(resolve_prefs_frame, text='Ingest Render Preset',
                                                      **toolkit_UI.ctk_form_label_settings)
            ingest_render_preset_input = ctk.CTkEntry(resolve_prefs_frame,
                                                      textvariable=ingest_render_preset_var,
                                                      **toolkit_UI.ctk_form_entry_settings_double)

            # ADD ELEMENTS TO GRID
            disable_resolve_api_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            disable_resolve_api_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            open_transcripts_on_timeline_change_label.grid(row=2, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            open_transcripts_on_timeline_change_input.grid(row=2, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            close_transcripts_on_timeline_change_label.grid(row=3, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            close_transcripts_on_timeline_change_input.grid(row=3, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            default_marker_color_label.grid(row=4, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            default_marker_color_input.grid(row=4, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcription_render_preset_label.grid(row=5, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            transcription_render_preset_input.grid(row=5, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            ingest_render_preset_label.grid(row=6, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            ingest_render_preset_input.grid(row=6, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            return form_vars

        def add_assistant_prefs(self, parent: tk.Widget, skip_general=False, **kwargs) -> dict or None:
            """
            This function adds the assistant preferences
            :param parent: the parent widget
            :param skip_general: if True, app wide settings will be skipped (for eg. OpenAI API key)
            :param kwargs: additional arguments
            """

            # create the frames
            assistant_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)
            openai_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)
            advanced_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)

            # create labels for the frames (and style them according to the theme)
            assistant_prefs_label = ctk.CTkLabel(parent, text='Assistant Settings', **toolkit_UI.ctk_frame_label_settings)
            openai_prefs_label = ctk.CTkLabel(parent, text='OpenAI Settings', **toolkit_UI.ctk_frame_label_settings)
            advanced_prefs_label = ctk.CTkLabel(parent, text='Advanced', **toolkit_UI.ctk_frame_label_settings)

            # we're going to create the form_vars dict to store all the variables
            # we will use this dict at the end of the function to gather all the created tk variables
            form_vars = {}

            # get the last grid row for the parent
            l_row = parent.grid_size()[1]

            # add the labels and frames to the parent
            assistant_prefs_label.grid(row=l_row + 1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            assistant_prefs_frame.grid(row=l_row + 2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            if not skip_general:
                openai_prefs_label.grid(row=l_row + 3, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
                openai_prefs_frame.grid(row=l_row + 4, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            advanced_prefs_label.grid(row=l_row + 5, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            advanced_prefs_frame.grid(row=l_row + 6, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # make the column expandable
            parent.columnconfigure(0, weight=1)
            openai_prefs_frame.columnconfigure(1, weight=1)

            # ASSISTANT PROVIDER
            assistant_provider = \
                kwargs.get('assistant_provider', None) \
                    if kwargs.get('assistant_provider', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_provider', default_if_none='OpenAI')

            assistant_provider_list = AssistantUtils.assistant_available_providers()

            form_vars['assistant_provider_var'] = \
                assistant_provider_var = tk.StringVar(assistant_prefs_frame, value=assistant_provider)
            assistant_provider_label = ctk.CTkLabel(assistant_prefs_frame, text='Assistant Provider',
                                                    **toolkit_UI.ctk_form_label_settings)
            assistant_provider_input = ctk.CTkOptionMenu(assistant_prefs_frame,
                                                         variable=assistant_provider_var,
                                                         values=assistant_provider_list,
                                                         **toolkit_UI.ctk_form_entry_settings)

            # ASSISTANT MODEL
            assistant_model = \
                kwargs.get('assistant_model', None) \
                    if kwargs.get('assistant_model', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_model', default_if_none='gpt-3.5-turbo')

            assistant_model_list = AssistantUtils.assistant_available_models(assistant_provider)

            form_vars['assistant_model_var'] = \
                assistant_model_var = tk.StringVar(assistant_prefs_frame, value=assistant_model)
            assistant_model_label = ctk.CTkLabel(assistant_prefs_frame, text='Assistant Model',
                                                 **toolkit_UI.ctk_form_label_settings)
            assistant_model_input = ctk.CTkOptionMenu(assistant_prefs_frame,
                                                      variable=assistant_model_var,
                                                      values=assistant_model_list,
                                                      **toolkit_UI.ctk_form_entry_settings)

            # store the initial provider value
            # so we can update the model list when the provider changes
            assistant_provider_var.previous_provider = assistant_provider_var.get()

            def update_assistant_model_options(*args):

                # Get the current provider
                current_provider = assistant_provider_var.get()

                # Check if the provider has actually changed
                if current_provider != assistant_provider_var.previous_provider:
                    # Update the model list based on the current provider
                    new_model_list = AssistantUtils.assistant_available_models(current_provider)

                    # Update the OptionMenu with new models
                    assistant_model_input.configure(values=new_model_list)

                    # Optionally, set the assistant_model_var to a default value
                    assistant_model_var.set(new_model_list[0])

                    # Update the previous provider for the next change
                    assistant_provider_var.previous_provider = current_provider

            # Trace the 'assistant_provider_var' to call the update function whenever it changes
            assistant_provider_var.trace('w', update_assistant_model_options)

            # System Prompt (Text)
            system_prompt = \
                kwargs.get('assistant_system_prompt', None) \
                    if kwargs.get('assistant_system_prompt', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_system_prompt',
                                                                  default_if_none=ASSISTANT_DEFAULT_SYSTEM_MESSAGE)

            # create the system prompt variable, label and input
            form_vars['assistant_system_prompt_var'] = \
                system_prompt_var = tk.StringVar(advanced_prefs_frame, value=system_prompt)
            system_prompt_label = ctk.CTkLabel(advanced_prefs_frame, text='System Prompt', **toolkit_UI.ctk_form_label_settings)
            system_prompt_input = ctk.CTkTextbox(advanced_prefs_frame, wrap=tk.WORD, **toolkit_UI.ctk_form_textbox)
            system_prompt_input.insert(tk.END, system_prompt)

            # if the initial prompt input changes, update the initial prompt variable
            def update_system_prompt(*args):
                system_prompt_var.set(system_prompt_input.get('1.0', tk.END))

            system_prompt_input.bind('<KeyRelease>', update_system_prompt)

            # TEMPERATURE
            temperature = \
                kwargs.get('assistant_temperature', None) \
                    if kwargs.get('assistant_temperature', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_temperature', default_if_none=1)

            form_vars['assistant_temperature_var'] = \
                temperature_var = tk.DoubleVar(advanced_prefs_frame, value=temperature)
            temperature_label = ctk.CTkLabel(advanced_prefs_frame, text='Temperature',
                                             **toolkit_UI.ctk_form_label_settings)

            temperature_slider_frame = ctk.CTkFrame(advanced_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            temperature_slider = ctk.CTkSlider(temperature_slider_frame, from_=0, to=2, variable=temperature_var,
                                               **toolkit_UI.ctk_form_slider_settings)

            temperature_entry = ctk.CTkEntry(temperature_slider_frame, width=50)
            temperature_entry.insert(0, str(temperature))
            toolkit_UI.bind_sync_functions(temperature_entry, temperature_slider, 0, 2)
            temperature_slider.pack(side=ctk.LEFT)
            temperature_entry.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)



            # MAXIMUM LENGTH
            max_length = \
                kwargs.get('assistant_max_length', None) \
                    if kwargs.get('assistant_max_length', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_max_length', default_if_none=512)

            form_vars['assistant_max_length_var'] = \
                max_length_var = tk.IntVar(advanced_prefs_frame, value=max_length)
            max_length_label = ctk.CTkLabel(advanced_prefs_frame, text='Maximum Length',
                                            **toolkit_UI.ctk_form_label_settings)
            max_length_slider_frame = ctk.CTkFrame(advanced_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            max_length_slider = ctk.CTkSlider(max_length_slider_frame, from_=1, to=4095, variable=max_length_var,
                                              **toolkit_UI.ctk_form_entry_settings)
            max_length_entry = ctk.CTkEntry(max_length_slider_frame, width=50)
            max_length_entry.insert(0, str(max_length))
            toolkit_UI.bind_sync_functions(max_length_entry, max_length_slider, 1, 4095, round_val=0)
            max_length_slider.pack(side=ctk.LEFT)
            max_length_entry.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)

            # STOP SEQUENCES
            # - this is a bit more difficult to implement since it would need a separator
            # stop_sequences = \
            #     kwargs.get('assistant_stop_sequences', None) \
            #         if kwargs.get('assistant_stop_sequences', None) is not None \
            #         else self.toolkit_UI_obj.stAI.get_app_setting('assistant_stop_sequences', default_if_none='')
            # form_vars['stop_sequences_var'] = \
            #     stop_sequences_var = tk.StringVar(advanced_prefs_frame, value=system_prompt)
            # stop_sequences_label = ctk.CTkLabel(advanced_prefs_frame, text='Stop sequences (one per line)',
            #                                    **toolkit_UI.ctk_form_label_settings)
            # stop_sequences_input = ctk.CTkTextbox(advanced_prefs_frame, wrap=tk.WORD, **toolkit_UI.ctk_form_textbox)
            # stop_sequences_input.insert(tk.END, stop_sequences)

            # if the stop sequences input changes, update the variable
            # def update_stop_sequences(*args):
            #     stop_sequences_var.set(system_prompt_input.get('1.0', tk.END))

            # stop_sequences_input.bind('<KeyRelease>', update_stop_sequences)

            # TOP P
            top_p = \
                kwargs.get('assistant_top_p', None) \
                    if kwargs.get('assistant_top_p', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_top_p', default_if_none=1)

            form_vars['assistant_top_p_var'] = \
                top_p_var = tk.DoubleVar(advanced_prefs_frame, value=top_p)
            top_p_label = ctk.CTkLabel(advanced_prefs_frame, text='Top P', **toolkit_UI.ctk_form_label_settings)
            top_p_slider_frame = ctk.CTkFrame(advanced_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            top_p_slider = ctk.CTkSlider(top_p_slider_frame, from_=0, to=1, variable=top_p_var,
                                         **toolkit_UI.ctk_form_entry_settings)
            top_p_entry = ctk.CTkEntry(top_p_slider_frame, width=50)
            top_p_entry.insert(0, str(top_p))
            toolkit_UI.bind_sync_functions(top_p_entry, top_p_slider, 0, 1)
            top_p_slider.pack(side=ctk.LEFT)
            top_p_entry.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)

            # FREQUENCY PENALTY
            frequency_penalty = \
                kwargs.get('assistant_frequency_penalty', None) \
                    if kwargs.get('assistant_frequency_penalty', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_frequency_penalty', default_if_none=0.0)

            form_vars['assistant_frequency_penalty_var'] = \
                frequency_penalty_var = tk.DoubleVar(advanced_prefs_frame, value=frequency_penalty)
            frequency_penalty_label = ctk.CTkLabel(advanced_prefs_frame, text='Frequency Penalty',
                                                   **toolkit_UI.ctk_form_label_settings)
            frequency_penalty_slider_frame = ctk.CTkFrame(advanced_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            frequency_penalty_slider = ctk.CTkSlider(frequency_penalty_slider_frame, from_=0, to=2,
                                                     variable=frequency_penalty_var,
                                                     **toolkit_UI.ctk_form_entry_settings)
            frequency_penalty_entry = ctk.CTkEntry(frequency_penalty_slider_frame, width=50)
            frequency_penalty_entry.insert(0, str(frequency_penalty))
            toolkit_UI.bind_sync_functions(frequency_penalty_entry, frequency_penalty_slider, 0, 2)
            frequency_penalty_slider.pack(side=ctk.LEFT)
            frequency_penalty_entry.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)

            # PRESENCE PENALTY
            presence_penalty = \
                kwargs.get('assistant_presence_penalty', None) \
                    if kwargs.get('assistant_presence_penalty', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('assistant_presence_penalty', default_if_none=0.0)

            form_vars['assistant_presence_penalty_var'] = \
                presence_penalty_var = tk.DoubleVar(advanced_prefs_frame, value=presence_penalty)
            presence_penalty_label = ctk.CTkLabel(advanced_prefs_frame, text='Presence Penalty',
                                                  **toolkit_UI.ctk_form_label_settings)
            presence_penalty_slider_frame = ctk.CTkFrame(advanced_prefs_frame, **toolkit_UI.ctk_frame_transparent)
            presence_penalty_slider = ctk.CTkSlider(presence_penalty_slider_frame, from_=0, to=2, variable=presence_penalty_var,
                                                    **toolkit_UI.ctk_form_entry_settings)
            presence_penalty_entry = ctk.CTkEntry(presence_penalty_slider_frame, width=50)
            presence_penalty_entry.insert(0, str(presence_penalty))
            toolkit_UI.bind_sync_functions(presence_penalty_entry, presence_penalty_slider, 0, 2)
            presence_penalty_slider.pack(side=ctk.LEFT)
            presence_penalty_entry.pack(side=ctk.LEFT, **toolkit_UI.ctk_form_paddings)



            # ADD ELEMENTS TO ASSISTANT GRID
            assistant_provider_label.grid(row=0, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            assistant_provider_input.grid(row=0, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            assistant_model_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            assistant_model_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            # ADD ELEMENTS TO THE ADVANCED GRID
            system_prompt_label.grid(row=2, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            system_prompt_input.grid(row=2, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            temperature_label.grid(row=3, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            temperature_slider_frame.grid(row=3, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            max_length_label.grid(row=4, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            max_length_slider_frame.grid(row=4, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            # stop_sequences_label.grid(row=5, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            # stop_sequences_input.grid(row=5, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            top_p_label.grid(row=6, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            top_p_slider_frame.grid(row=6, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            frequency_penalty_label.grid(row=7, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            frequency_penalty_slider_frame.grid(row=7, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            presence_penalty_label.grid(row=8, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            presence_penalty_slider_frame.grid(row=8, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            if not skip_general:
                # OPENAI KEY
                # get the api key from the app settings
                openai_api_key = \
                    kwargs.get('openai_api_key', None) \
                        if kwargs.get('openai_api_key', None) is not None \
                        else self.toolkit_UI_obj.stAI.get_app_setting('openai_api_key', default_if_none=None)

                # create the openai api key variable, label and input
                form_vars['openai_api_key_var'] = \
                    openai_api_key_var = tk.StringVar(openai_prefs_frame, value=openai_api_key if openai_api_key else '')
                openai_api_key_label = ctk.CTkLabel(openai_prefs_frame, text='OpenAI API Key',
                                                    **toolkit_UI.ctk_form_label_settings)
                openai_api_key_input = ctk.CTkEntry(openai_prefs_frame, show="*",
                                                    textvariable=openai_api_key_var,
                                                    **toolkit_UI.ctk_form_entry_settings_double)

                # ADD ELEMENTS TO OPENAI GRID
                openai_api_key_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
                openai_api_key_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)


            return form_vars

        def add_search_prefs(self, parent: tk.Widget, **kwargs) -> dict or None:
            """
            This function adds the search preferences
            """

            # create the frames
            search_prefs_frame = ctk.CTkFrame(parent, **toolkit_UI.ctk_frame_transparent)

            # create labels for the frames (and style them according to the theme)
            search_prefs_label = ctk.CTkLabel(parent, text='Search Models', **toolkit_UI.ctk_frame_label_settings)

            # we're going to create the form_vars dict to store all the variables
            # we will use this dict at the end of the function to gather all the created tk variables
            form_vars = {}

            # get the last grid row for the parent
            l_row = parent.grid_size()[1]

            # add the labels and frames to the parent
            search_prefs_label.grid(row=l_row + 1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            search_prefs_frame.grid(row=l_row + 2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # make the column expandable
            parent.columnconfigure(0, weight=1)
            search_prefs_frame.columnconfigure(1, weight=1)

            # SEMANTIC SEARCH MODEL
            # get the model name from the app settings
            s_semantic_search_model_name = \
                kwargs.get('s_semantic_search_model_name', None) \
                    if kwargs.get('s_semantic_search_model_name', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('s_semantic_search_model_name', default_if_none=None)

            # create the variable, label and input
            form_vars['s_semantic_search_model_name_var'] = \
                s_semantic_search_model_name_var = tk.StringVar(
                search_prefs_frame, value=s_semantic_search_model_name if s_semantic_search_model_name else '')
            s_semantic_search_model_name_label = ctk.CTkLabel(search_prefs_frame, text='Semantic Search Model',
                                                              **toolkit_UI.ctk_form_label_settings)
            s_semantic_search_model_name_input = ctk.CTkEntry(search_prefs_frame,
                                                              textvariable=s_semantic_search_model_name_var,
                                                              **toolkit_UI.ctk_form_entry_settings_double)

            # TEXT CLASSIFIER MODEL
            # get the model from the app settings
            text_classifier_model = \
                kwargs.get('text_classifier_model', None) \
                    if kwargs.get('text_classifier_model', None) is not None \
                    else self.toolkit_UI_obj.stAI.get_app_setting('text_classifier_model', default_if_none=None)

            # create the model variable, label and input
            form_vars['text_classifier_model_var'] = \
                text_classifier_model_var = tk.StringVar(search_prefs_frame,
                                                         value=text_classifier_model if text_classifier_model else '')
            text_classifier_model_label = ctk.CTkLabel(search_prefs_frame, text='Text Classification Model',
                                                       **toolkit_UI.ctk_form_label_settings)
            text_classifier_model_input = ctk.CTkEntry(search_prefs_frame,
                                                       textvariable=text_classifier_model_var,
                                                       **toolkit_UI.ctk_form_entry_settings_double)

            # PRE-INDEXING TEXT ANALYSIS
            preindexing_textanalysis = kwargs.get('search_preindexing_textanalysis', None) \
                if kwargs.get('search_preindexing_textanalysis', None) is not None \
                else self.stAI.get_app_setting('search_preindexing_textanalysis', default_if_none=False)

            form_vars['search_preindexing_textanalysis_var'] = \
                preindexing_textanalysis_var = tk.BooleanVar(search_prefs_frame,
                                                         value=preindexing_textanalysis)
            preindexing_textanalysis_label = ctk.CTkLabel(search_prefs_frame, text='Pre-indexing Text Analysis',
                                                      **toolkit_UI.ctk_form_label_settings)
            preindexing_textanalysis_input = ctk.CTkSwitch(search_prefs_frame, variable=preindexing_textanalysis_var,
                                                       text='', **toolkit_UI.ctk_form_entry_settings)

            # AUTOCLEAR WINDOW
            search_clear_before_results = kwargs.get('search_clear_before_results', None) \
                if kwargs.get('search_clear_before_results', None) is not None \
                else self.stAI.get_app_setting('search_clear_before_results', default_if_none=True)

            form_vars['search_clear_before_results_var'] = \
                search_clear_before_results_var = tk.BooleanVar(search_prefs_frame,
                                                         value=search_clear_before_results)
            search_clear_before_results_label = ctk.CTkLabel(search_prefs_frame, text='Clear Before Results',
                                                      **toolkit_UI.ctk_form_label_settings)
            search_clear_before_results_input = ctk.CTkSwitch(search_prefs_frame, variable=search_clear_before_results_var,
                                                       text='', **toolkit_UI.ctk_form_entry_settings)

            # ADD ELEMENTS TO GRID
            s_semantic_search_model_name_label.grid(row=1, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            s_semantic_search_model_name_input.grid(row=1, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            text_classifier_model_label.grid(row=2, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            text_classifier_model_input.grid(row=2, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            preindexing_textanalysis_label.grid(row=3, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            preindexing_textanalysis_input.grid(row=3, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)
            search_clear_before_results_label.grid(row=4, column=0, sticky="w", **toolkit_UI.ctk_form_paddings)
            search_clear_before_results_input.grid(row=4, column=1, sticky="w", **toolkit_UI.ctk_form_paddings)

            return form_vars

        def save_preferences(self, input_variables: dict) -> bool:
            """
            Save the preferences stored in the input_variables to the app config file
            :param input_variables:
            :return:
            """

            # PROCESS THE VARIABLES HERE FIRST

            # if the user has entered a new API key, check if it's valid
            if input_variables['stai_api_key_var'].get() != '' \
                    and input_variables['stai_api_key_var'].get() != self.stAI.config.get('stai_api_key', None):

                if not self.stAI.check_api_key(input_variables['stai_api_key_var'].get()):
                    self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error', message='Invalid API key.')
                    return False

            # only allow values between 0 and 1 for transcription_speaker_detection_threshold
            if input_variables['transcription_speaker_detection_var'].get()\
            and not 0 < float(input_variables['transcription_speaker_detection_threshold_var'].get()) <= 1:
                self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error',
                                                          message='Speaker detection threshold '
                                                                  'must be greater than 0, but maximum 1.')
                return False

            # if no speaker detection is selected, remove the threshold
            elif not input_variables['transcription_speaker_detection_var'].get():
                del input_variables['transcription_speaker_detection_threshold_var']

            # if the user has entered transcription_custom_punctuation_marks,
            if input_variables['transcription_custom_punctuation_marks_var'].get() != '':

                # convert the string to a list, but use each space as a delimiter
                # but make sure it's a list
                transcription_custom_punctuation_marks = \
                    list(input_variables['transcription_custom_punctuation_marks_var'].get().strip().split(' '))

                # remove any empty strings
                transcription_custom_punctuation_marks = [x for x in transcription_custom_punctuation_marks if x != '']

                # only single, non-empty strings are allowed
                for punctuation_mark in transcription_custom_punctuation_marks:
                    if len(punctuation_mark) != 1:
                        self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error',
                                                                  message='Invalid punctuation mark: {}\n'
                                                                          'Please use only single characters '
                                                                          'divided by an empty space.'
                                                                  .format(punctuation_mark))
                        return False

                # set the config variable to save it later
                self.stAI.config['transcription_custom_punctuation_marks'] = transcription_custom_punctuation_marks

                # and remove it from the input_variables dict so we don't iterate over it later
                del input_variables['transcription_custom_punctuation_marks_var']

            # if the transcription_custom_punctuation_marks is empty, set it as an empty list
            else:
                del input_variables['transcription_custom_punctuation_marks']
                self.stAI.config['transcription_custom_punctuation_marks_var'] = []

            # depending on the unit,
            # we will either fill this variable with the max characters or the max words from the app settings / kwargs
            if input_variables['max_per_line_unit_var'].get() != '':
                max_per_line_setting_name = \
                    'transcription_max_words_per_segment' \
                        if input_variables['max_per_line_unit_var'].get() == 'words' \
                        else 'transcription_max_chars_per_segment'

                # set the config variables to save them later
                # the max_per_line unit
                self.stAI.config['transcription_max_per_line_unit'] \
                    = 'words' if max_per_line_setting_name == 'transcription_max_words_per_segment' else 'characters'
                # the max_per_line value
                self.stAI.config[max_per_line_setting_name] = input_variables['max_per_line_var'].get()

                del input_variables['max_per_line_unit_var']

            # delete this variable since we already used it if we had to
            del input_variables['max_per_line_var']

            # source language becomes transcription default language
            self.stAI.config['transcription_default_language'] = input_variables['source_language_var'].get()
            del input_variables['source_language_var']

            # model_name becomes whisper_model_name
            self.stAI.config['whisper_model_name'] = input_variables['model_name_var'].get()
            del input_variables['model_name_var']

            # device becomes whisper device
            self.stAI.config['whisper_device'] = input_variables['device_var'].get()
            del input_variables['device_var']

            # pre_detect_speech becomes transcription_pre_detect_speech
            self.stAI.config['transcription_pre_detect_speech'] = input_variables['pre_detect_speech_var'].get()
            del input_variables['pre_detect_speech_var']

            # word_timestamps_var becomes transcription_word_timestamps
            self.stAI.config['transcription_word_timestamps'] = input_variables['word_timestamps_var'].get()
            del input_variables['word_timestamps_var']

            # pre_detect_speech becomes initial_prompt_var
            self.stAI.config['transcription_initial_prompt'] = input_variables['initial_prompt_var'].get()
            del input_variables['initial_prompt_var']

            # split_on_punctuation becomes transcription_split_on_punctuation_marks
            self.stAI.config['transcription_split_on_punctuation_marks'] \
                = input_variables['split_on_punctuation_var'].get()
            del input_variables['split_on_punctuation_var']

            # prevent_gaps_shorter_than becomes transcription_prevent_short_gaps
            self.stAI.config['transcription_prevent_short_gaps'] \
                = input_variables['prevent_gaps_shorter_than_var'].get()
            del input_variables['prevent_gaps_shorter_than_var']

            # group_questions becomes transcription_group_questions
            self.stAI.config['transcription_group_questions'] = input_variables['group_questions_var'].get()
            del input_variables['group_questions_var']



            if input_variables['video_indexing_index_candidate_var'].get() == 'the first frame':
                self.stAI.config['video_indexing_index_candidate'] = 'first'
            else:
                self.stAI.config['video_indexing_index_candidate'] = 'sharp'
            del input_variables['video_indexing_index_candidate_var']

            # the video sensitivity needs a bit of conversion
            # sensitivity = input_variables['clip_shot_change_sensitivity_var'].get()
            # del input_variables['clip_shot_change_sensitivity_var']

            # the sensitivity is between 0 and 100, but the encoder expects a value between 255 (lowest) and 0 (highest)
            # self.stAI.config['clip_shot_change_sensitivity'] = 255 - int(sensitivity * 255 / 100)

            # SAVE THE VARIABLES FROM HERE ON

            # save all the variables to the config file
            for key, value in input_variables.items():

                # if the key ends with "_var", remove it
                if key.endswith('_var'):
                    # remove the "_var" from the key
                    key = key[:-4]

                self.stAI.config[key] = value.get()

            # save the config file
            if self.stAI.save_config():

                # let the user know it worked
                self.toolkit_UI_obj.notify_via_messagebox(type='info', title='Preferences Saved',
                                                          message='Preferences saved successfully.\n\n'
                                                                  'Please restart StoryToolkitAI for the new settings '
                                                                  'to take full effect.',
                                                          message_log='Preferences saved, need restart for full effect',
                                                          parent=self.toolkit_UI_obj.get_window_by_id('preferences'))


                # close the window
                self.toolkit_UI_obj.destroy_window_(window_id='preferences')
                return True

            else:
                self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Error',
                                                          message='Preferences could not be saved.\n'
                                                                  'Check log for details.',
                                                          message_log='Preferences could not be saved',
                                                          parent=self.toolkit_UI_obj.get_window_by_id('preferences'))

                return False

        def open_about_window(self):
            """
            Open the about window
            :return:
            """

            # open the about window

            # create a window for the about window if one doesn't already exist
            if about_window := self.toolkit_UI_obj.create_or_open_window(parent_element=self.root,
                                                                         window_id='about',
                                                                         title='About StoryToolkitAI', resizable=False,
                                                                         return_window=True):
                # the text justify
                justify = {'justify': ctk.LEFT}

                # create a frame for the about window
                about_frame = ctk.CTkFrame(about_window, **toolkit_UI.ctk_frame_transparent)
                about_frame.pack(**toolkit_UI.ctk_full_window_frame_paddings)

                # add the app name text
                app_name = 'StoryToolkitAI version ' + self.stAI.version

                # create the app name heading
                app_name_label = ctk.CTkLabel(about_frame, text=app_name, font=self.toolkit_UI_obj.default_font_h1,
                                              **justify)
                app_name_label.grid(column=1, row=1, sticky='w')

                # the made by frame
                made_by_frame = ctk.CTkFrame(about_frame, **toolkit_UI.ctk_frame_transparent)
                made_by_frame.grid(column=1, row=2, sticky='w')

                # create the made by label
                made_by_label = ctk.CTkLabel(made_by_frame, text='made by ', font=self.toolkit_UI_obj.default_font,
                                             **justify)
                made_by_label.pack(side=ctk.LEFT)

                # create the mots link label
                mots_label = ctk.CTkLabel(made_by_frame, text='mots', font=self.toolkit_UI_obj.default_font_link,
                                          **justify)
                mots_label.pack(side=ctk.LEFT)

                # make the made by text clickable
                mots_label.bind('<Button-1>', self.UI_menus.open_mots)

                # the project page frame
                project_page_frame = ctk.CTkFrame(about_frame, **toolkit_UI.ctk_frame_transparent)
                project_page_frame.grid(column=1, row=3, sticky='w', pady=toolkit_UI.ctk_form_paddings['pady'])

                # add the project page label
                project_page_label = ctk.CTkLabel(project_page_frame, text='Project page: ',
                                                  font=self.toolkit_UI_obj.default_font, **justify)
                project_page_label.pack(side=ctk.LEFT)

                # create the project page link label
                project_page_link_label = ctk.CTkLabel(project_page_frame, text='github.com/octimot/StoryToolkitAI',
                                                       font=self.toolkit_UI_obj.default_font_link, **justify)
                project_page_link_label.pack(side=ctk.LEFT)

                # make the project page text clickable
                project_page_link_label.bind('<Button-1>', self.UI_menus.open_project_page)

                # add license info
                license_info_label = ctk.CTkLabel(about_frame,
                                                  text='For third party software and license information\n'
                                                       'see the project page.',
                                                  font=self.toolkit_UI_obj.default_font, **justify)
                license_info_label.grid(column=1, row=4, sticky='w')

                return True

            return

    def __init__(self, toolkit_ops_obj=None, stAI=None, **other_options):

        # make a reference to toolkit ops obj
        self.toolkit_ops_obj = toolkit_ops_obj

        # make a reference to StoryToolkitAI obj
        self.stAI = stAI

        # initialize tkinter as the main GUI
        self.root = ctk.CTk()

        # what happens when the user tries to close the main window
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.UI_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'UI')

        # if the UI_folder wasn't found, try to find it relative to the directory of the main script
        if not os.path.isdir(self.UI_folder):
            self.UI_folder = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '..', 'UI')

        # if the UI_folder wasn't found, try to find it relative to the directory of the main script
        if not os.path.isdir(self.UI_folder):
            self.UI_folder = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), 'UI')

        # set window/bar icon
        self.UI_set_icon(self.root)

        # initialize app items object
        self.app_items_obj = self.AppItemsUI(toolkit_UI_obj=self)

        # load menu object
        self.main_menu = UImenus(toolkit_UI_obj=self, parent=self.root)

        logger.debug('Running with TK {}'.format(self.root.call("info", "patchlevel")))

        # initialize transcript edit object
        self.t_edit_obj = self.TranscriptEdit(toolkit_UI_obj=self)

        # alert the user if ffmpeg isn't installed
        if 'ffmpeg_status' in other_options and not other_options['ffmpeg_status']:
            self.notify_via_messagebox(title='FFMPEG not found',
                                       message='FFMPEG was not found on this machine.\n'
                                               'Please follow the installation instructions or StoryToolkitAI will '
                                               'not work correctly.',
                                       type='error'
                                       )

        # show welcome message, if it wasn't muted via configs
        # if self.stAI.get_app_setting('show_welcome', default_if_none=True):
        #    self.open_welcome_window()

        # keep all the window references here to find them easily by window_id
        self.windows = {}

        # keep track of which window is what type by window_id
        self.window_types = {}

        # keep track of all the window observers
        # {window_id: {action: observer_obj etc.}}
        self.windows_observers = {}

        # use this to keep the text_windows
        # this doesn't apply only to windows opened with the open_text_window method, but can be used for any window
        # that has a text widget which needs to be accessed externally
        # the format is {window_id: {text: str, text_widget: Text etc., find_window: str etc.}
        self.text_windows = {}

        # this is used to keep a reference to all the windows that have find functionality
        # the format is {find_window_id: {parent_window_id: str, find_text: str, find_text_widget: Text etc.}}
        self.find_windows = {}

        # find results indexes stored here
        # we're making it a dict so that we can store result indexes for each window individually
        self.find_result_indexes = {}

        # when searching for text, you may want the user to cycle through the results, so this keep track
        # keeps track on which search result is the user currently on (in each transcript window)
        self.find_result_pos = {}

        # to keep track of what is being searched on each window
        self.find_strings = {}

        # this holds a prompt history for the windows that support it
        # the format is {window_id: [prompt1, prompt2, prompt3, etc.]}
        self.window_prompts = {}

        # this holds the index of the current prompt in the prompt history
        self.window_prompts_index = {}

        # currently focused window (id only)
        self.current_focused_window = None

        # last focused window (id only)
        self.last_focused_window = None

        # what to call before exiting the app
        self.before_exit = None

        self.OS_scale_factor = self.UI_get_OS_scale_factor()

        # first - find out if there is any "courier" font installed
        # and select one of the versions
        available_fonts = font.families()
        if 'Courier' in available_fonts:
            courier_font_family = 'Courier'
        elif 'Courier New' in available_fonts:
            courier_font_family = 'Courier New'
        else:
            logger.debug('No "Courier" font found. Using default fixed font.')
            courier_font_family = 'TkFixedFont'

        # lock to dark mode
        ctk.set_appearance_mode("dark")

        # customtkinter font defaults:
        self.ctk_default_font_family = ctk.ThemeManager.theme["CTkFont"]["family"]
        self.ctk_default_font_size = ctk.ThemeManager.theme["CTkFont"]["size"]

        # get the font size, but scale them for the machine
        font_scale = 1.2
        self.default_font_size = self.UI_scale(self.ctk_default_font_size)
        self.transcript_font_size = self.UI_scale(self.stAI.get_app_setting('transcript_font_size', default_if_none=15)
                                                  * font_scale)
        self.console_font_size = self.UI_scale(self.stAI.get_app_setting('console_font_size', default_if_none=13)
                                               * font_scale)

        # set platform independent transcript font
        self.transcript_font = ctk.CTkFont(family=courier_font_family, size=self.transcript_font_size)

        # meta transcript segment font
        self.meta_transcript_font = \
            ctk.CTkFont(family=self.ctk_default_font_family, size=int(self.transcript_font_size*0.8))

        # set the platform independent fixed font (for console)
        # self.console_font = ctk.CTkFont(family='TkFixedFont', size=self.console_font_size)
        self.console_font = self.transcript_font

        # set the default font size
        self.default_font_size = self.UI_scale(self.default_font_size * font_scale)

        # set the platform independent default font (and variants)
        self.default_font = ctk.CTkFont(family=self.ctk_default_font_family, size=self.default_font_size)
        self.default_font_link = ctk.CTkFont(family=self.ctk_default_font_family, size=self.default_font_size)
        self.default_font_h1 = ctk.CTkFont(family=self.ctk_default_font_family, size=int(self.default_font_size + 7))
        self.default_font_h2 = ctk.CTkFont(family=self.ctk_default_font_family, size=int(self.default_font_size + 3))
        self.default_font_h3 = ctk.CTkFont(family=self.ctk_default_font_family, size=int(self.default_font_size + 1))

        # CMD or CTRL?
        # use CMD for Mac
        if platform.system() == 'Darwin':
            self.ctrl_cmd_bind = "Command"
            self.alt_bind = "Mod2"
        # use CTRL for Windows
        else:
            self.ctrl_cmd_bind = "Control"
            self.alt_bind = "Alt"

        # use this variable to remember if the user said it's ok that resolve is not available to continue a process
        self.no_resolve_ok = False

        # handling of api key validity
        if not self.stAI.api_key_valid:

            def show_support_popup(popup_title="One more thing!"):

                # recheck this before we show the popup
                # - maybe the connection took longer on the previous attempt
                if self.stAI.api_key_valid:
                    return

                support_page_url = 'https://storytoolkit.ai/support'

                # check if a support page is available
                try:
                    support_page = get(support_page_url, timeout=2)

                    # if the support page is not available
                    if support_page.status_code != 200:
                        return

                except Exception as e:
                    return

                support = messagebox.askyesno(popup_title,
                                              "StoryToolkitAI is completely free and open source.\n\n "
                                              "If you find it useful, "
                                              "we need your help to speed up development. \n\n"
                                              "Would you like to support the project?")
                if support:
                    webbrowser.open(support_page_url)

            def before_exit(event=None):

                show_support_popup(popup_title="One more thing!")

            # redefine the on exit function
            self.before_exit = before_exit

            if random.randint(0, 50) < 20:
                self.root.after(random.randint(4000, 7000), show_support_popup, ["Thanks for using StoryToolkitAI!"])

        # show the update available message if any
        if self.stAI.update_available and self.stAI.update_available is not None:

            # the url to the releases page
            release_url = 'https://github.com/octimot/StoryToolkitAI/releases/latest'

            goto_projectpage = False

            update_window_id = 'update_available'

            # if there is a new version available
            # the user will see a different update message
            # depending if they're using the standalone version or not
            if self.stAI.standalone:
                warn_message = 'A new standalone version of StoryToolkitAI is available.'

                # add the question to the pop up message box
                messagebox_message = warn_message + ' \n\nDo you want to open the release page?\n'

                changelog_instructions = 'Open the [release page]({}) to download it.\n\n'.format(release_url)

                # prepare some action buttons for the text window
                action_buttons = [{'text': 'Open release page', 'command': lambda: webbrowser.open(release_url)}]

            # for the non-standalone version
            else:
                warn_message = 'A new version of StoryToolkitAI is available.\n\n' \
                               'Use git pull to update.\n '

                changelog_instructions = 'Maybe update now before getting back to work?\n' + \
                                         'Click Update or quit the tool and use `git pull` to update.\n\n' \

                # prepare some action buttons for the text window
                def update_via_git():
                    """
                    This calls the update via git function from the stAI object
                    And triggers an error message if it fails
                    """

                    # try to update via git
                    if not self.stAI.update_via_git():

                        # if the update failed, show an error message
                        self.notify_via_messagebox(
                            type='error',
                            title='Unable to update',
                            message='Something went wrong with the automatic update process.\n\n'
                                    'Please check logs and try to update manually by running `git pull` '
                                    'in the installation folder.',
                            message_log='Unable to update via git',
                        )




                action_buttons = [{'text': 'Update', 'command': lambda: update_via_git()}]

            # read the CHANGELOG.md file from github
            changelog_file = get('https://raw.githubusercontent.com/octimot/StoryToolkitAI/master/CHANGELOG.md')

            # if the request was successful
            if changelog_file.status_code == 200:

                import packaging

                # get the changelog text
                changelog_text = changelog_file.text
                changelog_new_versions = '# A new update is waiting!\n' + \
                                         changelog_instructions

                changelog_new_versions_info = ''

                # split the changelog into versions
                # the changelog is in a markdown format
                changelog_versions = dict()
                for version_full in changelog_text.split('\n## '):

                    # split the version into the version string and the text
                    version_str, text = version_full.split('\n', 1)

                    version_no_and_date = version_str.split('] - ')

                    if len(version_no_and_date) == 2:
                        version_no = version_no_and_date[0].strip('[')
                        version_date = version_no_and_date[1].strip()

                        # add the version to the dictionary
                        changelog_versions[version_no] = {'date': version_date, 'text': text.strip()}

                # get the current installed version
                current_version = self.stAI.version

                # show the changelog for all versions newer than the current installed version
                for version_no, version_info in changelog_versions.items():

                    version_date = version_info['date']
                    text = version_info['text']

                    # remove any double newlines from the text
                    text = text.replace('\n\n', '\n')

                    # if we reached the current version, stop
                    # this doesn't behave well if the version number is x.x.x.x vs x.x.x
                    if packaging.version.parse(version_no) <= packaging.version.parse(current_version):
                        break

                    changelog_new_versions_info += f'\n## Version {version_no}\n\n{text}\n'

                # add the changelog to the message
                if changelog_new_versions_info != '':
                    changelog_new_versions += '# What\'s new since you last updated?\n' + changelog_new_versions_info

                # add the skip and later buttons to the action buttons
                action_buttons.append({'text': 'Skip this version',
                                       'command': lambda: self.ignore_update(
                                           version_to_ignore=self.stAI.online_version,
                                           window_id=update_window_id),
                                       'side': tk.RIGHT,
                                       'anchor': 'e'
                                       })
                action_buttons.append({'text': 'Later', 'command': lambda: self.destroy_text_window(update_window_id),
                                       'side': tk.RIGHT, 'anchor': 'e'})

                # open the CHANGELOG.md file from github in a text window
                update_window_id = self.open_text_window(title='New Update',
                                                         window_id=update_window_id,
                                                         initial_text=changelog_new_versions,
                                                         action_buttons=action_buttons)

                # format the text
                self.text_window_format_md(update_window_id)

            # if the changelog file is not available
            # show a simple message popup
            else:

                if self.stAI.standalone:
                    # notify the user and ask whether to open the release website or not
                    goto_projectpage = messagebox.askyesno(title="Update available",
                                                           message=messagebox_message)

                else:
                    messagebox.showinfo(title="Update available",
                                        message=warn_message)

            # notify the user via console
            logger.warning(warn_message)

            # open the browser and go to the release_url
            if goto_projectpage:
                webbrowser.open(release_url)

        # open the Queue window if something is up in the transcription queue
        if len(self.toolkit_ops_obj.processing_queue.get_all_queue_items()) > 0:
            self.open_queue_window()

    def UI_scale(self, value: int) -> int:
        """
        Applies the OS scale factor to the value.
        """

        if self.OS_scale_factor is None:
            self.UI_get_OS_scale_factor()

        return int(value * self.OS_scale_factor)

    def UI_get_OS_scale_factor(self) -> int:
        """
        Get the OS scale factor.
        """

        # Windows
        if sys.platform == "win32":
            import ctypes

            # this only gets the scaling of the primary monitor on Windows (device 0)
            self.OS_scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

        # MacOS and Linux
        elif sys.platform == "darwin" or sys.platform == "linux":

            # we keep the scaling factor at 1
            self.OS_scale_factor = 1

        # other alien systems
        else:
            self.OS_scale_factor = 1

        return self.OS_scale_factor

    def UI_set_icon(self, window):
        """
        Sets the bar icon for the window (only for windows)
        """

        # add icon
        try:

            photo = tk.PhotoImage(file=os.path.join(self.UI_folder, 'StoryToolkitAI.png'))
            window.wm_iconphoto(False, photo)

            # set bar icon for windows
            if sys.platform == 'win32':
                window.iconbitmap(os.path.join(self.UI_folder, 'StoryToolkitAI.ico'))

                # this hack is needed to override the 200ms icon replacement done by customtkinter
                window.after(300, lambda: window.iconbitmap(os.path.join(self.UI_folder, 'StoryToolkitAI.ico')))

        except:
            logger.debug('Could not load StoryToolkitAI icon.', exc_info=True)

    def only_allow_integers(self, value):
        """
        Validation function for the entry widget.
        """
        if value.isdigit():
            return True
        elif value == "":
            return True
        else:
            return False

    def only_allow_integers_non_null(self, value):
        """
        Validation function for the entry widget.
        """
        if value.isdigit():
            return True
        else:
            return False

    def only_allow_floats(self, value):
        """
        Validation function for the entry widget.
        """

        if value == "":
            return True

        try:
            float(value)
            return True
        except ValueError:
            return False

    def ignore_update(self, version_to_ignore=None, window_id=None):
        """
        This function is called when the user clicks the "Skip this version" button in the update window.
        :param version_to_ignore:
        :param window_id:
        :return:
        """

        # confirm the action
        if not messagebox.askyesno(title="Skip update",
                                   message="Are you sure you want to skip this update?\n\n"
                                           "You will only be notified again when a new update "
                                           "is available.",
                                   parent=self.windows[window_id] if window_id is not None else self.root):
            return False

        # if the window id is specified
        if window_id is not None:
            # destroy the window
            self.destroy_text_window(window_id)

        # if the version to ignore is not specified
        if version_to_ignore is None:
            return False

        # add the version_to_ignore to the config file
        self.stAI.config['ignore_update'] = version_to_ignore

        # save the config file
        self.stAI.save_config()

    def on_exit(self):
        """
        This function is usually called when the user closes the main window or exits the program via the menu.
        :return:
        """

        # check if there are any items left in the queue
        # if there are, ask the user if they want to quit anyway

        queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items(
            not_status=['failed', 'done', 'canceled', 'canceling'])

        if queue_items is not None and len(queue_items) > 0:

            quit_anyway = messagebox.askyesno(title="Are you sure?",
                                              message="There are still items in the queue.\n"
                                                      "These will be restarted when you restart StoryToolkitAI.\n\n"
                                                      "Quit anyway?")

            # if the user doesn't want to quit anyway, return
            if not quit_anyway:
                return

        # if a before_exit function is defined, call it
        if self.before_exit is not None:
            self.before_exit()

        # close the main window
        self.root.destroy()

        # and finally, exit the program
        sys.exit()

    # GENERAL WINDOW FUNCTIONS

    def get_window_by_id(self, window_id):
        """
        Simple function to get a window by its id from the windows dict.
        """

        if window_id and window_id in self.windows:
            return self.windows[window_id]

        # if the window id is not found, return None
        return None

    def focus_window(self, window_id=None, window=None):
        """
        This function focuses a window. Requires either a window_id or a window
        :param window_id: The window id of the window to focus. (must be available in self.windows)
        :param window: The window object to focus.
        """

        if window_id is None and window is None:
            logger.debug('We need at least a window id or a window object to focus a window.')
            return False

        # if the window id is not available in the window list, return
        if window_id is not None and window_id not in self.windows:
            logger.debug('Window not found: {}'.format(window_id))
            return False

        window = self.get_window_by_id(window_id) if window is None else window

        # bring the window to the top
        window.lift()

        # bring it to the front again after 100ms
        window.after(100, window.lift)

        # then focus on it
        window.focus_set()

    @staticmethod
    def _bring_window_inside_screen(window):
        """
        This checks if the window is over the top of the screen and moves it down if it is.
        :param window: The window to check.
        """

        # get the window x and y position
        window_x = window.winfo_x()
        window_y = window.winfo_y()

        move = False

        # if the window's top position is over the top of the screen
        if window.winfo_y() <= 0:
            # set the window's top position to 10
            window_y = 10

            move = True

        # if the window's left position is over the left of the screen
        if window.winfo_x() <= 0:
            # set the window's left position to 10
            window_x = 10

            move = True

        # position the window
        if move:
            window.geometry('+{}+{}'.format(window_x, window_y))

    def create_or_open_window(self, parent_element: tk.Toplevel or tk = None, window_id: str = None,
                              title: str = None, resizable: tuple or bool = False,
                              type: str = None,
                              close_action=None,
                              open_multiple: bool = False, return_window: bool = False, has_menubar: bool = False) \
            -> tk.Toplevel or str or bool:
        """
        This function creates a new window or opens an existing one based on the window_id.
        :param parent_element:
        :param window_id:
        :param title:
        :param resizable:
        :param close_action: The function to call when the window is being closed
        :param open_multiple: Allows to open multiple windows of the same type
                             (but adds the timestamp to the window_id for differentiations)
        :param return_window: If false, it just returns the window_id. If true, it returns the window object.
        :param has_menubar: If true, the window will have a menubar
        :return: The window_id, the window object if return_window is True, or False if the window already exists
        """

        # if the window is already opened somewhere, do this
        # (but only if open_multiple is False)
        # if this function throws an error make sure that, if the window was previously opened and closed,
        # it the window_id reference was removed from the self.windows dictionary in the destroy/close function!
        if window_id in self.windows and not open_multiple:

            # bring the window to the top
            # self.windows[window_id].attributes('-topmost', 1)
            # self.windows[window_id].attributes('-topmost', 0)
            window = self.get_window_by_id(window_id)
            window.lift()

            # then focus on it after 50ms
            window.after(50, window.focus_set)

            # but return false since we're not creating it
            return False

        else:

            # if the window exists, but we want to have multiple instances of it
            # use the current time as a unique suffix to the window_id
            if window_id in self.windows and open_multiple:
                window_id = window_id + "_" + str(time.time())

            # create a new window
            if parent_element is None:
                parent_element = self.root

            # add the window to the toolkit UI windows dictionary
            self.windows[window_id] = ctk.CTkToplevel(parent_element)

            # set bar icon for windows
            self.UI_set_icon(self.windows[window_id])

            # open the window on the same screen as the parent_element
            if isinstance(parent_element, ctk.CTkToplevel) or isinstance(parent_element, tk.Tk):

                # if the parent is root, position the window under it + 20 px
                if parent_element == self.root:

                    # get the parent element's height
                    parent_height = parent_element.winfo_height()

                    self.windows[window_id].geometry("+{}+{}".format(
                        parent_element.winfo_x() + 20, parent_element.winfo_y() + parent_height + 20))

                    def push_higher_if_too_low():
                        """
                        This makes sure that after the window is created, it is not too low on the screen.
                        """

                        # get the window's height
                        window_height = self.windows[window_id].winfo_height()

                        # get the screen height
                        screen_height = self.windows[window_id].winfo_screenheight()

                        # get the window's y position
                        window_y = self.windows[window_id].winfo_y()

                        # if the window is too low, push it up so that it fits the screen,
                        # just don't push it higher than the top of the screen
                        if window_y + window_height > screen_height:
                            # push the window up by the difference
                            self.windows[window_id].geometry("+{}+{}".format(
                                self.windows[window_id].winfo_x(),
                                window_y - (window_y + window_height - screen_height) if window_y > 20 else 20
                            ))

                        # but also bring it back down if it's too high
                        self._bring_window_inside_screen(self.windows[window_id])

                    # after the window is created, push it up if it's too low
                    self.windows[window_id].after(200, push_higher_if_too_low)

                else:
                    self.windows[window_id].geometry("+{}+{}".format(parent_element.winfo_x() + 20,
                                                                     parent_element.winfo_y() + 20))

            # Make Toplevel appear in Ctrl/Cmd+Tab list
            self.windows[window_id].attributes('-topmost', 'true')
            self.windows[window_id].after_idle(self.windows[window_id].attributes, '-topmost', 'false')

            # keep track of the window type
            if type is not None:
                self.set_window_type(window_id=window_id, type=type)

            # bring the transcription window to top
            # self.windows[window_id].attributes('-topmost', 'true')

            # set the window title
            self.windows[window_id].title(title)

            # is it resizable?
            if not resizable:
                self.windows[window_id].resizable(False, False)

            elif isinstance(resizable, tuple) and len(resizable) == 2:
                self.windows[window_id].resizable(resizable[0], resizable[1])

            # use the default destroy_window function in case something else wasn't passed
            if close_action is None:
                close_action = lambda: self.destroy_window_(window_id=window_id, windows_dict=self.windows)

            # then add the close action to the window, so that we can call it from anywhere else
            self.windows[window_id].close_action = close_action

            # add the window id to the window object in case it needs to reference itself
            self.windows[window_id].window_id = window_id

            # add a top menu bar if the OS is not macOS - for macOS the top menu bar is enough
            if has_menubar and sys.platform != "darwin":
                self.windows[window_id].menu_bar = UImenus(toolkit_UI_obj=self, parent=self.windows[window_id])
                self.windows[window_id].menu_bar.load_menubar()

            # also bind the close action to cmd+shift+w
            self.windows[window_id].bind("<" + self.ctrl_cmd_bind + "-Shift-W>", lambda event: close_action())

            # what happens when the user closes this window
            self.windows[window_id].protocol("WM_DELETE_WINDOW", close_action)

            # what happens when the user focuses on this window
            self.windows[window_id].bind("<FocusIn>", lambda event: self._focused_window(window_id))

            # focus on the window after 100ms
            self.windows[window_id].after(100, lambda l_window_id=window_id: self.focus_window(window_id=l_window_id))

            # add window_id to the window object
            self.windows[window_id].window_id = window_id

            # return the window_id or the window object
            if return_window:
                return self.windows[window_id]
            else:
                return window_id

    def destroy_window_(self, window_id, windows_dict=None):
        """
        This makes sure that the window reference is deleted when a user closes a window
        :param windows_dict: The dictionary that holds the window references
        :param window_id:
        :return:
        """

        # if no parent element is specified, use the windows dict
        if windows_dict is None:
            windows_dict = self.windows

        if window_id not in windows_dict:
            logger.debug('Unable to close window: ' + window_id + ' because it does not exist in the windows dict.')
            return None

        # also remove any observers that are registered for this window
        self.remove_observer_from_window(window_id=window_id)

        # remove the window from the window_types dictionary
        if window_id in self.window_types:
            del self.window_types[window_id]

        # destroy the window once the mainloop is idle
        windows_dict[window_id].after_idle(windows_dict[window_id].destroy)

        logger.debug('Closing window: ' + window_id)

        # then remove its reference
        del windows_dict[window_id]

    def add_observer_to_window(self, window_id, action, callback, dettach_after_call=False):
        """
        This adds an observer to a window, so that the callback can be called
        when the action is triggered from toolkit_ops_obj
        :param window_id: The window id
        :param action: The action to be observed
        :param callback: The callback function to be called when the Observer is notified
        :param dettach_after_call: If True, the observer will be dettached after the callback is called
        """

        # if the window_id is not in the windows_observers dictionary, add it
        if window_id not in self.windows_observers:
            self.windows_observers[window_id] = {}

        # if the action is already in the windows_observers dictionary, return
        if action in self.windows_observers[window_id]:
            return False

        # add an Observer to the transcription window
        window_observer = Observer()

        # wrap the call with after() so that all notifications are executed sequentially and not in parallel
        # this is important,
        # otherwise widgets might be destroyed by some threads while other threads are trying to access them
        # triggering a _tkinter.TclError: invalid command name exception
        def callback_after(*args, **kwargs):

            # get the window
            window = self.get_window_by_id(window_id=window_id)

            window.after(1, callback, *args, **kwargs)

        # if the dettach_after_call is True, execute the callback and then dettach the observer
        if dettach_after_call:

            # create a new callback which contains the callback and the dettach function
            def callback_with_dettach(*args, **kwargs):

                # call the callback through after()
                callback_after(*args, **kwargs)

                # dettach the observer
                self.toolkit_ops_obj.dettach_observer(action=action, observer=window_observer)

            # set the new callback
            window_observer.update = callback_with_dettach

        else:
            window_observer.update = callback_after

        # attach the observer to the action
        self.toolkit_ops_obj.attach_observer(action=action, observer=window_observer)

        # add the observer to the windows_observers dictionary
        self.windows_observers[window_id][action] = window_observer

        return window_observer

    def remove_observer_from_window(self, window_id, action=None):

        # first, dettach the observer from the toolkit_ops_obj
        # but if no action was specified, remove all actions (check them in the windows_observers dictionary)
        if action is None:

            # if the action is not in the windows_observers dictionary, return
            if window_id not in self.windows_observers:
                return

            # remove all actions related to this window
            for removable_action in self.windows_observers[window_id]:
                self.toolkit_ops_obj.dettach_observer(action=removable_action,
                                                      observer=self.windows_observers[window_id][removable_action])

        # if we do have an action, remove only that action
        else:
            self.toolkit_ops_obj.dettach_observer(action=action, observer=self.windows_observers[window_id][action])

        # if the window_id is in the windows_observers dictionary
        if window_id in self.windows_observers:

            # if an action was specified, only remove that action
            if action is not None and action in self.windows_observers[window_id]:
                del self.windows_observers[window_id][action]

            # otherwise, remove the entire window from the dictionary
            else:
                del self.windows_observers[window_id]

        return

    def get_window_type(self, window_id: str) -> str or None:
        """
        This function returns the type of a window based on the window_id
        :param window_id:
        :return:
        """

        if window_id in self.window_types:
            return self.window_types[window_id]
        elif window_id == 'main':
            return 'main'
        else:
            logger.debug('Window type not found for window_id: {}'.format(window_id))
            return None

    def set_window_type(self, window_id: str, type: str) -> None:
        """
        This function sets the type of a window based on the window_id
        """

        self.window_types[window_id] = type

    def get_all_windows_of_type(self, window_type: str) -> list:
        """
        This function returns all the windows of a certain type
        """

        return [window_id for window_id in self.window_types if self.window_types[window_id] == window_type]

    def _focused_window(self, window_id):
        """
        This function is called when a window is focused
        If the window has changed, we also trigger the on_window_focus_change function
        :param window_id:
        :return:
        """

        # if the previous focus trigger was on the same window, ignore
        if self.current_focused_window == window_id:
            return

        # change the last focused window variable
        self.last_focused_window = self.current_focused_window

        # change the focused window variable
        self.current_focused_window = window_id

        # logger.debug("Window focused: " + window_id)

    def _add_side_subframe_to_window(self, parent_frame, sub_frame: str):
        """
        This adds a sub-frame to the left or right frame of a window.

        :param window_id: the id of the text window
        :param side: the side of the window where the button should be added (left or right)
        :param sub_frame: the name of the sub-frame where the button should be added
        """

        # we call this "button_parent_frame" because we will mostly buttons, switches etc.
        new_frame = parent_frame

        # if the sub-frame doesn't exist as an attribute of the frame
        if sub_frame is not None and not hasattr(parent_frame, 'frame_{}'.format(sub_frame.strip().lower())):

            # create a new sub-frame
            new_frame = ctk.CTkFrame(parent_frame)

            # add a label to it
            ctk.CTkLabel(new_frame, text=sub_frame, anchor='n') \
                .pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            # add the new sub_frame to the parent frame
            new_frame.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            # add the new sub_frame as an attribute of the parent frame
            # so we can access it later
            setattr(parent_frame, 'frame_{}'.format(sub_frame.strip().lower()), new_frame)

        # if the sub_frame already exists, just use it for the return value
        elif sub_frame is not None and hasattr(parent_frame, 'frame_{}'.format(sub_frame.strip().lower())):

            new_frame = getattr(parent_frame, 'frame_{}'.format(sub_frame.strip().lower()))

        return new_frame

    def _add_button_to_side_frames_of_window(self, window_id: str, side: str,
                                             button_text: str, button_command: callable,
                                             sub_frame: str = None):
        """
        This adds a button to the left or right frame of a window. It also creates a sub-frame for it if needed.
        :param window_id: the id of the text window
        :param side: the side of the window where the button should be added (left or right)
        :param button_text: the text of the button
        :param button_command: the command of the button
        :param sub_frame: the name of the sub-frame where the button should be added
        :return: True if the button was added successfully, False otherwise
        """

        # we can pass the side as a string (either 'left' or 'right')
        if side == 'left':
            frame = self.windows[window_id].left_frame
            frame_column = 0

        elif side == 'right':
            frame = self.windows[window_id].right_frame
            frame_column = 2
        else:
            logger.error('Invalid side {} for window {}.'.format(side, window_id))
            return False

        # this will be the frame we use to add the button
        button_parent_frame = self._add_side_subframe_to_window(frame, sub_frame)

        # finally, add the button
        # but only if another button with the same text doesn't already exist
        if hasattr(button_parent_frame, 'button_{}'.format(button_text.strip().lower())):
            return False

        # add the button
        new_button = ctk.CTkButton(button_parent_frame, text=button_text, command=button_command,
                                   **self.ctk_side_frame_button_size
                                   )
        new_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

        # add the new button as an attribute of the sub-frame
        setattr(button_parent_frame, 'button_{}'.format(button_text.strip().lower()), new_button)

        # is the frame in the grid?
        if not frame.grid_info():
            # if not, add it so that it's visible
            frame.grid(row=0, column=frame_column, sticky="ns")

        return True

    def _add_switch_to_side_frames_of_window(self, window_id: str, side: str,
                                             switch_command: callable = None,
                                             switch_text: str = '',
                                             sub_frame: str = None,
                                             label_text=None):
        """
        This adds a switch to the left or right frame of a window. It also creates a sub-frame for it if needed.
        :param window_id: the id of the text window
        :param side: the side of the window where the button should be added (left or right)
        :param switch_text: the text of the button
        :param switch_command: the command of the button
        :param sub_frame: the name of the sub-frame where the button should be added
        :return: True if the button was added successfully, False otherwise
        """

        # we can pass the side as a string (either 'left' or 'right')
        if side == 'left':
            frame = self.windows[window_id].left_frame
            frame_column = 0

        elif side == 'right':
            frame = self.windows[window_id].right_frame
            frame_column = 2
        else:
            logger.error('Invalid side {} for window {}.'.format(side, window_id))
            return False

        # this will be the frame we use to add the switch
        switch_parent_frame = self._add_side_subframe_to_window(frame, sub_frame)

        # finally, add the switch
        # but only if another switch with the same text doesn't already exist
        if hasattr(switch_parent_frame, 'switch_{}'.format(
                label_text.strip().lower() if label_text is not None else switch_text.strip().lower()
        )):
            return False

        # add a frame to hold a switch and a label
        switch_frame = ctk.CTkFrame(
            switch_parent_frame, **self.ctk_side_frame_button_size)

        # add a label to it
        if label_text is not None:
            new_label = ctk.CTkLabel(switch_frame, text=label_text, **self.ctk_side_label_settings)
            new_label.grid(row=0, column=0, sticky='w', **self.ctk_side_label_paddings)

        # add a bool variable to hold the switch state
        switch_state_var = tk.BooleanVar()

        # add the button
        new_switch = ctk.CTkSwitch(switch_frame,
                                   text=switch_text,
                                   command=switch_command,
                                   variable=switch_state_var,
                                   **self.ctk_side_switch_settings
                                   )
        new_switch.grid(row=0, column=1, sticky='e')

        # the switch frame should fill the parent frame
        switch_frame.columnconfigure(0, weight=1)

        switch_frame.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='w')

        # add the new switch as an attribute of the sub-frame
        setattr(switch_parent_frame, 'switch_{}'.format(switch_text.strip().lower()), new_switch)

        # is the frame in the grid?
        if not frame.grid_info():
            # if not, add it so that it's visible
            frame.grid(row=0, column=frame_column, sticky="ns")

        return switch_state_var, switch_frame

    def reset_status_label_after(self, window_id, seconds=5):
        """
        This checks the last time the status label was updated via window.status_label_last_update
        and sets it to '' if it was more than X seconds ago.
        """

        if (window := self.get_window_by_id(window_id)) is None:
            logger.warning('Cannot reset status label for window with id {} - window not found.'.format(window_id))
            return False

        # set the last update time to 0 if it doesn't exist
        if not hasattr(window, 'status_last_update'):
            setattr(window, 'status_last_update', 0)

        if time.time() - window.status_last_update > seconds:
            self.update_window_status_label(window_id=window_id, text='')
            return True

        return None

    def get_window_status_label_text(self, window_id):

        if (window := self.get_window_by_id(window_id)) is None:
            logger.warning('Cannot update status label for window with id {} - window not found.'.format(window_id))
            return False

        if hasattr(window, 'status_label'):
            return window.status_label.cget('text')

        return None

    def update_window_status_label(self, window_id, text='', color=None):

        if (window := self.get_window_by_id(window_id)) is None:
            logger.warning('Cannot update status label for window with id {} - window not found.'.format(window_id))
            return False

        if hasattr(window, 'status_label'):

            color = self.theme_colors['normal'] \
                if color is None else self.theme_colors[color]

            # if the text in the status label is the same as the text we want to set it to
            # add a dot to the end of the text (but only up to 50 dots)
            if text != '' and window.status_label.cget('text').split('.')[0].lower() == text.split('.')[0].lower():
                # get the length of the text from the first dot to the end
                dots = len(window.status_label.cget('text')) - len(window.status_label.cget('text').split('.')[0])

                # add a dot to the end of the text if there are less than 50 dots
                text = window.status_label.cget('text') + '.' if dots < 50 else text

            window.status_label.configure(text=text, text_color=color)

            # reset the last update time if the text is not empty
            if text != '':
                window.status_last_update = time.time()

            return True

        logger.error \
            ('Cannot update status label for window with id {} - label attribute not found.'.format(window_id))
        return False

    # MAIN WINDOW

    def hide_main_window_frame(self, frame_name):
        """
        Used to hide main window frames, but only if they're not invisible already
        :param frame_name:
        :return:
        """

        # only attempt to remove the frame from the main window if it's known to be visible
        if frame_name in self.windows['main'].main_window_visible_frames:
            # first remove it from the view
            self.windows['main'].__dict__[frame_name].pack_forget()

            # then remove if from the visible frames list
            if frame_name in self.windows['main'].main_window_visible_frames:
                self.windows['main'].main_window_visible_frames.remove(frame_name)

            return True

        return False

    def show_main_window_frame(self, frame_name):
        """
        Used to show main window frames, but only if they're not visible already
        :param frame_name:
        :return:
        """

        # only attempt to show the frame from the main window if it's known not to be visible
        if frame_name not in self.windows['main'].main_window_visible_frames:
            # first show it
            self.windows['main'].__dict__[frame_name].pack(expand=True, fill=tk.X)

            # then add it to the visible frames list
            self.windows['main'].main_window_visible_frames.append(frame_name)

            return True

        return False

    def update_main_window(self):
        """
        Updates the main window GUI
        :return:
        """

        main_window = self.windows['main']

        #  show the tool buttons if they're not visible already
        self.show_main_window_frame('tool_buttons_frame')

        # if resolve isn't connected or if there's a communication error
        if not NLE.is_connected():
            # hide resolve related buttons
            self.hide_main_window_frame('resolve_buttons_frame')

        # if resolve is connected and the resolve buttons are not visible
        else:
            self.show_main_window_frame('resolve_buttons_frame')

        return

    def create_main_window(self):
        """
        Creates the main GUI window using Tkinter
        :return:
        """

        # set the main window title
        self.root.title("StoryToolkitAI v{}".format(self.stAI.__version__))

        # temporary width and height for the main window
        self.root.config(width=1, height=1)

        # the reference to the main window
        main_window = self.windows['main'] = self.root

        # any frames stored here in the future will be considered visible
        main_window.main_window_visible_frames = []

        # retrieve toolkit_ops object
        toolkit_ops_obj = self.toolkit_ops_obj

        # create the frame that will hold the tool buttons
        main_window.tool_buttons_frame = ctk.CTkFrame(self.root, **self.ctk_frame_transparent)

        # create the frame that will hold the resolve buttons
        main_window.resolve_buttons_frame = ctk.CTkFrame(self.root, **self.ctk_frame_transparent)

        # add footer frame
        main_window.footer_frame = ctk.CTkFrame(self.root, **self.ctk_frame_transparent)

        # draw buttons

        # resolve buttons frame
        main_window.r_transcribe = ctk.CTkButton(main_window.resolve_buttons_frame,
                                                 **self.ctk_button_size, text="Transcribe Timeline",
                                                 command=lambda: self.button_nle_transcribe_timeline())

        main_window.r_copy_markers_clip = ctk.CTkButton(main_window.resolve_buttons_frame,
                                                        **self.ctk_button_size,
                                                        text="Timeline Markers to Same Clip",
                                                        command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                                                            'copy_markers_timeline_to_clip', self))

        main_window.r_copy_markers_timeline = ctk.CTkButton(main_window.resolve_buttons_frame,
                                                            **self.ctk_button_size,
                                                            text="Clip Markers to Same Timeline",
                                                            command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                                                                'copy_markers_clip_to_timeline', self))

        # resolve buttons frame row 2
        main_window.r_render_marker_stils = ctk.CTkButton(main_window.resolve_buttons_frame,
                                                          **self.ctk_button_size, text="Render Markers to Stills",
                                                          command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                                                              'render_markers_to_stills', self))

        main_window.r_render_marker_clips = ctk.CTkButton(main_window.resolve_buttons_frame,
                                                          **self.ctk_button_size, text="Render Markers to Clips",
                                                          command=lambda: self.toolkit_ops_obj.execute_resolve_operation(
                                                              'render_markers_to_clips', self))

        # TOOL BUTTONS

        main_window.t_ingest = ctk.CTkButton(main_window.tool_buttons_frame,
                                             **self.ctk_button_size,
                                             text="Ingest", command=self.button_ingest)

        # add the shift+click binding to the button
        main_window.t_ingest.bind('<Shift-Button-1>',
                                  lambda event: self.button_ingest(select_dir=True))

        main_window.t_open_transcript = ctk.CTkButton(main_window.tool_buttons_frame,
                                                      **self.ctk_button_size,
                                                      text="Open Transcription", command=lambda: self.open_transcript())

        # THE STORY BUTTON
        main_window.open_story = ctk.CTkButton(main_window.tool_buttons_frame,
                                               **self.ctk_button_size,
                                                  text="Open Story",
                                                    command=lambda: self.open_story_editor_window())

        main_window.t_queue = ctk.CTkButton(main_window.tool_buttons_frame,
                                            **self.ctk_button_size,
                                            text="Queue",
                                            command=lambda: self.open_queue_window())

        # THE ADVANCED SEARCH BUTTON
        main_window.t_adv_search = ctk.CTkButton(main_window.tool_buttons_frame,
                                                 **self.ctk_button_size,
                                                 text="Search",
                                                 command=lambda: self.open_advanced_search_window())
        # add the shift+click binding to the button
        main_window.t_adv_search.bind('<Shift-Button-1>',
                                      lambda event: self.open_advanced_search_window(select_dir=True))

        # THE ASSISTANT BUTTON
        main_window.open_assistant = ctk.CTkButton(main_window.tool_buttons_frame,
                                                   **self.ctk_button_size,
                                                   text="Assistant",
                                                   command=lambda: self.open_assistant_window())

        # add the resolve buttons to the window
        # but first a label
        # ctk.CTkLabel(main_window.resolve_buttons_frame, text="Resolve", **self.ctk_main_window_label_settings)\
        #    .grid(row=1, column=0, sticky='ew')

        main_window.r_transcribe.grid(row=1, column=1, **self.ctk_main_paddings)
        main_window.r_copy_markers_clip.grid(row=1, column=2, **self.ctk_main_paddings)
        main_window.r_copy_markers_timeline.grid(row=1, column=3, **self.ctk_main_paddings)
        main_window.r_render_marker_stils.grid(row=1, column=4, **self.ctk_main_paddings)
        main_window.r_render_marker_clips.grid(row=1, column=5, **self.ctk_main_paddings)

        # make column 1 the size of the window
        # main_window.resolve_buttons_frame.grid_columnconfigure(1, weight=1)

        # add the app buttons to the window
        # but first the tool label
        # ctk.CTkLabel(main_window.tool_buttons_frame, text="Tool", **self.ctk_main_window_label_settings)\
        #    .grid(row=1, column=0, sticky='ew')

        main_window.t_ingest.grid(row=1, column=1, **self.ctk_main_paddings)
        main_window.t_open_transcript.grid(row=1, column=2, **self.ctk_main_paddings)
        main_window.open_story.grid(row=1, column=3, **self.ctk_main_paddings)
        main_window.t_queue.grid(row=1, column=4, **self.ctk_main_paddings)
        main_window.t_adv_search.grid(row=1, column=5, **self.ctk_main_paddings)
        main_window.open_assistant.grid(row=1, column=6, **self.ctk_main_paddings)

        # make column 1 the size of the window
        # main_window.tool_buttons_frame.grid_columnconfigure(1, weight=1)

        # Make the window resizable false
        self.root.resizable(False, False)

        # update the window after it's been created
        self.root.after(500, self.update_main_window())

        logger.info("Starting StoryToolkitAI GUI")

        # when the window is focused or clicked on
        main_window.bind("<FocusIn>", lambda event: self._focused_window('main'))
        main_window.bind("<Button-1>", lambda event: self._focused_window('main'))
        main_window.bind("<Button-2>", lambda event: self._focused_window('main'))
        main_window.bind("<Button-3>", lambda event: self._focused_window('main'))

        # add key bindings to the main window
        # key t for the transcription window
        main_window.bind("t", lambda event: self.button_ingest())

        # load menubar items
        self.main_menu.load_menubar()

        # load Tk mainloop
        self.root.mainloop()

        return

    @staticmethod
    def get_line_char_from_click(event, text_widget=None):

        index = text_widget.index("@%s,%s" % (event.x, event.y))
        line, char = index.split(".")

        return line, char

    # TEXT WINDOWS

    def _text_window_entry(self, window_id, event, **kwargs):
        """
        This function is called when the user presses any key in the text window text field
        :param window_id:
        :return:
        """

        # get the window object and the text widget
        window = self.get_window_by_id(window_id=window_id)
        text_widget = window.text_widget

        # get the current number of lines in the text widget
        lines = text_widget.index('end-1c')

        # on which line is the cursor?
        cursor_pos = text_widget.index('insert')
        
        # do not allow key entries if the text widget is locked
        if hasattr(text_widget, 'locked') and text_widget.locked:
            return 'break'

        # up/down for prompt history
        # the prompt history is saved in self.window_prompts[window_id]
        # when searching through the prompt history, we use self.window_prompts_index[window_id]
        # to keep track which prompt we are on
        if event.keysym in ['Up', 'Down']:

            # first move the cursor to the end of the last line
            text_widget.mark_set('insert', 'end-1c')

            # also scroll to the end of the last line
            text_widget.see('end-1c')

            # if the prompt history is empty, do nothing
            if window_id not in self.window_prompts or len(self.window_prompts[window_id]) == 0:
                return 'break'

            if window_id not in self.window_prompts_index:
                self.window_prompts_index[window_id] = -1

            # if the prompt history is not empty
            else:
                # if the key is up
                if event.keysym == 'Down':
                    # if the prompt history index is not at the end of the list
                    if self.window_prompts_index[window_id] < len(self.window_prompts[window_id]) - 1:
                        # increase the prompt history index
                        self.window_prompts_index[window_id] += 1
                    else:
                        # if the prompt history index is at the end of the list
                        # set the prompt history index to -1
                        # this means that the prompt history index is not on any prompt
                        self.window_prompts_index[window_id] = -1

                # if the key is down
                elif event.keysym == 'Up':
                    # if the prompt history index is not at the beginning of the list
                    if self.window_prompts_index[window_id] == -1:
                        # set the prompt history index to the last index in the list
                        self.window_prompts_index[window_id] = len(self.window_prompts[window_id]) - 1

                    else:
                        # decrease the prompt history index
                        self.window_prompts_index[window_id] -= 1

                # if the prompt history index is -1
                if self.window_prompts_index[window_id] == -1:
                    # set the prompt to an empty string
                    prompt = ''

                # if the prompt history index is not -1
                else:
                    # get the prompt from the prompt history
                    prompt = self.window_prompts[window_id][self.window_prompts_index[window_id]]

                # first, clear the last line
                text_widget.delete('end-1c linestart', 'end-1c lineend')

                # set the prompt in the text widget
                # but also add the prompt prefix if there is one
                text_widget.insert('end-1c', self.text_windows[window_id]['prompt_prefix'] + prompt)

            return 'break'

        # if the cursor is not past the last line, only allow arrow keys
        if int(cursor_pos.split('.')[0]) < int(lines.split('.')[0]):

            # do not allow backspace
            # but move the cursor to the end of the last line
            if event.keysym == 'BackSpace':
                # first move the cursor to the end of the last line
                text_widget.mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                text_widget.see('end-1c')

                return 'break'

            # if the key is an left-right arrow key, return 'normal'
            elif event.keysym in ['Left', 'Right']:
                return 'normal'

            # if the key is not an arrow key, move the cursor to the end of the last line
            else:
                # first move the cursor to the end of the last line
                text_widget.mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                text_widget.see('end-1c')

                # then return normal so that the key is processed as it should be
                return 'normal'

        # if the cursor is on the last line, allow typing (on conditions)
        # this is where the user is supposed to enter prompts
        else:

            # if the cursor is not past the prefix, move it to the end of the prefix
            if int(cursor_pos.split('.')[1]) < len(self.text_windows[window_id]['prompt_prefix']):
                # first move the cursor to the end of the last line
                text_widget.mark_set('insert', 'end-1c')

                # also scroll to the end of the last line
                text_widget.see('end-1c')

                return 'break'

            # if the key is Return, get the text and call the command
            if event.keysym == 'Return':

                # get the command entered by the user
                prompt = text_widget.get('end-1c linestart', 'end-1c lineend')

                # keep track of the last line of the text_widget where the user entered the prompt
                # use the text_widget functions
                text_widget.last_prompt_line = text_widget.index('end-1c linestart').split('.')[0]

                # remove the command prefix from the beginning of the command if it was given
                if kwargs.get('prompt_prefix', ''):
                    prompt = prompt.replace(kwargs.get('prompt_prefix', ''), '', 1)

                # add two new lines
                text_widget.insert('end', '\n\n')

                # also pass the prompt prefix if it was given
                self._text_window_prompts(prompt=prompt, window_id=window_id, **kwargs)

                # scroll to the end of the last line
                # but only if the window still exists
                # - this is disabled since it should be handled within _text_window_prompts() (i.e. by each command)
                # if window_id in self.text_windows:
                #    text_widget.see('end-1c')

                return 'break'

            # do not allow backspace past the first character + length of the prompt prefix of the last line
            elif event.keysym == 'BackSpace':

                last_line = (text_widget.index('end-1c linestart')).split('.')[0]

                # get the length of prompt_prefix
                prompt_prefix_length = len(kwargs.get('prompt_prefix', ''))

                if text_widget.index('insert') \
                        == str(last_line) + '.' + str(prompt_prefix_length):

                    return 'break'

            # if there is a selection
            if text_widget.tag_ranges('sel'):

                # get the last line of the text widget
                last_line = (text_widget.index('end-1c linestart')).split('.')[0]

                # get the length of prompt_prefix
                prompt_prefix_length = len(kwargs.get('prompt_prefix', ''))

                # get the end of the selection
                selection_end = text_widget.index('sel.last')

                # reset the selection to the beginning of the prompt prefix - last line, prompt prefix length
                text_widget.tag_remove('sel', 'sel.first', 'sel.last')
                text_widget.tag_add(
                   'sel', str(last_line) + '.' + str(prompt_prefix_length), selection_end)

                # only then return
                return

        return

    def _text_window_prompts(self, prompt, window_id=None, **kwargs):
        """
        This function calls prompts from the text window.
        :return:
        """

        response = None

        # first, add the prompt to the prompt history
        if window_id not in self.window_prompts:
            self.window_prompts[window_id] = [prompt]
        else:
            self.window_prompts[window_id].append(prompt)

        # reset the prompt history index
        self.window_prompts_index[window_id] = -1

        if kwargs.get('prompt_callback', ''):
            response = kwargs.get('prompt_callback', '')(prompt, **kwargs.get('prompt_callback_kwargs', {}))

        # if no command execution function is given, resort to the default commands
        else:

            if prompt == 'exit' or prompt == 'quit' or prompt == 'close':
                self.destroy_text_window(window_id=window_id)

            else:
                response = 'Ignoring "{}". Command unknown.'.format(prompt)
                logger.debug(response)

        # output the reply to the text window, if a window_id is given
        if window_id and response:
            self._text_window_update(window_id=window_id, text=response, prompt_prefix=kwargs.get('prompt_prefix', ''))

    def _text_window_update(self, window_id, text, **kwargs):
        """
        This function updates the text in the text window, but keeps the command line at the bottom if it exists
        :param window_id:
        :param text:
        :param args:
        :return:
        """

        # update some stuff if they were passed
        if kwargs.get('prompt_prefix', None):
            self.text_windows[window_id]['text_widget'].prompt_prefix = kwargs.get('prompt_prefix')
            self.text_windows[window_id]['prompt_prefix'] = kwargs.get('prompt_prefix')

        if kwargs.get('prompt_callback', None):
            self.text_windows[window_id]['text_widget'].prompt_callback = kwargs.get('prompt_callback')

        if kwargs.get('prompt_callback_kwargs', None):
            self.text_windows[window_id]['text_widget'].prompt_callback_kwargs = kwargs.get('prompt_callback_kwargs')

        prompt_prefix = self.text_windows[window_id]['prompt_prefix'] \
            if 'prompt_prefix' in self.text_windows[window_id] else None

        user_prompt = self.text_windows[window_id]['user_prompt'] \
            if 'user_prompt' in self.text_windows[window_id] else None

        # if clear is given, clear the text window by deleting all text
        if kwargs.get('clear', False):
            self.text_windows[window_id]['text_widget'].delete('1.0', 'end')

        # if user input is enabled and user_input prefix exists, move the cursor to the beginning of the last line
        linestart = ''
        if user_prompt and prompt_prefix:
            self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c linestart')

            # also use the linestart variable for the color change below
            linestart = ' linestart'

        # first get the current insert position
        insert_pos = self.text_windows[window_id]['text_widget'].index('insert')

        if text != '':
            self.text_windows[window_id]['text_widget'].insert('insert', text + '\n\n')

        # now change the color of the last entry to supernormal (almost white)
        self.text_windows[window_id]['text_widget'].tag_add('reply', insert_pos, 'end-1c' + linestart)
        self.text_windows[window_id]['text_widget'].tag_config('reply', foreground=self.theme_colors['supernormal'])

        # if user input is enabled and a prefix is given, make sure we have it at the beginning of the last line
        if user_prompt and prompt_prefix:

            # only add it if it is not already there
            if not self.text_windows[window_id]['text_widget'].get('end-1c linestart', 'end-1c lineend') \
                    .startswith(prompt_prefix):
                self.text_windows[window_id]['text_widget'].insert('end-1c linestart', prompt_prefix)

        # and move the insert position right at the end
        self.text_windows[window_id]['text_widget'].mark_set('insert', 'end-1c')

        # also scroll to the end of the last line (or to whatever scroll_to was sent)
        self.text_windows[window_id]['text_widget'].see(kwargs.get('scroll_to', 'end-1c'))

    def _text_window_set_prefix(self, window_id, prefix):
        """
        This changes the prefix of the prompt in the text window
        """

        # if the window_id does not exist, create it (this should never be the case...)
        if window_id not in self.text_windows:
            self.text_windows[window_id] = dict()

        self.text_windows[window_id]['prompt_prefix'] = prefix

    def _text_window_context_menu(self, event=None, window_id: str=None, **attributes):
        """
        This function creates a context menu for the text widget in the text window
        """

        # get the window object
        window = self.get_window_by_id(window_id=window_id)

        # get the text widget from the event
        text_widget = event.widget

        index = text_widget.index(f"@{event.x},{event.y}")
        tags = text_widget.tag_names(index)

        # if the item at the click position has the tag 'has_context_menu', do nothing
        # assuming that the context menu for it is defined some place else
        if 'has_context_menu' in tags:
            return

        # get the line and char from the click
        line, char = self.get_line_char_from_click(event, text_widget=text_widget)
        line = int(line)
        char = int(char)

        # spawn the context menu
        context_menu = tk.Menu(text_widget, tearoff=0)

        # add the menu items
        # if there is a selection
        if text_widget.tag_ranges("sel"):
            context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))

            # add the de-select all option
            context_menu.add_command(label="Deselect", command=lambda: text_widget.tag_remove("sel", "1.0", "end"))

        else:
            # add the select all option
            context_menu.add_command(label="Select All", command=lambda: text_widget.tag_add("sel", "1.0", "end"))

            # add a separator
            # context_menu.add_separator()

        # display the context menu
        context_menu.tk_popup(event.x_root, event.y_root)

    def _text_window_keypress(self, event=None, window_id: str=None, **attributes):

        window = self.get_window_by_id(window_id=window_id)

        if window is None:
            return

        if event.keysym == 'c' and attributes.get('special_key', None) == 'cmd':

            if hasattr(window, 'text_widget') and window.text_widget.tag_ranges("sel"):
                window.text_widget.event_generate("<<Copy>>")

            return 'break'

    def open_text_window(self, window_id=None, title: str = 'Console', initial_text: str = None,
                         can_find: bool = False, user_prompt: bool = False, prompt_prefix: str = None,
                         prompt_callback: callable = None, prompt_callback_kwargs: dict = None,
                         action_buttons: list = None, type: str = None, **kwargs):
        """
        This window is to display any kind of text in a scrollable window.
        But is also capable of receiving commands from the user (optional)

        This can be used for displaying the license info, or the readme, reading text files,
        welcome messages, the actual stdout etc.

        It will also contain a text input field for the user to enter prompts (optional)
        Plus, the option to have a child find window (optional)

        :param window_id: The id of the window. If not given, it will be generated from the title
        :param title: The title of the window
        :param initial_text: The initial text to display in the window
        :param can_find: If True, a find window will be available on CTRL+F
        :param user_prompt: If True, the user will be able to enter prompts in the window
        :param prompt_prefix: What appears before the user prompt, so the user knows it is a prompt
        :param prompt_callback: A function to call when the user enters a prompt
        :param prompt_callback_kwargs: A dict of kwargs to pass to the prompt_callback function. We will always pass the
                                        window_id, the prompt_prefix and the prompt as kwargs
        :param action_buttons: A list of action buttons to add to the window. Each button is a dict with the following
                                keys: text, command
        :param type: The type of text window (text, search etc.)
        :return:
        """

        # if no window id is given, use the title without spaces plus the time hash
        if not window_id:
            window_id = title.replace(' ', '_').replace('.', '') + str(time.time()).replace('.', '')

        close_action = kwargs.get('close_action', lambda l_window_id=window_id: self.destroy_text_window(l_window_id))

        # open the text window
        if window_id := self.create_or_open_window(
                parent_element=self.root, window_id=window_id, title=title, resizable=True,
                type=type if type else 'text',
                close_action=close_action,
                open_multiple=kwargs.get('open_multiple', True),
                has_menubar=kwargs.get('has_menubar', False),
        ):

            # create an entry in the text_windows dict
            self.text_windows[window_id] = {'text': initial_text}

            # add the user prompt prefix to the text windows dict if it was given
            if user_prompt:
                self.text_windows[window_id]['user_prompt'] = user_prompt
                self.text_windows[window_id]['prompt_prefix'] = prompt_prefix

            # add the CTRL+F behavior to the text window
            if can_find:
                # if the user presses CTRL/CMD+F, open the find window
                self.windows[window_id].bind('<' + self.ctrl_cmd_bind + '-f>',
                                             lambda event:
                                             self.open_find_replace_window(
                                                 parent_window_id=window_id,
                                                 title="Find in {}".format(title)
                                             )
                                             )

                # let's add the .find attribute to the window, so that the UI_menu can use it
                self.windows[window_id].find = lambda: self.open_find_replace_window(
                    parent_window_id=window_id,
                    title="Find in {}".format(title)
                )

            # THE THREE WINDOW COLUMN FRAMES
            current_tk_window = self.windows[window_id]

            # create the left frame
            # (but don't add it - this needs to be added outside of this function, only if needed)
            self.windows[window_id].left_frame = \
                left_frame = ctk.CTkFrame(current_tk_window)

            # create a frame for the text element
            text_form_frame = ctk.CTkFrame(current_tk_window)
            text_form_frame.grid(row=0, column=1, sticky="nsew")

            # create the right frame to hold other stuff
            # (but don't add it - this needs to be added outside of this function, only if needed)
            self.windows[window_id].right_frame = \
                right_frame = ctk.CTkFrame(current_tk_window)

            # add a minimum size for the frame2 column
            current_tk_window.grid_columnconfigure(1, weight=1, minsize=200)

            # make sure the grid also extends to the bottom of the window
            current_tk_window.grid_rowconfigure(0, weight=1)

            # THE MAIN TEXT ELEMENT

            # create the text widget
            # set up the text element where we'll add the actual transcript
            self.windows[window_id].text_widget = \
                text = tk.Text(text_form_frame,
                               font=self.console_font,
                               width=kwargs.get('window_width', 45),
                               height=kwargs.get('window_height', 30),
                               wrap=tk.WORD,
                               **self.ctk_full_textbox_paddings,
                               background=self.theme_colors['black'],
                               foreground=self.theme_colors['normal'])

            # make the widget highlight color the same as the background color
            text.configure(highlightbackground=self.theme_colors['black'], highlightcolor=self.theme_colors['normal'])

            # add a scrollbar to the text element
            scrollbar = ctk.CTkScrollbar(text_form_frame)
            scrollbar.configure(command=text.yview)
            scrollbar.pack(side=tk.RIGHT, fill='y', pady=5)

            # configure the text element to use the scrollbar
            text.configure(yscrollcommand=scrollbar.set)

            # add the initial text to the text element
            if initial_text:
                text.insert(ctk.END, initial_text + '\n\n')

            # change the color of text to supernormal (almost white)
            text.tag_add('reply', '1.0', 'end-1c')
            text.tag_config('reply', foreground=self.theme_colors['supernormal'])

            # set the top, in-between and bottom text spacing
            text.configure(spacing1=0, spacing2=0.2, spacing3=5)

            # then show the text element
            text.pack(anchor='w', expand=True, fill='both', **self.ctk_full_textbox_frame_paddings)

            # add right click for context menu
            text.bind(
                '<Button-3>', lambda e: self._text_window_context_menu(
                    e, window_id=window_id))

            # make context menu work on mac trackpad too
            text.bind(
                '<Button-2>', lambda e: self._text_window_context_menu(
                    e, window_id=window_id))

            # if the user can enter text, enable the text field and process any input
            if user_prompt:

                # if a command prefix is given, add it to the text element
                if prompt_prefix:
                    text.insert(ctk.END, prompt_prefix)

                # attach these to the text element so that we can update them later if needed
                text.prompt_prefix = prompt_prefix
                text.prompt_callback = prompt_callback
                text.prompt_callback_kwargs = prompt_callback_kwargs

                # any keypress in the text element will call the _text_window_entry function
                text.bind('<KeyPress>',
                          lambda event:
                          self._text_window_entry(window_id=window_id, event=event,
                                                  prompt_prefix=text.prompt_prefix,
                                                  prompt_callback=text.prompt_callback,
                                                  prompt_callback_kwargs=text.prompt_callback_kwargs,
                                                  **kwargs))

                # bind CMD/CTRL + key presses to text window actions
                text.bind(
                    "<" + self.ctrl_cmd_bind + "-KeyPress>",
                    lambda e: self._text_window_keypress(
                        event=e, window_id=window_id, special_key='cmd')
                )

                # focus on the text element
                text.focus_set()

            # otherwise, disable the text field
            else:
                text.configure(state=tk.DISABLED)

            # if action buttons are given, add them to the window
            if action_buttons:

                # create a frame for the action buttons
                action_buttons_frame = ctk.CTkFrame(self.windows[window_id])
                action_buttons_frame.grid(row=2, columnspan=3, sticky="sew")

                # add the action buttons to the frame
                for button in action_buttons:
                    # create the button
                    action_button = ctk.CTkButton(action_buttons_frame, text=button['text'],
                                                  command=button['command'])

                    # add the button to the frame
                    action_button.pack(side=button['side'] if 'side' in button else ctk.LEFT,
                                       anchor=button['anchor'] if 'anchor' in button else tk.W,
                                       **self.ctk_footer_button_paddings)

            # add the text widget to the text_windows dict
            self.text_windows[window_id]['text_widget'] = text

            # add the window to the text_windows dict
            self.text_windows[window_id]['window'] = self.windows[window_id]

            # UI - place the window on top for a moment so that the user sees that he has to interact
            self.windows[window_id].wm_attributes('-topmost', True)
            self.windows[window_id].wm_attributes('-topmost', False)
            self.windows[window_id].lift()

        return window_id

    def destroy_text_window(self, window_id):
        """
        This function destroys a text window
        :param window_id:
        :return:
        """

        # close any find windows
        if 'find_window_id' in self.text_windows[window_id]:
            find_window_id = self.text_windows[window_id]['find_window_id']

            # call the default destroy window function to destroy the find window
            self.destroy_find_replace_window(window_id=find_window_id)

        # clear the text windows dict
        if window_id in self.text_windows:
            del self.text_windows[window_id]

        # call the default destroy window function
        self.destroy_window_(windows_dict=self.windows, window_id=window_id)

    def text_window_format_md(self, window_id: str, text_widget: tk.Text = None):
        """
        This function will format markdown text in a text window.
        It will add url links and do header formatting
        :param window_id:
        :param text_widget:
        :return:
        """

        # if no text widget is given, get it from the text_windows dict
        if not text_widget:
            text_widget = self.text_windows[window_id]['text_widget']

        # get the text from the text widget
        text = text_widget.get('1.0', ctk.END)

        # change the font to default_font
        text_widget.configure(font=(self.default_font))

        # if the text is empty, return
        if not text:
            return

        # get the initial text widget state
        initial_state = text_widget.cget('state')

        # make widget writeable
        text_widget.configure(state=tk.NORMAL)

        # take each line of text and format it
        lines = text.split('\n')

        # clear the text widget
        text_widget.delete('1.0', ctk.END)

        for line in lines:

            md = False

            # FORMAT HEADERS
            if line.strip().startswith('#'):
                # get the number of # signs
                num_hashes = len(line.split(' ')[0])

                # header type
                header_type = 'h{}'.format(num_hashes)

                # get the header text
                header_text = line.split('# ')[1]

                # get current insert position
                start_index = text_widget.index(ctk.INSERT)

                # replace the line with the header text
                text_widget.insert(ctk.INSERT, header_text)

                # add the header tag
                text_widget.tag_add(header_type, start_index, ctk.INSERT)

                md = True

            # FORMAT URLS
            if re.search(r'\[.*\]\(.*\)', line):

                # get the url and it's url text, the format is [url text](url)
                # but remember that they are always together but they might be between other text
                # also there might be more than one url in the line
                # so we need to find all the urls and their text
                urls = re.findall(r'\[.*\]\(.*\)', line)

                n = 0
                for url_md in urls:
                    # use regex to get the url text
                    url_text = re.findall(r'\[(.*)\]', url_md)[0]
                    url = re.findall(r'\((.*)\)', url_md)[0]

                    # get the text before the url
                    text_before_url = line.split(url_md)[0]

                    # insert the text before the url
                    text_widget.insert(ctk.INSERT, text_before_url)

                    # remove the text before the url from the line
                    line = line.replace(text_before_url, '')

                    # remove the url from the line
                    line = line.replace(url_md, '')

                    # get current insert position for the url_text
                    start_index = text_widget.index(ctk.INSERT)

                    text_widget.insert(ctk.INSERT, url_text)

                    # add the url tags
                    text_widget.tag_add('url-color', start_index, ctk.INSERT)
                    text_widget.tag_add('url-' + str(start_index), start_index, ctk.INSERT)

                    # on click, open the url in the default browser
                    text_widget.tag_bind('url-' + str(start_index), '<Button-1>',
                                         lambda event, l_url=url: webbrowser.open(l_url))

                # finally, insert the rest of the line
                text_widget.insert(ctk.INSERT, line)

                md = True

            if not md:
                text_widget.insert(ctk.INSERT, line)

            # add a new line
            text_widget.insert(ctk.INSERT, '\n')

        # turn the text widget back to its initial state
        text_widget.configure(state=initial_state)

        # set the color of the text to supernormal (almost white)
        # text_widget.configure(text_color=self.theme_colors['supernormal'])

        # set the headers font
        text_widget.tag_config('h1', font=self.default_font_h1,
                               foreground=self.theme_colors['white'])
        text_widget.tag_config('h2', font=self.default_font_h2,
                               foreground=self.theme_colors['white'])
        text_widget.tag_config('h3', font=self.default_font_h3,
                               foreground=self.theme_colors['white'])

        # add a bit of space between the headers and the text
        text_widget.tag_config('h1', spacing1=10)
        text_widget.tag_config('h2', spacing1=10)
        text_widget.tag_config('h3', spacing1=10)

        # change the color of the version number
        text_widget.tag_config('version', foreground=self.theme_colors['white'])

        # change the font of the code blocks into console font
        text_widget.tag_config('code3', font=(self.console_font), foreground=self.theme_colors['normal'])

        # change the color of the url
        text_widget.tag_config('url-color', foreground=self.theme_colors['blue'])

        text_widget.tag_bind('url-color', '<Enter>', lambda event: text_widget.configure(cursor='hand2'))
        text_widget.tag_bind('url-color', '<Leave>', lambda event: text_widget.configure(cursor=''))

    @staticmethod
    def text_table(data, header):
        if not data:
            return ''

        # Determine the maximum width for each column and check if they are numbers
        col_widths = []
        is_number = []
        for i in range(len(data[0])):
            max_width = max(len(str(row[i])) for row in data)
            col_widths.append(max_width)

            # Check if the column contains only integers or floats
            all_numbers = all(isinstance(row[i], (int, float)) for row in data)
            is_number.append(all_numbers)

        # Create the header
        table = header + "\n"
        # table += " " * (sum(col_widths) + len(col_widths) * 3 + 3) + "\n"  # Adjust spacing between columns

        # Add the rows
        for row in data:
            row_str = ''
            for i, item in enumerate(row):
                fmt = f' {{:>{col_widths[i]}}}' if is_number[i] else f'{{:<{col_widths[i]}}} '
                row_str += fmt.format(item) + ''
            table += row_str + "\n"

        # table += " " * (sum(col_widths) + len(col_widths) * 3 + 3) + "\n"  # Adjust spacing between columns
        table += ""

        return table

    def inject_prompt(self, window_id: str, prompt: str, execute=True, clear_line=True):
        """
        This function injects a prompt into the text window and hits Return (if execute is True).
        """

        # get the text widget
        if window_id not in self.windows:
            logger.error('Window {} does not exist.'.format(window_id))
            return False

        if window_id not in self.text_windows or 'text_widget' not in self.text_windows[window_id]:
            logger.error('Window {} does not have a main text widget.'.format(window_id))
            return False

        text_widget = self.text_windows[window_id]['text_widget']

        # erase the current line
        if clear_line:
            text_widget.delete('insert linestart', 'insert lineend')

        # insert the prompt
        text_widget.insert(ctk.END, prompt)

        # move the cursor to the end
        text_widget.see(ctk.END)

        # focus on the text widget
        text_widget.focus()

        # hit enter
        if execute:
            text_widget.event_generate('<Return>')

    def open_text_file(self, file_path: str = None, window_id: str = None, tag_text=None, **kwargs):
        """
        This opens a text file in a new (or existing) text window
        :param file_path:
        :param window_id:
        :param tag_text:
        :return:
        """

        # first check if the file exists
        if file_path is None or not os.path.isfile(file_path):
            logger.error('Aborting. Unable to open text file. File path is invalid.')
            return False

        # now load the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            logger.error(f'Unable to open text file. Error: {e}')
            return False

        # now open the text window
        self.open_text_window(initial_text=file_content, window_id=window_id, can_find=True, **kwargs)

        def tag_passed_text():

            # if we have a tag_text, tag the text in the window
            if tag_text is not None and window_id in self.text_windows:

                # get the text widget
                text_widget = self.text_windows[window_id]['text_widget']

                # remove existing tags
                text_widget.tag_delete('find_result_tag')

                tag_index = text_widget.search(tag_text, 1.0, nocase=True, stopindex="end")

                # if we have a tag_index, tag the text
                if tag_index != -1:

                    # tag the text
                    # text_widget.tag_add('find_result_tag', f'{tag_index}', f'{tag_index} + {len(tag_text)}c')
                    text_widget.tag_add('find_result_tag', tag_index, '{}+{}c'.format(tag_index, len(tag_text)))

                    # configure the tag
                    text_widget.tag_config('find_result_tag', foreground=self.theme_colors['red'])

                    # scroll to the tag
                    text_widget.see(f'{tag_index}')

        text_window = self.get_window_by_id(window_id)

        # tag the text 50 ms after the window is opened
        text_window.after(50, tag_passed_text)

    # FIND-REPLACE MODAL WINDOW

    def open_find_replace_window(self, window_id=None, title: str = 'Find and Replace',
                                 parent_window_id: str = None, text_widget=None,
                                 replace_field: bool = False, find_text: str = None, replace_text: str = None,
                                 post_replace_action: str = None, post_replace_action_args: list = None,
                                 **kwargs
                                 ):
        """
        This window is used to find (and replace) text in a text widget of another window
        """

        if not parent_window_id and not text_widget:
            logger.error('Aborting. Unable to open find and replace window without a parent window.')
            return False

        # always use the parent in the window id if no window id is given
        if not window_id:
            window_id = 'find_' + parent_window_id.replace(' ', '_').replace('.', '')

        # open the find and replace window
        if self.create_or_open_window(parent_element=self.root, window_id=window_id, title=title, type='find',
                                      close_action=lambda l_window_id=window_id:
                                      self.destroy_find_replace_window(l_window_id, parent_window_id=parent_window_id)):

            # add the window to the find_windows dict, and also include the parent window id
            self.find_windows[window_id] = {'parent_window_id': parent_window_id}

            # add the window to the text_windows dict, in case we need to reference it from the parent window
            self.text_windows[parent_window_id]['find_window_id'] = window_id

            # create a frame for the find input
            find_frame = ctk.CTkFrame(self.windows[window_id], name='find_frame', **self.ctk_frame_transparent)
            find_frame.pack(expand=True, fill='both', **self.ctk_popup_frame_paddings)

            # create a label for the find input
            find_label = ctk.CTkLabel(find_frame, text='Find:', name='find_label')
            find_label.pack(side=ctk.LEFT, **self.ctk_popup_input_paddings)

            # create the find input
            find_str = tk.StringVar()
            find_input = ctk.CTkEntry(find_frame, textvariable=find_str, name='find_input')
            find_input.pack(side=ctk.LEFT, expand=True, fill='x', **self.ctk_popup_input_paddings)

            parent_text_widget = self.text_windows[parent_window_id]['text_widget']

            # create the select all button
            if kwargs.get('select_all_action', False):
                # only create the button here and add the lambda function later in the _find_text_in_widget function
                kwargs['select_all_button'] = \
                    ctk.CTkButton(find_frame, text='Select All', name='select_all_button')

            # if the user presses a key in the find input,
            # call the _find_text_in_widget function
            find_str.trace("w", lambda name, index, mode, l_find_str=find_str, l_parent_window_id=parent_window_id:
            self._find_text_in_widget(l_find_str, l_parent_window_id, text_widget=parent_text_widget, **kwargs))

            # return key cycles through the results
            find_input.bind('<Return>',
                            lambda e, l_parent_text_widget=parent_text_widget, l_parent_window_id=parent_window_id:
                            self._cycle_through_find_results(text_widget=l_parent_text_widget,
                                                             window_id=l_parent_window_id))

            # escape key closes the window
            find_input.bind('<Escape>', lambda e, l_window_id=window_id: self.destroy_find_replace_window(l_window_id))

            # if a find text is given, add it to the find input
            if find_text:
                find_input.insert(0, find_text)

            # todo: add replace field when needed
            if replace_field:
                # create a frame for the replace input
                replace_frame = ctk.CTkFrame(self.windows[window_id], name='replace_frame',
                                             **self.ctk_frame_transparent)
                replace_frame.pack(expand=True, fill='both', **self.ctk_popup_frame_paddings)

                # create a label for the replace input
                replace_label = ctk.CTkLabel(replace_frame, text='Replace:', name='replace_label')
                replace_label.pack(side=ctk.LEFT, **self.ctk_popup_input_paddings)

                # create the replace input
                replace_input = ctk.CTkEntry(replace_frame, name='replace_input')
                replace_input.pack(side=ctk.LEFT, expand=True, fill='x', **self.ctk_popup_input_paddings)

                # if a replace text is given, add it to the replace input
                if replace_text:
                    replace_input.insert(0, replace_text)

                replace_button = ctk.CTkButton(replace_frame, text='Replace', name='replace_button',
                                               command=lambda: self._replace_text_in_widget(
                                                   window_id=window_id,
                                                   text_widget=text_widget,
                                                   post_replace_action=post_replace_action,
                                                   post_replace_action_args=post_replace_action_args
                                               )
                                               )
                replace_button.pack(side=ctk.LEFT, **self.ctk_popup_input_paddings)

            # create a footer frame that holds stuff on the bottom of the window
            footer_frame = ctk.CTkFrame(self.windows[window_id], name='footer_frame', **self.ctk_frame_transparent)
            footer_frame.pack(expand=True, fill='both', **self.ctk_popup_frame_paddings)

            # add a status label to the footer frame
            status_label = ctk.CTkLabel(footer_frame, name='status_label',
                                        text="", anchor='w', text_color=self.theme_colors['normal'])
            status_label.pack(side=ctk.LEFT, **self.ctk_popup_input_paddings)

            # add the status label to the find_windows dict so we can update it later
            self.find_windows[window_id]['status_label'] = status_label

            # focus in the find_input after 100 ms
            find_input.after(100, lambda: find_input.focus_set())

    def destroy_find_replace_window(self, window_id, parent_window_id=None):
        """
        This function destroys a find text window
        :param window_id:
        :param parent_window_id:
        :return:
        """

        # if no parent window id is specified, try to find it
        if parent_window_id is None:
            if window_id in self.find_windows and 'parent_window_id' in self.find_windows[window_id]:
                parent_window_id = self.find_windows[window_id]['parent_window_id']

        # clear the find_window element in the text windows dict
        if 'find_window_id' in self.text_windows[parent_window_id]:
            del self.text_windows[parent_window_id]['find_window_id']

            # clear any find results from main text window

            if self.text_windows[parent_window_id]['text_widget'] is not None:
                self.text_windows[parent_window_id]['text_widget'].tag_delete('find_result_tag')
                self.text_windows[parent_window_id]['text_widget'].tag_delete('found')

        # clear the find windows dict
        if window_id in self.find_windows:
            del self.find_windows[window_id]

        # call the default destroy window function
        self.destroy_window_(windows_dict=self.windows, window_id=window_id)

    def _find_text_in_widget(self, search_str: str = None, window_id: str = None, text_widget: tk.Text = None,
                             **kwargs):
        """
        This function finds and highlights found matches in a text widget

        :param search_str: the string to search for
        :param window_id: the id of the window that contains the text widget
        :param text_widget: the text widget to search in

        :return:
        """

        if search_str is None or text_widget is None or window_id is None:
            logger.error('Aborting. Unable to find text in widget without a search string, text widget, and window id.')
            return False

        # remove tag 'found' from index 1 to ctk.END
        text_widget.tag_remove('found', '1.0', ctk.END)

        # remove tag 'current_result_tag' from index 1 to ctk.END
        text_widget.tag_remove('current_result_tag', '1.0', ctk.END)

        # reset the search result indexes and the result position
        self.find_result_indexes[window_id] = []
        self.find_result_pos[window_id] = 0

        # get the search string as the user is typing
        search_str = self.find_strings[window_id] = search_str.get()

        if search_str:
            idx = '1.0'

            self.find_strings[window_id] = search_str

            # do not search if the search string shorter than 0 characters
            # - this limit is a bad idea in general, considering that there are languages that use single characters...
            #   so we'll just keep it to 0 for now
            if len(search_str) >= 1:

                while 1:

                    # searches for desired string from index 1
                    idx = text_widget.search(search_str, idx, nocase=True, stopindex=ctk.END)

                    # stop the loop when we run out of results (indexes)
                    if not idx:
                        break

                    # store each index
                    self.find_result_indexes[window_id].append(idx)

                    # last index sum of current index and
                    # length of text
                    lastidx = '%s+%dc' % (idx, len(search_str))

                    # add the found tag at idx
                    text_widget.tag_add('found', idx, lastidx)
                    idx = lastidx

                # if we have results,
                # take the viewer to the first occurrence
                if self.find_result_indexes[window_id] and len(self.find_result_indexes[window_id]) > 0 \
                        and self.find_result_indexes[window_id][0] != '':
                    text_widget.see(self.find_result_indexes[window_id][0])

                    # and visually tag the results
                    self._tag_find_results(text_widget, self.find_result_indexes[window_id][0], window_id)

                    # if there is a select_all_action, show the select all button
                    if kwargs.get('select_all_action', False) and kwargs.get('select_all_button', False):
                        select_all_action = kwargs.get('select_all_action')

                        # add the select_all_action to the select_all_button
                        # but also send the transcription window id, the text widget and the result indexes
                        kwargs.get('select_all_button') \
                            .configure(command=lambda l_window_id=window_id, l_text_widget=text_widget:
                            select_all_action(
                                window_id=l_window_id,
                                text_element=l_text_widget,
                                text_indices=self.find_result_indexes[window_id])
                                           )

                        kwargs.get('select_all_button').pack(side=ctk.LEFT, **self.ctk_popup_input_paddings)

                # if we don't have results, hide the select all button (if there is any)
                else:
                    if kwargs.get('select_all_button', False):
                        kwargs.get('select_all_button').pack_forget()

                # mark located string with red
                text_widget.tag_config('found', foreground=self.theme_colors['red'])

                # update the status label in the find window

                if 'find_window_id' in self.text_windows[window_id]:
                    find_window_id = self.text_windows[window_id]['find_window_id']
                    self.find_windows[find_window_id]['status_label'] \
                        .configure(text=f'{len(self.find_result_indexes[window_id])} results found')

                return

        # clear the status label in the find window and hide the select all button
        if 'find_window_id' in self.text_windows[window_id]:

            find_window_id = self.text_windows[window_id]['find_window_id']
            self.find_windows[find_window_id]['status_label'] \
                .configure(text='')

            if kwargs.get('select_all_button', False):
                kwargs.get('select_all_button').pack_forget()

    def _tag_find_results(self, text_widget: tk.Text = None, text_index: str = None, window_id: str = None):
        """
        Another handy function that tags the search results directly on the transcript inside the transcript window
        This is also used to show on which of the search results is the user right now according to search_result_pos
        :param text_element:
        :param text_index:
        :param window_id:
        :return:
        """
        if text_widget is None:
            return False

        # remove previous position tags
        text_widget.tag_delete('find_result_tag')

        if not text_index or text_index == '' or text_index is None or window_id is None:
            return False

        # add tag to show the user on which result position we are now
        # the tag starts at the text_index and ends according to the length of the search string
        text_widget.tag_add('find_result_tag', text_index, text_index + '+'
                            + str(len(self.find_strings[window_id])) + 'c')

        # the result tag has a white background and a red foreground
        text_widget.tag_config('find_result_tag', background=self.theme_colors['white'],
                               foreground=self.theme_colors['red'])

    def _cycle_through_find_results(self, text_widget: tk.Text = None, window_id: str = None):

        if text_widget is not None or window_id is not None \
                or self.find_result_indexes[window_id] or self.find_result_indexes[window_id][0] != '':

            # if we have no results, return
            if window_id not in self.find_result_indexes \
                    or not self.find_result_indexes[window_id]:
                return False

            # get the current search result position
            current_pos = self.find_result_pos[window_id]

            # as long as we're not going over the number of results
            if current_pos < len(self.find_result_indexes[window_id]) - 1:

                # add 1 to the current result position
                current_pos = self.find_result_pos[window_id] = current_pos + 1

                # this is the index of the current result position
                text_index = self.find_result_indexes[window_id][current_pos]

                # go to the next search result
                text_widget.see(text_index)

            # otherwise go back to start
            else:
                current_pos = self.find_result_pos[window_id] = 0

                # this is the index of the current result position
                text_index = self.find_result_indexes[window_id][current_pos]

                # go to the next search result
                text_widget.see(self.find_result_indexes[window_id][current_pos])

            # visually tag the results
            self._tag_find_results(text_widget, text_index, window_id)

    class AskDialog(ctk.CTkToplevel):
        """
        This is a simple dialogue window that asks the user for input before continuing with the task
        But it also halts the execution of the main window until the user closes the dialogue window
        When the user closes the dialogue window, it will return the user input to the main window
        """

        def __init__(self, parent: str or tk.Tk, title, input_widgets, toolkit_UI_obj=None, buttons=None, **kwargs):

            self.toolkit_UI_obj = toolkit_UI_obj

            # if the parent is a string
            if isinstance(parent, str):
                # we need to get the parent window object from toolkit_UI_obj
                parent = self.toolkit_UI_obj.get_window_by_id(window_id=parent)

            super().__init__(parent)

            # set the icon
            self.toolkit_UI_obj.UI_set_icon(self)

            self.parent = parent
            self.title(title)

            self.custom_buttons = buttons

            # the transient function is used to make the window transient to the parent window
            # which means that the window will appear on top of the parent window
            # If the parent is not viewable, don't make the child transient, or else it
            # would be opened withdrawn
            if parent is not None and parent.winfo_viewable():
                self.transient(parent)

            # this is the dictionary that will hold the user input
            self.return_value = {}
            self.cancel_return = None

            # add the widgets
            self._add_widgets(input_widgets, **kwargs)

            # no resizing after this
            self.resizable(False, False)

            # do not allow clicking on other windows, including the parent window
            self.grab_set()

            # center the window after all the widgets have been added
            self.center_window()

            # if the user tries to defocus out of the window, do not allow it
            # self.bind("<FocusOut>", lambda e: self.focus_set())

            self.protocol("WM_DELETE_WINDOW", self.cancel)

            # wait for the user to close the window
            self.wait_window(self)

        def _add_widgets(self, input_widgets, **kwargs):
            """
            This adds the widgets to the window, depending what was passed to the class.
            We work with pairs of label+entry widgets, each having a name which we will use in the return dictionary.
            :param kwargs:
            :return:
            """

            have_input_widgets = False
            row = 0

            # create a frame for the input widgets
            input_frame = ctk.CTkFrame(self, **toolkit_UI.ctk_frame_transparent)

            # take all the entry widgets and add them to the window
            for widget in input_widgets:

                # get the widget name
                widget_name = widget['name']

                # get the widget label
                widget_label = widget.get('label', '')

                # get the widget default value
                widget_default_value = widget.get('default_value', None)

                # don't allow more than X characters per line in the label
                # - so add a new line after X characters but keep full words
                label_split = widget.get('label_split', None)
                if label_split:
                    words = widget_label.split(' ')
                    split_lines = []
                    current_line = ""

                    for word in words:
                        # If adding the new word exceeds the maximum line length, start a new line.
                        if len(current_line) + len(word) + (1 if current_line else 0) > label_split:
                            split_lines.append(current_line)
                            current_line = word
                        else:
                            # Otherwise, append the word to the current line.
                            if current_line:
                                current_line += " "
                            current_line += word

                    # Add the last processed line if it's non-empty
                    if current_line:
                        split_lines.append(current_line)

                    widget_label = '\n'.join(split_lines)

                # add the label
                label = ctk.CTkLabel(input_frame, text=widget_label)

                input_widget = None
                input_value = None

                input_widget_parent = input_frame
                input_unit = None

                # if we have a unit, add it to the input widget
                # and create a frame that holds them both
                if 'unit' in widget:
                    input_unit = widget['unit']

                    value_unit_frame = ctk.CTkFrame(input_frame, **toolkit_UI.ctk_frame_transparent)
                    input_widget_parent = value_unit_frame

                row = row + 1

                # add the input widget, depending on the type
                # entry widget
                if widget['type'] == 'entry':
                    input_value = tk.StringVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkEntry(input_widget_parent, textvariable=input_value,
                                                **toolkit_UI.ctk_askdialog_input_size)
                elif widget['type'] == 'entry_int':
                    input_value = tk.IntVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkEntry(input_widget_parent, textvariable=input_value,
                                                **toolkit_UI.ctk_askdialog_input_int_size)
                elif widget['type'] == 'entry_float':
                    input_value = tk.StringVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkEntry(input_widget_parent, textvariable=input_value,
                                                **toolkit_UI.ctk_askdialog_input_int_size)

                    # only allow floats in the input_widget
                    input_widget.configure(
                        validate="key",
                        validatecommand=(
                            input_widget.register(self.toolkit_UI_obj.only_allow_floats), '%P'
                        )
                    )

                # selection widget
                elif widget['type'] == 'option_menu' and 'options' in widget:
                    input_value = tk.StringVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkOptionMenu(input_widget_parent, variable=input_value, values=widget['options'],
                                                     **toolkit_UI.ctk_askdialog_input_size)
                    # input_widget.configure(takefocus=True)

                # checkbox widget
                elif widget['type'] == 'checkbutton':
                    input_value = tk.BooleanVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkCheckBox(input_widget_parent, variable=input_value)

                elif widget['type'] == 'switch':
                    input_value = tk.BooleanVar(input_frame, widget_default_value)
                    input_widget = ctk.CTkSwitch(input_widget_parent, variable=input_value, text='')

                # text widget
                elif widget['type'] == 'text':
                    input_value = tk.StringVar(input_frame, widget_default_value)
                    input_widget = tk.Text(input_widget_parent, height=5, width=30)
                    input_widget.insert(1.0, widget_default_value)

                elif widget['type'] == 'label':
                    input_value = None
                    input_widget = None

                # add the widget to the window
                if input_widget:

                    label.grid(row=row, column=0, sticky='e', **toolkit_UI.ctk_askdialog_input_paddings)

                    # if we don't have a unit label, add the widget to the input frame
                    if not input_unit:
                        input_widget.grid(row=row, column=1, sticky='w', **toolkit_UI.ctk_askdialog_input_paddings)

                    # otherwise, add the widget to the value_unit_frame
                    else:
                        # add the unit label
                        unit_label = ctk.CTkLabel(input_widget_parent, text=input_unit)
                        input_widget.grid(row=0, column=1, sticky='w', **toolkit_UI.ctk_askdialog_input_paddings)
                        unit_label.grid(row=0, column=2, sticky='w', **toolkit_UI.ctk_askdialog_input_paddings)

                        input_widget_parent.grid(row=row, column=1, sticky='w')

                    # add the widget to the user_input dictionary
                    self.return_value[widget_name] = input_value

                    if widget.get('error'):
                        self.toolkit_UI_obj.style_input_as_invalid(input_widget=input_widget, label=label)

                    # focus on the first input widget
                    if row == 1:
                        input_widget.focus_set()

                    # if we reached this point, we have a valid widget
                    have_input_widgets = True

                # if we don't have an input_widget it must mean that we're only adding a label which spans 2 columns
                # and has the text aligned to the left
                else:

                    if 'style' in widget and widget['style'] == 'main':
                        # get the current font of the label
                        current_font = label.cget("font")
                        current_font_family = current_font.cget('family')
                        current_font_size = current_font.cget('size')

                        # make the font bold
                        input_style = ctk.CTkFont(family=current_font_family, size=current_font_size, weight='bold')

                        # set the new font
                        label.configure(font=input_style)

                        # expand the input frame so that the labe will be centered
                        input_frame.columnconfigure(1, weight=1)

                        # make the label text white
                        label.configure(text_color=self.toolkit_UI_obj.theme_colors['highlight'])

                    label.configure(anchor='n', justify='center')
                    label.grid(
                        row=row, column=0, columnspan=2, sticky='ew', **toolkit_UI.ctk_askdialog_input_paddings)

            # if we have no input widgets or custom buttons, return
            if not have_input_widgets and not self.custom_buttons:
                logger.error('No input widgets were added to the Ask Dialogue window. Aborting.')
                return None

            # pack the input frame
            input_frame.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, **toolkit_UI.ctk_askdialog_frame_paddings)

            buttons_frame = ctk.CTkFrame(self, **toolkit_UI.ctk_frame_transparent)

            # when using custom buttons, AskDialog will also return the value of the button that was clicked
            # in the example below, we have the 2 buttons that will return a value for the key 'choice':
            # - value 'new' for the first button
            # - value 'show_text' for the second button
            # ask user using AskDialog
            # buttons = [
            #     {'name': 'choice', 'label': 'Save as new transcription', 'value': 'new'},
            #     {'name': 'choice', 'label': 'Just show the text', 'value': 'show_text'}
            # ]

            # dialog_transcription_message = "The Assistant replied with a transcription.\n\n" \
            #                                "What should we do with it?"

            # input_widgets = [
            #    {'name': 'transcription_name', 'label': dialog_transcription_message,
            #     'type': 'label', 'style': 'main'}
            #]

            # if we have custom buttons, add them
            if self.custom_buttons:
                for button_info in self.custom_buttons:

                    additional_return = {button_info['name']: button_info['value']}

                    # add the button
                    # for the command, we basically call the ok function with the additional return value
                    button = ctk.CTkButton(
                        buttons_frame,
                        text=button_info['label'],
                        command=lambda l_additional_return=additional_return:
                        self.ok(additional_return=l_additional_return)
                    )

                    # add each button on its own row:
                    button.pack(side=ctk.LEFT, **toolkit_UI.ctk_askdialog_input_paddings)

            # otherwise add an ok button
            else:
                # add the OK button
                ok_button = ctk.CTkButton(buttons_frame, text="OK", command=self.ok)
                ok_button.pack(side=ctk.LEFT, **toolkit_UI.ctk_askdialog_input_paddings)
                self.bind("<Return>", self.ok)

            # if we have a cancel_return, add the Cancel button
            if 'cancel_return' in kwargs:
                cancel_button = ctk.CTkButton(buttons_frame, text="Cancel", command=self.cancel)
                cancel_button.pack(side=ctk.LEFT, **toolkit_UI.ctk_askdialog_input_paddings)

                # add the cancel action
                self.cancel_return = kwargs['cancel_return']

                # enable the escape key to cancel the window
                self.bind("<Escape>", self.cancel)

            # pack the buttons frame
            buttons_frame.pack(side=ctk.TOP, fill=ctk.BOTH, expand=True, **toolkit_UI.ctk_askdialog_frame_paddings)

        def center_window(self):

            # get the window size
            window_width = self.winfo_reqwidth()
            window_height = self.winfo_reqheight()

            # if we have no parent window,
            # or the parent window is the root window, center on the screen
            if self.parent == self.toolkit_UI_obj.root:

                # get the screen size
                screen_width = self.parent.winfo_screenwidth()
                screen_height = self.parent.winfo_screenheight()

                # calculate the position of the window, considering its own size too
                x = (screen_width / 2) - (window_width / 2)
                y = (screen_height / 2) - (window_height / 2)


            else:

                # parent window size
                parent_width = self.parent.winfo_reqwidth()
                parent_height = self.parent.winfo_reqheight()

                # get the position of the parent window
                x = self.parent.winfo_rootx()
                y = self.parent.winfo_rooty()

                # set the position of the window so that it's centered on the parent window
                # self.geometry('+%d+%d' % (x + parent_width/2, y+parent_height/2))
                # but take the window size into account
                self.geometry(
                    '+%d+%d' % (x + parent_width / 2 - window_width / 2, y + parent_height / 2 - window_height / 2))

        def ok(self, event=None, additional_return=None):
            """
            This is the action that happens when the user clicks the OK button
            :return:
            """

            # take the user input and return it
            self.return_value = {k: v.get() for k, v in self.return_value.items()}

            # add any additional return values that were passed
            if additional_return is not None:
                self.return_value = {**self.return_value, **additional_return}

            # destroy the window
            self.destroy()

            # refocus on the parent element
            self.parent.focus_set()

        def cancel(self, event=None):
            """
            This is the action that happens when the user clicks the Cancel button
            :return:
            """

            self.return_value = None

            # execute the cancel action if it's callable
            if self.cancel_return is not None and callable(self.cancel_return):
                self.cancel_return()

            # if it's not callable, just return the cancel_return value
            elif self.cancel_return is not None:
                self.return_value = self.cancel_return

            # if it's None, return None
            else:
                self.return_value = None

            # destroy the window
            self.destroy()

            # refocus on the parent element
            self.parent.focus_set()

        def value(self):
            return self.return_value

    # INGEST WINDOW

    def open_ingest_window(self, title="Ingest Files", queue_id=None, **kwargs):
        """
        This will open the main window for ingesting files
        If a transcription_file_path that exists is passed, it will be used as a Re-transcribing window

        """

        # assign a queue_id for this window depending on the queue queue_id
        ingest_window_id = 'ingest-' + str(queue_id if queue_id is not None else time.time())

        # if a transcription path was passed, use its hash instead
        if 'transcription_file_path' in kwargs \
                and kwargs['transcription_file_path'] is not None:

            # get the transcription and load the file
            transcription = Transcription(transcription_file_path=kwargs['transcription_file_path'])

            # check if the transcription path exists
            if transcription.exists:

                # use the transcription path id in the window id
                ingest_window_id = 'ingest-' + transcription.transcription_path_id

                # add the name of the transcription to the window
                title = "Re-transcribe" + (' - ' + transcription.name if transcription.name else '')

            # if the transcription path doesn't exist, remove it from the kwargs
            else:
                del kwargs['transcription_file_path']

        # create a function to close the ingest window
        def close_ingest_window():
            self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id)

        # create an empty form_vars dictionary
        # so we can easily gather all the user input turned into variables
        # that need to be sent when pressing the start button (or any other buttons)
        form_vars = {}

        if self.create_or_open_window(parent_element=self.root, window_id=ingest_window_id, type='ingest',
                                      title=title, open_multiple=True, close_action=close_ingest_window,
                                      resizable=(False, True)
                                      ):

            # update the queue item status to 'waiting user'
            if queue_id is not None:
                self.toolkit_ops_obj.processing_queue.update_queue_item(queue_id=queue_id, status='waiting user')

                # add the queue id to the kwargs
                kwargs['queue_id'] = queue_id

                # add the queue id to the form vars as a tk variable
                form_vars['queue_id'] = tk.StringVar(value=queue_id)

            # use this variable for the ingest window object for cleaner code
            ingest_window = self.windows[ingest_window_id]

            # add the ingest_window_id to the kwargs
            kwargs['ingest_window_id'] = ingest_window_id

            # UI - escape key closes the window
            ingest_window.bind('<Escape>', lambda event: close_ingest_window())

            # UI - create the top frame
            top_frame = ctk.CTkFrame(ingest_window)

            # UI - create the middle frame (it's a tab view)
            middle_frame = ctk.CTkTabview(ingest_window)

            # UI - create the bottom frame
            bottom_frame = ctk.CTkFrame(ingest_window, **self.ctk_frame_transparent)

            # UI -
            # but instead of packing the frames, use a grid layout,
            # so that the top frame and the bottom frames only take the space they need
            # and the middle frame extends with the window
            top_frame.grid(row=0, column=0, sticky="ew", **self.ctk_frame_paddings)
            middle_frame.grid(row=1, column=0, sticky="nsew", **self.ctk_frame_paddings)
            bottom_frame.grid(row=2, column=0, sticky="ew", **self.ctk_frame_paddings)

            # UI - grid configure the middle frame so that it expands with the window
            ingest_window.grid_rowconfigure(1, weight=1)

            # UI - the columns should expand with the window
            ingest_window.grid_columnconfigure(0, weight=1, minsize=500)

            # TOP FRAME ELEMENTS
            # these will be added a few lines below

            # MIDDLE FRAME ELEMENTS

            # UI - add the audio and video tabs
            audio_tab = middle_frame.add('Audio')
            video_tab = middle_frame.add('Video')
            analysis_tab = middle_frame.add('Analysis')

            # UI - add a scrollable frame to the audio and video tabs
            audio_tab_scrollable_frame = ctk.CTkScrollableFrame(audio_tab, **self.ctk_frame_transparent)
            audio_tab_scrollable_frame.pack(fill='both', expand=True)

            video_tab_scrollable_frame = ctk.CTkScrollableFrame(video_tab, **self.ctk_frame_transparent)
            video_tab_scrollable_frame.pack(fill='both', expand=True)

            # UI - set the visibility on the audio tab
            middle_frame.set('Audio')
            middle_frame.columnconfigure(0, weight=1)

            # BOTTOM FRAME ELEMENTS
            # the bottom frame should have a start button, a cancel button, a progress bar, and a progress label
            # the start button should stick to the left
            # the cancel button should stick to the right
            # the progress bar should be under the start button and the cancel button

            # UI - create another frame for the buttons
            buttons_frame = ctk.CTkFrame(bottom_frame, **self.ctk_frame_transparent)

            # UI - create the start button
            start_button = ctk.CTkButton(buttons_frame, text='Start', state='disabled')

            # UI - create the cancel button
            cancel_button = ctk.CTkButton(buttons_frame, text='Cancel')

            # create the progress bar
            # progress_bar = ctk.CTkProgressBar(bottom_frame, mode='determinate')

            # create the progress label
            # progress_label = ctk.CTkLabel(bottom_frame, text='Ready')

            # UI - add the start button, the cancel button
            buttons_frame.grid(row=0, column=0, sticky="w", **self.ctk_frame_paddings)

            # UI - the buttons should be next to each other, so we'll use a pack layout
            start_button.pack(side='left', **self.ctk_footer_button_paddings)
            cancel_button.pack(side='left', **self.ctk_footer_button_paddings)

            # add the buttons to the kwargs so we can pass them to future functions
            kwargs['start_button'] = start_button
            kwargs['cancel_button'] = cancel_button

            # add the form_invalid attribute to the window to store which items are invalid (if any)
            ingest_window.form_invalid = []

            # add the file/folder selection form (in the top frame)
            file_path_var = self.add_select_files_form_elements(top_frame, **kwargs)

            # if something went wrong with the file selection, let's close the window
            if file_path_var is None:
                logger.error('Something went wrong with the file options')
                self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id, dont_ask=True)
                return None

            # add the ingest audio options to the audio tab (in the middle frame)
            audio_form_vars = self.add_ingest_audio_form_elements(audio_tab_scrollable_frame, **kwargs)

            # if something went wrong with the audio options tab, close the window
            if audio_form_vars is None:
                logger.error('Something went wrong with the audio options')
                self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id, dont_ask=True)
                return None

            # add the ingest video options to the video tab (in the middle frame)
            video_form_vars = self.add_ingest_video_form_elements(video_tab_scrollable_frame, **kwargs)

            # if something went wrong with the audio options tab, close the window
            if video_form_vars is None:
                logger.error('Something went wrong with the video options')
                self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id, dont_ask=True)
                return None

            # add the analysis options to the analysis tab (in the middle frame)
            analysis_form_vars = self.add_analysis_form_elements(analysis_tab, **kwargs)

            # if something went wrong with the analysis options tab, close the window
            if analysis_form_vars is None:
                logger.error('Something went wrong with the analysis options')
                self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id, dont_ask=True)
                return None

            # add the variables from the added forms above to the form variables
            form_vars = {**form_vars, **file_path_var,
                         'audio_form_vars': audio_form_vars,
                         'video_form_vars': video_form_vars,
                         'analysis_form_vars': analysis_form_vars}

            # UI - start button command
            # at this point, the kwargs should also contain the ingest_window_id
            start_button.configure(
                command=lambda:
                self.button_start_ingest(form_vars=form_vars, **kwargs)
            )

            # UI - cancel button command
            cancel_button.configure(
                command=lambda:
                self.button_cancel_ingest(window_id=ingest_window_id, queue_id=queue_id)
            )

            # the progress bar should be under the start button and the cancel button
            # progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", **self.ctk_frame_paddings)

            # the progress label should be under the progress bar
            # progress_label.grid(row=2, column=0, columnspan=2, sticky="w", **self.ctk_frame_paddings)

            # UI - configure the bottom columns and rows so that the elements expand with the window
            bottom_frame.columnconfigure(0, weight=1)
            bottom_frame.columnconfigure(1, weight=1)
            bottom_frame.rowconfigure(1, weight=1)
            bottom_frame.rowconfigure(2, weight=1)

            # UI - add a minimum height to the window
            ingest_window.minsize(500, 700
            if ingest_window.winfo_screenheight() > 700 else ingest_window.winfo_screenheight())

            # UI- add a maximum height to the window (to prevent it from being bigger than the screen)
            ingest_window.maxsize(600, ingest_window.winfo_screenheight())

            # add the form variables to the window
            ingest_window.form_vars = form_vars

            # and focus on the window
            self.focus_window(window=ingest_window)

            # if we're supposed to skip the settings
            if kwargs.get('skip_settings', False):
                # send all the vars to ingest
                # (this will also check if the form is valid)
                self.button_start_ingest(form_vars=form_vars, **kwargs)

            return

        else:
            # todo: simply update the existing window with the passed arguments
            #   then get back the updated from variables and an updated start button / and anything else?

            return

    def files_string_to_list(self, path):
        """
        This function takes a string and returns a list of files from it if it's in a valid format
        """

        # are these comma separated files or folders?
        if ',' in path:

            # split the paths
            path = path.split(',')

            # remove the quotes from the beginning and end of each path
            path = [p.strip(' \'\"') for p in path]

        # if there are no commas in the path, it must be a single file or folder
        # so if it exists, it's valid
        elif os.path.isfile(path.strip(' \'\"')) or os.path.isdir(path.strip(' \'\"')):
            path = [path]

        return path

    def validate_files_or_folders_path(self, var=None, path: str = None,
                                       valid_callback: callable = None, invalid_callback: callable = None, **kwargs):
        """
        Validates if the variable contains a valid file or folder paths

        :param var: the variable to validate
        :param entry: the entry to validate
        :param valid_callback: the callback to execute if the path is valid
        :param invalid_callback: the callback to execute if the path is invalid
        :return: the path if it's valid, None otherwise
        """

        if path is None and var is None:
            logger.error('Unable to validate files or folders - no path or variable was passed.')
            return None

        # if no path was passed, get the path from the variable
        if path is None:
            # get the variable value
            path = var.get()

        # convert the path to a list
        path = self.files_string_to_list(path)

        # check if all the paths are valid
        # if all the paths are valid, the result will be True
        valid = all([os.path.isfile(p.strip()) or os.path.isdir(p.strip()) for p in path])

        # take the files through the file analyzer to see if they're valid
        if valid and kwargs.get('file_analyze_callback') is not None:

            for current_path in path:

                # if one of the files is not valid, set valid to False and break
                if not kwargs.get('file_analyze_callback')(path=current_path, **kwargs):
                    valid = False
                    break

        # if the file path is empty, clear the label and return
        if valid:

            # execute the valid callback if it exists
            if valid_callback is not None:

                # check the reply from the callback and if it's False/None, return None
                valid = valid_callback(path=path, **kwargs)

                if not valid:
                    return None

            # return the path
            return path

        else:

            # execute the invalid callback if it exists
            if invalid_callback is not None:
                invalid_callback(path=path, **kwargs)

            # return None
            return None

    def validate_time_interval_var(self, var, valid_callback: callable = None,
                                   invalid_callback: callable = None, strict=False, **kwargs):
        """
        Validates if the variable contains valid time intervals
        We're basically just passing the variable to the validate_time_interval function
        and returning the result, while also executing the callbacks if they exist
        """

        valid = False

        # get the time intervals from the passed variable
        time_intervals = var.get()
        kwargs['time_intervals'] = time_intervals

        # validate the time intervals
        # (we're converting them to a list of lists, and checking if they're valid while doing so)
        valid = self.convert_text_to_time_intervals(text=time_intervals, supress_errors=True, **kwargs)

        # if this is just an empty string and we're not doing strict validation, validate
        if not strict and time_intervals.strip() == '':
            valid = True

        # if the time intervals are valid
        if valid:

            # execute the valid callback if it exists
            if valid_callback is not None:

                # check the reply from the callback and if it's False/None, return None
                valid = valid_callback(**kwargs)

                if not valid:
                    return None

            # return the time_intervals
            return time_intervals

        # execute the invalid callback if it exists
        if invalid_callback is not None:
            invalid_callback(**kwargs)

        # return None
        return None

    def add_select_files_form_elements(self, parent: tk.Widget, **kwargs) -> dict or None:
        """
        This is a universal function that creates a form section for selecting files or folders

        :param parent: the parent element
        :param kwargs: other stuff to pass to the function (start_button etc.)
        :return: all the variables that are created here in a dict or None if the function fails
        """

        if parent is None:
            return None

        # create a dict to gather all the form variables
        # so we can return them later
        form_vars = {}

        # create a frame for the form elements
        file_selection_form = ctk.CTkFrame(parent, **self.ctk_frame_transparent)

        form_vars['file_path_var'] = \
            file_path_var = tk.StringVar(parent)
        file_path_entry = ctk.CTkEntry(file_selection_form, width=100, textvariable=file_path_var)

        # create the browse button
        browse_button = ctk.CTkButton(file_selection_form, text='Browse')

        # add the browse button command
        browse_button.bind('<Button-1>', lambda e: self.ask_for_file_or_dir_for_var(parent, file_path_var))

        # browse for directories if Shift+Click
        # browse_button.bind('<Shift-Button-1>', lambda e: self.ask_for_file_or_dir_for_var(parent, file_path_var,
        #                                                                                 directory=True))

        # create the file info label (under the file path entry)
        file_info_label = ctk.CTkLabel(file_selection_form, text='', anchor='w')

        def files_are_valid(path, **kwargs):

            # add the file to the passed file info label label
            if kwargs.get('file_info_label') is not None:
                # reset the text of the file info label
                kwargs.get('file_info_label').configure(text="")

            # remove this from the from_invalid attribute of the window
            self.remove_form_invalid(window_id=kwargs.get('ingest_window_id'), key='file_path', **kwargs)

            # style the entry as valid
            if kwargs.get('file_path_entry') is not None:
                self.style_input_as_valid(kwargs.get('file_path_entry'))

        def files_are_invalid(path, **kwargs):

            # deactivate the start button if it exists
            if kwargs.get('start_button') is not None:
                start_button = kwargs.get('start_button')
                start_button.configure(state='disabled')

            # add this to the form_invalid attribute of the window
            self.add_form_invalid(window_id=kwargs.get('ingest_window_id'), key='file_path', **kwargs)

            # style the entry as invalid
            if kwargs.get('file_path_entry') is not None:
                self.style_input_as_invalid(kwargs.get('file_path_entry'))

        # if the source file path kwarg is set, add the source file path entry
        if kwargs.get('source_file_path', None) is not None:
            file_path_var.set(kwargs.get('source_file_path'))

        def files_changed_callback(*args, **kwargs):
            """
            This is called whenever the files change
            """

            # validate the files and execute the valid or invalid callback
            self.validate_files_or_folders_path(var=file_path_var, entry=file_path_entry,
                                                valid_callback=files_are_valid, file_info_label=file_info_label,
                                                invalid_callback=files_are_invalid, file_path_entry=file_path_entry,
                                                **kwargs)

            # if there a files_changed_callback kwarg exists, execute it
            if kwargs.get('files_changed_callback', None) is not None:
                kwargs.get('files_changed_callback')(path_str=file_path_var.get(), **kwargs)

        # if the source file path is empty, add the form invalid attribute
        # this will keep the start button disabled until the user selects a file
        if file_path_var.get() == '':
            self.add_form_invalid(window_id=kwargs.get('ingest_window_id'), key='file_path', **kwargs)

        # if it the source file path is not empty, validate it
        else:
            files_changed_callback(**kwargs)

        # if the file_path_var changes, validate it
        file_path_var.trace('w', lambda *args: files_changed_callback(file_path=file_path_var.get(), **kwargs))

        # Create the file path entry, the browse button, and the file info label
        # The file path entry should stick to the left and expand horizontally
        # The browse button should stick to the right and be next to the file path entry
        file_path_entry.grid(row=0, column=0, sticky="ew", **self.ctk_frame_paddings)
        browse_button.grid(row=0, column=1, sticky="e", **self.ctk_frame_paddings)

        # Configure column weight for the top frame to make the file_path_entry expand horizontally
        file_selection_form.columnconfigure(0, weight=1)

        # The file info label should be under the file path entry and the browse button
        # (but use the ext paddings to add a bit of space on the left and align it to the entry above)
        # file_info_label.grid(row=1, column=0, columnspan=3, sticky="w", **self.ctk_form_paddings_ext)

        # add the file selection form to the parent
        file_selection_form.pack(fill=ctk.X, expand=True, **self.ctk_frame_paddings)

        # disable the file selection form if we have a transcription path
        if kwargs.get('transcription_file_path', None) is not None:

            # disable the file path entry and the browse button
            file_path_entry.configure(state='disabled')
            browse_button.configure(state='disabled')

            # unbind the click from the browse button
            browse_button.unbind('<Button-1>')

            # remove browse button from grid
            browse_button.grid_forget()

            # make file_path_entry cover the whole row
            file_path_entry.grid(row=0, column=0, columnspan=2, sticky="ew", **self.ctk_frame_paddings)

            transcription = Transcription(transcription_file_path=kwargs.get('transcription_file_path'))

            # get the audio file path from the transcription data (if any) or transcription file
            audio_file_path = transcription.audio_file_path

            if audio_file_path is None:
                # let the user know that the audio file path could not be found
                logger.error("Audio file path not found, cannot re-transcribe.")

                return None

            # and use the audio file path from the transcription path
            file_path_var.set(audio_file_path)

        return form_vars

    def add_ingest_audio_form_elements(self, parent: tk.Widget, **kwargs) -> dict or None:
        """
        This function creates the elements for the ingest audio tab
        - it will be useful both the ingest settings window, but also for the preferences window

        :param parent: the parent element
        :param kwargs: other stuff to pass to the function (start_button, variable values etc.)
        :return: all the variables that are created here in a dict or None if the function fails
        """

        if parent is None:
            return None

        # the audio form elements are split into: basic, post-processing, and advanced
        # for each of these, we will create a frame, and add the elements to it

        # create the frames
        enable_disable_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        basic_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        speakers_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        post_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        advanced_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)

        # create labels for the frames (and style them according to the theme)
        basic_frame_label = ctk.CTkLabel(parent, text='Basic Transcription Settings', **self.ctk_frame_label_settings)
        speakers_frame_label = ctk.CTkLabel(parent, text='Transcription Speakers', **self.ctk_frame_label_settings)
        advanced_frame_label = ctk.CTkLabel(parent, text='Advanced Transcription Settings',
                                            **self.ctk_frame_label_settings)
        post_frame_label = ctk.CTkLabel(parent, text='Transcription Post-Processing', **self.ctk_frame_label_settings)
        # for the advanced settings, we will have a switch on a frame instead of the label
        # advanced_frame_label = ctk.CTkFrame(parent, fg_color=frame_label_fg_color)
        # advanced_frame_switch = ctk.CTkSwitch(advanced_frame_label, text='Advanced Settings')
        # advanced_frame_switch.grid(row=0, column=0, sticky="ew", **self.ctk_frame_paddings)
        # advanced_frame_label.columnconfigure(0, weight=1)

        # we're going to create the form_vars dict to store all the variables
        # we will use this dict at the end of the function to gather all the created tk variables
        form_vars = {}

        # get the last grid row for the parent
        l_row = parent.grid_size()[1]

        # add the labels and frames to the parent
        basic_frame_label.grid(row=l_row + 1, column=0, sticky="ew", **self.ctk_frame_paddings)
        enable_disable_frame.grid(row=l_row + 2, column=0, sticky="ew", **self.ctk_frame_paddings)
        basic_frame.grid(row=l_row + 3, column=0, sticky="ew", **self.ctk_frame_paddings)
        speakers_frame_label.grid(row=l_row + 4, column=0, sticky="ew", **self.ctk_frame_paddings)
        speakers_frame.grid(row=l_row + 5, column=0, sticky="ew", **self.ctk_frame_paddings)
        advanced_frame_label.grid(row=l_row + 6, column=0, sticky="ew", **self.ctk_frame_paddings)
        advanced_frame.grid(row=l_row + 7, column=0, sticky="ew", **self.ctk_frame_paddings)
        post_frame_label.grid(row=l_row + 8, column=0, sticky="ew", **self.ctk_frame_paddings)
        post_frame.grid(row=l_row + 9, column=0, sticky="ew", **self.ctk_frame_paddings)

        # make the column expandable
        parent.columnconfigure(0, weight=1)
        enable_disable_frame.columnconfigure(1, weight=1)
        basic_frame.columnconfigure(1, weight=1)
        speakers_frame.columnconfigure(1, weight=1)
        advanced_frame.columnconfigure(1, weight=1)
        post_frame.columnconfigure(1, weight=1)

        # TRANSCRIPTIONS ENABLE SWITCH
        transcription_enabled = kwargs.get('transcription_enabled', None) \
            if kwargs.get('transcription_enabled', None) is not None \
            else self.stAI.get_app_setting('transcription_enabled', default_if_none=True)

        form_vars['transcription_enabled_var'] = \
            transcription_enabled_var = tk.BooleanVar(enable_disable_frame,
                                                     value=transcription_enabled)
        transcription_enabled_label = ctk.CTkLabel(enable_disable_frame, text='Transcribe Audio',
                                                  **self.ctk_form_label_settings)
        transcription_enabled_input = ctk.CTkSwitch(enable_disable_frame, variable=transcription_enabled_var,
                                                   text='', **self.ctk_form_entry_settings)

        # SOURCE LANGUAGE DROPDOWN
        # get the available languages from whisper, and the default language from the app settings
        languages_available = self.toolkit_ops_obj.get_whisper_available_languages()

        # use either the language selected from the kwargs, or the default language from the app settings
        language_selected = \
            kwargs.get('language_selected', None) \
                if kwargs.get('language_selected', None) is not None \
                else self.stAI.get_app_setting('transcription_default_language', default_if_none='')

        # create the source language variable, label and input
        form_vars['source_language_var'] = \
            source_language_var = tk.StringVar(basic_frame, value=language_selected)
        source_language_label = ctk.CTkLabel(basic_frame, text='Source Language', **self.ctk_form_label_settings)
        source_language_input = ctk.CTkOptionMenu(basic_frame,
                                                  variable=source_language_var,
                                                  values=[''] + languages_available,
                                                  **self.ctk_form_entry_settings)

        # TASK DROPDOWN
        transcription_task = \
            kwargs.get('transcription_task', None) \
                if kwargs.get('transcription_task', None) is not None \
                else self.stAI.get_app_setting('transcription_task', default_if_none='transcribe')

        tasks_available = ['transcribe', 'translate', 'transcribe+translate']

        # create the task variable, label and input
        form_vars['transcription_task_var'] = \
            task_var = tk.StringVar(basic_frame, value=transcription_task)
        task_label = ctk.CTkLabel(basic_frame, text='Task', **self.ctk_form_label_settings)
        task_entry = ctk.CTkOptionMenu(basic_frame, variable=task_var, values=tasks_available,
                                       **self.ctk_form_entry_settings)

        # THE MODEL DROPDOWN
        # get the available models from whisper, and the default model from the app settings
        model_selected = \
            kwargs.get('model_selected', None) \
                if kwargs.get('model_selected', None) is not None \
                else self.stAI.get_app_setting('whisper_model_name', default_if_none='medium')

        # create the model variable, label and input
        form_vars['model_name_var'] = \
            model_name_var = tk.StringVar(basic_frame, value=model_selected)
        model_name_label = ctk.CTkLabel(basic_frame, text='Model', **self.ctk_form_label_settings)
        model_name_input = ctk.CTkOptionMenu(basic_frame, variable=model_name_var, values=whisper_available_models(),
                                             **self.ctk_form_entry_settings)

        # SPEAKER OPTIONS

        # SPEAKER DETECTION
        transcription_speaker_detection = \
            kwargs.get('transcription_speaker_detection', None) \
            if kwargs.get('transcription_speaker_detection', None) is not None \
            else self.stAI.get_app_setting('transcription_speaker_detection', default_if_none=True)

        # create the speaker detection variable, label and switch
        form_vars['transcription_speaker_detection_var'] = \
            transcription_speaker_detection_var = tk.BooleanVar(speakers_frame, value=transcription_speaker_detection)
        transcription_speaker_detection_label = ctk.CTkLabel(
            speakers_frame, text='Speaker Detection', **self.ctk_form_label_settings
        )
        transcription_speaker_detection_input = ctk.CTkSwitch(
            speakers_frame, variable=transcription_speaker_detection_var, text='', **self.ctk_form_entry_settings
        )

        # SPEAKER DETECTION THRESHOLD
        transcription_speaker_detection_threshold = \
            kwargs.get('transcription_speaker_detection_threshold', None) \
            if kwargs.get('transcription_speaker_detection_threshold', None) is not None \
            else self.stAI.get_app_setting('transcription_speaker_detection_threshold', default_if_none=0.3)

        # create the speaker detection threshold variable, label and input
        form_vars['transcription_speaker_detection_threshold_var'] = \
            transcription_speaker_detection_threshold_var = tk.StringVar(
            speakers_frame, value=transcription_speaker_detection_threshold
        )
        transcription_speaker_detection_threshold_label = ctk.CTkLabel(
            speakers_frame, text='Speaker Detection Threshold', **self.ctk_form_label_settings
        )
        transcription_speaker_detection_threshold_input = ctk.CTkEntry(
            speakers_frame,
            textvariable=transcription_speaker_detection_threshold_var, **self.ctk_form_entry_settings_half
        )

        # only allow floats in the transcription_speaker_detection_threshold_input
        transcription_speaker_detection_threshold_input.configure(
            validate="key",
            validatecommand=(transcription_speaker_detection_threshold_input.register(self.only_allow_floats), '%P')
        )

        # ADVANCED OPTIONS
        # device, pre-detect speech, initial prompt, increased time precision, time intervals

        # DEVICE DROPDOWN
        # get the available devices from the toolkit, and the default device from the app settings
        devices_available = ['auto'] + list(self.toolkit_ops_obj.queue_devices)
        device_selected = \
            kwargs.get('device_selected', None) \
                if kwargs.get('device_selected', None) is not None \
                else self.stAI.get_app_setting('whisper_device', default_if_none='auto')

        # create the device variable, label and input
        form_vars['device_var'] = \
            device_var = tk.StringVar(advanced_frame, value=device_selected)
        device_label = ctk.CTkLabel(advanced_frame, text='Device', **self.ctk_form_label_settings)
        device_input = ctk.CTkOptionMenu(advanced_frame, variable=device_var, values=devices_available,
                                         **self.ctk_form_entry_settings)

        # PRE-DETECT SPEECH SWITCH
        # get the pre-detect speech setting from the app settings
        pre_detect_speech = \
            kwargs.get('pre_detect_speech', None) \
                if kwargs.get('pre_detect_speech', None) is not None \
                else self.stAI.get_app_setting('transcription_pre_detect_speech', default_if_none=False)

        # create the pre-detect speech variable, label and input
        form_vars['pre_detect_speech_var'] = \
            pre_detect_speech_var = tk.BooleanVar(advanced_frame, value=pre_detect_speech)
        pre_detect_speech_label = ctk.CTkLabel(advanced_frame, text='Pre-Detect Speech', **self.ctk_form_label_settings)
        pre_detect_speech_input = ctk.CTkSwitch(advanced_frame,
                                                variable=pre_detect_speech_var,
                                                text='',
                                                **self.ctk_form_entry_settings)

        # INCREASED TIME PRECISION (WORD TIMESTAMPS) SWITCH
        # get the increased time precision setting from the app settings
        word_timestamps = \
            kwargs.get('transcription_word_timestamps', None) \
                if kwargs.get('transcription_word_timestamps', None) is not None \
                else self.stAI.get_app_setting('transcription_word_timestamps', default_if_none=False)

        # create the increased time precision variable, label and input
        form_vars['word_timestamps_var'] = \
            word_timestamps_var = tk.BooleanVar(advanced_frame, value=word_timestamps)
        word_timestamps_label = ctk.CTkLabel(advanced_frame, text='Increased Time Precision',
                                             **self.ctk_form_label_settings)
        word_timestamps_input = ctk.CTkSwitch(advanced_frame, variable=word_timestamps_var, text='',
                                              **self.ctk_form_entry_settings)

        # INITIAL PROMPT
        # get the initial prompt setting from the app settings
        initial_prompt = \
            kwargs.get('initial_prompt', None) \
                if kwargs.get('initial_prompt', None) is not None \
                else self.stAI.get_app_setting('transcription_initial_prompt',
                                               default_if_none=" - How are you?\n - I'm fine, thank you.")

        # create the initial prompt variable, label and input
        form_vars['initial_prompt_var'] = \
            initial_prompt_var = tk.StringVar(advanced_frame, value=initial_prompt)
        initial_prompt_label = ctk.CTkLabel(advanced_frame, text='Initial Prompt', **self.ctk_form_label_settings)
        initial_prompt_input = ctk.CTkTextbox(advanced_frame, **self.ctk_form_textbox)
        initial_prompt_input.insert(tk.END, initial_prompt)

        # if the initial prompt input changes, update the initial prompt variable
        def update_initial_prompt(*args):
            initial_prompt_var.set(initial_prompt_input.get('1.0', tk.END))

        initial_prompt_input.bind('<KeyRelease>', update_initial_prompt)

        # TIME INTERVALS
        # only show time intervals if we're not supposed to hide them
        if kwargs.get('show_time_intervals', True):
            # get the time intervals setting from the kwargs if any
            # (we don't need to get them from the app settings because they're unique to each transcription task)
            time_intervals = \
                kwargs.get('time_intervals', None) if kwargs.get('time_intervals', None) is not None else ''

            # create the time intervals variable, label and input
            form_vars['time_intervals_var'] = \
                time_intervals_var = tk.StringVar(advanced_frame, value=time_intervals)
            time_intervals_label = ctk.CTkLabel(advanced_frame, text='Time Intervals', **self.ctk_form_label_settings)
            time_intervals_input = ctk.CTkTextbox(advanced_frame, **self.ctk_form_textbox)
            time_intervals_input.insert(tk.END, time_intervals)

            # we will use this function for the exclude time intervals input validation too
            def time_intervals_are_invalid(name, **validation_kwargs):
                # add this to the form_invalid attribute of the window
                self.add_form_invalid(window_id=validation_kwargs.get('ingest_window_id'), key=name,
                                      **validation_kwargs)

                # style the time interval input as invalid
                self.style_input_as_invalid(
                    input_widget=validation_kwargs.get('input_widget'), label=validation_kwargs.get('label'))

            def time_intervals_are_valid(name, **validation_kwargs):
                # remove this from the form_invalid attribute of the window
                self.remove_form_invalid(window_id=validation_kwargs.get('ingest_window_id'), key=name,
                                         **validation_kwargs)

                # style the time interval input as valid
                self.style_input_as_valid(
                    input_widget=validation_kwargs.get('input_widget'), label=validation_kwargs.get('label'))

            # if the time intervals input changes, update the time intervals variable
            def update_time_intervals(event):
                time_intervals_var.set(time_intervals_input.get('1.0', tk.END))

            time_intervals_input.bind('<KeyRelease>', update_time_intervals)

            # validate when we're leaving the exclude time intervals input
            time_intervals_input.bind(
                '<FocusOut>',
                lambda e, l_time_intervals_var=time_intervals_var, l_kwargs=kwargs:
                self.validate_time_interval_var(name='time_intervals',
                                                var=l_time_intervals_var,
                                                input_widget=time_intervals_input, label=time_intervals_label,
                                                valid_callback=time_intervals_are_valid,
                                                invalid_callback=time_intervals_are_invalid, **l_kwargs)
            )

            # EXCLUDE TIME INTERVALS
            # get the exclude time intervals setting from the kwargs if any
            # (we don't need to get them from the app settings because they're unique to each transcription task)
            excluded_time_intervals = \
                kwargs.get('excluded_time_intervals', None) \
                    if kwargs.get('excluded_time_intervals', None) is not None else ''

            # create the time intervals variable, label and input
            form_vars['excluded_time_intervals_var'] = \
                excluded_time_intervals_var = tk.StringVar(advanced_frame,
                                                           value=excluded_time_intervals)
            excluded_time_intervals_label = ctk.CTkLabel(advanced_frame, text='Exclude Time Intervals',
                                                         **self.ctk_form_label_settings)
            excluded_time_intervals_input = ctk.CTkTextbox(advanced_frame, **self.ctk_form_textbox)
            excluded_time_intervals_input.insert(tk.END, excluded_time_intervals)

            # if the time intervals input changes, update the time intervals variable
            def update_time_intervals(event):
                excluded_time_intervals_var.set(excluded_time_intervals_input.get('1.0', tk.END))

            excluded_time_intervals_input.bind('<KeyRelease>', update_time_intervals)

            # validate when we're leaving the exclude time intervals input
            excluded_time_intervals_input.bind(
                '<FocusOut>',
                lambda e, exclude_time_intervals_var=excluded_time_intervals_var, l_kwargs=kwargs:
                self.validate_time_interval_var(name='excluded_time_intervals',
                                                var=exclude_time_intervals_var,
                                                input_widget=excluded_time_intervals_input,
                                                label=excluded_time_intervals_label,
                                                valid_callback=time_intervals_are_valid,
                                                invalid_callback=time_intervals_are_invalid, **l_kwargs)
            )

        # KEEP DEBUG INFO
        # get the keep debug info setting from the app settings
        keep_whisper_debug_info = \
            kwargs.get('keep_whisper_debug_info', None) \
                if kwargs.get('keep_whisper_debug_info', None) is not None \
                else self.stAI.get_app_setting('keep_whisper_debug_info', default_if_none=False)

        # create the increased time precision variable, label and input
        form_vars['keep_whisper_debug_info_var'] = \
            keep_whisper_debug_info_var = tk.BooleanVar(advanced_frame, value=keep_whisper_debug_info)
        keep_whisper_debug_info_label = ctk.CTkLabel(
            advanced_frame, text='Keep Debug Info', **self.ctk_form_label_settings)
        keep_whisper_debug_info_input = ctk.CTkSwitch(
            advanced_frame, variable=keep_whisper_debug_info_var, text='', **self.ctk_form_entry_settings)

        # POST-PROCESSING OPTIONS
        # max_per_line, max_per_line_unit, split_on_punctuation, prevent_gaps_shorter_than

        # MAX PER LINE
        # instead of creating a max_characters_per_line and a max_words_per_line variable,
        # we will create a single variable that holds either one, to which we add a unit selector (characters or words)
        max_per_line_unit = kwargs.get('transcription_max_per_line_unit', None) \
            if kwargs.get('transcription_max_per_line_unit', None) is not None \
            else self.stAI.get_app_setting('transcription_max_per_line_unit', default_if_none='characters')

        # make sure we're not using an invalid unit
        max_per_line_unit = 'characters' if max_per_line_unit not in ['characters', 'words'] else max_per_line_unit

        form_vars['max_per_line_unit_var'] = \
            max_per_line_unit_var = tk.StringVar(post_frame, value=max_per_line_unit)

        # depending on the unit,
        # we will either fill this variable with the max characters or the max words from the app settings / kwargs
        max_per_line_setting_name = 'transcription_max_words_per_segment' \
            if max_per_line_unit == 'words' else 'transcription_max_chars_per_segment'

        max_per_line = kwargs.get(max_per_line_setting_name, None) \
            if kwargs.get(max_per_line_setting_name, None) is not None \
            else self.stAI.get_app_setting(max_per_line_setting_name, default_if_none='')

        form_vars['max_per_line_var'] = \
            max_per_line_var = tk.StringVar(post_frame, value=max_per_line)
        max_per_line_label = ctk.CTkLabel(post_frame, text='Split lines at', **self.ctk_form_label_settings)

        max_per_line_frame = ctk.CTkFrame(post_frame, **self.ctk_frame_transparent)
        max_per_line_input = ctk.CTkEntry(max_per_line_frame, textvariable=max_per_line_var,
                                          **self.ctk_form_entry_settings_half)
        max_per_line_unit_input = ctk.CTkSegmentedButton(max_per_line_frame, variable=max_per_line_unit_var,
                                                         values=['characters', 'words'], dynamic_resizing=True)
        max_per_line_input.pack(side=ctk.LEFT)
        max_per_line_unit_input.pack(side=ctk.LEFT, **self.ctk_form_paddings)

        # only allow integers in the max_per_line_input
        max_per_line_input.configure(
            validate="key",
            validatecommand=(max_per_line_input.register(self.only_allow_integers), '%P')
        )

        # SPLIT ON PUNCTUATION
        split_on_punctuation = kwargs.get('transcription_split_on_punctuation_marks', None) \
            if kwargs.get('transcription_split_on_punctuation_marks', None) is not None \
            else self.stAI.get_app_setting('transcription_split_on_punctuation_marks', default_if_none=True)

        form_vars['split_on_punctuation_var'] = \
            split_on_punctuation_var = tk.BooleanVar(post_frame,
                                                     value=split_on_punctuation)
        split_on_punctuation_label = ctk.CTkLabel(post_frame, text='Split on punctuation',
                                                  **self.ctk_form_label_settings)
        split_on_punctuation_input = ctk.CTkSwitch(post_frame, variable=split_on_punctuation_var,
                                                   text='', **self.ctk_form_entry_settings)

        # CUSTOM PUNCTUATION MARKS
        # only show this if split_on_punctuation is True
        if kwargs.get('show_custom_punctuation_marks', False):
            custom_punctuation_marks_str = \
                kwargs.get('transcription_custom_punctuation_marks', None) \
                    if kwargs.get('transcription_custom_punctuation_marks', None) is not None \
                    else self.stAI.get_app_setting('transcription_custom_punctuation_marks',
                                                   default_if_none=['.', '!', '?', '…'])

            # convert the list to a string with spaces between the punctuation marks
            custom_punctuation_marks_str = ' '.join(custom_punctuation_marks_str)

            form_vars['transcription_custom_punctuation_marks_var'] = \
                transcription_custom_punctuation_marks = tk.StringVar(post_frame,
                                                                      value=custom_punctuation_marks_str)

            custom_punctuation_marks_label = ctk.CTkLabel(post_frame, text='Custom punctuation marks',
                                                          **self.ctk_form_label_settings)
            custom_punctuation_marks_input = ctk.CTkEntry(post_frame,
                                                          textvariable=transcription_custom_punctuation_marks,
                                                          **self.ctk_form_entry_settings)

        # PREVENT GAPS SHORTER THAN
        prevent_gaps_shorter_than = kwargs.get('transcription_prevent_short_gaps', None) \
            if kwargs.get('transcription_prevent_short_gaps', None) is not None \
            else self.stAI.get_app_setting('transcription_prevent_short_gaps', default_if_none='')

        form_vars['prevent_gaps_shorter_than_var'] = \
            prevent_gaps_shorter_than_var = tk.StringVar(post_frame,
                                                         value=prevent_gaps_shorter_than)
        prevent_gaps_shorter_than_label = ctk.CTkLabel(post_frame, text='Prevent gaps shorter than',
                                                       **self.ctk_form_label_settings)

        prevent_gaps_shorter_than_frame = ctk.CTkFrame(post_frame, **self.ctk_frame_transparent)
        prevent_gaps_shorter_than_input = ctk.CTkEntry(prevent_gaps_shorter_than_frame,
                                                       textvariable=prevent_gaps_shorter_than_var,
                                                       **self.ctk_form_entry_settings_half)
        prevent_gaps_shorter_than_unit_label = ctk.CTkLabel(prevent_gaps_shorter_than_frame, text='seconds')
        prevent_gaps_shorter_than_input.pack(side=ctk.LEFT)
        prevent_gaps_shorter_than_unit_label.pack(side=ctk.LEFT, **self.ctk_form_paddings)

        # only allow floats in the prevent_gaps_shorter_than_input
        prevent_gaps_shorter_than_input.configure(
            validate="key",
            validatecommand=(prevent_gaps_shorter_than_input.register(self.only_allow_floats), '%P')
        )

        # if word_timestamps_var is False, disable the max words per segment and max chars per segment inputs
        # but check on every change of the word_timestamps_var
        def update_max_per_segment_inputs_visibility(*f_args):

            if word_timestamps_var.get():
                max_per_line_label.grid()
                max_per_line_frame.grid()
                split_on_punctuation_input.grid()
                split_on_punctuation_label.grid()
            else:
                max_per_line_label.grid_remove()
                max_per_line_frame.grid_remove()
                split_on_punctuation_input.grid_remove()
                split_on_punctuation_label.grid_remove()

        word_timestamps_var.trace('w', update_max_per_segment_inputs_visibility)

        # if transcription_speaker_detection_var is False, disable the speaker detection threshold input
        # but check on every change of the transcription_speaker_detection_var
        def update_speaker_detection_threshold_inputs_visibility(*f_args):

            if transcription_speaker_detection_var.get():
                transcription_speaker_detection_threshold_label.grid()
                transcription_speaker_detection_threshold_input.grid()
            else:
                transcription_speaker_detection_threshold_label.grid_remove()
                transcription_speaker_detection_threshold_input.grid_remove()

        transcription_speaker_detection_var.trace('w', update_speaker_detection_threshold_inputs_visibility)

        # ENABLE/DISABLE function
        def update_transcription_enabled(*f_args):

            # enable all the elements in the audio tab
            if transcription_enabled_var.get():
                # basic_frame_label.grid()
                basic_frame.grid()
                advanced_frame_label.grid()
                advanced_frame.grid()
                post_frame_label.grid()
                post_frame.grid()

            # disable all the elements in the audio tab
            else:
                # basic_frame_label.grid_remove()
                basic_frame.grid_remove()
                advanced_frame_label.grid_remove()
                advanced_frame.grid_remove()
                post_frame_label.grid_remove()
                post_frame.grid_remove()

        # add enable/disable function to the transcription_enabled_var
        transcription_enabled_var.trace('w', update_transcription_enabled)
        update_transcription_enabled()

        # Adding all the elements to THE GRID:

        # ENABLE/DISABLE FRAME GRID
        transcription_enabled_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        transcription_enabled_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)

        # BASIC SETTINGS FRAME GRID add all the elements to the grid of the basic frame
        # add all elements to the grid of the basic frame
        source_language_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        source_language_input.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)
        task_label.grid(row=3, column=0, sticky="w", **self.ctk_form_paddings)
        task_entry.grid(row=3, column=1, sticky="w", **self.ctk_form_paddings)
        model_name_label.grid(row=4, column=0, sticky="w", **self.ctk_form_paddings)
        model_name_input.grid(row=4, column=1, sticky="w", **self.ctk_form_paddings)

        # SPEAKERS FRAME GRID
        # add all elements to the grid of the speakers frame
        transcription_speaker_detection_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        transcription_speaker_detection_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)
        transcription_speaker_detection_threshold_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        transcription_speaker_detection_threshold_input.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)

        # ADVANCED SETTINGS FRAME GRID
        # add all elements to the grid of the advanced options frame
        device_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        device_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)
        pre_detect_speech_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        pre_detect_speech_input.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)
        word_timestamps_label.grid(row=3, column=0, sticky="w", **self.ctk_form_paddings)
        word_timestamps_input.grid(row=3, column=1, sticky="w", **self.ctk_form_paddings)
        initial_prompt_label.grid(row=4, column=0, sticky="w", **self.ctk_form_paddings)
        initial_prompt_input.grid(row=4, column=1, sticky="w", **self.ctk_form_paddings)

        # don't show the time intervals if hide_time_intervals is True
        if kwargs.get('show_time_intervals', True):
            time_intervals_label.grid(row=5, column=0, sticky="w", **self.ctk_form_paddings)
            time_intervals_input.grid(row=5, column=1, sticky="w", **self.ctk_form_paddings)
            excluded_time_intervals_label.grid(row=6, column=0, sticky="w", **self.ctk_form_paddings)
            excluded_time_intervals_input.grid(row=6, column=1, sticky="w", **self.ctk_form_paddings)

        keep_whisper_debug_info_label.grid(row=7, column=0, sticky="w", **self.ctk_form_paddings)
        keep_whisper_debug_info_input.grid(row=7, column=1, sticky="w", **self.ctk_form_paddings)

        # POST PROCESSING FRAME GRID
        # add all elements to the grid of the post processing frame
        max_per_line_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        max_per_line_frame.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)
        split_on_punctuation_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        split_on_punctuation_input.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)

        if kwargs.get('show_custom_punctuation_marks', False):
            custom_punctuation_marks_label.grid(row=3, column=0, sticky="w", **self.ctk_form_paddings)
            custom_punctuation_marks_input.grid(row=3, column=1, sticky="w", **self.ctk_form_paddings)

        prevent_gaps_shorter_than_label.grid(row=4, column=0, sticky="w", **self.ctk_form_paddings)
        prevent_gaps_shorter_than_frame.grid(row=4, column=1, sticky="w", **self.ctk_form_paddings)

        update_max_per_segment_inputs_visibility()
        update_speaker_detection_threshold_inputs_visibility()

        # return all the gathered form variables
        return form_vars

    @staticmethod
    def form_to_video_indexing_settings(**kwargs):
        """
        This function takes the form variables and gets them into the video indexing settings
        """

        form_vars = kwargs.get('form_vars', None)
        video_form_vars = form_vars.get('video_form_vars', None)

        # if video indexing is not enabled, return None
        if video_form_vars.get('video_indexing_enabled_var', None) \
                and not video_form_vars.get('video_indexing_enabled_var').get():
            return None

        indexing_settings = dict()

        # first, the non-video indexing specific settings
        indexing_settings['queue_id'] = kwargs.get('queue_id', None)
        indexing_settings['timeline_name'] = kwargs.get('timeline_name', None)
        indexing_settings['project_name'] = kwargs.get('project_name', None)

        # if we have a transcription_file_path, pass it
        # but if we're also transcribing the video, then this will be ignored and that transcription will be used
        indexing_settings['transcription_file_path'] = kwargs.get('transcription_file_path', None)

        # then, the video indexing specific settings
        indexing_settings['video_file_path'] = kwargs.get('file_path', None)

        # create the indexing options dict if it doesn't exist
        # this will be passed to the index_video() function
        if 'indexing_options' not in indexing_settings:
            indexing_settings['indexing_options'] = dict()

        # this tells the indexing function to either use
        # the first frame in the scene or the sharpest it can find until the scene changes
        index_candidate = video_form_vars['video_indexing_index_candidate_var'].get()

        if index_candidate == 'the first frame':
            indexing_settings['indexing_options']['prefer_sharp'] = False
        else:
            indexing_settings['indexing_options']['prefer_sharp'] = True

        # this tells the indexing function to either skip color blocks or not
        indexing_settings['indexing_options']['skip_color_blocks'] = \
            video_form_vars['video_indexing_skip_color_blocks_var'].get() \
            if 'video_indexing_skip_color_blocks_var' in video_form_vars else True

        # this tells the indexing function to either skip similar neighbors or not
        indexing_settings['indexing_options']['skip_similar_neighbors'] = \
            video_form_vars['video_indexing_skip_similar_neighbors_var'].get() \
            if 'video_indexing_skip_similar_neighbors_var' in video_form_vars else True

        # this sets the patch_divider for the indexing function depending on what kind of attention we're using
        attention_type = video_form_vars['video_indexing_attention_type_var'].get() \
            if 'video_indexing_attention_type_var' in video_form_vars else None

        # if we want to focus on details, we need to split the picture into more patches
        # this is useful for frames with a lot of content
        if attention_type == 'details':
            indexing_settings['indexing_options']['patch_divider'] = 3.9

        # if we want to focus on the big picture, we need to split the picture into less patches
        # this is useful if we're searching the general content of frames
        # - that usually occupies a big portion of the frame
        elif attention_type == 'big picture':
            indexing_settings['indexing_options']['patch_divider'] = 1

        # otherwise find a middle ground
        else:
            indexing_settings['indexing_options']['patch_divider'] = 1.9

        # create the detection options dict if it doesn't exist
        # this will be passed to the index_video() function
        if 'detection_options' not in indexing_settings:
            indexing_settings['detection_options'] = dict()

        # how often do we want to check the content of the scene when detecting scenes?
        indexing_settings['detection_options']['content_analysis_every'] = \
            video_form_vars['scene_detection_content_analysis_var'].get() \
            if 'scene_detection_content_analysis_var' in video_form_vars else 40

        # use the expected_frequency to set the jump_every_frames ('low' - 40, 'medium' - 20, 'high' - 10)
        expected_frequency = video_form_vars['scene_detection_expected_frequency_var'].get() \
            if 'scene_detection_expected_frequency_var' in video_form_vars else 'medium'

        if expected_frequency == 'low':
            indexing_settings['detection_options']['jump_every_frames'] = 40
        elif expected_frequency == 'high':
            indexing_settings['detection_options']['jump_every_frames'] = 10
        else:
            indexing_settings['detection_options']['jump_every_frames'] = 20

        return indexing_settings

    def form_to_transcription_settings(self, **kwargs):
        """
        This function takes the form variables and gets them into the transcription settings
        :param: form_audio_vars: the form variables (a dict of tkinter variables)
        :param: kwargs: additional keyword arguments
        :return: transcription_settings: the transcription settings formatted for add_transcription_to_queue function
        """

        form_vars = kwargs.get('form_vars', None)

        audio_form_vars = form_vars.get('audio_form_vars', None)
        analysis_form_vars = form_vars.get('analysis_form_vars', None)

        if audio_form_vars.get('transcription_enabled_var', None) \
                and not audio_form_vars.get('transcription_enabled_var').get():
            return None

        transcription_settings = dict()

        # first, the non-transcription specific settings
        transcription_settings['queue_id'] = kwargs.get('queue_id', None)
        transcription_settings['timeline_name'] = kwargs.get('timeline_name', None)
        transcription_settings['project_name'] = kwargs.get('project_name', None)

        # if we have a transcription_file_path, pass it
        transcription_settings['transcription_file_path'] = kwargs.get('transcription_file_path', None)

        # retranscribe or not
        transcription_settings['retranscribe'] = kwargs.get('retranscribe', False)

        # then, the transcription specific settings
        transcription_settings['audio_file_path'] = kwargs.get('file_path', None)
        transcription_settings['transcription_task'] = audio_form_vars['transcription_task_var'].get()
        transcription_settings['model_name'] = audio_form_vars['model_name_var'].get()
        transcription_settings['device'] = audio_form_vars['device_var'].get()
        transcription_settings['pre_detect_speech'] = audio_form_vars['pre_detect_speech_var'].get()

        # speaker detection and threshold
        transcription_settings['transcription_speaker_detection'] = \
            audio_form_vars['transcription_speaker_detection_var'].get()

        # validate the speaker detection threshold if speaker detection is enabled
        if transcription_settings['transcription_speaker_detection']:

            transcription_speaker_detection_threshold = \
                float(audio_form_vars['transcription_speaker_detection_threshold_var'].get())

            # use the default threshold if the user didn't input anything
            # also, only allow values between 0 and 1
            if not 0 < transcription_speaker_detection_threshold <= 1:
                transcription_speaker_detection_threshold = \
                    self.stAI.get_app_setting('transcription_speaker_detection_threshold', default_if_none=0.3)

                logger.warning('The speaker detection threshold must be between 0 and 1. Using default value {}.'
                               .format(transcription_speaker_detection_threshold))

            transcription_settings['transcription_speaker_detection_threshold'] = \
                transcription_speaker_detection_threshold

        # choose between max words or characters per line
        if audio_form_vars['max_per_line_unit_var'].get() == 'words':
            transcription_settings['max_words_per_segment'] = audio_form_vars['max_per_line_var'].get()
        else:
            transcription_settings['max_chars_per_segment'] = audio_form_vars['max_per_line_var'].get()

        transcription_settings['split_on_punctuation_marks'] = audio_form_vars['split_on_punctuation_var'].get()
        transcription_settings['prevent_short_gaps'] = audio_form_vars['prevent_gaps_shorter_than_var'].get()
        transcription_settings['time_intervals'] = audio_form_vars['time_intervals_var'].get()
        transcription_settings['excluded_time_intervals'] = audio_form_vars['excluded_time_intervals_var'].get()

        # validate the time intervals
        transcription_settings['time_intervals'] = \
            self.convert_text_to_time_intervals(transcription_settings['time_intervals'],
                                                transcription_file_path= \
                                                    kwargs.get('transcription_file_path', None),
                                                window_id=kwargs.get('ingest_window_id'),
                                                pop_error=True
                                                )

        if not transcription_settings['time_intervals']:
            return False

        # validate the excluded time intervals
        transcription_settings['excluded_time_intervals'] = \
            self.convert_text_to_time_intervals(transcription_settings['excluded_time_intervals'],
                                                transcription_file_path= \
                                                    kwargs.get('transcription_file_path', None),
                                                window_id=kwargs.get('ingest_window_id'),
                                                pop_error=True
                                                )

        if not transcription_settings['excluded_time_intervals']:
            return False

        transcription_settings['keep_whisper_debug_info'] = audio_form_vars['keep_whisper_debug_info_var'].get()

        # the whisper options
        transcription_settings['whisper_options'] = dict()
        transcription_settings['whisper_options']['language'] = audio_form_vars['source_language_var'].get()
        transcription_settings['whisper_options']['initial_prompt'] = audio_form_vars['initial_prompt_var'].get()
        transcription_settings['whisper_options']['word_timestamps'] = audio_form_vars['word_timestamps_var'].get()

        # some options from the analysis form that
        transcription_settings['transcription_group_questions'] = analysis_form_vars['group_questions_var'].get()

        return transcription_settings

    def add_ingest_video_form_elements(self, parent: tk.Widget, **kwargs) -> dict or None:
        """
        This function adds the form elements for the analysis window
        """

        # create the frames
        enable_disable_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        video_indexing_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)
        scene_detection_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)

        # create labels for the frames (and style them according to the theme)
        video_indexing_label = ctk.CTkLabel(parent, text='Video Indexing', **self.ctk_frame_label_settings)
        scene_detection_label = ctk.CTkLabel(parent, text='Scene Detection', **self.ctk_frame_label_settings)

        # we're going to create the form_vars dict to store all the variables
        # we will use this dict at the end of the function to gather all the created tk variables
        form_vars = {}

        # get the last grid row for the parent
        l_row = parent.grid_size()[1]

        # add the labels and frames to the parent
        video_indexing_label.grid(row=l_row + 1, column=0, sticky="ew", **self.ctk_frame_paddings)
        enable_disable_frame.grid(row=l_row + 2, column=0, sticky="ew", **self.ctk_frame_paddings)
        video_indexing_frame.grid(row=l_row + 3, column=0, sticky="ew", **self.ctk_frame_paddings)
        scene_detection_label.grid(row=l_row + 4, column=0, sticky="ew", **self.ctk_frame_paddings)
        scene_detection_frame.grid(row=l_row + 5, column=0, sticky="ew", **self.ctk_frame_paddings)

        # make the column expandable
        parent.columnconfigure(0, weight=1)
        enable_disable_frame.columnconfigure(1, weight=1)
        video_indexing_frame.columnconfigure(1, weight=1)

        # VIDEO INDEXING ENABLE SWITCH
        video_indexing_enabled = kwargs.get('video_indexing_enabled', None) \
            if kwargs.get('video_indexing_enabled', None) is not None \
            else self.stAI.get_app_setting('video_indexing_enabled', default_if_none=True)

        form_vars['video_indexing_enabled_var'] = \
            video_indexing_enabled_var = tk.BooleanVar(enable_disable_frame,
                                                     value=video_indexing_enabled)
        video_indexing_enabled_label = ctk.CTkLabel(enable_disable_frame, text='Index Video',
                                                  **self.ctk_form_label_settings)
        video_indexing_enabled_input = ctk.CTkSwitch(enable_disable_frame, variable=video_indexing_enabled_var,
                                                   text='', **self.ctk_form_entry_settings)


        # Focus: fine details, details, balanced, big picture
        # Index:  / first frame ... in scene
        # Index color-block frames: switch
        # Skip neighbors with similar content

        # THE ATTENTION
        attention_type = \
            kwargs.get('video_indexing_attention_type', None) \
                if kwargs.get('video_indexing_attention_type', None) is not None \
                else self.stAI.get_app_setting('video_indexing_attention_type', default_if_none='balanced')

        form_vars['video_indexing_attention_type_var'] = \
            video_indexing_attention_type_var = tk.StringVar(video_indexing_frame, value=attention_type)

        video_indexing_attention_type_label = ctk.CTkLabel(
            video_indexing_frame, text='Attention Type', **self.ctk_form_label_settings)
        video_indexing_attention_type_input = ctk.CTkSegmentedButton(
            video_indexing_frame, variable=video_indexing_attention_type_var,
            values=['details', 'balanced'], dynamic_resizing=True)
            #values=['details', 'balanced', 'big picture'], dynamic_resizing=True)

        # THE FRAME SELECTION
        video_indexing_index_candidate = \
            kwargs.get('video_indexing_index_candidate', None) \
                if kwargs.get('video_indexing_index_candidate', None) is not None \
                else self.stAI.get_app_setting('video_indexing_index_candidate', default_if_none='sharp')

        if video_indexing_index_candidate == 'first':
            video_indexing_index_candidate = 'the first frame'
        else:
            video_indexing_index_candidate = 'a sharper frame'

        form_vars['video_indexing_index_candidate_var'] = \
            video_indexing_index_candidate_var = tk.StringVar(video_indexing_frame,
                                                              value=video_indexing_index_candidate)

        video_indexing_index_candidate_label = \
            ctk.CTkLabel(video_indexing_frame, text='Index Candidate', **self.ctk_form_label_settings)
        video_indexing_index_candidate_input = \
            ctk.CTkSegmentedButton(
                video_indexing_frame, variable=video_indexing_index_candidate_var,
                values=['a sharper frame', 'the first frame'], dynamic_resizing=True)

        # SKIP SINGLE COLOR FRAMES
        video_indexing_skip_color_blocks = kwargs.get('video_indexing_skip_color_blocks', None) \
            if kwargs.get('video_indexing_skip_color_blocks', None) is not None \
            else self.stAI.get_app_setting('video_indexing_skip_color_blocks', default_if_none=True)

        form_vars['video_indexing_skip_color_blocks_var'] = \
            video_indexing_skip_color_blocks_var = tk.BooleanVar(video_indexing_frame,
                                                     value=video_indexing_skip_color_blocks)
        video_indexing_color_block_label = ctk.CTkLabel(video_indexing_frame, text='Skip Single Color Frames',
                                                  **self.ctk_form_label_settings)
        video_indexing_color_block_input = ctk.CTkSwitch(video_indexing_frame,
                                                         variable=video_indexing_skip_color_blocks_var,
                                                   text='', **self.ctk_form_entry_settings)

        # SKIP SIMILAR NEIGHBORS
        video_indexing_skip_similar_neighbors = kwargs.get('video_indexing_skip_similar_neighbors', None) \
            if kwargs.get('video_indexing_skip_similar_neighbors', None) is not None \
            else self.stAI.get_app_setting('video_indexing_skip_similar_neighbors', default_if_none=True)

        form_vars['video_indexing_skip_similar_neighbors_var'] = \
            video_indexing_skip_similar_neighbors_var = tk.BooleanVar(video_indexing_frame,
                                                        value=video_indexing_skip_similar_neighbors)

        video_indexing_skip_similar_neighbors_label = \
            ctk.CTkLabel(video_indexing_frame, text='Skip Similar Neighbors', **self.ctk_form_label_settings)
        video_indexing_skip_similar_neighbors_input = \
            ctk.CTkSwitch(video_indexing_frame, variable=video_indexing_skip_similar_neighbors_var,
                                                    text='', **self.ctk_form_entry_settings)


        # SCENE DETECTION TAB

        # EXPECTED SHOT CHANGE FREQUENCY
        scene_detection_expected_frequency = \
            kwargs.get('scene_detection_expected_frequency', None) \
                if kwargs.get('scene_detection_expected_frequency', None) is not None \
                else self.stAI.get_app_setting('scene_detection_expected_frequency', default_if_none='medium')

        form_vars['scene_detection_expected_frequency_var'] = \
            scene_detection_expected_frequency_var = tk.StringVar(scene_detection_frame,
                                                                     value=scene_detection_expected_frequency)

        scene_detection_expected_frequency_label = \
            ctk.CTkLabel(scene_detection_frame, text='Expected Shot Frequency',
                            **self.ctk_form_label_settings)

        scene_detection_expected_frequency_input = \
            ctk.CTkSegmentedButton(scene_detection_frame, variable=scene_detection_expected_frequency_var,

                                      values=['low', 'medium', 'high'], dynamic_resizing=True)

        # CONTENT ANALYSIS
        scene_detection_content_analysis = \
            kwargs.get('scene_detection_content_analysis', None) \
                if kwargs.get('scene_detection_content_analysis', None) is not None \
                else self.stAI.get_app_setting('scene_detection_content_analysis', default_if_none=40)

        form_vars['scene_detection_content_analysis_var'] = \
            scene_detection_content_analysis_var = tk.IntVar(scene_detection_frame,
                                                                value=scene_detection_content_analysis)

        scene_detection_content_analysis_label = \
            ctk.CTkLabel(scene_detection_frame, text='Analyze Scenes',
                            **self.ctk_form_label_settings)

        scene_detection_content_analysis_frame = ctk.CTkFrame(scene_detection_frame, **self.ctk_frame_transparent)

        scene_detection_content_analysis_unit_label1 = \
            ctk.CTkLabel(scene_detection_content_analysis_frame, text='every')

        scene_detection_content_analysis_input = \
            ctk.CTkEntry(scene_detection_content_analysis_frame, textvariable=scene_detection_content_analysis_var,
                         **self.ctk_form_entry_settings_half)

        scene_detection_content_analysis_unit_label2 = \
            ctk.CTkLabel(scene_detection_content_analysis_frame, text='frames')

        scene_detection_content_analysis_unit_label1.pack(side=ctk.LEFT)
        scene_detection_content_analysis_input.pack(side=ctk.LEFT, **self.ctk_form_paddings)
        scene_detection_content_analysis_unit_label2.pack(side=ctk.LEFT)

        # only allow integers in the scene_detection_content_analysis_input
        scene_detection_content_analysis_input.configure(
            validate="key",
            validatecommand=(scene_detection_content_analysis_input.register(self.only_allow_integers_non_null), '%P')
        )















        # THE MODEL DROPDOWN
        # get the available models from ClipIndex, and the default model from the app settings
        # model_selected = \
        #     kwargs.get('clip_model_name', None) \
        #         if kwargs.get('clip_model_name', None) is not None \
        #         else self.stAI.get_app_setting('clip_model_name', default_if_none='RN50x4')

        # create the model variable, label and input
        # form_vars['clip_model_name_var'] = \
        #     model_name_var = tk.StringVar(video_indexing_frame, value=model_selected)
        # model_name_label = ctk.CTkLabel(video_indexing_frame, text='Model', **self.ctk_form_label_settings)
        # model_name_input = ctk.CTkOptionMenu(video_indexing_frame, variable=model_name_var,
        #                                      values=ClipIndex.get_available_clip_models(),
        #                                      **self.ctk_form_entry_settings)

        # THE SHOT CHANGE SENSITIVITY
        # get the available models from ClipIndex, and the default model from the app settings
        # shot_change_sensitivity = \
        #     kwargs.get('clip_shot_change_sensitivity', None) \
        #         if kwargs.get('clip_shot_change_sensitivity', None) is not None \
        #         else self.stAI.get_app_setting('clip_shot_change_sensitivity', default_if_none=13)

        # convert the sensitivity to a value between 0 and 100
        # shot_change_sensitivity = 100 - int(shot_change_sensitivity * 100 / 255)

        # create the variable, label and input
        # form_vars['clip_shot_change_sensitivity_var'] = \
        #     sensitivity_var = tk.IntVar(video_indexing_frame, value=shot_change_sensitivity)
        # sensitivity_label \
        #     = ctk.CTkLabel(video_indexing_frame, text='Shot Change Sensitivity', **self.ctk_form_label_settings)

        # sensitivity_input_frame = ctk.CTkFrame(video_indexing_frame, **self.ctk_frame_transparent)

        # sensitivity_input \
        #     = ctk.CTkSlider(sensitivity_input_frame, from_=10, to=100, number_of_steps=18, variable=sensitivity_var,
        #                     **self.ctk_form_entry_settings)
        # sensitivity_slider_value \
        #     = ctk.CTkLabel(sensitivity_input_frame, textvariable=sensitivity_var, **self.ctk_form_label_settings)

        # sensitivity_input.pack(side=ctk.LEFT)
        # sensitivity_slider_value.pack(side=ctk.LEFT, **self.ctk_form_paddings)

        # ENABLE/DISABLE function
        def update_video_indexing_enabled(*f_args):

            # enable all the elements in the audio tab
            if video_indexing_enabled_var.get():
                # video_indexing_label.grid()
                video_indexing_frame.grid()
                scene_detection_label.grid()
                scene_detection_frame.grid()

            # disable all the elements in the audio tab
            else:
                # video_indexing_label.grid_remove()
                video_indexing_frame.grid_remove()
                scene_detection_label.grid_remove()
                scene_detection_frame.grid_remove()

        # add enable/disable function to the transcription_enabled_var
        video_indexing_enabled_var.trace('w', update_video_indexing_enabled)
        update_video_indexing_enabled()

        # Adding all the elemente to the grid

        # ENABLE/DISABLE FRAME GRID
        video_indexing_enabled_label.grid(row=0, column=0, sticky="w", **self.ctk_form_paddings)
        video_indexing_enabled_input.grid(row=0, column=1, sticky="w", **self.ctk_form_paddings)


        # VIDEO INDEXING GRID
        video_indexing_attention_type_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        video_indexing_attention_type_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)
        video_indexing_index_candidate_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        video_indexing_index_candidate_input.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)
        video_indexing_color_block_label.grid(row=3, column=0, sticky="w", **self.ctk_form_paddings)
        video_indexing_color_block_input.grid(row=3, column=1, sticky="w", **self.ctk_form_paddings)
        video_indexing_skip_similar_neighbors_label.grid(row=4, column=0, sticky="w", **self.ctk_form_paddings)
        video_indexing_skip_similar_neighbors_input.grid(row=4, column=1, sticky="w", **self.ctk_form_paddings)

        # SCENE DETECTION GRID
        scene_detection_expected_frequency_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        scene_detection_expected_frequency_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)
        scene_detection_content_analysis_label.grid(row=2, column=0, sticky="w", **self.ctk_form_paddings)
        scene_detection_content_analysis_frame.grid(row=2, column=1, sticky="w", **self.ctk_form_paddings)

        return form_vars

    def add_analysis_form_elements(self, parent: tk.Widget, **kwargs) -> dict or None:
        """
        This function adds the form elements for the analysis window
        """

        # create the frames
        speech_analysis_frame = ctk.CTkFrame(parent, **self.ctk_frame_transparent)

        # create labels for the frames (and style them according to the theme)
        speech_analysis_label = ctk.CTkLabel(parent, text='Speech Analysis', **self.ctk_frame_label_settings)

        # we're going to create the form_vars dict to store all the variables
        # we will use this dict at the end of the function to gather all the created tk variables
        form_vars = {}

        # get the last grid row for the parent
        l_row = parent.grid_size()[1]

        # add the labels and frames to the parent
        speech_analysis_label.grid(row=l_row + 1, column=0, sticky="ew", **self.ctk_frame_paddings)
        speech_analysis_frame.grid(row=l_row + 2, column=0, sticky="ew", **self.ctk_frame_paddings)

        # make the column expandable
        parent.columnconfigure(0, weight=1)
        speech_analysis_frame.columnconfigure(1, weight=1)

        # GROUP QUESTIONS
        # get the group questions setting from the app settings
        group_questions = \
            kwargs.get('group_questions', None) \
                if kwargs.get('group_questions', None) is not None \
                else self.stAI.get_app_setting('transcription_group_questions', default_if_none=False)

        # create the pre-detect speech variable, label and input
        form_vars['group_questions_var'] = \
            group_questions_var = tk.BooleanVar(speech_analysis_frame, value=group_questions)
        group_questions_label = ctk.CTkLabel(speech_analysis_frame, text='Group Questions',
                                             **self.ctk_form_label_settings)
        group_questions_input = ctk.CTkSwitch(speech_analysis_frame,
                                              variable=group_questions_var,
                                              text='',
                                              **self.ctk_form_entry_settings)

        # Adding all the elemente to the grid

        # TEXT ANALYSIS FRAME GRID
        group_questions_label.grid(row=1, column=0, sticky="w", **self.ctk_form_paddings)
        group_questions_input.grid(row=1, column=1, sticky="w", **self.ctk_form_paddings)

        return form_vars

    def button_start_ingest(self, **kwargs):
        """
        This function is called when the user clicks the start ingest button
        and basically takes all the form variables and passes it to the ingest function
        """

        ingest_window_id = kwargs.get('ingest_window_id', None)
        form_vars = kwargs.get('form_vars', None)
        queue_id = kwargs.get('queue_id', None)

        # check if the form is valid before proceeding
        if not self.is_form_valid(window_id=ingest_window_id):
            logger.debug("Failed form validation. Cannot proceed with ingest.")

            # focus back on the window
            self.focus_window(window_id=ingest_window_id)

            return False

        # validate the file path(s)
        file_paths = self.validate_files_or_folders_path(path=form_vars['file_path_var'].get())

        # the file path should be a list of file paths
        if not isinstance(file_paths, list) or len(file_paths) == 0:
            logger.error('No file paths found in the ingest call. Aborting ingest.')
            return False

        # convert the audio form variables to transcription settings
        transcription_settings = self.form_to_transcription_settings(**kwargs)

        # convert the video form variables to video indexing settings
        video_indexing_settings = self.form_to_video_indexing_settings(**kwargs)

        if transcription_settings is None and video_indexing_settings is None:
            self.notify_via_messagebox(type='warning',
                                       message='Both transcription and video indexing are disabled. '
                                               'Enable one of them to proceed.',
                                       message_log='Nothing to send to queue ' \
                                                   '- both transcription and video indexing are disabled.',
                                       parent=self.get_window_by_id(ingest_window_id)
            )
            return False

        # add the transcription job(s) to the queue
        if self.toolkit_ops_obj.add_media_to_queue(source_file_paths=file_paths, queue_id=queue_id,
                                                   video_indexing_settings=video_indexing_settings,
                                                   transcription_settings=transcription_settings):

            # if we reached this point safely, just open the queue window
            self.open_queue_window()

            # close the ingest window
            self.destroy_window_(windows_dict=self.windows, window_id=ingest_window_id)

        # if this returns false, it means that there are no files to ingest
        else:
            self.notify_via_messagebox(type='warning',
                                       message='Cannot start ingest. See log for more details. ',
                                       parent=self.get_window_by_id(ingest_window_id)
                                       )

        return

    def button_cancel_ingest(self, window_id, queue_id, parent_element=None, dont_ask=False):

        if dont_ask or messagebox.askyesno(
                title="Cancel Ingest",
                message='Are you sure you want to cancel?',
                parent=self.windows[window_id]
        ):

            if queue_id is not None:
                self.toolkit_ops_obj.processing_queue.update_queue_item(queue_id=queue_id, status='canceled')

            # call the default destroy window function
            self.destroy_window_(windows_dict=self.windows, window_id=window_id)

            return True

        return False

    def style_input_as_invalid(self, input_widget=None, label: ctk.CTkLabel = None, **kwargs):
        """
        This function styles the entry and the label as invalid
        """

        if input_widget is not None:
            # change the input color to the error color
            try:
                input_widget.configure(fg_color=self.theme_colors['error'])
            except tk.TclError:
                pass

        if label is not None:
            # revert the style of the label to the theme default
            try:
                label.configure(text_color=self.theme_colors['error_text'])
            except tk.TclError:
                pass

    def style_input_as_valid(self, input_widget=None, label: ctk.CTkLabel = None, **kwargs):
        """
        This function reverts the style of the entry and the label to the theme default
        """

        if input_widget is not None and input_widget.winfo_exists():
            # get the instance type of the input
            input_type = type(input_widget).__name__

            # revert the style of the input to the theme default
            try:
                input_widget.configure(fg_color=ctk.ThemeManager.theme[input_type]["fg_color"])

            # this seems to throw an invalid command name error
            # likely because the window and the widgets were destroyed before reaching this
            # since it's not crucial, we'll just pass
            except tk.TclError:
                pass

        if label is not None and label.winfo_exists():
            # revert the style of the label to the theme default
            try:
                label.configure(text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])

            # same as above
            except tk.TclError:
                pass

    def is_form_valid(self, window_id: str, **kwargs):
        """
        This checks the form_invalid attribute of the window and returns True if it's False
        If the window has no form_invalid attribute, it returns True
        """

        # if the window doesn't exist, return None
        if window_id not in self.windows:
            return None

        # if the window has a form_invalid attribute check and it's not empty, return False
        if hasattr(self.windows[window_id], 'form_invalid') \
                and len(self.windows[window_id].form_invalid) > 0:

            # deactivate the start button if it exists
            if kwargs.get('start_button') is not None:
                start_button = kwargs.get('start_button')
                start_button.configure(state='disabled')

            return False

        # otherwise, it means the form is valid

        # deactivate the start button if it exists
        if kwargs.get('start_button') is not None:
            start_button = kwargs.get('start_button')
            start_button.configure(state='normal')

        return True

    def add_form_invalid(self, window_id: str, key: str, **kwargs):
        """
        This updates the form_invalid attribute of the window
        """

        # if the window doesn't exist, return None
        if window_id not in self.windows:
            return None

        # if the window doesn't have a form_invalid attribute, create it
        if not hasattr(self.windows[window_id], 'form_invalid'):
            self.windows[window_id].form_invalid = []

        # append the form_invalid attribute with the passed key
        if key not in self.windows[window_id].form_invalid:
            self.windows[window_id].form_invalid.append(key)

        # do a validation check to potentially change the start button state
        self.is_form_valid(window_id=window_id, **kwargs)

    def remove_form_invalid(self, window_id: str, key: str, **kwargs):

        # if the window doesn't exist, return None
        if window_id not in self.windows:
            return None

        # if the window doesn't have a form_invalid attribute, create it
        if not hasattr(self.windows[window_id], 'form_invalid'):
            self.windows[window_id].form_invalid = []

        # get the current form_invalid attribute
        current_form_invalid = self.windows[window_id].form_invalid

        # if the key is in the form_invalid attribute, remove it
        if key in current_form_invalid:
            current_form_invalid.remove(key)

        # update the form_invalid attribute
        self.windows[window_id].form_invalid = current_form_invalid

        # do a validation check to potentially change the start button state
        self.is_form_valid(window_id=window_id, **kwargs)

    def button_ingest(self, target_files=None, transcription_task='transcribe', **kwargs):
        """
        This prompts the user for a file path and opens the ingest window
        """

        # this ensures that we show the ingest window
        # and simply use the default settings (selected from Preferences window)
        if self.stAI.get_app_setting('ingest_skip_settings', default_if_none=False):
            kwargs['skip_settings'] = True

        # ask the user for the target files if none were passed
        if target_files is None:
            target_files = self.ask_for_file_or_dir_for_var(self.root,
                                                            select_dir=kwargs.get('select_dir'),
                                                            multiple=True)

        # add it to the transcription list
        if target_files:

            # a unique id is also useful to keep track
            if 'queue_id' not in kwargs:
                kwargs['queue_id'] = self.toolkit_ops_obj.processing_queue.generate_queue_id()

            # now open up the transcription settings window
            self.open_ingest_window(
                title='Ingest',
                source_file_path=target_files,
                transcription_task=transcription_task, **kwargs)

            return True

        # or close the process if the user canceled
        else:
            return False

    def button_nle_transcribe_timeline(self, transcription_task='transcribe', **kwargs):
        """
        Used to render a timeline in Resolve and add it to the ingest window, once it's rendered
        """

        # get info from resolve
        # todo: this needs to be done using the NLE object in the future
        try:
            resolve_data = self.toolkit_ops_obj.resolve_api.get_resolve_data()
        # in case of exception still create a dict with an empty resolve object
        except:
            resolve_data = {'resolve': None}

        # set an empty target directory for future use
        target_dir = ''

        if resolve_data is not None and resolve_data['resolve'] != None \
                and 'currentTimeline' in resolve_data and \
                resolve_data['currentTimeline'] != '' and resolve_data['currentTimeline'] is not None:

            # did we ever save a target dir for this project?
            last_target_dir = self.stAI.get_project_setting(project_name=NLE.current_project,
                                                            setting_key='last_target_dir')

            # get the current timeline from Resolve
            currentTimelineName = resolve_data['currentTimeline']['name']

            # ask the user where to save the files
            while target_dir == '' or not os.path.exists(os.path.join(target_dir)):
                logger.info("Prompting user for render path.")
                # target_dir = self.ask_for_target_dir(target_dir=last_target_dir)

                target_file = self.ask_for_save_file(target_dir=last_target_dir,
                                                     initialfile=currentTimelineName
                                                     )
                if target_file:
                    # get the file_name
                    target_dir = os.path.dirname(target_file)

                    # get the file_name
                    file_name = os.path.basename(target_file)

                # remember this target_dir for the next time we're working on this project
                # (but only if it was selected by the user)
                if target_dir and target_dir != last_target_dir:
                    self.stAI.save_project_setting(project_name=NLE.current_project,
                                                   setting_key='last_target_dir', setting_value=target_dir)

                # cancel if the user presses cancel
                if not target_dir:
                    logger.info("User canceled transcription operation.")
                    return

            # send the timeline name via kwargs
            kwargs['timeline_name'] = currentTimelineName

            # get the current project name from Resolve
            if 'currentProject' in resolve_data and resolve_data['currentProject'] is not None:
                # get the project name from Resolve
                kwargs['project_name'] = resolve_data['currentProject']

            # suspend NLE polling while we're rendering
            NLE.suspend_polling = True

            # and wait for a second to make sure that the last poll was executed
            time.sleep(1)

            # generate a unique id to keep track of this file in the queue and transcription log
            if kwargs.get('queue_id', None) is None:
                kwargs['queue_id'] = self.toolkit_ops_obj.processing_queue.generate_queue_id(name=file_name)

            # update the transcription log
            self.toolkit_ops_obj.processing_queue.update_queue_item(
                name=file_name, queue_id=kwargs['queue_id'], status='waiting for render')

            # open the queue window
            self.open_queue_window()

            # use transcription_WAV render preset if it exists
            # transcription_WAV is an audio only custom render preset that renders Linear PCM codec in a Wave format
            # instead of Quicktime mp4; this is just to work with wav files instead of mp4 to improve compatibility.
            # but the user needs to add it manually to resolve in order for it to work since the Resolve API
            # doesn't permit choosing the audio format (only the codec)
            render_preset = self.stAI.get_app_setting(setting_name='transcription_render_preset',
                                                      default_if_none='transcription_WAV')

            # let the user know that we're starting the render
            self.notify_via_os("Starting Render", "Starting Render in Resolve",
                               "Saving into {} and starting render.".format(target_dir))

            render_monitor, render_file_paths \
                = self.toolkit_ops_obj.start_resolve_render_and_monitor(
                target_dir=target_dir, render_preset=render_preset, start_render=False,
                add_file_suffix=False, add_date=False, add_timestamp=True, file_name=file_name,
            )

            # turn the rendered files into a string separated by commas with each element between double quotes
            # so they fit the files input in the ingest window
            if len(render_file_paths) > 1:
                render_file_paths = ', '.join(['"{}"'.format(f) for f in render_file_paths])
            else:
                render_file_paths = '{}'.format(render_file_paths[0])

            # add the done function to the render monitor
            # - when the monitor reaches the done state, it will call the function button_transcribe
            render_monitor.add_done_callback(
                lambda l_render_file_paths=render_file_paths:
                self.button_ingest(target_files=l_render_file_paths, transcription_task=transcription_task, **kwargs)
            )

            # resume polling
            NLE.suspend_polling = False

    def convert_text_to_time_intervals(self, text, **kwargs):
        """
        Takes all the time interval lines and converts them to time intervals list.
        If using timecodes, we need to have either a transcription_data or transcription_file_path in the kwargs,
            and the transcription data must contain the framerate and the start time of the transcription.
        """

        time_intervals = []

        # split the text into lines
        lines = text.splitlines()

        # for each line
        for line in lines:

            # don't process empty lines
            if line.strip() == '':
                continue

            # when we validate, we get back a list with start and end times in return
            time_interval = self.validate_time_interval(line, **kwargs)

            if isinstance(time_interval, list):
                time_intervals.append(time_interval)

            # if we received a boolean and it's False,
            # it means that the time interval is invalid
            elif isinstance(time_interval, bool) and not time_interval:

                # so just return invalid
                return False

        if time_intervals == []:
            return True

        return time_intervals

    def validate_time_interval(self, time_interval_str, pop_error=False, **kwargs):
        """
        Validates a time interval and returns the start and end times in seconds.
        If timecode_data was passed in the kwargs, it will be used to convert the timecodes to seconds.
        """
        # split the line into two parts, separated by a dash
        parts = time_interval_str.split('-')

        # if we don't have two parts, it means that the time interval is invalid
        if len(parts) == 2:

            # remove any spaces
            start = parts[0].strip()
            end = parts[1].strip()

            # convert the start and end times to seconds
            start_seconds = self.convert_time_to_seconds(start, **kwargs)

            # if we get a bunch of nones back, it means that the time interval is invalid
            # and it doesn't make sense to check the end seconds
            if start_seconds == (None, (None, None)):
                return False

            # if the start time is a tuple, it means that we have a timecode with timecode data,
            # so let's unpack it and use the timecode data later
            if isinstance(start_seconds, tuple) and len(start_seconds) == 2:
                kwargs['timecode_data'] = start_seconds[1]
                start_seconds = start_seconds[0]

            end_seconds = self.convert_time_to_seconds(end, **kwargs)

            # now unpack the end time
            if isinstance(end_seconds, tuple) and len(end_seconds) == 2:
                kwargs['timecode_data'] = end_seconds[1]
                end_seconds = end_seconds[0]

            # if both start and end times are valid
            if start_seconds is not None and end_seconds is not None:
                # add the time interval to the list
                return [start_seconds, end_seconds]

        # if we got here, it means that the time interval is invalid
        if kwargs.get('surpress_errors', False):
            logger.error("Invalid time interval: " + time_interval_str)

        # pop an error message if we need to
        if pop_error:
            messagebox.showerror(title="Error", message="Invalid time interval: " + time_interval_str)

        # return false if the time interval is invalid
        return False

    def convert_time_to_seconds(self, time_str, **kwargs):
        """
        Converts a time string to seconds

        # the time can be a string that looks like this
        # 0:00:00:00 (timecode)
        # or like this:
        # 0:00:00.000
        # or like this:
        # 0,0
        # or like this:
        # 0.0

        If we're using timecode, we need to have either a transcription_data or transcription_file_path in the kwargs,
        and the transcription data must contain the framerate and the start time of the transcription,
        otherwise it's impossible to convert the timecode to seconds.

        """

        # if no window_id was sent, try to use the first thing from kwargs that ends with window_id
        if kwargs.get('window_id', None) is None:
            for key, value in kwargs.items():
                if key.endswith('window_id'):
                    kwargs['window_id'] = value
                    break

        window = self.get_window_by_id(kwargs.get('window_id', 'main'))

        # if the format is 0:00:00.000 or 0:00:00:00
        if ':' in time_str:

            time_array = time_str.split(':')

            # if the format is 0:00:00:00 - assume timecode stings were used
            # so try to get the timecode data to calculate to seconds
            if len(time_array) == 4:

                if kwargs.get('transcription_file_path', None) is None:
                    logger.error("Cannot convert timecode to seconds - "
                                 "unable to determine framerate or start timecode without a transcription file path.")
                    return None

                time_converted = None
                timecode_data = kwargs.get('timecode_data', None)

                # we will need the transcription object to get the timecode data or convert the timecode to seconds
                transcription = Transcription(transcription_file_path=kwargs.get('transcription_file_path', None))

                # if no timecode data were sent in the call,
                # let's try to get the timecode data from the transcription file
                if not timecode_data and kwargs.get('transcription_file_path', None) is not None:

                    timecode_data = transcription.get_timecode_data()

                    if not transcription or not transcription.exists or not timecode_data:
                        logger.error("Cannot convert timecode to seconds - "
                                     "unable to determine framerate or start timecode from transcription file {}."
                                     .format(transcription.transcription_file_path))

                # if we have timecode data, let's use it to convert the timecode to seconds
                if timecode_data and len(timecode_data) == 2:
                    time_converted = transcription.timecode_to_seconds(
                            timecode=time_str,
                            fps=timecode_data[0],
                            start_tc_offset=timecode_data[1]
                    )

                    if not time_converted:
                        self.notify_via_messagebox(title='Timecode error',
                                                   message='The timecode "{}" you entered is invalid. '
                                                           'Please try again.'.format(time_str),
                                                   message_log="Invalid Timecode or Frame Rate.",
                                                   parent=window,
                                                   type='warning')
                        return None

                # if the time isn't a float or an int, it means that the timecode couldn't be converted to seconds
                if not isinstance(time_converted, float) and not isinstance(time_converted, int):

                    if messagebox.askokcancel("Error", "You're using timecodes, "
                                                       "but we can't determine the framerate "
                                                       "or the start timecode of the media file.\n"
                                                       "Please enter these and try again."):

                        timecode_data = self.t_edit_obj.ask_for_transcription_timecode_data(
                            window_id=kwargs.get('window_id', 'main'),
                            transcription=transcription,
                            default_start_tc='01:00:00:00'
                        )

                        # replace the timecode data from the kwargs
                        if timecode_data is not None:
                            kwargs['timecode_data'] = timecode_data

                        # try the conversion again
                        time_converted = transcription.timecode_to_seconds(
                            timecode=time_str,
                            fps=timecode_data[0],
                            start_tc_offset=timecode_data[1]
                        )

                    # if user cancels, return None
                    else:
                        return None

                return time_converted, timecode_data

            elif len(time_array) == 3:
                # hours, minutes, seconds
                return int(time_array[0]) * 3600 + int(time_array[1]) * 60 + float(time_array[2])

            elif len(time_array) == 2:
                # minutes, seconds
                return int(time_array[0]) * 60 + float(time_array[1])

            elif len(time_array) == 1:
                # seconds
                return float(time_array[0])

            else:
                return 0

        # if the format is 0,0
        elif ',' in time_str:
            return float(time_str.replace(',', '.'))

        # if the format is 0.0
        elif '.' in time_str:
            return float(time_str)

        elif time_str.isnumeric():
            return int(time_str)

        else:
            if kwargs.get('supress_errors', False):
                logger.error('The time value "{}" is not recognized.'.format(time_str))
            return None

    # TRANSCRIPTION WINDOW FUNCTIONS

    class TranscriptEdit:
        """
        All the functions available in the transcript window should be part of this class
        """

        def __init__(self, toolkit_UI_obj=None):

            # keep a reference to the toolkit_UI object here
            self.toolkit_UI_obj = toolkit_UI_obj

            # keep a reference to the StoryToolkitAI object here
            self.stAI = toolkit_UI_obj.stAI

            # keep a reference to the toolkit_ops_obj object here
            self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj

            self.root = toolkit_UI_obj.root

            # search results indexes stored here
            # we're making it a dict so that we can store result indexes for each window individually
            self.search_result_indexes = {}

            # when searching for text, you may want the user to cycle through the results, so this keep track
            # keeps track on which search result is the user currently on (in each transcript window)
            self.search_result_pos = {}

            # to keep track of what is being searched on each window
            self.search_strings = {}

            # to stop certain events while typing,
            # we keep track if we have typing going on in any of the windows
            self.typing = {}

            # to know in which windows is the user editing transcripts
            self.transcript_editing = {}

            # all the selected transcript segments of each window
            # the selected segments dict will use the text element line number as an index, for eg:
            # self.selected_segments[window_id][line] = transcript_segment
            self.selected_segments = {}

            # to keep track of the modified transcripts
            self.transcript_modified = {}

            # the active_segment stores the text line number of each window to keep track where
            # the cursor is currently on the transcript
            self.active_segment = {}

            # when changed, active segments line numbers move to last_active_segment
            self.last_active_segment = {}

            # the current timecode of each window
            self.current_window_tc = {}

            # this keeps track of which transcription window is in sync with the resolve playhead
            self.sync_with_playhead = {}

        def link_to_timeline_button(self, window_id: str, link=None, timeline_name: str = None):

            # the window
            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

            # the transcription object
            window_transcription = self.get_window_transcription(window_id=window_id)

            # get the button
            button = window.nametowidget('left_frame.r_buttons_frame.link_button')

            if window_transcription is None and window_id is None:
                logger.debug('No transcription or window id provided')
                return None

            link_result = self.toolkit_ops_obj.link_transcription_path_to_timeline(
                transcription_file_path=window_transcription.transcription_file_path,
                link=link, timeline_name=timeline_name)

            # make the UI link (or unlink) the transcript to the timeline
            if link_result and link_result is not None:

                # if the reply is true, it means that the transcript is linked
                # therefore the button needs to read the opposite action
                button.configure(text="Unlink from Timeline")
                return True
            elif not link_result and link_result is not None:
                # and the opposite if transcript is not linked
                button.configure(text="Link to Timeline")
                return False

            # if the link result is None
            # don't change anything to the button
            else:
                return

        def sync_with_playhead_button(self, button=None, window_id=None, sync=None):

            if window_id is None:
                return False

            self.sync_with_playhead_update(window_id, sync)

            # update the transcript window GUI
            self.toolkit_UI_obj.update_transcription_window(window_id)

            return sync

        def button_import_srt_to_bin(self, window_id=None):
            """
            This checks if there's a srt file linked to the transcription and imports it to the bin.
            """

            if window_id is None:
                logger.error('Cannot import srt to bin - no window id was provided to get the transcription from.')

            # get the transcription object
            transcription = self.get_window_transcription(window_id=window_id)


            # get the srt file name
            full_srt_file_path = transcription.srt_file_path

            if full_srt_file_path is None:
                self.toolkit_UI_obj.notify_via_messagebox(
                    title="Cannot find SRT file",
                    type="error",
                    message='No SRT file seems to be linked to this transcription. Cannot import to bin.',
                )
                return

            # if the path is not absolute, use the transcription file path to get the absolute path
            if not os.path.isabs(full_srt_file_path):
                full_srt_file_path = \
                    os.path.join(os.path.dirname(transcription.transcription_file_path), full_srt_file_path)

            # test if the file exists
            while not os.path.isfile(full_srt_file_path):
                logger.warning('The SRT file {} doesn\'t exist.'.format(transcription.srt_file_path))

                window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

                # ask user via messagebox whether to make it
                if not messagebox.askyesno(title='SRT file not found',
                                           message='The SRT file was not found, should we export it?',
                                           parent=window):
                    return

                self.button_export_as_srt(window_id=window_id, export_file_path=full_srt_file_path)

            # if we reached this point, import the srt file to the bin
            self.toolkit_ops_obj.resolve_api.import_media(full_srt_file_path)

        def sync_with_playhead_update(self, window_id, sync=None):

            if window_id not in self.sync_with_playhead:
                self.sync_with_playhead[window_id] = False

            # if no sync variable was passed, toggle the current sync state
            if sync is None:
                sync = not self.sync_with_playhead[window_id]

            self.sync_with_playhead[window_id] = sync

            return sync

        def set_typing_in_window(self, event=None, window_id=None, typing=None):

            if window_id is None:
                return None

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.typing:
                self.typing[window_id] = False

            # if typing was passed, assign it
            if typing is not None:
                self.typing[window_id] = typing

            # return the status of the typing
            return self.typing[window_id]

        def get_typing_in_window(self, window_id):

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.typing:
                self.typing[window_id] = False

            return self.typing[window_id]

        def set_transcript_editing(self, event=None, window_id=None, editing=None):

            if window_id is None:
                return None

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.transcript_editing:
                self.transcript_editing[window_id] = False

            # if typing was passed, assign it
            if editing is not None:
                self.transcript_editing[window_id] = editing

            # return the status of the typing
            return self.transcript_editing[window_id]

        def get_transcript_editing_in_window(self, window_id):

            # if there isn't a typing tracker for this window, create one
            if window_id not in self.transcript_editing:
                self.transcript_editing[window_id] = False

            return self.transcript_editing[window_id]

        def _transcription_window_context_menu(self, event=None, window_id: str = None, **attributes):
            """
            This creates a context menu for the text widget in the transcription window.
            """

            # get the window object
            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

            # get the text widget from the event
            text_widget = event.widget

            # get the line and char from the click
            line, char = self.toolkit_UI_obj.get_line_char_from_click(event, text_widget=text_widget)
            line = int(line)
            char = int(char)

            # get the segment at the click
            segment = self.get_segment(window_id=window_id, line=line)

            # spawn the context menu
            context_menu = tk.Menu(text_widget, tearoff=0)

            # add the menu items
            # if there is a selection
            if text_widget.tag_ranges("sel"):
                context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))

                # add a separator
                context_menu.add_separator()

            # THE SELECT SEGMENT BUTTON

            select_button_text = "Select Segment"
            if self.is_selected(window_id=window_id, line=line):
                select_button_text = "Deselect Segment"

            # add select segment
            context_menu.add_command(
                label=select_button_text,
                command=lambda: self.segment_to_selection(window_id, text_widget, line),
                accelerator="v"
            )

            # THE SELECT ALL BUTTON
            select_all_button_text = "Select All Segments"

            if self.has_selected_segments(window_id=window_id):
                select_all_button_text = "Deselect All Segments"

            # add the select/deselect all option
            context_menu.add_command(
                label=select_all_button_text,
                command=lambda: self.button_select_deselect_all(window_id, text_element=text_widget),
                accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+a"
            )

            # THIS MAKES SURE WE SEE THE SELECTION CONTEXT MENU WITHOUT A SELECTION
            # temporary solution to force the context menu to always think there are selected segments
            none_selected = False
            if not self.has_selected_segments(window_id=window_id):
                none_selected = True

                # temporary select the segment at the click
                self.segment_to_selection(window_id, text_widget, line)

            # if the window has a selection
            if self.has_selected_segments(window_id=window_id):

                # add separator
                context_menu.add_separator()

                # the add to story sub-menu
                add_to_story_menu = tk.Menu(context_menu, tearoff=0)

                # the "New Story" button
                add_to_story_menu.add_command(
                    label="New Story...",
                    command=lambda: self.button_add_to_new_story(window_id=window_id)
                )
                add_to_story_menu.add_separator()

                story_editor_windows = self.toolkit_UI_obj.get_all_windows_of_type('story_editor')

                for story_editor_window_id in story_editor_windows:

                    story_editor_window = self.toolkit_UI_obj.get_window_by_id(window_id=story_editor_window_id)

                    add_to_story_menu.add_command(
                        label="{}".format(story_editor_window.title()),
                        command=lambda: self.button_add_to_story(
                            window_id=window_id, story_editor_window_id=story_editor_window_id)
                    )

                # add the add to story sub-menu
                context_menu.add_cascade(label="Add to Story", menu=add_to_story_menu)

                # add send to assistant
                context_menu.add_command(
                    label="Send to Assistant",
                    command=lambda: self.button_send_to_assistant(window_id),
                    accelerator="o"
                )

                context_menu.add_command(
                    label="Send to Assistant with TC",
                    command=lambda: self.button_send_to_assistant(window_id=window_id, with_timecodes=True),
                    accelerator="Shift+O"
                )

                # add: add to new group
                context_menu.add_command(
                    label="Add to New Group",
                    command=lambda: self.button_add_to_new_group(window_id),
                    accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+g"
                )

                # copy selected segments
                context_menu.add_command(
                    label="Copy with TC",
                    command=lambda: self.button_copy_segments_to_clipboard(
                        window_id, with_timecodes=True, per_line=True),
                    accelerator="Shift+"+self.toolkit_UI_obj.ctrl_cmd_bind + "+c"
                )

                context_menu.add_command(
                    label="Copy with Block TC",
                    command=lambda: self.button_copy_segments_to_clipboard(
                        window_id, with_timecodes=True, per_line=False),
                    accelerator="Shift+C"
                )

                context_menu.add_command(
                    label="Re-transcribe",
                    command=lambda: self.button_retranscribe(window_id=window_id),
                    accelerator="t"
                )

                context_menu.add_command(
                    label="Detect Speakers for Selection",
                    command=lambda: self.button_detect_speakers(window_id=window_id)
                )

                context_menu.add_command(
                    label="Edit",
                    command=lambda: self.edit_transcript(window_id=window_id),
                    accelerator=self.toolkit_UI_obj.ctrl_cmd_bind + "+e"
                )

            # if this is a transcription window enable the relevant menu items
            if NLE.is_connected() and NLE.current_timeline is not None:

                context_menu.add_separator()

                context_menu.add_command(
                    label="Markers to Segments",
                    command=lambda: self.toolkit_UI_obj.t_edit_obj.button_markers_to_segments(
                        window_id=window_id)
                )

                # if the window has a selection
                if self.has_selected_segments(window_id=window_id):

                    context_menu.add_command(
                        label="Move Playhead to Selection Start",
                        command=lambda: self.go_to_selected_time(
                            window_id=window_id, position='start')
                    )
                    context_menu.add_command(
                        label="Move Playhead to Selection End",
                        command=lambda: self.go_to_selected_time(
                            window_id=window_id, position='end')
                    )
                    context_menu.add_command(
                        label="Align Segment Start to Playhead",
                        command=lambda: self.align_line_to_playhead(
                            window_id=window_id, position='start')
                    )
                    context_menu.add_command(
                        label="Align Segment End to Playhead",
                        command=lambda: self.align_line_to_playhead(
                            window_id=window_id, position='end')
                    )

            # add a separator
            context_menu.add_separator()

            # use timecode if available
            window_transcription = self.get_window_transcription(window_id=window_id)
            timecode_data = window_transcription.get_timecode_data()

            if timecode_data is not False and timecode_data is not [None, None]:
                segment_start = window_transcription.seconds_to_timecode(
                    seconds=segment.start, fps=timecode_data[0], start_tc_offset=timecode_data[1])

                segment_end = window_transcription.seconds_to_timecode(
                    seconds=segment.end, fps=timecode_data[0], start_tc_offset=timecode_data[1])

                segment_info = "{} to {}".format(segment_start, segment_end)

                if self.stAI.debug_mode:
                    segment_info = "\nTime: {:.4f} to {:.4f}".format(segment.start, segment.end)

            else:
                segment_start = segment.start
                segment_end = segment.end

                # add the segment info as a disabled menu item
                if self.stAI.debug_mode:
                    segment_info = "Time: {:.4f} to {:.4f}".format(segment.start, segment.end)
                else:
                    segment_info = "Time: {:.2f} to {:.2f}".format(segment_start, segment_end)

            context_menu.add_command(label=segment_info, state=tk.DISABLED)

            # display the context menu
            context_menu.tk_popup(event.x_root, event.y_root)

            # this will deselect the temporary selection
            if none_selected:
                self.segment_to_selection(window_id, text_widget, line)

            return

        def transcription_window_keypress(self, event=None, **attributes):
            """
            What to do with the keypresses on transcription windows?
            :param attributes:
            :return:
            """

            if self.get_typing_in_window(attributes['window_id']):
                return

            # for now, simply pass to select text lines if it matches one of these keys
            if event.keysym in ['Up', 'Down', 'v', 'V', 'A', 'i', 'o', 'O', 'm', 'M', 'C', 's', 'S', 'L',
                                'g', 'G', 'BackSpace', 't', 'a', 'equal',
                                'apostrophe', 'semicolon', 'colon', 'quotedbl']:
                self.segment_actions(event, **attributes)

        def transcription_window_mouse(self, event=None, **attributes):
            """
            What to do with mouse presses on transcription windows?
            :param event:
            :param attributes:
            :return:
            """

            # print(event.state)
            # for now simply pass the event to the segment actions
            self.segment_actions(event, mouse=True, **attributes)

        def segment_actions(self, event=None, text_element=None, window_id=None,
                            special_key=None, mouse=False, status_label=None):
            """
            Handles the key and mouse presses in relation with transcript segments (lines)
            :return:
            """

            if text_element is None or window_id is None:
                return False

            # temporary solution, until we clean this mess up
            # get the currently focused widget
            focused_widget = self.toolkit_UI_obj.root.focus_get()

            transcript_focused = False
            # check if the focused widget is the transcript text widget
            if str(focused_widget).endswith('middle_frame.text_form_frame.transcript_text'):
                transcript_focused = True

            # if special_key is not None:
            #     print(special_key)

            # HERE ARE SOME USEFUL SHORTCUTS FOR THE TRANSCRIPTION WINDOW:
            # see the shortcuts in the README file

            # get the current window
            transcription_window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # initialize the active segment number
            self.active_segment[window_id] = self.get_active_segment(window_id, 1)

            # PRE-CURSOR MOVE EVENTS:
            # below we have the events that should happen prior to moving the cursor

            # UP key events
            if event.keysym == 'Up':

                if str(focused_widget).endswith('transcriptgroupsmodule'):
                    focused_widget.select_previous()
                else:
                    # move cursor (active segment) on the previous segment on the transcript
                    self.set_active_segment(window_id, text_element, line_calc=-1)

            # DOWN key events
            elif event.keysym == 'Down':

                if str(focused_widget).endswith('transcriptgroupsmodule'):
                    focused_widget.select_next()
                else:
                    # move cursor (active segment) on the next segment on the transcript
                    self.set_active_segment(window_id, text_element, line_calc=1)

            # APOSTROPHE key events
            if event.keysym == 'apostrophe':
                # go_to_time end time of the last selected segment
                self.go_to_selected_time(window_id=window_id, position='end')

            # SEMICOLON key events
            elif event.keysym == 'semicolon':
                # go_to_time start time of the first selected segment
                self.go_to_selected_time(window_id=window_id, position='start')

            # on mouse presses
            if mouse:

                # first get the line and char numbers based text under the click event
                index = text_element.index("@%s,%s" % (event.x, event.y))
                line_str, char_str = index.split(".")

                # make the clicked segment into active segment
                self.set_active_segment(window_id, text_element, int(line_str))

                # and move playhead to that time
                self.go_to_selected_time(window_id, 'start', ignore_selection=True)

                # if cmd was also pressed
                if special_key == 'cmd':
                    # add clicked segment to selection
                    self.segment_to_selection(window_id, text_element, int(line_str))

            # what is the currently selected line number again?
            line = self.get_active_segment(window_id)

            # POST-CURSOR MOVE EVENTS
            # these are the events that might require the new line and segment numbers

            # v key events
            if event.keysym == 'v' and transcript_focused:
                # add/remove active segment to selection
                # if it's not in the selection
                self.segment_to_selection(window_id, text_element, line)

                # call auto add to group function
                self.auto_add_selection_to_group(window_id)

            # Shift+V key events
            # if event.keysym == 'V':
            #    # clear selection
            #    self.clear_selection(window_id, text_element)

            # CMD+A key (select/deselect all)
            if event.keysym == 'a' and special_key == 'cmd' and transcript_focused:
                return self.button_select_deselect_all(window_id, text_element)

            # Shift+A key (select between current and last active segment)
            if event.keysym == 'A':
                self.button_select_between_segments(window_id, text_element)

            # Shift+C and CMD/CTRL+Shift+C key event (copy segments with timecodes to clipboard)
            if event.keysym == 'C':
                # copy the text content to clipboard
                # but if CMD/CTRL is also pressed - then add timecodes to each line
                # otherwise add timecodes to each new chunk of text
                self.button_copy_segments_to_clipboard(window_id,
                                                       with_timecodes=True,
                                                       per_line=True if special_key == 'cmd' else False
                                                       )

            # m key event (quick add duration markers)
            # and Shift+M key event (add duration markers with name input)
            # CMD/CTRL+M key event (select all segments between markers)
            if event.keysym == 'm' or event.keysym == 'M':

                # this only works if resolve is connected
                if self.toolkit_ops_obj.resolve_exists() and 'name' in NLE.current_timeline:

                    # if CMD/CTRL+M was pressed
                    # select segments based on current timeline markers
                    # (from Resolve to tool)
                    if special_key == 'cmd':
                        self.button_markers_to_segments(window_id=window_id, text_element=text_element)

                    # otherwise (if cmd wasn't pressed)
                    # add segment based markers
                    # (from tool to Resolve)
                    else:

                        # if Shift+M was pressed, prompt the user for the marker name
                        if event.keysym == 'M':
                            self.button_segments_to_markers(window_id=window_id, text_element=text_element, prompt=True)

                        # otherwise, just add the marker with the default name (quick add)
                        else:
                            self.button_segments_to_markers(window_id=window_id, text_element=text_element)

            # Shift+L key event (link current timeline to this transcription)
            if event.keysym == 'L':
                # link transcription to file
                # self.toolkit_ops_obj.link_transcription_to_timeline(self.transcription_file_paths[window_id])
                self.link_to_timeline_button(window_id=window_id)

            # s key event (sync transcript cursor with playhead)
            if event.keysym == 's':
                # self.sync_with_playhead_update(window_id=window_id)
                self.sync_with_playhead_button(window_id=window_id)

            # CMD+G adds the selected segments to a new group
            if (event.keysym == 'g') and special_key == 'cmd':
                self.button_add_to_new_group(window_id=window_id, only_add=False)

            # SHIFT+G shows the group module
            # elif event.keysym == 'G':
            #    self.button_toggle_groups_module(window_id=window_id)
            #    return 'break'

            # colon key event (align current segment start to playhead)
            if event.keysym == 'colon' and transcript_focused:
                self.align_line_to_playhead(window_id=window_id, position='start', line_index=line)

            # double quote key event (align current segment end to playhead)
            if event.keysym == 'quotedbl' and transcript_focused:
                self.align_line_to_playhead(window_id=window_id, position='end', line_index=line)

            # 't' key event (re-transcribe selected segments)
            if event.keysym == 't':
                self.button_retranscribe(window_id=window_id)

            # 'o' key sends active segment as context to the Assistant window
            # Shift+O also includes a time column
            if (event.keysym == 'o' or event.keysym == 'O') and transcript_focused:

                # Shift+O includes a time column
                if event.keysym == 'O':
                    self.button_send_to_assistant(window_id=window_id, with_timecodes=True)
                else:
                    self.button_send_to_assistant(window_id=window_id, with_timecodes=False)

            # BackSpace key event to delete selected segments
            if event.keysym == 'BackSpace' and transcript_focused:

                selected_segments = self.get_segments_or_selection_indexes(window_id=window_id)

                # if we have selected segments, delete them
                if len(selected_segments) > 0:
                    self.delete_lines(window_id=window_id, text_widget_lines=selected_segments)

                # if we don't have selected segments, delete the active segment
                else:
                    self.delete_line(window_id=window_id,  text_widget_line_no=selected_segments[0])

            # BackSpace key event to delete selected group
            elif event.keysym == 'BackSpace' and str(focused_widget).endswith('transcriptgroupsmodule'):
                focused_widget.delete_selected_group()

            # CMD/CTRL+Shift+s key event (Export transcription as...)
            if event.keysym == 'S' and special_key == 'cmd':
                self.button_export_as(window_id=window_id)

            # equal key event (go to timecode)
            if event.keysym == 'equal':
                self.button_go_to_timecode(window_id=window_id)

            # todo: this is very un-necessary because it's redrawing the whole window on each segment move
            # final step, update the window
            self.toolkit_UI_obj.update_transcription_window(window_id=window_id)

        def button_select_deselect_all(self, window_id, text_element=None):
            """
            Selects or deselects all the text in the transcript text element
            :param window_id:
            :param text_element:
            :return:
            """

            transcription = self.get_window_transcription(window_id=window_id)

            # if the text element hasn't been sent
            if text_element is None and window_id in self.toolkit_UI_obj.windows:
                # try to find it in the transcript text elements
                text_element = self.toolkit_UI_obj.windows[window_id] \
                    .nametowidget('middle_frame.text_form_frame.transcript_text')

            if text_element is None:
                logger.error('Could not find transcript text element in window {}'.format(window_id))
                return 'break'

            # if this window contains a selection, just clear it
            # since we're expecting the user to want to deselect first
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:
                self.clear_selection(window_id, text_element)

                # and clear any selection on the text element
                text_element.tag_remove("sel", "1.0", "end")

                return 'break'

            # but if no selection exists, select all segments:

            # create a list containing all the segment numbers
            segment_list = list(range(1, transcription.get_num_lines() + 1))

            # select all segments by passing all the line numbers
            self.segment_to_selection(window_id, text_element, segment_list)

            # call auto add to group function
            self.auto_add_selection_to_group(window_id, confirm=True if len(segment_list) > 10 else False)

            return 'break'

        def button_select_between_segments(self, window_id, text_element):
            """
            Selects all segments between the active segment and the last active segment
            """

            # first, try to see if there is a text selection (i.e. drag and select type selection)
            selection = text_element.tag_ranges("sel")

            # if there is such a selection
            if len(selection) > 0:

                # get the first and last segment numbers of the selection
                start_segment = int(str(selection[0]).split(".")[0])
                max_segment = int(str(selection[1]).split(".")[0])

                # clear the selection
                text_element.tag_delete("sel")

            # if there is no such selection
            else:

                # get the active_segment and the last_active_segment
                # to use them as the start and end of the selection
                start_segment = self.last_active_segment[window_id]
                max_segment = self.active_segment[window_id]

            # make sure that we're counting in the right direction
            if start_segment > max_segment:
                start_segment, max_segment = max_segment, start_segment

            # clear the existing selection
            # self.clear_selection(window_id, text_element)

            # how many segments are we selecting?
            num_segments = max_segment - start_segment + 1

            # then take each segment, from the first to the last
            n = start_segment
            while n <= max_segment:
                # and add it to the selection
                self.segment_to_selection(window_id, text_element, n, only_add=True)
                n = n + 1

            # and also call auto add to group function
            self.auto_add_selection_to_group(window_id, confirm=True if num_segments > 10 else False)

        def button_send_to_assistant(self, window_id, with_timecodes=False):
            """
            Sends the selected segments to the Assistant window
            """

            if with_timecodes:
                text, full_text, _, _, transcription_segments \
                    = self.get_segments_or_selection(window_id, split_by='line', add_time_column=True)

            else:
                text, full_text, _, _, transcription_segments \
                    = self.get_segments_or_selection(window_id, split_by='line',
                                                     add_time_column=False, timecodes=False)

            self.toolkit_UI_obj.open_assistant_window(
                assistant_window_id='assistant', transcript_text=full_text.strip(),
                transcription_segments=transcription_segments)

        def button_add_to_story(self, window_id, story_editor_window_id):

            text, full_text, start_sec, end_sec, _ \
                = self.get_segments_or_selection(window_id, split_by='line',
                                                 add_time_column=False, timecodes=False)

            # get the transcription object associated with this window
            transcription = self.get_window_transcription(window_id=window_id)

            new_lines = []

            for line in text:
                new_lines.append({
                    'text': line.get('text', '').strip(),
                    'type': 'transcription_segment',
                    'source_start': line.get('start', 0),
                    'source_end': line.get('end', line.get('start', 0.01)),
                    'transcription_file_path': transcription.transcription_file_path,
                    'source_file_path': transcription.audio_file_path,
                    'source_fps': transcription.timeline_fps,
                    'source_start_tc': transcription.timeline_start_tc,
                })

            if new_lines:
                story_editor_window = self.toolkit_UI_obj.get_window_by_id(story_editor_window_id)

                toolkit_UI.StoryEdit.paste_to_story_editor(
                    window=story_editor_window, lines_to_paste=new_lines,
                    toolkit_UI_obj=self.toolkit_UI_obj)

                # save the story
                toolkit_UI.StoryEdit.save_story(window_id=story_editor_window, toolkit_UI_obj=self.toolkit_UI_obj)

        def button_add_to_new_story(self, window_id):

            # first open a new story
            if story_editor_window := self.toolkit_UI_obj.open_new_story_editor_window():
                self.button_add_to_story(window_id, story_editor_window.window_id)


        def button_add_to_new_group(self, window_id, only_add=True):
            """
            Adds the selected segments to a group
            """

            # the transcription window
            t_window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # the groups module for this window
            window_groups_module = t_window.transcript_groups_module

            # add the new group (and group all the selected segments in it)
            window_groups_module.add_new_group()

            return

        def button_toggle_groups_module(self, window_id):

            # the transcription window
            t_window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # the groups module for this window
            window_groups_module = t_window.transcript_groups_module

            # toggle the groups module
            window_groups_module.toggle_groups_module_visibility()

        def button_copy_segments_to_clipboard(self, window_id, with_timecodes=False, per_line=False):
            """
            Copies the selected segments to clipboard
            :param window_id:
            :param with_timecodes: Adds timecodes
            :param per_line: If true, the timecodes are added to each line, otherwise to each block of text
            """

            if with_timecodes:

                # if per_line is true, then add timecodes to each line
                if per_line:
                    text, _, _, _, _ \
                        = self.get_segments_or_selection(window_id, split_by='line',
                                                         add_to_clipboard=True, add_time_column=True)

                # otherwise add timecodes to each block of text
                else:
                    self.get_segments_or_selection(window_id, add_to_clipboard=True, split_by='index')

            else:
                logger.debug('Not possible to copy segments to clipboard without timecodes using this function.')
                return

        def button_retranscribe(self, window_id):
            """
            Re-transcribes the selected segments
            """
            # first get the selected (or active) text from the transcript
            text, full_text, start_sec, end_sec, _ = \
                self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                               split_by='index', timecodes=False, allow_active_segment=False)

            # now turn the text blocks into time intervals
            time_intervals = ''
            retranscribe = False
            ask_message = "Working on this transcription while it's being re-transcribed is not recommended.\n\n" \
                          "Do you still want to re-transcribe the entire transcript?"
            if text is not None and text and len(text) > 0:

                # get all the time intervals based on the text blocks
                for text_block in text:
                    time_intervals = time_intervals + "{}-{}\n".format(text_block['start'], text_block['end'])

                ask_message = "Working on this transcription while it's being re-transcribed is not recommended.\n\n" \
                              "Do you still want to re-transcribe the selected segments?"

            # ask the user if they want to re-transcribe
            retranscribe = messagebox.askyesno(title='Re-transcribe',
                                               parent=self.toolkit_UI_obj.windows[window_id],
                                               message=ask_message)

            # if the user cancels re-transcribe or no segments were selected, cancel
            if not retranscribe:
                return False

            # open the ingest window with the transcription file to show the re-transcribing options
            self.toolkit_UI_obj.open_ingest_window(
                transcription_file_path=self.get_window_transcription(window_id=window_id).transcription_file_path,
                time_intervals=time_intervals, retranscribe=True,
                video_indexing_enabled=False
            )

            # close the transcription window
            self.toolkit_UI_obj.destroy_transcription_window(window_id)

            # remove the selection references too
            # self.clear_selection(window_id=window_id)

        def button_markers_to_segments(self, window_id, text_element=None):
            """
            This function selects all the segments between certain markers
            """

            # first, see if there are any markers on the timeline
            if not NLE.is_connected() or 'markers' not in NLE.current_timeline:
                logger.debug('No markers found on the timeline.')
                return

            # if no text_element is provided, try to get it from the window
            if text_element is None:
                text_element = self.toolkit_UI_obj.windows[window_id] \
                    .nametowidget('middle_frame.text_form_frame.transcript_text')

            # get the marker colors from all the markers in the current_timeline['markers'] dict
            marker_colors = [' '] + sorted(list(set([NLE.current_timeline['markers'][marker]['color']
                                                     for marker in NLE.current_timeline['markers']])))

            # create a list of widgets for the input dialogue
            input_widgets = [
                {'name': 'starts_with', 'label': 'Starts With:', 'type': 'entry', 'default_value': ''},
                {'name': 'color', 'label': 'Color:', 'type': 'option_menu', 'default_value': 'Blue',
                 'options': marker_colors}
            ]

            # then we call the ask_dialogue function
            user_input = self.toolkit_UI_obj.AskDialog(title='Markers to Selection',
                                                       input_widgets=input_widgets,
                                                       parent=self.toolkit_UI_obj.windows[window_id],
                                                       toolkit_UI_obj=self.toolkit_UI_obj
                                                       ).value()

            # if the user didn't cancel add the group
            if user_input is not None:

                # get the user input
                starts_with = user_input['starts_with']
                color = user_input['color']

                selected_markers = {}

                # go through the markers on the timeline
                for marker in NLE.current_timeline['markers']:

                    # if the marker starts with the text the user entered (if not empty)
                    # and the marker color matches the color the user selected (if not empty)
                    if (starts_with == ''
                        or NLE.current_timeline['markers'][marker]['name'].startswith(starts_with)) \
                            and (color == ' ' or NLE.current_timeline['markers'][marker]['color'] == color):
                        # add the marker to the marker_groups dictionary
                        selected_markers[marker] = NLE.current_timeline['markers'][marker]

                # if there are markers in the selection
                if len(selected_markers) > 0:

                    time_intervals = []

                    # add them to the transcript group, based on their start time and duration
                    # the start time (marker) and duration are in frames
                    for marker in selected_markers:
                        # convert the frames to seconds
                        start_time = int(marker) / NLE.current_timeline_fps
                        duration = int(
                            NLE.current_timeline['markers'][marker]['duration']) / NLE.current_timeline_fps
                        end_time = start_time + duration

                        # add the time interval to the list of time intervals
                        time_intervals.append({'start': start_time, 'end': end_time})

                    # get the window transcription object
                    window_transcription = self.get_window_transcription(window_id=window_id)

                    # get only the transcript segments that are within the time intervals
                    segment_list = window_transcription.time_intervals_to_transcript_segments(time_intervals)

                    # now select the segments
                    self.segment_to_selection(window_id, text_element, segment_list)

        def button_segments_to_markers(self, window_id, text_element=None, prompt=False):

            # first, see if there are any markers on the timeline
            if not NLE.is_connected() or NLE.current_timeline is None:
                logger.debug('No timeline available.')
                return

            # if no text_element is provided, try to get it from the window
            if text_element is None:
                text_element = self.toolkit_UI_obj.windows[window_id] \
                    .nametowidget('middle_frame.text_form_frame.transcript_text')

            # check if the user is trying to add markers
            # to a timeline that is not connected to the transcription in this window
            is_linked, _ = self.toolkit_ops_obj.get_transcription_path_to_timeline_link(
                transcription_file_path=self.get_window_transcription(window_id).transcription_file_path,
                timeline_name=NLE.current_timeline['name'],
                project_name=NLE.current_project)

            # if the transcription is not linked to the timeline
            if not is_linked:

                # warn the user that the transcription is not linked to the timeline
                user_response = messagebox.askyesnocancel(
                    parent=self.toolkit_UI_obj.windows[window_id],
                    title='Transcription not linked to timeline',
                    message='The transcription is not linked to the current timeline.\n\n'
                            'Do you want to link it before adding the markers?')

                # if the user wants to link the transcription to the timeline
                if user_response:

                    # link the transcription to the current timeline
                    self.link_to_timeline_button(window_id=window_id, link=True)

                # if the user cancels the linking
                elif user_response is None:
                    logger.debug('User canceled selection to marker operation.')
                    return

            # first get the selected (or active) text from the transcript
            # this should return a list of all the text chunks, the full text
            #   and the start and end times of the entire text
            text, full_text, start_sec, end_sec, _ = \
                self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                               split_by='index', timecodes=True)

            # now, take care of the marker name
            marker_name = False
            marker_color = self.stAI.get_app_setting('default_marker_color', default_if_none='Blue')

            # ask the user for the marker name if prompt is true
            if prompt:

                # create a list of widgets for the input dialogue
                input_widgets = [
                    {'name': 'name', 'label': 'Name:', 'type': 'entry', 'default_value': ''},
                    {'name': 'color', 'label': 'Color:', 'type': 'option_menu',
                     'default_value': self.stAI.get_app_setting('default_marker_color',
                                                                default_if_none='Blue'),
                     'options': list(self.toolkit_UI_obj.resolve_marker_colors.keys())}
                ]

                # then we call the ask_dialogue function
                user_input = self.toolkit_UI_obj.AskDialog(title='Add Markers from Selection',
                                                           input_widgets=input_widgets,
                                                           parent=self.toolkit_UI_obj.windows[window_id],
                                                           toolkit_UI_obj=self.toolkit_UI_obj
                                                           ).value()

                # if the user didn't cancel add the group
                if user_input == None:
                    return False

                marker_name = user_input['name']
                marker_color = user_input['color']

                # if the user pressed cancel, return
                if not marker_name or marker_name == '':
                    return False

            # if we still don't have a marker name
            if not marker_name or marker_name == '':
                # use a generic name which the user will most likely change afterwards
                marker_name = 'Transcript Marker'

            # calculate the start timecode of the timeline (simply use second 0 for the conversion)
            # we will use this to calculate the text_chunk durations
            timeline_start_tc = self.toolkit_ops_obj.calculate_sec_to_resolve_timecode(0)

            # now take all the text chunks
            for text_chunk in text:

                # calculate the end timecodes for each text chunk
                end_tc = self.toolkit_ops_obj.calculate_sec_to_resolve_timecode(text_chunk['end'])

                # get the start_tc from the text_chunk but place it back into a Timecode object
                # using the timeline framerate
                start_tc = Timecode(timeline_start_tc.framerate, text_chunk['start_tc'])

                # and subtract the end timecode from the start_tc of the text_chunk
                # to get the marker duration (still timecode object for now)
                # the start_tc of the text_chunk should be already in the text list
                marker_duration_tc = end_tc - start_tc

                # in Resolve, marker indexes are the number of frames from the beginning of the timeline
                # so in order to get the marker index, we need to subtract the timeline_start_tc from start_tc

                # but only if the start_tc is larger than the timeline_start_tc so we don't get a
                # Timecode class error
                if start_tc > timeline_start_tc:
                    start_tc_zero = start_tc - timeline_start_tc
                    marker_index = start_tc_zero.frames

                # if not consider that we are at frame 1
                else:
                    marker_index = 1

                # check if there's another marker at the exact same index
                index_blocked = True
                while index_blocked:

                    if 'markers' in NLE.current_timeline and marker_index in NLE.current_timeline['markers']:

                        # give up if the duration is under a frame:
                        if marker_duration_tc.frames <= 1:
                            self.toolkit_UI_obj.notify_via_messagebox(title='Cannot add marker',
                                                                      message='Not enough space to add marker on timeline.',
                                                                      type='warning',
                                                                      parent=self.toolkit_UI_obj.windows[window_id]
                                                                      )
                            return False

                        # notify the user that the index is blocked by another marker
                        add_frame = messagebox.askyesno(parent=self.toolkit_UI_obj.windows[window_id],
                                                        title='Cannot add marker',
                                                        message="Another marker exists at {}.\n\n"
                                                                "Do you want to place the new marker one frame later?"
                                                        .format(start_tc))

                        # if the user wants to move this marker one frame to the right, be it
                        if add_frame:
                            start_tc.frames = start_tc.frames + 1
                            marker_index = marker_index + 1

                            # but this means that the duration should be one frame shorter
                            marker_duration_tc.frames = marker_duration_tc.frames - 1
                        else:
                            return False

                    else:
                        index_blocked = False

                marker_data = {}
                marker_data[marker_index] = {}

                # the name of the marker
                marker_data[marker_index]['name'] = marker_name

                # choose the marker color from Resolve
                marker_data[marker_index]['color'] = marker_color

                # add the text to the marker data
                marker_data[marker_index]['note'] = text_chunk['text']

                # the marker duration needs to be in frames
                marker_data[marker_index]['duration'] = marker_duration_tc.frames

                # no need for custom data
                marker_data[marker_index]['customData'] = ''

                # pass the marker add request to resolve
                self.toolkit_ops_obj.resolve_api.add_timeline_markers(NLE.current_timeline['name'],
                                                                      marker_data,
                                                                      False)

        def button_export_as(self, window_id, export_file_path=None):
            """
            Exports the transcript to a file.
            For now, only SRT and TXT is supported.
            """

            # get the transcription file path from the window
            transcription_file_path = \
                self.get_window_transcription(window_id).transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Export as...',
                                                                initialdir=os.path.dirname(transcription_file_path),
                                                                initialfile=os.path.basename(transcription_file_path)
                                                                .replace('.transcription.json', ''),
                                                                filetypes=[('SRT files', '*.srt'),
                                                                           ('TXT files', '*.txt')
                                                                           ],
                                                                defaultextension='.srt')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled Export As process.')
                    return False

            # pass this to the relevant export function
            if export_file_path.endswith('.srt'):
                return self.button_export_as_srt(window_id, export_file_path)
            elif export_file_path.endswith('.txt'):
                return self.button_export_as_txt(window_id, export_file_path)
            else:
                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='Not supported',
                                                          message='Export as {} is not supported.'
                                                          .format(export_file_path.split('.')[-1]),
                                                          type='warning'
                                                          )
                return False

        def button_export_as_srt(self, window_id, export_file_path=None):
            """
            Exports the transcript as an SRT file
            """

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            # get the transcription file path from the window
            transcription_file_path = window_transcription.transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Save as SRT',
                                                                initialdir=os.path.dirname(transcription_file_path),
                                                                initialfile=os.path.basename(transcription_file_path)
                                                                .replace('.transcription.json', '.srt'),
                                                                filetypes=[('SRT files', '*.srt')],
                                                                defaultextension='.srt')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled save as SRT.')
                    return False

            window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # write the SRT file if the transcription has segments
            if window_transcription.segments is not None \
                    or window_transcription.segments != [] \
                    or len(window_transcription) > 0:

                # write the SRT file
                TranscriptionUtils.write_srt(
                    transcript_segments=window_transcription.segments, srt_file_path=export_file_path)

                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='SRT file export',
                                                          message='The SRT file was exported successfully.',
                                                          message_log='The SRT file was exported successfully to {}.'
                                                            .format(export_file_path),
                                                          type='info',
                                                          parent=window
                                                          )

                # focus back on the transcription window
                self.toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='No segments to export',
                                                          message='No segments found in this transcription.',
                                                          type='warning',
                                                          parent=window
                                                          )

                # focus back on the transcription window
                self.toolkit_UI_obj.focus_window(window_id)

                return False

        def button_export_as_txt(self, window_id, export_file_path=None):
            """
            Exports the transcript as a TXT file
            """

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            # get the transcription file path from the window
            transcription_file_path = window_transcription.transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Save as Text',
                                                                initialdir=os.path.dirname(transcription_file_path),
                                                                initialfile=os.path.basename(transcription_file_path)
                                                                .replace('.transcription.json', '.txt'),
                                                                filetypes=[('TXT files', '*.txt')],
                                                                defaultextension='.txt')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled save as TXT.')
                    return False

            # write the TXT file
            if window_transcription.segments is not None \
                    or window_transcription.segments != [] \
                    or len(window_transcription) > 0:

                # write the TXT file
                TranscriptionUtils.write_txt(
                    transcript_segments=window_transcription.segments, txt_file_path=export_file_path)

                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='Text file export',
                                                          message='The text file was exported successfully.',
                                                          type='info'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='No transcription data',
                                                          message='No transcription data was found.',
                                                          type='warning'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return False

        def button_export_as_avid_ds(self, window_id, export_file_path=None):
            """
            Exports the transcript as an Avid DS file
            """

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            # get the transcription file path from the window
            transcription_file_path = window_transcription.transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Save as AVID DS',
                                                                initialdir=os.path.dirname(transcription_file_path),
                                                                initialfile=os.path.basename(transcription_file_path)
                                                                .replace('.transcription.json', '.txt'),
                                                                filetypes=[('AVID DS files', '*.txt')],
                                                                defaultextension='.txt')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled save as AVID DS.')
                    return False

            # get the timecode data
            timecode_data = self.get_timecode_data_from_transcription(window_id=window_id)

            if not timecode_data or not isinstance(timecode_data, tuple) or len(timecode_data) != 2:

                self.toolkit_UI_obj.notify_via_messagebox(
                    title='No timecode data',
                    message='No timecode data was found for this transcription.\n\nAborting AVID DS export.',
                    message_log='No timecode data was found for this transcription. Aborting AVID DS export.',
                    type='error'
                )

                return False

            # write the AVID DS file
            if window_transcription.segments is not None \
                    or window_transcription.segments != [] \
                    or len(window_transcription) > 0:

                # uwrite the AVID DS file
                TranscriptionUtils.write_avid_ds(transcript_segments=window_transcription.segments,
                                                   avid_ds_file_path=export_file_path,
                                                   timeline_fps=timecode_data[0],
                                                   timeline_start_tc=timecode_data[1])

                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='AVID DS file export',
                                                          message='The AVID DS file was exported successfully.',
                                                          type='info'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='No transcription data',
                                                          message='No transcription data was found.',
                                                          type='warning'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return False

        def button_export_as_fusion_text_comp(self, window_id, transcription_file_path=None, export_file_path=None):
            """
            Exports the transcript as an Fusion comp file with a text node
            """

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            # get the transcription file path from the window
            transcription_file_path = window_transcription.transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Save as Fusion Comp',
                                                                initialdir=os.path.dirname(transcription_file_path),
                                                                initialfile=os.path.basename(transcription_file_path)
                                                                .replace('.transcription.json', '.comp'),
                                                                filetypes=[('Fusion Comp files', '*.comp')],
                                                                defaultextension='.comp')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled save as Fusion Comp.')
                    return False

            # get the timecode data
            timecode_data = self.get_timecode_data_from_transcription(window_id=window_id)

            if not timecode_data or not isinstance(timecode_data, tuple) or len(timecode_data) != 2:
                self.toolkit_UI_obj.notify_via_messagebox(
                    title='No timecode data found',
                    message='No timecode data was found for this transcription.\n\nAborting Fusion Comp export.',
                    message_log='No timecode data was found for this transcription. Aborting Fusion Comp export.',
                    type='error'
                )
                return False

            # write the Fusion Comp file
            if window_transcription.segments is not None \
                    or window_transcription.segments != [] \
                    or len(window_transcription) > 0:

                # write the Fusion Comp file
                TranscriptionUtils.write_fusion_text_comp(
                    transcript_segments=window_transcription.segments,
                    comp_file_path=export_file_path,
                    timeline_fps=timecode_data[0])

                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='Fusion Comp file export',
                                                          message='The Fusion Comp file was exported successfully.',
                                                          type='info'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                self.toolkit_UI_obj.notify_via_messagebox(title='No transcription data',
                                                          message='No transcription data was found.',
                                                          type='warning'
                                                          )

                # focus back on the window
                self.toolkit_UI_obj.focus_window(window_id)

                return False

        def button_detect_speakers(self, window_id, transcription_file_path=None, ignore_selection=False):
            """
            Detects the speakers in a given transcription
            """

            # get the window
            window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            # we'll use this later
            selected_time_intervals = []

            if window_transcription:
                # get the transcription file path from the window
                transcription_file_path = window_transcription.transcription_file_path

                if not ignore_selection:

                    # if there is a window_transcription, also get the selected text from the transcript
                    text, full_text, start_sec, end_sec, _ = \
                        self.get_segments_or_selection(window_id, add_to_clipboard=False,
                                                       split_by='index', timecodes=False, allow_active_segment=False)

                    # now turn the text blocks into time intervals
                    if text is not None and text and len(text) > 0:

                        # get all the time intervals based on the text blocks
                        for text_block in text:
                            selected_time_intervals.append([text_block['start'], text_block['end']])

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path received.')
                return False

            if selected_time_intervals:
                continue_message = "Speaker detection will overwrite existing speakers for the selected segments.\n\n"
                continue_message += "Do you want to continue?"
            else:
                continue_message = "Speaker detection will overwrite all existing transcription speakers.\n\n"
                continue_message += "Do want to continue?"

            if messagebox.askyesno(
                    title='Detect Speakers{}'.format(' for Selection' if selected_time_intervals else ''),
                    message="Working on this transcription while speaker detection is performed "
                            "is not recommended.\n\n" + continue_message,
                    parent=window
            ):

                # wait for a second after the user has confirmed to allow the message box to close
                time.sleep(1)
            else:
                return

            # get the speaker detection settings
            # we're not asking the user for time_intervals, but we're passing them to the function
            user_input_valid = False
            threshold = self.stAI.get_app_setting('transcription_speaker_detection_threshold', default_if_none=0.3)
            threshold_error = False
            while not user_input_valid:

                user_input = toolkit_UI.AskDialog(
                    title='Speaker Detection Settings',
                    input_widgets=[
                        {'name': 'device_name', 'label': 'Device', 'type': 'option_menu', 'default_value': 'auto',
                            'options': ['auto'] + list(self.toolkit_ops_obj.queue_devices)},
                        {'name': 'transcription_speaker_detection_threshold',
                         'label': 'Detection Threshold', 'type': 'entry_float',
                         'default_value': threshold,
                         'error': threshold_error
                         }
                    ],
                    cancel_return=False,
                    parent=window_id,
                    toolkit_UI_obj=self.toolkit_UI_obj) \
                    .value()

                if not user_input:
                    return

                # validate transcript_speaker_detection_threshold
                if not 'transcription_speaker_detection_threshold' in user_input:
                    logger.warning('No transcription_speaker_detection_threshold received. Aborting.')
                    return

                if user_input['transcription_speaker_detection_threshold'] is None \
                or user_input['transcription_speaker_detection_threshold'] == '' \
                or not 0 < float(user_input['transcription_speaker_detection_threshold']) <= 1:

                    self.toolkit_UI_obj.notify_via_messagebox(type='error', title='Invalid Threshold',
                                                              message='Speaker detection threshold '
                                                                      'must be greater than 0, but maximum 1.',
                                                              parent=window)
                    threshold = user_input['transcription_speaker_detection_threshold']
                    threshold_error = True

                    continue

                else:
                    user_input_valid = True

            queue_item_name = '{} {}'.format(window_transcription.name, '(Speaker Detection)')

            queue_item_id = self.toolkit_ops_obj.add_speaker_detection_to_queue(
                queue_item_name=queue_item_name,
                transcription_file_path=transcription_file_path,
                device_name=user_input['device_name'],
                time_intervals=selected_time_intervals
            )

            # attach a queue item observer that updates the window when the queue item is done
            self.toolkit_UI_obj.add_observer_to_window(
                window_id=window_id,
                action='{}_queue_item_done'.format(queue_item_id),
                callback=lambda: self.toolkit_UI_obj.update_transcription_window(window_id),
                dettach_after_call=True
            )

            # add transcription window update observer

            # open the queue window
            self.toolkit_UI_obj.open_queue_window()

        def button_group_questions(self, window_id, transcription_file_path=None):
            """
            Groups the questions in the transcript
            """

            # get the window
            window = self.toolkit_UI_obj.get_window_by_id(window_id)

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id)

            if window_transcription:
                # get the transcription file path from the window
                transcription_file_path = window_transcription.transcription_file_path

            # if we still don't have a transcription file path, return
            if transcription_file_path is None:
                logger.debug('No transcription file path received.')
                return False

            # warn user that this might take a while
            if len(window_transcription) > 15:

                if messagebox.askyesno(title='Group Questions',
                                       message="Working on this transcription while it's being processed "
                                               "is not recommended.\n\n"
                                               "Do you want to continue?",
                                       parent=window
                                       ):

                    # wait for a second after the user has confirmed to allow the message box to close
                    time.sleep(1)
                else:
                    return

            # ask the user for the name of the new group
            user_input = self.toolkit_UI_obj.AskDialog(
                title='Questions Group Name',
                input_widgets=[
                    {'name': 'group_name', 'label': 'Group Name:', 'type': 'entry', 'default_value': ''}
                ],
                parent=window_id,
                toolkit_UI_obj=self.toolkit_UI_obj) \
                .value()

            if not user_input or 'group_name' not in user_input or not user_input['group_name']:
                return

            queue_item_name = '{} {}'.format(window_transcription.name, '(Group Questions)')
            group_name = user_input['group_name']

            self.toolkit_ops_obj.add_group_questions_to_queue(
                queue_item_name=queue_item_name, transcription_file_path=transcription_file_path, group_name=group_name)

            # open the queue window
            self.toolkit_UI_obj.open_queue_window()

        def button_go_to_timecode(self, window_id, timecode=None):

            self.go_to_timecode_dialog(window_id, timecode)

        def delete_line(self, window_id, text_widget_line_no):
            """
            Deletes a specific line of text from the transcript and saves the file
            :param window_id:
            :param text_widget_line_no:
            :return:
            """

            window = self.toolkit_UI_obj.get_window_by_id(window_id)
            window_transcription = self.get_window_transcription(window_id=window_id)

            if text_widget_line_no > window_transcription.get_num_lines():
                return False

            # ask the user if they are sure
            if messagebox.askyesno(title='Delete line',
                                   message='Are you sure you want to delete this line?',
                                   parent=self.toolkit_UI_obj.windows[window_id],
                                   ):

                text_widget = window.text_widget

                # get the line
                tkinter_line_index = \
                    '{}.0'.format(text_widget_line_no), '{}.0'.format(int(text_widget_line_no) + 1).split(' ')

                # enable editing on the text element
                text_widget.config(state=ctk.NORMAL)

                # delete the line - doesn't work!
                # remove the line from the text widget
                text_widget.delete(tkinter_line_index[0], tkinter_line_index[1])

                # disable editing on the text element
                text_widget.config(state=ctk.DISABLED)

                # remove the line no from any window reference
                self.clean_line_from_selection(window_id=window_id, text_widget_line_no=text_widget_line_no)

                # calculate the segment index
                segment_index = int(text_widget_line_no) - 1

                # remove the line from the text list
                window_transcription.delete_segment(segment_index=segment_index)

                # mark the transcript as modified
                self.set_transcript_modified(window_id=window_id, modified=True)

                # save the transcript
                save_status = self.save_transcript(window_id=window_id)

                # let the user know what happened via the status label
                self.update_status_label_after_save(window_id=window_id, save_status=save_status)

                return True

            return False

        def delete_lines(self, window_id, text_widget_lines: list):
            """
            This deletes multiple lines from the transcript.
            :param window_id: the window id
            :param text_widget_lines: a list of text widget line indexes to delete
            """

            window = self.toolkit_UI_obj.get_window_by_id(window_id)
            window_transcription = self.get_window_transcription(window_id=window_id)

            if not window or not window_transcription:
                logger.error('Cannot delete multiple lines: no window or transcription found.')
                return False

            # ask the user if they are sure
            if messagebox.askyesno(title='Delete lines',
                                   message='Are you sure you want to delete these lines?',
                                   parent=window,
                                   ):
                
                text_widget = window.text_widget
                
                # what is the state of the text widget?
                initial_text_widget_state = text_widget.cget('state')

                # make text widget editable
                text_widget.config(state=ctk.NORMAL)

                for text_widget_line_no in text_widget_lines:

                    # make sure the line is an integer
                    text_widget_line_no = int(text_widget_line_no)

                    # the line index in the text widget (from line start to line end)
                    tkinter_line_index = '{}.0'.format(text_widget_line_no), '{}.0'.format(text_widget_line_no+1)
                    
                    # remove the line from the text widget
                    text_widget.delete(tkinter_line_index[0], tkinter_line_index[1])

                    # remove the line no from any window reference
                    self.clean_line_from_selection(window_id=window_id, text_widget_line_no=text_widget_line_no)
                    
                    # calculate the segment index to pass the change to the transcription object
                    segment_index = text_widget_line_no - 1

                    # remove the line from the text list (but only reset on the last segment)
                    window_transcription.delete_segment(
                        segment_index=segment_index, 
                        reset_segments=False if text_widget_line_no != text_widget_lines[-1] else True
                    )

                # mark the transcript as modified
                self.set_transcript_modified(window_id=window_id, modified=True)

                # save the transcript
                save_status = self.save_transcript(window_id=window_id)

                # let the user know what happened via the status label
                self.update_status_label_after_save(window_id=window_id, save_status=save_status)

                # set the text widget back to initial state
                text_widget.config(state=initial_text_widget_state)

                return True

            return False

        def get_segment(self, window_id, line=None, segment_index=None):
            """
            This returns the segment object based on the line number in the text widget or the segment index
            """

            if segment_index is None and line is not None:
                segment_index = line - 1

            if segment_index is None:
                return None

            window_transcription = self.get_window_transcription(window_id=window_id)

            if window_transcription is None:
                logger.error('Cannot get segment info No transcription found for window {}'.format(window_id))
                return None

            # get the segment info
            segment = window_transcription.get_segment(segment_index=segment_index)

            return segment

        def align_line_to_playhead(self, window_id, position, line_index=None):
            """
            Aligns a transcript line to the playhead (only works if Resolve is connected)
            by setting the start time or end time of the line to the playhead position.

            :param window_id: the window id
            :param line_index: the segment index
            :param position: the position to align to (the start or the end of the segment)
            :return: None
            """

            if line_index is None:
                # try to get the line from the active segment
                line_index = self.get_active_segment(window_id)

            if NLE.is_connected() is None:
                logger.error('Resolve is not connected.')
                return False

            move_playhead = messagebox.askokcancel(title='Move playhead',
                                                   message='Move the Resolve playhead exactly '
                                                           'where you want to align the {} of this segment, '
                                                           'then press OK to align.'.format(position),
                                                   parent=self.toolkit_UI_obj.windows[window_id]
                                                   )

            if not move_playhead:
                logger.debug('User canceled segment alignment.')
                return False

            # convert the current_tc to seconds
            current_tc_sec = self.toolkit_ops_obj.calculate_resolve_timecode_to_sec()

            # check if we actually have a timecode
            if current_tc_sec is None:
                self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                          message='Cannot align to playhead: '
                                                                  'Resolve playhead timecode not available.',
                                                          type='error')
                return False

            # convert line_index to segment_index (not segment_id!)
            segment_index = line_index - 1

            # use the transcription object
            window_transcription = self.get_window_transcription(window_id=window_id)

            # stop if the segment index is not in the transcript segments
            if segment_index > window_transcription.get_num_lines() - 1:
                logger.error('Cannot align line to playhead: no segment index found.')
                return False

            # get the segment data
            segment_data = window_transcription.get_segment(segment_index=segment_index)

            # replace the start or end time with the current_tc_sec
            if position == 'start':
                segment_data.set('start', current_tc_sec)
            elif position == 'end':
                segment_data.set('end', current_tc_sec)

            # return False if no position was specified
            # (will probably never reach this since we're checking it above)
            else:
                logger.error('No position specified for align_line_to_playhead()')
                return False

            # check if the start time is after the end time
            # and throw an error and cancel if it is
            if segment_data.start >= segment_data.end:
                self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                          message='Cannot align to playhead: '
                                                                  'Start time is after end time.',
                                                          type='error')
                return False

            # check if the start time is before the previous segment end time
            # and throw an error and cancel if it is
            if segment_index > 0:
                if segment_data.start < window_transcription.get_segment(segment_index=segment_index - 1).end:
                    self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                              message='Cannot align to playhead: '
                                                                      'Start time is before previous segment\'s end time.',
                                                              type='error')
                    return False

            # check if the end time is after the next segment start time
            # and throw an error and cancel if it is
            if segment_index < window_transcription.get_num_lines() - 1:
                if segment_data.end > window_transcription.get_segment(segment_index=segment_index + 1).start:
                    self.toolkit_UI_obj.notify_via_messagebox(title='Cannot align line to playhead',
                                                              message='Cannot align to playhead: '
                                                                      'End time is after next segment\'s start time.',
                                                              type='error')
                    return False

            # mark the transcript as modified
            self.set_transcript_modified(window_id=window_id, modified=True)

            # save the transcript
            self.save_transcript(window_id=window_id)

            return True

        def go_to_timecode_dialog(self, window_id=None, default_timecode=None):
            """
            Opens a dialog to ask the user for a timecode to go to
            """

            goto_time = None
            goto_timecode = None

            # get the transcription object for this window
            if (window_transcription := self.get_window_transcription(window_id=window_id)) is None:
                logger.warn('No transcription found for window id: {}'.format(window_id))
                return None, None

            # get the current window
            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

            # get the timecode data
            timecode_data = self.get_timecode_data_from_transcription(window_id=window_id, ask_again=True)

            # if we don't have timecode data, we'll ask the user to enter it
            if not timecode_data:
                logger.warn('No timecode data found for transcription: {}'.format(window_id))

                return

            if timecode_data and isinstance(timecode_data, tuple) \
                    and len(timecode_data) == 2 \
                    and timecode_data[0] and timecode_data[1]:

                # get the transcription object for this window
                window_transcription = self.get_window_transcription(window_id=window_id)

                # get the start_tc of the active segment so we can use it in the input
                current_sec = \
                    window_transcription.get_segment(segment_index=self.get_active_segment(window_id=window_id)).start

                # use the timecode data
                fps = timecode_data[0]
                start_tc = timecode_data[1]
                default_timecode = window_transcription.seconds_to_timecode(seconds=current_sec,
                                                                            fps=fps,
                                                                            start_tc_offset=start_tc)

                # loop this until we return something
                while goto_time is None:

                    # create a list of widgets for the input dialogue
                    input_widgets = [
                        {'name': 'goto_timecode', 'label': 'Timecode:', 'type': 'entry',
                         'default_value': default_timecode}
                    ]

                    # then we call the ask_dialogue function
                    user_input = self.toolkit_UI_obj.AskDialog(title='Go To Timecode',
                                                               input_widgets=input_widgets,
                                                               parent=window,
                                                               cancel_return=None,
                                                               toolkit_UI_obj=self.toolkit_UI_obj
                                                               ).value()

                    # if the user canceled, return None
                    if user_input is None:
                        return None

                    # validation happens here
                    # if the user input is not a valid timecode, we'll ask them to try again
                    try:

                        goto_timecode = Timecode(fps, user_input['goto_timecode'])

                        self.toolkit_UI_obj \
                            .sync_current_tc_to_transcript(window_id=window_id,
                                                           timecode=goto_timecode, fps=fps, start_tc=start_tc)

                        goto_time = True

                    except ValueError or IndexError:
                        default_timecode = user_input['goto_timecode']
                        goto_time = None

                        # notify the user that the timecode is invalid
                        self.toolkit_UI_obj.notify_via_messagebox(title='Timecode error',
                                                                  message='Invalid Timecode\n"{}".\n\nTry again.'
                                                                  .format(user_input['goto_timecode']),
                                                                  message_log='Invalid Timecode "{}".'
                                                                  .format(user_input['goto_timecode']),
                                                                  type='warning',
                                                                  parent=window
                                                                  )

        def ask_for_transcription_timecode_data(self,
                                                window_id,
                                                default_start_tc='',
                                                default_fps='',
                                                transcription=None):
            """
            Opens a dialog to ask the user for timeline framerate and start time.
            And then saves the data to the transcription data dict.
            :param window_id: the window id
            :param default_start_tc: the default start timecode
            :param default_fps: the default framerate
            :return: timeline_fps, timeline_start_tc or None, None
            """

            # if a transcription was passed, use that
            if isinstance(transcription, Transcription):
                window_transcription = transcription

            # otherwise get the transcription object for this window
            elif (window_transcription := self.get_window_transcription(window_id=window_id)) is None:
                logger.warn('No transcription found for window id: {}'.format(window_id))
                return None, None

            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

            # try to get the default start timecode and fps from the transcription
            # to use them in the input dialogue
            default_start_tc = window_transcription.timeline_start_tc
            default_fps = window_transcription.timeline_fps

            # create a list of widgets for the input dialogue
            input_widgets = [
                {'name': 'info', 'label': 'Please enter the timecode info for the transcription {}.'
                 .format(window_transcription.name), 'label_split': 52, 'type': 'label'},
                {'name': 'timeline_start_tc', 'label': 'Start Timecode:', 'type': 'entry',
                 'default_value': default_start_tc},
                {'name': 'timeline_fps', 'label': 'Frame Rate:', 'type': 'entry',
                 'default_value': default_fps}
            ]

            start_tc = None
            fps = None

            # loop this until we return something
            while start_tc is None or fps is None:

                try:
                    # then we call the ask_dialogue function
                    user_input = self.toolkit_UI_obj.AskDialog(title='Timeline Timecode Info',
                                                               input_widgets=input_widgets,
                                                               parent=window,
                                                               cancel_return=None,
                                                               toolkit_UI_obj=self.toolkit_UI_obj
                                                               ).value()

                    # if the user clicked cancel, stop the loop
                    if user_input is None:
                        return None, None
                except:
                    logger.error('Error while asking for timecode data.', exc_info=True)
                    return None, None

                # validate the user input
                try:
                    # try to see if the timecode is valid
                    start_tc = Timecode(user_input['timeline_fps'], user_input['timeline_start_tc'])

                    # set the new timecode data
                    window_transcription.set_timecode_data(
                        timeline_fps=user_input['timeline_fps'],
                        timeline_start_tc=user_input['timeline_start_tc']
                    )

                    logger.debug('Set timecode data for {}'.format(window_transcription.transcription_file_path))

                    # if we reached this point, return the fps and start_tc
                    return user_input['timeline_fps'], user_input['timeline_start_tc']

                except:

                    logger.warning('Invalid Timecode or Frame Rate: {} @ {}'
                                   .format(user_input['timeline_start_tc'], user_input['timeline_fps']),
                                   exc_info=True
                                   )

                    # notify user
                    self.toolkit_UI_obj.notify_via_messagebox(title='Timecode or Frame Rate error',
                                                              message="The Start Timecode or Frame Rate "
                                                                      "you entered is invalid. Please try again.",
                                                              message_log="Invalid Timecode or Frame Rate.",
                                                              parent=window,
                                                              type='warning')

        def get_timecode_data_from_transcription(self, window_id, notify_if_fail=False, ask_again=False):
            """
            Gets the timecode data from the transcription data dict.
            :param window_id: the window id
            :param notify_if_fail: if True, will notify the user if the timecode data
            :return: tuple of timeline_fps, timeline_start_tc, or None, None if no timecode data was found
            """

            # get the transcription object from the window
            window_transcription = self.get_window_transcription(window_id=window_id)

            # get the current window
            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)

            # if the transcription data is None, it means that the transcription data is invalid
            # there's not much to do, so notify the user
            if window_transcription is None:
                # show error message
                self.toolkit_UI_obj.notify_via_messagebox(title='Cannot get timecode data',
                                                          message='Cannot get timecode data: '
                                                                  'Transcription data invalid or not found',
                                                          message_log='Transcription data invalid or not found.',
                                                          parent=window,
                                                          type='error')
                return None, None

            timecode_data = window_transcription.get_timecode_data()

            # if the transcription data is False, it means that the transcription exists
            # but it doesn't contain timecode data
            # so the user will be asked if they want to enter the timecode data manually (remember his choice)
            if (timecode_data is False or timecode_data is [None, None]) \
                    and (ask_again or not getattr(window, 'asked_for_timecode', False)):

                # ask the user if they want to enter the timecode data manually
                if messagebox.askyesno(title='Timecode data not found',
                                       message='Frame rate or start timecode not found in transcription.\n\n'
                                               'Would you like to enter them now?',
                                       parent=window,
                                       ):
                    # ask the user for the timecode data
                    timecode_data = self.ask_for_transcription_timecode_data(window_id=window_id)

                # if the user clicked no, remember this for next time (this session only)
                else:

                    # remember this for next time
                    setattr(window, 'asked_for_timecode', True)

            # if the timecode data is valid, set the fps and start timecode
            if timecode_data is not None and timecode_data is not False \
                    and isinstance(timecode_data, tuple) and len(timecode_data) == 2:
                timeline_fps = timecode_data[0] if timecode_data[0] else None
                timeline_start_tc = Timecode(timeline_fps, timecode_data[1]) if timecode_data[1] else None

                return timeline_fps, timeline_start_tc

            if notify_if_fail:
                self.toolkit_UI_obj.notify_via_messagebox(
                    title='No timecode data',
                    type="warning",
                    message='No timecode data found in transcription.\n\nUsing seconds as time units.',
                    message_log='No timecode data found in transcription {}. Using seconds as time units.'
                    .format(window_transcription.transcription_file_path),
                    parent=window,
                )
            else:
                logger.debug('No timecode data found in transcription {}. Using seconds as time units.'
                             .format(window_transcription.transcription_file_path))

            # last resort, just return None, None
            return None, None

        def get_window_selected_segments(self, window_id, list_only=False):
            """
            This returns the list of selected segments for the given window_id

            :param window_id: the window id
            :param list_only: if True, will return only the list of selected segments,
                               otherwise will return the full dict containing {line: segment} pairs
            """

            # if the window has selected segments
            if window_id in self.selected_segments:
                # return either the list or the full dict
                return list(self.selected_segments[window_id].values()) \
                    if list_only else self.selected_segments[window_id]

            return None

        def has_selected_segments(self, window_id):
            """
            Checks if any segments are selected in the transcript
            """

            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:
                return True

            return False

        def is_selected(self, window_id, line=None, segment=None):
            """
            Tell whether the given text widget line or transcription segment is selected
            """

            # if the line is None, calculate the line number from the segment
            if line is None and segment is not None:
                line = int(segment) + 1

            # if the segment is None, return False
            if line is None:
                return False

            # if the window has selected segments
            if self.has_selected_segments(window_id=window_id):

                # if the segment is in the selected segments list
                if line in self.selected_segments[window_id]:
                    return True

            return False

        def get_segments_or_selection_indexes(self, window_id, allow_active_segment=True):
            """
            This returns a list of text widget indexes for either the selected segments
            or the active segment if no selection exists for the window
            """

            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:

                # we're only interested in the keys (the widget line number) of the selected segments
                return list(self.selected_segments[window_id].keys())

            # if there are no selected segments, return the active segment
            elif allow_active_segment:
                return [self.get_active_segment(window_id=window_id)]

            return None

        def get_segments_or_selection(self, window_id, add_to_clipboard=False, split_by=None, timecodes=True,
                                      allow_active_segment=True, add_time_column=False):
            """
            Used to extract the text from either the active segment or from the selection
            Will return the text, and the start and end times

            If the split_by parameter is 'index', the text will be split into blocks of text that
            are next to each other in the main transcript_segments[window_id] list.

            If the split_by parameter is 'time', the text will be split into blocks of text that
            have no time gaps between them.

            If timecodes is true, the return will also include the text blocks' start and end timecodes
            (if Resolve is available)

            If add_to_clipboard is True, the function copies the full_text to the clipboard

            :param window_id:
            :param add_to_clipboard:
            :param split_by: None, 'index' or 'time'
            :param timecodes: if True, will return the timecodes of the text blocks
            :param allow_active_segment: if True, will return the active segment if no selection is found
            :param add_time_column: if True, will add a time column to the text
            :param timecodes
            :return: text, full_text, start_sec, end_sec, transcription_segments
            """

            # get the transcription object for the given window_id
            window_transcription = self.get_window_transcription(window_id=window_id)

            # the full text string
            full_text = ''

            # the return text list
            text = [{}]

            # the transcription segments to return
            transcription_segments = []

            # the start and end times of the entire selection
            start_sec = None
            end_sec = None

            # if timecodes is True,
            # get the timecode data from the transcription data
            if timecodes:

                timeline_fps, timeline_start_tc \
                    = self.get_timecode_data_from_transcription(window_id=window_id, notify_if_fail=False)

                # if no timecode was received, disable timecodes
                if not timeline_start_tc or timeline_start_tc is None:
                    timecodes = False

            # if we have some selected segments, use their start and end times
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0:

                start_segment = None
                end_segment = None
                start_sec = 0
                end_sec = 0

                from operator import itemgetter

                # first sort the selected segments by start time
                # (but we are losing the line numbers which are normally in the dict keys!)
                sorted_selected_segments = sorted(self.selected_segments[window_id].values(),
                                                  key=lambda segment: segment.start)

                # use this later to see where the selected_segment is in the original transcript
                transcript_segment_index = 0
                prev_transcript_segment_index = None
                prev_segment_end_time = None

                # keep track of text chunks in case the split by parameter was passed
                current_chunk_num = 0

                # add each text
                for selected_segment in sorted_selected_segments:

                    # see where this selected_segment is in the original transcript
                    transcript_segment_index = \
                        window_transcription.get_segment(segment_id=selected_segment.id).get_index()

                    # split each blocks of text that are next to each other in the main transcript_segments[window_id] list
                    if split_by == 'index':

                        # assign a value if this is the first transcript_segment_index of this iteration
                        if prev_transcript_segment_index is None:
                            prev_transcript_segment_index = transcript_segment_index

                        # if the segment is not right after the previous segment that we processed
                        # it means that there are other segments between them which haven't been selected
                        elif prev_transcript_segment_index + 1 != transcript_segment_index:
                            current_chunk_num = current_chunk_num + 1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text + '\n[...]\n'

                    # split into blocks of text that have no time gaps between them
                    if split_by == 'time':

                        # assign the end time of the first selected segment
                        if prev_segment_end_time is None:
                            prev_segment_end_time = selected_segment['end']

                        # if the start time of the current segment
                        # doesn't match with the end time of the previous segment
                        elif selected_segment.start != prev_segment_end_time:
                            current_chunk_num = current_chunk_num + 1
                            text.append({})

                            # show that there might be missing text from the transcription
                            full_text = full_text + '\n[...]\n'

                    # add the current segment text to the current text chunk
                    text[current_chunk_num]['text'] = \
                        text[current_chunk_num]['text'] + '\n' + selected_segment.text.strip() \
                            if 'text' in text[current_chunk_num] else selected_segment.text

                    # add the start time to the current text block
                    # but only for the first segment of this text block
                    # and we determine that by checking if the start time is not already set
                    if 'start' not in text[current_chunk_num]:
                        text[current_chunk_num]['start'] = selected_segment.start

                        # also calculate the start timecode of this text chunk (only if Resolve available)
                        # the end timecode isn't needed at this point, so no sense in wasting resources
                        text[current_chunk_num]['start_tc'] = None
                        if timecodes:

                            # init the segment start timecode object
                            # but only if the start seconds are larger than 0
                            if float(selected_segment.start) > 0:
                                segment_start_timecode = Timecode(timeline_fps,
                                                                  start_seconds=selected_segment.start)

                                # factor in the timeline start tc and use it for this chunk
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc + segment_start_timecode)

                            # otherwise use the timeline_start_timecode
                            else:
                                text[current_chunk_num]['start_tc'] = str(timeline_start_tc)

                            # add it to the beginning of the text
                            text[current_chunk_num]['text'] = \
                                text[current_chunk_num]['start_tc'] + ':\n' + text[current_chunk_num]['text'].strip()

                            # add it to the full text body
                            # but only if we're not adding a time column later
                            if not add_time_column:
                                full_text = full_text + '\n' + text[current_chunk_num]['start_tc'] + ':\n'

                    # add the end time of the current text chunk
                    text[current_chunk_num]['end'] = selected_segment.end

                    # add the time to the full text, if this was requested
                    if add_time_column:
                        # use timecode or seconds depending on the timecodes parameter
                        time_column = text[current_chunk_num]['start_tc'] \
                            if timecodes else '{:.2f}'.format(text[current_chunk_num]['start'])

                        full_text = '{}{}\t'.format(full_text, str(time_column))

                    # add the segment text to the full text variable
                    full_text = (full_text + selected_segment.text.strip() + '\n')

                    # remember the index for the next iteration
                    prev_transcript_segment_index = transcript_segment_index

                    # split the text by each line, no matter if they're next to each other or not
                    if split_by == 'line':
                        current_chunk_num = current_chunk_num + 1
                        text.append({})

                        transcription_segments.append(selected_segment)

            # if there are no selected segments on this window
            # get the text of the active segment
            else:
                # if active segments are not allowed
                if not allow_active_segment:
                    return None, None, None, None, None

                # if there is no active_segment for the window
                if window_id not in self.active_segment:
                    # create one
                    self.active_segment[window_id] = 1

                # get the line number from the active segment
                line = self.active_segment[window_id]

                # we need to convert the line number to the segment_index used in the transcript_segments list
                segment_index = line - 1

                transcript_segment = window_transcription.get_segment(segment_index=segment_index)

                # get the text from the active segment
                full_text = transcript_segment.text.strip()

                # return the segment as a list
                transcription_segments = [transcript_segment]

                # get the start and end times from the active segment
                start_sec = transcript_segment.start
                end_sec = transcript_segment.end

                # add this to the return list
                text = [{'text': full_text.strip(), 'start': start_sec, 'end': end_sec, 'start_tc': None}]

                if NLE.is_connected() and timecodes:
                    start_seconds = start_sec if int(start_sec) > 0 else 0.01
                    start_tc = None

                    # init the segment start timecode object
                    # but only if the start seconds are larger than 0
                    if start_sec > 0:
                        segment_start_timecode = Timecode(timeline_fps, start_seconds=start_sec)

                        # factor in the timeline start tc and use it for this chunk
                        start_tc = str(timeline_start_tc + segment_start_timecode)

                    # otherwise use the timeline_start_timecode
                    else:
                        start_tc = str(timeline_start_tc)

                    # add it at the beginning of the text body
                    full_text = start_tc + ':\n' + full_text

                    # add this to the return list
                    text = [{'text': full_text.strip(), 'start': start_sec, 'end': end_sec, 'start_tc': start_tc}]

            # remove the last empty text chunk
            if 'text' not in text[-1]:
                text.pop()

            if add_to_clipboard:
                self.root.clipboard_clear()
                self.root.clipboard_append(full_text.strip())
                logger.debug('Copied segments to clipboard')

            # now get the start_sec and the end_sec for the whole text
            start_sec = text[0]['start']
            end_sec = text[-1]['end']

            return text, full_text, start_sec, end_sec, transcription_segments

        def go_to_selected_time(self, window_id=None, position=None, ignore_selection=False):

            window_transcription = self.get_window_transcription(window_id=window_id)

            # if the transcription has no segments, just ignore this
            if not window_transcription.has_segments:
                return None

            # if we have some selected segments, use their start and end times
            if window_id in self.selected_segments and len(self.selected_segments[window_id]) > 0 \
                    and not ignore_selection:

                start_sec = None
                end_sec = None

                # go though all the selected_segments and get the lowest start time and the highest end time
                for segment_index in self.selected_segments[window_id]:

                    # get the start time of the earliest selected segment
                    if start_sec is None or self.selected_segments[window_id][segment_index].start < start_sec:
                        start_sec = self.selected_segments[window_id][segment_index].start

                    # get the end time of the latest selected segment
                    if end_sec is None or self.selected_segments[window_id][segment_index].end > end_sec:
                        end_sec = self.selected_segments[window_id][segment_index].end

            # otherwise use the active segment start and end times
            else:

                # if there is no active_segment for the window, create one
                if window_id not in self.active_segment:
                    self.active_segment[window_id] = 1

                # get the text_widget_line number from the active segment
                text_widget_line = self.active_segment[window_id]

                # we need to convert the line number to the segment_index used in the transcript_segments list
                segment_index = text_widget_line - 1

                # get the start and end times from the active segment
                start_sec = window_transcription.get_segment(segment_index=segment_index).start
                end_sec = window_transcription.get_segment(segment_index=segment_index).end

            # decide where to go depending on which position requested
            if position == 'end':
                seconds = end_sec
            else:
                seconds = start_sec

            # move playhead to seconds
            self.toolkit_ops_obj.go_to_time(seconds=seconds)

            # update the transcription window
            self.toolkit_UI_obj.update_transcription_window(window_id=window_id)

        def get_active_segment(self, window_id=None, initial_value=0):
            """
            This returns the active segment number for the window with the window_id
            :param window_id:
            :return:
            """

            # if there is no active_segment for the window, create one
            # this will help us keep track of where we are with the cursor
            if window_id not in self.active_segment:
                # but start with 0, considering that it will be re-calculated below
                self.active_segment[window_id] = initial_value

            # same as above for the last_active_segment
            if window_id not in self.last_active_segment:
                # but start with 0, considering that it will be re-calculated below
                self.last_active_segment[window_id] = initial_value

            return self.active_segment[window_id]

        def get_transcription_window_text_widget(self, window_id=None):

            if window_id is None:
                logger.error('No window id was passed.')
                return None

            # try to get the text widget from the window by name
            try:
                text_element = \
                    self.toolkit_UI_obj.windows[window_id].nametowidget('middle_frame.text_form_frame.transcript_text')

            except Exception as e:
                logger.error('Could not get the text widget from the window {}'.format(window_id), exc_info=True)
                return None

            return text_element

        def set_active_segment(self, window_id=None, text_widget=None, text_widget_line=None, line_calc=None):

            window_transcription = self.get_window_transcription(window_id=window_id)

            # if no text element is passed,
            # try to get the transcript text element from the window with the window_id
            if text_widget is None and self.toolkit_UI_obj is not None and window_id is not None \
                    and window_id in self.toolkit_UI_obj.windows:
                text_widget = self.get_transcription_window_text_widget(window_id=window_id)

            # if no text element is found, return
            if text_widget is None:
                return False

            # remove any active segment tags
            text_widget.tag_delete('l_active')

            # count the number of lines in the text
            text_num_lines = window_transcription.get_num_lines()

            # initialize the active segment number
            self.active_segment[window_id] = self.get_active_segment(window_id)

            # interpret the line number correctly
            # by passing line_calc, we can add that to the current line number
            if text_widget_line is None and line_calc:
                text_widget_line = self.active_segment[window_id] + line_calc

            # remove the active segment if no text_widget_line or line_calc was passed
            if text_widget_line is None and line_calc is None:
                del self.active_segment[window_id]
                return False

            # make sure we're using integers
            if text_widget_line is not None:
                text_widget_line = int(text_widget_line)

            # if passed text_widget_line is lower than 1, go to the end of the transcript
            if text_widget_line < 1:
                text_widget_line = text_num_lines

            # if the text_widget_line is larger than the number of lines, go to the beginning of the transcript
            elif text_widget_line > text_num_lines:
                text_widget_line = 1

            # first copy the active segment line number to the last active segment line number
            self.last_active_segment[window_id] = self.active_segment[window_id]

            # then update the active segment
            self.active_segment[window_id] = text_widget_line

            # now tag the active segment
            text_widget.tag_add("l_active", "{}.0".format(text_widget_line), "{}.end+1c".format(text_widget_line))
            # text_element.tag_config('l_active', foreground=self.toolkit_UI_obj.theme_colors['white'])

            # add some nice colors
            text_widget.tag_config('l_active', foreground=self.toolkit_UI_obj.theme_colors['superblack'],
                                   background=self.toolkit_UI_obj.theme_colors['normal'])

            # also scroll the text element to the line
            text_widget.see(str(text_widget_line) + ".0")

            # make the text element the currently focused widget
            text_widget.focus_set()

        def clear_selection(self, window_id=None, text_element=None):
            """
            This clears the segment selection for the said window
            :param window_id:
            :return:
            """

            if window_id is None:
                return False

            self.selected_segments[window_id] = {}

            self.selected_segments[window_id].clear()

            if text_element is None:
                text_element = self.get_transcription_window_text_widget(window_id=window_id)

            if text_element is not None:
                text_element.tag_delete("l_selected")

        def clean_line_from_selection(self, window_id, text_widget_line_no):
            """
            This removes the given line from both the active segment and the selection
            """

            if window_id is None or text_widget_line_no is None:
                return False

            # if the window has selected segments and the line is in the selection
            if window_id in self.selected_segments and text_widget_line_no in self.selected_segments[window_id]:
                # remove it
                del self.selected_segments[window_id][text_widget_line_no]

            # if the active segment is the same as the line we're removing
            if window_id in self.active_segment and self.active_segment[window_id] == text_widget_line_no:
                self.set_active_segment(window_id=window_id, text_widget_line=text_widget_line_no)


        def text_indices_to_selection(self, window_id=None, text_element=None, text_indices: int or list = None):
            """
            Given a list of text indices (for eg. ['16.8', '18.52', '20.11']),
            this function takes each indices and selects the corresponding segment
            """

            if window_id is None or text_element is None:
                logger.warning('Unable to select segments based on text indices '
                               'because no window id or text element was passed.')
                return False

            if text_indices is None:
                logger.warning('Unable to select segments based on text indices '
                               'because no text indices were passed.')
                return False

            if isinstance(text_indices, int):
                text_indices = [text_indices]

            # first clear the selection
            self.clear_selection(window_id=window_id, text_element=text_element)

            for text_index in text_indices:
                # get the line number from the text index
                line = int(text_index.split('.')[0])

                # select the segment
                self.segment_to_selection(window_id=window_id, text_element=text_element, line=line)

        def segment_to_selection(self,
                                 window_id=None,
                                 text_element=None,
                                 line: Union[int, List[int], List[TranscriptionSegment]] = None,
                                 only_add=False):
            """
            This either adds or removes a segment to a selection,
            depending if it's already in the selection or not

            If line is a list, it will add all the lines in the list to the selection and remove the rest

            :param window_id:
            :param text_element:
            :param line: Either a line no. a list of line numbers, or a list of segments
            :param only_add: Do not deselect if the line is not part of the selection
            :return:
            """

            window_transcription = self.get_window_transcription(window_id=window_id)

            # if no text element is passed,
            # try to get the transcript text element from the window with the window_id
            if text_element is None and self.toolkit_UI_obj is not None and window_id is not None \
                    and window_id in self.toolkit_UI_obj.windows:
                text_element = self.get_transcription_window_text_widget(window_id=window_id)

            if text_element is None or line is None:
                logger.warning('Unable to select segment - no text element or line was passed.')
                return False

            # if there is no selected_segments dict for the current window, create one
            if window_id not in self.selected_segments:
                self.selected_segments[window_id] = {}

            # if a list of lines (or segments) was passed, add all the lines to the selection
            if type(line) is list:

                # first clear the selection
                self.clear_selection(window_id=window_id, text_element=text_element)

                # select all the lines in the list
                for line_num in line:

                    # if the "lines" are segments, get the line number based on the segment.id
                    if type(line_num) is TranscriptionSegment:

                        # the segment is the line_num item
                        segment = line_num

                        # and the line_num is the segment_index
                        line_num = segment.get_index() + 1

                    else:
                        # convert the line number to segment_index
                        segment_index = line_num - 1

                        segment = window_transcription.get_segment(segment_index=segment_index)

                    self.selected_segments[window_id][line_num] = segment

                    # tag the text on the text element
                    text_element.tag_add("l_selected", "{}.0".format(line_num), "{}.end+1c".format(line_num))

                    # raise the tag so we can see it above other tags
                    text_element.tag_raise("l_selected")

                    # color the tag accordingly
                    text_element.tag_config('l_selected', foreground=toolkit_UI.theme_colors['selected_blue_text'],
                                            background=self.toolkit_UI_obj.theme_colors['selected_blue_bg'])

                return True

            # if a single line was passed, add or remove it from the selection
            else:

                # convert the line number to segment_index
                segment_index = line - 1

                # if the segment is in the transcript segments dict
                if line in self.selected_segments[window_id] and not only_add:

                    # remove it
                    del self.selected_segments[window_id][line]

                    # remove the tag on the text in the text element
                    text_element.tag_remove("l_selected", "{}.0".format(line), "{}.end+1c".format(line))

                # otherwise add it
                elif line not in self.selected_segments[window_id]:
                    self.selected_segments[window_id][line] \
                        = window_transcription.get_segment(segment_index=segment_index)

                    # tag the text on the text element
                    text_element.tag_add("l_selected", "{}.0".format(line), "{}.end+1c".format(line))

                    # raise the tag so we can see it above other tags
                    text_element.tag_raise("l_selected")

                    # color the tag accordingly
                    text_element.tag_config('l_selected', foreground=toolkit_UI.theme_colors['selected_blue_text'],
                                            background=self.toolkit_UI_obj.theme_colors['selected_blue_bg'])

            return True

        def go_to_first_selected_segment(self, window_id=None):
            """
            This function will go to the first selected segment in the transcript,
            but only if there's no active segment

            :param window_id:

            """

            # get the text element
            text_element = self.get_transcription_window_text_widget(window_id=window_id)

            # get the first selected segment by looking at the l_selected tag
            first_selected_segment = text_element.tag_ranges('l_selected')

            # if there is a selected segment
            if first_selected_segment:
                # go to that segment using see
                text_element.see(first_selected_segment[0])

        def auto_add_selection_to_group(self, t_window_id: str, confirm=False, auto_add_button=None) -> None:
            """
            This function checks if the auto add to group option is enabled in the UI
            and if it is, it will add the selected segments to the group that is selected in the UI
            """

            # the transcription window
            t_window = self.toolkit_UI_obj.get_window_by_id(t_window_id)

            window_groups_module = t_window.transcript_groups_module

            # if a group is selected
            # and the auto add to group option is enabled
            if window_groups_module.selected_group_id is not None and window_groups_module.update_segments:

                window_groups_module.update_group_segments()

            # if a group is selected
            # but the auto add to group option is disabled
            elif window_groups_module.selected_group_id is not None and not window_groups_module.update_segments:

                # deselect the group to avoid confusion
                window_groups_module.deselect_group(keep_segment_selection=True)

            return

        def on_press_add_segment(self, event, window_id=None, text_widget=None):
            """
            This adds a new segment to the transcript
            :param event: the event that triggered this function
            :param window_id: the window id
            :param text_widget: the text widget
            :return:
            """

            if window_id is None or text_widget is None:
                return False

            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)
            window_transcription = self.get_window_transcription(window_id=window_id)

            # get the cursor position where the event was triggered (key was pressed)
            # and the last character of the line
            text_widget_line, text_widget_char, text_widget_last_char = \
                self.get_current_segment_chars(text=text_widget)

            # calculate the segment indexes (not the id!)
            segment_index = int(text_widget_line) - 1
            next_segment_index = segment_index + 1

            # get the current segment
            current_segment = window_transcription.get_segment(segment_index=segment_index)

            # first, let's understand if we're splitting words,
            # or simply pressing enter at the beginning or the end of a line:
            # are we at the end of the line?
            # or we at the beginning of the line?
            # or are the characters after the cursor spaces?
            sentence_split = True
            if text_widget_char == text_widget_last_char\
                or text_widget_char == '0'\
                or text_widget.get(
                    "{}.{}".format(text_widget_line, text_widget_char),
                    "{}.end".format(text_widget_line)
                ).strip() == '':
                sentence_split = False

            # was shift pressed?
            shift_pressed = event.state & 0x1 != 0

            # if shift was pressed, and we're not splitting sentences,
            # it means that we're adding a meta line
            if shift_pressed and not sentence_split:

                # insert the new line at the end of the current segment
                # if we're not at the beginning of the line:
                if text_widget_char != '0':
                    text_widget.insert("{}.end".format(text_widget_line), "\n ")

                    # add the l_meta tag to the new line
                    self._tag_meta_segment(text_widget=text_widget, line_no=int(text_widget_line)+1)

                    # for this case, we need to use the start time of the next segment
                    next_segment = window_transcription.get_segment(segment_index=segment_index+1)

                    # create new meta segment object
                    new_segment = TranscriptionSegment({
                        'text': ' ',
                        'start': next_segment.start if next_segment is not None else current_segment.end,
                        'end': next_segment.start if next_segment is not None else current_segment.end,
                        'meta': True
                    })

                # otherwise insert the new line before the current segment
                else:
                    text_widget.insert("{}.0-1c".format(text_widget_line), "\n")

                    # then we need to insert the new segment before the current segment in the transcription
                    next_segment_index = segment_index

                    # add the l_meta tag to the new line
                    self._tag_meta_segment(text_widget=text_widget, line_no=text_widget_line)

                    # create new meta segment object
                    new_segment = TranscriptionSegment({
                        'text': ' ',
                        'start': current_segment.start,
                        'end': current_segment.start,
                        'meta': True
                    })

                self._format_meta_tags(text_widget=text_widget)

                # add the new segment to the window transcription
                window_transcription.add_segment(segment=new_segment, segment_index=next_segment_index)

                # update the transcript_modified flag
                self.set_transcript_modified(window_id=window_id, modified=True)

                # save the transcript
                self.save_transcript(window_id=window_id)

                return 'break'

            # use the start and end times of the current segment as min and max
            split_time_seconds_min = current_segment.start
            split_time_seconds_max = current_segment.end

            # get the current focus out event for the text widget
            text_widget_focus_out_event = text_widget.bind('<FocusOut>')

            def add_back_focus_out_event():
                """
                This adds back the focus out event to the text widget
                """
                text_widget.bind('<FocusOut>', text_widget_focus_out_event)

            # disable the focus out event on the text widget to avoid triggering it when the dialogs open
            text_widget.unbind('<FocusOut>')

            # if resolve is connected, get the timecode from resolve
            if NLE.is_connected():

                # ask the user to move the playhead in Resolve to where the split should happen via info dialog
                move_playhead = messagebox.askokcancel(title='Move playhead',
                                                       message='Move the Resolve playhead exactly '
                                                               'where you want to split the segment, '
                                                               'then press OK here to split.',
                                                       parent=window
                                                       if window_id is not None else None
                                                       )

                if not move_playhead:
                    logger.debug('User canceled segment split.')
                    add_back_focus_out_event()
                    return 'break'

                # convert the current resolve timecode to seconds
                split_time_seconds = self.toolkit_ops_obj.calculate_resolve_timecode_to_sec()

            # if resolve isn't connected, ask the user to enter the timecode manually
            else:

                # keep asking the user to enter the timecode until they enter a valid one
                # or until they cancel
                while True:

                    input_widgets = [
                        {'name': 'message',
                         'label': 'Where should we split this segment?\n\nEnter a value between {} and {}.'
                            .format(split_time_seconds_min, split_time_seconds_max),
                         'type': 'label', 'style': 'main'
                         },
                        {'name': 'split_time', 'label': 'Split Time:', 'type': 'entry',
                         'default_value': split_time_seconds_min}
                    ]

                    user_input = toolkit_UI.AskDialog(
                        title='Split Transcript Line',
                        input_widgets=input_widgets,
                        parent=window,
                        cancel_return=False,
                        toolkit_UI_obj=self.toolkit_UI_obj) \
                        .value()

                    split_time_seconds = user_input['split_time'] if user_input else None

                    # if the user didn't specify the split time, cancel this
                    if not split_time_seconds and split_time_seconds != '':
                        add_back_focus_out_event()
                        return 'break'

                    try:
                        if float(split_time_seconds) >= float(split_time_seconds_max):
                            self.toolkit_UI_obj.notify_via_messagebox(
                                title='Time Value Error',
                                message="The time you entered goes past the end time of "
                                        "the segment you're splitting.\n\n"
                                        "You can only split a segment between its start and end times.",
                                parent=window,
                                type='error')
                            continue

                        elif float(split_time_seconds) <= float(split_time_seconds_min):
                            self.toolkit_UI_obj.notify_via_messagebox(
                                title='Time Value Error',
                                message="The time you entered is before the start time of "
                                        "the segment you're splitting.\n\n"
                                        "You can only split a segment between its start and end times.",
                                parent=window,
                                type='error')
                            continue

                    except ValueError:
                        self.toolkit_UI_obj.notify_via_messagebox(
                            title='Time Value Error',
                            message='Invalid time value entered. Try again.'.format(split_time_seconds),
                            type='error')
                        continue

                    except:
                        logger.error('Unable to split segment.', exc_info=True)
                        add_back_focus_out_event()

                        # focus back on the text widget
                        text_widget.focus()
                        return 'break'

            # Re-enable the <FocusOut> event after AskDialog is done
            add_back_focus_out_event()

            # focus back on the text widget
            text_widget.focus()

            # set the insert position to text_widget_line,text_widget_char
            text_widget.mark_set(ctk.INSERT, "{}.{}".format(text_widget_line, text_widget_char))

            # split the text in the text widget at the cursor position
            text_widget.insert(ctk.INSERT, "\n")

            # get the new line number
            new_line_number = int(text_widget_line) + 1

            # set the active segment to the new segment
            # self.set_active_segment(window_id=window_id, text_widget=text_widget, text_widget_line=new_line_number)

            # get the new line index
            new_line_index = "{}.0".format(new_line_number)

            # initialize the new_line dict
            new_segment_data = dict()

            # set the new segment text
            new_segment_data['text'] = text_widget.get(new_line_index, "{}.end".format(new_line_number))

            # the end time of the next segment is the end of the current segment
            new_segment_data['end'] = current_segment.end

            # the split time becomes the start time of the new line and also the end of the current segment
            new_segment_data['start'] = split_time_seconds

            # set the end time of the current segment to the split time
            current_segment.set('end', split_time_seconds)

            # get the current segment text (what remained)
            current_segment_text = \
                text_widget.get("{}.0".format(text_widget_line), "{}.{}".format(text_widget_line, text_widget_char))

            # set the current segment text to the text before the split
            current_segment.set('text', current_segment_text)

            # create new segment object
            new_segment = TranscriptionSegment(new_segment_data)

            # add the new segment to the window transcription
            window_transcription.add_segment(segment=new_segment, segment_index=next_segment_index)

            # update the transcript_modified flag
            self.set_transcript_modified(window_id=window_id, modified=True)

            # save the transcript
            self.save_transcript(window_id=window_id)

            # prevent RETURN key from adding another line break in the text
            return 'break'

        def edit_transcript(self, window_id=None):

            if window_id is None:
                logger.error('Unable to edit transcript - no window id or text widget was passed.')
                return False

            # get the text widget from the window
            window = self.toolkit_UI_obj.get_window_by_id(window_id=window_id)
            text = window.text_widget

            # get the window transcription
            window_transcription = self.get_window_transcription(window_id=window_id)

            # ignore if the transcription doesn't have any segments
            if not window_transcription.has_segments:
                return None

            text.focus()

            # enable typing mode to disable some shortcuts
            self.set_typing_in_window(window_id=window_id, typing=True)

            # enable transcript_editing for this window
            self.set_transcript_editing(window_id=window_id, editing=True)

            # deselect any groups
            window.transcript_groups_module.deselect_group()

            # deselect any segments
            self.clear_selection(window_id=window_id, text_element=text)

            # remove active segment tag
            self.set_active_segment(window_id=window_id, text_widget=text, text_widget_line=None)

            text.bind('<Return>', lambda e: self.on_press_add_segment(e, window_id=window_id, text_widget=text))

            # ESCAPE key de-focuses transcript (and implicitly saves the transcript, see below)
            text.bind('<Escape>', lambda e: self.defocus_transcript(text=text))

            # text focusout saves transcript
            text.bind('<FocusOut>', lambda e: self.on_text_widget_defocus(e, window_id=window_id))

            # BACKSPACE key at first line character merges the current and the previous segment
            text.bind(
                '<BackSpace>',
                lambda e:
                self.on_press_merge_segments(e, window_id=window_id, text_widget=text, merge_direction='previous')
            )

            # DELETE key at last line character merges the current and the next segment
            text.bind(
                '<Delete>',
                lambda e:
                self.on_press_merge_segments(e, window_id=window_id, text_widget=text, merge_direction='next')
            )

            # BIND all other key presses to the _on_transcript_key_press function
            text.bind('<KeyPress>', lambda e, l_window=window: self._on_transcript_key_press(e, window=l_window))

            self.toolkit_UI_obj.update_window_status_label(
                window_id=window_id, text='Transcript not saved.', color='bright_red')

            text.config(state=ctk.NORMAL)

        def _on_transcript_key_press(self, event, window):
            """
            This handles the key presses in the transcript text widget while editing
            with a few exceptions (Return Escape, BackSpace, Delete - see edit_transcript() for that)
            """

            # if it's left, right, up, down, delete, backspace, return pass it down to the text widget
            if event.keysym in ['Left', 'Right', 'Up', 'Down', 'Delete', 'BackSpace', 'Return']:
                return

            # get the line_no
            line_no, char_no = window.text_widget.index(ctk.INSERT).split('.')

            # convert to transcription segment index
            segment_index = int(line_no) - 1

            # get the transcription segment
            transcription_segment = window.transcription.get_segment(segment_index=segment_index)

            # if this is a meta segment, insert the pressed key inside the already existing l_meta tag
            # since we can't do that with a native tkinter method, we need to do it manually
            if transcription_segment.meta:

                text_widget = window.text_widget

                # capture the pressed key character
                pressed_key = event.char

                # if the current line contents shorter than 2 characters
                if len(text_widget.get('{}.0'.format(line_no), '{}.end'.format(line_no)).strip()) < 2:

                    if len(text_widget.get('{}.0'.format(line_no), '{}.end'.format(line_no)).strip()) < 1:
                        # insert pressed_key and then wrap it in the l_meta tag
                        text_widget.insert('{}.0'.format(line_no), pressed_key)

                        # move the cursor to line.1
                        text_widget.mark_set(ctk.INSERT, '{}.1'.format(line_no))
                    else:
                        # insert pressed_key and then wrap it in the l_meta tag
                        text_widget.insert('{}.1'.format(line_no), pressed_key)

                    # add the l_meta tag to the new line
                    self._tag_meta_segment(text_widget=text_widget, line_no=line_no)

                    # format the meta tags
                    self._format_meta_tags(text_widget=text_widget)

                    return 'break'

                # if we're on the first character of the line
                if char_no == '0':

                    # memorize the character at line.0
                    first_char = text_widget.get('{}.0'.format(line_no))

                    # insert the pressed key character on position line.1 ("inside" the tag)
                    window.text_widget.insert('{}.1'.format(line_no), pressed_key)

                    # delete the original character at line.0
                    window.text_widget.delete('{}.0'.format(line_no))

                    # insert the memorized character  (after the pressed key)
                    window.text_widget.insert('{}.1'.format(line_no), first_char)

                    # move the cursor to line.1
                    window.text_widget.mark_set(ctk.INSERT, '{}.1'.format(line_no))

                    return 'break'

                # if we're on the last character of the line we must be on the \n character
                elif char_no == text_widget.index('{}.end'.format(line_no)).split('.')[1]:

                    # so we need to insert the pressed key character before the \n character
                    # but first, get the character before the \n character
                    last_char = text_widget.get('{}.end-1c'.format(line_no))

                    # insert our pressed character
                    window.text_widget.insert('{}.end-1c'.format(line_no), pressed_key)

                    # remove the last character
                    window.text_widget.delete('{}.end-1c'.format(line_no))

                    # insert the memorized character (before the pressed key)
                    window.text_widget.insert('{}.end-1c'.format(line_no), last_char)

                    # move the cursor to line.end-1c
                    window.text_widget.mark_set(ctk.INSERT, '{}.end'.format(line_no))

                    return 'break'

        def add_segments_to_text_widget(self, transcription: Transcription, text_widget, clear_text_widget=True):
            """
            This function adds the segments from the transcription object to the text widget
            :param transcription: the transcription object
            :param text_widget: the text widget
            :param clear_text_widget: whether to clear the text widget before adding the segments
            """

            # get the text_widget state
            text_widget_state = text_widget.cget('state')

            # make the text widget not read-only
            text_widget.config(state=ctk.NORMAL)

            # clear first, if needed
            if clear_text_widget:
                text_widget.delete('1.0', ctk.END)

            # we'll need to count segments soon
            segment_count = 0

            # initialize line numbers
            text_widget_line = 0

            # take each transcript segment
            segments = transcription.get_segments()

            # if there are segments
            if segments:

                for t_segment in segments:

                    # start counting the lines
                    text_widget_line = text_widget_line + 1

                    # if there is a text element, simply insert it in the window
                    if hasattr(t_segment, 'text'):
                        text = t_segment.text

                    # if not, add an empty line and log a warning
                    else:
                        logger.warning('No text found in segment {}. Adding empty line.'.format(t_segment.id))
                        text = ''

                    insert_pos = '{}.0'.format(text_widget_line)

                    # count the segments
                    segment_count = segment_count + 1

                    # insert the text
                    text_widget.insert(ctk.END, text.strip() + ' ')

                    # if this is the longest segment, keep that in mind
                    if len(text) > text_widget.longest_segment_num_char:
                        text_widget.longest_segment_num_char = len(text)

                    if t_segment.meta:
                        self._tag_meta_segment(text_widget, text_widget_line)

                    # for now, just add 2 new lines after each segment:
                    text_widget.insert(ctk.END, '\n')

            # format the meta tags
            self._format_meta_tags(text_widget)

            # return the text_widget to its original state
            text_widget.config(state=text_widget_state)

            # update the text_widget last_sync according to the transcription last_save_time
            text_widget.last_hash = transcription.last_hash

        @staticmethod
        def _tag_meta_segment(text_widget, line_no):

            text_widget.tag_add('l_meta', "{}.0".format(line_no), "{}.end".format(line_no))

        def _format_meta_tags(self, text_widget):

            text_widget.tag_config('l_meta', foreground=toolkit_UI.theme_colors['meta_text'], )

            # add half of line of space as a top padding
            text_widget.tag_config('l_meta', spacing1=20)

            # also make it all caps
            text_widget.tag_config('l_meta', font=self.toolkit_UI_obj.meta_transcript_font)

        @staticmethod
        def unbind_editing_keys(text):
            """
            This function unbinds all the keys used for editing the transcription
            :return:
            """

            text.unbind('<Return>')
            text.unbind('<Escape>')
            text.unbind('<BackSpace>')
            text.unbind('<Delete>')

        @staticmethod
        def get_current_segment_chars(text):
            """
            This function returns the current segment's start and end character positions
            :param text: the text widget
            :return: line_no, insert_char, end_char
            """

            # get the position of the cursor on the text widget
            line_no, insert_char = text.index(ctk.INSERT).split('.')

            # get the index of the last character of the text widget line where the cursor is
            _, end_char = text.index("{}.end".format(line_no)).split('.')

            return line_no, insert_char, end_char

        def set_transcript_modified(self, window_id=None, modified=True):
            """
            This function sets the transcript_modified flag for the given window
            :param window_id:
            :param modified:
            :return:
            """

            if window_id is None:
                return False

            self.transcript_modified[window_id] = modified

        def get_transcript_modified(self, window_id):
            """
            This function returns the transcript_modified flag for the given window
            :param window_id:
            :return:
            """

            if window_id in self.transcript_modified:
                return self.transcript_modified[window_id]
            else:
                return False

        def on_press_merge_segments(self, event, window_id, text_widget, merge_direction=None):
            """
            This function checks whether the cursor is at the beginning or at the end of the line and
            it merges the current transcript segment either with the previous or with the next segment

            :param event:
            :param window_id:
            :param text_widget:
            :param merge_direction:
            :return:
            """

            if window_id is None or text_widget is None:
                return False

            if merge_direction not in ['previous', 'next']:
                logger.error('Merge direction not specified.')
                return 'break'

            # get the transcription object of the current window
            window_transcription = self.get_window_transcription(window_id=window_id)

            # get the cursor position where the event was triggered (key was pressed)
            # and the last character of the line
            text_widget_line, text_widget_char, text_widget_last_char = self.get_current_segment_chars(text=text_widget)

            # if there's a 'sel' tag on the text window
            # see if we have to perform a multi-line delete
            if text_widget.tag_ranges('sel'):

                # get the line numbers of the selection but using the index function
                start_line = int(text_widget.index(text_widget.tag_ranges('sel')[0]).split('.')[0])
                end_line = int(text_widget.index(text_widget.tag_ranges('sel')[-1]).split('.')[0])

                # if the selection is not on the same line,
                # pass them to delete_lines
                if start_line != end_line:

                    # remove the selection
                    text_widget.tag_remove('sel', '1.0', 'end')

                    # re make the selection so it extends from start to end of lines
                    text_widget.tag_add('sel', '{}.0'.format(start_line), '{}.end'.format(end_line))

                    # compile a list of all the lines in the selection,
                    # we're adding 1 to have the full range
                    selection_lines = list(range(start_line, end_line+1))

                    # pass the lines to:
                    self.delete_lines(window_id=window_id, text_widget_lines=selection_lines)

                    return 'break'

            # pass to _on_transcript_key_press if we are not at the beginning nor at the end of the current line
            # or if the direction of the merge doesn't match the character number
            if text_widget_char not in ['0', text_widget_last_char] \
                    or (text_widget_char == '0' and merge_direction != 'previous') \
                    or (text_widget_char == text_widget_last_char and merge_direction != 'next'):
                return self._on_transcript_key_press(event, window=self.toolkit_UI_obj.get_window_by_id(window_id))

            first_segment_index = None
            second_segment_index = None

            # if we are at the beginning of the line
            # and the merge_direction direction is 'prev'
            # we are merging the CURRENT SEGMENT WITH THE PREVIOUS ONE
            if text_widget_char == '0' and merge_direction == 'previous':

                first_segment_index = int(text_widget_line) - 2
                second_segment_index = int(text_widget_line) - 1

                # get the two transcription segments
                first_segment = window_transcription.get_segment(segment_index=first_segment_index)
                second_segment = window_transcription.get_segment(segment_index=second_segment_index)

                # if they're not both meta or non-meta, we can't merge them
                if first_segment.meta != second_segment.meta:
                    return 'break'

                # remove the line break from the previous line
                text_widget.delete("{}.end".format(second_segment_index), "{}.end+1c".format(second_segment_index))

            # if we are at the end of the line
            # and the merge direction is 'next'
            if text_widget_char == text_widget_last_char and merge_direction == 'next':

                first_segment_index = int(text_widget_line) - 1
                second_segment_index = int(text_widget_line)

                # get the two transcription segments
                first_segment = window_transcription.get_segment(segment_index=first_segment_index)
                second_segment = window_transcription.get_segment(segment_index=second_segment_index)

                # if they're not both meta or non-meta, we can't merge them
                if first_segment.meta != second_segment.meta:
                    return 'break'

                # remove the line break from current line
                text_widget.delete('{}.end'.format(text_widget_line), '{}.end+1c'.format(text_widget_line))

            # if we have both the first and the second segment index
            # we can merge the segments and save the transcript
            if first_segment_index is not None and second_segment_index is not None:

                # merge the segments
                window_transcription.merge_segments(segment_index_list=[first_segment_index, second_segment_index])

                # update the transcript_modified flag
                self.set_transcript_modified(window_id=window_id, modified=True)

                # save the transcript
                self.save_transcript(window_id=window_id)

            return 'break'

        def defocus_transcript(self, text):

            # defocus from transcript text
            tk_transcription_window = text.winfo_toplevel()
            tk_transcription_window.focus()

            # disable text editing again
            text.config(state=ctk.DISABLED)

            # unbind all the editing keys
            self.unbind_editing_keys(text)

        def on_press_save_transcript(self, event, window_id, text=None):

            if window_id is None:
                return False

            # get the text widget from the event
            if text is None:
                text = event.widget

            if text is None:
                return False

            # disable text editing again
            text.config(state=ctk.DISABLED)

            # unbind all the editing keys
            self.unbind_editing_keys(text)

            # deactivate typing and editing for this window
            self.set_typing_in_window(window_id=window_id, typing=False)
            self.set_transcript_editing(window_id=window_id, editing=False)

            # save the transcript
            # (this will also update the status label depending on the result)
            save_status = self.save_transcript(window_id=window_id)

        def update_status_label_after_save(self, window_id, save_status=None):

            if save_status is True:
                # show the user that the transcript was saved
                self.toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Transcript saved.', color='normal')

            # in case anything went wrong while saving,
            # let the user know about it
            elif save_status == 'fail':
                self.toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Transcript save failed.', color='bright_red')

            # in case the save status is False
            # assume that nothing needed saving
            else:
                self.toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Transcript unchanged.', color='normal')

        def on_text_widget_defocus(self, e, window_id):
            """
            This function is called when the user clicks outside of the transcript text widget
            """

            if window_id is None:
                return False

            # if the transcript was changed
            if self.is_transcript_changed(window_id=window_id):
                self.on_press_save_transcript(e, window_id=window_id)

        def is_transcript_changed(self, window_id):
            """
            This checks if the transcript has been changed compared to what's stored in the window Transcription object

            :param window_id:
            :param save_if_changed:
            """

            if window_id is None:
                return False

            changed = False

            # get the transcription object for this window
            window_transcription = self.get_window_transcription(window_id=window_id)

            # get the text widget for this window
            text_widget = self.get_transcription_window_text_widget(window_id=window_id)

            # take each line and compare it to the corresponding segment in the transcription object
            # do a -1 to skip the last line, which is always empty on a text widget
            for widget_line_no in range(1, int(text_widget.index('end').split('.')[0]) - 1):

                # get the text of the line
                line_text = text_widget.get('{}.0'.format(widget_line_no), '{}.end'.format(widget_line_no))

                # get the corresponding segment from the transcription object
                segment = window_transcription.get_segment(segment_index=widget_line_no - 1)

                # if the line text is different from the segment text
                if segment is not None and line_text != segment.text:

                    # update the segment
                    segment.set('text', line_text)

                    changed = True

            # if we got here, the transcript is unchanged
            return changed

        def save_transcript(self, window_id=None, text=None, force=False):
            """
            This function lets the Transcript object know that the transcription should be saved.
            The transcription object times the saving so that it doesn't happen too often
            and also does a check on its _dirty flag to see the transcription needs to be saved

            :param window_id:
            :param text:
            :param force: if this is True, the tool
                            will ignore the transcript object's _dirty flag and save the transcript
            :return:
            """

            # todo: remove the text parameter and use the window_id to get the text widget if needed...

            if window_id is None and text is None:
                logger.debug('No window id or text provided.')
                return False

            # get the transcription object for this window
            window_transcription = self.get_window_transcription(window_id=window_id)

            # send the save command to the transcription object
            return window_transcription.save_soon(
                backup=self.stAI.transcript_backup_interval,
                force=force,
                if_successful=lambda: self.update_status_label_after_save(window_id, True),
                if_failed=lambda: self.update_status_label_after_save(window_id, 'fail'),
                if_none=lambda: self.update_status_label_after_save(window_id)
            )

        def set_window_transcription(self, window_id: str, transcription: Transcription):
            """
            This adds a transcription object to the window
            """

            if window := self.toolkit_UI_obj.get_window_by_id(window_id=window_id):
                setattr(window, 'transcription', transcription)

                # notify observers of the transcription update
                self.toolkit_ops_obj.notify_observers(action='update_transcription_{}'.format(window_id))

                return True

            return False

        def get_window_transcription(self, window_id: str):
            """
            This returns the transcription object for the window_id
            """

            if window := self.toolkit_UI_obj.get_window_by_id(window_id=window_id):

                # return either the object or None
                return getattr(window, 'transcription') if getattr(window, 'transcription') is not None else None

    def open_transcript(self, **options):
        """
        This prompts the user to open a transcript file and then opens it a transcript window
        :return:
        """

        # did we ever save a target dir for this project?
        last_target_dir = None
        if NLE.is_connected() and NLE.current_project is not None:
            last_target_dir = self.stAI.get_project_setting(project_name=NLE.current_project,
                                                            setting_key='last_target_dir')

        # ask user which transcript to open
        transcription_json_file_path = self.ask_for_target_file(filetypes=[("Json files", "json srt")],
                                                                target_dir=last_target_dir)

        # abort if user cancels
        if not transcription_json_file_path:
            return False

        # if resolve is connected, save the directory where the file is as a last last target dir
        if NLE.is_connected() and transcription_json_file_path and os.path.exists(transcription_json_file_path):
            self.stAI.save_project_setting(project_name=NLE.current_project,
                                           setting_key='last_target_dir',
                                           setting_value=os.path.dirname(transcription_json_file_path))

        # if this is an srt file, but a .transcription.json file exists in the same directory,
        # ask the user if they want to open the .transcription.json file instead
        if transcription_json_file_path.endswith('.srt') \
                and os.path.exists(transcription_json_file_path.replace('.srt', '.transcription.json')):

            # ask user
            if messagebox.askyesno(title="Open Transcription",
                                   message='The file you selected is an SRT file, '
                                           'but a transcription.json file with the exact name '
                                           'exists in the same folder.\n\n'
                                           'Do you want to open the transcription.json file instead?'
                                           '\n\n'
                                           'If you answer NO, the transcription.json will be '
                                           'overwritten with the content of the SRT file '
                                           'and you will lose all work done on that transcription.'
                                           ''):
                # change the file path
                transcription_json_file_path = transcription_json_file_path.replace('.srt', '.transcription.json')

        # if this is an srt file, ask the user if they want to convert it to json
        if transcription_json_file_path.endswith('.srt'):

            convert_from_srt = messagebox.askyesno(title="Convert SRT?",
                                                   message='Do you want to convert this SRT file '
                                                           'to a transcription file?')

            # if the user wants to convert the srt file to json
            if convert_from_srt:
                # convert the srt file to json
                # (it will overwrite any existing transcription.json with the same name in the same directory)
                transcription_json_file_path \
                    = TranscriptionUtils.convert_srt_to_transcription_json(
                    srt_file_path=transcription_json_file_path,
                    overwrite=True
                )

        # if the file is not a json file, abort
        if not transcription_json_file_path.endswith('.json'):
            self.notify_via_messagebox(title='Not a transcription',
                                       message='The file \n{}\nis not a transcription file.'
                                       .format(os.path.basename(transcription_json_file_path)),
                                       message_log='The file {} is not a transcription file.',
                                       type='error')
            return False

        # open the transcript in a transcript window

        # why not open the transcript in a transcription window?
        self.open_transcription_window(transcription_file_path=transcription_json_file_path, **options)

    def open_new_transcription_window(self, transcription_segments=None, transcription_file_path=None,
                                      source_transcription=None, transcript_groups=None):
        """
        This makes the user choose a file path for the new transcription and then opens a new transcription window
        """

        # ask the user where to save the transcription if no file path was passed
        if transcription_file_path is None:
            transcription_file_path = self.ask_for_save_file(
                title='New Transcription',
                filetypes=[('Transcription files', '.json')]
            )

        # if the user didn't choose a file path, stop
        if not transcription_file_path:
            return False

        # replace .transcription.json with .json to avoid doubling .transcription on the next step
        transcription_file_path = transcription_file_path.replace('.transcription.json', '.json')

        # now re-add .transcription.json
        transcription_file_path = transcription_file_path.replace('.json', '.transcription.json')

        # remove the file if it already exists
        if os.path.exists(transcription_file_path):
            # just remove it (the OS should have asked for confirmation already)
            os.remove(transcription_file_path)

        # load the transcription, or force reload it if the object already exists
        transcription = Transcription(transcription_file_path=transcription_file_path, force_reload=True)

        # if another transcription was passed, copy its data to the new transcription
        if source_transcription is not None:
            transcription.copy_transcription(source_transcription=source_transcription, include_groups=True)

        # if we have a list of segments, use them in the new transcription
        if transcription_segments is not None:

            # add the segments to the transcription
            transcription.add_segments(transcription_segments)

        # otherwise use the list of segments from the source transcription
        elif source_transcription is not None:
            transcription.add_segments(source_transcription.get_segments())

        # if we have a list of transcript groups, use them in the new transcription
        # (this will add them next to any copied groups from the source transcription)
        if transcript_groups is not None:

            # get the existing transcript groups
            existing_transcript_groups = copy.deepcopy(transcription.get_all_transcript_groups())

            # take each group and prepare it for the transcription
            # this will eventually return a dict looking like this {group_id: group_data, group_id2: group_data2 ....}
            for current_group in transcript_groups:

                # all groups must have a non-empty name
                if 'group_name' not in current_group or not current_group['group_name']:
                    logger.debug('Cannot add group "{}" - no group name provided.'.format(current_group))
                    continue

                # all groups must have a non-empty time intervals dict
                if 'time_intervals' not in current_group or not current_group['time_intervals']:
                    logger.debug('Cannot add group "{}" - no time intervals provided.'
                                 .format(current_group['group_name']))
                    continue

                new_group = transcription.prepare_transcript_group(
                    group_name=current_group['group_name'],
                    group_notes=current_group.get('group_notes', ''),
                    time_intervals=current_group['time_intervals']
                )

                # add the new group to the groups data dict
                existing_transcript_groups = {**existing_transcript_groups, **new_group}

            transcription.set_transcript_groups(transcript_groups=existing_transcript_groups)

        # use the name of the transcription file as the name of the transcription
        transcription.set('name', os.path.basename(transcription_file_path).split('.transcription.json')[0])

        transcription.save_soon(backup=False, force=True, sec=0)

        time.sleep(0.2)

        # open the story editor window and return it
        return self.open_transcription_window(transcription_file_path=transcription_file_path)

    def open_transcription_window(self, title=None, transcription_file_path=None,
                                  select_line_no=None, add_to_selection=None, select_group=None, goto_time=None,
                                  new_transcription_segments=None, new_transcript_groups=None):
        """
        This opens a transcription window
        :param title: the title of the window
        :param transcription_file_path: the path to the transcription file
        :param select_line_no: the line number to select
        :param add_to_selection: a list of line numbers to add to the selection
        :param select_group: the group id to select
        :param goto_time: the time to go to
        :param new_transcription_segments: a list of new segments to add to the transcription
                                           (only works if transcription is already open)
        :param new_transcript_groups: a list of new groups to add to the transcription
                                        (only works if transcription is already open)
        """

        # Note: most of the transcription window functions are stored in the TranscriptEdit class
        transcription = Transcription(transcription_file_path=transcription_file_path)

        # only continue if the transcription path was passed and the file exists
        if not transcription.exists:
            self.notify_via_messagebox(
                title='Not found',
                type='error',
                message='The transcription file {} cannot be found.'
                .format(transcription.transcription_file_path)
            )
            return False

        if not transcription.is_transcription_file:
            self.notify_via_messagebox(
                title='Invalid Transcription',
                type='error',
                message='The file {} is not a valid transcription file.'
                .format(transcription.transcription_file_path)
            )
            return False

        # todo make this work
        # was this transcription flagged incomplete
        if transcription.incomplete:
            self.notify_via_messagebox(
                title="Incomplete Transcription",
                type="warning",
                message="This transcription looks incomplete.\n\n" \
                        "Which means that it's either still being processed, or that something went wrong.\n\n"
                        "To fix this, you can simply press retranscribe "
                        "and try to re-transcribe the parts that are missing."
            )

        # use the transcription path id for the window id
        t_window_id = 't_window_{}'.format(transcription.transcription_path_id)

        # for the window title, we either used the passed title or the transcription name
        title = title if title else transcription.name

        # if we don't have a transcription file name,
        # just use the transcription file path without the .transcription.json extension
        if title is None and transcription.transcription_file_path is not None:
            title = os.path.basename(transcription.transcription_file_path).split('.transcription.json')[0]

        # create a window for the transcript if one doesn't already exist
        if self.create_or_open_window(parent_element=self.root, window_id=t_window_id, title=title, resizable=True,
                                      type='transcription',
                                      close_action=lambda l_t_window_id=t_window_id: \
                                              self.destroy_transcription_window(l_t_window_id),
                                      has_menubar=True
                                      ):

            # add the Transcription object to this window
            self.t_edit_obj.set_window_transcription(t_window_id, transcription)

            #
            # UI ELEMENTS
            # THE THREE WINDOW COLUMN FRAMES
            t_window = self.get_window_by_id(t_window_id)

            # create the left frame
            left_frame = ctk.CTkFrame(t_window, name='left_frame', **self.ctk_frame_transparent)
            left_frame.grid(row=0, column=0, sticky="ns", **self.ctk_side_frame_button_paddings)

            # create the middle frame to hold the text element
            middle_frame = ctk.CTkFrame(t_window, name='middle_frame', **self.ctk_frame_transparent)
            middle_frame.grid(row=0, column=1, sticky="nsew")

            # create a frame for the text element inside the middle frame
            text_form_frame = ctk.CTkFrame(middle_frame, name='text_form_frame',
                                           **self.ctk_frame_transparent)
            text_form_frame.grid(row=0, column=0, sticky="nsew")

            # make the text_form_frame expand to fill the middle_frame
            middle_frame.grid_rowconfigure(0, weight=1)
            middle_frame.grid_columnconfigure(0, weight=1)

            # create the right frame to hold other stuff, like transcript groups etc.
            right_frame = ctk.CTkFrame(t_window, name='right_frame', **self.ctk_frame_transparent)
            right_frame.grid(row=0, column=2, sticky="ns", **self.ctk_side_frame_button_paddings)

            # add a footer frame
            footer_frame = ctk.CTkFrame(t_window, name='footer_frame', **self.ctk_frame_transparent)
            footer_frame.grid(row=1, column=0, columnspan=3, sticky="ew", **self.ctk_frame_paddings)

            # add a minimum size for the frame2 column
            t_window.grid_columnconfigure(1, weight=1, minsize=200)

            # Add column and row configuration for resizing
            t_window.grid_rowconfigure(0, weight=1)

            # LEFT FRAME SUB-FRAMES (with their respective labels)
            left_t_buttons_frame = ctk.CTkFrame(left_frame, name='t_buttons_frame')
            ctk.CTkLabel(left_t_buttons_frame, text='Transcript', anchor='n') \
                .pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            left_s_buttons_frame = ctk.CTkFrame(left_frame, name='s_buttons_frame')
            ctk.CTkLabel(left_s_buttons_frame, text='Selection', anchor='n') \
                .pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            left_r_buttons_frame = ctk.CTkFrame(left_frame, name='r_buttons_frame')
            ctk.CTkLabel(left_r_buttons_frame, text='Resolve', anchor='n') \
                .pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            left_t_buttons_frame.grid(row=0, column=0, **self.ctk_side_frame_button_paddings)

            # add the segment buttons to the left frame
            # SEND TO ASSISTANT BUTTON
            send_to_assistant_button = ctk.CTkButton(left_s_buttons_frame, text='Send to Assistant',
                                                     command=lambda: self.t_edit_obj.button_send_to_assistant(
                                                         window_id=t_window_id),
                                                     name='send_to_assistant_button', **self.ctk_side_frame_button_size)
            send_to_assistant_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            send_to_assistant_with_tc_button = ctk.CTkButton(left_s_buttons_frame, text='Send to Assistant with TC',
                                                             command=lambda: self.t_edit_obj.button_send_to_assistant(
                                                                 window_id=t_window_id, with_timecodes=True),
                                                             name='send_to_assistant_button_with_tc',
                                                             **self.ctk_side_frame_button_size)
            send_to_assistant_with_tc_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings,
                                                  anchor='nw')

            # ADD TO GROUP BUTTON
            add_to_group_button = ctk.CTkButton(left_s_buttons_frame, text='Add to New Group',
                                                command=lambda: self.t_edit_obj.button_add_to_new_group(
                                                    window_id=t_window_id, only_add=True),
                                                name='add_to_group_button', **self.ctk_side_frame_button_size)
            add_to_group_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            # COPY TO BUTTONS

            copy_to_clipboard_with_tc_button = ctk.CTkButton(left_s_buttons_frame, text='Copy with TC',
                                                             command=lambda: self.t_edit_obj.button_copy_segments_to_clipboard(
                                                                 t_window_id, with_timecodes=True, per_line=True),
                                                             name='copy_to_clipboard_with_tc_button',
                                                             **self.ctk_side_frame_button_size)

            copy_to_clipboard_with_tc_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings,
                                                  anchor='nw')

            copy_to_clipboard_with_block_tc_button = ctk.CTkButton(left_s_buttons_frame, text='Copy with Block TC',
                                                                   command=lambda: self.t_edit_obj.button_copy_segments_to_clipboard(
                                                                       t_window_id, with_timecodes=True,
                                                                       per_line=False),
                                                                   name='copy_to_clipboard_with_block_tc_button')

            copy_to_clipboard_with_block_tc_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings,
                                                        anchor='nw')

            # RE-TRANSCRIBE BUTTON
            retranscribe_button = ctk.CTkButton(left_s_buttons_frame, text='Re-transcribe',
                                                command=lambda: self.t_edit_obj.button_retranscribe(
                                                    window_id=t_window_id),
                                                name='retranscribe_button', **self.ctk_side_frame_button_size)

            retranscribe_button.pack(fill='x', expand=True, **self.ctk_side_frame_button_paddings, anchor='nw')

            # THE MAIN TEXT ELEMENT

            # does the json file actually contain transcript segments generated by whisper?
            if transcription.is_transcription_file:

                # initialize the transcript text element
                t_window.text_widget = \
                    text = tk.Text(text_form_frame,
                                   name='transcript_text',
                                   font=self.transcript_font,
                                   width=45, height=30,
                                   **self.ctk_full_textbox_paddings,
                                   wrap=tk.WORD,
                                   background=self.theme_colors['black'],
                                   foreground=self.theme_colors['normal'],
                                   highlightcolor=self.theme_colors['dark'],
                                   highlightbackground=self.theme_colors['dark'],
                                   )

                # add a scrollbar to the text element
                text_scrollbar = ctk.CTkScrollbar(text_form_frame)
                text_scrollbar.configure(command=text.yview)
                text_scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y, pady=5)

                # configure the text element to use the scrollbar
                text.config(yscrollcommand=text_scrollbar.set)

                # use this to calculate the longest segment (but don't accept anything under 30)
                text.longest_segment_num_char = 40

                # add the segments to the text widget
                self.t_edit_obj.add_segments_to_text_widget(
                    transcription=transcription, text_widget=text, clear_text_widget=False)

                # make the text read only
                # and take into consideration the longest segment to adjust the width of the window
                if text.longest_segment_num_char > 60:
                    text.longest_segment_num_char = 60
                text.config(state=ctk.DISABLED, width=text.longest_segment_num_char)

                # set the top, in-between and bottom text spacing
                text.config(spacing1=0, spacing2=0.2, spacing3=5)

                # then show the text element
                text.pack(anchor='w', expand=True, fill='both', **self.ctk_full_textbox_frame_paddings)

                # add a status label to print out current transcription status
                status_label = ctk.CTkLabel(footer_frame, name='status_label',
                                            text="", anchor='w', **self.ctk_frame_transparent)
                status_label.grid(row=0, column=0, sticky='ew', **self.ctk_footer_status_paddings)

                # add the status label to the window attributes
                t_window.status_label = status_label

                select_options = {'window_id': t_window_id, 'text_element': text, 'status_label': status_label}

                # bind all key presses to transcription window actions
                self.windows[t_window_id].bind(
                    "<KeyPress>",
                    lambda e: self.t_edit_obj.transcription_window_keypress(event=e, **select_options)
                )

                # bind CMD/CTRL + key presses to transcription window actions
                self.windows[t_window_id].bind(
                    "<" + self.ctrl_cmd_bind + "-KeyPress>",
                    lambda e: self.t_edit_obj.transcription_window_keypress(
                        event=e, special_key='cmd', **select_options)
                )

                # bind all mouse clicks on text
                text.bind(
                    "<Button-1>",
                    lambda e, select_options1=select_options:
                    self.t_edit_obj.transcription_window_mouse(e,  **select_options))

                # bind CMD/CTRL + mouse Clicks to text
                text.bind(
                    "<" + self.ctrl_cmd_bind + "-Button-1>",
                    lambda e, l_select_options=select_options:
                    self.t_edit_obj.transcription_window_mouse(e, special_key='cmd', **l_select_options)
                )

                # bind ALT/OPT + mouse Click to edit transcript
                text.bind(
                    "<" + self.alt_bind + "-Button-1>",
                    lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id)
                )

                # bind CMD/CTRL + e to edit transcript
                self.windows[t_window_id].bind(
                    "<" + self.ctrl_cmd_bind + "-e>",
                    lambda e: self.t_edit_obj.edit_transcript(window_id=t_window_id)
                )

                # add right click for context menu
                text.bind(
                    '<Button-3>', lambda e: self.t_edit_obj._transcription_window_context_menu(
                        e, window_id=t_window_id))

                # make context menu work on mac trackpad too
                text.bind(
                    '<Button-2>', lambda e: self.t_edit_obj._transcription_window_context_menu(
                        e, window_id=t_window_id))

                # FIND BUTTON

                find_button = ctk.CTkButton(
                    left_t_buttons_frame, text='Find', name='find_replace_button',
                    command=lambda: self.open_find_replace_window(
                        parent_window_id=t_window_id, title="Find in {}".format(title),
                        select_all_action=self.t_edit_obj.text_indices_to_selection
                    ),
                    **self.ctk_side_frame_button_size
                )

                # bind CMD/CTRL + f to the WINDOW, to open the find and replace window
                t_window.bind(
                    "<" + self.ctrl_cmd_bind + "-f>",
                    lambda e: self.open_find_replace_window(
                        parent_window_id=t_window_id,
                        title="Find in {}".format(title),
                        select_all_action=self.t_edit_obj.text_indices_to_selection
                    )
                )

                # let's add the .find attribute to the window, so that the UI_menu can use it
                t_window.find = \
                    lambda: self.open_find_replace_window(
                        parent_window_id=t_window_id,
                        title="Find in {}".format(title),
                        select_all_action=self.t_edit_obj.text_indices_to_selection
                )

                # ADVANCED SEARCH
                # this button will open a new window with advanced search options
                advanced_search_button = \
                    ctk.CTkButton(
                        left_t_buttons_frame, text='Advanced Search', name='advanced_search_button',
                        command=lambda:
                        self.open_advanced_search_window(
                            transcription_window_id=t_window_id,
                            search_file_path=transcription.transcription_file_path
                        ),
                        **self.ctk_side_frame_button_size
                    )

                # GROUP QUESTIONS BUTTON
                group_questions_button = \
                    ctk.CTkButton(
                        left_t_buttons_frame, text='Group Questions', name='group_questions_button',
                        command=lambda:
                        self.t_edit_obj.button_group_questions(
                            window_id=t_window_id
                        ),
                        **self.ctk_side_frame_button_size
                    )

                find_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings, anchor='nw')
                advanced_search_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings, anchor='nw')
                group_questions_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings, anchor='nw')

                # IMPORT SRT BUTTON
                import_srt_button = \
                    ctk.CTkButton(
                        left_r_buttons_frame,
                        name='import_srt_button',
                        text="Import SRT into Bin",
                        command=lambda l_t_window_id=t_window_id:
                        self.t_edit_obj.button_import_srt_to_bin(window_id=l_t_window_id),
                        **self.ctk_side_frame_button_size
                    )
                import_srt_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings, anchor='sw')

                if not NLE.is_connected():
                    import_srt_button.pack_forget()

                # SYNC BUTTON

                sync_button = \
                    ctk.CTkButton(
                        left_r_buttons_frame,
                        name='sync_button',
                        **self.ctk_side_frame_button_size)

                sync_button.configure(
                    command=lambda l_sync_button=sync_button, l_t_window_id=t_window_id:
                    self.t_edit_obj.sync_with_playhead_button(
                        button=l_sync_button,
                        window_id=l_t_window_id)
                )

                # LINK TO TIMELINE BUTTON

                # is this transcript linked to the current timeline?

                # prepare an empty link button for now, and only show it when/if resolve starts
                link_button = ctk.CTkButton(left_r_buttons_frame, name='link_button', **self.ctk_side_frame_button_size)
                link_button.configure(
                    command=lambda: self.t_edit_obj.link_to_timeline_button(window_id=t_window_id)
                )

                # RESOLVE SEGMENTS + MARKERS BUTTONS

                selection_to_markers_button = ctk.CTkButton(left_r_buttons_frame, text='Selection to Markers',
                                                            name='selection_to_markers_button',
                                                            **self.ctk_side_frame_button_size)

                selection_to_markers_button.configure(command=lambda:
                self.t_edit_obj.button_segments_to_markers(window_id=t_window_id, prompt=True)
                                                      )

                selection_to_markers_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings,
                                                 anchor='sw')

                markers_to_selection_button = ctk.CTkButton(left_r_buttons_frame,
                                                            text='Markers to Selection',
                                                            name='markers_to_selection_button',
                                                            **self.ctk_side_frame_button_size)

                markers_to_selection_button.configure(command=lambda:
                self.t_edit_obj.button_markers_to_segments(window_id=t_window_id))

                markers_to_selection_button.pack(side=ctk.TOP, fill='x', **self.ctk_side_frame_button_paddings,
                                                 anchor='sw')

                # END RESOLVE SEGMENTS + MARKERS BUTTONS

                # start update the transcription window with some stuff
                # here we send the update transcription window function a few items that need to be updated
                self.windows[t_window_id].after(
                    100,
                    lambda l_link_button=link_button, l_t_window_id=t_window_id,
                    l_transcription_file_path=transcription.transcription_file_path:
                    self.update_transcription_window(window_id=l_t_window_id,
                                                     link_button=l_link_button,
                                                     sync_button=sync_button,
                                                     import_srt_button=import_srt_button,
                                                     transcription_file_path=l_transcription_file_path,
                                                     text=text)
                )

                # add this window to the list of text windows
                self.text_windows[t_window_id] = {'text_widget': text}

            # if no segment was found in the json file, alert the user
            # else:
            #     no_segments_message = 'The file {} doesn\'t have any segments.'.format(
            #         os.path.basename(transcription_file_path))

            #     self.notify_via_messagebox(title='No segments',
            #                                message=no_segments_message,
            #                                type='warning'
            #                                )
            #     self.destroy_window_(window_id=t_window_id)

            # keep this window on top if the user has that config option enabled
            if self.stAI.get_app_setting('transcripts_always_on_top', default_if_none=False):
                self.window_on_top(window_id=t_window_id, on_top=self.stAI.get_app_setting('transcripts_always_on_top'))

            # add an observer to this window
            # for the action, we'll use  update_transcription_ + the transcription id
            # for the callback, we'll use the update_transcription_window function
            # so whenever the observer is notified from toolkit the ops object,
            # it will call the update_transcription_window function
            self.add_observer_to_window(
                window_id=t_window_id,
                action='{}_{}'
                .format('update_transcription_', transcription.transcription_path_id),
                callback=lambda: self.update_transcription_window(t_window_id)
            )

            # add the transcript groups form to the right frame
            transcript_groups_module = self.TranscriptGroupsModule(
                master=right_frame, window_id=t_window_id, toolkit_UI_obj=self)

            # and attach it to the window
            t_window.transcript_groups_module = transcript_groups_module

        # if the transcription window already exists,
        # we won't know the window id since it's not passed
        else:

            # get the current window and the transcript groups module
            t_window = current_tk_window = self.get_window_by_id(t_window_id)
            transcript_groups_module = current_tk_window.transcript_groups_module

            # if new_transcription_segments were passed, add them to the transcription
            if new_transcription_segments is not None:

                # add the segments to the transcription
                transcription.add_segments(new_transcription_segments, overwrite=True)
                # transcription.save_soon(force=True, sec=0)

                # reload the groups in the transcript groups module
                # transcript_groups_module.update_groups()

                self.t_edit_obj.clear_selection(t_window_id, text_element=t_window.text_widget)

                # add the segments to the text widget
                self.t_edit_obj.add_segments_to_text_widget(transcription, t_window.text_widget)

                # refresh the transcription window to make sure everything updated (except groups)
                self.update_transcription_window(t_window_id)

                self.t_edit_obj.save_transcript(window_id=t_window_id)

            # if new_transcript_groups were passed, add them to the transcription
            if new_transcript_groups is not None:

                # add the groups to the transcription
                transcript_groups_module.add_new_groups(groups_data=new_transcript_groups)

            # check if we have to refresh the text widget
            # and if the transcription was changed since the last refresh
            if t_window.text_widget.last_hash != transcription.last_hash:

                # add the segments to the text widget
                self.t_edit_obj.add_segments_to_text_widget(transcription, t_window.text_widget)

            # so update all the windows just to make sure that all the elements are in the right state
            self.update_all_transcription_windows()

        # if select_line_no was passed
        if select_line_no is not None:
            # select the line in the text widget
            self.t_edit_obj.set_active_segment(window_id=t_window_id, text_widget_line=select_line_no)

        # if add_to_selection was passed
        if add_to_selection is not None and add_to_selection and type(add_to_selection) is list:

            # go through all the add_to_selection items
            for selection_line_no in add_to_selection:
                # and add them to the selection

                # select the line in the text widget
                self.t_edit_obj.segment_to_selection(window_id=t_window_id, line=selection_line_no)

        # also select any group that may have been passed
        if select_group is not None:
            transcript_groups_module.select_group(group_id=select_group, show_first_segment=True)

        # select the line at the given time in seconds if goto_time was passed
        if goto_time is not None:
            self.set_active_segment_by_time(
                transcript_sec=goto_time, window_id=t_window_id,
                text_widget=t_window.text_widget, transcription=transcription, toolkit_UI_obj=self)

    def update_transcription_window(self, window_id, update_all: bool = True, confirmed=True, **update_attr):
        """
        Auto-updates a transcription window GUI

        :param window_id:
        :param update_all: If this is True, try to update all the GUI elements of the window
                            by using their hard-coded names, even if they were not passed in the update_attr dict.
        :param confirmed: If this is not true, the user will be asked to confirm any text widget updates
        :param update_attr:
        :return:
        """

        t_window = self.get_window_by_id(window_id)

        # ignore if the window doesn't exist
        if not t_window:
            return

        # get the transcription object
        transcription = self.t_edit_obj.get_window_transcription(window_id=window_id)

        # check if we have to refresh the text widget
        # and if the transcription was changed since the last refresh
        # todo: find proper way to update without breaking user changes on window
        if t_window.text_widget.last_hash != transcription.last_hash and confirmed:

            # add the segments to the text widget
            self.t_edit_obj.add_segments_to_text_widget(transcription, t_window.text_widget)

        # reset the status_label if it's been more than 5 seconds since the last update
        self.reset_status_label_after(window_id=window_id, seconds=5)

        # if the update_all attribute is True
        # try to get the following GUI elements from the window, if they were not passed in the update_attr dict
        # so we update them later in the function
        if update_all:

            update_attr['transcription_file_path'] \
                = self.t_edit_obj.get_window_transcription(window_id=window_id).transcription_file_path

            update_attr['link_button'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame.link_button')

            update_attr['sync_button'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame.sync_button')

            update_attr['import_srt_button'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame.import_srt_button')

            update_attr['text'] \
                = self.windows[window_id].nametowidget('middle_frame.text_form_frame.transcript_text')

            update_attr['r_buttons_frame'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame')

            update_attr['s_buttons_frame'] \
                = self.windows[window_id].nametowidget('left_frame.s_buttons_frame')

            update_attr['selection_to_markers_button'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame.selection_to_markers_button')

            update_attr['markers_to_selection_button'] \
                = self.windows[window_id].nametowidget('left_frame.r_buttons_frame.markers_to_selection_button')

        # update the selection buttons
        show_selection_buttons = False
        if 's_buttons_frame' in update_attr:

            # and segments are selected
            if window_id in self.t_edit_obj.selected_segments \
                    and len(self.t_edit_obj.selected_segments[window_id]) > 0:
                # show the segment buttons
                show_selection_buttons = True

        # if NLE is connected and there is a current timeline
        show_resolve_buttons = False
        if NLE.is_connected() and NLE.current_timeline is not None:

            # if we still don't have a transcription file path by now,
            # assume there is no link between the window and the resolve timeline
            # although that might be very weird, so warn the user
            if 'transcription_file_path' not in update_attr:
                logger.warning('No transcription file path found for window {}'.format(window_id))
                link = False
            else:
                # is there a link between the transcription and the resolve timeline?
                link, _ = self.toolkit_ops_obj.get_transcription_path_to_timeline_link(
                    transcription_file_path=update_attr['transcription_file_path'],
                    timeline_name=NLE.current_timeline['name'],
                    project_name=NLE.current_project)

            # update the import srt button if it was passed in the call
            if update_attr.get('import_srt_button', None) is not None:
                # update the import srt button on the transcription window
                update_attr['import_srt_button'] \
                    .pack(side=tk.BOTTOM, fill='x', **self.ctk_side_frame_button_paddings, anchor='sw')

            # update the link button text if it was passed in the call
            if update_attr.get('link_button', None) is not None:

                # the link button text depends on the above link
                if link:
                    link_button_text = 'Unlink from Timeline'
                    # update_attr['error_label'].config(text='')
                else:
                    link_button_text = 'Link to Timeline'

                    # if there's no link, let the user know
                    # update_attr['error_label'].config(text='Timeline mismatch')

                # update the link button on the transcription window
                update_attr['link_button'].configure(text=link_button_text)
                update_attr['link_button'] \
                    .pack(side=tk.BOTTOM, fill='x', **self.ctk_side_frame_button_paddings, anchor='sw')

            if window_id not in self.t_edit_obj.sync_with_playhead:
                self.t_edit_obj.sync_with_playhead[window_id] = False

            # update the sync button if it was passed in the call
            if update_attr.get('sync_button', None) is not None:

                if self.t_edit_obj.sync_with_playhead[window_id]:
                    sync_button_text = "Don't sync"
                else:
                    sync_button_text = "Sync with Playhead"

                # update the sync button on the transcription window
                update_attr['sync_button'].configure(text=sync_button_text)
                update_attr['sync_button'] \
                    .pack(side=tk.BOTTOM, fill='x', **self.ctk_side_frame_button_paddings, anchor='sw')

            # create the current_window_tc reference if it doesn't exist
            if window_id not in self.t_edit_obj.current_window_tc:
                self.t_edit_obj.current_window_tc[window_id] = ''

            # HOW WE CONVERT THE RESOLVE PLAYHEAD TIMECODE TO TRANSCRIPT LINES

            # only do this if the sync is on for this window
            # and if the timecode in resolve has changed compared to last time
            if self.t_edit_obj.sync_with_playhead[window_id] \
                    and self.t_edit_obj.current_window_tc[window_id] != NLE.current_tc:
                update_attr = self.sync_current_tc_to_transcript(window_id=window_id, **update_attr)

            # update the resolve buttons frame if it was passed in the call
            if update_attr.get('r_buttons_frame', None) is not None:
                show_resolve_buttons = True

        # finally, start showing the frames that need to be shown
        # if show_selection_buttons:
        #    # but also make sure that the s_buttons_frame is right after the t_buttons_frame
        update_attr['s_buttons_frame'].grid(row=1, column=0, **self.ctk_side_frame_button_paddings)

        # if there are no segments selected, disable the buttons in the s_buttons_frame
        for button in update_attr['s_buttons_frame'].winfo_children():
            if not show_selection_buttons:
                button.configure(state=tk.DISABLED)
            else:
                button.configure(state=tk.NORMAL)

        # also disable the segments-related buttons in the r_buttons_frame
        for button in [update_attr['selection_to_markers_button']]:
            if not show_selection_buttons:
                button.configure(state=tk.DISABLED)
            else:
                button.configure(state=tk.NORMAL)

        if show_resolve_buttons:
            update_attr['r_buttons_frame'].grid(row=2, column=0, **self.ctk_side_frame_button_paddings)
        else:
            update_attr['r_buttons_frame'].grid_forget()

    def sync_current_tc_to_transcript(self, window_id, **update_attr):

        # get the window transcription object
        transcription = self.get_window_by_id(window_id=window_id).transcription

        # if no text was passed, get it from the window
        if 'text' not in update_attr or type(update_attr['text']) is not tk.Text:
            # so get the link button from the window by using the hard-coded name
            update_attr['text'] \
                = self.windows[window_id].nametowidget('middle_frame.text_form_frame.transcript_text')

        # how many lines does the transcript on this window contain?
        max_lines = transcription.get_num_lines()

        if 'timecode' in update_attr and 'fps' in update_attr and 'start_tc' in update_attr:
            # initialize the timecode object for the current_tc
            current_tc_obj = Timecode(update_attr['fps'], update_attr['timecode'])

            # initialize the timecode object for the timeline start_tc
            timeline_start_tc_obj = Timecode(update_attr['fps'], update_attr['start_tc'])

        elif NLE.current_timeline_fps is not None and NLE.current_tc is not None:
            # initialize the timecode object for the current_tc
            current_tc_obj = Timecode(NLE.current_timeline_fps, NLE.current_tc)

            # initialize the timecode object for the timeline start_tc
            timeline_start_tc_obj = Timecode(NLE.current_timeline_fps, NLE.current_timeline['startTC'])

        else:
            logger.warning('No timecode or fps passed to sync_current_tc_to_transcript()')
            return None

        # subtract the two timecodes to get the corresponding transcript seconds
        if current_tc_obj > timeline_start_tc_obj:
            transcript_tc = current_tc_obj - timeline_start_tc_obj

            # so we can now convert the current tc into seconds
            transcript_sec = transcript_tc.float

        # but if the current_tc_obj is at 0 or less
        else:
            transcript_sec = 0

        self.set_active_segment_by_time(
            transcript_sec=transcript_sec, window_id=window_id,
            text_widget=update_attr['text'], transcription=transcription, toolkit_UI_obj=self)

        # highlight current line on transcript
        # update_attr['text'].tag_add('current_time')

        # now remember that we did the update for the current timecode
        self.t_edit_obj.current_window_tc[window_id] = NLE.current_tc

        return update_attr

    @staticmethod
    def set_active_segment_by_time(transcript_sec, window_id, text_widget, transcription, toolkit_UI_obj):
        """
        This attempts to find the closest segment to the transcript_sec time (in seconds)
        """

        # remove the current_time segment first
        text_widget.tag_delete('current_time')

        # find out which segment matches the passed transcript_sec
        for index, segment in enumerate(transcription.get_segments()):

            # if the transcript timecode in seconds is between the start and the end of this line
            if segment.start <= transcript_sec < segment.end - 0.01:
                text_widget_line = index + 1

                # set the line as the active segment on the timeline
                toolkit_UI_obj.t_edit_obj.set_active_segment(
                    window_id=window_id, text_widget=text_widget, text_widget_line=text_widget_line)

        text_widget.tag_config('current_time', foreground=toolkit_UI.theme_colors['white'])

    def sync_all_transcription_windows(self):

        # loop through all the open windows
        for window_id in self.windows:

            # check if it needs to be synced with the playhead
            if window_id in self.t_edit_obj.sync_with_playhead \
                    and self.t_edit_obj.sync_with_playhead[window_id]:
                # and if it does, sync it
                self.sync_current_tc_to_transcript(window_id)

    def update_all_transcription_windows(self):

        # loop through all the open windows
        for window_id in self.windows:

            # if the window is a transcription window
            if self.get_window_type(window_id=window_id) == 'transcription':
                # update the window
                self.update_transcription_window(window_id)

    def close_inactive_transcription_windows(self, timeline_transcription_file_paths=None):
        """
        Closes all transcription windows that are not in the timeline_transcription_file_paths list
        (or all of them if no list is passed)
        :param timeline_transcription_file_paths: list of transcription file paths
        :return: None
        """

        # get all transcription windows
        transcription_windows = self.get_all_windows_of_type('transcription')

        # loop through all transcription windows
        for transcription_window in transcription_windows:

            # if the transcription window is not in the timeline_transcription_file_paths
            if timeline_transcription_file_paths is None \
                    or timeline_transcription_file_paths == [] \
                    not in timeline_transcription_file_paths:

                # if the transcription window is open
                if transcription_window in self.windows:
                    # close the window
                    self.destroy_transcription_window(transcription_window)

    def destroy_transcription_window(self, window_id):

        # close any associated find windows and remove the reference from the text windows
        if window_id in self.text_windows:
            if 'find_window_id' in self.text_windows[window_id]:
                find_window_id = self.text_windows[window_id]['find_window_id']

                # call the default destroy window function to destroy the find window
                self.destroy_find_replace_window(window_id=find_window_id)

            # completely remove the reference from the text windows
            del self.text_windows[window_id]

        # destroy the associated search window (if it exists)
        # - in the future, if were to have multiple search windows, we will need to do it differently
        if window_id + '_search' in self.windows:
            self.destroy_window_(windows_dict=self.windows, window_id=window_id + '_search')

        # remove all other references to the transcription window
        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.typing[window_id]

        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.transcript_editing[window_id]

        if window_id in self.t_edit_obj.selected_segments:
            del self.t_edit_obj.selected_segments[window_id]

        if window_id in self.t_edit_obj.transcript_modified:
            del self.t_edit_obj.transcript_modified[window_id]

        if window_id in self.t_edit_obj.active_segment:
            del self.t_edit_obj.active_segment[window_id]

        if window_id in self.t_edit_obj.last_active_segment:
            del self.t_edit_obj.last_active_segment[window_id]

        if window_id in self.t_edit_obj.current_window_tc:
            del self.t_edit_obj.current_window_tc[window_id]

        if window_id in self.t_edit_obj.typing:
            del self.t_edit_obj.sync_with_playhead[window_id]

        # call the default destroy window function
        self.destroy_window_(windows_dict=self.windows, window_id=window_id)

    # TRANSCRIPT GROUP UI FUNCTIONS

    class TranscriptGroupsModule(ctk.CTkFrame):

        def __init__(self, master, window_id, toolkit_UI_obj, **kwargs):

            if window_id is None or toolkit_UI_obj is None:
                logger.error('Cannot add transcript groups module - window_id and toolkit_UI_obj must be provided')
                raise ValueError('window_id and toolkit_UI_obj cannot be None')

            # we will need these
            self.toolkit_UI_obj = toolkit_UI_obj
            self.t_edit_obj = toolkit_UI_obj.t_edit_obj
            self.toolkit_ops_obj = toolkit_UI_obj.toolkit_ops_obj
            self.stAI = toolkit_UI_obj.stAI

            # create the CTKScrollableFrame
            super().__init__(master, **kwargs)

            # also create the label for the group frame on the same parent
            self.groups_label = ctk.CTkLabel(self, text='Groups')

            # keep track of the window id in the object too (until we implement window objects)
            self.window_id = window_id

            # and the window itself (until we implement window objects)
            self.window = self.toolkit_UI_obj.get_window_by_id(self.window_id)

            # add the transcription object
            self._window_transcription = self.t_edit_obj.get_window_transcription(self.window_id)

            # we'll use another scrollable frame for the groups list because customtkinter doesn't support listboxes
            self._groups_list_frame = ctk.CTkScrollableFrame(self, name='groups_list_frame')
            self._groups_list_frame.bindtags(self._groups_list_frame.bindtags() + ('can_take_focus',))

            # add the groups form (where we can edit the selected group)
            self._groups_form = ctk.CTkFrame(self, name='groups_form')

            # add the form elements
            self._group_form_label = ctk.CTkLabel(self._groups_form, text='Edit Group')

            self._group_name_var = tk.StringVar(self)
            self._group_name_input = ctk.CTkEntry(self._groups_form, textvariable=self._group_name_var,
                                                  fg_color=toolkit_UI.theme_colors['black'])
            self._group_notes_var = tk.StringVar(self)
            self._group_notes_input = ctk.CTkTextbox(self._groups_form, fg_color=toolkit_UI.theme_colors['black'],
                                                     wrap=ctk.WORD)

            # add the buttons frame
            self._group_buttons_frame = ctk.CTkFrame(self._groups_form, **toolkit_UI.ctk_frame_transparent)

            # get the default update_segments
            self.update_segments = self.stAI.get_app_setting('transcript_update_group_segments', default_if_none=True)

            # add the auto-add CTkSwitch
            self._group_update_segments_var = tk.BooleanVar(self, value=self.update_segments)
            self._group_update_segments_switch = ctk.CTkSwitch(
                self._group_buttons_frame,
                text='Update Segments',
                variable=self._group_update_segments_var,
                command=self._toggle_update_segments
            )

            # if the _group_notes_input changes, update the initial prompt variable too
            def update_group_notes_input(*args):

                # update the group notes var
                self._group_notes_var.set(self._group_notes_input.get('1.0', tk.END))

            self._group_notes_input.bind('<KeyRelease>', update_group_notes_input)

            # we need to set the typing attribute to True when the user is typing in the group name or notes
            # so we don't trigger window shortcuts and other stuff
            self._group_name_input.bind('<FocusIn>', self._on_group_form_input_focusin)
            self._group_name_input.bind('<FocusOut>', self._on_group_form_input_focusout)
            self._group_notes_input.bind('<FocusIn>', self._on_group_form_input_focusin)
            self._group_notes_input.bind('<FocusOut>', self._on_group_form_input_focusout)

            # defocus on ESC
            self._group_name_input.bind('<Escape>', lambda event: self.focus_set())
            self._group_notes_input.bind('<Escape>', lambda event: self.focus_set())

            # same on ENTER
            self._group_name_input.bind('<Return>', lambda event: self.focus_set())
            self._group_notes_input.bind('<Return>', lambda event: self.focus_set())

            # but not on CMD+ENTER
            self._group_notes_input.bind('<Command-Return>', lambda event: None)

            # done with UI stuff for now

            # let's start with the data

            # keep track of the groups that are listed in this module
            # {'group id' = {group_data}, ...}
            self._groups_data = {}

            # keep track of the selected group id
            # but use selected_group_id attribute - see @property below
            self._selected_group_id = None
            self._selected_group_list_idx = None
            self._selected_group_label = None

            # this says what happens with the segment selection on the window when we deselect a group
            self._keep_segment_selection = False

            # if this is True,
            # we will show the first segment of the group in the text widget right after selection
            self._show_first_segment = False

            # this will determine whether self is on a grid or not
            # set the module visibility to false for starters
            self._visible = False

            # on which row of the grid should the module be placed?
            # if none was provided, place it on the next row
            self._grid_row = kwargs.get('grid_row', self.master.grid_size()[1] + 1)

            # set the paddings, if not provided
            self._module_paddings = dict()
            self._module_paddings['padx'] = toolkit_UI.ctk_side_frame_button_paddings['padx'] \
                if 'padx' not in kwargs else kwargs['padx']
            self._module_paddings['padx'] = toolkit_UI.ctk_side_frame_button_paddings['pady'] \
                if 'pady' not in kwargs else kwargs['pady']

            # get the transcription file path using the window id
            # we cannot open the groups module without a transcription file path to get the data from
            if self._window_transcription.transcription_file_path is None:
                logger.error('Cannot open groups module - no transcription file path found for window id: {}'
                             .format(self.window_id))
                raise RuntimeError('Cannot open groups module - no transcription file path found for window id: {}')

            # add transcript groups module to the parent frame
            # this also adds the groups into the groups list
            if self._add_transcript_groups_module() is None:
                logger.error('Cannot add transcript groups module or window {}.'.format(self.window_id))
                raise RuntimeError('Cannot add transcript groups module or window {}.'.format(self.window_id))

            # add an OBSERVER - whenever the groups list changes externally, we need to update the transcript groups
            self.update_observer = self.toolkit_UI_obj.add_observer_to_window(
                window_id=self.window_id,
                action='update_transcription_groups_{}'.format(self._window_transcription.transcription_path_id),
                callback=lambda: self.reload_list()
            )

        @property
        def window_transcription(self):
            return self._window_transcription

        @property
        def selected_group_id(self):
            return self._selected_group_id

        @selected_group_id.setter
        def selected_group_id(self, value):

            # once the group id is changed...
            self._selected_group_id = value

            # get the children of the groups list frame
            children = self._groups_list_frame.winfo_children()

            self._selected_group_label = None
            group_y_pos = 0

            # find the child that has the same group id as the selected group id
            for idx, child in enumerate(children):

                # if the child has the same name as the selected group id, set the selected group list idx
                if child.group_id == self._selected_group_id:
                    self._selected_group_list_idx = idx

                    # set the fg_color to the "selected" color
                    child.configure(fg_color=toolkit_UI.ctk_selected_color)

                    # set the selected group label
                    self._selected_group_label = child

                    # make sure the selected group is in view
                    if self._selected_group_label and not self._is_group_label_in_view(self._selected_group_label):
                        # get the y position of the child and the height of the parent frame
                        group_y_pos = self._selected_group_label.winfo_y() \
                                      - (1 if self._selected_group_label.winfo_y() > 1 else 0)

                        parent_frame_height = self._groups_list_frame.winfo_height()

                        # illegally move the canvas of the groups list frame to the selected group
                        self._groups_list_frame._parent_canvas.yview_moveto((group_y_pos / parent_frame_height))

                    continue

                # otherwise set the fg_color "unselected" color
                child.configure(fg_color=toolkit_UI.ctk_unselected_color)

            # select the transcript segments in the transcript window that are in the group
            self._select_selected_group_segments()

            # populate the group form with the selected group data
            self._populate_group_form()

        def _add_transcript_groups_module(self, **kwargs):
            """
            Adds the transcript groups module to the parent frame
            """

            # add the group frame to the grid and configure it so that it expands
            self.grid(row=self._grid_row, column=0, sticky="nsew", **self._module_paddings)
            self.columnconfigure(0, weight=1)

            # add the group label and groups list in the main frame that we added above
            self.groups_label.grid(row=1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
            self._groups_list_frame.grid(row=2, column=0, sticky="nsew", **toolkit_UI.ctk_frame_paddings)

            # add the buttons frame
            self._group_buttons_frame.grid(row=3, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # add the buttons to the buttons frame
            self._group_update_segments_switch.grid(row=0, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # extend the row we just created on the master as much as possible vertically
            # keeping a weight of 1 will equal distribution of space among widgets
            self.master.rowconfigure(self._grid_row, weight=1)

            # extend the groups list frame as much as possible vertically
            self.rowconfigure(2, weight=1)

            # bind the _groups_list_frame to the press event
            # so that we deselect the all groups if we click outside of them
            # but for some reason we need to bind this to the master
            self._groups_list_frame.master.bind('<Button-1>', lambda event: self._on_groups_list_frame_press(event))

            # do an initial update of the groups list
            self.update_list()

            return True

        def update_list(self):
            """
            This updates the groups list in the transcript groups module
            """

            # get the transcript groups for this window
            if not self._set_groups_data():
                # if nothing has changed, we don't need to do anything
                return

            self._populate_groups_list()

        def reload_list(self):
            """
            This calls the transcription to be reloaded from file and then updates the groups list
            """

            # reload the groups from the transcription file
            self._window_transcription.reload_from_file(save_first=True)

            # perform list update
            self.update_list()

            # update the status bar in the transcription window
            self.toolkit_UI_obj.update_window_status_label(
                self.window_id, text='Groups reloaded.')

        def _set_groups_data(self):
            """
            This asks the UI object to get the groups data from the transcription
            If the data we have is different to the data we have in the object, we update the object

            :return: True if the groups data is different to the data we have in the object, False otherwise
            """

            new_transcript_groups_data = self._window_transcription.transcript_groups

            # compare the two dictionaries
            if new_transcript_groups_data != self._groups_data:
                # update the groups data in the object
                self._groups_data = new_transcript_groups_data

                return True

            return False

        def _populate_groups_list(self):
            """
            We're populating the groups list with the groups - which contains the id and the details of the group
            """

            # empty the groups list by destroying all the widgets in the groups frame
            # get the children of the groups frame
            children = self._groups_list_frame.winfo_children()

            # remove all the children of the groups list frame
            for child in children:
                # does the child still exist in the groups list frame?
                if child.winfo_exists():
                    # destroy the child
                    child.destroy()

            if isinstance(self._groups_data, dict):

                # sort the groups data by ['name'] alphabetically
                self._groups_data = {k: v for k, v in sorted(self._groups_data.items(), key=lambda x: x[1]['name'])}

                row_num = 0

                # loop through the groups
                for group_id, group_details in self._groups_data.items():
                    # increment the row number
                    row_num += 1

                    # add a label for the group
                    group_label = ctk.CTkLabel(self._groups_list_frame, anchor="w", text=group_details['name'],
                                               name=group_id, **toolkit_UI.ctk_fake_listbox_label_paddings)
                    group_label.grid(row=row_num, column=0, sticky="ew", **toolkit_UI.ctk_fake_listbox_paddings)

                    # add the group id to the group label
                    group_label.group_id = group_id

                    # bind a click event to the group label
                    group_label.bind('<Button-1>',
                                     lambda event, l_group_id=group_id: self._on_group_press(event, l_group_id))

                # make sure the column is expanded
                self._groups_list_frame.columnconfigure(0, weight=1)

            # select the group that was already selected
            self.select_group(self.selected_group_id)

        def select_group(self, group_id: str = None, show_first_segment: bool = False):
            """
            This selects a group in the groups list
            """

            # set the show first segment flag
            self._show_first_segment = show_first_segment

            # change the selected_group_id property
            # this will also trigger the selected_group_id setter
            self.selected_group_id = group_id

            # set the show first segment flag back to False
            self._show_first_segment = False

        def deselect_group(self, keep_segment_selection=False):
            """
            This deselects the currently selected group
            :param keep_segment_selection: if True, the segments selected in the parent window will not be deselected
            """

            # toggle this flag to keep the segment selection if needed
            self._keep_segment_selection = keep_segment_selection

            # then, deselect the group
            self.selected_group_id = None

            # toggle the flag back to False
            self._keep_segment_selection = False

        def _select_first_group(self):

            # get the first group id
            group_id = list(self._groups_data.keys())[0]

            # select the group
            self.select_group(group_id)

        def _select_last_group(self):

            # get the last group id
            group_id = list(self._groups_data.keys())[-1]

            # select the group
            self.select_group(group_id)

        def select_next(self):
            """
            This selects the next group in the groups list
            """

            # if there are no groups, we can't select the next group
            if not self._groups_data:
                return

            # if there is no selected group, we select the first group
            if not self.selected_group_id:
                self._select_first_group()
                return

            # increment the index of the selected group +1
            # or if it's out of range, use 0
            next_index = self._selected_group_list_idx + 1 \
                if len(self._groups_data) > self._selected_group_list_idx + 1 else 0

            # get the group id of the next group
            group_id = list(self._groups_data.keys())[next_index]

            # select the group
            self.select_group(group_id)

        def select_previous(self):
            """
            This selects the previous group in the groups list
            """

            # if there are no groups, we can't select the previous group
            if not self._groups_data:
                return

            # if there is no selected group, we select the last group
            if not self.selected_group_id:
                self._select_last_group()
                return

            # decrement the index of the selected group -1
            previous_index = self._selected_group_list_idx - 1 \
                if self._selected_group_list_idx - 1 >= 0 else len(self._groups_data) - 1

            # get the group id of the previous group
            group_id = list(self._groups_data.keys())[previous_index]

            # select the group
            self.select_group(group_id)

        def _on_group_press(self, event, group_id):
            """
            This is called when a group is pressed in the groups list
            """

            # deselect all other tkinter items on the window
            self.toolkit_UI_obj.get_window_by_id(self.window_id).focus_set()

            # if we're pressing the group that is already selected,
            # deselect the group
            if group_id == self.selected_group_id:
                # deselect the group
                self.select_group(group_id=None)
                return 'break'

            # otherwise
            # select the group and show the first segment
            self.select_group(group_id=group_id, show_first_segment=True)

            # force focus on this widget
            self.focus_set()

            # don't propagate the event
            return "break"

        def _on_groups_list_frame_press(self, event):
            """
            When pressing the groups list frame, we want to deselect the group
            """

            # deselect all other tkinter items on the window
            self.toolkit_UI_obj.get_window_by_id(self.window_id).focus_set()

            # deselect all the groups
            self.select_group(group_id=None)

        def _select_selected_group_segments(self):
            """
            This selects the segments in the transcript window that are in the selected group
            """

            # don't do anything if we're supposed to keep the segment selection
            if self._keep_segment_selection:
                return

            # if we don't have a selected group
            if self.selected_group_id is None:
                # clear the segment selection
                self.t_edit_obj.clear_selection(self.window_id)
                return

            # get the time intervals from the group
            time_intervals = self._groups_data[self.selected_group_id]['time_intervals']

            self._select_window_segments(time_intervals)

        def _select_window_segments(self, time_intervals):
            """
            This selects the segments in the transcript window that are in the given time intervals
            """

            # get only the transcript segments that are within the time intervals
            group_segments = self.window_transcription.time_intervals_to_transcript_segments(time_intervals)

            # and select the segments
            self.t_edit_obj.segment_to_selection(window_id=self.window_id, line=group_segments)

            # if the show first segment flag is True, show the first selected segment in the transcript
            if self._show_first_segment:
                self.t_edit_obj.go_to_first_selected_segment(window_id=self.window_id)

        def _populate_group_form(self):
            """
            This populates the group form with the details of the selected group
            """

            # if we don't have a selected group, grid forget the group form
            if self.selected_group_id is None:

                # grid forget the group form
                self._groups_form.grid_forget()

                return

            else:

                # put the group details in the variable
                self._group_name_var.set(self._groups_data[self.selected_group_id]['name'])

                # put the group notes in the variable
                self._group_notes_var.set(self._groups_data[self.selected_group_id]['notes'])

                # but also in the text, since the variable cannot be attached to the text widget
                self._group_notes_input.delete('1.0', 'end')
                self._group_notes_input.insert('1.0', self._groups_data[self.selected_group_id]['notes'])

                # add the groups form elements to the groups form
                self._group_form_label.grid(row=0, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
                self._group_name_input.grid(row=1, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)
                self._group_notes_input.grid(row=2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

                # add the groups form to the grid
                self._groups_form.grid(row=3, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

                return

        def _on_group_form_input_focusin(self, *args, **kwargs):
            """
            Trigger this whenever you focus in the group form inputs
            """

            # the typing in window lock
            self.t_edit_obj.set_typing_in_window(None, self.window_id, True)

            # change the status of the transcription window
            self.toolkit_UI_obj.update_window_status_label(
                self.window_id, text='Group info not saved.', color='bright_red')

        def _on_group_form_input_focusout(self, *args, **kwargs):
            """
            Trigger this whenever you focus out of the group form inputs
            """

            # release the typing in window lock
            self.t_edit_obj.set_typing_in_window(None, self.window_id, False)

            # save the group form
            self._save_group_form()

        def _save_group_form(self):
            """
            This saves the group form
            """

            # if we don't have a selected group, return
            if self.selected_group_id is None:
                return

            # get the group name and notes
            group_name = self._group_name_var.get().strip()
            group_notes = self._group_notes_var.get().strip()

            # if the group name is different than the one in the group data
            if group_name != self._groups_data[self.selected_group_id]['name']:

                # check if there isn't already a group with this new name
                # and have the user confirm if they want to proceed with having two groups with the same name
                if not self._duplicate_name_confirm(group_name):
                    # if they don't want that, stop
                    return

            # if the group name or notes are different than the ones in the group data
            if group_name != self._groups_data[self.selected_group_id]['name'] \
                    or group_notes != self._groups_data[self.selected_group_id]['notes']:
                # make a copy of the groups data
                new_groups_data = copy.deepcopy(self._groups_data)

                # add the group name and notes to the new groups data
                new_groups_data[self.selected_group_id]['name'] = group_name
                new_groups_data[self.selected_group_id]['notes'] = group_notes

                # update transcription
                self._push_group_change_to_transcription(new_groups_data)

                # update window status label
                self.toolkit_UI_obj.update_window_status_label(self.window_id, 'Group info updated.')

                # update the group list
                self.update_list()

                return True

            # update window status label
            self.toolkit_UI_obj.update_window_status_label(self.window_id, '')

        def _duplicate_name_confirm(self, group_name: str) -> bool:

            # check if there isn't already a group with this new name
            if self._groups_data and len(self._groups_data) > 0 \
                    and group_name.lower().strip() in \
                    [self._groups_data[group_id]['name'].lower().strip() for group_id in self._groups_data]:
                # and ask the user if they want to overwrite it

                if not messagebox.askyesno(title='Duplicate name?',
                                           message='There is already a group "{}" for this transcript.\n'
                                                   'Are you sure you want to continue?'.format(group_name),
                                           parent=self.window):
                    # if they don't want to overwrite it, focus on the group name input
                    self._group_name_input.focus()

                    # and stop the save process
                    return False

            return True

        def delete_selected_group(self):
            """
            This deletes the selected group
            """

            # if we don't have a selected group, return
            if self.selected_group_id is None:
                return

            # ask the user if they are sure they want to delete the group
            if not messagebox.askyesno(title='Delete group?',
                                       message='Are you sure you want to delete the group "{}"?'.format(
                                           self._groups_data[self.selected_group_id]['name'])):
                return

            # get a copy of the group data
            new_groups_data = copy.deepcopy(self._groups_data)

            # get the group name for the status label
            group_name = new_groups_data[self.selected_group_id]['name']

            # delete the group from the group data
            del new_groups_data[self.selected_group_id]

            # deselect the group
            self.selected_group_id = None

            # update transcription
            self._push_group_change_to_transcription(new_groups_data)

            # update window status label
            self.toolkit_UI_obj.update_window_status_label(self.window_id, 'Group "{}" deleted.'.format(group_name))

            # update the group list
            self.update_list()

            return

        def update_group_segments(self):
            """
            This updates the group segments of the selected group
            according to the the segments selected in the parent window
            """

            # if we don't have a selected group, return
            if self.selected_group_id is None:
                return

            # collect the selected segments from the parent window
            group_time_intervals = self._selected_segments_to_group_intervals()

            # if the group time intervals are different than the ones in the group data
            if group_time_intervals != self._groups_data[self.selected_group_id]['time_intervals']:
                # make a copy of the groups data
                new_groups_data = copy.deepcopy(self._groups_data)

                # add the group time intervals to the new groups data
                new_groups_data[self.selected_group_id]['time_intervals'] = group_time_intervals

                # update transcription
                self._push_group_change_to_transcription(new_groups_data)

                # update window status label
                self.toolkit_UI_obj.update_window_status_label(self.window_id, 'Group segments updated.')

                # update the group list
                self.update_list()

            return

        def _push_group_change_to_transcription(self, groups_data):
            """
            This pushes the group change to the transcription

            :param: groups_data: the new groups data (must contain the all the groups, similar to self._groups_data)
            """

            # push this change to the toolkit_ops_obj
            self._window_transcription.set_transcript_groups(transcript_groups=groups_data)

            # ask the transcription for a save to file
            self._window_transcription.save_soon(
                backup=self.stAI.transcript_backup_interval,
                if_successful=lambda: self.t_edit_obj.update_status_label_after_save(self.window_id, True),
                if_failed=lambda: self.t_edit_obj.update_status_label_after_save(self.window_id, 'fail'),
                if_none=lambda: self.t_edit_obj.update_status_label_after_save(self.window_id, False)
            )

        def _toggle_update_segments(self):
            """
            This toggles the auto add to group option
            """

            # toggle the auto add to group option according to the _group_update_segments_var
            self.update_segments = self._group_update_segments_var.get()

        def _selected_segments_to_group_intervals(self):
            """
            This converts the segments selected in the parent window to intervals used for the group data
            """

            # get the segments selected in the parent window
            selected_segments = self.t_edit_obj.get_window_selected_segments(
                window_id=self.window_id, list_only=True)

            # get a proper list of time intervals based on the segments
            group_time_intervals = \
                self._window_transcription.transcript_segments_to_time_intervals(segments=selected_segments)

            return group_time_intervals

        def add_new_group(self):
            """
            This adds a new group and then adds the segments selected in the parent window to it (if any are selected)
            """

            # ask for the group name
            # create a list of widgets for the input dialogue
            input_widgets = [
                {'name': 'group_name', 'label': 'Group Name:', 'type': 'entry', 'default_value': ''}
            ]

            user_input = self.toolkit_UI_obj.AskDialog(
                title='New Group', input_widgets=input_widgets, parent=self.window, toolkit_UI_obj=self.toolkit_UI_obj) \
                .value()

            if not user_input or 'group_name' not in user_input or not user_input['group_name']:
                return False

            # check if there isn't already a group with this new name
            # and ask the user to confirm if they want to have multiple groups with the same name
            if not self._duplicate_name_confirm(user_input['group_name']):
                return False

            # make a copy of the groups data
            new_groups_data = copy.deepcopy(self._groups_data) if self._groups_data else {}

            # collect the selected segments from the parent window
            group_time_intervals = self._selected_segments_to_group_intervals()

            # ask the user to confirm if they want to add an empty group
            if not group_time_intervals or not isinstance(group_time_intervals, list) or len(group_time_intervals) == 0:
                if not messagebox.askyesno(title="Empty group",
                                           message="You haven't selected any segments to add to the group.\n"
                                                   "Add new group anyway?"):
                    return False

            # prepare the new dict of the new group
            # (this will return a dict looking like this {group_id: group_data})
            new_group = self._window_transcription.prepare_transcript_group(
                group_name=user_input['group_name'],
                time_intervals=group_time_intervals
            )

            # get the group id
            new_group_id = list(new_group.keys())[0]

            # add the new group to the group data
            new_groups_data = {**new_groups_data, **new_group}

            # update transcription
            self._push_group_change_to_transcription(new_groups_data)

            # update window status label
            self.toolkit_UI_obj.update_window_status_label(self.window_id, 'New group added.')

            # update the group list
            self.update_list()

            # finally, select the new group
            self.select_group(group_id=new_group_id)

            return

        def add_new_groups(self, groups_data):
            """
            This adds new groups to the transcription
            """

            # if we don't have any groups data, return
            if not groups_data:
                return

            # deselect all groups
            self.deselect_group()

            # make a copy of the groups data
            new_groups_data = copy.deepcopy(self._groups_data) if self._groups_data else {}

            # take each group and prepare it for the transcription
            # this will eventually return a dict looking like this {group_id: group_data, group_id2: group_data2 ....}
            for current_group in groups_data:

                # all groups must have a non-empty name
                if 'group_name' not in current_group or not current_group['group_name']:
                    logger.debug('Cannot add group "{}" - no group name provided.'.format(current_group))
                    continue

                # all groups must have a non-empty time intervals dict
                if 'time_intervals' not in current_group or not current_group['time_intervals']:
                    logger.debug('Cannot add group "{}" - no time intervals provided.'
                                 .format(current_group['group_name']))
                    continue

                new_group = self._window_transcription.prepare_transcript_group(
                    group_name=current_group['group_name'],
                    group_notes=current_group.get('group_notes', ''),
                    time_intervals=current_group['time_intervals']
                )

                # add the new group to the groups data dict
                new_groups_data = {**new_groups_data, **new_group}

            # update window status label
            self.toolkit_UI_obj.update_window_status_label(self.window_id, 'New groups added.')

            # update transcription
            self._push_group_change_to_transcription(new_groups_data)

            # update the group list
            self.update_list()

        def _is_group_label_in_view(self, label_widget=None):
            """
            This checks if the group label is in view
            """

            scrollable_frame = self._groups_list_frame

            label_coords = label_widget.winfo_x(), label_widget.winfo_y()
            canvas_coords = scrollable_frame._parent_canvas.canvasx(0), scrollable_frame._parent_canvas.canvasy(0)
            canvas_size = scrollable_frame._parent_canvas.winfo_width(), scrollable_frame._parent_canvas.winfo_height()
            label_size = label_widget.winfo_width(), label_widget.winfo_height()

            if scrollable_frame._orientation == "horizontal":
                visible_range = (canvas_coords[0], canvas_coords[0] + canvas_size[0])
                label_range = (label_coords[0], label_coords[0] + label_size[0])
            elif scrollable_frame._orientation == "vertical":
                visible_range = (canvas_coords[1], canvas_coords[1] + canvas_size[1])
                label_range = (label_coords[1], label_coords[1] + label_size[1])

            else:
                raise ValueError("Invalid orientation: {}".format(scrollable_frame._orientation))

            return visible_range[0] <= label_range[0] and visible_range[1] >= label_range[1]

    # STORY EDITOR WINDOW FUNCTIONS

    class StoryEdit:

        @classmethod
        def edit_story_text(cls, window_id, toolkit_UI_obj):

            if window_id is None:
                logger.error('Cannot edit story. No window id provided.')
                return False

            # get the window
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # get the story text
            story_text = window.text_widget.get('1.0', 'end-1c')

            window.typing = True
            window.editing = True

            window.text_widget.focus()

            # ESCAPE key defocuses from widget (and implicitly saves the story, see below)
            window.text_widget.bind('<Escape>',
                                    lambda e: cls.defocus_text(
                                        window_id=window_id, toolkit_UI_obj=toolkit_UI_obj)
                                    )

            # text focusout saves story
            window.text_widget.bind('<FocusOut>',
                                    lambda e: cls.on_text_widget_defocus(
                                        e, window_id=window_id, toolkit_UI_obj=toolkit_UI_obj)
                                    )

            # bind CMD/CTRL + key events
            window.text_widget.bind("<" + toolkit_UI_obj.ctrl_cmd_bind + "-KeyPress>",
                                    lambda e: toolkit_UI.StoryEdit.on_edit_press(
                                        e, window=window, toolkit_UI_obj=toolkit_UI_obj, special_key='cmd')
                                    )

            # on any other button press, process through the on_edit_press function
            window.text_widget.bind('<Key>',
                                    lambda e: cls.on_edit_press(
                                        e, window=window, toolkit_UI_obj=toolkit_UI_obj)
                                    )

            window.text_widget.config(state=ctk.NORMAL)

        @staticmethod
        def is_story_changed(window_id, toolkit_UI_obj):
            """
            We're using the window.story_lines list to compare it with the window.story.lines list (not the text widget)
            """

            changed = False

            # get the window
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # if the lists have different lengths, the story has changed
            if len(window.story_lines) != len(window.story.lines):
                return True

            # take each line and compare it to the corresponding line in the story object
            for line_num, line in enumerate(window.story_lines):

                # if the line is different than the one in the story object
                if line.get('text', '') != window.story.lines[line_num].text\
                        or line.get('type', 'text') != window.story.lines[line_num].type:

                    # set the changed flag to True
                    return True

            if not changed:
                toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Story unchanged.', color='normal')

            # if we got here, the story is unchanged
            return changed

        @classmethod
        def on_text_widget_defocus(cls, e, window_id, toolkit_UI_obj):
            """
            This function is called when the user clicks outside of the transcript text widget
            """

            if window_id is None:
                return False

            # if the transcript was changed
            if cls.is_story_changed(window_id=window_id, toolkit_UI_obj=toolkit_UI_obj):
                cls.on_press_save_story(e, window_id=window_id, toolkit_UI_obj=toolkit_UI_obj)

        @classmethod
        def defocus_text(cls, window_id, toolkit_UI_obj):

            window = toolkit_UI_obj.get_window_by_id(window_id)

            # defocus from transcript text
            tk_transcription_window = window.text_widget.winfo_toplevel()
            tk_transcription_window.focus()

            # disable text editing again
            window.text_widget.config(state=ctk.DISABLED)

            # unbind all the editing keys
            cls.unbind_editing_keys(window.text_widget)

        @staticmethod
        def unbind_editing_keys(text_widget):
            text_widget.unbind('<Escape>')
            text_widget.unbind('<Key>')

        @classmethod
        def on_press_save_story(cls, e, window_id, toolkit_UI_obj):

            window = toolkit_UI_obj.get_window_by_id(window_id)

            # disable text editing again
            window.text_widget.config(state=ctk.DISABLED)

            # unbind all the editing keys
            cls.unbind_editing_keys(window.text_widget)

            # deactivate typing and editing
            window.typing = False
            window.editing = False

            # save the story
            cls.save_story(window_id=window_id, toolkit_UI_obj=toolkit_UI_obj)

        @staticmethod
        def save_story(window_id, toolkit_UI_obj, force=False, sec=1):

            # use the window_id to get the window object
            if isinstance(window_id, str):
                window = toolkit_UI_obj.get_window_by_id(window_id)

            # or if the window object was passed instead of its id, make use of it
            else:
                window = window_id
                window_id = window.window_id

            # replace all the lines in the story object with the lines in the window.story_lines list
            window.story.replace_all_lines(window.story_lines)

            return window.story.save_soon(
                backup=toolkit_UI_obj.stAI.story_backup_interval,
                force=force,
                if_successful=lambda: toolkit_UI.StoryEdit.update_status_label_after_save(
                    window_id=window_id, toolkit_UI_obj=toolkit_UI_obj, save_status=True),
                if_failed=lambda: toolkit_UI.StoryEdit.update_status_label_after_save(
                    window_id=window_id, toolkit_UI_obj=toolkit_UI_obj, save_status='fail'),
                if_none=lambda: toolkit_UI.StoryEdit.update_status_label_after_save(
                    window_id=window_id, toolkit_UI_obj=toolkit_UI_obj),
                sec=sec
            )

        @staticmethod
        def update_status_label_after_save(window_id, toolkit_UI_obj, save_status=None):

            if save_status is True:
                # show the user that the transcript was saved
                toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Story saved.', color='normal')

            # in case anything went wrong while saving,
            # let the user know about it
            elif save_status == 'fail':
                toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Story save failed.', color='bright_red')

            # in case the save status is False
            # assume that nothing needed saving
            else:
                toolkit_UI_obj.update_window_status_label(
                    window_id=window_id, text='Story unchanged.', color='normal')

        @classmethod
        def update_text_widget(cls, window_id: str or object, toolkit_UI_obj, story_lines=None):

            # assume that we're getting the window object if the window_id is not a string
            window = toolkit_UI_obj.get_window_by_id(window_id) if isinstance(window_id, str) else window_id

            # if we don't have story lines, get them from the story object
            if story_lines is None:
                story_lines = window.story_lines

            # if we still don't have story lines, stop
            if story_lines is None:
                return None

            # get the text widget state so we can restore it after updating the text widget
            text_widget_state = window.text_widget.cget('state')

            window.text_widget.config(state=ctk.NORMAL)

            # remember the scroll position
            text_widget_scroll_position = window.text_widget.yview()[0]

            # clear the text widget
            window.text_widget.delete('1.0', 'end')

            # add the story lines to the text widget
            for line in story_lines:

                current_line_no = window.text_widget.index('end-1c').split('.')[0]

                # if the line is a dict, get the text from the dict
                line_text = line.get('text', None)

                # add the line to the text widget
                window.text_widget.insert('end', line_text + '\n')

                if line.get('type', 'text') != 'text':

                    # add a tag to the new line
                    window.text_widget.tag_add(
                        'line_external_{}'.format(current_line_no),
                        '{}.0'.format(int(current_line_no)),
                        '{}.end'.format(int(current_line_no))
                    )

                    # change the background color to superblack
                    window.text_widget.tag_config(
                        'line_external_{}'.format(current_line_no), foreground=toolkit_UI.theme_colors['supernormal'])

            # remove the last newline character
            window.text_widget.delete('end-1c')

            # restore the text widget state
            window.text_widget.config(state=text_widget_state)

            # restore the scroll position
            # - this is not 100% precise but better than any other solution...
            window.text_widget.yview_moveto(text_widget_scroll_position)

            return True

        @classmethod
        def add_undo_step(cls, window):

            # take a snapshot of the current story lines
            # current_story_lines = window.story_lines.copy()
            current_story_lines = copy.deepcopy(window.story_lines)

            if not hasattr(window, 'story_lines_undo_steps'):
                window.story_lines_undo_steps = []

            # if we have more than 30 undo steps, remove the oldest one
            if len(window.story_lines_undo_steps) > 30:
                del window.story_lines_undo_steps[0]

            line, char, _ = cls.get_current_line_char(window.text_widget)

            # add the current story lines and the cursor position to the undo steps
            window.story_lines_undo_steps.append({'story_lines': current_story_lines, 'pos': (line, char)})

            window.text_widget.edit_separator()

            # also reset the redo steps
            window.story_lines_redo_steps = []

        @classmethod
        def recall_undo_redo(cls, window, toolkit_UI_obj, undo=True):

            reverted_step = {'story_lines': [], 'pos': (0, 0)}

            # if we're undoing
            if undo:

                if hasattr(window, 'story_lines_undo_steps') and len(window.story_lines_undo_steps) > 0:

                    # get the last undo step
                    reverted_step = window.story_lines_undo_steps.pop()

                    # if we have more than 30 redo steps, remove the oldest one
                    if len(window.story_lines_redo_steps) > 30:
                        del window.story_lines_redo_steps[0]

                    # add the current story lines and insert position to the redo steps
                    line, char, _ = cls.get_current_line_char(window.text_widget)
                    current_story_lines = copy.deepcopy(window.story_lines)
                    window.story_lines_redo_steps.append({'story_lines': current_story_lines, 'pos': (line, char)})

                    # set the story lines to the last undo step
                    window.story_lines = reverted_step['story_lines']

                    cls.update_text_widget(window_id=window, toolkit_UI_obj=toolkit_UI_obj)

            # if we're redoing
            else:

                if hasattr(window, 'story_lines_redo_steps') and len(window.story_lines_redo_steps) > 0:

                    # get the last redo step
                    reverted_step = window.story_lines_redo_steps.pop()

                    # add the current story lines and insert position to the redo steps
                    line, char, _ = cls.get_current_line_char(window.text_widget)
                    current_story_lines = copy.deepcopy(window.story_lines)
                    window.story_lines_undo_steps.append({'story_lines': current_story_lines, 'pos': (line, char)})

                    # set the story lines to the last redo step
                    window.story_lines = reverted_step['story_lines']

                    cls.update_text_widget(window_id=window, toolkit_UI_obj=toolkit_UI_obj)

            # get the position of the cursor on the undo/redo step
            line, char = reverted_step.get('pos')

            # go to the line we were on before the undo, but only if it exists
            if line != 0:
                window.text_widget.mark_set('insert', '{}.{}'.format(line, char))

            # move the scroll to the line we were on before the undo if it's not in view
            if not cls.is_line_in_view(window.text_widget, line):
                window.text_widget.see('insert')

        @staticmethod
        def label_to_not_saved(window, toolkit_UI_obj):

            # change label to 'Not saved'
            if toolkit_UI_obj.get_window_status_label_text(window_id=window.window_id) != 'Changes not saved.':
                toolkit_UI_obj.update_window_status_label(
                    window_id=window.window_id, text='Changes not saved.', color='red')

        @classmethod
        def on_edit_press(cls, e, window, toolkit_UI_obj, special_key=None):

            # we're using the window object here instead of the window_id to optimize performance
            # since we're using this function on every key press
            line, char, end_char = cls.get_current_line_char(window.text_widget)

            # move the index on the current line
            story_line_index = int(line) - 1

            # prepare a function to deal with the active selection on some key presses
            def delete_active_selection():

                if window.text_widget.tag_ranges('sel'):

                    # get the current key press
                    current_key = e.keysym

                    # call this same function, while triggering the DELETE key
                    e.keysym = 'Delete'

                    # simulate the DELETE key press to delete the selection
                    cls.on_edit_press(e, window, toolkit_UI_obj, special_key='')

                    # restore the current key press
                    e.keysym = current_key

                return False

            # first capture the special key presses
            # COPY and CUT
            if (special_key == 'cmd' and e.keysym.lower() == 'c') \
                    or (special_key == 'cmd' and e.keysym == 'x'):

                # if there's an active selection, process it
                if window.text_widget.tag_ranges('sel'):

                    # get the start and end of the selection
                    sel_start_line, sel_start_char = window.text_widget.index('sel.first').split('.')
                    sel_end_line, sel_end_char = window.text_widget.index('sel.last').split('.')

                    # convert to int
                    sel_start_line = int(sel_start_line)
                    sel_start_char = int(sel_start_char)
                    sel_end_line = int(sel_end_line)
                    sel_end_char = int(sel_end_char)

                    # this clears the real clipboard
                    clipboard_text = ''
                    window.clipboard_clear()

                    # clear the story editor clipboard
                    window.story_list_clipboard = []

                    for c_line in range(sel_start_line, sel_end_line+1):

                        current_line = copy.deepcopy(cls.get_line(window, line_index=int(c_line) - 1))

                        # this might happen if we're selecting text beyond the last line of the story
                        if current_line is None:
                            continue

                        # if the line is a text line, mind the start and end chars
                        if 'type' not in current_line or current_line['type'] == 'text':

                            if c_line == sel_start_line and sel_start_char > 0:
                                if c_line == sel_end_line:
                                    # for the case when we're selecting text from a single line
                                    current_line['text'] = current_line['text'][sel_start_char:sel_end_char]
                                else:
                                    current_line['text'] = current_line['text'][sel_start_char:]

                            # if this is the last line, only keep the text before the end char
                            elif c_line == sel_end_line:
                                current_line['text'] = current_line['text'][:sel_end_char]

                        # add to story editor clipboard
                        window.story_list_clipboard.append(current_line)

                        # add to real clipboard
                        clipboard_text += current_line['text'] + '\n'

                    # remove the last newline character, if it's a new line
                    if clipboard_text.endswith('\n'):
                        clipboard_text = clipboard_text[:-1]

                    # add the text to the real clipboard
                    window.clipboard_append(clipboard_text)

                    # if we're cutting, delete the selection
                    if special_key == 'cmd' and e.keysym == 'x':

                        # but simply call this same function, while triggering the DELETE key
                        e.keysym = 'Delete'
                        cls.on_edit_press(e, window, toolkit_UI_obj, special_key='')

                return 'break'

            # SELECT ALL
            elif special_key == 'cmd' and e.keysym.lower() == 'a':
                pass

            # UNDO
            elif special_key == 'cmd' and not e.state & 0x1 and e.keysym.lower() == 'z':
                cls.recall_undo_redo(window, toolkit_UI_obj, undo=True)
                return 'break'

            # REDO
            elif special_key == 'cmd' and e.state & 0x1 and e.keysym.lower() == 'z':
                cls.recall_undo_redo(window, toolkit_UI_obj, undo=False)
                return 'break'

            # FIND
            elif special_key == 'cmd' and e.keysym.lower() == 'f':
                pass

            # SAVE
            elif special_key == 'cmd' and e.keysym.lower() == 's':
                # save the story
                cls.save_story(window_id=window.window_id, toolkit_UI_obj=toolkit_UI_obj, sec=0)
                return 'break'

            # PASTE
            elif special_key == 'cmd' and e.keysym.lower() == 'v':

                delete_active_selection()

                # make sure we know where the cursor is
                line, char, end_char = cls.get_current_line_char(window.text_widget)

                # move the index on the current line
                story_line_index = int(line) - 1

                cls.paste_to_story_editor(window=window, toolkit_UI_obj=toolkit_UI_obj, line=line, char=char)
                return 'break'

            # DEL, BACKSPACE
            # if we have an active selection and the user pressed the delete, backspace key
            elif (e.keysym == 'BackSpace' or e.keysym == 'Delete') \
                    and window.text_widget.tag_ranges('sel'):

                # get the start and end of the selection
                selection_start = window.text_widget.index('sel.first')
                selection_end = window.text_widget.index('sel.last')

                # we must remove the lines from the list since it's going to be removed from the text widget
                # get the start and end line numbers
                start_line = int(selection_start.split('.')[0])
                end_line = int(selection_end.split('.')[0])

                # get the start and end char numbers
                start_char = int(selection_start.split('.')[1])
                end_char = int(selection_end.split('.')[1])

                # make sure that the end_line also exists in the story lines list
                # - if the user also selected the very last line of the text index (end-1c)
                #   then the end_line will be one line after the last line in the story lines list
                #   (due to how tkinter text widget works)
                #   so we need to make sure that the end_line is not greater than the number of lines in the story
                if end_line > len(window.story_lines):
                    end_line = len(window.story_lines)

                    # and set the character to the last character in the line
                    end_char = window.text_widget.index('{}.end'.format(end_line)).split('.')[1]

                # are the first or the last lines text lines?
                first_line_is_text = \
                    'type' not in window.story_lines[start_line-1] \
                    or window.story_lines[start_line-1]['type'] == 'text'

                last_line_is_text = \
                    'type' not in window.story_lines[end_line-1] \
                    or window.story_lines[end_line-1]['type'] == 'text'

                # get the text of the first line until the start char
                first_line_text \
                    = window.text_widget.get('{}.0'.format(start_line), '{}.{}'.format(start_line, start_char))

                # get the text of the last line, from the end char until the end of the line
                last_line_text \
                    = window.text_widget.get('{}.{}'.format(end_line, end_char), '{}.end'.format(end_line))

                cls.add_undo_step(window)
                cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)
                window.text_widget.edit_modified(True)

                # delete the lines from the story lines list
                for c_line in range(start_line, end_line+1):

                    # we're not using the c_line variable here because the line numbers decrease after each deletion
                    cls.del_line(window=window, line_index=int(start_line)-1)

                # decide what to leave on the remaining line
                new_line_text = None
                insert_cursor_char = 0
                if first_line_is_text:
                    new_line_text = first_line_text
                    insert_cursor_char = len(first_line_text)

                if last_line_is_text and new_line_text is not None:
                    new_line_text += last_line_text

                elif last_line_is_text:
                    new_line_text = last_line_text

                if new_line_text is not None:
                    cls.add_line(window=window, line_index=start_line-2,
                                 line_data=new_line_text, toolkit_UI_obj=toolkit_UI_obj)

                # update the text widget
                cls.update_text_widget(window_id=window, toolkit_UI_obj=toolkit_UI_obj)

                # take the cursor to the beginning of the first line
                window.text_widget.mark_set('insert', '{}.{}'.format(start_line, insert_cursor_char))

                if not cls.is_line_in_view(window.text_widget, line_no=int(start_line)):
                    window.text_widget.see('insert')

                return 'break'

            # if the user pressed the backspace key
            # and we're at the beginning of the line and the line is not the first line
            elif e.keysym == 'BackSpace' and char == '0' and line != '1':

                # if the previous line is not a text line, just delete the line and move the cursor up
                if window.story_lines[story_line_index - 1]['type'] != 'text':

                    # but only delete if the current line is empty
                    if window.story_lines[story_line_index]['text'] == '':

                        cls.add_undo_step(window)
                        cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)

                        # delete the current line from the story lines list
                        cls.del_line(window=window, line_index=story_line_index)

                        # delete the current line from the text widget
                        window.text_widget.delete('{}.0'.format(int(line)), '{}.end+1c'.format(int(line)))

                    # move the cursor to the end of the previous line
                    window.text_widget.mark_set('insert', '{}.end'.format(int(line) - 1))

                    return 'break'

                # if this line is a text line merge it with the previous line
                if window.story_lines[story_line_index]['type'] == 'text':

                    # get the text of the previous line
                    previous_line_text = \
                        window.text_widget.get('{}.0'.format(int(line) - 1), '{}.end'.format(int(line) - 1))

                    # get the text of the current line
                    current_line_text = \
                        window.text_widget.get('{}.0'.format(line), '{}.end'.format(line))

                    # merge the two lines
                    new_line_text = previous_line_text + current_line_text

                    cls.add_undo_step(window)
                    cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)
                    window.text_widget.edit_modified(True)

                    # delete the current line from the story lines list
                    cls.del_line(window=window, line_index=story_line_index)

                    # set the previous line text
                    cls.set_line(
                        window=window, line_index=story_line_index - 1,
                        line_data=new_line_text, toolkit_UI_obj=toolkit_UI_obj
                    )

                    return

                # if this is not a text line
                else:
                    # just move to the last character of the previous line
                    insert_position = '{}.end'.format(int(line) - 1)
                    window.text_widget.mark_set('insert', insert_position)

                    if not cls.is_line_in_view(window.text_widget, line_no=int(line)-1):
                        window.text_widget.see('insert')

                    return 'break'

            # if the user pressed the delete key
            # and we're at the end of the line and the line is not the last line
            elif e.keysym == 'Delete' and char == end_char and line != window.text_widget.index('end').split('.')[0]:

                # if the next line is not a text line, delete this current line
                if window.story_lines[story_line_index + 1]['type'] != 'text':

                    # but only delete if the current line is empty
                    if window.story_lines[story_line_index]['text'] == '':

                        cls.add_undo_step(window)
                        cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)

                        # delete the current line from the story lines list
                        cls.del_line(window=window, line_index=story_line_index)

                        # delete the current line from the text widget
                        window.text_widget.delete('{}.0'.format(int(line)), '{}.end+1c'.format(int(line)))

                    # move the cursor to the beginning of the next line
                    window.text_widget.mark_set('insert', '{}.0'.format(int(line) + 1))

                    return 'break'

                # move the cursor to the beginning of the next line
                # window.text_widget.mark_set('insert', '{}.end'.format(int(line) + 1))

                # if this line is a text line merge it with the next line
                if window.story_lines[story_line_index]['type'] == 'text':

                    # get the text of the next line
                    next_line_text = \
                        window.text_widget.get('{}.0'.format(int(line) + 1), '{}.end'.format(int(line) + 1))

                    # get the text of the current line
                    current_line_text = \
                        window.text_widget.get('{}.0'.format(line), '{}.end'.format(line))

                    # merge the two lines
                    new_line_text = current_line_text + next_line_text

                    cls.add_undo_step(window)
                    cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)
                    window.text_widget.edit_modified(True)

                    # delete the next line from the story lines list
                    cls.del_line(window=window, line_index=story_line_index + 1)

                    # set the current line text
                    cls.set_line(
                        window=window, line_index=story_line_index,
                        line_data=new_line_text, toolkit_UI_obj=toolkit_UI_obj
                    )

                    return

                # otherwise just take the cursor to the beginning of the next line
                else:
                    # just move to the last character of the previous line
                    insert_position = '{}.0'.format(int(line) + 1)
                    window.text_widget.mark_set('insert', insert_position)

                    if not cls.is_line_in_view(window.text_widget, line_no=int(line)+1):
                        window.text_widget.see('insert')

                    return 'break'

            elif e.keysym == 'Return':

                delete_active_selection()

                # make sure we know where the cursor is
                line, char, end_char = cls.get_current_line_char(window.text_widget)

                # move the index on the current line
                story_line_index = int(line) - 1

                # if this is a text line
                if window.story_lines[story_line_index]['type'] == 'text':
                    # get the text that we're going to move to the next line
                    new_line_text = window.text_widget.get('{}.{}'.format(line, char), '{}.end'.format(line))

                    # what's the text that will stay on this line?
                    remaining_line_text = window.text_widget.get('{}.0'.format(line), '{}.{}'.format(line, char))

                    # delete the text that we're going to move to the next line from the current line
                    window.text_widget.delete('{}.{}'.format(line, char), '{}.end'.format(line))

                    # add a new line
                    window.text_widget.insert('{}.{}'.format(line, char), '\n')

                    # add the new line text to the next line in the text widget
                    window.text_widget.insert('{}.0'.format(int(line) + 1), new_line_text)

                    # take the cursor to the beginning of the next line
                    window.text_widget.mark_set('insert', '{}.0'.format(int(line) + 1))

                    cls.add_undo_step(window)
                    cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)
                    window.text_widget.edit_modified(True)

                    # now deal with the two lines in the story lines list
                    cls.set_line(
                        window=window, line_index=story_line_index, line_data=remaining_line_text,
                        toolkit_UI_obj=toolkit_UI_obj)

                    # add a new line to the story lines list
                    cls.add_line(
                        window=window, line_index=story_line_index, line_data=new_line_text,
                        toolkit_UI_obj=toolkit_UI_obj)

                    if not cls.is_line_in_view(window.text_widget, line_no=int(line)+1):
                        window.text_widget.see('insert')

                # if this is not a text line
                else:

                    # insert a new line in the text widget to trigger the creation of a new line
                    window.text_widget.insert('{}.end'.format(line, char), '\n')

                    # then move the cursor to the new line
                    window.text_widget.mark_set('insert', '{}.0'.format(int(line) + 1))

                    # see the cursor if it's not in view
                    if not cls.is_line_in_view(window.text_widget, line_no=int(line)+1):
                        window.text_widget.see('insert')

                    # add the new line to the story lines list
                    cls.add_line(window=window, line_index=story_line_index,
                                 line_data='', toolkit_UI_obj=toolkit_UI_obj)

                    return 'break'

                return 'break'

            # for navigation keys, just do whatever tkinter does
            elif e.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Prior', 'Next']:
                return

            # DEL and BACKSPACE for non-text lines
            elif 'type' in window.story_lines[story_line_index] \
                and window.story_lines[story_line_index]['type'] != 'text' \
                and e.keysym in ['BackSpace', 'Delete']:

                # add an undo step
                cls.add_undo_step(window)
                cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)

                # delete the line
                cls.del_line(window=window, line_index=story_line_index)

                # update the text widget
                cls.update_text_widget(window_id=window, toolkit_UI_obj=toolkit_UI_obj)

                # go to the previous line
                insert_line = int(line)
                if e.keysym == 'BackSpace' and int(line) > 1:
                    window.text_widget.mark_set('insert', '{}.0'.format(insert_line))

                # stay on this line
                elif e.keysym == 'Delete' and line != window.text_widget.index('end').split('.')[0]:
                    insert_line = int(line)
                    window.text_widget.mark_set('insert', '{}.0'.format(insert_line))

                # go to the previous line
                elif e.keysym == 'Delete' and line == window.text_widget.index('end').split('.')[0]:
                    window.text_widget.mark_set('insert', '{}.end'.format(insert_line))

                # stay on this line
                elif e.keysym == 'BackSpace' and int(line) == 1:
                    insert_line = int(line)
                    window.text_widget.mark_set('insert', '{}.0'.format(insert_line))

                # see the cursor
                if not cls.is_line_in_view(window.text_widget, line_no=insert_line):
                    window.text_widget.see('insert')

                return 'break'

            # block any other key presses if we're not on a text line
            elif 'type' in window.story_lines[story_line_index] \
                and window.story_lines[story_line_index]['type'] != 'text':
                logger.debug('Blocked key press on non-text line')
                return 'break'

            # if the user pressed a key that represents a character
            elif e.char:

                delete_active_selection()

                # make sure we know where the cursor is
                line, char, end_char = cls.get_current_line_char(window.text_widget)

                # move the index on the current line
                story_line_index = int(line) - 1

                # if this is a text line
                if window.story_lines[story_line_index]['type'] == 'text':

                    # add the new character to the text widget
                    window.text_widget.insert('{}.{}'.format(line, char), e.char)

                    # get the text of the line from the window
                    line_text = window.text_widget.get('{}.0'.format(line), '{}.end'.format(line))

                    cls.add_undo_step(window)
                    cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)
                    window.text_widget.edit_modified(True)

                    cls.set_line(
                        window=window, line_index=story_line_index, line_data=line_text, toolkit_UI_obj=toolkit_UI_obj)

                    # if the line is not in view, show it
                    if not cls.is_line_in_view(window.text_widget, line_no=int(line)):
                        window.text_widget.see('insert')

                    return 'break'

                # if this is not a text line
                else:

                    # insert a new line in the text widget to trigger the creation of a new line
                    window.text_widget.insert('{}.end'.format(line, char), '\n')

                    # then move the cursor to the new line
                    window.text_widget.mark_set('insert', '{}.0'.format(int(line) + 1))

                    # if the line is not in view, show it
                    if not cls.is_line_in_view(window.text_widget, line_no=int(line) + 1):
                        window.text_widget.see('insert')

                    cls.add_undo_step(window)
                    cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)

                    # add the new line to the story lines list
                    cls.add_line(window=window, line_index=story_line_index,
                                 line_data='', toolkit_UI_obj=toolkit_UI_obj)

                    # and then trigger the on_edit_press function again
                    cls.on_edit_press(e, window=window, toolkit_UI_obj=toolkit_UI_obj)

                    return 'break'

            # if we reached this point, we need to make sure that whatever action happens once we exit this function
            # is reflected in the story lines list
            # but since we have no way of knowing what the action will be since tkinter doesn't tell us here,
            # we just start a timer that will update the story lines list

            def update_story_lines_list():

                # get the text of the line from the window
                line_text = window.text_widget.get('{}.0'.format(line), '{}.end'.format(line))

                # update the story lines list
                cls.set_line(
                    window=window, line_index=story_line_index, line_data=line_text, toolkit_UI_obj=toolkit_UI_obj)

            # start the timer
            window.after(20, update_story_lines_list)

        @classmethod
        def is_line_in_view(cls, text_widget, line_no):

            # get the top and bottom lines in view
            top_line, bottom_line = cls.lines_in_view(text_widget)

            # if the line is in view, return True
            if int(top_line) <= int(line_no) <= int(bottom_line):
                return True

            return False

        @staticmethod
        def lines_in_view(text_widget):
            # yview returns a tuple (start, end)
            start, end = text_widget.yview()

            # get the total number of lines
            total_lines = int(text_widget.index('end').split('.')[0])

            # calculate line numbers from start and end using total_lines
            top_line = int(round(start * total_lines)) + 1

            # end * total_lines could be in between a line (a float number). We
            # use math.ceil to always round up to the nearest integer to make sure
            # the last visible line is included.
            bottom_line = int(end * total_lines)

            return top_line, bottom_line

        @classmethod
        def paste_to_story_editor(cls, window, toolkit_UI_obj, line=None, char=None, lines_to_paste=None):

            # print('passed line, char', line, char)

            # throttle the paste event to 100ms to avoid colliding with another paste event
            time.sleep(0.1)

            # if we don't have lines_to_paste to paste that were sent in the function call
            # use the clipboard (real + story_list_clipboard)
            if lines_to_paste is None:

                # this is the text from the real clipboard
                pasted_text = window.clipboard_get()

                # if the pasted text is empty, stop
                if not pasted_text:
                    return 'break'

                # add an undo step
                cls.add_undo_step(window)
                cls.label_to_not_saved(window, toolkit_UI_obj=toolkit_UI_obj)

                pasted_lines = pasted_text.split('\n')

                # if we have an active selection, remove it to make room for the pasted text
                if window.text_widget.tag_ranges('sel'):

                    # get whatever status the text widget is in
                    text_widget_state = window.text_widget.cget('state')

                    # enable editing
                    window.text_widget.config(state=ctk.NORMAL)

                    # simulate pressing the delete key
                    window.text_widget.event_generate('<Delete>')

                    # restore the text widget state
                    window.text_widget.config(state=text_widget_state)

                # if the window doesn't have a story_list_clipboard, create it
                if not hasattr(window, 'story_list_clipboard'):
                    window.story_list_clipboard = []

                # we need to compare the story_list_clipboard with the text we have in the real clipboard
                # since we will eventually use the story_list_clipboard to paste the text and build the story lines list
                for pasted_line_index, pasted_line in enumerate(pasted_lines):

                    # if the story_list_clipboard at this index doesn't exist
                    if len(window.story_list_clipboard) <= pasted_line_index:
                        window.story_list_clipboard.append({'text': pasted_line, 'type': 'text'})

                    # if the text of don't match, update the story_list_clipboard
                    elif 'text' not in window.story_list_clipboard[pasted_line_index] \
                        or window.story_list_clipboard[pasted_line_index]['text'] != pasted_line:

                        window.story_list_clipboard[pasted_line_index]['text'] = pasted_line
                        window.story_list_clipboard[pasted_line_index]['type'] = 'text'

                # if for some reason our story_list_clipboard is empty, stop
                if len(window.story_list_clipboard) == 0:
                    logger.debug('Nothing to paste - story_list_clipboard is empty')
                    return 'break'

                # remove all other lines from the story_list_clipboard that are beyond the length of the pasted lines
                window.story_list_clipboard = window.story_list_clipboard[:len(pasted_lines)]

                # use this variable to paste the lines into the story editor
                lines_to_paste = window.story_list_clipboard

            if not isinstance(lines_to_paste, list):
                logger.error('Unable to paste to story editor - lines_to_paste is not a list')
                return None

            # now deal with the actual PASTING in both the text widget and the window.story_lines list

            # memorize the insert char so we can go to it after pasting
            insert_char = len(lines_to_paste[-1]['text'])

            # get the text widget state so we can restore it after updating the text widget
            text_widget_state = window.text_widget.cget('state')

            # enable editing
            window.text_widget.config(state=ctk.NORMAL)

            # get the current line and char
            # todo: implement the line, char attributes above
            line, char, _ = cls.get_current_line_char(window.text_widget)
            # print('line, char here', line, char)

            # how many lines does the tkinter text widget have?
            # we always subtract 1 because tkinter adds an extra line at the end
            # text_widget_line_count = int(window.text_widget.index('end').split('.')[0])-1

            # we will use these to add text to the lines we're pasting if we're pasting into a text line
            first_line_text_part = ''
            last_line_text_part = ''
            paste_into_text_line = False

            # if the current line in the story editor window is a text line
            # we will need to eventually split it in two
            current_line = cls.get_line(window, line_index=int(line)-1)

            # is the current line a text line?
            if 'type' not in current_line or current_line['type'] == 'text':
                first_line_text_part = current_line['text'][:int(char)]
                last_line_text_part = current_line['text'][int(char):]
                paste_into_text_line = True
                insert_line_add = 1
            else:
                insert_line_add = 1

            paste_into_line_index = current_line_index = int(line) - 1
            remove_first_line_index = None
            for list_clipboard_line_index, list_clipboard_story_line in enumerate(lines_to_paste):

                current_line_index = paste_into_line_index + list_clipboard_line_index

                # if this is the first line we're pasting
                # and if we pasted into a text line and what we're pasting is also a text line
                if list_clipboard_line_index == 0 \
                    and paste_into_text_line and list_clipboard_story_line['type'] == 'text':

                    # add the first part of the current line to the pasted line
                    list_clipboard_story_line['text'] = first_line_text_part + list_clipboard_story_line['text']

                    # we need to remove the first line only after the entire process is finished
                    # to avoid messing up the line indexes count in this loop
                    remove_first_line_index = current_line_index

                # if this is the last line we're pasting
                # and if we pasted into a text line and what we're pasting is also a text line
                elif list_clipboard_line_index == len(lines_to_paste) - 1 \
                    and paste_into_text_line and list_clipboard_story_line['type'] == 'text':

                    # add the last part of the current line to the pasted line
                    list_clipboard_story_line['text'] = list_clipboard_story_line['text'] + last_line_text_part

                    # reset the last_line_text_part
                    last_line_text_part = ''

                # add the line to the story lines list
                cls.add_line(line_index=current_line_index, line_data=list_clipboard_story_line,
                             toolkit_UI_obj=toolkit_UI_obj, window=window)

            # if we still have a last_line_text_part after pasting, we need to add it to the next line
            if last_line_text_part != '':
                current_line_index += 1

                cls.add_line(line_index=current_line_index, line_data={'text': last_line_text_part, 'type': 'text'},
                             toolkit_UI_obj=toolkit_UI_obj, window=window)

            # remove the remove_first_line_index if it exists
            if remove_first_line_index is not None:
                cls.del_line(window=window, line_index=remove_first_line_index)

            # re-generate the text widget
            cls.update_text_widget(window_id=window, toolkit_UI_obj=toolkit_UI_obj)

            # go to the line at the end of the pasted text
            window.text_widget.mark_set('insert', '{}.{}'.format(current_line_index + 1 + insert_line_add, insert_char))

            # see the cursor if it's not in view
            if not cls.is_line_in_view(window.text_widget, line_no=current_line_index + 1 + insert_line_add):
                window.text_widget.see('insert')

            # revert the text widget state to whatever it was before
            window.text_widget.config(state=text_widget_state)

            return 'break'

        @staticmethod
        def get_line(window, line_index: int):
            """
            This gets a line from the story lines list (not from the text widget)
            :param window: the window object
            :param line_index: the index of the line to get (0-based, -1 from the text widget line number!)
            """

            if not hasattr(window, 'story_lines'):
                logger.error('Cannot get line. No story lines attached to window.')
                return None

            # make sure the line index is within the story lines range
            # allow minus values to get the last lines
            if line_index >= len(window.story_lines) or line_index < -len(window.story_lines):
                return None

            # get the story line from the window
            return window.story_lines[line_index]

        @staticmethod
        def del_line(window, line_index: int) -> dict or None:
            """
            This deletes a line from the story lines list and returns the deleted line
            :param window: the window object
            :param line_index: the index of the line to delete (0-based, -1 from the text widget line number!)
            """

            # does the window have a story line list?
            if not hasattr(window, 'story_lines'):
                logger.error('Cannot delete line - no story lines list attached to window.')
                return None

            # make sure the line index is within the story lines range
            # allow minus values to get the last lines
            if -len(window.story_lines) < int(line_index) < len(window.story_lines):

                # clear the modified flag
                window.text_widget.edit_modified(False)

                return window.story_lines.pop(line_index)

        @staticmethod
        def set_line(window, line_index: int, line_data: dict or str, toolkit_UI_obj):
            """
            This sets a line in the story lines list (not in the text widget)
            :param window: the window object
            :param line_index: the index of the line to set (0-based, -1 from the text widget line number!)
            :param line_data: the line data to set (if it's just a string, we'll assume it's the line text)
            :param toolkit_UI_obj: the toolkit UI object
            """

            # does the window have a story line list?
            if not hasattr(window, 'story_lines'):
                logger.error('Cannot set line. No story lines list attached to window.')
                return None

            # does the line index exist?
            if line_index != 0 and line_index >= len(window.story_lines):
                logger.error('Cannot set line. Line index {} does not exist.'.format(line_index))
                return None

            # allow the first line to be set even if the story lines list is empty
            elif line_index == 0 and len(window.story_lines) == 0:
                window.story_lines.append({'text': ''})

            # if the line data is a string, and the story_line type is text,
            # only modify the line text
            if isinstance(line_data, str) \
                and ('type' not in window.story_lines[line_index] or window.story_lines[line_index]['type'] == 'text'):
                window.story_lines[line_index]['text'] = line_data
                window.story_lines[line_index]['type'] = 'text'

            elif isinstance(line_data, str) \
                    and 'type' in window.story_lines[line_index] \
                    and window.story_lines[line_index]['type'] != 'text':
                logger.error('Cannot set non-text line only by text. You must update using the source.')
                return

            # otherwise, replace the line dict with the new line data
            else:
                window.story_lines[line_index] = line_data

            # if the line doesn't contain a type, make it a text line
            if 'type' not in window.story_lines[line_index]:
                window.story_lines[line_index]['type'] = 'text'

            # clear the modified flag
            window.text_widget.edit_modified(False)

        @classmethod
        def add_line(cls, window, line_index: int, line_data: dict or str, toolkit_UI_obj):
            """
            This adds a line to the story lines list (not in the text widget)
            :param window: the window object
            :param line_index: the index of the line to add (0-based, -1 from the text widget line number!)
            :param line_data: the line data to add (if it's just a string, we'll assume it's the line text)
            :param toolkit_UI_obj: the toolkit UI object
            """

            # does the window have a story line list?
            if not hasattr(window, 'story_lines'):
                logger.error('Cannot set line. No story lines list attached to window.')
                return None

            # add an empty list element at the line index
            window.story_lines.insert(line_index+1, {'text': ''})

            # then set the line data
            cls.set_line(
               window=window, line_index=line_index+1, line_data=line_data, toolkit_UI_obj=toolkit_UI_obj)

            # clear the modified flag
            window.text_widget.edit_modified(False)

        @staticmethod
        def get_current_line_char(text_widget):

            # get the position of the cursor on the text widget
            line_no, insert_char = text_widget.index(ctk.INSERT).split('.')

            # get the index of the last character of the text widget line where the cursor is
            _, end_char = text_widget.index("{}.end".format(line_no)).split('.')

            return line_no, insert_char, end_char

        @classmethod
        def story_editor_context_menu(cls, e, window_id, toolkit_UI_obj):

            window = toolkit_UI_obj.get_window_by_id(window_id)

            # line, char, end_char = cls.get_current_line_char(window.text_widget)

            # get the line and char at click event
            line, char = window.text_widget.index("@{},{}".format(e.x, e.y)).split('.')

            clicked_story_line = cls.get_line(window=window, line_index=int(line)-1)

            # spawn the context menu
            context_menu = tk.Menu(window.text_widget, tearoff=0)

            # add the menu items

            # COPY + PASTE
            if window.text_widget.tag_ranges("sel") or window.clipboard_get():
                # show COPY if there is a selection
                if window.text_widget.tag_ranges("sel"):
                    context_menu.add_command(
                        label="Copy", command=lambda: window.text_widget.event_generate("<<Copy>>"))

                # show PASTE if there is something in the clipboard
                if window.clipboard_get():
                   context_menu.add_command(
                       label="Paste",
                       command=lambda: cls.paste_to_story_editor(
                           window=window, toolkit_UI_obj=toolkit_UI_obj, line=line, char=char)
                   )

                # add a separator
                context_menu.add_separator()

            # transcription stuff
            if 'type' in clicked_story_line and clicked_story_line['type'] == 'transcription_segment'\
                and 'transcription_file_path' in clicked_story_line:

                # add a separator
                context_menu.add_separator()

                # open transcription window at segment

                transcription = Transcription(clicked_story_line['transcription_file_path'])

                context_menu.add_command(
                    label=transcription.name,
                    state=tk.DISABLED
                )

                # use timecode if available
                timecode_data = transcription.get_timecode_data()

                if timecode_data is not False and timecode_data is not (None, None):
                    segment_start = transcription.seconds_to_timecode(
                        seconds=clicked_story_line['source_start'], fps=timecode_data[0], start_tc_offset=timecode_data[1])

                    segment_end = transcription.seconds_to_timecode(
                        seconds=clicked_story_line['source_end'], fps=timecode_data[0], start_tc_offset=timecode_data[1])

                    segment_info = "{} to {}".format(segment_start, segment_end)

                    if toolkit_UI_obj.stAI.debug_mode:
                        segment_info += "\n{:.4f} to {:.4f}"\
                            .format(clicked_story_line['source_start'], clicked_story_line['source_end'])

                else:
                    segment_start = clicked_story_line['source_start']
                    segment_end = clicked_story_line['source_end']

                    # add the segment info as a disabled menu item
                    if toolkit_UI_obj.stAI.debug_mode:
                        segment_info = "{:.4f} to {:.4f}"\
                            .format(clicked_story_line['source_start'], clicked_story_line['source_end'])
                    else:
                        segment_info = "{:.2f} to {:.2f}".format(segment_start, segment_end)

                # open transcription window at segment
                context_menu.add_command(
                    label=segment_info,
                    command=lambda: toolkit_UI_obj.open_transcription_window(
                        transcription_file_path=clicked_story_line['transcription_file_path'],
                        goto_time=clicked_story_line['source_start'],
                    )
                )


            # display the context menu
            context_menu.tk_popup(e.x_root, e.y_root)

            return

        @classmethod
        def check_timecode_data(cls, window_id, toolkit_UI_obj, add_timecode_data=False, lookup_source_media=False):
            """
            This takes each line that has a transcription as a source and updates the timecode data in the story lines.
            If the transcription doesn't have timecode data, the user will be asked to add it
            if add_timecode_data is True.
            """

            # get the window to get the window.story
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # we're using this list to keep track of the transcriptions we've already asked the user about
            asked_timecode_data = []

            logger.debug('Checking timecode data for story lines of {}.'.format(window.story.name))

            story_timecodes_changed = False

            not_found_source_media = []

            # loop through the story lines
            for line in window.story_lines:

                source_transcription_file_path = line.get('transcription_file_path', None)

                if source_transcription_file_path and source_transcription_file_path in asked_timecode_data:
                    continue

                if line.get('type', None) != 'transcription_segment' and line.get('type', None) != 'video_segment':
                    continue

                # open the source transcription for this line
                source_transcription = Transcription(source_transcription_file_path)

                if not source_transcription:
                    # notify user
                    toolkit_UI_obj.notify_via_messagebox(
                        title='Transcription {} not found'
                            .format(os.path.basename(source_transcription_file_path)),
                        message="Transcription {} not found.\n"
                                "We need access to the transcription file to retrieve the timecode data."
                            .format(os.path.basename(source_transcription_file_path)),
                        message_log="Unable to check timecode data - transcription not found: {} "
                            .format(source_transcription_file_path),
                        parent=window,
                        type='warning'
                    )

                    # don't mention this transcription again
                    asked_timecode_data.append(source_transcription_file_path)

                    continue

                timecode_data = source_transcription.get_timecode_data()

                # if the transcription doesn't have timecode data, ask the user to edit it
                # but only if we're supposed to add_timecode_data
                if add_timecode_data and (not timecode_data or timecode_data == (None, None)) \
                        and source_transcription_file_path not in asked_timecode_data:

                    timecode_data = toolkit_UI_obj.t_edit_obj.ask_for_transcription_timecode_data(
                        window_id=window_id,
                        transcription=source_transcription,
                        default_start_tc='01:00:00:00'
                    )

                    # if the user pressed cancel for this transcription, don't show the message again
                    if not timecode_data or timecode_data == (None, None):

                        # notify user
                        toolkit_UI_obj.notify_via_messagebox(
                            title='Timeline timecode info not available'
                            .format(os.path.basename(source_transcription_file_path)),
                            message="Timeline timecode info not available for {}.\n\n"
                                    "The lines related to this transcription will be skipped on story export "
                                    "if they don't contain the timecode data."
                            .format(os.path.basename(source_transcription_file_path)),
                            message_log="Timecode data not available for: {} "
                            .format(source_transcription_file_path),
                            parent=window,
                            type='warning'
                        )

                        # don't ask again
                        asked_timecode_data.append(source_transcription_file_path)

                # if we received useful timecode_data
                # let's see if we have to update the line timecode data
                if timecode_data is not None or timecode_data != (None, None):

                    # update the timecode data in the story lines if its different compared to the source
                    if line.get('source_fps', None) != timecode_data[0] and timecode_data[0] is not None:
                        story_timecodes_changed = True
                        line['source_fps'] = timecode_data[0]

                    if line.get('source_start_tc', None) != timecode_data[1] and timecode_data[1] is not None:
                        story_timecodes_changed = True
                        line['source_start_tc'] = timecode_data[1]

                if lookup_source_media and source_transcription.audio_file_path not in not_found_source_media:

                    if not source_transcription.audio_file_path:

                        # notify user
                        toolkit_UI_obj.notify_via_messagebox(
                            title='Source media unknown',
                            message="Source media not known for transcription {}.\n\n"
                                    "Some export features might not work correctly without "
                                    "knowing the source media file."
                            .format(source_transcription.transcription_file_path),
                            message_log="Source media not found for transcription: {} ",
                            parent=window,
                            type='warning'
                        )

                        not_found_source_media.append(source_transcription_file_path)

                    elif not os.path.isfile(source_transcription.audio_file_path):

                        # notify user
                        toolkit_UI_obj.notify_via_messagebox(
                            title='Source media not found',
                            message="Source media {} not found.\n\n"
                                    "Some export features might not work correctly without "
                                    "knowing the source media file.".format(source_transcription.audio_file_path),
                            message_log="Source media {} not found for transcription {}"
                                .format(source_transcription.transcription_file_path,
                                        source_transcription.audio_file_path),
                            parent=window,
                            type='warning'
                        )

                        not_found_source_media.append(source_transcription_file_path)


            if story_timecodes_changed:
                # save the story function (this will also copy window.story_lines to window.story.lines)
                cls.save_story(window_id=window_id, toolkit_UI_obj=toolkit_UI_obj, sec=0)

        @classmethod
        def button_export_as_text(cls, window_id, export_file_path=None, toolkit_UI_obj=None):
            """
            Exports the story as a text file (.txt or .fountain)
            """

            # get the window story
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # first make sure that the story is saved
            # - this should also update the story lines list in the object
            cls.save_story(window_id=window_id, toolkit_UI_obj=toolkit_UI_obj, sec=0)

            # wait a moment
            time.sleep(0.1)

            # get the story file path from the window
            story_file_path = window.story.story_file_path

            # if we still don't have a story file path, return
            if story_file_path is None:
                logger.debug('No story file path found.')
                return False

            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(title='Save Story as Text or Fountain',
                                                                initialdir=os.path.dirname(story_file_path),
                                                                initialfile=os.path.basename(story_file_path)
                                                                .replace('.story.json', '.txt'),
                                                                filetypes=[('TXT files', '*.txt'),
                                                                           ('Fountain files', '*.fountain')
                                                                           ],
                                                                defaultextension='.txt')

                # if the user pressed cancel, return
                if export_file_path is None or export_file_path == '':
                    logger.debug('User canceled save as TXT.')
                    return False

            # write the TXT file
            if window.story.lines is not None \
                    or window.story.lines != [] \
                    or len(window.story) > 0:

                # write the TXT file
                StoryUtils.write_txt(
                    story_lines=window.story.lines, txt_file_path=export_file_path)

                # notify the user
                toolkit_UI_obj.notify_via_messagebox(title='Text file export',
                                                          message='The text file was exported successfully.',
                                                          type='info'
                                                          )

                # focus back on the window
                toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                toolkit_UI_obj.notify_via_messagebox(title='No story data',
                                                          message='No story data was found.',
                                                          type='warning'
                                                          )

                # focus back on the window
                toolkit_UI_obj.focus_window(window_id)

                return False

        @classmethod
        def prepare_export_as_timeline(cls, window_id, toolkit_UI_obj=None, export_file_path=None):
            """
            Prepares the story for export as timeline (EDL, FCP7XML etc.)
            """

            # get the window story
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # first make sure that the story is saved
            # - this should also update the story lines list in the object
            cls.save_story(window_id=window_id, toolkit_UI_obj=toolkit_UI_obj, sec=0)

            # wait a moment
            time.sleep(0.1)

            # get the story file path from the window
            story_file_path = window.story.story_file_path

            # if we still don't have a story file path, return
            if story_file_path is None:
                logger.debug('No story file path found.')
                return False

            # LINES TIMECODE DATA
            cls.check_timecode_data(
                window_id,
                toolkit_UI_obj=toolkit_UI_obj,
                add_timecode_data=True,
                lookup_source_media=True
            )

            # EDL EXPORT SETTINGS
            # create a list of widgets for the input dialogue
            input_widgets = [
                {'name': 'timeline_name', 'label': 'Name:', 'type': 'entry',
                 'default_value': window.story.name},
                {'name': 'timeline_start_tc', 'label': 'Start Timecode:', 'type': 'entry',
                 'default_value': '01:00:00:00'},
                {'name': 'timeline_fps', 'label': 'Frame Rate:', 'type': 'entry',
                 'default_value': 24},
                {'name': 'use_timelines', 'label': 'Use Timelines:', 'type': 'switch',
                 'default_value': False},
                {'name': 'export_notes', 'label': 'Export Notes:', 'type': 'switch',
                 'default_value': True},
                {'name': 'join_gaps', 'label': 'Join Gaps Shorter Than:', 'type': 'entry_int',
                 'default_value': 0, 'unit': 'frames'}
            ]

            timeline_name = None
            timeline_fps = None
            timeline_start_tc = None
            use_timelines = None
            export_notes = None
            join_gaps = None

            # loop this until we get something useful
            while timeline_start_tc is None or timeline_fps is None:

                try:
                    # then we call the ask_dialogue function
                    user_input = toolkit_UI_obj.AskDialog(title='Timeline Export Settings',
                                                          input_widgets=input_widgets,
                                                          parent=window,
                                                          cancel_return=None,
                                                          toolkit_UI_obj=toolkit_UI_obj
                                                          ).value()

                    # if the user clicked cancel, stop the loop
                    if user_input is None:
                        return False
                except:
                    logger.error('Error while asking for timecode data.', exc_info=True)
                    return False

                # validate the user input
                try:

                    # try to see if the timecode is valid
                    start_tc = Timecode(
                        user_input['timeline_fps'],
                        user_input['timeline_start_tc'] if user_input['timeline_start_tc'] != '00:00:00:00' else None)

                    # if we reached this point, take the values
                    timeline_name = user_input['timeline_name']
                    timeline_fps = user_input['timeline_fps']
                    timeline_start_tc = user_input['timeline_start_tc']
                    use_timelines = user_input['use_timelines']
                    export_notes = user_input['export_notes']
                    join_gaps = user_input['join_gaps']

                    # and break from the loop
                    break

                except:

                    logger.warning('Invalid Timecode or Frame Rate: {} @ {}'
                                   .format(user_input['timeline_start_tc'], user_input['timeline_fps']),
                                   exc_info=True
                                   )

                    # notify user
                    toolkit_UI_obj.notify_via_messagebox(title='Timecode or Frame Rate error',
                                                         message="The Start Timecode or Frame Rate "
                                                                 "you entered is invalid. Please try again.",
                                                         message_log="Invalid Timecode or Frame Rate.",
                                                         parent=window,
                                                         type='warning')

            # THE SAVE PATH
            # if we don't have a save file path, ask the user for it
            if export_file_path is None:
                # ask the user where to save the file
                export_file_path = filedialog.asksaveasfilename(
                    title='Save as Text',
                    initialdir=os.path.dirname(story_file_path),
                    initialfile= \
                        timeline_name if timeline_name else (
                            os.path.basename(story_file_path).replace('.story.json', '.edl')),
                    filetypes=[('EDL files', '*.edl'), ('FCP7 XML files', '*.xml')],
                    defaultextension='.xml')

                # if the user pressed cancel, return
                if not export_file_path:
                    logger.debug('User canceled save as EDL.')
                    return False

            return timeline_name, timeline_fps, timeline_start_tc, use_timelines, export_notes, export_file_path, join_gaps

        @classmethod
        def button_export_as_timeline(cls, window_id, export_file_path=None, toolkit_UI_obj=None):
            """
            This is a wrapper for the EDL and FCP7XML export functions which decides which one to call
            depending on the file extension that the user selected
            """

            timeline_name, timeline_fps, timeline_start_tc, use_timelines, export_notes, export_file_path, join_gaps \
                = cls.prepare_export_as_timeline(
                    window_id, toolkit_UI_obj=toolkit_UI_obj, export_file_path=export_file_path)

            # get the extension of the export file path
            export_file_path_extension = os.path.splitext(export_file_path)[1]

            # get the window story
            window = toolkit_UI_obj.get_window_by_id(window_id)

            # EXPORTING
            # write the file
            if window.story.lines is not None \
                    or window.story.lines != [] \
                    or len(window.story) > 0:

                # if the extension is .xml, call the FCP7XML export function
                if export_file_path_extension == '.xml':
                    export_result = StoryUtils.write_fcp7xml(
                        story_name=window.story.name if not timeline_name else timeline_name,
                        story_lines=window.story.lines,
                        xml_file_path=export_file_path,
                        edit_timeline_fps=timeline_fps, edit_timeline_start_tc=timeline_start_tc,
                        use_timelines=use_timelines, export_notes=export_notes, join_gaps=join_gaps)

                # otherwise, call the EDL export function
                else:
                    export_result = StoryUtils.write_edl(
                        story_name=window.story.name if not timeline_name else timeline_name,
                        story_lines=window.story.lines,
                        edl_file_path=export_file_path,
                        edit_timeline_fps=timeline_fps, edit_timeline_start_tc=timeline_start_tc,
                        use_timelines=use_timelines, export_notes=export_notes, join_gaps=join_gaps)

                if export_result:
                    # notify the user
                    toolkit_UI_obj.notify_via_messagebox(title='File export',
                                                         message="The file {} was exported successfully."
                                                         .format(os.path.basename(export_file_path)),
                                                         type='info'
                                                         )

                # focus back on the window
                toolkit_UI_obj.focus_window(window_id)

                return True

            else:
                # notify the user
                toolkit_UI_obj.notify_via_messagebox(title='No story data',
                                                     message='No story data was found.',
                                                     type='warning'
                                                     )

                # focus back on the window
                toolkit_UI_obj.focus_window(window_id)

                return False

    def open_new_story_editor_window(self):
        """
        This makes the user choose a file path for the new story and then opens a new story editor window
        """

        # ask the user where to save the story
        story_file_path = self.ask_for_save_file(
            title='New Story',
            filetypes=[('Story files', '.sts')]
        )

        # if the user didn't choose a file path, stop
        if not story_file_path:
            return False

        # remove the file if it already exists
        if os.path.exists(story_file_path):

            # just remove it (the OS should have asked for confirmation already)
            os.remove(story_file_path)

        # and add an empty line to it to make sure that it passes the story file validation
        story = Story(story_file_path=story_file_path)

        story.add_line({'text': '', 'type': 'text'})
        story.set('name', os.path.basename(story_file_path).split('.')[0])
        story.save_soon(backup=False, force=True, sec=0)

        time.sleep(0.1)

        # open the story editor window and return it
        return self.open_story_editor_window(story_file_path=story_file_path)

    def open_story_editor_window(self, title=None, story_file_path=None):

        if story_file_path is None:

            # ask the user which story file to open
            story_file_path = filedialog.askopenfilename(
                initialdir=self.stAI.initial_target_dir,
                title='Open Story',
                filetypes=[('Story files', '.sts')]
            )

            if not story_file_path:
                return False

            self.stAI.update_initial_target_dir(os.path.dirname(story_file_path))

        story = Story(story_file_path=story_file_path)

        if not story.exists:
            self.notify_via_messagebox(
                title='Not found',
                type='error',
                message='The story file {} cannot be found.'
                .format(story.story_file_path)
            )
            return False

        if not story.is_story_file:
            self.notify_via_messagebox(
                title='Invalid Story file',
                type='error',
                message='The file {} is not a valid story file.'
                .format(story.story_file_path)
            )
            return False

        # use the story path id for the window id
        window_id = "story_editor_{}".format(story_file_path)

        title = title if title else (story.name if story.name else 'Story Editor')

        if self.create_or_open_window(
                parent_element=self.root, window_id=window_id, title=title, resizable=True,
                close_action=lambda l_window_id=window_id: self.destroy_story_editor_window(l_window_id),
                type="story_editor", has_menubar=True):

            # get the window
            window = self.get_window_by_id(window_id)

            # attach the story object to the window
            window.story = story

            # the story lines list will be used to store the story lines
            # and we initialize them with whatever is in the story object
            window.story_lines = story.to_dict().get('lines', [])

            # some attributes we'll use later
            window.typing = False
            window.edited = False

            # UI stuff

            # create the left frame
            window.left_frame = ctk.CTkFrame(window, name='left_frame', **self.ctk_frame_transparent)
            window.left_frame.grid(row=0, column=0, sticky="ns", **self.ctk_side_frame_button_paddings)
            window.left_frame.grid_forget()

            # create the middle frame to hold the text element
            window.middle_frame = ctk.CTkFrame(window, name='middle_frame', **self.ctk_frame_transparent)
            window.middle_frame.grid(row=0, column=1, sticky="nsew")

            # create a frame for the text element inside the middle frame
            window.text_form_frame = ctk.CTkFrame(window.middle_frame, name='text_form_frame',
                                           **self.ctk_frame_transparent)
            window.text_form_frame.grid(row=0, column=0, sticky="nsew")

            # make the text_form_frame expand to fill the middle_frame
            window.middle_frame.grid_rowconfigure(0, weight=1)
            window.middle_frame.grid_columnconfigure(0, weight=1)

            # create the right frame to hold other stuff, like transcript groups etc.
            window.right_frame = ctk.CTkFrame(window, name='right_frame', **self.ctk_frame_transparent)
            window.right_frame.grid(row=0, column=2, sticky="ns", **self.ctk_side_frame_button_paddings)
            window.right_frame.grid_forget()

            # add a footer frame
            window.footer_frame = ctk.CTkFrame(window, name='footer_frame', **self.ctk_frame_transparent)
            window.footer_frame.grid(row=1, column=0, columnspan=3, sticky="ew", **self.ctk_frame_paddings)

            # add a minimum size for the frame2 column
            window.grid_columnconfigure(1, weight=1, minsize=200)

            # Add column and row configuration for resizing
            window.grid_rowconfigure(0, weight=1)

            # initialize the story text element
            window.text_widget = tk.Text(window.text_form_frame,
                               name='story_text',
                               font=self.transcript_font,
                               width=45, height=30,
                               **self.ctk_full_textbox_paddings,
                               wrap=tk.WORD,
                               background=self.theme_colors['black'],
                               foreground=self.theme_colors['normal'],
                               highlightcolor=self.theme_colors['dark'],
                               highlightbackground=self.theme_colors['dark'],
                               )

            # add a scrollbar to the text element
            text_scrollbar = ctk.CTkScrollbar(window.text_form_frame)
            text_scrollbar.configure(command=window.text_widget.yview)
            text_scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y, pady=5)

            # configure the text element to use the scrollbar
            window.text_widget.config(yscrollcommand=text_scrollbar.set)

            # update the text widget with the story lines
            toolkit_UI.StoryEdit.update_text_widget(
                window_id=window, toolkit_UI_obj=self, story_lines=window.story_lines)

            # disable the text widget and set its width to 50 characters
            window.text_widget.config(state=ctk.DISABLED, width=50)

            # set the top, in-between and bottom text spacing
            window.text_widget.config(spacing1=0, spacing2=0.2, spacing3=5)

            # then show the text element
            window.text_widget.pack(anchor='w', expand=True, fill='both', **self.ctk_full_textbox_frame_paddings)

            # add a status label to print out current transcription status
            window.status_label = ctk.CTkLabel(window.footer_frame, name='status_label',
                                        text="", anchor='w', **self.ctk_frame_transparent)
            window.status_label.grid(row=0, column=0, sticky='ew', **self.ctk_footer_status_paddings)

            # bind mouse Click to edit story
            window.text_widget.bind(
                "<Button-1>",
                lambda e: toolkit_UI.StoryEdit.edit_story_text(
                    window_id=window_id, toolkit_UI_obj=self)
            )

            # bind CMD/CTRL + e to edit story
            window.bind(
                "<" + self.ctrl_cmd_bind + "-e>",
                lambda e: toolkit_UI.StoryEdit.edit_story_text(
                    window_id=window_id, toolkit_UI_obj=self)
            )

            # bind CMD/CTRL + s to save story
            # this is also binded on the text widget itself
            window.bind(
                "<" + self.ctrl_cmd_bind + "-s>",
                lambda e: toolkit_UI.StoryEdit.save_story(window_id=window_id, toolkit_UI_obj=self, sec=0)
            )

            # if the user presses CTRL/CMD+F, open the find window
            window.bind('<' + self.ctrl_cmd_bind + '-f>',
                                         lambda event:
                                         self.open_find_replace_window(
                                             parent_window_id=window_id,
                                             title="Find in {}".format(title)
                                         )
                                         )

            # let's add the .find attribute to the window, so that the UI_menu can use it
            window.find = lambda: self.open_find_replace_window(
                parent_window_id=window_id,
                title="Find in {}".format(title)
            )

            # add this window to the list of text windows - we need this for the find window
            self.text_windows[window_id] = {'text_widget': window.text_widget}

            # add right click for context menu
            window.text_widget.bind(
                '<Button-3>', lambda e: self.StoryEdit.story_editor_context_menu(
                    e, window_id=window_id, toolkit_UI_obj=self))

            # make context menu work on mac trackpad too
            window.text_widget.bind(
                '<Button-2>', lambda e: self.StoryEdit.story_editor_context_menu(
                    e, window_id=window_id, toolkit_UI_obj=self))

            return window

    def destroy_story_editor_window(self, window_id):
        """
        This function destroys a story editor window
        :param window_id:
        :return:
        """

        # close any find windows
        if 'find_window_id' in self.text_windows[window_id]:
            find_window_id = self.text_windows[window_id]['find_window_id']

            # call the default destroy window function to destroy the find window
            self.destroy_find_replace_window(window_id=find_window_id)

        # clear the text windows dict
        if window_id in self.text_windows:
            del self.text_windows[window_id]

        # call the default destroy window function
        self.destroy_window_(windows_dict=self.windows, window_id=window_id)

    # QUEUE WINDOW

    def on_button_cancel_queue_item(self, queue_id, button_cancel):

        all_queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items()

        # is the queue id in the Queue?
        if queue_id in all_queue_items:

            # ask the user if they're sure they want to cancel the transcription
            if not messagebox.askyesno('Cancel transcription',
                                       'Are you sure you want to cancel this item?'):
                return

            # cancel via toolkit_ops
            self.toolkit_ops_obj.processing_queue.set_to_canceled(queue_id=queue_id)

        # update the queue window
        self.update_queue_window()

    def on_click_queue_item(self, queue_id, button_cancel):
        """
        When the user clicks on a queue item, this will open the transcription window
        """

        # get the queue item
        queue_item = self.toolkit_ops_obj.processing_queue.get_item(queue_id=queue_id)

        # if the status is done
        if queue_item['status'] == 'done':

            # and the type is 'transcription', and we have a transcription_file_path
            if queue_item['item_type'] == 'transcription' and queue_item.get('transcription_file_path', None):

                # open the transcription window
                self.open_transcription_window(transcription_file_path=queue_item['transcription_file_path'])

            elif queue_item['item_type'] == 'search' and queue_item.get('search_file_paths', None):

                self.open_advanced_search_window(search_file_path=queue_item['search_file_paths'])

        else:
            logger.debug('Queue item is not done yet. Status: {}'.format(queue_item['status']))

    def on_button_cancel_queue(self):

        all_queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items()

        if len(all_queue_items) == 0:
            return

        # ask the user if they're sure they want to cancel all transcriptions
        if not messagebox.askyesno('Cancel entire queue',
                                   'Are you sure you want to cancel all the items from queue?'):
            return

        # take each queue item from the queue
        for queue_id in all_queue_items:

            # if the transcription is not already done, canceled or failed
            if all_queue_items[queue_id]['status'] not in ['canceling', 'canceled', 'done', 'failed']:
                # cancel via toolkit_ops
                self.toolkit_ops_obj.processing_queue.set_to_canceled(queue_id=queue_id)

        # update the queue window
        self.update_queue_window()

    def update_queue_window(self, force_redraw=False):

        # get the queue window
        queue_window = self.get_window_by_id('queue')

        # add the last_update attribute to the queue window if it doesn't exist
        if not hasattr(queue_window, 'last_update'):
            queue_window.last_update = time.time()

        elif hasattr(queue_window, 'last_update') and not force_redraw:
            # don't update the queue window if it was updated less than 0.5 seconds ago
            if time.time() - queue_window.last_update < 0.5:
                return

        # load all the queue items
        all_queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items()

        # redraw the queue list if needed
        if force_redraw or \
                not hasattr(queue_window, 'queue_items') \
                or len(queue_window.queue_items) != len(all_queue_items):
            self.draw_queue_list(all_queue_items)

        for row_num, queue_id in enumerate(all_queue_items):

            q_item = all_queue_items[queue_id]

            # the status may contain the progress too
            status_progress = ''
            if q_item.get('progress', '') != '':

                # prevent weirdness with progress values over 100%
                if int(q_item['progress']) > 100:
                    q_item['progress'] = 100

                status_progress = ' (' + str(q_item['progress']) + '%)'

            # update the name label variable which is in the queue window
            if q_item.get('name', '') == '':
                q_item['name'] = 'Unknown'

            queue_window.queue_items[queue_id]['name_var'].set(q_item['name'])

            # update the status label variable which is in the queue window
            if 'status' not in q_item:
                q_item['status'] = ''
            queue_window.queue_items[queue_id]['status_var'].set(q_item['status'] + status_progress)

            # show the cancel button
            # unless the transcription is already done, canceled or failed
            if q_item['status'] not in ['canceling', 'canceled', 'done', 'failed']:

                # show the cancel button
                queue_window.queue_items[queue_id]['button_cancel'] \
                    .grid(row=0, column=2, **self.ctk_list_paddings, sticky='w')

            else:
                # hide the cancel button
                queue_window.queue_items[queue_id]['button_cancel'].grid_forget()

            # show the progress bar
            if 'progress' in q_item and q_item['progress'] and q_item['progress'] != '':

                # the value of the progressbar is between 0 and 1
                progress_bar_val = int(q_item['progress']) / 100

                # update the progress bar
                queue_window.queue_items[queue_id]['progress_bar'].set(progress_bar_val)
                queue_window.queue_items[queue_id]['progress_bar'].grid(row=1, column=0, columnspan=3, sticky='ew',
                                                                        **self.ctk_form_paddings)

            else:
                queue_window.queue_items[queue_id]['progress_bar'].set(0)
                queue_window.queue_items[queue_id]['progress_bar'].grid_forget()

    def draw_queue_list(self, queue_items=None):
        """
        We're using this to (re-)draw the list of items in the Queue window
        """

        queue_items_frame = self.windows['queue'].queue_items_frame

        # this is the queue window
        queue_window = self.windows['queue']

        # get the queue
        if queue_items is None:
            all_queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items()
        else:
            all_queue_items = queue_items

        # reset the queue items dict for this window
        queue_window.queue_items = {}

        # empty queue_items_frame from all widgets
        for widget in queue_items_frame.winfo_children():

            # does the widget still exist
            # - to prevent trying to destroy a widget that was destroyed by another thread
            if widget.winfo_exists():
                widget.destroy()

        # create a new frame to hold the queue items
        # queue_items_frame = queue_window.queue_items_frame = ctk.CTkScrollableFrame(queue_window)

        # if the queue is empty
        if len(all_queue_items) == 0:
            # add a label to the queue window
            ctk.CTkLabel(queue_items_frame, text='The queue is empty').grid(row=0, column=0, sticky='w',
                                                                            **self.ctk_form_paddings)

            # disable the cancel button
            if hasattr(self.windows['queue'], 'button_cancel_all') \
                    and self.windows['queue'].button_cancel_all.grid_info():
                self.windows['queue'].button_cancel_all.configure(state='disabled')

        # if the queue is not empty
        else:
            for row_num, queue_id in enumerate(all_queue_items):

                # create a frame to hold the queue item
                queue_item_frame = ctk.CTkFrame(queue_items_frame, **self.ctk_list_item)

                # add the queue item dict to the queue window
                window_queue_item = queue_window.queue_items[queue_id] = {}

                # add the name label
                window_queue_item['name_var'] = \
                    name_var = ctk.StringVar(queue_window)
                name_label = ctk.CTkLabel(queue_item_frame, textvariable=name_var, anchor='w')

                # expand the name label to fill the space
                queue_item_frame.columnconfigure(0, weight=1)

                # add the status label
                window_queue_item['status_var'] = \
                    status_var = ctk.StringVar(queue_window)
                status_label = ctk.CTkLabel(queue_item_frame, textvariable=status_var)

                # add the progress bar (under both the name and status labels)
                window_queue_item['progress_bar'] = \
                    progress_bar = ctk.CTkProgressBar(queue_item_frame, height=5)

                # add a button to cancel the transcription
                window_queue_item['button_cancel'] = \
                    button_cancel = ctk.CTkButton(queue_item_frame, text='x', width=1)

                # bind the button to the cancel_transcription function
                button_cancel.bind("<Button-1>", lambda e, l_queue_id=queue_id, l_button_cancel=button_cancel:
                self.on_button_cancel_queue_item(l_queue_id, l_button_cancel))

                # add the name and status labels to the queue item frame (but don't add the progress bar yet)
                name_label.grid(row=0, column=0, sticky='w', **self.ctk_form_paddings)
                status_label.grid(row=0, column=1, sticky='e', **self.ctk_form_paddings)

                # add an action to click on the frame
                queue_item_frame.bind("<Button-1>", lambda e, l_queue_id=queue_id:
                self.on_click_queue_item(l_queue_id, queue_item_frame))

                # add an action to click on the label and status
                name_label.bind("<Button-1>", lambda e, l_queue_id=queue_id:
                self.on_click_queue_item(l_queue_id, queue_item_frame))

                status_label.bind("<Button-1>", lambda e, l_queue_id=queue_id:
                self.on_click_queue_item(l_queue_id, queue_item_frame))

                # add the queue item to the queue items frame
                queue_item_frame.grid(row=row_num, column=0, sticky='ew', **self.ctk_form_paddings)

            # enable the cancel button
            if hasattr(self.windows['queue'], 'button_cancel_all'):
                self.windows['queue'].button_cancel_all.configure(state='normal')

        # add the queue items frame to the queue window
        queue_items_frame.grid(row=0, column=0, sticky='nsew')

        # make sure it expands horizontally to fill the window
        queue_items_frame.columnconfigure(0, weight=1)

        # make the window larger if the queue items frame is larger than the window
        queue_window.update_idletasks()

        # get the height of the queue items frame
        queue_items_frame_height = queue_items_frame.winfo_height()

        # get the height of the queue window
        queue_window_height = queue_window.winfo_height()

        # if the queue items frame is larger than the window
        if queue_items_frame_height > queue_window_height:
            # make the window larger
            queue_window.geometry('{}x{}'.format(queue_window.winfo_width(), queue_items_frame_height + 50))

        return

    def open_queue_window(self):

        # create a window for the Queue if one doesn't already exist
        if self.create_or_open_window(parent_element=self.root, type='queue',
                                      window_id='queue', title='Queue', resizable=True):

            queue_window = self.get_window_by_id('queue')

            # add a frame to hold all the queue items
            queue_window.queue_items_frame = \
                queue_items_frame = ctk.CTkScrollableFrame(queue_window)

            # add a frame to hold the footer
            bottom_footer = ctk.CTkFrame(queue_window)

            # the queue items are drawn on update

            # add the bottom footer to the queue window
            bottom_footer.grid(row=1, column=0, sticky='nsew')

            # the column needs to be expanded to fill the window
            queue_window.columnconfigure(0, weight=1)
            queue_window.rowconfigure(0, weight=1)

            # the window must be minimum 600px wide
            queue_window.minsize(600, 0)

            # add a cancel all button in the footer
            queue_window.button_cancel_all = \
                button_cancel_all = ctk.CTkButton(bottom_footer, text='Cancel all')

            button_cancel_all.grid(row=0, column=0, sticky='e', **self.ctk_form_entry_paddings)

            # bind the button to the cancel_all_transcriptions function
            button_cancel_all.bind("<Button-1>", lambda e: self.on_button_cancel_queue())

            # add an observer to the queue window to make sure it gets updated if any item changes
            self.add_observer_to_window(
                window_id='queue',
                action='update_queue_item',
                callback=lambda: self.update_queue_window()
            )

            # add an observer to the queue window to make sure it gets redrawn when the queue changes
            self.add_observer_to_window(
                window_id='queue',
                action='update_queue',
                callback=lambda: self.update_queue_window(force_redraw=True)
            )

            # and then call the update function to fill the window up
            self.update_queue_window()

            # make sure the windows top position is not over the top of the screen it's on
            self._bring_window_inside_screen(queue_window)

            return True

    # ADVANCED SEARCH WINDOW

    def advanced_search_ask_for_paths(self, search_file_path=None,
                                      transcription_window_id=None, select_dir=False, **kwargs):

        # declare the empty list of search file paths
        search_file_paths = []

        # if a transcription window id was passed, get the transcription object from it
        if search_file_path is None and transcription_window_id is not None:

            # get the transcription object, if a transcription window id was passed
            window_transcription = self.t_edit_obj.get_window_transcription(transcription_window_id)

            # and use the transcription file path as the searchable file path
            search_file_path = window_transcription.transcription_file_path

        # if we still don't have a searchable file path (or paths),
        # ask the user to manually select the files
        if search_file_path is None and not search_file_paths:

            # get the initial dir to use in the file dialog
            # depending if we're using the NLE
            if NLE.is_connected():
                initial_dir = self.stAI.get_project_setting(project_name=NLE.current_project,
                                                            setting_key='last_target_dir')

            # if we're not using the NLE, use the last selected dir
            else:
                initial_dir = self.stAI.initial_target_dir

            # if select_dir is true, allow the user to select a directory
            if select_dir:
                # ask the user to select a directory with searchable files
                selected_file_path = filedialog.askdirectory(initialdir=initial_dir,
                                                             title='Select a directory to use in the search')

                # if the user aborted the file selection, return False
                if not selected_file_path:
                    return None

                # update the last selected dir
                if selected_file_path:
                    search_file_paths = selected_file_path
                    self.stAI.update_initial_target_dir(selected_file_path)

            else:
                # ask the user to select the searchable files to use in the search corpus
                selected_file_path \
                    = filedialog.askopenfilenames(initialdir=initial_dir,
                                                  title='Select files to use in the search',
                                                  filetypes=[('Transcription files', '*.json'),
                                                             ('Text files', '*.txt')
                                                             ])

                # if the user aborted the file selection, return False
                if not selected_file_path:
                    return None

                # update the last selected dir
                if selected_file_path:

                    def validate_either(path):
                        return TextSearch.is_file_searchable(path) or VideoSearch.is_file_searchable(path)

                    # turn directories into files and filter out non-searchable files (by extension)
                    search_file_paths = SearchItem.filter_file_paths(
                        search_paths=selected_file_path,
                        file_validator=validate_either
                    )
                    self.stAI.update_initial_target_dir(os.path.dirname(selected_file_path[0]))

            # if resolve is connected, save the last target dir
            if NLE.is_connected() and search_file_paths \
                    and type(search_file_paths) is list and os.path.exists(search_file_paths[0]):
                self.stAI.save_project_setting(project_name=NLE.current_project,
                                               setting_key='last_target_dir',
                                               setting_value=os.path.dirname(search_file_paths[0]))

        # but if the call included a search file path, format it as a list if it isn't already
        elif search_file_path is not None:
            search_file_paths = search_file_path if isinstance(search_file_path, list) else [search_file_path]

        return search_file_paths

    def open_advanced_search_window(self, transcription_window_id=None, search_file_path=None,
                                    select_dir=False, **kwargs):

        if self.toolkit_ops_obj is None or self.toolkit_ops_obj.t_search_obj is None:
            logger.error('Cannot open advanced search window. A ToolkitSearch object is needed to continue.')
            return False

        # get the transcription object, if a transcription window id was passed
        window_transcription = self.t_edit_obj.get_window_transcription(transcription_window_id)

        # process the selected paths and return only the files that are valid
        # this works for both a single file path and a directory (depending what the user selected above)
        # search_file_paths = search_item.process_file_paths(selected_file_path)

        # process the search file paths or ask the user to select them
        search_file_paths = self.advanced_search_ask_for_paths(
            search_file_path=search_file_path,
            transcription_window_id=transcription_window_id,
            select_dir=select_dir
        )

        # abort if we don't have any search file paths (but don't show the message if the user aborted - none)
        if search_file_paths is not None and not search_file_paths:
           self.notify_via_messagebox(
               type='info', message='No valid files found for search.', parent=self.get_window_by_id('main'))
           return None

        if not search_file_paths:
            return None

        # if the call included a transcription window
        # init the search window id, the title and the parent element
        if window_transcription is not None and window_transcription.exists \
                and transcription_window_id is not None and search_file_path is not None:

            search_window_id = transcription_window_id + '_search'

            # don't open multiple search widows for the same transcription window
            open_multiple = False

            # the transcription_file_paths has only one element
            search_file_paths = [search_file_path]

            # get the parent window
            parent_window = self.get_window_by_id(transcription_window_id)

            # use either the transcription name or the file name for the search window title
            search_window_title_ext = \
                window_transcription.name \
                if window_transcription.name \
                else os.path.basename(search_file_path).split('.transcription.json')[0]

        # if there is no transcription window id or any search_file_path
        else:

            search_window_title_ext = ''

            # if we have a list of one, take the first element
            if search_file_paths and isinstance(search_file_paths, list) and len(search_file_paths) == 1:
                search_file_paths = search_file_paths[0]

            # if the user selected a directory and it exists
            if select_dir and isinstance(search_file_paths, str) \
                    and search_file_paths and os.path.isdir(search_file_paths):

                # use the directory name as the title
                search_window_title_ext = os.path.basename(search_file_paths)

            # if we have a single file, use the file name as the title
            elif search_file_paths and isinstance(search_file_paths, str) \
                    and search_file_paths and os.path.isfile(search_file_paths):

                search_window_title_ext = os.path.basename(search_file_paths)

            # if we have multiple files, use the name of the first file as the title
            elif search_file_paths and (isinstance(search_file_paths, list) or isinstance(search_file_paths, tuple)):

                search_window_title_ext = os.path.basename(search_file_paths[0])

                # if there are multiple files, show that there are others
                if len(search_file_paths) > 1:
                    search_window_title_ext += ' and others'

            search_window_id = 'adv_search_{}'.format(str(time.time()))

            # the parent is in this case the main window
            parent_window = self.root

            # since we're not coming from a transcription window,
            # we can open multiple search windows at the same time
            open_multiple = True

        # format the full search window title
        search_window_title = 'Search{}'.format(' - '+search_window_title_ext if search_window_title_ext else '')

        # we need to filter out the files that are not searchable
        # even if this was done before, just to make sure we're using the same TextSearch object

        # filter the files that are not searchable (by extension) and turn directories into files
        text_search_file_paths = TextSearch.filter_file_paths(search_file_paths)

        # filter the video search file paths
        video_search_file_paths = VideoSearch.filter_file_paths(search_file_paths)

        # use_analyzer
        use_analyzer = self.stAI.get_app_setting('search_preindexing_textanalysis', default_if_none=False)

        # initialize the search item object
        text_search_item = TextSearch(toolkit_ops_obj=self.toolkit_ops_obj, search_file_paths=text_search_file_paths,
                                 search_type='semantic', use_analyzer=use_analyzer)

        video_search_item = VideoSearch(toolkit_ops_obj=self.toolkit_ops_obj, search_file_paths=video_search_file_paths)

        # if this search has a file path id,
        if text_search_item.search_file_path_id is not None:

            # let's use it in the search window's id
            # this will help if we want to avoid re-opening it for the same file paths
            search_window_id = 'adv_search_{}'.format(text_search_item.search_file_path_id)

            open_multiple = False

        # open a new console search window
        search_window_id = self.open_text_window(window_id=search_window_id,
                                                 title=search_window_title,
                                                 can_find=True,
                                                 user_prompt=True,
                                                 close_action=lambda l_search_window_id=search_window_id:
                                                 self.destroy_advanced_search_window(l_search_window_id),
                                                 prompt_prefix='SEARCH > ',
                                                 prompt_callback=self.advanced_search,
                                                 prompt_callback_kwargs={
                                                     'text_search_item': text_search_item,
                                                     'video_search_item': video_search_item,
                                                     'search_window_id': search_window_id},
                                                 type='search',
                                                 open_multiple=open_multiple,
                                                 window_width=60,
                                                 has_menubar=True
                                                 )

        # if the window was not created and is not in the list of windows, throw an error
        if search_window_id and not self.get_window_by_id(search_window_id):
            logger.error('Search window {} was not created.'.format(search_window_id))
            return False

        # if the window was not created, but it's in the list of windows, just return
        # the window will be focused by now and the user will be able to use it
        if not search_window_id:
            return

        help_console_info = "Type [help] to see all available commands.\n\n"

        def ready_for_search():
            """
            This updates the window with the "ready for search" prefix and message
            """

            text_widget = self.get_window_by_id(search_window_id).text_widget

            # get the current prefix
            current_prefix = self.text_windows[search_window_id].get('prompt_prefix', '')

            # calculate the starting index of the last line
            start_of_last_line = text_widget.index('end-1c linestart')

            # get the text on the last line excluding the prefix
            typed_text = text_widget.get(start_of_last_line, 'end-1c')

            # optionally remove the prefix from the typed text (but only the first instance)
            typed_text = typed_text.replace(current_prefix, '', 1)

            # change the prefix back to SEARCH
            self._text_window_set_prefix(window_id=search_window_id, prefix='SEARCH > ')

            # update the text window
            self._text_window_update(
                search_window_id, help_console_info + 'Ready for search.', clear=True)

            # insert the typed text back into the text window
            text_widget.insert('end', typed_text)

        # get this window object
        search_window = self.get_window_by_id(search_window_id)

        # change the prefix of the window from SEARCH to nothing until the processing is done
        self._text_window_set_prefix(window_id=search_window_id, prefix=' > ')

        # let the user know that we're now reading the files
        self._text_window_update(
            search_window_id,
            text=help_console_info+'Reading {} {}...'.format(
                text_search_item.search_file_paths_count,
                'file' if text_search_item.search_file_paths_count == 1 else 'files'),
            clear=True
        )

        # TEXT SEARCH
        # check if we have text files to search, otherwise this is video search only and we can skip this
        if text_search_file_paths:
            def process_text_items(thread):
                """
                This processes the indexing for this search window, either directly in a thread or through the queue.
                """

                # the preparation of the search corpus needs to happen before sending the search item to the queue
                # this is the only way to find out if we have a cache or not
                # but it also means that we're taking it through TextAnalysis which might be slow...
                text_search_item.prepare_search_corpus()

                queue_items = self.toolkit_ops_obj.processing_queue.get_all_queue_items()

                in_queue = False
                # look through all the queue items and see if the search_file_paths match
                for q_item_id, q_item in queue_items.items():

                    # if the queue item is a search item
                    if q_item.get('item_type', None) == 'search' \
                            and q_item.get('search_file_paths', None) == text_search_file_paths:

                        # if the item is done, let the user know that he can search
                        if q_item['status'] == 'done':
                            ready_for_search()

                            # we're saying it is in the queue, just to avoid re-processing it
                            in_queue = True
                            break

                        # if the item is still processing, let the user know that he has to wait
                        elif q_item['status'] not in ['failed', 'canceled', 'canceling']:
                            self._text_window_update(
                                window_id=search_window_id,
                                text=help_console_info + 'Waiting for queue to finish processing...', clear=True)
                            in_queue = True
                            break

                        # for any other status (failed, canceled, canceling), we can say it's not in the queue
                        else:
                            in_queue = False
                            break

                # if the search_file_paths_size is larger than 300kb and doesn't have a cache
                if not in_queue \
                        and text_search_item.search_file_paths_size > 300000 \
                        and not text_search_item.cache_exists:

                    # add the search item to the queue
                    queue_id = self.toolkit_ops_obj.add_index_text_to_queue(
                        queue_item_name='Indexing text of {}'.format(search_window_title_ext),
                        search_file_paths=text_search_file_paths)

                    self._text_window_update(
                        search_window_id, help_console_info+'Sent processing job to the queue...', clear=True)

                    if queue_id:

                        # add the queue id as a processing item to the window
                        #  - this will be removed when the observer is notified at the end of the processing
                        self.add_window_processing(window_id=search_window_id, processing_item=queue_id)

                        def window_indexing_done():
                            """
                            We use this as a callback to update the text window when the done indexing observer is notified
                            """

                            # remove the processing queue item from the window
                            self.remove_window_processing(window_id=search_window_id, processing_item=queue_id)

                            # if the window is no longer processing anything, we can update the text window
                            if not self.is_window_processing(window_id=search_window_id):
                                ready_for_search()

                        def window_indexing_failed():
                            """
                            We use this as a callback to update the text window
                            when the failed indexing observer is notified
                            """

                            self.notify_via_messagebox(
                                message="The indexing was either canceled or it failed for this search. \n"
                                        "Please re-open this window if you want to try again."
                                .format(search_window_title),
                                type='error',
                                parent=search_window,
                                message_log="Indexing failed for search window {}.".format(search_window_title)
                            )

                            # close this window
                            self.destroy_advanced_search_window(search_window_id)

                        # add window observer to track when the queue is done processing
                        self.add_observer_to_window(
                            window_id=search_window_id,
                            action='update_done_indexing_search_file_path_{}'
                            .format(text_search_item.search_file_path_id),
                            callback=window_indexing_done,
                            dettach_after_call=True
                        )

                        # add window observer to track when the queue failed/canceled processing
                        self.add_observer_to_window(
                            window_id=search_window_id,
                            action='update_fail_indexing_search_file_path_{}'
                            .format(text_search_item.search_file_path_id),
                            callback=window_indexing_failed,
                            dettach_after_call=True
                        )

                        # open the queue window
                        self.open_queue_window()

                        # check if the processing isn't already done by the time we reach this
                        # - sometimes the queue is so fast that we miss the observer notification
                        queue_item = self.toolkit_ops_obj.processing_queue.get_item(queue_id)
                        if queue_item['status'] == 'done':
                            window_indexing_done()

                # if the total file size is smaller than 150kb, process it now
                elif not in_queue:

                    self._text_window_update(
                        search_window_id, help_console_info+'Processing for a moment...', clear=True)

                    # use the toolkit method of indexing text
                    self.toolkit_ops_obj.index_text(search_file_paths=text_search_file_paths)

                # when this is done, remove the processing text item from the window
                self.remove_window_processing(window_id=search_window_id, processing_item=thread)

                # if the window is no longer processing anything, we're ready for search
                if not self.is_window_processing(window_id=search_window_id):
                    ready_for_search()

            # create a new thread to prevent locking the window
            processing_thread = Thread(target=lambda: process_text_items(processing_thread))
            # start the thread
            processing_thread.start()

            # add the processing item to the window so it "knows" that it's processing something
            self.add_window_processing(window_id=search_window_id, processing_item=processing_thread)

        # VIDEO SEARCH
        if video_search_file_paths and video_search_item.search_file_paths:

            def process_video_items(thread):

                self._text_window_update(
                    search_window_id, help_console_info+'Processing for a moment...', clear=True)

                # load the video search
                video_search_item.load_index_paths()

                self._text_window_update(
                    search_window_id, help_console_info+'Loading video search...', clear=True)

                # load the clip model
                video_search_item.load_model()

                # when this is done, remove the processing text item from the window
                self.remove_window_processing(window_id=search_window_id, processing_item=thread)

                # if the window is no longer processing anything, we're ready for search
                if not self.is_window_processing(window_id=search_window_id):
                    ready_for_search()

            # create a new thread to prevent locking the window
            processing_video_thread = Thread(target=lambda: process_video_items(processing_video_thread))
            # start the thread
            processing_video_thread.start()

            # add the processing item to the window so it "knows" that it's processing something
            self.add_window_processing(window_id=search_window_id, processing_item=processing_video_thread)

        # if the parent of the window is not the main window
        if parent_window != self.root:

            # add this window to the parent window
            parent_window.search_window = search_window

        # add the search item to the search window
        search_window.text_search_item = text_search_item

        # add the button to the left frame of the search window

        # SEARCH BUTTONS
        # self._add_button_to_side_frames_of_window(search_window_id, side='left',
        #                                           button_text='Change model',
        #                                           button_command=
        #                                           lambda search_window_id=search_window_id:
        #                                           self.button_search_change_model(search_window_id),
        #                                           sub_frame="Search")

        self._add_button_to_side_frames_of_window(search_window_id, side='left',
                                                  button_text='List files',
                                                  button_command=
                                                  lambda l_search_window_id=search_window_id:
                                                  self.button_search_list_files(l_search_window_id),
                                                  sub_frame="Search")

        search_window.search_text_switch_var, search_window.search_text_switch_input = \
            self._add_switch_to_side_frames_of_window(search_window_id, side='left',
                                                      label_text='Search text',
                                                      sub_frame="Search")

        if text_search_item.search_file_paths:
            search_window.search_text_switch_var.set(True)
        else:
            search_window.search_text_switch_var.set(False)
            search_window.search_text_switch_input.pack_forget()
            search_window.search_video_switch_input.pack_forget()

        search_window.search_video_switch_var, search_window.search_video_switch_input =\
            self._add_switch_to_side_frames_of_window(search_window_id, side='left',
                                                      label_text='Search video',
                                                      sub_frame="Search")

        if video_search_item.search_file_paths:
            search_window.search_video_switch_var.set(True)
        else:
            search_window.search_video_switch_var.set(False)
            search_window.search_video_switch_input.pack_forget()
            search_window.search_text_switch_input.pack_forget()

        # don't let both be off, so if one gets off, turn the other on
        def switch_search_text():

            if search_window.search_text_switch_var.get() == 0:
                search_window.search_video_switch_var.set(True)

        def switch_search_video():

            if search_window.search_video_switch_var.get() == 0:
                search_window.search_text_switch_var.set(True)

        search_window.search_text_switch_var.trace('w', lambda *args: switch_search_text())
        search_window.search_video_switch_var.trace('w', lambda *args: switch_search_video())

        # SPACY BUTTONS
        # self._add_switch_to_side_frames_of_window(search_window_id, side='left',
        #                                               switch_text='Cluster phrases',
        #                                               switch_command=
        #                                               lambda search_window_id=search_window_id:
        #                                                print(search_window_id),
        #                                               sub_frame="Source Text")

        # TRANSCRIPT RESULTS BUTTONS
        # self._add_button_to_side_frames_of_window(search_window_id, side='left',
        #                                               button_text='Show results',
        #                                               button_command=button_no_command,
        #                                               sub_frame="Results")

        # self._add_button_to_side_frames_of_window(search_window_id, side='left',
        #                                               button_text='Select results',
        #                                               button_command=button_no_command,
        #                                               sub_frame="Results")

        # self._add_button_to_side_frames_of_window(search_window_id, side='left',
        #                                               button_text='Select group results',
        #                                               button_command=button_no_command,
        #                                               sub_frame="Results")

        # add text to the search window
        # self._text_window_update(search_window_id, 'Reading {} file{}.'
        #                         .format(len(search_file_paths), 's' if len(search_file_paths) > 1 else ''))

        # now prepare the search corpus
        # (everything happens within the search item, that's why we don't really need to return anything)
        # if the search corpus was prepared successfully, update the search window

        self._text_window_update(search_window_id, help_console_info)

        # if the window is still processing, show this:
        if self.is_window_processing(search_window_id):
            self._text_window_update(search_window_id, 'Processing search files. Please wait...')

        # focus in the text widget after 110 ms
        search_window.after(110, lambda: self.text_windows[search_window_id]['text_widget'].focus_set())

    def is_window_processing(self, window_id: str):
        """
        This checks if a window has any processing items
        """

        if window_id not in self.windows:
            return False

        if not hasattr(self.windows[window_id], 'processing'):
            return False

        # if the window has processing items, return them
        # otherwise return False
        return self.windows[window_id].processing if len(self.windows[window_id].processing) > 0 else False

    def add_window_processing(self, window_id: str, processing_item: int or Thread):
        """
        This sets the processing list of a window
        """

        if window_id not in self.windows:
            return False

        # append the processing item to the list of processing items
        # but first create the list if it doesn't exist
        if not hasattr(self.windows[window_id], 'processing'):
            self.windows[window_id].processing = []

        self.windows[window_id].processing.append(processing_item)

    def remove_window_processing(self, window_id: str, processing_item: int or Thread):
        """
        This removes an item from the list of processing items
        """

        if window_id not in self.windows:
            return False

        # if the window doesn't have a processing list, return False
        if not hasattr(self.windows[window_id], 'processing'):
            return False

        # if the processing item is not in the list, return False
        if processing_item not in self.windows[window_id].processing:
            return False

        # remove the processing item from the list
        self.windows[window_id].processing.remove(processing_item)

        return True

    def _advanced_search_list_files_in_window(self, search_window_id: str, search_item=None, clear=False):
        """
        This function lists the files that are loaded for search in the search window.
        """

        # load the search item using the window id if it wasn't passed
        if search_item is None:
            search_item = self.windows[search_window_id].search_item

        search_file_list = ''

        # prepare a list with all the files
        for search_file_path in search_item.search_file_paths:
            search_file_list = search_file_list + os.path.basename(search_file_path) + '\n'

        search_file_list = search_file_list.strip()
        self._text_window_update(search_window_id, 'Looking into {} {} for this search:'
                                 .format(len(search_item.search_file_paths),
                                         'file' if len(search_item.search_file_paths) == 1 else 'files'), clear=clear)

        self._text_window_update(search_window_id, search_file_list)

    def advanced_search(self, prompt, text_search_item=None, video_search_item=None, search_window_id=None):
        """
        This is the callback function for the advanced search window.
        It calls the search function of the search item and passes the prompt as the search query.
        Then it updates the search window with the results.
        """

        # the window object
        search_window = self.get_window_by_id(search_window_id)

        if search_window is None:
            logger.error('Cannot search - the search window is not defined.')
            return False

        # are we supposed to clear the window before each reply?
        clear_before_reply = self.stAI.get_app_setting('search_clear_before_results', default_if_none=True)

        # is the user asking for help?
        if prompt.lower() == '[help]':

            help_reply = 'Simply enter a search term and press enter.\n' \
                         'For eg.: about life events\n\n' \
                         'If you want to restrict the number of results, ' \
                         'just add [n] to the beginning of the query.\n' \
                         'For eg.: [10] about life events\n\n' \
                         'If you want to perform multiple searches in the same time, ' \
                         'use the | character to split the search terms\n' \
                         'For eg.: about life events | about family\n\n' \
                         'If you want to change the model, use [model:<model_name>]\n' \
                         'For eg.: [model:distiluse-base-multilingual-cased-v1]\n\n' \
                         'See list of models here: https://www.sbert.net/docs/pretrained_models.html\n'

            # use this to make sure we have a new prompt prefix for the next search
            self._text_window_update(search_window_id, help_reply, clear=clear_before_reply)
            return

        # if the user sent either [model] or [model:<model_name>] as the prompt
        elif prompt.lower().startswith('[model') and prompt.lower().endswith(']'):

            # if the model contains a colon, it means that the user wants to load a new model
            if prompt.lower() != '[model]' and ':' in prompt.lower():

                # if a model was passed (eg.: [model:en_core_web_sm]), load it
                # using regex to extract the model name
                model_name = re.search(r'\[model:(.*?)\]', prompt.lower()).group(1)

                if model_name.strip() != '':

                    # let the user know that we are loading the model
                    self._text_window_update(
                        search_window_id, 'Loading model {}...'.format(model_name), clear=clear_before_reply)

                    # load the model
                    try:
                        text_search_item.load_model(model_name=model_name)
                    except:
                        self._text_window_update(search_window_id, 'Could not load model {}.'.format(model_name))
                        return

            if text_search_item.model_name:
                self._text_window_update(
                    search_window_id, 'Using model {}'.format(text_search_item.model_name), clear=clear_before_reply)
            else:
                self._text_window_update(
                    search_window_id,
                    'No model loaded.\n'
                    'Perform a search first to load the default model.\n'
                    'Or load a model with the [model:<model_name>] command and it will be used '
                    'for all the searches in this window.',
                    clear=clear_before_reply
                )
            return

        # this clears the search window
        elif prompt.lower() == '[clear]':
            self._text_window_update(search_window_id, '', clear=clear_before_reply)
            return

        elif prompt.lower() == '[listfiles]' or prompt.lower() == '[list files]':
            self._advanced_search_list_files_in_window(search_window_id, text_search_item, clear=clear_before_reply)
            return

        # is the user trying to quit?
        elif prompt.lower() == '[quit]':
            self.destroy_advanced_search_window(search_window_id)
            return

        # if we reached this point, we're sending the prompt to the search item
        # but first, we need to make sure that the window is not processing
        # if it is, we need to wait for it to finish
        if self.is_window_processing(search_window_id):

            # let the user know that the window is processing
            self._text_window_update(
                window_id=search_window_id,
                text="Cannot search yet - we're processing the search files. Try again later."
            )
            return

        # perform the text search if the user sent a text search item
        # and if the search_window.search_text_switch_var exists and is set to True
        if text_search_item is not None and hasattr(search_window, 'search_text_switch_var') \
                and search_window.search_text_switch_var.get() is True:

            self.advanced_search_text(
                text_search_item=text_search_item, search_window_id=search_window_id, prompt=prompt,
                clear_before_reply=clear_before_reply)

            # set this to false so that the video search doesn't clear the window
            clear_before_reply = False

        else:
            text_search_item = None

        if video_search_item and hasattr(search_window, 'search_video_switch_var') \
                and search_window.search_video_switch_var.get() is True:

            # add some space between the text and video results
            # if text_search_item is not None:

            #     # get the search window text element
            #     results_text_element = self.text_windows[search_window_id]['text_widget']

            #     # add a new line to separate the text and video results
            #     results_text_element.insert(ctk.END, "\n")

            self.advanced_search_video(
                video_search_item=video_search_item, search_window_id=search_window_id, prompt=prompt,
                clear_before_reply=clear_before_reply)

        else:
            video_search_item = None

        # use this to make sure we have a new prompt prefix for the next search
        if text_search_item is not None or video_search_item is not None:
            self._text_window_update(search_window_id, 'Ready for new search.', scroll_to='1.1')
        else:

            if search_window.search_video_switch_var.get() is False \
                    and search_window.search_text_switch_var.get() is False:

                self.notify_via_messagebox('warning', message="Both text and video search are disabled.")

            self._text_window_update(search_window_id, 'Ready for new search.', clear=clear_before_reply)

    def _format_time_for_search_results(self, time_in_seconds=None):
        """
        Formats the time in seconds to a human readable format
        """

        return "{:02d}:{:02d}:{:02d}.{:03d}" \
            .format(int(time_in_seconds // 3600),
                    int((time_in_seconds // 60) % 60),
                    int(time_in_seconds % 60),
                    int((time_in_seconds % 1) * 1000)
                    )

    def advanced_search_text(self, text_search_item, search_window_id, prompt, clear_before_reply=True):

        # keep track of when we started the search
        start_search_time = time.time()

        search_results, max_results = text_search_item.search(query=prompt)

        # get the search window text element
        results_text_element = self.text_windows[search_window_id]['text_widget']

        # how long did the search take?
        # total_search_time = time.time() - start_search_time

        # clear the search window if we're supposed to
        if clear_before_reply:
            self._text_window_update(search_window_id, '', clear=clear_before_reply)

            # but add back the search term before the results
            results_text_element.insert(ctk.END, prompt + "\n\n")

        # now add the search results to the search results window
        if len(search_results) > 0:

            # add text to the search window
            # self._text_window_update(search_window_id + '_B', 'Searched in files...')

            # reset the previous search_term
            result_search_term = ''

            # keep track of scores to calculate the average later
            scores = []

            for result in search_results:

                # if we've changed the search term, add a new header
                if result['search_term'] != result_search_term:
                    result_search_term = result['search_term']

                    # add the search term header
                    # if we haven't cleared the previous results,
                    # we need to somehow mark the beginning of the new results, so that they're easier to spot
                    #if not clear_before_reply:
                    #    results_text_element.insert(ctk.END, 'Searching for: "' + result_search_term + '"\n')
                    #    results_text_element.insert(ctk.END, '--------------------------------------\n')

                    results_text_element.insert(ctk.END, 'Top {} closest phrases:\n\n'.format(max_results))

                # remember the current insert position
                current_insert_position = results_text_element.index(ctk.INSERT)

                # add the result text
                text_result = result['text']

                # replace new lines with spaces
                text_result = text_result.replace('\n', ' ')

                # remove double spaces
                text_result = text_result.replace('  ', ' ')

                # add the result text
                results_text_element.insert(ctk.END, str(text_result).strip() + '\n')

                # color it in blue
                results_text_element.tag_add('white', current_insert_position, ctk.INSERT)
                results_text_element.tag_config('white', foreground=self.theme_colors['supernormal'])

                # if the type is a transcription
                if result['type'] == 'transcription':

                    # time_str = "{:.2f}".format(result['transcript_time']) \
                    #    if result['timecode'] is None else result['timecode']

                    # for the time string, we either use the timecode or the transcript time
                    if result['timecode'] is None:

                        # format the time string to HH:MM:SS.MS
                        time_str = self._format_time_for_search_results(result['transcript_time'])

                    else:
                        time_str = result['timecode']

                    # add the time string to the result text
                    results_text_element.insert(ctk.END, '{} '.format(time_str))

                    # add the transcription file path and segment index to the result
                    results_text_element.insert(ctk.END, '- {} '.format(result['name']))

                    # add a new line
                    results_text_element.insert(ctk.END, '\n')

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, tk.INSERT)

                    # add the tag 'has_context_menu' so that the text window doesn't fire its own context menu
                    results_text_element.tag_add('has_context_menu', current_insert_position, tk.INSERT)

                    # add the transcription file path and segment index to the tag
                    # so we can use it to open the transcription window with the transcription file and jump to the segment
                    results_text_element.tag_bind(tag_name, '<Button-1>',
                                                  lambda event,
                                                         transcription_file_path=result['transcription_file_path'],
                                                         line_no=result['line_no']:
                                                  self.open_transcription_window(
                                                      transcription_file_path=transcription_file_path,
                                                      select_line_no=line_no))

                    # bind mouse clicks press events on the results text box
                    # bind CMD/CTRL + mouse Clicks to text
                    # this adds the clicked line to the existing selection
                    results_text_element.tag_bind(tag_name, "<" + self.ctrl_cmd_bind + "-Button-1>",
                                                  lambda event,
                                                         transcription_file_path=result['transcription_file_path'],
                                                         line_no=result['line_no'],
                                                         all_lines=result['all_lines']:
                                                  self.open_transcription_window(
                                                      transcription_file_path=transcription_file_path,
                                                      select_line_no=line_no,
                                                      add_to_selection=all_lines)
                                                  )

                    # SEARCH RESULT CONTEXT MENU
                    # add right click for context menu
                    # results_text_element.tag_bind(tag_name,
                    #     '<Button-3>', lambda e: self._text_window_context_menu(
                    #         e, window_id=search_window_id))

                    # results_text_element.bindtags((tag_name, str(results_text_element), "Text", "."))

                    segment_indexes = [int(result_line_no) - 1 for result_line_no in result['all_lines']]

                    results_text_element.tag_bind(
                        tag_name,
                        '<Button-3>',
                        lambda e, result_segment_indexes=segment_indexes[:],
                               transcription_file_path=result['transcription_file_path']:
                        self._text_search_result_context_menu(
                            e, segment_indexes=result_segment_indexes,
                            transcription_file_path=transcription_file_path
                        )
                    )

                    results_text_element.tag_bind(
                        tag_name,
                        '<Button-2>',
                        lambda e, result_segment_indexes=segment_indexes[:],
                               transcription_file_path=result['transcription_file_path']:
                        self._text_search_result_context_menu(
                            e, segment_indexes=result_segment_indexes,
                            transcription_file_path=transcription_file_path
                        )
                    )

                # if the type is text
                elif result['type'] == 'text':
                    # add the transcription file path and segment index to the result
                    results_text_element.insert(ctk.END, '{}\n'
                                                .format(os.path.basename(result['file_path'])))

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, ctk.INSERT)

                    # print('tag_name', tag_name, result['idx'])

                    # hash the file path so we can use it as a window id
                    file_path_hash = hashlib.md5(result['file_path'].encode('utf-8')).hexdigest()

                    # get the file basename so we can use it as a window title
                    file_basename = os.path.basename(result['file_path'])

                    # if the user clicks on the result
                    # open the file in the default program (must work for Windows, Mac and Linux)
                    results_text_element.tag_bind(tag_name, '<Button-1>',
                                                  lambda event,
                                                         l_file_path=result['file_path'],
                                                         l_result_text=result['text'],
                                                         l_file_path_hash=file_path_hash,
                                                         l_file_basename=file_basename:
                                                  self.open_text_file(file_path=l_file_path,
                                                                      window_id="text_" + l_file_path_hash,
                                                                      title=l_file_basename,
                                                                      tag_text=l_result_text))

                # if the type is a marker
                elif result['type'] == 'marker':

                    # if we have timecode data for this result
                    if result.get('timeline_fps', None) is not None \
                            and result.get('timeline_start_tc', None) is not None:

                        # convert the marker_index to timecode
                        timecode = Timecode(
                            result['timeline_fps'],
                            frames=int(result['marker_index']) if int(result['marker_index']) != 0 else None
                        )

                        if result['timeline_start_tc'] != '00:00:00:00':

                            try:
                                timecode += Timecode(result['timeline_fps'], result['timeline_start_tc'])

                            except:
                                pass

                        marker_index_or_time_str = str(timecode)

                    else:
                        marker_index_or_time_str = "frame {}".format(result['marker_index'])

                    # add the timeline name
                    results_text_element.insert(
                        ctk.END, 'Marker at {} - {}, project: {}\n'
                        .format(marker_index_or_time_str, result['timeline'], result['project'])
                    )

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, tk.INSERT)

                elif result['type'] == 'transcript_group':

                    # add the timeline name
                    results_text_element.insert(ctk.END, 'Transcript Group - {} \n'.
                                                format(result['transcription_name']))

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, ctk.INSERT)

                    # add the transcription file path and segment index to the tag
                    # so we can use it to open the transcription window with the transcription file and jump to the segment
                    results_text_element.tag_bind(tag_name, '<Button-1>',
                                                  lambda event,
                                                         transcription_file_path=result['file_path'],
                                                         group_name=result['group_name']:
                                                  self.open_transcription_window(
                                                      transcription_file_path=transcription_file_path,
                                                      select_group=group_name))

                else:
                    # mention that the result source is unknown
                    results_text_element.insert(ctk.END, 'source unknown\n')

                    # add a tag to the above text to make it clickable
                    tag_name = 'clickable_{}'.format(result['idx'])
                    results_text_element.tag_add(tag_name, current_insert_position, tk.INSERT)

                # show score if in debug mode
                if self.stAI.debug_mode:

                    # add score to the result
                    # consider the result as low confidence if the score is less than 0.35
                    if result['score'] < 0.35:
                        result_confidence = ' (Low)'
                    elif result['score'] > 0.8:
                        result_confidence = ' (Good)'
                    else:
                        result_confidence = ''

                    results_text_element.insert(
                        ctk.END, ' -- Score: {:.4f}{}\n'.format(result['score'], result_confidence))

                # highlight the tag when the mouse enters the tag
                # (the unhighlight function is called when the mouse leaves the tag)
                results_text_element.tag_bind(tag_name, '<Enter>',
                                              lambda event, l_tag_name=tag_name:
                                              self._highlight_result_tag(
                                                 self.text_windows[search_window_id]['text_widget'], l_tag_name))

                # add a new line
                results_text_element.insert(ctk.END, '\n')

                # add the score to the list of scores
                scores.append(result['score'])

            # calculate the average score
            # average_score = round(sum(scores) / len(scores) * 10, 1)

            # update the results text element
            results_text_element.insert(ctk.END, '--------------------------------------\n\n')
            # results_text_element.insert(ctk.END, 'Search took {:.2f} seconds\n'.format(total_search_time))
            # results_text_element.insert(ctk.END, 'Average results score {:.1f} out of 10\n'.format(average_score))

        else:
            results_text_element.insert(ctk.END, 'No text results found for {}.\n\n'.format(prompt))
            results_text_element.insert(ctk.END, '--------------------------------------\n\n')

    def _text_search_result_context_menu(self, event, segment_indexes, transcription_file_path):

        # get the text widget from the event
        text_widget = event.widget

        # get the line and char from the click
        line, char = self.get_line_char_from_click(event, text_widget=text_widget)
        line = int(line)
        char = int(char)

        # spawn the context menu
        context_menu = tk.Menu(text_widget, tearoff=0)

        # add the menu items
        # if there is a selection
        if text_widget.tag_ranges("sel"):
            context_menu.add_command(label="Copy",
                                     command=lambda: text_widget.event_generate("<<Copy>>"))

            # add the de-select all option
            context_menu.add_command(label="Deselect",
                                     command=lambda: text_widget.tag_remove("sel", "1.0", "end"))

        else:
            # add the select all option
            context_menu.add_command(label="Select All",
                                     command=lambda: text_widget.tag_add("sel", "1.0", "end"))

            # add a separator
            # context_menu.add_separator()

        # add separator
        context_menu.add_separator()

        # the add to story sub-menu
        add_to_story_menu = tk.Menu(context_menu, tearoff=0)

        # the "New Story" button
        add_to_story_menu.add_command(
            label="New Story...",
            command=lambda:
            self.button_add_text_result_to_new_story(
                segment_indexes=segment_indexes, transcription_file_path=transcription_file_path)
        )
        add_to_story_menu.add_separator()

        story_editor_windows = self.get_all_windows_of_type('story_editor')

        for story_editor_window_id in story_editor_windows:
            story_editor_window = self.get_window_by_id(window_id=story_editor_window_id)

            add_to_story_menu.add_command(
                label="{}".format(story_editor_window.title()),
                command=lambda: self.button_add_text_result_to_story(
                    segment_indexes=segment_indexes, transcription_file_path=transcription_file_path,
                    story_editor_window_id=story_editor_window_id)
            )

        # add the add to story sub-menu
        context_menu.add_cascade(label="Add to Story", menu=add_to_story_menu)

        # display the context menu
        context_menu.tk_popup(event.x_root, event.y_root)

    def button_add_text_result_to_new_story(self, segment_indexes, transcription_file_path: str):

        # first open a new story
        if story_editor_window := self.open_new_story_editor_window():
            self.button_add_text_result_to_story(segment_indexes, transcription_file_path, story_editor_window.window_id)

    def button_add_text_result_to_story(self, segment_indexes, transcription_file_path: str, story_editor_window_id: str):

        transcription = Transcription(transcription_file_path)

        new_lines = list()

        for segment_index in segment_indexes:

            segment = transcription.get_segment(segment_index=segment_index)

            new_lines.append({
                'text': segment.text.strip(),
                'type': 'transcription_segment',
                'source_start': segment.start if segment.start is not None else 0.0,
                'source_end': segment.end if segment.end is not None else 0.01,
                'transcription_file_path': transcription.transcription_file_path,
                'source_file_path': transcription.audio_file_path,
                'source_fps': transcription.timeline_fps,
                'source_start_tc': transcription.timeline_start_tc,
            })

        if new_lines:
            story_editor_window = self.get_window_by_id(story_editor_window_id)

            toolkit_UI.StoryEdit.paste_to_story_editor(
                window=story_editor_window, lines_to_paste=new_lines,
                toolkit_UI_obj=self)

            # save the story
            toolkit_UI.StoryEdit.save_story(window_id=story_editor_window, toolkit_UI_obj=self)

        pass


    @staticmethod
    def cv2_image_to_tkinter(parent, cv2_image):

        image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)

        # resize the image proportionally, so that it's maximum 300 pixels wide or 300 pixels high
        # (whichever comes first)
        max_width = 500
        max_height = 300

        # get the image dimensions
        height, width, channels = image.shape

        # if the image is wider than it is high
        if width > height:

            # if the image is wider than the maximum width
            if width > max_width:

                # calculate the ratio of the new width to the old width
                ratio = max_width / width

                # calculate the new height
                new_height = int(height * ratio)

                # resize the image
                image = cv2.resize(image, (max_width, new_height))

        # if the image is higher than it is wide
        else:

            # if the image is higher than the maximum height
            if height > max_height:

                # calculate the ratio of the new height to the old height
                ratio = max_height / height

                # calculate the new width
                new_width = int(width * ratio)

                # resize the image
                image = cv2.resize(image, (new_width, max_height))

        # convert the image to a PIL image
        pil_image = Image.fromarray(image)

        # convert the PIL image to a Tkinter image
        tk_image = ImageTk.PhotoImage(pil_image)

        # save image to parent
        if hasattr(parent, 'temp_images'):
            parent.temp_images.append(tk_image)
        else:
            parent.temp_images = [tk_image]

        return tk_image

    def advanced_search_video(self, video_search_item, search_window_id, prompt, clear_before_reply=True):

        # get the search window
        window = self.get_window_by_id(search_window_id)

        # whether to combine the patches of the same frame if they are similar
        combine_patches = self.stAI.get_app_setting('clip_combine_patches', default_if_none=True)

        # search
        results, max_results = video_search_item.search(prompt, combine_patches=combine_patches)

        if not results:
            return False

        # get the search window text element
        results_text_element = self.text_windows[search_window_id]['text_widget']

        # sort results by score
        results = sorted(results, key=lambda x: x['score'], reverse=True)

        # clear the search window if we're supposed to
        if clear_before_reply:
            self._text_window_update(search_window_id, '', clear=clear_before_reply)

        if len(results) > 0:

            results_text_element.insert(ctk.END, 'Top {} closest frames:\n\n'.format(max_results))

            # take all the results and convert them frames to seconds
            for result in results:

                video_frame = video_search_item.video_frame(result['full_path'], result['frame'])

                tk_image = self.cv2_image_to_tkinter(window, video_frame)

                # add the image to the text element
                results_text_element.image_create(tk.END, image=tk_image)

                # add a new line
                results_text_element.insert(ctk.END, '\n')

                result_fps = result_start_tc = None

                # there are two ways to get the fps and start timecode of the timeline
                # todo: 1. from the transcription data
                #
                # 2. from the actual result, based on what the video index found (but without the start timecode)

                # if we only have fps, we assume the start timecode is 00:00:00:00
                if result.get('video_fps', None) is not None \
                        and result.get('video_start_tc', '00:00:00:00') is not None:

                    result_fps = result.get('video_fps')
                    result_start_tc = result.get('video_start_tc', '00:00:00:00')

                # if we have timecode data for this result
                if result_fps is not None \
                        and result_start_tc is not None:

                    # convert the marker_index to timecode
                    # but only if we're not at frame 0
                    if result['frame'] != 0:
                        timecode = Timecode(result_fps, frames=int(result['frame']))

                    else:
                        timecode = '00:00:00:00'

                    # if the start timecode is not 00:00:00:00 and we're not at frame 0
                    if result_start_tc != '00:00:00:00' and result['frame'] != 0:

                        try:
                            timecode += Timecode(result_fps, result_start_tc)

                        except:
                            pass

                    # if we're at frame 0 and there is a start timecode, use that
                    elif result_start_tc != '00:00:00:00' and result['frame'] == 0:
                        timecode = result_start_tc

                    frame_index_or_time_str = str(timecode)

                else:
                    frame_index_or_time_str = "Frame {}".format(result['frame'])

                # add time code to the video file
                results_text_element.insert(ctk.END, '{} - {}\n'.format(frame_index_or_time_str, result['path']))

                if self.stAI.debug_mode:
                    results_text_element.insert(
                        ctk.END, ' -- Score: {:.4f}\n'.format(result['score']))

                # add a new line
                results_text_element.insert(ctk.END, '\n')

            results_text_element.insert(ctk.END, '--------------------------------------\n\n')

        else:
            results_text_element.insert(ctk.END, 'No video results found for {}.\n\n'.format(prompt))
            results_text_element.insert(ctk.END, '--------------------------------------\n\n')

    def destroy_advanced_search_window(self, window_id: str = None):

        logger.debug('Deleting caches of search window {}'.format(window_id))

        # call the default destroy window function
        self.destroy_text_window(window_id=window_id)

    def _unhighlight_result_tag(self, parent_element, tag_name, initial_background_color=None, initial_cursor=None):

        # revert to the original cursor
        parent_element.config(cursor=initial_cursor)

        # revert to the original background color
        parent_element.tag_config(tag_name, background=initial_background_color)

    def _highlight_result_tag(self, parent_element, tag_name):

        # get the current cursor of the parent element
        current_cursor = parent_element.cget("cursor")

        # get the current background color of the tag
        current_background_color = parent_element.tag_cget(tag_name, "background")

        # show the hand cursor when hovering over the clickable text
        parent_element.config(cursor="hand2")

        #
        parent_element.tag_config(tag_name, background=self.theme_colors['superblack'])

        # add the leave event
        parent_element.tag_bind(tag_name, '<Leave>', lambda event, l_tag_name=tag_name,
                                                            l_initial_background_color=current_background_color,
                                                            l_initial_cursor=current_cursor:
        self._unhighlight_result_tag(parent_element, l_tag_name,
                                     l_initial_background_color, l_initial_cursor)
                                )

    def button_search_list_files(self, search_window_id: str = None):

        if search_window_id not in self.windows:
            logger.error('Cannot list files. The search window ID is not valid.')

        # inject the prompt that lists the files
        self.inject_prompt(search_window_id, '[listfiles]')
        return

    def button_search_change_model(self, search_window_id: str = None):
        """
        This opens up an AskDialog with a list of search models to choose from.
        """

        # get the search item from the search window
        if not self.get_window_by_id(search_window_id):
            logger.error('Cannot change search model. The search window ID is not valid.')
            return False

        search_window = self.get_window_by_id(search_window_id)

        if not hasattr(search_window, 'text_search_item'):
            logger.error('Cannot change search model. The search window does not have a search item.')
            return False

        # get the current model name from the search item
        current_model_name = search_window.text_search_item.model_name

        # create a list of widgets for the input dialogue
        input_widgets = [
            {'name': 'model_name', 'label': 'Model:', 'type': 'entry', 'default_value': current_model_name}
        ]

        # then we call the ask_dialogue function
        user_input = self.AskDialog(title='Change Advanced Search Model',
                                    input_widgets=input_widgets,
                                    parent=search_window,
                                    toolkit_UI_obj=self
                                    ).value()

        if not user_input or 'model_name' not in user_input or not user_input['model_name']:
            return False

        # bring the search window to the front
        search_window.focus_force()

        # and select the text widget
        self.text_windows[search_window_id]['text_widget'].focus_force()

        # inject the prompt that changes the model
        self.inject_prompt(search_window_id, '[model:{}]'.format(user_input['model_name']))

    # THE ASSISTANT WINDOW

    def open_assistant_window(self, assistant_window_id: str = None,
                              transcript_text: str = None,
                              transcription_segments: list = None,
                              ):

        if self.toolkit_ops_obj is None:
            logger.error('Cannot open advanced search window. A ToolkitOps object is needed to continue.')
            return False

        # open a new console assistant window
        # only one assistant window can be open at a time for now, so we'll use a fixed window id
        assistant_window_id = 'assistant'
        assistant_window_title = 'Assistant'

        default_model_provider = self.stAI.get_app_setting('assistant_provider', default_if_none='OpenAI')
        default_model_name = self.stAI.get_app_setting('assistant_model', default_if_none='gpt-3.5-turbo')

        assistant_settings = {
            'system_prompt': self.stAI.get_app_setting(
                'assistant_system_prompt', default_if_none=ASSISTANT_DEFAULT_SYSTEM_MESSAGE),
            "temperature": self.stAI.get_app_setting('assistant_temperature', default_if_none=1),
            "max_length": self.stAI.get_app_setting('assistant_max_length', default_if_none=512),
            "top_p": self.stAI.get_app_setting('assistant_top_p', default_if_none=1),
            "frequency_penalty": self.stAI.get_app_setting('assistant_frequency_penalty', default_if_none=0.0),
            "presence_penalty": self.stAI.get_app_setting('assistant_presence_penalty', default_if_none=0.0)
        }

        # does this window already exist?
        window_existed = False
        if assistant_window_id in self.windows:
            window_existed = True

        # open a new console search window
        self.open_text_window(window_id=assistant_window_id,
                              title=assistant_window_title,
                              can_find=True,
                              user_prompt=True,
                              close_action=lambda l_assistant_window_id=assistant_window_id:
                              self.destroy_assistant_window(l_assistant_window_id),
                              prompt_prefix='U > ',
                              prompt_callback=self.assistant_query,
                              prompt_callback_kwargs={
                                  'assistant_window_id': assistant_window_id
                              },
                              window_width=60,
                              open_multiple=False,
                              type='assistant',
                              has_menubar=True
                              )

        # get this window object
        assistant_window = self.get_window_by_id(assistant_window_id)

        # do this if the window didn't exist before
        if not window_existed:

            # add the context menu
            # add right click for context menu
            assistant_window.text_widget.bind(
                '<Button-3>', lambda e: self._assistant_window_context_menu(
                    e, window_id=assistant_window_id))

            # make context menu work on mac trackpad too
            assistant_window.text_widget.bind(
                '<Button-2>', lambda e: self._assistant_window_context_menu(
                    e, window_id=assistant_window_id))

            # initialize an assistant item if one doesn't already exist
            if not hasattr(assistant_window, 'assistant_item'):
                assistant_window.assistant_item = AssistantUtils.assistant_handler(
                    toolkit_ops_obj=self.toolkit_ops_obj,
                    model_provider=default_model_provider,
                    model_name=default_model_name
                )

            initial_info = 'Using {} ({})\n'.format(
                assistant_window.assistant_item.model_description, assistant_window.assistant_item.model_provider)

            initial_info += 'Your requests might be billed by your AI model provider.\n' + \
                            'Type [help] to see available commands or just ask a question.'

            # also add the assistant settings to the window for future reference
            assistant_window.assistant_settings = assistant_settings

            self._text_window_update(assistant_window_id, initial_info)

        # add the transcript text as context to the assistant
        if transcript_text is not None:
            transcript_text = "TRANSCRIPT\n\n{}\n\nEND".format(transcript_text)
            assistant_window.assistant_item.add_context(context=transcript_text)

            self._text_window_update(assistant_window_id, 'Added items as context.')

        if transcription_segments is not None:
            assistant_window.transcription_segments = transcription_segments

        # focus in the text widget after 110 ms
        assistant_window.after(110, lambda: self.text_windows[assistant_window_id]['text_widget'].focus_set())

    def open_assistant_window_settings(self, assistant_window_id: str = None, **kwargs):
        """
        Open a window with the assistant settings.
        """

        # does the assistant window exist?
        assistant_window = self.get_window_by_id(assistant_window_id)

        if not assistant_window:
            logger.error('Cannot open assistant settings. The "{}" assistant window does not exist.'
                         .format(assistant_window_id))
            return False

        # use the assistant_window_id in the name of the settings window
        settings_window_id = assistant_window_id + '_settings'

        # get the assistant settings from the window
        assistant_settings = assistant_window.assistant_settings

        # add 'assistant_' in front of each setting name
        assistant_settings = {**{'assistant_' + k: v for k, v in assistant_settings.items()}}

        assistant_item = assistant_window.assistant_item

        assistant_settings['assistant_provider'] = assistant_item.model_provider
        assistant_settings['assistant_model'] = assistant_item.model_name

        # create a window if one doesn't already exist
        if settings_window_id := self.create_or_open_window(
                parent_element=assistant_window, window_id=settings_window_id,
                title='Current Assistant Settings', resizable=(False, True),
                type='assistant_window_settings'):

            # get the window
            settings_window = self.get_window_by_id(settings_window_id)

            # UI - create the middle frame
            middle_frame = ctk.CTkScrollableFrame(settings_window, **toolkit_UI.ctk_frame_transparent)

            # UI - create the bottom frame
            bottom_frame = ctk.CTkFrame(settings_window, **toolkit_UI.ctk_frame_transparent)

            # UI - middle and bottom frames
            middle_frame.grid(row=1, column=0, sticky="nsew", **toolkit_UI.ctk_frame_paddings)
            bottom_frame.grid(row=2, column=0, sticky="ew", **toolkit_UI.ctk_frame_paddings)

            # UI - grid configure the middle frame so that it expands with the window
            settings_window.grid_rowconfigure(1, weight=1)

            # UI - the columns should expand with the window
            settings_window.grid_columnconfigure(0, weight=1, minsize=500)

            # UI - set the visibility on the General tab
            middle_frame.columnconfigure(0, weight=1)

            # UI - create another frame for the buttons
            buttons_frame = ctk.CTkFrame(bottom_frame, **toolkit_UI.ctk_frame_transparent)

            # UI - create the start button
            save_button = ctk.CTkButton(buttons_frame, text='Save')

            # UI - create the cancel button
            cancel_button = ctk.CTkButton(buttons_frame, text='Cancel')

            # UI - add the start button, the cancel button
            buttons_frame.grid(row=0, column=0, sticky="w", **toolkit_UI.ctk_frame_paddings)

            # UI - the buttons should be next to each other, so we'll use a pack layout
            save_button.pack(side='left', **toolkit_UI.ctk_footer_button_paddings)
            cancel_button.pack(side='left', **toolkit_UI.ctk_footer_button_paddings)

            # add the buttons to the kwargs so we can pass them to future functions
            kwargs['save_button'] = save_button
            kwargs['cancel_button'] = cancel_button

            # ASSISTANT SETTINGS FORM
            # (also send the assistant settings)
            assistant_form_vars = self.app_items_obj.add_assistant_prefs(
                parent=middle_frame, skip_general=True, **assistant_settings)

            form_vars = {**assistant_form_vars}

            # UI - start button command
            # at this point, the kwargs should also contain the ingest_window_id
            save_button.configure(
                command=lambda l_assistant_window_id=assistant_window_id:
                self.save_assistant_settings(assistant_window_id=l_assistant_window_id, input_variables=form_vars)
            )

            # UI - cancel button command
            cancel_button.configure(
                command=lambda l_settings_window_id=settings_window_id:
                self.destroy_window_(window_id=l_settings_window_id)
            )

            # UI - configure the bottom columns and rows so that the elements expand with the window
            bottom_frame.columnconfigure(0, weight=1)
            bottom_frame.columnconfigure(1, weight=1)
            bottom_frame.rowconfigure(1, weight=1)
            bottom_frame.rowconfigure(2, weight=1)

            # UI - add a minimum height to the window
            settings_window.minsize(500, 700
            if settings_window.winfo_screenheight() > 700 else settings_window.winfo_screenheight())

            # UI- add a maximum height to the window (to prevent it from being bigger than the screen)
            settings_window.maxsize(600, settings_window.winfo_screenheight())

    def save_assistant_settings(self, assistant_window_id, input_variables: dict = None):

        # remove _var from all the input variables and get their values into a new dict
        assistant_settings = {}
        for key, form_var in input_variables.items():
            if key.endswith('_var'):
                assistant_settings[key[:-4]] = form_var.get()
            else:
                assistant_settings[key] = form_var.get()

        # get the assistant window
        assistant_window = self.get_window_by_id(assistant_window_id)

        # use a shorter name for the assistant item
        assistant_item = assistant_window.assistant_item

        # set a new model provider and model name (only if they are different from the current ones)
        if assistant_settings.get('assistant_provider', None) and assistant_settings.get('assistant_model', None) \
            and (assistant_settings.get('assistant_provider', None) != assistant_item.model_provider
                or assistant_settings.get('assistant_model', None) != assistant_item.model_name):

            # reset the assistant item
            new_assistant_item = AssistantUtils.assistant_handler(
                toolkit_ops_obj=self.toolkit_ops_obj,
                model_provider=assistant_settings.get('assistant_provider'),
                model_name=assistant_settings.get('assistant_model')
            )

            if new_assistant_item is None:
                logger.error('Cannot change assistant model. The model provider or model name is invalid.')
                return False

            # copy the context and chat history from the old to the new assistant item
            ToolkitAssistant.copy_context_and_chat(assistant_item, new_assistant_item)

            # if the model is valid, replace the assistant item
            assistant_window.assistant_item = new_assistant_item
            assistant_item = new_assistant_item

            # update the assistant window
            model_reply = "Model changed to {} {}.\n" \
                            .format(assistant_item.model_provider, assistant_item.model_description)

            if new_assistant_item.info is not None and 'pricing_info' in new_assistant_item.info:
                model_reply += "See {} for more reliable pricing." \
                                .format(assistant_item.info.get('pricing_info'))

            model_reply += "\nUsage for this window has been reset to 0 due to model change."

            # when updating the text window
            self._text_window_update(assistant_window_id, model_reply)

        # we don't need the assistant_model and assistant_provider in the settings from here on
        # since we already used them previously
        if 'assistant_model' in assistant_settings:
            del assistant_settings['assistant_model']

        if 'assistant_provider' in assistant_settings:
            del assistant_settings['assistant_provider']

        # update the system prompt (if not empty)
        if assistant_settings.get('assistant_system_prompt', None) is not None:
            assistant_item.set_system(system_message=assistant_settings.get('assistant_system_prompt'))
            self._text_window_update(assistant_window_id, 'System prompt changed.')

        # remove the 'assistant_' prefix from the settings
        assistant_settings = {k[10:]: v for k, v in assistant_settings.items() if k.startswith('assistant_')}

        # update the assistant settings
        assistant_window.assistant_settings = assistant_settings

        # let the user know that the settings were saved
        self._text_window_update(assistant_window_id, 'New settings loaded.')

        # destroy the settings window after 100ms
        assistant_window.after(100, lambda: self.destroy_window_(window_id=assistant_window_id+'_settings'))

    def assistant_query(self, prompt, assistant_window_id: str, assistant_item=None):

        # get this window object
        assistant_window = self.get_window_by_id(assistant_window_id)

        if assistant_item is None:

            # use the assistant item from the assistant window
            assistant_item = assistant_window.assistant_item if hasattr(assistant_window, 'assistant_item') else None

            if assistant_item is None:
                error_no_assistant = 'Cannot run assistant query - no assistant item found.'
                logger.error(error_no_assistant)
                self._text_window_update(assistant_window_id,
                                         error_no_assistant + '\nPlease set a default model in Preferences.')
                return

        text_widget = assistant_window.text_widget

        # strip the prompt
        prompt = prompt.strip()

        # we use this whenever we're changing the context only for the current prompt
        temp_context = None

        # this decides whether we should save the prompt and response to the chat history
        # depending on what type of prompt this is
        save_to_history = True

        # we use this to add or remove things from the actual prompt when sending it to the model
        enhanced_prompt = prompt

        # use this to know if there's any specific format the user requested
        requested_format = None

        # try to run the assistant query
        try:
            # is the user asking for help?
            if prompt.lower() == '[help]':

                help_reply = ("You are using {} ({}).\n"
                              .format(assistant_item.model_description, assistant_item.model_provider))

                if assistant_item.info is not None and 'pricing_info' in assistant_item.info:
                    help_reply += "See {} for more reliable pricing. \n" \
                                   .format(assistant_item.info.get('pricing_info'))

                help_reply += "\n"

                help_reply += "Every time you ask something, you may send out the entire conversation " \
                              "and the initial context.\n" \
                              "The longer the conversation, the more tokens you are using on each request.\n\n" \
                              "Use [usage] to keep track of your usage in this Assistant window.\n" \
                              "Use [calc] to get the minimum number of tokens you're sending with each request.\n" \
                              "Use [price] to see how much the model costs.\n\n" \
                              "Use [reset] to reset the conversation, while preserving any contexts.\n" \
                              "Use [resetall] to reset the conversation and the initial context.\n" \
                              "Resetting will reduce the tokens you're sending out.\n\n" \
                              "Use [context] to see the initial context text that is sent out with each prompt.\n\n" \
                              "Use [model] to see the model used in this window.\n" \
                              "Use [model:MODEL_PROVIDER:MODEL_NAME] to change the model used in this window.\n" \
                              "Use [models] to see the available models.\n\n" \
                              "Use [exit] to exit the Assistant.\n\n" \
                              "Use [t] or [st] before the prompt, to send a transcription or story focused prompt.\n" \
                              "These will make the assistant aware of the transcription and story content " \
                              "and try to influence a relevant response. " \
                              "Note: when using [t] or [st], " \
                              "the prompt and response will not be saved to the chat history " \
                              "unless you add it afterwards."

                # use this to make sure we have a new prompt prefix for the next search
                self._text_window_update(assistant_window_id, help_reply)
                return

            elif prompt.lower().startswith('[model:') and prompt.lower().endswith(']'):

                # make sure that the correct syntax is used - [model:MODEL_PROVIDER:MODEL_NAME]
                model_and_provider_name = prompt[7:-1]

                if ':' not in model_and_provider_name:
                    self._text_window_update(assistant_window_id, 'Invalid model and provider name.\n'
                                                                  'Use [model:MODEL_PROVIDER:MODEL_NAME]. '
                                                                  'For eg.: [model:OpenAI:gpt-4]')
                    return

                model_and_provider_name = model_and_provider_name.split(':')
                model_provider = model_and_provider_name[0]
                model_name = model_and_provider_name[1]

                # if the model provider and names are the same as the current ones, do nothing
                if model_provider == assistant_item.model_provider and model_name == assistant_item.model_name:
                    self._text_window_update(
                        assistant_window_id,
                        'You are already using {} {}.\n'.format(model_provider, model_name)
                    )
                    return

                new_assistant_item = AssistantUtils.assistant_handler(
                    toolkit_ops_obj=self.toolkit_ops_obj, model_provider=model_provider, model_name=model_name)

                if new_assistant_item is None:

                    model_reply = "Invalid model or provider name.\n"
                    model_reply += ("You are still using {} {}.\n"
                                    .format(assistant_item.model_provider, assistant_item.model_description))

                    self._text_window_update(assistant_window_id, model_reply)
                    return

                # copy the context and chat history from the old to the new assistant item
                ToolkitAssistant.copy_context_and_chat(assistant_item, new_assistant_item)

                # if the model is valid, replace the assistant item
                assistant_window.assistant_item = new_assistant_item
                assistant_item = new_assistant_item

                # update the assistant window
                model_reply = "Model changed to {} {}.\n" \
                              .format(assistant_item.model_provider, assistant_item.model_description)

                if assistant_item.info is not None and 'pricing_info' in assistant_item.info:
                    model_reply += "See {} for more reliable pricing. \n" \
                        .format(assistant_item.info.get('pricing_info'))

                model_reply += "\nUsage for this window has been reset to 0 due to model change.\n"

                # get the current text_widget prompt kwargs
                prompt_callback_kwargs = text_widget.prompt_callback_kwargs

                # update the assistant_item in the prompt kwargs
                prompt_callback_kwargs['assistant_item'] = new_assistant_item

                # when updating the text window
                self._text_window_update(assistant_window_id, model_reply)

                return

            elif prompt.lower() == '[models]':

                # list all the available models in assistant_item.LLM_AVAILABLE_MODELS
                models_reply = "Available models:\n"

                for available_model_provider in assistant_item.available_models:

                    for available_model_name in assistant_item.available_models[available_model_provider]:

                        models_reply += "{} {}\n" \
                                         .format(available_model_provider, available_model_name)

                self._text_window_update(assistant_window_id, models_reply)
                return

            elif prompt.lower() == '[model]':

                model_reply = "You are using {} ({}).\n" \
                              .format(assistant_item.model_description, assistant_item.model_provider)

                if assistant_item.info is not None and 'pricing_info' in assistant_item.info:
                    model_reply += "See {} for more reliable pricing. \n" \
                                   .format(assistant_item.info.get('pricing_info'))

                model_reply += '\nUse [model:MODEL_PROVIDER:MODEL_NAME] to change the model used in this window.\n'
                self._text_window_update(assistant_window_id, model_reply)
                return

            elif prompt.lower() == '[price]':

                price_reply = ("You are using {} ({}).\n"
                               .format(assistant_item.model_description, assistant_item.model_provider))

                if isinstance(assistant_item.model_price, tuple) and len(assistant_item.model_price) == 3:
                    price_reply += "According to our info, the model costs:\n"
                    price_reply += ("{} {} per 1000 tokens sent.\n"
                                    .format(assistant_item.model_price[0], assistant_item.model_price[2]))
                    price_reply += ("{} {} per 1000 tokens received.\n\n"
                                    .format(assistant_item.model_price[1], assistant_item.model_price[2]))

                    price_reply += "This information might not be up to date!\n"

                else:
                    price_reply += "We don't have enough pricing information for this model.\n"

                if assistant_item.info is not None and 'pricing_info' in assistant_item.info:
                    price_reply += "See {} for more reliable model pricing info. \n" \
                                   .format(assistant_item.info.get('pricing_info'))

                # use this to make sure we have a new prompt prefix for the next search
                self._text_window_update(assistant_window_id, price_reply)

                return

            # if the user is asking for usage
            elif prompt.lower() == '[usage]' or prompt.lower() == '[calc]':

                if prompt.lower() == '[calc]':
                    num_tokens = assistant_item.calculate_history_tokens()
                    if num_tokens is not None:
                        calc_reply = "The context plus conversation uses {} tokens/request\n\n".format(num_tokens)

                        calc_reply += "This is the minimum amount of tokens you send on each request, " \
                                      "plus your message, unless you [reset] or [resetall]."

                    else:
                        calc_reply = "Cannot calculate the number of tokens used. Model not supported."

                    self._text_window_update(assistant_window_id, calc_reply)

                used_tokens_in = int(assistant_item.tokens_used[0])
                used_tokens_out = int(assistant_item.tokens_used[1])
                used_tokens_total = used_tokens_in + used_tokens_out

                total_price = None
                if isinstance(assistant_item.model_price, tuple) and len(assistant_item.model_price) == 3\
                        and assistant_item.model_price[0] is not None and assistant_item.model_price[1] is not None:
                    price_in = assistant_item.model_price[0] * used_tokens_in / 1000
                    price_out = assistant_item.model_price[1] * used_tokens_out / 1000
                    total_price = price_in + price_out
                else:
                    logger.warning('Cannot calculate price for model {} {}. Pricing schema not valid.'.format(
                        assistant_item.model_provider, assistant_item.model_name
                    ))

                header = "Approximate token usage in this Assistant window:"
                tokens_data = [
                    ("Sent:", used_tokens_out, ' tokens'),
                    ("Received:", used_tokens_in, ' tokens'),
                    ("Total:", used_tokens_total, ' tokens')
                ]

                usage_reply = self.text_table(tokens_data, header)

                if total_price is not None:
                    usage_reply += "\n"
                    usage_reply += "Total price: cca. {:.6f} {}.\n" \
                                   .format(total_price, assistant_item.model_price[2])

                    if assistant_item.info is not None and 'pricing_info' in assistant_item.info:
                        usage_reply += "\nSee {} for more accurate model pricing info. \n" \
                            .format(assistant_item.info.get('pricing_info'))

                usage_reply += "\nImportant: this calculation might not be accurate!"

                self._text_window_update(assistant_window_id, usage_reply)
                return

            elif prompt.lower() == '[reset]' or prompt.lower() == '[resetall]':
                assistant_item.reset()

                # remove all references to the assistant item from the chat history
                if hasattr(assistant_window, 'chat_history') and 'items' in assistant_window.chat_history:
                    for key, current_chat_history_item in assistant_window.chat_history['items'].items():
                        assistant_window.chat_history['items'][key]['assistant_chat_history_index'] = None

                        self.assistant_toggle_history_item_color(tag_id=key, text_widget=text_widget, active=False)

                if prompt.lower() == '[resetall]':
                    assistant_item.add_context(context='')
                    assistant_window.transcription_segments = None
                    self._text_window_update(assistant_window_id, 'Conversation reset and context removed.')
                else:
                    self._text_window_update(assistant_window_id, 'Conversation reset, but context preserved.')
                return

            elif prompt.lower() == '[clear]':
                self._text_window_update(assistant_window_id, '', clear=True)
                return

            elif prompt.lower() == '[context]':

                if assistant_item.context is None:
                    self._text_window_update(assistant_window_id, 'No context used for this conversation.')

                else:
                    if assistant_window.transcription_segments is not None:
                        self._text_window_update(assistant_window_id, "Context contains transcription segments.")

                    self._text_window_update(assistant_window_id,
                                             "The context used for this conversation is:\n\n{}\n"
                                             .format(assistant_item.context))

                return

            # is the user trying to quit?
            elif prompt.lower() == '[quit]':
                self.destroy_assistant_window(assistant_window_id)
                return

            elif prompt.lower() == '[settings]':

                # open the assistant settings window
                self.open_assistant_window_settings(assistant_window_id=assistant_window_id)
                self._text_window_update(assistant_window_id, '')
                return

            elif prompt.lower().startswith(('[t]', '[st]')):

                # Extracting the content inside the first square brackets
                match = re.match(r'\[([^\]]+)\]', prompt)
                requested_format = match.group(1) if match else None

                temp_context_type = 'transcription_json'

                if requested_format == 'st':
                    temp_context_type = 'story_json'

                if not hasattr(assistant_window, 'transcription_segments') \
                   or not assistant_window.transcription_segments:

                    self._text_window_update(assistant_window_id, 'No transcription segments found in context.')
                    return

                # instead of sending the text context, we're going to use a json formatted context
                temp_context = {'type': temp_context_type, 'lines': []}

                if assistant_window.transcription_segments is not None:

                    for segment in assistant_window.transcription_segments:

                        temp_context['lines'].append(segment.to_list())

                # use replace to remove the requested_format keyword when sending the prompt to the model
                enhanced_prompt = enhanced_prompt.replace('[{}]'.format(requested_format), '', 1)

                # strip the prompt again
                enhanced_prompt = enhanced_prompt.strip()

                # add the formatting details to the enhanced prompt
                enhanced_prompt += "\nuse exact same json format or you'll break my code: "
                enhanced_prompt += '{{"type": "{}", "lines": [[start, end, text], ...]'.format(temp_context_type)
                enhanced_prompt += ', "groups": [[start, end, title, optional_text], ...]'
                enhanced_prompt += '}}'

                # don't this query to the chat history since it might be large
                save_to_history = False

                # get the settings from the window again
            assistant_settings = assistant_window.assistant_settings

            # parse json to string
            if temp_context is not None:
                temp_context = json.dumps(temp_context)

            def query_assistant():

                # first lock the text_widget to prevent the user from typing until a reply is received
                text_widget.locked = True

                # assuming that the user pressed enter to send the prompt,
                # we need to get the correct index of the prompt line so that we add it to the window chat history
                prompt_line_index_start = text_widget.index(text_widget.last_prompt_line + '.0')
                prompt_line_index_end = text_widget.index(text_widget.last_prompt_line + '.0 lineend +1c')

                # construct a unique prompt tag using the current time and a random number
                unique_prompt_tag = 'p_'+str(time.time())+str(random.randint(0, 100000))

                # add a unique tag to the prompt line
                text_widget.tag_add(unique_prompt_tag, prompt_line_index_start, prompt_line_index_end)

                # get the assistant response
                # we're wrapping this in a try/except block
                # to make sure we unlock the text_widget no matter what
                try:

                    # send the prompt to the assistant
                    # it should return both the response and the used history
                    assistant_response, used_history = assistant_item.send_query(
                       enhanced_prompt, assistant_settings, temp_context=temp_context, save_to_history=save_to_history)

                    # only add to history if we have a completion
                    if assistant_response.completion is not None:

                        # prompt goes to chat history
                        # - we're using the used_history[:-1] because the last item in the used_history is the response
                        # - we use the last_assistant_message_idx-1 as reference to the last prompt in the chat history
                        #   but only if we're saving the prompt to the history
                        self._add_to_assistant_window_chat_history(
                            content_type='prompt',
                            content=enhanced_prompt,
                            widget_text=prompt,
                            widget_tag=unique_prompt_tag,
                            assistant_window=assistant_window,
                            assistant_chat_history=used_history[:-1] if len(used_history) > 0 else [],
                            assistant_chat_history_index=
                            assistant_item.last_assistant_message_idx-1
                            if (save_to_history and assistant_item.last_assistant_message_idx) else None
                        )

                        self.assistant_toggle_history_item_color(
                            tag_id=unique_prompt_tag, text_widget=text_widget, active=save_to_history)

                    # we need this to wrap the response in a tag later
                    response_line_index_start = text_widget.index(ctk.INSERT)

                    # construct a unique response tag using the current time and a random number
                    unique_response_tag = 'r_' + str(time.time()) + str(random.randint(0, 100000))

                    # POST PROCESS THE RESPONSE (for some cases)
                    # did we request a specific format?
                    response_was_parsed = None
                    if requested_format is not None and not assistant_response.error:

                        # take the response through the response parser
                        response_was_parsed = self.assistant_parse_response(
                            assistant_window_id=assistant_window_id, assistant_response=assistant_response.completion)

                        # stop here if the response_was_parsed is True or False (but not None)
                        # - meaning something was already displayed on the text window from assistant_parse_response
                        if response_was_parsed is not None:
                            text_widget.locked = False

                        # otherwise mention that we didn't receive what we were expecting
                        # (and also show the raw response below)
                        else:
                            self._text_window_update(
                                assistant_window_id, "The Assistant didn't reply in the requested format."
                            )

                            # move the start of the response tag here
                            response_line_index_start = text_widget.index(ctk.INSERT)

                    # update the assistant window (only if it wasn't already updated by assistant_parse_response)
                    if response_was_parsed is None:
                        if not assistant_response.error:
                            self._text_window_update(assistant_window_id, "A > " + assistant_response.completion)

                        else:
                            self._text_window_update(assistant_window_id, assistant_response.error)

                    # response goes to the window chat history but only if it's not an error
                    if not assistant_response.error:

                        self._add_to_assistant_window_chat_history(
                            content_type='response',
                            content=assistant_response,
                            widget_tag=unique_response_tag,
                            assistant_window=assistant_window,
                            requested_format=requested_format,
                            assistant_chat_history=used_history,
                            assistant_chat_history_index=
                            assistant_item.last_assistant_message_idx if save_to_history else None
                        )

                        # add a unique tag to the response lines
                        # for the end index, we use the index of the last line of the response minus 1 line since
                        # we're assuming that the _text_window_update function will add a new line and the prompt prefix
                        # after the actual response
                        text_widget.tag_add(
                            unique_response_tag,
                            text_widget.index(response_line_index_start),
                            text_widget.index(text_widget.index(ctk.INSERT + '-1l') + ' lineend')
                        )

                        self.assistant_toggle_history_item_color(
                            tag_id=unique_response_tag, text_widget=text_widget, active=save_to_history)

                except:
                    logger.error('Error while running assistant query.', exc_info=True)

                # unlock the text_widget
                text_widget.locked = False

            # execute assistant query in a separate thread
            Thread(target=query_assistant).start()

        except:
            logger.error('Error while running assistant query.', exc_info=True)

            # update the assistant window
            self._text_window_update(assistant_window_id, 'An error occurred :-(')

    def assistant_toggle_history_item_color(self, tag_id, text_widget, window_id=None, active=None):

        # if no active state is provided, we'll figure it out based on the tag_id
        if active is None:

            if window_id is None:
                logger.error('Cannot toggle history item color. No window_id provided.')
                return

            # is the item in the chat history?
            chat_history_item = self._get_chat_history_item_at_tag(window_id, tag_id)

            if chat_history_item is None:
                return

            if not chat_history_item.get('assistant_chat_history_index', None):
                active = False
            else:
                active = True

        # make the background a bit lighter if it's in the chat history
        if active:
            # make this look more washed out
            text_widget.tag_config(tag_id, background=toolkit_UI.theme_colors['darker'])

        # otherwise, adopt the text widget theme
        else:
            # get the background color of the text widget
            text_widget_background = text_widget.cget('background')
            text_widget.tag_config(tag_id, background=text_widget_background)

    @staticmethod
    def _add_to_assistant_window_chat_history(
            assistant_window, content_type, content, assistant_chat_history,
            widget_tag, widget_text=None,
            assistant_chat_history_index=None, requested_format=None
    ):
        """
        This adds prompts and responses to the assistant window chat history.
        :param assistant_window: the assistant window object
        :param content_type: the type of content we're adding to the chat history (prompt or response)
        :param content: the content we're adding to the chat history
        :param assistant_chat_history: the assistant chat history
        :param widget_tag: the tag that wraps the content in the text widget
                           (this also serves as a the unique id of the content in the widget)
        :param widget_text: the text widget text for this content -
                            if None, we will have to re-parse it from the content if we need to refresh the text widget
        :param assistant_chat_history_index: the index of the assistant chat history where the content is
        :param requested_format: the format requested for the response
        """

        # make sure we have a chat_history attribute on the window,
        # so we can keep track of what messages we see on the window,
        # and which are referenced in the assistant_item.chat_history
        # below, the chat_history is a dict with two keys:
        # - order (stores the order of the messages in the text widget) and
        # - items (stores the actual messages)
        if not hasattr(assistant_window, 'chat_history'):
            assistant_window.chat_history = {'order': [], 'items': {}}

        history_item = {
            'type': content_type,
            'content': content,
            'assistant_chat_history': assistant_chat_history,
            'text_widget_text': widget_text,
            'assistant_chat_history_index': assistant_chat_history_index,
            'requested_format': requested_format
        }

        # add the history item to the window chat history
        assistant_window.chat_history['items'][widget_tag] = history_item

        # append the widget_tag to the order list
        assistant_window.chat_history['order'].append(widget_tag)

    def _get_chat_history_item_at_tag(self, assistant_window_id, widget_tag):
        """
        This looks into the chat history of the window and returns the item that has the given widget_tag.
        """

        # get the window object
        assistant_window = self.get_window_by_id(assistant_window_id)

        if assistant_window is None:
            logger.error('Cannot get chat history item. Assistant window not found.')
            return None

        # if the window doesn't have a chat history, create one
        if not hasattr(assistant_window, 'chat_history'):
            assistant_window.chat_history = {'order': [], 'items': {}}

        # go through all the items in the chat history
        if widget_tag in assistant_window.chat_history['items']:
            return assistant_window.chat_history['items'][widget_tag]

        return None

    def _assistant_window_context_menu(self, event=None, window_id: str = None, context_menu=None, **attributes):
        """
        This is the context menu for the assistant window.
        """

        # get the window object
        window = self.get_window_by_id(window_id=window_id)

        # get the text widget from the event
        text_widget = event.widget

        index = text_widget.index(f"@{event.x},{event.y}")
        tags = text_widget.tag_names(index)

        # if the item at the click position has the tag 'has_context_menu', do nothing
        # assuming that the context menu for it is defined some place else
        if 'has_context_menu' in tags and context_menu is None:
            return

        # get the line and char from the click
        line, char = self.get_line_char_from_click(event, text_widget=text_widget)
        line = int(line)
        char = int(char)

        # create the context menu
        if not context_menu:
            context_menu = tk.Menu(text_widget, tearoff=0)

        # otherwise, add separator to keep the existing menu items separate from the one's we're adding
        else:
            context_menu.add_separator()

        # add the menu items
        # if there is a selection
        if text_widget.tag_ranges("sel"):
            context_menu.add_command(label="Copy", command=lambda: text_widget.event_generate("<<Copy>>"))

            # add the de-select all option
            context_menu.add_command(label="Deselect", command=lambda: text_widget.tag_remove("sel", "1.0", "end"))

        else:
            # add the select all option
            context_menu.add_command(label="Select All", command=lambda: text_widget.tag_add("sel", "1.0", "end"))

            # add a separator
            # context_menu.add_separator()

        # get the tags at the click position
        tags_at_click = text_widget.tag_names(index)

        # HANDLING OF PROMPT AND RESPONSE CONTEXT MENU OPTIONS

        # are there any tags that starts with p_ or r_ ?
        # p_ is for prompt, r_ is for response
        if any([tag.startswith('p_') or tag.startswith('r_') for tag in tags_at_click]):

            def get_insert_conversation_index(tag_id):
                """
                This goes through the window chat history and returns the index closest to the given tag_id,
                according to item['assistant_chat_history_index'].
                """

                closest_index = None
                passed_tag_id = False

                for key, current_chat_history_item in window.chat_history['items'].items():
                    # Update closest_index if a valid assistant_chat_history_index is found
                    if current_chat_history_item['assistant_chat_history_index'] is not None:
                        closest_index = current_chat_history_item['assistant_chat_history_index']
                        if passed_tag_id:
                            # if we have already passed the tag_id,
                            # it means that we have found the closest index after it
                            # so we need to return the closest_index so that we shift everything after it by 1
                            return closest_index

                    # check if we've reached our tag_id
                    if key == tag_id:
                        passed_tag_id = True
                        if closest_index is not None:
                            # if closest_index is set, return the index after it
                            return closest_index + 1

                # if we didn't find anything,
                # we return the length of the assistant chat history so that we insert at the end
                return len(window.assistant_item.chat_history)

            def add_to_conversation(tag_id, item):

                # make sure that the window assistant chat item is not in the conversation already
                if item['assistant_chat_history_index'] is not None:
                    logger.debug('Cannot add to conversation. Item {} is already in the conversation.'.format(tag_id))
                    return

                # get the index where we should insert the item in the assistant chat history
                insert_index = get_insert_conversation_index(tag_id)

                # prepare the item to be added to the assistant chat history
                assistant_chat_history_item = {
                    'role': 'user' if item['type'] == 'prompt' else 'assistant',
                    'content': item['content']
                }

                # first, shift all the assistant chat history indexes after the insert_index by 1
                # this will ensure that all the references are correct
                # we need to first shift and then add the item to the assistant chat history
                # otherwise we'll shift the item's index too
                for key, current_chat_history_item in window.chat_history['items'].items():
                    if current_chat_history_item['assistant_chat_history_index'] is not None \
                            and current_chat_history_item['assistant_chat_history_index'] >= insert_index:
                        window.chat_history['items'][key]['assistant_chat_history_index'] += 1

                # then, add the item to the assistant chat history
                window.assistant_item.chat_history.insert(insert_index, assistant_chat_history_item)

                # add the reference to the assistant chat history index to the item
                item['assistant_chat_history_index'] = insert_index

                # toggle the color of the item in the text widget
                self.assistant_toggle_history_item_color(tag_id=tag_id, text_widget=text_widget, active=True)

                return

            def remove_from_conversation(tag_id, item):

                # make sure that the window assistant chat item is in the conversation
                if item['assistant_chat_history_index'] is None:
                    logger.debug('Cannot remove from conversation. '
                                 'Item {} is already not in the conversation.'.format(tag_id))

                # use the index to remove it from the assistant chat history
                window.assistant_item.chat_history.pop(item['assistant_chat_history_index'])

                past_item_index = item['assistant_chat_history_index']

                # mark this item as not being in the conversation
                item['assistant_chat_history_index'] = None

                # toggle the color of the item in the text widget
                self.assistant_toggle_history_item_color(tag_id=tag_id, text_widget=text_widget, active=False)

                # now shift down all the assistant chat history indexes after the removed item by 1
                for key, current_chat_history_item in window.chat_history['items'].items():
                    if current_chat_history_item['assistant_chat_history_index'] is not None \
                    and current_chat_history_item['assistant_chat_history_index'] > past_item_index:
                        current_chat_history_item['assistant_chat_history_index'] -= 1

                return

            widget_tag = None
            # get the first tag that starts with p_ or r_
            for tag in tags_at_click:
                if tag.startswith('p_') or tag.startswith('r_'):
                    widget_tag = tag
                    break

            # prompt / response specific options
            # get the chat history item of the line we clicked on
            chat_history_item = self._get_chat_history_item_at_tag(assistant_window_id=window_id, widget_tag=widget_tag)

            # is this used in the assistant item history as context?
            if isinstance(chat_history_item, dict) and 'assistant_chat_history_index' in chat_history_item:

                context_menu.add_separator()

                if chat_history_item['assistant_chat_history_index'] is None:

                    context_menu.add_command(
                        label='Add to conversation',
                        command=lambda: add_to_conversation(tag_id=widget_tag, item=chat_history_item)
                    )

                else:
                    context_menu.add_command(
                        label='Remove from conversation',
                        command=lambda: remove_from_conversation(tag_id=widget_tag, item=chat_history_item)
                    )

            # prompt specific options
            if any([tag.startswith('p_') for tag in tags_at_click]):
                context_menu.add_command(
                    label="Reuse prompt",
                    command=lambda: self.inject_prompt(
                        window_id=window_id, prompt=chat_history_item['text_widget_text'], execute=False,
                        clear_line=False
                    )
                )

                context_menu.add_command(
                    label="Copy prompt and conversation",
                    command=lambda:
                    self.copy_to_clipboard(
                        self._assistant_parse_chat_history_item_history(chat_history_item, include_prompt=True))
                )

        # display the context menu
        context_menu.tk_popup(event.x_root, event.y_root)

    @staticmethod
    def _assistant_parse_chat_history_item_history(chat_history_item, output='text', include_prompt=False):

        # first get the chat_history of the item
        chat_history = chat_history_item.get('assistant_chat_history', '')

        if include_prompt:
            chat_history.append({'role': 'user', 'content': chat_history_item.get('content', '')})

        if output == 'text':
            result = ''
            # parse the json to string
            for message in chat_history:

                result += message.get('role', '')+':\n'+message.get('content', '')+'\n\n'

            # remove the last \n\n
            result = result[:-2]

            return result

        else:
            return chat_history


    def assistant_parse_response(self, assistant_response, assistant_window_id):
        """
        This tries to recognize what kind of response the assistant gave, for eg. transcription, story, etc.
        and populates the assistant window's text widget.
        """

        # first, clean the response and try to parse it to json
        assistant_response_dict = AssistantUtils.parse_response_to_dict(assistant_response=assistant_response)

        # if no parsing was possible, just return None
        if assistant_response_dict is None:
            return None

        # get the text widget from the assistant window
        assistant_window = self.get_window_by_id(assistant_window_id)

        if assistant_window is None:
            logger.error('Cannot parse assistant response. Assistant window not found.')
            return None

        text_widget = assistant_window.text_widget

        # now let's try to figure out what kind of response this is
        # is there a type in the response?
        response_type = None
        parsed = False
        try:
            response_type = assistant_response_dict['type']

        except KeyError:
            logger.error('Cannot parse assistant response. No type found in response dict.')

        except TypeError:
            logger.error('Cannot parse assistant response. Response dict is not a dict.')

        except:
            logger.error('Cannot parse assistant response.', exc_info=True)

        # print(json.dumps(assistant_response_dict, indent=4))

        # get the text widget prompt prefix
        def minify_and_add_response(response_string, context_menu=None, **context_menu_kwargs):
            """
            We're using this function to add the response to the text widget.
            """

            # move the cursor past the \n at the end of the line
            text_widget.mark_set(ctk.INSERT, ctk.END + '-1c')

            full_insert_pos = text_widget.index(ctk.INSERT)

            # add the prompt prefix first
            text_widget.insert(ctk.END, 'A > ')

            # get the current insert position
            insert_pos = text_widget.index(ctk.INSERT)

            text_widget.insert(ctk.END, response_string)

            # now change the color of the full A > response to supernormal (similar to  _text_window_update())
            text_widget.tag_add('reply', full_insert_pos, text_widget.index(ctk.INSERT))
            text_widget.tag_config('reply', foreground=self.theme_colors['supernormal'])

            # use the timestamp to make the tag unique
            # plus the current line number
            tag_id = 'assistant_response_{}'.format(str(time.time()) + str(text_widget.index(ctk.INSERT)))

            # change the color of the above text (without A > prefix) so the users know it's of a different kind
            text_widget.tag_add(tag_id, insert_pos, text_widget.index(ctk.INSERT))
            text_widget.tag_config(tag_id, foreground=toolkit_UI.theme_colors['blue'])

            # make sure to add the has_context_menu tag so that we don't show the text window context menu
            text_widget.tag_add('has_context_menu', insert_pos, text_widget.index(ctk.INSERT))

            # add the context menu
            if context_menu is not None:

                # add right click for context menu
                text_widget.tag_bind(
                    tag_id,
                    '<Button-3>',
                    lambda event: context_menu(event, tag_id, **context_menu_kwargs)
                )

                # make this work on macos trackpad too
                text_widget.tag_bind(
                    tag_id,
                    '<Button-2>',
                    lambda event: context_menu(event, tag_id, **context_menu_kwargs)
                )

        def show_response_details(base_tag, details_tag, text):
            """
            We use this function to show the details of a response right after the response itself.
            If we already showed some details for said response, they will be replaced with the new ones.
            """
            tag_range = text_widget.tag_ranges(base_tag)

            if not tag_range:
                print(f"Base tag '{base_tag}' not found.")
                return

            _, base_tag_end = tag_range
            details_range = text_widget.tag_ranges(details_tag)

            if details_range:
                start, end = details_range
                text_widget.delete(start, end)
                text_widget.insert(start, text)
                text_widget.tag_add(details_tag, start, f"{start} + {len(text)}c")
            else:
                next_line_index = text_widget.index(f"{base_tag_end} + 1 line linestart")
                text_widget.insert(next_line_index, text)
                text_widget.tag_add(details_tag, next_line_index, f"{next_line_index} + {len(text)}c")

        def show_transcription_text(base_tag, details_tag):
            text_response = ''
            for segment in assistant_response_dict['lines']:
                text_response += '{} - {}:\n{}\n\n'.format(
                    round(float(segment[0]), 3),
                    round(float(segment[1]), 3),
                    str(segment[2]).strip()
                )
            show_response_details(base_tag, details_tag=details_tag, text=text_response)

        def show_raw_text(base_tag, details_tag):
            show_response_details(base_tag, details_tag=details_tag, text=assistant_response)

        def hide_text(base_tag, details_tag):
            show_response_details(base_tag, details_tag=details_tag, text='')

        # if the response is a transcription
        if response_type == 'transcription_json' \
            and 'lines' in assistant_response_dict and isinstance(assistant_response_dict['lines'], list):

            logger.debug('Parsing assistant response as transcription.')

            # parse any transcript groups
            parsed_groups = None
            if 'groups' in assistant_response_dict:

                parsed_groups = []
                try:
                    for group in assistant_response_dict['groups']:

                        new_group = {
                            'group_name': group[2],
                            'group_notes': group[3] if len(group) > 3 else '',
                            'time_intervals': [{'start': group[0], 'end': group[1]}],
                        }
                        parsed_groups.append(new_group)

                except:
                    logger.error('Cannot parse transcript groups.', exc_info=True)

            def transcription_context_menu(event, clicked_tag_id, **kwargs):
                """
                This is triggered on right-click on the transcription response
                and it basically shows the context menu for the Transcription type response
                """

                details_tag = clicked_tag_id + '_details'

                # create the context menu
                context_menu = tk.Menu(text_widget, tearoff=0)

                # the add to transcription sub-menu
                add_to_transcription_menu = tk.Menu(context_menu, tearoff=0)
                
                # use the parent transcription of the first segment as the source transcription
                try:
                    source_transcription = kwargs.get('transcription_segments')[0].parent_transcription
                except TypeError or IndexError:
                    source_transcription = None

                # the "New Transcription" button
                add_to_transcription_menu.add_command(
                    label="New Transcription...",
                    command=lambda: self.open_new_transcription_window(
                                    source_transcription=source_transcription,
                                    transcription_segments=assistant_response_dict['lines'],
                                    transcript_groups=parsed_groups
                                )
                )
                add_to_transcription_menu.add_separator()

                transcription_windows = self.get_all_windows_of_type('transcription')

                for transcription_window_id in transcription_windows:
                    transcription_window = self.get_window_by_id(window_id=transcription_window_id)
                    transcription_file_path = \
                        self.t_edit_obj.get_window_transcription(transcription_window_id).transcription_file_path

                    add_to_transcription_menu.add_command(
                        label="{}".format(transcription_window.title()),
                        command=lambda l_transcription_window_id=transcription_window_id,
                        l_transcription_file_path=transcription_file_path:
                        self.open_transcription_window(
                            transcription_file_path=l_transcription_file_path,
                            new_transcription_segments=assistant_response_dict.get('lines', None),
                            new_transcript_groups=parsed_groups,
                        )
                    )

                # add the add to transcription sub-menu
                context_menu.add_cascade(label="Add to Transcription", menu=add_to_transcription_menu)

                # add separator
                context_menu.add_separator()

                # add the text menu items
                context_menu.add_command(
                    label="Show text response",
                    command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                    show_transcription_text(l_base_tag, l_details_tag)
                )
                context_menu.add_command(
                    label="Show raw response",
                    command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                    show_raw_text(l_base_tag, l_details_tag)
                )

                # is there a details tag?
                if text_widget.tag_ranges(details_tag):
                    # then show the hide details option
                    context_menu.add_command(
                        label="Hide response",
                        command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                        hide_text(l_base_tag, l_details_tag)
                    )

                # now call the assistant window context menu (also with the previously added)
                self._assistant_window_context_menu(
                    event=event, window_id=assistant_window_id, context_menu=context_menu,
                )

            # if we received this kind of response,
            # we must assume that we had transcription_segments when making the assistant query
            # we will use these to add the context menu to the response
            # so add them to the transcription segments to the context_menu_kwargs
            # this doesn't work if we have multiple transcriptions as sources
            context_transcription_segments = assistant_window.transcription_segments

            minify_and_add_response(
                response_string='Received Transcription',
                context_menu=transcription_context_menu,
                transcription_segments=context_transcription_segments
            )

            parsed = True

        # if the response is a story
        elif response_type == 'story_json' \
            and 'lines' in assistant_response_dict and isinstance(assistant_response_dict['lines'], list):

            logger.debug('Parsing assistant response as story.')

            def story_context_menu(event, clicked_tag_id, **kwargs):
                """
                This is triggered on right-click on the transcription response
                and it basically shows the context menu for the Transcription type response
                """

                details_tag = clicked_tag_id + '_details'

                # create the context menu
                context_menu = tk.Menu(text_widget, tearoff=0)

                # the add to transcription sub-menu
                add_to_story_menu = tk.Menu(context_menu, tearoff=0)

                # use the parent transcription of the first segment as the source transcription
                try:
                    source_transcription = kwargs.get('transcription_segments')[0].parent_transcription
                except TypeError or IndexError:
                    source_transcription = None

                def add_to_story(story_editor_window_id):
                    new_lines = []

                    for segment in assistant_response_dict['lines']:
                        new_lines.append({
                            'text': segment[2].strip(),
                            'type': 'transcription_segment',
                            'source_start': segment[0],
                            'source_end': segment[1],
                            'transcription_file_path': source_transcription.transcription_file_path,
                            'source_file_path': source_transcription.audio_file_path,
                            'source_fps': source_transcription.timeline_fps,
                            'source_start_tc': source_transcription.timeline_start_tc,
                        })

                    if new_lines:
                        story_editor_window = self.get_window_by_id(story_editor_window_id)

                        toolkit_UI.StoryEdit.paste_to_story_editor(
                            window=story_editor_window, lines_to_paste=new_lines,
                            toolkit_UI_obj=self)

                        # save the story
                        toolkit_UI.StoryEdit.save_story(window_id=story_editor_window,
                                                        toolkit_UI_obj=self)

                def add_to_new_story():
                    if new_story_editor_window := self.open_new_story_editor_window():
                        add_to_story(story_editor_window_id=new_story_editor_window.window_id)

                # the "New Story" button
                add_to_story_menu.add_command(
                    label="New Story...",
                    command=add_to_new_story
                )
                add_to_story_menu.add_separator()

                story_editor_windows = self.get_all_windows_of_type('story_editor')

                for story_window_id in story_editor_windows:
                    story_editor_window = self.get_window_by_id(window_id=story_window_id)

                    add_to_story_menu.add_command(
                        label="{}".format(story_editor_window.title()),
                        command=lambda l_story_editor_window_id=story_window_id:
                        add_to_story(story_editor_window_id=l_story_editor_window_id)
                    )

                # add the add to transcription sub-menu
                context_menu.add_cascade(label="Add to Story", menu=add_to_story_menu)

                # add separator
                context_menu.add_separator()

                # add the text menu items
                context_menu.add_command(
                    label="Show text response",
                    command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                    show_transcription_text(l_base_tag, l_details_tag)
                )
                context_menu.add_command(
                    label="Show raw response",
                    command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                    show_raw_text(l_base_tag, l_details_tag)
                )

                # is there a details tag?
                if text_widget.tag_ranges(details_tag):
                    # then show the hide details option
                    context_menu.add_command(
                        label="Hide response",
                        command=lambda l_base_tag=clicked_tag_id, l_details_tag=details_tag:
                        hide_text(l_base_tag, l_details_tag)
                    )

                # display the context menu
                context_menu.tk_popup(event.x_root, event.y_root)

            # if we received this kind of response,
            # we must assume that we had transcription_segments when making the assistant query
            # we will use these to add the context menu to the response
            # so add them to the transcription segments to the context_menu_kwargs
            # this doesn't work if we have multiple transcriptions as sources
            context_transcription_segments = assistant_window.transcription_segments

            minify_and_add_response(
                response_string='Received Story',
                context_menu=story_context_menu,
                transcription_segments=context_transcription_segments
            )

            parsed = True

        elif response_type in ['transcription_json', 'story_json'] and 'lines' not in assistant_response_dict:
            logger.warning(
                'Cannot parse assistant response as "{}". Lines not found in response dict.'.format(response_type))

            # print(json.dumps(assistant_response_dict, indent=4))
            parsed = None

        else:
            logger.warning('Cannot parse assistant response. Unknown response type "{}".'.format(response_type))
            parsed = None

        # add the text widget line stuff
        if parsed:
            text_widget.insert('insert', '\n')

            # wait for a second
            self._text_window_update(assistant_window_id, text=' ')

        return parsed

    def destroy_assistant_window(self, assistant_window_id: str):
        """
        Destroys the assistant window
        """

        # also remove any settings window it might have
        settings_window_id = assistant_window_id + '_settings'
        if settings_window_id in self.windows:
            self.destroy_window_(window_id=settings_window_id)

        # destroy the assistant window
        self.destroy_text_window(assistant_window_id)

    # GENERAL FUNCTIONS

    def on_connect_resolve_api_press(self):

        # update menu references
        self.toolkit_ops_obj.resolve_enable()

        # now wait for resolve to connect
        while self.toolkit_ops_obj.resolve_api is None:
            time.sleep(0.01)

        # if the app config says that we should connect, ask the user if they still want that
        if self.toolkit_ops_obj.stAI.get_app_setting('disable_resolve_api', default_if_none=False) is True:

            # and ask the user if they want to always connect to Resolve API on startup
            always_connect = messagebox.askyesno(title='Always Connect?',
                                                 message='We\'re now connected to Resolve.\n\n'
                                                         'Do you want to always connect to the Resolve API '
                                                         'on tool startup?'
                                                 )

            time.sleep(0.1)

            if always_connect:
                self.toolkit_ops_obj.stAI.save_config('disable_resolve_api', False)

    def on_disable_resolve_api_press(self):

        # disable resolve api
        self.toolkit_ops_obj.resolve_disable()

        # if the app config says that we should connect, ask the user if they still want that
        if self.toolkit_ops_obj.stAI.get_app_setting('disable_resolve_api', default_if_none=False) is False:

            # and ask the user if they want to connect to Resolve API on startup
            always_connect = messagebox.askyesno(title='Connect back at startup?',
                                                 message='Resolve API connection disabled.\n\n'
                                                         'Do you want to still reconnect to the Resolve API at tool startup?'
                                                 )

            if not always_connect:
                self.toolkit_ops_obj.stAI.save_config('disable_resolve_api', True)

    def open_file_in_os(self, file_path):
        """
        Opens any file in the default program for the OS (works for Windows, Mac and Linux)
        :param file_path:
        :return:
        """

        # if the file exists
        if os.path.exists(file_path):
            # open the file in the default program
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', file_path], close_fds=True)
            else:
                try:
                    subprocess.Popen(['xdg-open', file_path])
                except OSError:
                    logger.error('Please open the file manually on your system: {}'.format(file_path))
        else:
            # otherwise, show an error
            messagebox.showerror('Error', 'File not found: {}'.format(file_path))

    def ask_for_target_dir(self, title=None, target_dir=None, **kwargs):

        # if an initial target dir was passed
        if target_dir is not None:
            # assign it as the initial_target_dir
            self.stAI.update_initial_target_dir(target_dir)

        # put the UI on top
        # self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog where can we find the directory
        title = "Where should we save the files?" if title is None else title

        target_dir = filedialog.askdirectory(title=title, initialdir=self.stAI.initial_target_dir)

        # what happens if the user cancels
        if not target_dir:
            return False

        # remember which directory the user selected for next time
        if isinstance(target_dir, str):
            self.stAI.update_initial_target_dir(target_dir)

        # use the first directory in the tuple
        elif isinstance(target_dir, tuple):
            self.stAI.update_initial_target_dir(target_dir[0])

        return target_dir

    def ask_for_file_or_dir_for_var(self, parent=None, var=None, **kwargs):
        """
        This function asks the user for files or a folder
        and then updates the variable passed to it with the file path(s)
        """

        # default to multiple files if not specified
        if 'multiple' not in kwargs:
            kwargs['multiple'] = True

        # ask the user for the target file
        if kwargs.get('select_dir', None) is None:
            target_path = self.ask_for_target_file(**kwargs)
        else:
            target_path = self.ask_for_target_dir(**kwargs)

            # turn it into a list, if it isn't already
            if isinstance(target_path, str):
                target_path = [target_path]

        # if the user canceled
        if not target_path:

            # re-focus on the parent window
            if parent is not None:
                self.focus_window(window=parent)

            return False

        if target_path:

            # take all the file paths and put them into a string separated by commas,
            # where each file path is wrapped in quotes

            # if there is only one file path
            if len(target_path) == 1:
                # we don't need the quotes
                target_path = target_path[0]

            else:
                # otherwise, we need to wrap each file path in quotes
                target_path = ', '.join(['"{}"'.format(f) for f in target_path])

            if var is None:
                # if no variable was passed, just return the file path(s)
                return target_path

            # if we have a tk variable, do this:
            # update the variable passed to this function with the file path(s)
            var.set(target_path)

            # re-focus on the parent window
            if parent is not None:
                self.focus_window(window=parent)

            # return the file path(s)
            return target_path

    def ask_for_target_file(self, filetypes=[("Audio files", ".mov .mp4 .wav .mp3")], target_dir=None, multiple=False,
                            **kwargs):

        # if an initial target_dir was passed
        if target_dir is not None:
            # assign it as the initial_target_dir
            self.stAI.update_initial_target_dir(target_dir)

        # put the UI on top
        # self.root.wm_attributes('-topmost', True)
        self.root.lift()

        # ask the user via os dialog which file to use
        if not multiple:
            target_file = filedialog.askopenfilename(title="Choose a file", initialdir=self.stAI.initial_target_dir,
                                                     filetypes=filetypes)
        else:
            target_file = filedialog.askopenfilenames(title="Choose the files", initialdir=self.stAI.initial_target_dir,
                                                      filetypes=filetypes)

        # what happens if the user cancels
        if not target_file:
            return False

        # remember what the user selected for next time
        self.stAI.update_initial_target_dir(
            os.path.dirname(target_file if isinstance(target_file, str) else target_file[0]))

        return target_file

    def ask_for_save_file(self, target_dir=None, **kwargs):

        # if an initial target_dir was passed
        if target_dir is not None:
            # assign it as the initial_target_dir
            self.stAI.update_initial_target_dir(target_dir)

        # put the UI on top
        # self.root.wm_attributes('-topmost', True)
        self.root.lift()

        if 'title' not in kwargs:
            kwargs['title'] = "Save file.."

        # ask the user via os dialog which file to use
        target_file = filedialog.asksaveasfilename(initialdir=self.stAI.initial_target_dir,
                                                   **kwargs)

        # what happens if the user cancels
        if not target_file:
            return False

        # remember what the user selected for next time
        self.stAI.update_initial_target_dir(os.path.dirname(target_file))

        return target_file

    def window_on_top(self, window_id=None, on_top=None):

        if window_id is not None:

            # does the window exist?
            if window_id in self.windows:

                # keep the window on top if on_top is true
                if on_top is not None and on_top:
                    self.windows[window_id].wm_attributes("-topmost", 1)
                    return True
                # don't keep the window on top if on top is false
                elif on_top is not None:
                    self.windows[window_id].wm_attributes("-topmost", 0)
                    return False
                # if the on top variable wasn't passed
                else:
                    # toggle between on and off
                    topmost = self.windows[window_id].wm_attributes("-topmost")
                    self.windows[window_id].wm_attributes("-topmost", not topmost)

                    # and return the current state
                    return self.windows[window_id].wm_attributes("-topmost")

    def get_window_on_top_state(self, window_id=None):

        if window_id is not None and window_id in self.windows:
            return self.windows[window_id].wm_attributes("-topmost")

    def window_on_top_button(self, button=None, window_id=None, on_top=None):

        # ask the UI to keep (or not) the window with this window_id on_top
        if self.window_on_top(window_id=window_id, on_top=on_top):

            # if the reply is true, it means that the window will be kept on top
            # therefore the button needs to read the opposite action
            button.config(text="Don't keep on top")
            return True
        else:
            # and the opposite if the window will not be kept on top
            button.config(text="Keep on top")
            return False

    def notify_via_os(self, title, text, debug_message):
        """
        Uses OS specific tools to notify the user

        :param title:
        :param text:
        :param debug_message:
        :return:
        """

        # log and print to console first
        logger.info(debug_message)

        # notify the user depending on which platform they're on
        try:
            if platform.system() == 'Darwin':  # macOS
                os.system("""
                                                        osascript -e 'display notification "{}" with title "{}"'
                                                        """.format(text, title))

            elif platform.system() == 'Windows':  # Windows
                return
            else:  # linux variants
                return
        except:
            logger.error("Cannot notify user via OS", exc_info=True)

    def notify_via_messagebox(self, type='info', message_log=None, message=None, **options):

        if message_log is None:
            message_log = message

        # alert the user using the messagebox according to the type
        # and log the message
        if type == 'error':
            messagebox.showerror(message=message, **options)
            logger.error(message_log)

        elif type == 'info':
            messagebox.showinfo(message=message, **options)
            logger.info(message_log)

        elif type == 'warning':
            messagebox.showwarning(message=message, **options)
            logger.warning(message_log)

        # if no type was passed, just log the message
        else:
            logger.debug(message_log)

    @staticmethod
    def sync_entry_with_slider(entry, slider, slider_from, slider_to, round_val=None):
        """ Synchronize the entry with the slider value. """
        try:
            value = float(entry.get())

            # first round the value to however decimals were required
            if round_val is not None and round_val > 0:
                value = round(value, round_val)
            elif round_val is not None and round_val == 0:
                value = round(value)

            if value < slider_from:
                value = slider_from

            elif value > slider_to:
                value = slider_to

            slider.set(value)

            entry.delete(0, tk.END)
            entry.insert(0, str(slider.get()))

        except ValueError:
            entry.delete(0, tk.END)
            entry.insert(0, str(slider.get()))

    @staticmethod
    def sync_slider_with_entry(slider, entry, round_val=None):
        """ Synchronize the slider with the entry value. """

        value = float(slider.get())

        # first round the value to however decimals were required
        if round_val is not None and round_val > 0:
            value = round(value, round_val)
        elif round_val is not None and round_val == 0:
            value = round(value)

        entry.delete(0, tk.END)
        entry.insert(0, str(value))

    @staticmethod
    def bind_sync_functions(entry, slider, slider_from, slider_to, round_val=None):
        entry.bind(
            "<Return>", lambda event: toolkit_UI.sync_entry_with_slider(entry, slider, slider_from, slider_to, round_val))
        entry.bind(
            "<FocusOut>", lambda event: toolkit_UI.sync_entry_with_slider(entry, slider, slider_from, slider_to, round_val))
        slider.configure(
            command=lambda value, l_round_val=round_val: toolkit_UI.sync_slider_with_entry(slider, entry, l_round_val))

    def copy_to_clipboard(self, full_text: str):

        self.root.clipboard_clear()
        self.root.clipboard_append(full_text.strip())

        logger.debug('Copied text to clipboard')



def run_gui(toolkit_ops_obj, stAI):
    # initialize GUI
    app_UI = toolkit_UI(toolkit_ops_obj=toolkit_ops_obj, stAI=stAI)

    # connect app UI to operations object
    toolkit_ops_obj.toolkit_UI_obj = app_UI

    # create the main window
    app_UI.create_main_window()
