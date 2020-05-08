__copyright__ = "Copyright (C) 2018 CVision AI."
__license__ = "GPLv3"
# This file is part of OpenEM, released under GPLv3.
# OpenEM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OpenEM.  If not, see <http://www.gnu.org/licenses/>.

"""Functions for training detection algorithm.
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
import cv2
def _save_model(config, model):
    """Loads best weights and converts to protobuf file.

    # Arguments
        config: ConfigInterface object.
        model: Keras Model object.
    """
    from openem_train.util.model_utils import keras_to_tensorflow
    if config.detect_do_validation():
        best = glob.glob(os.path.join(config.checkpoints_dir('detect'), '*best*'))
    else:
        best = glob.glob(os.path.join(config.checkpoints_dir('detect'), '*periodic*'))
    latest = max(best, key=os.path.getctime)
    model.load_weights(latest)
    os.makedirs(config.detect_model_dir(), exist_ok=True)
    keras_to_tensorflow(model, ['output_node0'], config.detect_model_path())

def train(config):
    """Trains detection model.

    # Arguments
        config: ConfigInterface object.
    """
    # Import keras.
    from keras.optimizers import Adam
    from keras.callbacks import ModelCheckpoint
    from keras.callbacks import TensorBoard
    from keras.applications.inception_v3 import preprocess_input
    from openem_train.ssd import ssd
    from openem_train.ssd.ssd_training import MultiboxLoss
    from openem_train.ssd.ssd_utils import BBoxUtility
    from openem_train.ssd.ssd_dataset import SSDDataset
    from openem_train.util.utils import find_epoch

    # Create tensorboard and checkpoints directories.
    tensorboard_dir = config.tensorboard_dir('detect')
    os.makedirs(config.checkpoints_dir('detect'), exist_ok=True)
    os.makedirs(tensorboard_dir, exist_ok=True)

    # Build the ssd model.
    model = ssd.ssd_model(
        input_shape=(config.detect_height(), config.detect_width(), 3),
        num_classes=config.num_classes())
    
    # If initial epoch is nonzero we load the model from checkpoints 
    # directory.
    initial_epoch = config.detect_initial_epoch()
    if initial_epoch != 0:
        checkpoint = find_epoch(
            config.checkpoints_dir('detect'),
            initial_epoch
        )
        model.load_weights(checkpoint)

    # Set trainable layers.
    for layer in model.layers:
        layer.trainable = True

    # Set up loss and optimizer.
    loss_obj = MultiboxLoss(
        config.num_classes(),
        neg_pos_ratio=2.0,
        pos_cost_multiplier=1.1)
    adam = Adam(lr=3e-5)

    # Compile the model.
    model.compile(loss=loss_obj.compute_loss, optimizer=adam)
    model.summary()

    # Get prior box layers from model.
    prior_box_names = [
        'conv4_3_norm_mbox_priorbox',
        'fc7_mbox_priorbox',
        'conv6_2_mbox_priorbox',
        'conv7_2_mbox_priorbox',
        'conv8_2_mbox_priorbox',
        'pool6_mbox_priorbox']
    priors = []
    for prior_box_name in prior_box_names:
        layer = model.get_layer(prior_box_name)
        if layer is not None:
            priors.append(layer.prior_boxes)
    priors = np.vstack(priors)

    # Set up bounding box utility.
    bbox_util = BBoxUtility(config.num_classes(), priors)

    # Set up dataset interface.
    dataset = SSDDataset(
        config,
        bbox_util=bbox_util,
        preproc=lambda x: x)

    # Set up keras callbacks.
    checkpoint_best = ModelCheckpoint(
        config.checkpoint_best('detect'),
        verbose=1,
        save_weights_only=False,
        save_best_only=True)

    checkpoint_periodic = ModelCheckpoint(
        config.checkpoint_periodic('detect'),
        verbose=1,
        save_weights_only=False,
        period=1)

    tensorboard = TensorBoard(
        tensorboard_dir,
        histogram_freq=0,
        write_graph=True,
        write_images=True)

    # Determine steps per epoch.
    batch_size = config.detect_batch_size()
    steps_per_epoch = config.detect_steps_per_epoch()
    if not steps_per_epoch:
        steps_per_epoch = dataset.nb_train_samples // batch_size

    # Set up validation generator.
    val_batch_size = config.detect_val_batch_size()
    validation_gen = None
    validation_steps = None
    if config.detect_do_validation():
        validation_gen = dataset.generate_ssd(
            batch_size=val_batch_size,
            is_training=False
        )
        validation_steps = dataset.nb_test_samples // val_batch_size

    # Fit the model.
    model.fit_generator(
        dataset.generate_ssd(
            batch_size=batch_size,
            is_training=True),
        steps_per_epoch=steps_per_epoch,
        epochs=config.detect_num_epochs(),
        verbose=1,
        callbacks=[checkpoint_best, checkpoint_periodic, tensorboard],
        validation_data=validation_gen,
        validation_steps=validation_steps,
        initial_epoch=initial_epoch)

    # Save the model.
    _save_model(config, model)

def predict(config):
    """Runs detection model on extracted ROIs.

    # Arguments
        config: ConfigInterface object.
    """
    # Import deployment library.
    sys.path.append('../python')
    import openem
    from openem import Detect

    # Make a dict to contain detection results.
    det_data = {
        'video_id' : [],
        'frame' : [],
        'x' : [],
        'y' : [],
        'w' : [],
        'h' : [],
        'det_conf' : [],
        'det_species' : []
    }

    # Initialize detector from deployment library.
    detector = Detect.SSDDetector(config.detect_model_path())
    if not detector:
        raise IOError("Failed to initialize detector!")

    limit = None
    count = 0
    threshold=0
    if config.config.has_option('Detect', 'Limit'):
        limit = config.config.getint('Detect','Limit')
    if config.config.has_option('Detect', 'Threshold'):
        threshold= config.config.getfloat('Detect', 'Threshold')

    images=set()
    for img_path in config.train_rois():
        images.add(os.path.basename(os.path.dirname(img_path)))
        if limit:
            print(f"Limiting process to {limit} files.")
            if len(images) >= limit:
                break
            else:
                count = count + 1


        img = cv2.imread(img_path)
        # Add image to processing queue.
        detector.addImage(img)

        # Process the loaded image.
        detections = detector.process()

        # Write detection to dict.
        for dets in detections:
            for det in dets:
                path, f = os.path.split(img_path)
                frame, _ = os.path.splitext(f)
                video_id = os.path.basename(os.path.normpath(path))
                x, y, w, h = det.location
                if det.confidence >= threshold:
                    det_data['video_id'].append(video_id)
                    det_data['frame'].append(frame)
                    det_data['x'].append(x)
                    det_data['y'].append(y)
                    det_data['w'].append(w)
                    det_data['h'].append(h)
                    det_data['det_conf'].append(det.confidence)
                    det_data['det_species'].append(det.species)
        print("Finished detection on {}".format(img_path))

    # Write detections to csv.
    os.makedirs(config.inference_dir(), exist_ok=True)
    d = pd.DataFrame(det_data)
    d.to_csv(config.detect_inference_path(), index=False)
