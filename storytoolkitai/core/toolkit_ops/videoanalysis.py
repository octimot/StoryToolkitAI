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

from storytoolkitai.core.logger import logger


class ClipIndex:

    def __init__(self, base_resolution=720, patch_divider=2, device=None, clip_model_name='RN50x4'):
        """
        :param patch_size: size of the patches to use for indexing
        :param device: device to use for CLIP model
        """

        # start with a video frame of 720px720p, just to have a base resolution
        # - this will be re-calculated as soon as we load the video
        self._base_resolution = self._height = self._width = base_resolution

        self._patch_size, self._patch_step, self._patch_shape = self.calculate_patch_dims()

        self.device = device

        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        logger.info("Loading CLIP Model")

        self.clip_model_name = clip_model_name
        self.clip_model, self.clip_prep = clip.load(self.clip_model_name, self.device, jit=False)

        # this will contain all the image features for our video in a tensor
        self.video_encoded = None

        # this will hold the metadata for every image feature held in video_encoded
        self.video_metadata = []

        # this will hold the frame indexes at which shot changes occur
        self.shot_changes = []

        self.source_path = None

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

        # start at the trim before frame
        current_frame_index = trim_before_frame

        # initialize some stuff
        last_frame = None
        shot_change_detected = False
        total_encoded_frames = 0

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
                        logger.debug('Encoding frame {}'.format(current_frame_index))

                        # encode the frame
                        self.encode_frame(frame, path, current_frame_index)

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
            frame_metadata.append({'path': os.path.basename(path), 'frame': current_frame})
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

        # add the frame metadata to the video metadata
        self.video_metadata.extend(frame_metadata)

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

    def search(self, query, n=6, threshold=35):

        # ask CLIP to encode our query into a feature vector
        query_tensor = torch.cat([clip.tokenize(query)]).to(self.device)
        with torch.no_grad():
            query_features = self.clip_model.encode_text(query_tensor)

        # normalize the query feature vector so that it has a length of 1
        query_features /= query_features.norm(dim=-1, keepdim=True)

        # do the actual search here by calculating the distances between the query vector
        # and all of the image features from our video with a single dot product
        similarity = (100.0 * query_features @ self.video_encoded.T)

        # lets pull out the best matches
        values, indices = similarity[0].topk(min(n * 10, len(self.video_metadata)))

        # build and return the result set
        result = []
        time = 0

        # for each of the top matches
        for i, d in enumerate(zip(values, indices)):

            # i: count; d[0]: score; d[1]: index
            meta = self.video_metadata[d[1]]
            if len(result) < n and d[0] > threshold and abs(meta['t'] - time) > 0.1:
                time = meta['t']
                result.append({'score': float(d[0]), 'path': meta['path'], 't': meta['t']})

        return result

    def save_embeddings(self, numpy_file_path=None, metadata_file_path=None):
        """
        This saves the video features to a .npy file
        """

        # if no video features are available, abort
        if self.video_encoded is None:
            logger.warning('Cannot save embeddings for {} - no video features available'.format(self.source_path))
            return None

        if not self.video_metadata:
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
            # todo 230612 - test this on GPU always encode on CPU for cross platform compatibility
            np.save(numpy_file_path, self.video_encoded.to('cpu').numpy())

        except:
            logger.error('Failed to save embeddings file {}:'.format(numpy_file_path), exc_info=True)
            return None

        try:
            metadata_dict = dict()

            # since we're saving the embeddings in relation to the video file, we need to get the relative path to it
            metadata_dict['video_file_path'] = os.path.relpath(self.source_path, metadata_file_path)

            # the name of the model used to encode the video
            metadata_dict['clip_model'] = self.clip_model_name

            # shot changes indexes
            metadata_dict['shot_changes'] = self.shot_changes

            # the metadata containing the frame indexes and timestamps
            # without this it's impossible to map the embeddings back to the video
            metadata_dict['metadata'] = self.video_metadata

            # and save the metadata to a json file using utf-8 encoding
            with open(metadata_file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f)

        except:
            logger.error('Failed to save metadata file {}:'.format(metadata_file_path), exc_info=True)
            return None

        return numpy_file_path, metadata_file_path

    def load_embeddings(self, path=None):
        """
        This loads the video features from a .npy file
        """

        # if no path is provided
        if path is None:

            # get the source path
            path = self.source_path

            # and add the .npy extension
            path += '.npy'

        # load numpy from file, but make sure allow_pickle is set to True
        numpy_array = torch.from_numpy(np.load(path, allow_pickle=True)).to(self.device)

        try:
            # convert the numpy array to a tensor
            self.video_encoded = torch.from_numpy(numpy_array).to(self.device)

            # and load the metadata from a json file
            with open(self.source_path + '.npy.json', 'r') as f:
                metadata_dict = json.load(f)

            self.video_metadata = metadata_dict.get('metadata', [])

        except:
            logger.error('Failed to load embeddings for {}'.format(path))

        return self.video_encoded, self.video_metadata

    @staticmethod
    def video_frame(path, timestamp=0):
        """
        :param path: path to video file
        :param timestamp: timestamp of the frame to return (seconds)
        :return: frame in RGB format
        """

        # Open the video file
        video = cv2.VideoCapture(path)

        # Set the timestamp of the video to the given timestamp
        video.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)

        # Read the video frame at the given timestamp
        ret,frame = video.read()

        # Convert the frame from BGR to RGB
        frame = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

        # Return the frame if it was read correctly, otherwise return None
        return frame if ret else None

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
    def get_available_clip_models():
        return clip.available_models()
