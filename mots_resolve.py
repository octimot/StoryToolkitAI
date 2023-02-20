#!/usr/bin/env python
# coding: utf-8

import time
from datetime import datetime

import sys

import subprocess
import os
import platform
import json

from timecode import Timecode

import logging

# this logger will not be used within MotsResolve class if a logger is passed on init
log_resolve = logging.getLogger('MotsResolve')

# add formatter to show the levelname and message in the log
log_resolve.setLevel(logging.INFO if '--debug' not in sys.argv else logging.DEBUG)
formatter = logging.Formatter("%(levelname)s: %(message)s (%(filename)s:%(lineno)d)")
# add the formatter to the handler
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log_resolve.addHandler(ch)


class MotsResolve:

    def __init__(self, logger=None):

        # use the logging object if one was passed
        self.logger = logger

        # if no logger was passed, use the default logger
        if logger is None:
            self.logger = log_resolve
            self.logger.warning("No logger was passed to the MotsResolve class, using default logger.")

        self.logger.debug("MotsResolve module initialized.")

        # initialize the main objects
        self.resolve \
            = self.project \
            = self.mediaPool \
            = self.projectManager \
            = self.currentBin \
            = self.currentTimeline \
            = None


        # keep track if the Resolve API module
        self.api_module_loaded = False

        # keep track if DaVinciResolveScript is not available on the machine
        # presume it is available - the get_resolve() function will update this next
        self.api_module_available = True

        # this is where we hold the fusionscript module
        self.bmd = None

        # initialize the Resolve API
        self.api = self.get_resolve()

    def get_resolve(self):
        '''
        This function is a modified copy of the GetResolve() function in python_get_resolve.py script from the DaVinci
        Resolve Scripting API. Let's hope that the below paths will not be changed by Blackmagic Design in the future.

        In case of errors, please check the original python_get_resolve.py that comes with the DaVinci Resolve.
        :return:
        '''

        # if the module wasn't loaded, try to load it
        if not self.api_module_loaded:

            self.logger.debug("Trying to load DaVinciResolveScript module...")

            try:
                # The PYTHONPATH needs to be set correctly for this import statement to work.
                # An alternative is to import the DaVinciResolveScript
                # by specifying absolute path (see ExceptionHandler logic)
                import DaVinciResolveScript as bmd

                self.bmd = bmd

                # remember that the API module was loaded
                self.api_module_available = True
                self.api_module_loaded = True

                self.logger.debug("DaVinciResolveScript module loaded from PYTHONPATH")

            except ImportError:

                # first try to find out if Davinci Resolve is installed at its default location

                # since the DaVinciResolveScript will use the path to the DaVinci Resolve application,
                # add that to the RESOLVE_SCRIPT_LIB environment variable
                import os

                # this is the default location for the DaVinci Resolve on Windows
                if platform.system() == 'Windows':
                   default_resolve_dir = 'C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\'
                   executable = 'Resolve.exe'

                # this is the default location for DaVinci Resolve on Mac
                elif platform.system() == 'Darwin':
                    default_resolve_dir = '/Applications/DaVinci Resolve/'
                    executable = 'DaVinci Resolve.app'

                # this is the default location for the DaVinci Resolve on Linux
                elif platform.system() == 'Linux':
                    default_resolve_dir = '/opt/resolve/'

                    # @todo find out the executable name for Davinci Resolve on Linux
                    executable = '/bin/resolve'

                else:
                    # check if the default path has it...
                    self.logger.error("Unable to determine default DaVinci Resolve path for this system "
                                      "(not Windows, Mac or Linux).")
                    self.api_module_available = False
                    return None

                # check if the resolve app is installed at the default location
                if not os.path.exists(os.path.join(default_resolve_dir, executable)):
                    self.logger.warning("DaVinci Resolve not installed at the default location: {}"
                                      .format(default_resolve_dir))

                    self.logger.warning("Resolve API connection disabled")

                    self.api_module_available = False
                    return None

                    #@todo find a way to get the path to the DaVinci Resolve application
                    # then add that to the RESOLVE_SCRIPT_LIB environment variable
                    # (see DaVinciResolveScript.py, because the paths might differ
                    # from the default location depending on system)
                    #os.environ['RESOLVE_SCRIPT_LIB'] = default_resolve_dir

                else:
                    self.logger.debug("Found DaVinci Resolve at the default location: {}".format(default_resolve_dir))

                if sys.platform.startswith("darwin"):
                    expectedPath = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/"
                elif sys.platform.startswith("win") or sys.platform.startswith("cygwin"):
                    import os
                    expectedPath = os.getenv(
                        'PROGRAMDATA') + "\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting\\Modules\\"
                elif sys.platform.startswith("linux"):
                    expectedPath = "/opt/resolve/libs/Fusion/Modules/"

                # check if the default path has it...
                self.logger.debug("Unable to find module DaVinciResolveScript from PYTHONPATH "
                                  "- trying default locations next")

                # check if the default path has it...
                try:
                    import imp
                    self.bmd = imp.load_source('DaVinciResolveScript', expectedPath + "DaVinciResolveScript.py")

                except (ImportError, FileNotFoundError):

                    # if the module is not available, return None and say that the module is not available
                    self.logger.error(
                        "Unable to find module DaVinciResolveScript.py")
                    self.logger.error(
                        "For a default DaVinci Resolve installation, the module is expected to be located in: " + expectedPath)
                    self.logger.error(
                        "Resolve API connection disabled")

                    self.api_module_available = False

                    return None

            self.logger.info('Resolve API module found and loaded')

        #if self.bmd is None:
        #    return None

        # return the API module
        return self.bmd.scriptapp("Resolve")



    def initialize_resolve(self, silent=False):
        """
        Returns most of the necessary Resolve API objects that are needed to do most operations,
        it's a good common ground for initializing and handling the operations
        :param:
            silent: bool When True, this will prevent the function from printing anything on the screen

        :return:
            [resolve, project, mediaPool, projectManager, currentBin, currentTimeline]: dict

        """

        # first initialize all the objects with None values
        # if any of the following get requests fails, these values will still be None
        resolve = project = mediaPool = projectManager = currentBin = currentTimeline = None

        # wrap this in a try/except block to catch any errors
        # Resolve might be closed in the middle of the operation and this will prevent the script from crashing
        try:

            # refresh the resolve object
            resolve = self.api = self.get_resolve()

            # get the project manager if resolve is opened
            if resolve is not None and resolve:
                # get the project manager
                projectManager = resolve.GetProjectManager()
            else:
                if not silent:
                    self.logger.debug("Resolve is not started.")

            # get the project if the project manager is opened
            if projectManager is not None and projectManager:
                # get the project
                project = projectManager.GetCurrentProject()

            # if a project is opened, get the media pool and the current timeline
            if project is not None and project:
                # get the media pool
                mediaPool = project.GetMediaPool()

                # get the timeline
                currentTimeline = project.GetCurrentTimeline()
            else:
                if not silent:
                    self.logger.debug("No Resolve project is loaded.")

            # get the current bin, if the media pool is available
            if mediaPool is not None:
                currentBin = mediaPool.GetCurrentFolder()
            else:
                if not silent:
                    self.logger.debug("Resolve Media Pool not available.")

            if currentTimeline is None or not currentTimeline:
                if not silent:
                    self.logger.debug("Resolve Timeline not loaded or unavailable.")

            if currentBin is None or not currentBin:
                if not silent:
                    self.logger.debug("Resolve Bins not loaded or unavailable.")

            # store all the object in the class
            self.resolve = resolve
            self.project = project
            self.mediaPool = mediaPool
            self.projectManager = projectManager
            self.currentBin = currentBin
            self.currentTimeline = currentTimeline

        # in case of any exception, it means that Resolve API is no longer responding
        # so, clear the objects
        except Exception as e:
            self.logger.debug("Resolve API exception: {}".format(e))

        return [self.resolve, self.project, self.mediaPool, self.projectManager, self.currentBin, self.currentTimeline]

    def clear_resolve(self):
        '''
        Clears all the Resolve API objects from the class
        :return:
        '''

        # clear all the data
        self.resolve = None
        self.project = None
        self.mediaPool = None
        self.projectManager = None
        self.currentBin = None
        self.currentTimeline = None

        return [self.resolve, self.project, self.mediaPool, self.projectManager, self.currentBin, self.currentTimeline]

    def get_resolve_data(self, silent=False):
        """
        Returns resolve objects in a nicely formatted dict

        :return:
            resolve_data: dict
        """

        # initialize resolve objects

        resolve_init = [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] \
            = self.initialize_resolve(silent=silent)

        resolve_data = {'currentProject': ''}

        # wrap this in a try/except block to catch any errors
        # Resolve might be closed in the middle of the operation and this will prevent the script from crashing
        try:

            # add resolve object to return dict
            resolve_data['resolve'] = resolve

            if project is not None:
                # add project name
                resolve_data['currentProject'] = project.GetName()

                # add available render presets
                resolve_data['renderPresets'] = project.GetRenderPresetList()
            else:
                resolve_data['currentProject'] = resolve_data['renderPresets'] = None


            # the current bin and the bin clips
            resolve_data['currentBin'] = None
            resolve_data['binClips'] = None
            if currentBin is not None and currentBin:

                # get the name of the current bin
                resolve_data['currentBin'] = currentBin.GetName()

                #check bin clips
                clips = currentBin.GetClipList()

                if clips:
                    binClips = {}
                    for clip in clips:

                        clip_name = clip.GetName()

                        # ignore .srt files since the clip.GetClipProperty() call crashes Resolve
                        if clip_name is not None and '.srt' not in clip_name:
                            binClips[clip.GetName()] = {'name': clip.GetName(), 'metadata': clip.GetMetadata(),
                                                      'markers': clip.GetMarkers(), 'property': clip.GetClipProperty()
                                                    }
                        # add clips to return dict
                        resolve_data['binClips'] = binClips

            resolve_data['currentTimeline'] = resolve_data['currentTC'] = resolve_data['currentTimelineFPS'] = None
            if currentTimeline and currentTimeline != None:

                # add timeline info to return dict
                resolve_data['currentTimeline'] = {'name': currentTimeline.GetName(),
                                                   'markers': currentTimeline.GetMarkers(),
                                                   'startTC': currentTimeline.GetStartTimecode(),
                                                   'uid': currentTimeline.GetUniqueId()
                                                   }

                # add current timecode to return dict
                resolve_data['currentTC'] = currentTimeline.GetCurrentTimecode()

                # add the timeline frame rate to return dict
                resolve_data['currentTimelineFPS'] = currentTimeline.GetSetting('timelineFrameRate')

                #self.logger.debug(currentTimeline.GetSetting('timelineFrameRate'))

                #@TODO: fix hack - for some reason 23.976 is no longer outputed by Resolve
                if resolve_data['currentTimelineFPS'] == '23':
                    resolve_data['currentTimelineFPS'] = '24'

        # in case of any exception, it means that Resolve API is no longer responding
        # so, clear the objects
        except Exception as e:
            self.logger.debug("Resolve API exception: {}".format(e))
            self.clear_resolve()

        return resolve_data



    def set_resolve_tc(self, new_tc):
        """
        Moves the playhead to the requested timecode
        And returns either resolve objects or False if unsuccessful

        :param new_tc: timecode

        :return: resolve object or False

        """

        # @todo: move this out
        resolve = self.api = self.get_resolve()

        if resolve is None or not resolve:
            return False

        currentTimeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()

        if currentTimeline is None or not currentTimeline:
            return False

        # take the playhead to new_tc timecode
        if currentTimeline:
            currentTimeline.SetCurrentTimecode(new_tc)

            return self.get_resolve_data()

        return False

    def save_timeline_marker(self, timeline_name, marker_id, marker_data):
        """
        Saves a marker to the current timeline or simply deletes it if no marker_data['name'] was passed

        :param timeline_name:
        :param marker_id:
        :param marker_data:
        :return: the markers of the current timeline
        """

        #@ todo move this
        resolve = self.api = self.get_resolve()
        currentTimeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()

        # make sure we're on the right timeline
        currentTimeline_name = currentTimeline.GetName()
        if timeline_name and marker_id != '' and currentTimeline_name and timeline_name == currentTimeline.GetName():

            # make sure we're passing everything even if it's empty
            empty_marker_data = {'color': '', 'name': '', 'note': '', 'duration': 1}

            # merge the marker data into the empty data
            marker_data = {**empty_marker_data, **marker_data}

            # delete marker at frame first (if there is any)
            currentTimeline.DeleteMarkerAtFrame(float(marker_id))

            # send marker to resolve - like this, if the name == '', the marker will not be added
            currentTimeline.AddMarker(float(marker_id), marker_data['color'], marker_data['name'], marker_data['note'], float(marker_data['duration']))

        return currentTimeline.GetMarkers()

    # save_timeline_marker('AT 51 Caterina plays the piano2', 10455, \
    #                       {'color': 'Blue', 'name': 'Marker 8 test', 'note': '', 'duration': '1'}


    def copy_markers(self, source_type, destination_type, source_name, destination_name, delete_destination_markers):
        """
        Copies markers between timelines and bin clips.
        In order for this to work, the user has to have the bin and the timline open in Resolve otherwise it will not work
        due to API limitations

        :param source_type:
        :param destination_type:
        :param source_name:
        :param destination_name:
        :param delete_destination_markers:
        :return:
        """

        # initialize resolve objects
        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        # initialize markers variable
        loaded_markers = {}

        # if the source is a timeline
        if source_type == 'timeline':

            # load the timeline markers (if it matches the source_name)
            if currentTimeline and currentTimeline is not None and currentTimeline.GetName() == source_name:
                loaded_markers = currentTimeline.GetMarkers()

                if not loaded_markers:
                    self.logger.warning('Timeline {} does not have any markers'.format(source_name))
                    return False

            else:
                self.logger.eror('Timeline {} not found'.format(source_name))

        # if the source is a clip
        elif source_type == 'clip':

            # then load the clip markers
            loaded_markers = self.get_clip_markers(source_name)

            if loaded_markers is None:
                self.logger.error('Source clip {} not found in current bin'.format(source_name))
                return False

            if not loaded_markers:
                self.logger.warning('Source clip {} does not have any markers'.format(source_name))
                return False

        else:
            self.logger.error("Source clip type unknown")
            return False

        # if the destination is a timeline
        if destination_type == 'timeline':

            self.logger.info("Copying markers from {} {} to timeline".format(source_name, source_type))

            # add the timeline markers
            self.add_timeline_markers(destination_name, loaded_markers, delete_destination_markers)

            return True

        # if destination is a clip
        elif destination_type == 'clip':

            # does the clip exist in the current bin?
            if self.get_clip_markers(destination_name) is None:
                self.logger.error('Destination clip {} not found in current bin'.format(destination_name))
                return False

            self.logger.info("Copying markers from {} {} to clip".format(source_name, source_type))

            # add the clip markers
            self.add_clip_markers(destination_name, loaded_markers, delete_destination_markers)
            return True

        else:
            self.logger.error("Destination clip type unknown")
            return False


    def get_clip_markers(self, clip_name):
        """
        This gets the markers of a specific bin clip (by clip_name).
        The clip needs to be in the current bin. If the clip isn't found it will return False

        :param clip_name:
        :return:
        """

        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        # get the clips in the current bin
        if currentBin and currentBin is not None:
            clips = currentBin.GetClipList()

            # if there are clips in the bin
            if clips and clips is not None:

                # search for the clip with the right name
                for clip in clips:

                    # if the clip was found
                    if clip.GetName() == clip_name:

                        # this will return either the markers or False
                        return clip.GetMarkers()

        #if it all fails
        return None


    def add_clip_markers(self, clip_name, markers, delete_clip_markers):
        """
        Adds markers to a clip in the current bin. If the clip isn't found it will return False

        :param clip_name:
        :param markers: list with ['color', 'name', 'note', 'duration', ''customData] for each marker
        :param delete_clip_markers: if True it will delete the existing clip markers before adding the new ones
        :return:
        """

        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        clips = None

        # get the clips in the current bin
        if currentBin and currentBin is not None:
            clips = currentBin.GetClipList()

        # if there are clips in the bin
        if clips and clips is not None:

            # search for the clip with the right name
            for clip in clips:

                # if the clip was found
                if clip.GetName() == clip_name:

                    # should we first delete its markers?
                    if delete_clip_markers == True:
                        clip.DeleteMarkersByColor('All')

                    # now copy all the markers to the clip
                    for marker in markers:
                        clip.AddMarker(marker,
                                       markers[marker]['color'], markers[marker]['name'],
                                       markers[marker]['note'],
                                       markers[marker]['duration'], markers[marker]['customData'])
                    return True

        return False

    def add_timeline_markers(self, timeline_name, markers, delete_timeline_markers):

        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        # check if the timeline object exists and it matches the requested name
        if currentTimeline and currentTimeline is not None and currentTimeline.GetName() == timeline_name:

            # should we first delete its markers?
            if delete_timeline_markers == True:
                currentTimeline.DeleteMarkersByColor('All')

            # now copy all the markers to the timeline
            for marker in markers:
                currentTimeline.AddMarker(marker,
                               markers[marker]['color'], markers[marker]['name'],
                               markers[marker]['note'],
                               markers[marker]['duration'], markers[marker]['customData'])

            return True


        return False

    def import_media(self, file_path):

        # initialize resolve objects
        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        self.logger.debug('Importing {} into media pool: '.format(file_path))

        # import clip into current Media Folder
        if file_path and os.path.exists(file_path):
            mediaPoolItem = mediaPool.ImportMedia(file_path)
            return mediaPoolItem

        return False


    def import_media_into_timeline(self, file_path):
        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        mediaPoolItem = self.import_media(file_path)

        self.logger.debug('Importing {} into timeline'.format(mediaPoolItem))

        if mediaPoolItem:
            mediaPool.AppendToTimeline(mediaPoolItem)

        return False


    # This will be the render preset that the script will choose in case nothing was passed during the call
    # H.264 Master should be available in any new Resolve installation, it's in QuickTime format and uses H.264 as codec
    DEFAULT_RENDER_PRESET = 'H.264 Master'

    # These are render settings for presets we use and are not in Resolve
    # use 'BasePreset' if you want to load a preset that is predefined in Resolve and then modify that
    # use 'SaveAfterLoad' if you want to save the preset after loading it in Resolve
    MOTS_RENDER_PRESET_SETTINGS = {'Still_TIFF':
                                       {'SaveAfterLoad': True, 'ExportVideo': True, 'ExportAudio': False},
                                   'transcription_WAV':
                                       {'BasePreset': 'Audio Only', 'ExportVideo': False, 'ExportAudio': True, 'AudioCodec': 'LinearPCM'},
                                   }

    # Resolve API uses a different call to get the render format and codec, so we'll store them separately
    MOTS_RENDER_PRESET_FORMAT_CODEC = {'Still_TIFF':
                                           {'format': 'tif', 'codec': 'RGB16LZW'},
                                       'transcription_WAV':
                                           {},
                                       }

    RESOLVE_MARKER_COLORS = ["Blue", "Cyan", "Green", "Yellow", "Red", "Pink",
                             "Purple", "Fuchsia", "Rose", "Lavender", "Sky",
                             "Mint", "Lemon", "Sand", "Cocoa", "Cream"]

    def render_markers(self, marker_color, target_dir, add_timestamp=False, stills=False, start_render=False,
                       render_preset='h264_LQ3000', save_marker_data=False, marker_id=None, starts_with=None):
        '''
            Adds the markers of a specific marker_color to the render queue
            and starts the render if start_render is True

            Parameters:
                marker_color: str or None
                    The colors of the markers
                target_dir: str
                    Where to render
                add_timestamp: bool
                    Adds a timestamp at the end of the rendered file name
                stills: bool
                    Renders to TIFF and then converts them to JPEG. This only works if start_render is also True
                start_render: bool
                    Should we start the render too (True), or are we just adding jobs to the render queue (False)?
                render_preset: str
                    Which render preset to be used. This is ignored if stills is True.
                save_marker_data: bool,str
                    Saves some info about the marker next to the rendered file in a json format. This will not work if we start_render is False
                starts_with: str
                    Only render markers that start with this string (if this is passed marker_color can be None)
        '''

        resolve_objects = [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        # get the current page, so we can get back to it when we're done
        current_resolve_page = resolve.GetCurrentPage()

        # initialize markers variable
        loaded_markers = {}

        if marker_color is None and starts_with is None:
            self.logger.debug("No marker color or starts_with string was passed. Exiting.")
            return False

        # load the timeline markers
        if currentTimeline and currentTimeline is not None:
            loaded_markers = currentTimeline.GetMarkers()

            # don't continue if we haven't found any markers
            if len(loaded_markers) < 1:
                self.logger.debug("No {} markers were found.".format(marker_color))
                return False

            # create render jobs array
            new_render_jobs = []

            # create a dict to hold the markers for the rendered jobs
            # this will be used to save the marker data next to the rendered file if save_marker_data is True
            render_jobs_markers = {}

            # just in case the render preset is False
            if not render_preset:
                # default to a known one
                render_preset = self.DEFAULT_RENDER_PRESET

            # if we're rendering to stills, use the proper preset
            # the Still_TIFF is a video only render preset with the following settings:
            #  - Format: TIFF
            #  - Codec RGB 16bits (LZW Compression)
            elif stills:
                render_preset = 'Still_TIFF'

            # try to select the passed render preset
            # we're only setting this once for all the renders jobs in this function
            if not self.select_render_preset(render_preset, project):
                return False

            for marker in loaded_markers:

                # assuming that we can't have both marker_color and starts_with set to None
                # (due to above check), do the following checks

                # if this is not passing the color filter, skip it (if the marker color was mentioned)
                if marker_color is not None and loaded_markers[marker]['color'] != marker_color:
                    continue

                # if this is not passing the starts_with filter, skip it (if the starts_with string was mentioned)
                if starts_with is not None and not loaded_markers[marker]['name'].startswith(starts_with):
                    continue

                # if this is not a still and the duration is 1, skip it
                if loaded_markers[marker]['duration'] == 1 and not stills:
                    continue

                # create marker data for easier access
                marker_data = loaded_markers[marker]

                # reset render settings for this marker
                renderSettings = {}

                # get the correct timeline start frame
                startFrame = currentTimeline.GetStartFrame()

                # set the render in and out points according to the marker
                renderSettings["MarkIn"] = startFrame + marker
                renderSettings["MarkOut"] = startFrame + marker + int(marker_data['duration']) - 1

                # only render the first frame if we're in stills mode
                if stills:
                    renderSettings["MarkOut"] = startFrame + marker + 0

                # the render file name is givven by the marker name
                renderSettings["CustomName"] = marker_data["name"]

                # prepare timestamp for name and saved marker data
                render_timestamp = str(time.time()).split('.')[0]

                # add timestamp if required
                if add_timestamp:
                    renderSettings["CustomName"] = renderSettings['CustomName']+" "+render_timestamp

                # set the render dir
                renderSettings["TargetDir"] = target_dir

                project.SetRenderSettings(renderSettings)

                # replace all slashes and backslashes with an empty space in the file name
                renderSettings["CustomName"] = str(renderSettings["CustomName"]).replace("\\", " ").replace("/", " ")

                self.logger.debug('Adding marker {} render job'.format(marker))

                # append the render job id to the new_render_jobs
                render_job_id = project.AddRenderJob()

                new_render_jobs.append(render_job_id)

                # remember the markers associated with the job
                # we are storing the in_offset and the duration in frames, just as it is in the marker data
                #  so we will need to convert that into seconds whenever we need to
                if save_marker_data:

                    # get the timeline FPS
                    current_fps = currentTimeline.GetSetting('timelineFrameRate')

                    # round up for the non-dropframe 23.976fps - this is a hack, since resolve rounds up due to bug
                    if int(current_fps) >= 23.97 and int(current_fps) <= 24:
                        current_fps = "24"

                    render_jobs_markers[render_job_id] = {'project_name': project.GetName(),
                                                          'timeline_name': currentTimeline.GetName(),
                                                          'timeline_start_tc': currentTimeline.GetStartTimecode(),
                                                          'render_name': renderSettings["CustomName"],
                                                          'marker_name': marker_data["name"],
                                                          'in_offset': marker,
                                                          'duration': marker_data['duration'],
                                                          'fps': current_fps,
                                                          'render_timestamp': render_timestamp
                                                          }

                self.logger.debug("Added render job {} from marker {}".format(render_job_id, marker))
                self.logger.debug("Render settings: {}".format(renderSettings))

            # return false if no new render jobs exist
            if not new_render_jobs:
                return False

            # start the render
            if start_render and new_render_jobs:

                self.logger.debug('Starting render')
                render_status =  self.render(new_render_jobs, resolve_objects, stills,
                              render_jobs_markers if 'render_jobs_markers' in locals() else False
                              )

                # go back to the initial resolve page
                resolve.OpenPage(current_resolve_page)

                return render_status

            else:

                self.logger.info("Render jobs added to queue. Waiting for user to start render in Resolve.")

                # go back to the initial resolve page
                resolve.OpenPage(current_resolve_page)
                return new_render_jobs

        self.logger.error("Unable to get current Resolve timeline.")
        return False

    def select_render_preset(self, render_preset, project) -> bool:
        '''

        Selects a render preset that is available either in Resolve or predefined in this class.

        If the preset is not found, it will return False

        :param render_preset:
        :param project:
        :return: bool
        '''

        # get the available render presets
        available_render_presets = project.GetRenderPresetList()

        # use the render preset that was passed
        # if it's in the available render presets, use it
        if render_preset in available_render_presets:
            self.logger.debug('Found render preset {} in available presets list in Resolve'.format(render_preset))

            project.LoadRenderPreset(render_preset)

            return True

        # if it's not in the available render presets in Resolve,
        # check if it's in the mots_resolve settings
        elif render_preset in self.MOTS_RENDER_PRESET_SETTINGS \
                and render_preset in self.MOTS_RENDER_PRESET_FORMAT_CODEC:

            self.logger.debug('Found render preset {} in mots_resolve settings'.format(render_preset))

            save_after_load = False

            # should we save the render preset?
            if 'SaveAfterLoad' in self.MOTS_RENDER_PRESET_SETTINGS[render_preset]:
                save_after_load = True

                del self.MOTS_RENDER_PRESET_SETTINGS[render_preset]['SaveAfterLoad']

            # so now try to load it

            # first, if there's a base preset, load that first
            # (assuming it's in the available presets, if it's not Resolve might crash!)
            if 'BasePreset' in self.MOTS_RENDER_PRESET_SETTINGS[render_preset]:
                self.logger.debug('Loading base preset {}'
                      .format(self.MOTS_RENDER_PRESET_SETTINGS[render_preset]['BasePreset']))

                # load the base preset
                project.LoadRenderPreset(self.MOTS_RENDER_PRESET_SETTINGS[render_preset]['BasePreset'])

                # remove this from the settings, so we don't pass it to the SetRenderSettings function
                del self.MOTS_RENDER_PRESET_SETTINGS[render_preset]['BasePreset']

            # now load the render format and codec
            # if they were set in the settings
            if 'format' in self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset] \
                    and 'codec' in self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset]:
                self.logger.debug('Setting render format and codec to {} and {}'.format(
                    self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset]['format'],
                    self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset]['codec']
                ))

                project.SetCurrentRenderFormatAndCodec(
                    self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset]['format'],
                    self.MOTS_RENDER_PRESET_FORMAT_CODEC[render_preset]['codec'])

            self.logger.debug('Setting other preset related render settings: {}'
                  .format(self.MOTS_RENDER_PRESET_SETTINGS[render_preset]))

            # now load the other render settings related to the preset
            project.SetRenderSettings(self.MOTS_RENDER_PRESET_SETTINGS[render_preset])

            # save the render preset if we should
            if save_after_load:
                self.logger.info('Saving render preset {}'.format(render_preset))
                project.SaveAsNewRenderPreset(render_preset)

            return True

        # or try to find it in the mots_resolve settings
        else:
            self.logger.debug("Selected render preset {} not available in Resolve nor in mots_resolve settings."
                  .format(render_preset))
            return False

    def render_timeline(self, target_dir, render_preset='H.264 Master', start_render=False,
                        add_file_suffix=False, add_date=False, add_timestamp=False):
        '''
        Renders the timeline that is currently open in Resolve.

        :param target_dir: Where to save the rendered file.
        :param render_preset: Either a render preset available in Resolve or a preset that is defined in this class.
        :param start_render: This also starts the render after the render job has been added to the queue in Resolve
        :param add_file_suffix:
        :param add_date:
        :param add_timestamp:
        :return:
        '''

        resolve_objects = [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] \
            = self.initialize_resolve()

        # get the current page, so we can get back to it when we're done
        current_resolve_page = resolve.GetCurrentPage()

        # load the timeline
        if currentTimeline and currentTimeline is not None:

            # select the right render preset
            # and return False if it's not available
            if not self.select_render_preset(render_preset, project):
                return False

            # reset render settings for this marker
            renderSettings = {}

            # set the render in and out points according to the timeline
            renderSettings["MarkIn"] = currentTimeline.GetStartFrame()
            renderSettings["MarkOut"] = currentTimeline.GetEndFrame()

            # the render file name is given by the timeline name
            renderSettings["CustomName"] = currentTimeline.GetName()

            # add file suffix if requested
            if add_file_suffix and add_file_suffix != '':
                renderSettings["CustomName"] = renderSettings["CustomName"] + " " + str(add_file_suffix)

            # if add date was passed, use it to format the date
            # and add it at the end of the file name
            if add_date:
                #try:
                now = datetime.now()
                renderSettings["CustomName"] = renderSettings["CustomName"] + " " + now.strftime(add_date)
                #except:
                #    print("Wrong date format was passed. Use %Y %m %d for eg. or see python date formatting.")
                #    return False

            render_timestamp = str(time.time()).split('.')[0]
            # add timestamp to the name if required
            if add_timestamp:
                renderSettings["CustomName"] = renderSettings['CustomName'] + " " + render_timestamp

            # set the render dir
            renderSettings["TargetDir"] = target_dir

            # replace all slashes and backslashes with an empty space in the file name
            renderSettings["CustomName"] = str(renderSettings["CustomName"]).replace("\\", " ").replace("/", " ")

            self.logger.debug('Setting render settings: {}'.format(renderSettings))
            project.SetRenderSettings(renderSettings)

            self.logger.debug('Adding render job to queue')
            # append the render job id to the new_render_jobs
            render_job_id = project.AddRenderJob()

            # get the timeline FPS
            current_fps = currentTimeline.GetSetting('timelineFrameRate')

            # round up for the non-dropframe 23.976fps - this is a hack, since resolve rounds up due to bug
            if int(current_fps) >= 23.97 and int(current_fps) <= 24:
                current_fps = "24"

            # prepare the render data to pass to the file
            # this will not be used if we don't start the render here
            render_data = {}
            render_data[render_job_id] = {'project_name': project.GetName(),
                                          'timeline_name': currentTimeline.GetName(),
                                          'timeline_start_tc': currentTimeline.GetStartTimecode(),
                                          'render_name': renderSettings["CustomName"],
                                          'in_offset': 0,
                                          'duration': int(renderSettings["MarkOut"]) - int(renderSettings["MarkIn"]),
                                          'fps': current_fps,
                                          'render_timestamp': render_timestamp
                                          }

            # start render if that was called
            if start_render:
                self.logger.info("Starting render")
                render_status = self.render([render_job_id], resolve_objects, False, render_data)

                # go back to the initial resolve page
                resolve.OpenPage(current_resolve_page)
                return render_status

            # otherwise just return the job id
            else:
                self.logger.info("Render jobs added to queue. Waiting for user to start render in Resolve.")

                # go back to the initial resolve page
                resolve.OpenPage(current_resolve_page)
                return render_job_id

        else:
            self.logger.error("Unable to get current Resolve timeline")
            return False


    def render(self, render_jobs=[], resolve_objects=False, stills=False, render_data={}):

        if not resolve_objects:
            [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()
        else:
            [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = resolve_objects

        # if render was asked and we've added new render jobs
        if render_jobs:

            # start the render and wait until it finishes
            project.StartRendering(render_jobs)
            while project.IsRenderingInProgress():
                time.sleep(1)

            # after Resolve finished rendering
            rendered_files = []

            # check which jobs have rendered and add them to the list
            for rendered_clip in project.GetRenderJobList():

                # we're only interested in the jobs that were added by this function
                if rendered_clip['JobId'] in render_jobs:

                    # add the rendered jobs to the dict
                    rendered_files.append(rendered_clip['TargetDir'] + "/" + rendered_clip['OutputFilename'])

                    # print("Added " + rendered_clip['TargetDir'] + "/" + rendered_clip[
                    #    'OutputFilename'] + " to the rendered files list")

                    # if requested, also save some data next to the rendered file
                    if render_data and len(render_data) > 0:
                        # print(render_jobs_markers[rendered_clip['JobId']])

                        # write the render info in the file
                        with open(os.path.join(rendered_clip['TargetDir'], rendered_clip['OutputFilename'] + '.json'),
                                  'w') as outfile:
                            json.dump(render_data[rendered_clip['JobId']], outfile, indent=4)

            # convert rendered TIFFs to JPEG
            if stills:

                # process for MacOS
                if platform.system() == 'Darwin':  # macOS

                    # convert using ffmpeg in macOS
                    for rendered_clip in rendered_files:
                        # subprocess.call(['ffmpeg', '-y', '-i', rendered_clip, rendered_clip + ".jpg"])
                        result = subprocess.run(
                            ['ffmpeg', '-y', '-i', rendered_clip, '-qmin', '1', '-qscale:v', '1', rendered_clip + ".jpg"],
                            capture_output=True)

                        # save log next to the rendered file
                        # if result.returncode:
                        #    print(str(result))

                        # with open(rendered_clip+'.txt', 'w') as f:
                        #    f.write(str(result))
                        #    f.close()

                    def notify(title, text):
                        os.system("""
                                                                osascript -e 'display notification "{}" with title "{}"'
                                                                """.format(text, title))

                    # when done notify via mac os notifications
                    notify("Stills Rendered", "Stills based on Markers exported to JPEG.")

                # TODO - tiff conversion on other platforms
                # since ffmpeg is required, we should pass the conversion to it
                '''
                elif platform.system() == 'Windows':    # Windows
                    os.startfile(filepath)
                else: # linux variants
                    subprocess.call(('xdg-open', csvFile))
                '''

            # and return the rendered files
            return rendered_files

        self.logger.warning('No jobs were sent for render')
        return False


    def offset_start_tc_bin_item(self, offset=0, tc_larger_than='00:00:00:00', update_slate=True):
        """
        Batch offsets the start timecode of the videos in the current bin.

        For eg. offset_start_tc_bin_item(10) will offset the start timecode of all videos in current bin by 10 frames

        You can also offset only the timecodes of videos that start past a certain timecode, for eg:
        offset_start_tc_bin_item(20, '15:20:30:20') only offset the videos with the start timecode past 15:20:30:20
        this is useful if the timecode on the video recording has drifted after a certain clip

        The third update_slate parameter makes sure that the Slate TC is also updated, but could be bypassed if necessary

        :param offset: offset amount in frames
        :param tc_larger_than: only offset clips past this timecode
        :param update_slate: should it update the Slate TC aswell?
        :return:
        """

        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = self.initialize_resolve()

        # get the clips in the current bin
        if currentBin and currentBin is not None:
            clips = currentBin.GetClipList()

            # if there are clips in the bin
            if clips and clips is not None:

                # search for the clip with the right name
                for clip in clips:

                    # get the clip properties
                    clip_properties = clip.GetClipProperty()

                    # set the initial timecode into a timecode object
                    initial_tc = Timecode(clip_properties['FPS'], clip_properties['Start TC'])

                    filter_tc = Timecode(clip_properties['FPS'], tc_larger_than)

                    self.logger.info('Offsetting clip {}'.format(clip.GetName()))

                    # only apply if the clip is video and audio
                    if clip_properties['Type'] == 'Video + Audio' and initial_tc.frames-filter_tc.frames > 0:

                        #print(clip_properties['Start TC'])
                        #print(clip_properties['Slate TC'])
                        #print(clip_properties['FPS'])

                        # calculate the new timecode, based on the offset
                        offset_tc = initial_tc + offset

                        self.logger.info(" - Current Start TC: "+str(initial_tc))
                        self.logger.info(" - Updated to: "+ str(offset_tc))

                        # set the new start timecode
                        clip.SetClipProperty('Start TC', str(offset_tc))

                        # update the slate too if asked for (default is true)
                        if update_slate:
                            clip.SetClipProperty('Slate TC', str(offset_tc))

                    else:
                        self.logger.info('Skipping clip {} (not video+audio or Start TC is lower needed)'
                              .format(clip.GetName()))

        # if it all fails
        return False

if __name__ == '__main__':

    print('Mots Resolve API needs to be called from another script.')

