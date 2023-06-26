import copy
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

import torch
import torchvision.models as models
import torchvision.transforms as transforms

from scipy import stats
from scipy.spatial.distance import cosine
from skimage.metrics import structural_similarity as ssim

from collections import defaultdict

from storytoolkitai.core.logger import logger

class ClipIndex:

    __version__ = '0.1'

    def __init__(self, path: str=None, patch_divider=1.9, device=None, clip_model_name='RN50x4', **kwargs):
        """
        :param patch_size: size of the patches to use for indexing
        :param device: device to use for CLIP model
        """

        # these need to be calculated before starting the indexing
        self._height = self._width = 0

        self._patch_divider = patch_divider

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

        # this will hold the indexes of the frames that were indexed
        self.indexed_frames = []

        # this will hold the indexes of the frames where a shot change was detected
        self.scene_change_frames = []

        self.source_path = path

    @property
    def video_fps(self):
        return self._video_fps

    @property
    def unique_frames(self):
        """
        Get a list of unique frames per path, each path with its own list of unique frames {path: [frames]}
        """

        unique_frames = dict()

        for frame in self.video_frames:

            if frame['path'] not in unique_frames:
                unique_frames[frame['path']] = []

            # if the frame already exists for this path, don't add it
            if frame['frame'] in unique_frames[frame['path']]:
                continue

            unique_frames[frame['path']].append(frame['frame'])

        return unique_frames

    def calculate_patch_dims(self, ratio=None):
        '''
        Calculate the patch size and step based on the ratio of the lowest dimension of the video
        and the base resolution
        '''

        # calculate the scaling factor based on the lowest dimension of the video
        smallest_dim = min(self._height, self._width)

        # use the patch divider as ratio if no ratio is provided
        ratio = self._patch_divider if ratio is None else ratio

        # calculate the patch size and step based on the scaling factor
        self._patch_size = int(min(smallest_dim // ratio, smallest_dim))

        # calculate the number of patches that will fit in the video on both axes
        num_patches_width = math.ceil(self._width / self._patch_size)
        num_patches_height = math.ceil(self._height / self._patch_size)

        # calculate the step size for the patches
        if num_patches_width > 1:
            patch_step_width = math.floor((self._width - self._patch_size) / (num_patches_width - 1))
        else:
            patch_step_width = self._width

        if num_patches_height > 1:
            patch_step_height = math.floor((self._height - self._patch_size) / (num_patches_height - 1))
        else:
            patch_step_height = self._height

        # make sure the patch size is divisible by 2
        self._patch_step = [patch_step_height, patch_step_width]

        # calculate the patch shape
        self._patch_shape = (self._patch_size, self._patch_size, 3)

        return self._patch_size, self._patch_step, self._patch_shape

    @staticmethod
    def compare_rgb(frame1, frame2):
        """
        Compares two frames using the absolute difference between the two frames.
        """

        # calculate the absolute difference between the two frames
        frame_diff = cv2.absdiff(frame1, frame2)
        frame_diff = np.sum(frame_diff, axis=2)

        # calculate the percentage of the frame that has changed in absolute terms and normalize it
        abs_shot_change_score = np.sum(frame_diff) / (frame_diff.shape[0] * frame_diff.shape[1] * 255 * 3)

        return abs_shot_change_score

    @staticmethod
    def compare_greyscale(frame1, frame2):
        """
        Compares two frames using the absolute difference between the two frames.
        """

        # convert the frames to grayscale
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # calculate the absolute difference between the two frames
        frame_diff = cv2.absdiff(frame1, frame2)

        # calculate the percentage of the frame that has changed in absolute terms
        # with this we basically calculate the difference in luminance of the scene
        abs_shot_change_score = np.sum(frame_diff) / (frame_diff.shape[0] * frame_diff.shape[1])

        return abs_shot_change_score

    @staticmethod
    def compare_histograms(frame1, frame2):
        """
        Compares two frames using histograms.
        - a correlation of 1 means that the two histograms are identical
        - a correlation of 0 means that the two histograms are completely different
        - a correlation of -1 means that the two histograms are identical but inverted
        """

        # calculate the histogram of the frame
        hist1 = cv2.calcHist([frame1], [0], None, [256], [0, 256])

        # normalize the histogram and return it
        hist1 = cv2.normalize(hist1, hist1).flatten()

        # calculate the histogram of the frame
        hist2 = cv2.calcHist([frame2], [0], None, [256], [0, 256])

        # normalize the histogram and return it
        hist2 = cv2.normalize(hist2, hist2).flatten()

        # compare the histograms using the correlation method
        return cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

    @staticmethod
    def compare_using_optical_flow_dense_motion(frame1, frame2, visualize=False):
        """
        This function compares the motion between two frames using optical flow.
        The function calculates the average "movement magnitude" for the whole frame.

        Higher average magnitude values indicate more significant motion between the frames,
        while lower values suggest minimal movement.

        The values are normalized between 0 and 1 (0 being no movement and 1 being maximum movement).
        """

        # convert the frames to grayscale
        frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # calculate the optical flow between the two frames
        flow = cv2.calcOpticalFlowFarneback(frame1, frame2, None, 0.5, 3, 15, 3, 5, 1.2, 0)

        # calculate the magnitude and angle of the 2D vectors
        magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

        # normalize the magnitude values between 0 and 1
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX)
        avg_magnitude = np.average(magnitude)

        # visualize the optical flow
        if visualize:
            hsv = np.zeros((frame1.shape[0], frame1.shape[1], 3), dtype=np.uint8)
            hsv[..., 0] = angle * 180 / np.pi / 2
            hsv[..., 1] = 255
            hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
            bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # overlay the optical flow on top of the frame
            frame2_resized = cv2.resize(frame2, (bgr.shape[1], bgr.shape[0]))
            frame2_3channel = cv2.cvtColor(frame2_resized, cv2.COLOR_GRAY2BGR)
            bgr = cv2.addWeighted(frame2_3channel, 1, bgr, 2, 0)

            # show the frame
            cv2.imshow('frame2', bgr)
            cv2.waitKey(1)

        return avg_magnitude

    @staticmethod
    def compare_using_optical_flow_sparse_motion(frame1, frame2, visualize=False):

        # Parameters for Shi-Tomasi Corner Detection
        feature_params = dict(maxCorners=100, qualityLevel=0.3, minDistance=7, blockSize=7)

        # Parameters for Lucas-Kanade Optical Flow
        lk_params = dict(winSize=(15, 15),
                         maxLevel=2,
                         criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.3))

        # Convert the frames to grayscale
        frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Detect corners in the first frame
        p0 = cv2.goodFeaturesToTrack(frame1_gray, mask=None, **feature_params)

        # Calculate the optical flow between the two frames using Lucas-Kanade method
        if p0 is not None:
            p1, st, err = cv2.calcOpticalFlowPyrLK(frame1_gray, frame2_gray, p0, None, **lk_params)

            # Calculate the magnitude and angle of the 2D vectors using only the good points
            flow = p1[st == 1] - p0[st == 1]
            magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])

            if magnitude is None:
                return 0

            # Calculate the average magnitude
            avg_magnitude = np.average(magnitude) if magnitude is not None else 0

            # Calculate the maximum possible magnitude (diagonal of the frame)
            frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            height, width = frame1_gray.shape
            max_magnitude = np.sqrt(height ** 2 + width ** 2)

            # Normalize the average magnitude and threshold
            normalized_avg_magnitude = avg_magnitude / max_magnitude

            # visualize the optical flow
            if visualize:

                # Create a mask image for drawing purposes
                mask = np.zeros_like(frame1)

                # Draw the lines
                for i, (new, old) in enumerate(zip(p1[st == 1], p0[st == 1])):
                    a, b = new.ravel()
                    c, d = old.ravel()
                    mask = cv2.line(mask, (int(a), int(b)), (int(c), int(d)), (0, 255, 0), 2)
                    frame2 = cv2.circle(frame2, (int(a), int(b)), 5, (0, 255, 0), -1)
                img = cv2.add(frame2, mask)
                cv2.imshow('Optical Flow', img)
                cv2.waitKey(500)

            return normalized_avg_magnitude

        return 0

    @staticmethod
    def compare_using_orb(frame1, frame2, points=500, visualize=False, **kwargs):
        """
        This function compares the two frames using ORB to see which points are the same in both frames.
        It creates a list of good matches and returns the ratio of good matches to the total number of matches.
        """

        # convert the frames to grayscale if they are not already
        if len(frame1.shape) > 2:
            frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        frame1 = cv2.equalizeHist(frame1)

        # sharpen the image
        frame1 = cv2.GaussianBlur(frame1, (0, 0), 3)


        if len(frame2.shape) > 2:
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        frame2 = cv2.equalizeHist(frame2)

        # sharpen the image
        frame2 = cv2.GaussianBlur(frame2, (0, 0), 3)

        # Create ORB detector and descriptor
        orb = cv2.ORB_create(nfeatures=points)

        # Detect points and compute descriptors for both images
        kp1, des1 = orb.detectAndCompute(frame1, None)
        kp2, des2 = orb.detectAndCompute(frame2, None)

        # If there are no key points in either image
        if des1 is None or des2 is None or not des1.any() or not des2.any():
            return None

        # Matcher for descriptors (BruteForce-Hamming)
        matcher = cv2.DescriptorMatcher_create(cv2.DESCRIPTOR_MATCHER_BRUTEFORCE_HAMMING)
        matches = matcher.match(des1, des2)

        # Filter matches based on some criteria, e.g., distance
        good_matches = []
        for m in matches:
            if m.distance < 32:  # You can adjust this threshold depending on your application
                good_matches.append(m)

        # Visualize the matches
        if visualize:
            img_matches = cv2.drawMatches(frame1, kp1, frame2, kp2, good_matches, None)
            img_matches = cv2.resize(img_matches, (0, 0), fx=0.5, fy=0.5)
            cv2.imshow("ORB Point Matches", img_matches)
            cv2.waitKey(1)

        # Calculate ratio of good matches to total keypoints detected
        matches_ratio = len(good_matches) / points

        return matches_ratio

    @staticmethod
    def remove_black_bars(frame):
        """
        This function removes the black bars from the top and bottom of the frame.
        """

        # convert the frame to grayscale if it is not already grayscale
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # threshold the grayscale image to get the black bars
        _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)

        # find the contours of the black bars
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # if there are no contours, return the original frame
        if not contours:
            return frame

        # if the entire frame is black, return it
        if len(contours) == 1 and cv2.contourArea(contours[0]) == frame.shape[0] * frame.shape[1]:
            return frame

        # find the largest contour
        largest_cnt = max(contours, key=cv2.contourArea)

        # find the bounding rectangle of the largest contour
        x, y, w, h = cv2.boundingRect(largest_cnt)

        # crop the frame to the bounding rectangle
        cropped = frame[y:y + h, x:x + w]

        return cropped

    @staticmethod
    def _use_cropped_frames(frame1, frame2, **kwargs):
        """
        This crops two frames if they have black bars around them, and makes sure that they are the same size.

        If the cropped frames are within 5 pixels of each other in width and height,
        they will both be cropped to the size of the first frame.

        If the cropped images are two different sizes, we will return the original frames.
        """

        # let's remove any black bars from the frame to focus on the content
        # the black bars might bias the histogram correlation
        # making the alghorithm think that the images are more similar than they actually are
        cropped_frame1 = ClipIndex.remove_black_bars(frame1)
        cropped_frame2 = ClipIndex.remove_black_bars(frame2)

        # if the two crops are the same size, use them
        if cropped_frame1.shape[0] == cropped_frame2.shape[0] \
                and cropped_frame1.shape[1] == cropped_frame2.shape[1]:
            frame1 = cropped_frame1
            frame2 = cropped_frame2

        # if the two crops are almost the same size (within 5 pixels), make them the same size
        elif abs(cropped_frame1.shape[0] - cropped_frame2.shape[0]) < 5 \
                and abs(cropped_frame1.shape[1] - cropped_frame2.shape[1]) < 5:

            # use the size of the first frame to resize the second frame
            frame2 = cv2.resize(cropped_frame2, (cropped_frame1.shape[1], cropped_frame1.shape[0]))
            frame1 = cropped_frame1

        return frame1, frame2

    @staticmethod
    def _pad_frames(frame1, frame2):
        """
        This function pads two frames to make them the same size.
        """

        # get the maximum height and width of the two frames
        max_height = max(frame1.shape[0], frame2.shape[0])
        max_width = max(frame1.shape[1], frame2.shape[1])

        # pad the frames to make them the same size
        frame1 = cv2.copyMakeBorder(frame1, 0, max_height - frame1.shape[0], 0, max_width - frame1.shape[1],
                                    cv2.BORDER_CONSTANT, value=0)
        frame2 = cv2.copyMakeBorder(frame2, 0, max_height - frame2.shape[0], 0, max_width - frame2.shape[1],
                                    cv2.BORDER_CONSTANT, value=0)

        return frame1, frame2

    @staticmethod
    def ssim(frame1, frame2, device=None):
        """
        Computes the structural similarity index between two frames.

        WORK IN PROGRESS - the pytorch ssim implementation doesn't return the same results as the skimage ssim
        """

        ssim_index = ssim(frame1, frame2, multichannel=True, win_size=3)

        return ssim_index

        # for now, we use the skimage implementation above until we can figure out why the pytorch implementation
        # gives different results
        '''

        import torch.nn.functional as F
        import pytorch_ssim

        def modified_ssim(img1, img2, window, window_size, channel, padding, device):
            window = window.to(device)
            img1 = img1.to(device)
            img2 = img2.to(device)

            mu1 = F.conv2d(img1, window, padding=padding, groups=channel)
            mu2 = F.conv2d(img2, window, padding=padding, groups=channel)

            mu1_sq = mu1.pow(2)
            mu2_sq = mu2.pow(2)
            mu1_mu2 = mu1 * mu2

            sigma1_sq = F.conv2d(img1 * img1, window, padding=padding, groups=channel) - mu1_sq
            sigma2_sq = F.conv2d(img2 * img2, window, padding=padding, groups=channel) - mu2_sq
            sigma12 = F.conv2d(img1 * img2, window, padding=padding, groups=channel) - mu1_mu2

            C1 = 0.01 ** 2
            C2 = 0.03 ** 2

            ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / (
                    (mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2)
            )

            return ssim_map.mean().item()

        frame1_tensor = torch.from_numpy(frame1).permute(2, 0, 1).unsqueeze(0).double()
        frame2_tensor = torch.from_numpy(frame2).permute(2, 0, 1).unsqueeze(0).double()

        window_size = 3
        padding = window_size // 2
        channel = 3

        if device is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        start_time = time.time()
        ssim_index = ssim(frame1, frame2, multichannel=True, win_size=3)
        print("\nskimage ssim: ", ssim_index, 'time', time.time() - start_time, 'seconds')


        start_time = time.time()
        window = pytorch_ssim.create_window(window_size, channel).double()
        ssim_correlation = modified_ssim(frame1_tensor, frame2_tensor, window, window_size, channel, padding,
                                         device)

        # turn tensor ssim_correlation into a float
        print("pytorch ssim: ", ssim_correlation, 'time', time.time() - start_time, 'seconds')

        return ssim_correlation
        '''

    @staticmethod
    def fast_detect_change(frame1, frame2, resize_factor=0.5, hist_threshold=0.92, **kwargs):
        """
        This function detects if the shot has changed between two frames by looking at their histograms
        and comparing how many common points do the images have.

        It is using a very simple method of calculating the absolute difference between the two frames and then
        calculating the percentage of the frame that has changed. If the percentage of the frame that has changed is
        greater than our threshold, then we consider the shot to have changed.

        :param frame1: first frame
        :param frame2: second frame
        :param resize_factor: factor to resize the frames by before comparing them
        :param hist_threshold: the threshold for the histogram correlation
        """

        # if either the first or second frame is None, return False
        if frame1 is None or frame2 is None:
            return None

        # downscale the frames if the resize factor is not 1 or None
        if resize_factor is not None and resize_factor < 1:
            resized_frame1 = cv2.resize(frame1, (0, 0), fx=resize_factor, fy=resize_factor)
            resized_frame2 = cv2.resize(frame2, (0, 0), fx=resize_factor, fy=resize_factor)

        # crop the frames if they have black bars around them
        resized_frame1, resized_frame2 = ClipIndex._use_cropped_frames(resized_frame1, resized_frame2)

        # if the two frames are not the same size, it's clear that the shot has changed
        if resized_frame1.shape != resized_frame2.shape:
            return True

        # calculate the histogram correlation between the two histograms
        hist_correlation = ClipIndex.compare_histograms(resized_frame1, resized_frame2)
        # print("histogram correlation: ", hist_correlation)

        # if the correlation is higher than 0.99, make sure by doing a ssim comparison
        # but only if we're not dealing with frames that are single color blocks
        ssim_index = None
        orb_matches = None
        if hist_correlation > 0.97 \
                and not (ClipIndex.is_single_color_block(resized_frame1)
                         and ClipIndex.is_single_color_block(resized_frame2)):

            # calculate the ssim correlation between the two frames
            ssim_index = ClipIndex.ssim(resized_frame1, resized_frame2)

            # print("ssim correlation: ", ssim_index)

            # if the ssim correlation is lower than 0.75, it's contradicting the histogram correlation by a lot
            # so let's try to check the ORB matches
            if ssim_index < 0.75:

                # do the ORB comparison, but use the original frames, not the resized ones
                orb_matches = ClipIndex.compare_using_orb(frame1, frame1, points=500, visualize=False)
                # print("orb matches: ", orb_matches)

                if orb_matches is not None and ssim_index > 0.65 and orb_matches > 0.1:
                    ssim_index = None

                # if the orb matches exist and are higher than 0.4, ignore the ssim correlation
                elif orb_matches is not None and orb_matches > 0.4:
                    ssim_index = None

        # if the histogram correlation is higher than the threshold
        # the images "look" the same
        # and we either couldn't find any ORB matches - meaning that the ORB algorithm couldn't find any useful points
        # or we found too many ORB matches - meaning that the ORB algorithm found too many points that are the same
        if hist_correlation >= hist_threshold and (ssim_index is None or ssim_index > 0.75):

            # so no shot change
            return False

        # if we get here, the shot has changed

        return True

    def load_model(self):
        """
        This function loads the CLIP model and the preprocessor but only if they are not already loaded.
        """

        if self.clip_model is None or self.clip_prep is None:
            self._load_model()

    def _load_model(self):

        logger.info('Loading CLIP Model "{}" to {}'.format(self.clip_model_name, self.device))

        self.clip_model, self.clip_prep = clip.load(self.clip_model_name, self.device, jit=False)

    def index_video(self, path=None,
                    *,
                    detected_shots: list = None,
                    shot_change_threshold: int = None,
                    prefer_sharp: bool = True,
                    skip_color_blocks: bool = True,
                    skip_empty: int = 0,
                    skip_dark: int = 11,
                    skip_similar_neighbors: bool = True,
                    frame_progress_callback: callable = None,
                    **kwargs):
        """
        :param path: path to video file
        :param detected_shots: list of detected shots to be processed from the video,
                               if bool True, all video frames will be processed
                               if None, no frames will be processed
        :param shot_change_threshold:
        :param prefer_sharp: if this is True, the algorithm will try to find the first sharpest frame
                            between the current frame and the next one in the list, and use that for indexing
        :param skip_color_blocks: if this is True, the algorithm will skip frames that are single color blocks
        :param skip_empty: this sets the threshold for how dark an image can be before it's considered empty
                           if the frame is darker than this (using absolute greyscale value), it will be skipped
        :param skip_dark: this sets the threshold for how darkan image can be before it's considered dark
                          (using average intensity - IRE 0-100)
        :param skip_similar_neighbors: if this is True, the algorithm
                                       will not index frames that are similar to the previous frame it indexed
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

        def next_frame_in_list(current_frame_index, detected_shots):
            """
            This function returns the next frame index in the list of detected shots.
            """

            if detected_shots is None or current_frame_index is None:
                return None

            # get the index in the list of the current_frame_index
            try:
                current_idx = detected_shots.index(current_frame_index)

            except ValueError:

                # if the current frame index is not in the list, we need to find the closest frame index
                # that is lower than the current frame index
                # so we get the list of frame indexes that are lower than the current frame index
                # and then we get the last one in the list
                current_idx = max([i for i in detected_shots if i < current_frame_index])

            # we increment the current index by 1, if it's not None
            current_idx = current_idx + 1 if current_idx is not None else 0

            # return the frame index if it exists, otherwise return None
            return detected_shots[current_idx] if len(detected_shots) > current_idx else None

        def scene_range(current_frame_index, detected_shots):
            """
            This returns the range of frames that are in the same scene
            :param current_idx: the current index in the list of detected shots
            :param detected_shots: the list of detected shots
            :return: a tuple containing the first and last frame index of the scene
            """

            if detected_shots is None or current_frame_index is None:
                return current_frame_index, None

            # get the next frame index
            next_frame_index = next_frame_in_list(current_frame_index, detected_shots)

            # if the next frame is None, we are at the end of the list
            if next_frame_index is None:
                return current_frame_index, None

            # otherwise we return the range of frames
            return current_frame_index, next_frame_index

        # the first frame index is the first frame in the list of detected shots
        current_frame_index = detected_shots[0] if detected_shots is not None else 0

        # initialize some stuff

        # the total number of frames we have encoded
        total_encoded_frames = 0
        total_empty_frames = 0

        # the frame features of the last frame that was encoded
        last_frame_features = None

        # use tqdm to show a progress bar
        progress_bar = tqdm.tqdm(total=total_frames, unit='frames', desc="Indexing Frames")

        # while we have a frame
        while ret and current_frame_index is not None:

            # print('Looking at frame', current_frame_index)

            # if we have a progress callback
            # gracefully cancel if it returns false or None
            if frame_progress_callback and callable(frame_progress_callback):
                if not frame_progress_callback(current_frame_index=current_frame_index, total_frames=total_frames):
                    # release the video
                    cap.release()

                    # and end the indexing
                    return False

            # go to the frame that we have to process
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_index)

            # read the next frame
            ret, frame = cap.read()

            # if the frame is empty, skip it
            if (skip_color_blocks and self.is_single_color_block(frame)) \
                    or self.is_empty_frame(frame, threshold=skip_empty)\
                    or self.is_dark_frame(frame, ire=skip_dark):

                logger.debug('Skipping empty, color block or dark frame {}'.format(current_frame_index))

                total_empty_frames += 1

                # go to the next frame in the list of detected shots
                current_frame_index = next_frame_in_list(current_frame_index, detected_shots)

                # if there are no more frames to process, stop
                if current_frame_index is None:
                    break

                progress_bar.update(current_frame_index - progress_bar.n)
                continue

            # we're using this variable just in case we need to select the sharpest frame
            selected_frame_index = current_frame_index

            # try to find the first frame that looks sharp enough
            if prefer_sharp:

                # get the range of frames that are in the same scene
                scene_start, scene_end = scene_range(current_frame_index, detected_shots)

                # print('  Scene range: {} - {}'.format(scene_start, scene_end))

                # if we have a scene range
                if scene_end is not None and scene_start < scene_end:

                    scene_sharpness = []

                    scene_frame_index = scene_start

                    # go to the first frame in the scene
                    cap.set(cv2.CAP_PROP_POS_FRAMES, scene_frame_index)

                    while scene_frame_index < scene_end:

                        # check if we're still improving the sharpness every 24 frames
                        if len(scene_sharpness) % 24 == 0 and len(scene_sharpness) > 0:

                            # calculate the slope
                            slope, _, _, _, _ = stats.linregress(range(len(scene_sharpness)), scene_sharpness)

                            # if the slope is not positive, we stop
                            if slope < 0:
                                break

                        # read the frame
                        ret, frame_for_sharpness = cap.read()

                        # how sharp is this frame?
                        frame_sharpness = self.get_frame_sharpness_laplacian(frame_for_sharpness)

                        # print('  Frame {} sharpness: {}'.format(scene_frame_index, frame_sharpness))

                        # stop if the frame is sharp enough
                        if frame_sharpness > 1:
                            scene_sharpness = [frame_sharpness]
                            break

                        # add the sharpness score to the list
                        scene_sharpness.append(frame_sharpness)

                        # otherwise, go to the next frame
                        scene_frame_index += 1

                    # the sharpest frame becomes the frame we will encode
                    sharpest_frame_index = scene_sharpness.index(max(scene_sharpness))
                    # print('  - Sharpest frame index: {}'.format(scene_start + sharpest_frame_index))

                    # read the sharpest frame to send it to the encoder
                    cap.set(cv2.CAP_PROP_POS_FRAMES, scene_start + sharpest_frame_index)
                    ret, frame = cap.read()

                    selected_frame_index = scene_start + sharpest_frame_index

                    # show the sharpest frame next to the current frame (in the same window)
                    # cv2.imshow('frame', np.hstack((frame, frame_sharpest)))
                    # cv2.waitKey(0)

            logger.debug('Encoding frame {}'.format(selected_frame_index))

            # show the frame
            # cv2.imshow('frame', frame)
            # cv2.waitKey(0)

            # this is the frame we will compare the next frame with
            # if the skip_similar_neighbors flag is False, we will not compare the frame with the last frame
            # so if this is None, we will effectively skip the comparison and basically index every frame
            comparison_frame_features = last_frame_features if skip_similar_neighbors else None

            # encode and index the frame
            # this also compares the current frame with the last frame we encoded
            # and skips the indexing if they are too similar (if the skip_similar_neighbors flag is not False)
            resulting_features = self.encode_frame(frame, path, selected_frame_index, comparison_frame_features)

            # if we don't get any features back, keep on using the last frame features
            # this happens when the frame is too similar to the last frame
            # otherwise, use the features we got back
            # but if the resulting features are None, we don't encode the frame and we keep the last frame features
            # to compare with the next frame in line (if the skip_similar_neighbors flag is not False)
            if resulting_features is not None:

                # use the newly encoded frame as the comparison frame for the next frame
                last_frame_features = resulting_features

                # add this frame to the list of frames we have encoded
                self.indexed_frames.append(current_frame_index)

                total_encoded_frames += 1

            current_frame_index = next_frame_in_list(current_frame_index, detected_shots)

            # if there are no more frames to process, stop
            if current_frame_index is None:
                break

            # update the progress bar
            progress_bar.update(current_frame_index - progress_bar.n)

        # do a final update on the progress bar
        progress_bar.update(progress_bar.total - progress_bar.n)

        # release the video
        cap.release()

        logger.info('Finished indexing: {}. Encoded {} out of {} frames.'
                    .format(path, total_encoded_frames, total_frames))

        return True

    @staticmethod
    def get_frame_sharpness_laplacian(frame):
        """
        Calculate the sharpness of a frame by calculating the laplacian variance
        """

        # turn the frame into grayscale if it isn't already
        if len(frame.shape) > 2:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # scale the image to 0.5x
        gray = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_score = laplacian.var()

        # normalize the score
        sharpness_score = sharpness_score / 1000

        return sharpness_score

    def get_frame_sharpness_gaussian(self, frame):
        """
        Calculate the sharpness of a frame by calculating
        the difference between the frame and a blurred version of the frame
        """

        if len(frame.shape) > 2:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # scale the image to 0.5x
        gray = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        gray = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)

        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        diff = cv2.absdiff(gray, blur)
        sharpness_score = np.average(diff)

        return sharpness_score

    def get_frame_sharpness(self, frame):
        """
        WORK IN PROGRESS - the normalization isn't working as expected
        Use both methods to calculate the sharpness of a frame
        """

        laplacian_sharpness = self.get_frame_sharpness_laplacian(frame)
        gaussian_sharpness = self.get_frame_sharpness_gaussian(frame)

        laplacian_min, laplacian_max = 0, 1000  # Adjust these values as needed
        gaussian_min, gaussian_max = 0, 255

        normalized_laplacian = (laplacian_sharpness - laplacian_min) / (laplacian_max - laplacian_min)
        normalized_gaussian = (gaussian_sharpness - gaussian_min) / (gaussian_max - gaussian_min)

        print('laplacian_sharpness', normalized_laplacian)
        print('gaussian_sharpness', normalized_gaussian)

        average_sharpness = (normalized_laplacian + normalized_gaussian) / 2

        return average_sharpness


    @staticmethod
    def _visualize_shot_change(last_frame, frame, current_frame_index, shot_change_detected):
        """
        Visualize the shot change detection
        """
        last_frame_small = cv2.resize(last_frame, (0, 0), fx=0.3, fy=0.3)
        frame_small = cv2.resize(frame, (0, 0), fx=0.3, fy=0.3)

        cv2.putText(last_frame_small, str(current_frame_index - 1), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255),
                    2)
        cv2.putText(frame_small, str(current_frame_index), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # open the two frames in a window 1000px wide, side by side
        cv2.imshow('frame', np.hstack((last_frame_small, frame_small)))

        # place this in the middle of the screen
        cv2.moveWindow('frame', 100, 100)

        cv2.waitKey(1)

        if shot_change_detected:
            cv2.waitKey(2000)

    @staticmethod
    def patchify_custom(img: object, patch_shape: object, patch_step: tuple[int, int],
                        return_coordinates: bool = False) \
            -> object:

        # if the image is grayscale, add a channel dimension
        shape = ((img.shape[0] - patch_shape[0]) // patch_step[0] + 1,
                 (img.shape[1] - patch_shape[1]) // patch_step[1] + 1)
        channels = img.shape[2] if len(img.shape) == 3 else 1

        # create the patches array
        patches = np.zeros((shape[0], shape[1], patch_shape[0], patch_shape[1], channels), dtype=img.dtype)
        coordinates = []

        # fill the patches array
        for i in range(shape[0]):
            for j in range(shape[1]):
                x_start, x_end = i * patch_step[0], (i * patch_step[0]) + patch_shape[0]
                y_start, y_end = j * patch_step[1], (j * patch_step[1]) + patch_shape[1]
                patches[i, j, :, :, :] = img[x_start:x_end, y_start:y_end, :]
                coordinates.append((x_start, y_start))

        if return_coordinates:
            return patches.squeeze(), coordinates

        return patches.squeeze()

    def get_patch_coordinates(self):
        patch_coordinates = []
        for x in range(0, self._height, self._patch_step[0]):
            for y in range(0, self._width, self._patch_step[1]):
                patch_coordinates.append((x, y))
        return patch_coordinates

    def show_patches(self, frame, patches_coordinates):
        """
        This shows the patches on the frame in a cv2 window using the coordinates and the patch_shape
        """

        # show the patches on the frame in a cv2 window using the coordinates and the patch_shape
        for i in range(len(patches_coordinates)):
            x, y = patches_coordinates[i]

            # random rgb:
            color = tuple(np.random.randint(0, 255, 3).tolist())

            cv2.rectangle(frame, (y, x), (y + self._patch_shape[1], x + self._patch_shape[0]), color, 2)

        # cv2.imshow('frame', frame)
        # cv2.waitKey(0)
        cv2.imwrite('frame_with_patches.png', frame)

    def encode_frame(self, frame, path, frame_idx, last_frame_features=None, skip_similar_threshold=0.90):
        """
        This encodes a frame using the clip model.
        :param frame: The frame to encode
        :param path: The path to the video file
        :param frame_idx: The current frame index
        :param last_frame_features: The features of the last frame, if we want to compare the two
        :param skip_similar_threshold: The threshold to use when comparing the last frame to the current frame
        """

        if self.clip_model is None or self.clip_prep is None:
            self._load_model()

        if path is None or not os.path.isfile(path):
            logger.error('Cannot encode frame - file {} not found or is not a file.'.format(path))
            return False

        # initialize the metadata list for this frame
        frame_metadata = []

        # split frame into patches - but use the custom patchify function
        # patches = patchify(frame, self._patch_shape, self._patch_step).squeeze()
        patches, coordinates = self.patchify_custom(frame, self._patch_shape, self._patch_step, return_coordinates=True)

        # show the patches on the frame in a cv2 window using the coordinates and the patch_shape
        # self.show_patches(frame, coordinates)

        # todo: add a few bigger patches that cover the entire image to make sure we have all the content
        # resize the frame so that it fits the self._patch_shape on it's smallest side
        # aspect_ratio = float(frame.shape[1]) / float(frame.shape[0])
        # if frame.shape[1] > frame.shape[0]:
        #     new_shape = (int(self._patch_size * aspect_ratio), self._patch_size)
        # else:
        #     new_shape = (self._patch_size, int(self._patch_size / aspect_ratio))
        # frame_small = cv2.resize(frame, new_shape)

        # patches2 = self.patchify_custom(frame_small, self._patch_shape, self._patch_step)

        # patches is a 2d array of images patches lets unravel into a 1d array of patches
        shape = patches.shape
        patches = patches.reshape(shape[0] * shape[1], *self._patch_shape)

        # clip wants PIL image objects
        pils = []
        for p in patches:

            # add the metadata for this patch
            frame_metadata.append({'path': os.path.basename(path), 'frame': frame_idx})

            # convert the patch to a PIL image and add it to the list
            pils.append(self.clip_prep(Image.fromarray(p)))

        # place all the patches into a single tensor
        tensor = torch.stack(pils, dim=0)
        uploaded = tensor.to(self.device)

        # encode the image features for our patches into a feature vector
        with torch.no_grad():
            frame_features = self.clip_model.encode_image(uploaded)

        # make sure that we have the same number of features and metadata
        if frame_features.shape[0] != len(frame_metadata):
            logger.error('Frame features and metadata do not match. Aborting.')
            return

        # normalize the image feature vectors so that they all have a length of 1
        frame_features /= frame_features.norm(dim=-1, keepdim=True)

        # if we have a last frame, compare the two and decide whether to skip this frame or to index it
        if last_frame_features is not None:

            # calculate the similarity between the two frames
            similarity = torch.cosine_similarity(frame_features, last_frame_features, dim=-1)

            # since this is a batch of patches, we take the average similarity
            average_similarity = torch.mean(similarity)

            # if the average similarity is above the threshold,
            # it means that this frame is very similar to the last
            if average_similarity > skip_similar_threshold:

                # print('Skipping frame {} - similarity: {}'.format(frame_idx, average_similarity))

                # so we skip it
                return None

            # print('Adding frame {} to index - similarity: {}'.format(frame_idx, average_similarity))

        # if we reached this point, it means that we want to index this frame
        self._index_frame(frame_features, frame_metadata)

        return frame_features

    def _index_frame(self, frame_features, frame_metadata):
        """
        This indexes a frame by adding its features to the video features and its metadata to the video frames list.
        """

        # if we reached this point, it means that we want to index this frame
        # add the frame features to the video features
        if self.video_encoded is not None:

            # concatenate the frame features to the video features if we already have some
            self.video_encoded = torch.cat((self.video_encoded, frame_features), dim=0)
        else:

            # otherwise just set the video features to the frame features
            self.video_encoded = frame_features

        # add the frame metadata to the video frames list
        self.video_frames.extend(frame_metadata)

    @staticmethod
    def is_empty_frame(frame, resize_factor=0.5, threshold=2):
        """
        This checks if the frame looks empty by resizing it
        and calculating the standard deviation of the grayscale image.
        If the standard deviation is below the threshold, then the frame is considered empty.
        """

        if not threshold:
            return False

        # downsample the frame by resizing
        small_frame = cv2.resize(frame, (0, 0), fx=resize_factor, fy=resize_factor)

        # Convert the frame to grayscale
        gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)

        # Calculate the standard deviation of the grayscale frame
        is_empty = np.std(gray) < threshold

        return is_empty

    @staticmethod
    def is_dark_frame(frame, ire=10):
        """
        This checks if the frame is dark by calculating the average intensity of the frame.
        """

        # convert the frame to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # if the image is bigger than 720p, downsample it
        if gray.shape[0] > 720:

            # downsample the frame by resizing
            gray = cv2.resize(gray, (0, 0), fx=0.5, fy=0.5)

        # calculate the average intensity of the frame
        average_intensity = np.average(gray)

        # if the average intensity is below the threshold, then the frame is considered dark
        is_dark = average_intensity < ire

        return is_dark

    @staticmethod
    def is_single_color_block(frame, threshold=2, return_color=False):
        """
        This checks if the frame is a single color block by calculating the range of each channel.
        If the range of each channel is below the threshold, then the frame is considered a single color block.

        :param frame: The frame to check
        :param threshold: The threshold to use when comparing the standard deviations (0-255)
        :param return_color: Whether to return the average color of the frame
        :return: A tuple containing a boolean and the average color of the frame (if return_color is True)
                 or just the boolean (if return_color is False)
        """

        # calculate the range of each channel
        min_b, max_b = np.min(frame[:, :, 0]), np.max(frame[:, :, 0])
        min_g, max_g = np.min(frame[:, :, 1]), np.max(frame[:, :, 1])
        min_r, max_r = np.min(frame[:, :, 2]), np.max(frame[:, :, 2])

        is_single_color = (max_b - min_b < threshold) and (max_g - min_g < threshold) and (max_r - min_r < threshold)

        # if we need the color back, calculate it
        if return_color:

            if is_single_color:
                # Calculate the average color in the BGR format
                avg_b = np.mean(frame[:, :, 0])
                avg_g = np.mean(frame[:, :, 1])
                avg_r = np.mean(frame[:, :, 2])

                return True, (avg_b, avg_g, avg_r)

            else:
                return False, None

        # otherwise just return the boolean
        else:
            return is_single_color

    def get_scene_changes(self,
                          path=None,
                          *,
                          trim_after_frame: int = None,  trim_before_frame: int = 0,
                          frame_progress_callback: callable = None,
                          content_analysis_every: int = 40,
                          jump_every_frames: int = 10,
                          **kwargs):
        """
        This returns the frame indexes where a shot change occurs.
        :param path: The path of the video to analyze, if this is None we'll use self.source_path
        :param trim_after_frame: The frame where to stop the analysis
        :param trim_before_frame: The frame where to start the analysis
        :param frame_progress_callback: A callback function to call after each frame is analyzed
        :param content_analysis_every: How many frames to skip before analyzing the content of the frame
        :param jump_every_frames: How many frames to jump to detect the scene change
                                    - if a change is detected though, we'll go back to where we started the jump
                                      and compare each frame to find the exact frame where the change occurs


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

        logger.info('Detecting scene changes in video: {}'.format(path))

        # open the video
        cap = cv2.VideoCapture(path)

        trim_before_frame = int(trim_before_frame) if trim_before_frame else 0

        # calculate the total frames based on the trim before and trim after frames
        total_frames = math.ceil((total_frames if not trim_after_frame else trim_after_frame) - trim_before_frame)

        # set the current frame index (and take into account the trim before frame)
        current_frame_index = (trim_before_frame if trim_before_frame and int(trim_before_frame) > 0 else 0)

        # read the first frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_index)

        # read the first frame
        ret, current_frame = cap.read()

        # use tqdm to show a progress bar
        progress_bar = tqdm.tqdm(total=total_frames, unit='frames', desc="Detecting Scene Changes") \
            if kwargs.get('show_progress_bar', True) else None

        # this is the last frame we've seen
        previous_frame = None
        previous_frame_index = None

        # did we detect a shot change in the last frame?
        shot_change_detected = False

        # this is the last frame we detected as a shot change
        scene_start_frame = None
        scene_start_frame_index = None

        # store all the frame indexes where we detected a shot change
        scene_changes = []

        # some statistics
        total_detected = 0

        # hold all stats in a dict
        stats = dict()

        # while we have a frame
        while ret:

            # if we have a trim after and we have reached it then break
            if trim_after_frame is not None and current_frame_index >= trim_after_frame:
                logger.debug('Reached trim frame {}. Stopping indexing here.'.format(trim_after_frame))
                break

            # if we have a progress callback
            # gracefully cancel if it returns false or None
            if frame_progress_callback and callable(frame_progress_callback):
                if not frame_progress_callback(
                        current_frame_index=current_frame_index,
                        current_frame=current_frame,
                        last_detected_frame=scene_start_frame,
                        last_detected_frame_index=scene_start_frame_index,
                        total_frames=total_frames,
                        stats=stats
                ):
                    # release the video
                    cap.release()

                    # and end the detection
                    return False

            # we don't have a last frame or we detected a change
            if previous_frame is None \
                    or (shot_change_detected := self.fast_detect_change(current_frame, previous_frame, **kwargs)):

                # since we're jumping frames, whenever a change was detected, we need to go back
                # and check all the skipped frames for changes find the exact frame where it happened
                if previous_frame is not None:
                    stopped_at_frame = current_frame_index

                    # take the current frame index back to the frame before the jump
                    current_frame_index = current_frame_index - jump_every_frames + 1

                    # print('\n\nJumping back to', current_frame_index)

                    # prevent the current frame index from going below 0
                    if current_frame_index < 0:
                        current_frame_index = 0

                    # move the playhead back to the frame before the jump
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_index)

                    # until we reach the frame where we stopped for the deep dive
                    while current_frame_index <= stopped_at_frame:

                        # read the frame
                        ret, current_frame = cap.read()

                        # compare using fast_detect
                        if self.fast_detect_change(current_frame, previous_frame, **kwargs):
                            # if we detect a shot change, break out of the loop
                            break

                        # if we didn't detect a shot change, move to the next frame
                        previous_frame = current_frame
                        current_frame_index += 1

                # store the frame where the shot change happened
                scene_start_frame = current_frame
                scene_start_frame_index = current_frame_index

                # add the frame index to the list of scene changes
                scene_changes.append(scene_start_frame_index)

                total_detected += 1

                # and move the playhead to the next frame
                current_frame_index += jump_every_frames

            # compare using content analysis every X frames since the last detected change
            elif current_frame_index - scene_start_frame_index >= content_analysis_every:

                # Check if frames are similar
                similarity = ClipIndex.calculate_similarity(current_frame, previous_frame, device=self.device)

                if similarity < 0.85:

                    # store the frame where the shot change happened
                    scene_start_frame = current_frame
                    scene_start_frame_index = current_frame_index

                    # add the frame index to the list of scene changes
                    scene_changes.append(scene_start_frame_index)

                    total_detected += 1

                    # print('Detected content change')

                # and move the playhead to the next frame
                current_frame_index += jump_every_frames


            else:
                # otherwise we just move to the next frame (or to the last frame if we reached the end)
                current_frame_index += jump_every_frames \
                    if current_frame_index + jump_every_frames < total_frames else total_frames - current_frame_index

            if previous_frame is not None and kwargs.get('visualize', False):
               self._visualize_shot_change(previous_frame, current_frame, current_frame_index, shot_change_detected)

            # this frame now becomes the last frame we saw
            previous_frame = current_frame
            previous_frame_index = current_frame_index

            # move the playhead before the next frame that we should read
            cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame_index)

            # and read the next frame
            ret, current_frame = cap.read()

            # calculate the progress bar update
            if progress_bar:
                progress_bar.update(current_frame_index - progress_bar.n)

        if len(scene_changes) <= 1:
            logger.info('No shot changes detected.')
            return []

        return scene_changes

    def analyze_neighbor_shots(self, scene_changes,
                               path=None, cap=None,
                               shot_frequency: str ='medium',
                               frame_progress_callback: callable = None,
                               **kwargs):
        """
        This takes each shot within a certain distance from each other and analyzes them to see if they're similar,
        and therefore part of the same scene.

        :param scene_changes: a list of frame indexes where we detected a shot change
        :param path: the path to the video file or...
        :param cap: a cv2.VideoCapture object
        :param shot_frequency: how often should we expect shots to change
        :param frame_progress_callback: a callback function that will be called after each frame is processed
        :param kwargs:

        """

        if path is None and cap is None:
            raise ValueError('You need to provide a path or a cap object.')

        if cap is None:
            cap = cv2.VideoCapture(path)

        if not scene_changes:
            return None

        # get the last frame index
        video_last_frame_index = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # this is the index of the last frame that stays in the filtered list of scene changes
        last_standing_frame = None
        last_standing_frame_index = 0

        # use tqdm to show a progress bar
        progress_bar = tqdm.tqdm(total=video_last_frame_index, unit='frames', desc="Analyzing Neighbor Frames") \
            if kwargs.get('show_progress_bar', True) else None

        # reset closeness_threshold
        # if the shot frequency is high,
        # we expect shots to change often, so we set the closeness threshold to 1/3 of the video's FPS
        if shot_frequency == 'high':
            closeness_threshold = int(cap.get(cv2.CAP_PROP_FPS)) // 2

        # if the shot frequency is low,
        # we expect shots to change rarely, so we set the closeness threshold to 1/1 of the video's FPS
        elif shot_frequency == 'low':
            closeness_threshold = int(cap.get(cv2.CAP_PROP_FPS)) * 2

        # if the shot frequency is medium,
        # we set the closeness threshold to 1/2 of the video's FPS
        else:
            closeness_threshold = int(cap.get(cv2.CAP_PROP_FPS)) // 1

        # the shot_frequency parameter helps us figure out the closeness threshold
        # the closeness_threshold is the maximum distance between two shots
        # that we want to analyze in order to see if they're not actually the same shot

        # at the end of the process, this will only hold the scene changes
        #  basically scene_changes minus the false positives
        filtered_scene_changes = copy.deepcopy(scene_changes)

        # in this, we hold the scene changes that we're not sure about
        uncertain_scene_changes = []

        # we use this to send stats to the progress callback if it exists
        stats = dict()

        # idx is the index of the shot in the scene_changes list (not relative to the video)
        # frame_index is the frame index of the shot (relative to the video)
        for idx, frame_index in enumerate(scene_changes):

            local_closeness_threshold = closeness_threshold

            if progress_bar:
                progress_bar.update(frame_index - progress_bar.n)

            # if this frame is no longer in the filtered list of scene changes, skip it
            if frame_index not in filtered_scene_changes:
                continue

            # print('\n-----\nFrame', frame_index)
            # print(' - max neighbor:', frame_index+local_closeness_threshold)

            # let's read this shot
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame1 = cap.read()

            # if the next shot is too far away, or this is the last shot, break
            while idx + 1 < len(scene_changes) \
                    and frame_index + local_closeness_threshold >= scene_changes[idx + 1]:

                next_frame_index = scene_changes[idx+1]

                shot_removed = False

                # if we have a progress callback
                # gracefully cancel if it returns false or None
                if frame_progress_callback and callable(frame_progress_callback):
                    if not frame_progress_callback(
                            current_frame_index=frame_index,
                            current_frame=frame1,
                            last_detected_frame=last_standing_frame,
                            last_detected_frame_index=last_standing_frame_index,
                            total_frames=video_last_frame_index,
                            stats=stats
                    ):
                        # release the video
                        cap.release()

                        # and end the indexing
                        return False

                # and the next one
                cap.set(cv2.CAP_PROP_POS_FRAMES, next_frame_index)
                ret, frame2 = cap.read()

                # use the cropped version of the frames in case they have black bars (to focus on the actual content)
                frame1, frame2 = self._use_cropped_frames(frame1, frame2)

                # if the frames are of different sizes,
                # it's clear that they're not the same, so the next shot is not a false positive
                if frame1.shape != frame2.shape:
                    break

                # how similar are they?
                stats['ssim_index'] = \
                    ssim_index = self.ssim(frame1, frame2)

                # calculate number of matching points
                stats['points_matching_ratio'] = \
                    points_matching_ratio = self.compare_using_orb(frame1, frame2, visualize=False)

                stats['similarity'] = \
                    similarity = None

                # this means that the orb detector couldn't find any points that are trackable in the images
                if points_matching_ratio is None:
                    points_matching_ratio = 0

                # if the ssim index is high enough, or the points matching ratio is high enough
                # we can assume that these two shots are part of the same scene
                if (ssim_index > 0.65 and points_matching_ratio > 0.50)\
                        or (ssim_index > 0.75 and points_matching_ratio > 0.10) \
                        or ssim_index > 0.79 \
                        or points_matching_ratio > 0.50:

                    # let's remove this shot from the list
                    filtered_scene_changes.remove(next_frame_index)

                    shot_removed = True

                # if the ssim index is low, and the points matching ratio is low
                # we need to analyze the frames more closely using ML
                else:

                    # Check if frames are similar
                    similarity = ClipIndex.calculate_similarity(frame1, frame2, device=self.device)

                    stats['similarity'] = similarity

                    if similarity > 0.85:

                        # let's remove this shot from the list
                        filtered_scene_changes.remove(next_frame_index)

                        shot_removed = True

                        # idx += 1

                # print(frame_index, 'vs', next_frame_index, stats)

                if shot_removed:

                    # once we remove the next shot from the list, we must now also check the shots that were close to it
                    # this is because we were initially assuming that the shot that we just removed was a scene change,
                    # but since it isn't we must compare the neighboring shots also with frame1
                    # instead of frame2 that we just removed

                    # so, if there are more shots to check
                    if idx + 1 < len(scene_changes):

                        # the closeness_threshold should be
                        # =
                        # the distance to the shot that we just removed + plus the closeness threshold (+10%)
                        local_closeness_threshold \
                            = scene_changes[idx + 1] - frame_index + closeness_threshold*1.1

                        idx += 1

                    else:
                        # if there are no more shots to check,
                        # we can break from frame1's loop and go to the next frame
                        break

                # if the shot was not removed, we leave it in the list, but also add it to the list of uncertain shots
                else:
                    uncertain_scene_changes.append(next_frame_index)

                    last_standing_frame_index = frame_index
                    last_standing_frame = frame1

                    # also, let's break from frame1's loop and go to the next frame
                    break

            self.scene_change_frames = filtered_scene_changes

        return filtered_scene_changes, uncertain_scene_changes

    @staticmethod
    def tensor_from_frame(frame):
        loader = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
                                     transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                                          std=[0.229, 0.224, 0.225])])
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = Image.fromarray(frame).convert('RGB')
        frame = loader(frame).unsqueeze(0)
        return frame

    @staticmethod
    def calculate_similarity(frame1, frame2, device='cpu'):
        model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1).to(device)
        model = torch.nn.Sequential(*(list(model.children())[:-1]))
        model.eval()

        frame1_data = ClipIndex.tensor_from_frame(frame1).to(device)
        frame2_data = ClipIndex.tensor_from_frame(frame2).to(device)

        features1 = model(frame1_data).view(-1).detach().cpu().numpy()
        features2 = model(frame2_data).view(-1).detach().cpu().numpy()

        return 1 - cosine(features1.flatten(), features2.flatten())


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

        # todo try the negative prompt
        '''
        # Encode positive and negative queries.
        positive_encoded = self.encode_queries(query)
        #if self.negative_queries:
        negative_encoded = self.encode_queries('black frame')
        #else:
        #    negative_encoded = 0

        # Calculate the similarity.
        similarity = (100.0 * (positive_encoded - negative_encoded) @ self.video_encoded.T)
        '''

        # do the actual search here by calculating the distances between the query vector
        # and all of the image features from our video with a single dot product
        similarity = (100.0 * query_features @ self.video_encoded.T)

        # we're combining the patches into frames to avoid having duplicate frames for the same shot
        if combine_patches:
            result = self._combine_patches(similarity, n)
        else:
            result = self._all_patches(similarity, n, threshold)

        return result

    def encode_queries(self, queries):
        query_tensors = torch.cat([clip.tokenize(query) for query in queries]).to(self.device)
        with torch.no_grad():
            query_features = self.clip_model.encode_text(query_tensors)

        query_features /= query_features.norm(dim=-1, keepdim=True)
        return query_features

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

            # indexed frames
            metadata_dict['indexed_frames'] = self.indexed_frames

            # shot changes
            metadata_dict['scene_change_frames'] = self.scene_change_frames

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

    def video_duration(self, path: str = None, return_frames=False):
        """
        :param path: path to video file
        :param return_frames: return the duration in frames instead of seconds
        :return: duration of the video (seconds)
        """

        # Open the video file
        video = cv2.VideoCapture(self.source_path if path is None else path)

        # Get the frame count of the video
        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

        # return the frame count if requested
        if return_frames:
           return frame_count

        # or return the duration in seconds:

        # Get the frame rate and frame count of the video
        fps = video.get(cv2.CAP_PROP_FPS)

        # Return the duration of the video in seconds or frames
        return frame_count/fps

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

