#!/usr/bin/env python
# coding: utf-8

import time
from datetime import datetime
from python_get_resolve import GetResolve

import sys

import subprocess
import os
import platform
import json

from timecode import Timecode


def initialize_resolve():
    """
    Returns most of the necessary Resolve API objects that are needed to do most operations,
    it's a good common ground for initializing and handling the operations

    :return:
        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline]: dict

    """

    resolve = GetResolve()
    if resolve is None or not resolve:
        print("Resolve is not started. Exiting app.")
        sys.exit()
        # return False

    project = resolve.GetProjectManager().GetCurrentProject()

    if project is None or not project:
        print("No Resolve project is loaded. Exiting app.")
        sys.exit()
        # return False

    mediaPool = project.GetMediaPool()

    if mediaPool is None:
        print("Media Pool not available. Exiting app.")
        sys.exit()
        # return False

    if resolve:
        projectManager = resolve.GetProjectManager()

    if mediaPool:
        currentBin = mediaPool.GetCurrentFolder()

    if currentBin is None or not currentBin:
        print("Resolve bins not loaded.")

    # get timeline info
    if project:
        currentTimeline = project.GetCurrentTimeline()

    return [resolve, project, mediaPool, projectManager, currentBin, currentTimeline]


def get_resolve_data():
    """
    Returns resolve objects in a nicely formatted dict

    :return:
        resolve_data: dict
    """

    # initialize resolve objects
    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    resolve_data = {'currentProject': ''}

    # add project and bin to return dict
    resolve_data['currentProject'] = project.GetName()

    # available render presets
    resolve_data['renderPresets'] = project.GetRenderPresetList()


    if currentBin is not None and currentBin:
        resolve_data['currentBin'] = currentBin.GetName()

        #check bin clips
        clips = currentBin.GetClipList()

        if clips:
            binClips = {}
            for clip in clips:

                clip_name = clip.GetName()

                # ignore .srt files since the clip.GetClipProperty() call crashes Resolve
                if '.srt' not in clip_name:
                    binClips[clip.GetName()] = {'name': clip.GetName(), 'metadata': clip.GetMetadata(),
                                              'markers': clip.GetMarkers(), 'property': clip.GetClipProperty()
                                            }
                # add clips to return dict
                resolve_data['binClips'] = binClips

    else:
        resolve_data['currentBin'] = ''
        resolve_data['binClips'] = {}
    
    if currentTimeline and currentTimeline != None:

        # add timeline info to return dict
        resolve_data['currentTimeline'] = {'name': currentTimeline.GetName(), 'markers': currentTimeline.GetMarkers()}

        # add current timecode to return dict
        resolve_data['currentTC'] = currentTimeline.GetCurrentTimecode()

        # add the timeline frame rate to return dict
        resolve_data['currentTimelineFPS'] = currentTimeline.GetSetting('timelineFrameRate')

        #print(currentTimeline.GetSetting('timelineFrameRate'))

        #TODO: fix hack - for some reason 23.976 is no longer outputed by Resolve
        if resolve_data['currentTimelineFPS'] == '23':
            resolve_data['currentTimelineFPS'] = '24'

    return resolve_data



def set_resolve_tc(new_tc):
    """
    Moves the playhead to the requested timecode
    And returns either resolve objects or False if unsuccessful

    :param new_tc: timecode

    :return: resolve object or False

    """
    
    resolve = GetResolve()
    currentTimeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    
    if currentTimeline:
        currentTimeline.SetCurrentTimecode(new_tc) 
        
        return get_resolve_data()
    
    return False

# print(set_resolve_tc('01:03:20:01'))

def save_timeline_marker(timeline_name, marker_id, marker_data):
    """
    Saves a marker to the current timeline or simply deletes it if no marker_data['name'] was passed

    :param timeline_name:
    :param marker_id:
    :param marker_data:
    :return: the markers of the current timeline
    """
    
    resolve = GetResolve()
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


def copy_markers(source_type, destination_type, source_name, destination_name, delete_destination_markers):
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
    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    # initialize markers variable
    loaded_markers = {}

    # if the source is a timeline
    if source_type == 'timeline':

        # load the timeline markers (if it matches the source_name)
        if currentTimeline and currentTimeline is not None and currentTimeline.GetName() == source_name:
            loaded_markers = currentTimeline.GetMarkers()

    # if the source is a clip
    elif source_type == 'clip':

        # load the clip markers
        loaded_markers = get_clip_markers(source_name)

    else:
        print("Source type unknown")
        return False

    # if the destination is a timeline
    if destination_type == 'timeline':

        # add the timeline markers
        add_timeline_markers(destination_name, loaded_markers, delete_destination_markers)

        return True

    # if destination is a clip
    elif destination_type == 'clip':

        # add the clip markers
        add_clip_markers(destination_name, loaded_markers, delete_destination_markers)
        return True

    else:
        print("Destination type unknown")
        return False


def get_clip_markers(clip_name):
    """
    This gets the markers of a specific bin clip (by clip_name).
    The clip needs to be in the current bin. If the clip isn't found it will return False

    :param clip_name:
    :return:
    """

    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    # get the clips in the current bin
    if currentBin and currentBin is not None:
        clips = currentBin.GetClipList()

        # if there are clips in the bin
        if clips and clips is not None:

            # search for the clip with the right name
            for clip in clips:

                # if the clip was found
                if clip.GetName() == clip_name:
                    return clip.GetMarkers()

    #if it all fails
    return False

# print(get_clip_markers('AT 51 Caterina plays the piano copy'))


def add_clip_markers(clip_name, markers, delete_clip_markers):
    """
    Adds markers to a clip in the current bin. If the clip isn't found it will return False

    :param clip_name:
    :param markers: list with ['color', 'name', 'note', 'duration', ''customData] for each marker
    :param delete_clip_markers: if True it will delete the existing clip markers before adding the new ones
    :return:
    """

    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

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
                if delete_clip_markers == '1':
                    clip.DeleteMarkersByColor('All')

                # now copy all the markers to the clip
                for marker in markers:
                    clip.AddMarker(marker,
                                   markers[marker]['color'], markers[marker]['name'],
                                   markers[marker]['note'],
                                   markers[marker]['duration'], markers[marker]['customData'])
                return True

    return False

def add_timeline_markers(timeline_name, markers, delete_timeline_markers):

    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    # check if the timeline object exists and it matches the requested name
    if currentTimeline and currentTimeline is not None and currentTimeline.GetName() == timeline_name:

        # should we first delete its markers?
        if delete_timeline_markers == '1':
            currentTimeline.DeleteMarkersByColor('All')

        # now copy all the markers to the timeline
        for marker in markers:
            currentTimeline.AddMarker(marker,
                           markers[marker]['color'], markers[marker]['name'],
                           markers[marker]['note'],
                           markers[marker]['duration'], markers[marker]['customData'])

        return True


    return False

def import_media(file_path):

    # initialize resolve objects
    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    print(file_path)

    # import clip into current Media Folder
    if file_path and os.path.exists(file_path):
        mediaPoolItem = mediaPool.ImportMedia(file_path)
        return mediaPoolItem

    return False


def import_media_into_timeline(file_path):
    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    mediaPoolItem = import_media(file_path)

    print(mediaPoolItem)

    if mediaPoolItem:
        mediaPool.AppendToTimeline(mediaPoolItem)

    return False




#def import_media_into_timeline(file_path):
#    import_media(file_path)



DEFAULT_RENDER_PRESET = 'H.264 Master'

def render_markers(marker_color, target_dir, add_timestamp=False, stills=False, start_render=False, render_preset='h264_LQ3000', save_marker_data=False, marker_id=None):
    '''
        Adds the markers of a specific marker_color to the render queue
        and starts the render if start_render is True

        Parameters:
            marker_color: str
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
    '''

    #print('marker id', marker_id)

    #return

    resolve_objects = [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    # get the current page, so we can get back to it when we're done
    current_resolve_page = resolve.GetCurrentPage()

    # initialize markers variable
    loaded_markers = {}

    # load the timeline markers
    if currentTimeline and currentTimeline is not None:
        loaded_markers = currentTimeline.GetMarkers()

        # don't continue if we haven't found any markers
        if len(loaded_markers) < 1:
            print("No {} markers were found.".format(marker_color))
            return False

        # create render jobs array
        new_render_jobs = []

        # create a dict to hold the markers for the rendered jobs
        if save_marker_data:
            render_jobs_markers = {}

        # just in case the render preset is False
        if not render_preset:
            # default to a known one
            render_preset = DEFAULT_RENDER_PRESET

        # if we're rendering to stills, use the proper preset
        elif stills:
            render_preset = 'Still_TIFF'

        # get the available render presets
        available_render_presets = project.GetRenderPresetList()

        # check if the render preset is available in the project
        if render_preset in available_render_presets:
            # then use it
            project.LoadRenderPreset(render_preset)
        # or throw an error if it's not
        else:
            print("Selected render preset doesn't exist.")
            return False

        #print(loaded_markers)

        for marker in loaded_markers:

            if loaded_markers[marker]['color'] == marker_color and (loaded_markers[marker]['duration'] > 1 or stills):

                # create marker data for easier access
                marker_data = loaded_markers[marker]

                # reset render settings for this marker
                renderSettings = {}

                # get the correct timeline start frame
                startFrame = currentTimeline.GetStartFrame()

                # set the render in and out points according to the marker
                renderSettings["MarkIn"] = startFrame + marker
                renderSettings["MarkOut"] = startFrame + marker + int(marker_data['duration']) - 1

                # the render file name is givven by the marker name
                renderSettings["CustomName"] = marker_data["name"]

                # prepare timestamp for name and saved marker data
                render_timestamp = str(time.time()).split('.')[0]

                # add timestamp if required
                if add_timestamp:
                    renderSettings["CustomName"] = renderSettings['CustomName']+" "+render_timestamp

                # set the render dir
                renderSettings["TargetDir"] = target_dir

                #print("Queuing for render:")
                #print(renderSettings)

                project.SetRenderSettings(renderSettings)

                # replace all slashes and backslashes with an empty space in the file name
                renderSettings["CustomName"] = str(renderSettings["CustomName"]).replace("\\", " ").replace("/", " ")

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
                                                          'render_name': renderSettings["CustomName"],
                                                          'marker_name': marker_data["name"],
                                                          'in_offset': marker,
                                                          'duration': marker_data['duration'],
                                                          'fps': current_fps,
                                                          'render_timestamp': render_timestamp
                                                          }

                # print("Added render job " + render_job_id)
                # print(renderSettings)

        # return false if no new render jobs exist
        if not new_render_jobs:
            return False

        # start the render
        if start_render and new_render_jobs:
            render_status =  render(new_render_jobs, resolve_objects, stills,
                          render_jobs_markers if 'render_jobs_markers' in locals() else False
                          )

            # go back to the initial resolve page
            resolve.OpenPage(current_resolve_page)

            return render_status

        else:

            # go back to the initial resolve page
            resolve.OpenPage(current_resolve_page)
            return new_render_jobs

    print("Unable to get current Resolve timeline.")
    return False



def render_timeline(target_dir, render_preset='H.264 Master', start_render=False, add_file_suffix=False, add_date=False, add_timestamp=False):

    resolve_objects = [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

    # get the current page, so we can get back to it when we're done
    current_resolve_page = resolve.GetCurrentPage()

    # load the timeline
    if currentTimeline and currentTimeline is not None:

        # get the available render presets
        available_render_presets = project.GetRenderPresetList()

        # use the render preset that was passed
        if render_preset in available_render_presets:
            project.LoadRenderPreset(render_preset)
        # or throw an error if it doesn't exist in the presets list
        else:
            print("Selected render preset doesn't exist.")
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

        project.SetRenderSettings(renderSettings)

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
                                              'render_name': renderSettings["CustomName"],
                                              'in_offset': 0,
                                              'duration': int(renderSettings["MarkOut"]) - int(renderSettings["MarkIn"]),
                                              'fps': current_fps,
                                              'render_timestamp': render_timestamp
                                              }

        # start render if that was called
        if start_render:
            render_status = render([render_job_id], resolve_objects, False, render_data)

            # go back to the initial resolve page
            resolve.OpenPage(current_resolve_page)
            return render_status

        # otherwise just return the job id
        else:
            # go back to the initial resolve page
            resolve.OpenPage(current_resolve_page)
            return render_job_id

    else:
        print("Unable to get current Resolve timeline.")
        return False


def render(render_jobs=[], resolve_objects=False, stills=False, render_data={}):

    if not resolve_objects:
        [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()
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

                    # write the marker info in the file
                    with open(os.path.join(rendered_clip['TargetDir'], rendered_clip['OutputFilename'] + '.json'),
                              'w') as outfile:
                        json.dump(render_data[rendered_clip['JobId']], outfile)

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
            '''
            elif platform.system() == 'Windows':    # Windows
                os.startfile(filepath)
            else: # linux variants
                subprocess.call(('xdg-open', csvFile))
            '''

        # and return the rendered files
        return rendered_files

    print('No jobs were sent for render')
    return False


def offset_start_tc_bin_item(offset=0, tc_larger_than='00:00:00:00', update_slate=True):
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

    [resolve, project, mediaPool, projectManager, currentBin, currentTimeline] = initialize_resolve()

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

                print(clip.GetName())

                # only apply if the clip is video and audio
                if clip_properties['Type'] == 'Video + Audio' and initial_tc.frames-filter_tc.frames > 0:

                    #print(clip_properties['Start TC'])
                    #print(clip_properties['Slate TC'])
                    #print(clip_properties['FPS'])

                    # calculate the new timecode, based on the offset
                    offset_tc = initial_tc + offset

                    print("Current Start TC: "+str(initial_tc))
                    print("Updated to: "+ str(offset_tc))

                    # set the new start timecode
                    clip.SetClipProperty('Start TC', str(offset_tc))

                    # update the slate too if asked for (default is true)
                    if update_slate:
                        clip.SetClipProperty('Slate TC', str(offset_tc))

                else:
                    print('Not video+audio or Start TC lower than asked for. Skipping.')

    # if it all fails
    return False

if __name__ == '__main__':
    print("Hello")


    #offset_start_tc_bin_item(6) #<-- calculated for AT85
    #print("No call.")



    # -11 frames 08:39:20
    # +12 frames 09:16:40

