import os.path

import tqdm

import math
import numpy as np
import cv2
from PIL import Image
from patchify import patchify
import torch
import clip
import json

from collections import defaultdict

from storytoolkitai.core.logger import logger


class ClipIndex:

    __version__ = '0.1'

    def __init__(self, base_resolution=720, patch_divider=2, device=None, clip_model_name='RN50x4', **kwargs):
        """
        :param patch_size: size of the patches to use for indexing
        :param device: device to use for CLIP model
        """

        # these need to be calculated before starting the indexing
        self._base_resolution = self._height = self._width = base_resolution

        self._patch_size = self._patch_step = self._patch_shape = None

        self.device = device

        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.clip_model_name = clip_model_name
        self.clip_model = self.clip_prep = None

        # this will contain all the image features for our video in a tensor
        self.video_encoded = None

        # this will hold the metadata for every image feature held in video_encoded
        self.video_frames = []

        # this will hold other metadata (like fps etc.) for the video
        self.video_other_metadata = []

        self._video_fps = None

        # this will hold the frame indexes at which shot changes occur
        self.shot_changes = []

        self.source_path = None

    @property
    def video_fps(self):
        return self._video_fps

    def calculate_patch_dims(self):

        # calculate the scaling factor based on the lowest dimension of the video and the base resolution
        scaling_factor = min(self._height, self._width) / self._base_resolution

        # calculate the patch size and step based on the scaling factor
        self._patch_size = int(self._base_resolution // 2 * scaling_factor)

        # make sure the patch size is divisible by 2
        self._patch_step = int(self._patch_size // 2)

        # calculate the patch shape
        self._patch_shape = (self._patch_size, self._patch_size, 3)

        return self._patch_size, self._patch_step, self._patch_step

    @staticmethod
    def calculate_histogram(frame):
        # calculate the histogram of the frame
        hist = cv2.calcHist([frame], [0], None, [256], [0, 256])

        # normalize the histogram and return it
        return cv2.normalize(hist, hist).flatten()

    @staticmethod
    def compare_histograms(hist1, hist2):

        # compare the histograms using the correlation method
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    @staticmethod
    def detect_shot_change(frame1, frame2, threshold=50):
        """
        This function detects if the shot has changed between two frames.

        It is using a very simple method of calculating the absolute difference between the two frames and then
        calculating the percentage of the frame that has changed. If the percentage of the frame that has changed is
        greater than our threshold, then we consider the shot to have changed.

        :param frame1: first frame
        :param frame2: second frame
        :param threshold: threshold for shot change detection - between 0 and 255,
                          the larger the value, the bigger the changes need to be for the detection to trigger
                          but anything beyond 70 will trigger only on major changes
        """

        # if either the first or second frame is None, return False
        if frame1 is None or frame2 is None:
            return None

        # if someone did pass None as the threshold, set it to 20
        if threshold is None:
            threshold = 50

        # convert the frames to grayscale
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # calculate the absolute difference between the two frames
        frame_diff = cv2.absdiff(frame1, frame2)

        # calculate the percentage of the frame that has changed
        shot_change_score = np.sum(frame_diff) / (frame_diff.shape[0] * frame_diff.shape[1])

        # if the percentage of the frame that has changed is greater than our threshold
        if shot_change_score > threshold:
            return True
        else:
            return False

    def load_model(self):
        """
        This function loads the CLIP model and the preprocessor but only if they are not already loaded.
        """

        if self.clip_model is None or self.clip_prep is None:
            self._load_model()

    def _load_model(self):

        logger.info('Loading CLIP Model "{}" to {}'.format(self.clip_model_name, self.device))

        self.clip_model, self.clip_prep = clip.load(self.clip_model_name, self.device, jit=False)

    def index_video(self, path=None, shot_change_threshold: int = None, skip_frames: int = 0,
                    trim_after_frame: int=None, trim_before_frame: int=0, frame_progress_callback: callable = None,
                    **kwargs):
        """
        :param path: path to video file
        :param shot_change_threshold: threshold for shot change detection
                                        (0 to 255, 0 means identical frames, 255 means no correlation)
        :param skip_frames: number of frames to skip after a new shot was detected
        :param trim_after_frame: where to stop indexing the video
        :param trim_before_frame: where to stop indexing the video
        :param frame_progress_callback: callback function to call after every frame is processed
        :return: None
        """

        if self.clip_model is None or self.clip_prep is None:
            self._load_model()

        # if no path was provided, try to use the source path
        if path is None:
            path = self.source_path

        # check if the path exists and is a file
        if os.path.isfile(path) is False:
            logger.error('File not found or path is not a file: {}'.format(path))
            return False

        self.source_path = path

        # get the total frames of the video
        total_frames = self.video_total_frames(path)

        logger.info('Indexing video: {}'.format(path))

        # open the video
        cap = cv2.VideoCapture(path)

        trim_before_frame = int(trim_before_frame if trim_before_frame else 0)

        # calculate the total frames based on the trim before and trim after frames
        total_frames = math.ceil((total_frames if not trim_after_frame else trim_after_frame) - trim_before_frame)

        # read the first frame
        # ret is a boolean indicating if the frame was read correctly, frame is the frame itself
        ret, frame = cap.read()

        # get the height and width of the frame
        self._height, self._width = frame.shape[:2]

        # calculate the patch dimensions based on the height and width of the frame
        self.calculate_patch_dims()

        # get the fps of the video
        if self._video_fps is None:
            self._video_fps = self.get_video_fps(cap)

        # start at the trim before frame
        current_frame_index = trim_before_frame

        # initialize some stuff
        last_frame = None
        shot_change_detected = False
        total_encoded_frames = 0
        last_frame_features = None

        # use tqdm to show a progress bar
        with tqdm.tqdm(total=total_frames, unit='frames', desc="Indexing Frames") as progress_bar:

            # while we have a frame
            while ret:

                # if we have a progress callback
                # gracefully cancel if it returns false or None
                if frame_progress_callback and callable(frame_progress_callback):
                    if not frame_progress_callback(current_frame_index, total_frames):
                        # release the video
                        cap.release()

                        # and end the indexing
                        return False

                # if we have a trim after and we have reached it then break
                if trim_after_frame is not None and current_frame_index > trim_after_frame:
                    logger.debut('Reached trim point of {}s. Stopping indexing here.'.format(trim_after_frame))
                    break

                # if this is the first frame (we don't have any last_frame),
                # or the shot has changed
                if last_frame is None \
                    or (shot_change_detected :=
                    self.detect_shot_change(frame, last_frame, threshold=shot_change_threshold)):

                    # add the frame index to the shot change list
                    self.shot_changes.append(current_frame_index)

                    # if the frame doesn't look empty, index it
                    if not self.is_empty_frame(frame):
                        # logger.debug('Encoding frame {}'.format(current_frame_index))

                        # encode the frame
                        last_frame_features = self.encode_frame(frame, path, current_frame_index)

                        total_encoded_frames += 1

                    # if the frame looks empty, skip it
                    else:
                        logger.debug('Skipping encoding of empty frame {}'.format(current_frame_index))

                # read the next frame (or skip frames if we have a shot change)
                for _ in range(1 + (skip_frames if shot_change_detected else 0)):

                    # store the current frame as the last frame,
                    # so we use it when comparing the shot change
                    last_frame = frame

                    ret, frame = cap.read()
                    current_frame_index += 1

                    # calculate the progress bar position
                    progress_bar.update(current_frame_index - progress_bar.n)

        # do a final update on the progress bar
        progress_bar.update(progress_bar.total - progress_bar.n)

        # release the video
        cap.release()

        logger.info('Finished indexing: {}. Encoded {} out of {} frames.'
                    .format(path, total_encoded_frames, total_frames))

        return True

    def encode_frame(self, frame, path, current_frame):

        if self.clip_model is None or self.clip_prep is None:
            self._load_model()

        if path is None or not os.path.isfile(path):
            logger.error('Cannot encode frame - file {} not found or is not a file.'.format(path))
            return False

        # initialize the metadata list for this frame
        frame_metadata = []

        # chop frame up into patches
        patches = patchify(frame, self._patch_shape, self._patch_step).squeeze()

        # patches is a 2d array of images patches lets unravel into a 1d array of patches
        shape = patches.shape
        patches = patches.reshape(shape[0] * shape[1], *self._patch_shape)

        # clip wants PIL image objects
        pils = []
        for p in patches:

            # add the metadata for this patch
            frame_metadata.append({'path': os.path.basename(path), 'frame': current_frame})

            # convert the patch to a PIL image and add it to the list
            pils.append(self.clip_prep(Image.fromarray(p)))

        # put all of the images patches into a single tensor
        tensor = torch.stack(pils, dim=0)
        uploaded = tensor.to(self.device)

        # ask CLIP to encode the image features for our patches into a feature vector
        with torch.no_grad():
            frame_features = self.clip_model.encode_image(uploaded)

        # make sure that we have the same number of features and metadata
        if frame_features.shape[0] != len(frame_metadata):
            logger.error('Frame features and metadata do not match. Aborting.')
            return

        # normalize the image feature vectors so that they all have a length of 1
        frame_features /= frame_features.norm(dim=-1, keepdim=True)

        # add the frame features to the video features
        if self.video_encoded is not None:

            # concatenate the frame features to the video features if we already have some
            self.video_encoded = torch.cat((self.video_encoded, frame_features), dim=0)
        else:

            # otherwise just set the video features to the frame features
            self.video_encoded = frame_features

        # add the frame metadata to the video frames list
        self.video_frames.extend(frame_metadata)

        return frame_features

    def is_empty_frame(self, frame):
        """
        Check if the current frame is empty

        Empty means that the frame contains a variation of the same color
        """

        # convert the frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # calculate the standard deviation of the grayscale frame
        # if the standard deviation is below 5 (out of 255) then we consider it an empty frame
        return np.std(gray) < 2

    def search(self, query, n=6, threshold=35, combine_patches=True):

        if self.video_encoded is None or self.video_frames is None:
            return

        if self.clip_model is None:
            self._load_model()

        # ask CLIP to encode our query into a feature vector
        query_tensor = torch.cat([clip.tokenize(query)]).to(self.device)
        with torch.no_grad():
            query_features = self.clip_model.encode_text(query_tensor)

        # normalize the query feature vector so that it has a length of 1
        query_features /= query_features.norm(dim=-1, keepdim=True)

        # convert the embeddings to this machine's dtype if necessary
        if query_features.dtype != self.video_encoded.dtype:
            self.video_encoded = self.video_encoded.to(query_features.dtype)

        # do the actual search here by calculating the distances between the query vector
        # and all of the image features from our video with a single dot product
        similarity = (100.0 * query_features @ self.video_encoded.T)

        # we're combining the patches into frames to avoid having duplicate frames for the same shot
        if combine_patches:
            result = self._combine_patches(similarity, n)
        else:
            result = self._all_patches(similarity, n, threshold)

        return result

    def _all_patches(self, similarity, n, threshold):
        """
        This function returns all the patches of a frame if they match the similarity threshold.
        """

        # let's pull out the best matches
        values, indices = similarity[0].topk(min(n * 10, len(self.video_frames)))

        # build and return the result set
        result = []
        frame = 0

        # for each of the top matches
        for i, d in enumerate(zip(values, indices)):

            # i: count; d[0]: score; d[1]: index
            meta = self.video_frames[d[1]]
            if len(result) < n and d[0] > threshold and abs(meta['frame'] - frame) > 0.1:
                frame = meta['frame']

                frame_data = {
                    'frame': meta['frame'],
                    'score': float(d[0]),
                    'path': meta['path'],
                    'full_path': meta.get('full_path', None),
                    'video_fps': meta.get('video_fps', None),
                    'videoanalysis_version': meta.get('videoanalysis_version', None)
                }
                result.append(frame_data)

        return result

    def _combine_patches(self, similarity, n):
        """
        This function combines all the patches of a frame into a single image to calculate similarity
        depending whether the patches themselves are similar or not.
        """

        frame_groups = defaultdict(list)
        for idx, frame_data in enumerate(self.video_frames):
            frame_groups[frame_data['frame']].append(idx)

        frame_similarity = {}
        for frame, indices_list in frame_groups.items():
            total_similarity = sum(similarity[0, idx].item() for idx in indices_list)
            avg_similarity = total_similarity / len(indices_list)
            frame_similarity[frame] = avg_similarity

        sorted_frames = sorted(frame_similarity.items(), key=lambda item: item[1], reverse=True)
        unique_frames = sorted_frames[:n]

        result = []
        for frame, avg_similarity in unique_frames:
            frame_indices = frame_groups[frame]
            best_patch_meta = self.video_frames[frame_indices[0]]
            frame_data = {
                'frame': best_patch_meta['frame'],
                'score': avg_similarity,
                'path': best_patch_meta['path'],
                'full_path': best_patch_meta.get('full_path', None),
                'video_fps': best_patch_meta.get('video_fps', None),
                'videoanalysis_version': best_patch_meta.get('videoanalysis_version', None),
            }
            result.append(frame_data)

        return result

    def save_embeddings(self, numpy_file_path=None, metadata_file_path=None):
        """
        This saves the video features to a .npy file
        """

        # if no video features are available, abort
        if self.video_encoded is None:
            logger.warning('Cannot save embeddings for {} - no video features available'.format(self.source_path))
            return None

        if not self.video_frames:
            logger.warning('Cannot save embeddings for {} - no video metadata available'.format(self.source_path))
            return None

        # if no numpy path is provided
        if numpy_file_path is None:

            # get the source path
            numpy_file_path = self.source_path

            # and add the .npy extension
            numpy_file_path += '.npy'

        # if no metadata path is provided
        if metadata_file_path is None:

            # add a .json extension to the numpy path
            metadata_file_path = numpy_file_path + '.json'

        # numpy file path cannot be in a different directory than the metadata file path
        if os.path.dirname(numpy_file_path) != os.path.dirname(metadata_file_path):
            logger.error('Cannot save embeddings for {} '
                         '- numpy file and metadata file must be in the same directory'
                         .format(self.source_path))
            return None

        try:
            # save the numpy array to file,
            # but make sure we're using the right device
            np.save(numpy_file_path, self.video_encoded.to('cpu').numpy())

        except:
            logger.error('Failed to save embeddings file {}:'.format(numpy_file_path), exc_info=True)
            return None

        try:
            metadata_dict = dict()

            # the name of the model used to encode the video
            metadata_dict['clip_model'] = self.clip_model_name

            # the framerate
            metadata_dict['video_fps'] = self._video_fps

            # the version of the video analysis library used to encode the video
            metadata_dict['videoanalysis_version'] = self.__version__

            # shot changes indexes
            metadata_dict['shot_changes'] = self.shot_changes

            # the metadata containing the frame indexes and timestamps
            # without this it's impossible to map the embeddings back to the video
            metadata_dict['frames'] = self.video_frames

            # and save the metadata to a json file using utf-8 encoding
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f)

        except:
            logger.error('Failed to save metadata file {}:'.format(metadata_file_path), exc_info=True)
            return None

        return numpy_file_path, metadata_file_path

    def load_into_instance(self, npy_paths=None):
        """
        This loads the video features from a .npy file into this instance
        """

        # if no path is provided
        if npy_paths is None and self.source_path is not None:

            # get the source path
            npy_paths = self.source_path + '.npy'

        # if no path is provided
        if npy_paths is None:
            logger.error('Cannot load embeddings for {} - no path provided'.format(self.source_path))
            return None

        self.video_encoded, self.video_frames = self._load_multiple_embeddings(npy_paths)

    def _load_embeddings(self, npy_path=None, model_name=None):
        """
        This loads the video features from a .npy file
        """

        # load numpy from file, but make sure allow_pickle is set to True
        numpy_array = torch.from_numpy(np.load(npy_path, allow_pickle=True)).to(self.device)

        try:
            # convert the numpy array to a tensor
            # video_encoded = torch.from_numpy(numpy_array).to(self.device)
            video_encoded = numpy_array.to(self.device)

            if not os.path.isfile(npy_path + '.json'):
                logger.error('Cannot load embeddings for {} - no metadata file found at {}'
                             .format(npy_path, npy_path + '.json'))
                return None, None

            # and load the metadata from a json file
            with open(npy_path + '.json', 'r') as f:
                metadata_dict = json.load(f)

            # if a model name was mentioned, only load the embeddings if the model name matches
            if model_name is not None and metadata_dict.get('clip_model', None) != model_name:
                logger.error('Cannot load embeddings for {} - model "{}" is not "{}".'
                             .format(npy_path, metadata_dict.get('clip_model', None), model_name))
                return None, None

            # get the video frames from the metadata
            video_frames = metadata_dict.get('frames', [])

            # add some other metadata to the video frames
            all_video_frames = []
            if video_frames:

                # we're adding the full path, the fps and some other metadata to each video frame
                # so we can easily map the embeddings back to the video and find out what's what on the frame
                for frame in video_frames:

                    frame['full_path'] = os.path.join(os.path.dirname(npy_path), frame['path'])
                    frame['video_fps'] = metadata_dict.get('video_fps', None)
                    frame['videoanalysis_version'] = metadata_dict.get('videoanalysis_version', None)

                    all_video_frames.append(frame)

            # other_metadata is metadata - frames
            other_metadata = metadata_dict.copy()
            other_metadata.pop('frames', None)

            return video_encoded, all_video_frames, other_metadata

        except:
            logger.error('Failed to load embeddings for {}'.format(npy_path), exc_info=True)

        return None, None

    def _load_multiple_embeddings(self, npy_paths):
        """
        This loads multiple embeddings and concatenates them into a single tensor and a single metadata list
        """

        video_encoded_list = []
        video_frames_list = []
        total_offset = 0
        model_name = None

        # if the paths are not a list, make them a list
        if not isinstance(npy_paths, list):
            npy_paths = [npy_paths]

        for npy_path in npy_paths:

            # load the embeddings
            embeddings, frames, metadata = self._load_embeddings(npy_path, model_name=model_name)

            # if the embeddings were loaded successfully
            if embeddings is not None:

                # store the model name for the next iteration
                model_name = metadata.get('clip_model', None)

                # append them to the arrays
                video_encoded_list.append(embeddings)

                for frame_data in frames:

                    # Update this metadata with the offset
                    frame_data['offset'] = total_offset

                    video_frames_list.append(frame_data)

                total_offset += len(embeddings)  # Update the offset for the next batch of embeddings

        # Concatenate the embeddings
        if video_encoded_list:
            video_encoded = torch.cat(video_encoded_list, dim=0)
        else:
            video_encoded = torch.empty(size=(0,), dtype=torch.float32)

        return video_encoded, video_frames_list

    @staticmethod
    def video_frame(path, frame):
        try:
            # Check if the file exists
            if not os.path.exists(path):
                raise FileNotFoundError(f"File not found: {path}")

            # Open the video file
            video = cv2.VideoCapture(path)

            # Check if the video file was opened successfully
            if not video.isOpened():
                raise Exception(f"Unable to open video file: {path}")

            # Set the timestamp of the video to the given frame
            video.set(cv2.CAP_PROP_POS_FRAMES, frame)

            # Read the video frame at the given timestamp
            ret, frame = video.read()

            # Check if the frame was read correctly
            if not ret:
                raise Exception("Unable to read frame at specified frame")

            # Convert the frame from BGR to RGB
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Return the frame
            return frame

        except Exception as e:
            print(f"Error: {e}")
            return None

    @staticmethod
    def video_duration(path, return_frames=False):
        """
        :param path: path to video file
        :param return_frames: return the duration in frames instead of seconds
        :return: duration of the video (seconds)
        """

        # Open the video file
        video = cv2.VideoCapture(path)

        # Get the frame rate and frame count of the video
        fps = video.get(cv2.CAP_PROP_FPS)

        # Get the frame count of the video
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

        # Return the duration of the video in seconds or frames
        return frame_count/fps if not return_frames else frame_count

    @staticmethod
    def get_video_fps(video=None, path=None):
        """
        This gets the video fps either from the video stream or from the video file itself
        :param video: video stream
        :param path: path to video file
        :return: the fps of the video
        """

        if video is None and path is None:
            raise Exception("Either video or path must be specified")

        if video is None:
            # Open the video file
            video = cv2.VideoCapture(path)

        # Get the frame rate and frame count of the video
        fps = video.get(cv2.CAP_PROP_FPS)

        return fps

    @staticmethod
    def video_total_frames(video_path):
        import cv2

        # Open the video file
        cap = cv2.VideoCapture(video_path)

        # Check if the video was opened correctly
        if not cap.isOpened():
            return None

        # Get the total number of frames in the video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.release()

        return total_frames

    @staticmethod
    def convert_frames_to_timestamps(frame, fps):
        """
        Very basic function to convert frames into timestamps
        :param frames: list of frames
        :param fps: frames per second
        :return: list of timestamps
        """

        seconds = frame / fps

        # format the seconds into a timestamp
        timestamp = '{:02d}:{:02d}:{:02d}'.format(int(seconds / 3600), int(seconds / 60) % 60, int(seconds % 60))

        return timestamp

    @staticmethod
    def get_available_clip_models():
        return clip.available_models()


