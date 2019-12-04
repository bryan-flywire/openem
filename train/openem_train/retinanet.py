""" Wrapper to invoke retinanet training scripts from openem """

import subprocess
import os
import csv
import pandas as pd
import cv2

from collections import namedtuple

from openem_train.util import utils
from openem_train.util.roi_transform import RoiTransform
from openem_train.util.img_augmentation import resizeAndFill

import progressbar

FishBoxDetection = namedtuple(
    'FishBoxDetection',
    ['video_id', 'frame', 'x', 'y', 'width', 'height', 'theta', 'class_id'])

def prep(config):
    """ Generates a csv file compatible with retinanet training script
        outputs it in the OPENEM_WORK area for subsequent commands to use
    """

    work_dir = config.work_dir()
    species_csv = os.path.join(work_dir, "retinanet", "species.csv")
    retinanet_csv = os.path.join(work_dir, "retinanet", "annotations.csv")

    # Generate the species csv file first
    # This is a csv file with each species on a new line, with no
    # header
    species_df = pd.DataFrame(columns=['species'], data=config.species)
    species_df.to_csv(species_csv, header=False, index=False)

    # Generate the annotations csv for retinanet; this is in the format
    # from the keras_retinanet.preprocessing.csv_generator module
    # img_file, x1, y1, x2, y2, class_name = row
    # Where x1,y1 and x2,y2 represent the diagonal across a box annotation
    # Also valid row is
    # image_file,,,,,
    # This represents an image file with no annotations; it is ignored by
    # the preprocessor in keras_retinanet

    # Before we start converting/transforming we setup the roi transform
    # object and figure out if we are in line or box mode
    roi_transform = RoiTransform(config)
    length = pd.read_csv(self.config.length_path())

    keys = length.keys()
    linekeys=['x1','x2','y1','y2']
    boxkeys=['x','y','width','height','theta']
    if all(x in keys for x in linekeys):
        lineMode = True
    elif all(x in keys for x in boxkeys):
        lineMode = False

    retinanet_cols=['img_file', 'x1', 'y1', 'x2', 'y2', 'class_name']
    retinanet_df = pd.Dataframe(columns=retinanet_cols)

    bar = progressbar.ProgressBar(max_value=len(length))
    # Iterate over each row in the length.csv and make a retinanet.csv
    for _, row in bar(length.iterrows()):
        # Ignore no detections for retinanet csv
        if row.species_id == 0:
            continue

        # Each video id / image id has a unique RoI transform
        # TODO: This seems like it could be frame dependent
        # depending on the scenario
        tform = self.roi_transform.transform_for_clip(
            detection.video_id,
            dst_w=self.config.detect_width(),
            dst_h=self.config.detect_height())

        # Construct image path
        image_file = os.path.join(config.train_rois_dir(),
                                  row.video_id,
                                  f"{row.frame:04d}.jpg")

        # Species id in openem is 1-based index
        species_id_0 = row.species_id - 1
        species_name = config.species[species_id_0]

        # If the roi image is not the same dims as the detect input we
        # have a scale factor to apply
        img = cv2.imread(image_file)

        # Don't care about actual image contents
        _, scale = resizeAndFill(img, (self.config.detect_height(),
                                       self.config.detect_width()))

        # OpenEM detection csv is in image coordinates, need to convert
        # that to roi coordinates because that is what we train on.
        # Logic is pretty similar for line+aspect ratio and box style
        # annotations
        if lineMode:
            aspect_ratio = self.config.aspect_ratios()[species_id_0]
            coords_image = np.array([[detection.x1*scale[1],
                                      detection.y1*scale[0]],
                                     [detection.x2*scale[1],
                                      detection.y2*scale[0]]])
            coords_roi = tform.inverse(coords_image)
            coords_box0, coords_box1 = utils.bbox_for_line(coords_in_crop[0,:],
                                                           coords_in_crop[1,:],
                                                           aspect_ratio)
        else:
            # Make the row a detection object (in image coords)
            detection_image = FishBoxDetection(
                video_id=row.video_id,
                frame=row.frame,
                x=row.x, y=row.y,
                width=row.width,
                height=row.height,
                theta=row.theta,
                class_id=row.species_id
            )
            rotated_detection_image = utils.rotate_detection(detection_image)
            # Box is now converted from x,y,w,h to 4 points representing each
            # corner
            # Need to apply the scale
            rotated_detection_image[:,0] *= scale[1]
            rotated_detection_image[:,1] *= scale[0]
            # We translate all 4 points
            topLeftIdx,bottomRightIdx=utils.find_corners(coords_in_crop)
            # These are now the diagnol representing the bounding box.
            coords_box0=coords_in_crop[topLeftIdx]
            coords_box1=coords_in_crop[bottomRightIdx]

        datum={'img_file' : image_file,
               'class_name' : species_name,
               'x1': coords_box0[0],
               'y1': coords_box0[1],
               'x2': coords_box[0],
               'y2': coords_box[1]}

        retinanet_df = retinanet_df.append(pd.Dataframe(columns=retinanet_cols,
                                                        data=[datum]))

    # After all the iterations, generate the file
    retinanet_df.to_csv(retinanet_csv, index=False, header=False)


def train(config):
    work_dir = config.work_dir()
    species_csv = os.path.join(work_dir, "retinanet", "species.csv")
    retinanet_csv = os.path.join(work_dir, "retinanet", "annotations.csv")
    if not os.path.exists(species_csv):
        print(f"Need to make species.csv in {work_dir}")
        print("Attempting to generate it for you from config.ini")
        with open(species_csv,'w') as csv_file:
            writer = csv.writer(csv_file)
            for species in config.species():
                print(f"\t+Adding {species}")
                writer.writerow([species])
            print("Done!")
    else:
        print("Detected Species.csv in training dir")

    args = ['python',
            '/keras_retinanet/scripts/train.py',
            '--train_img_dir',
            config.train_imgs_dir(),
            'openem',
            boxes_csv,
            species_csv]
    p=subprocess.Popen(args)
    p.wait()
    return p.returncode
