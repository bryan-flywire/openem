"""Functions for preprocessing training data.
"""

import os
import pandas
import scipy.misc
import skimage
from cv2 import VideoCapture
from cv2 import imwrite
from openem_train.util.roi_transform import RoiTransform

def _find_no_fish(config):
    """ Find frames containing no fish.

    # Arguments
        config: ConfigInterface object.

    # Returns
        Dict containing video ID as keys, list of frame numbers as values.
    """
    cover = pandas.read_csv(config.cover_path())
    no_fish = {}
    for _, row in cover.iterrows():
        if row.cover == 0:
            if row.video_id not in no_fish:
                no_fish[row.video_id] = []
            no_fish[row.video_id].append(int(row.frame))
    return no_fish

def extract_images(config):
    """Extracts images from video.

    # Arguments
        config: ConfigInterface object.
    """

    # Create directories to store images.
    os.makedirs(config.train_imgs_dir(), exist_ok=True)

    # Read in length annotations.
    ann = pandas.read_csv(config.length_path())
    vid_ids = ann.video_id.tolist()
    ann_frames = ann.frame.tolist()

    # Find frames containing no fish.
    no_fish = _find_no_fish(config)

    # Start converting images.
    for vid in config.train_vids():
        vid_id, _ = os.path.splitext(os.path.basename(vid))
        img_dir = os.path.join(config.train_imgs_dir(), vid_id)
        os.makedirs(img_dir, exist_ok=True)
        reader = VideoCapture(vid)
        keyframes = [a for a, b in zip(ann_frames, vid_ids) if b == vid_id]
        if vid_id in no_fish:
            keyframes += no_fish[vid_id]
        frame = 0
        while reader.isOpened():
            ret, img = reader.read()
            if frame in keyframes:
                img_path = os.path.join(img_dir, '{:04}.jpg'.format(frame))
                print("Saving image to: {}".format(img_path))
                imwrite(img_path, img)
            frame += 1
            if not ret:
                break

def extract_rois(config):
    """Extracts region of interest.

    # Arguments:
        config: ConfigInterface object.
    """

    # Create directories to store ROIs.
    os.makedirs(config.train_rois_dir(), exist_ok=True)

    # Create a transform object.
    roi_transform = RoiTransform(config)

    # Build a map between video ID and list of enum containing image 
    # and roi paths.
    lookup = {}
    for img_path in config.train_imgs():
        path, f = os.path.split(img_path)
        vid_id = os.path.basename(path)
        roi_path = os.path.join(config.train_rois_dir(), vid_id, f)
        if vid_id not in lookup:
            lookup[vid_id] = []
        lookup[vid_id].append((img_path, roi_path))

    # Create the ROIs.
    for vid_id in lookup:
        vid_dir = os.path.join(config.train_rois_dir(), vid_id)
        os.makedirs(vid_dir, exist_ok=True)
        tform = roi_transform.transform_for_clip(
            vid_id,
            dst_w=config.detect_width(),
            dst_h=config.detect_height())
        for img_path, roi_path in lookup[vid_id]:
            img = scipy.misc.imread(img_path)
            roi = skimage.transform.warp(
                img,
                tform,
                mode='edge',
                order=3,
                output_shape=(
                    config.detect_height(),
                    config.detect_width()))
            print("Saving ROI to: {}".format(img_path))
            scipy.misc.imsave(roi_path, roi)
