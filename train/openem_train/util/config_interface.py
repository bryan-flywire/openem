"""Defines interface to config file."""

import os
import glob
import configparser

class ConfigInterface:
    """Interface to config file.
    """
    def __init__(self, config_file):
        """Constructor.

        # Arguments
            config_file: Path to config file.
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Read in species info.
        self._species = self.config.get('Data', 'Species').split(',')
        self._ratios = self.config.get('Data', 'AspectRatios').split(',')
        self._ratios = [float(r) for r in self._ratios]
        if len(self._ratios) != len(self._species):
            msg = (
                "Invalid config file!  "
                "Number of species and aspect ratios must match!  "
                "Number of species: {}, "
                "Number of aspect ratios: {}")
            msg.format(len(self._species), len(self._ratios))
            raise ValueError(msg)
        self._num_classes = len(self._species) + 1

    def model_dir(self):
        """Gets model directory.
        """
        return os.path.join(self.config.get('Paths', 'ModelDir'), 'deploy')

    def detect_model_dir(self):
        """Gets detection model directory.
        """
        return os.path.join(self.model_dir(), 'detect')

    def detect_model_path(self):
        """Gets detection file path.
        """
        return os.path.join(self.detect_model_dir(), 'detect.pb')

    def classify_model_dir(self):
        """Gets classification model directory.
        """
        return os.path.join(self.model_dir(), 'classify')

    def classify_model_path(self):
        """Gets classification file path.
        """
        return os.path.join(self.classify_model_dir(), 'classify.pb')

    def count_model_dir(self):
        """Gets count model directory.
        """
        return os.path.join(self.model_dir(), 'count')

    def count_model_path(self):
        """Gets count file path.
        """
        return os.path.join(self.count_model_dir(), 'count.pb')

    def work_dir(self):
        """Gets working directory.
        """
        return self.config.get('Paths', 'WorkDir')

    def train_dir(self):
        """Returns training directory.
        """
        return self.config.get('Paths', 'TrainDir')

    def num_classes(self):
        """Returns number of classes, including null class.
        """
        return self._num_classes

    def species(self):
        """Returns list of species names.
        """
        return self._species

    def aspect_ratios(self):
        """Returns list of species aspect ratios.
        """
        return self._ratios

    def detect_width(self):
        """Returns width of ROI used for detection.
        """
        return self.config.getint('Detect', 'Width')

    def detect_height(self):
        """Returns height of ROI used for detection.
        """
        return self.config.getint('Detect', 'Height')

    def detect_batch_size(self):
        """Returns batch size used for detection training.
        """
        return self.config.getint('Detect', 'BatchSize')

    def detect_val_batch_size(self):
        """Returns batch size used for detection validation.
        """
        return self.config.getint('Detect', 'ValBatchSize')

    def detect_num_epochs(self):
        """Returns number of epochs used for detection training.
        """
        return self.config.getint('Detect', 'NumEpochs')

    def classify_width(self):
        """Returns width of detections used for classification training.
        """
        return self.config.getint('Classify', 'Width')

    def classify_height(self):
        """Returns height of detections used for classification training.
        """
        return self.config.getint('Classify', 'Height')

    def classify_batch_size(self):
        """Returns batch size used for classification training.
        """
        return self.config.getint('Classify', 'BatchSize')

    def classify_val_batch_size(self):
        """Returns batch size used for classification validation.
        """
        return self.config.getint('Classify', 'ValBatchSize')

    def classify_num_epochs(self):
        """Returns number of epochs used for classification training.
        """
        return self.config.getint('Classify', 'NumEpochs')

    def count_num_steps(self):
        """Returns number of timesteps used as input to count model.
        """
        return self.config.getint('Count', 'NumSteps')

    def count_num_steps_crop(self):
        """Returns number of timesteps to crop for count model.
        """
        return self.config.getint('Count', 'NumStepsCrop')

    def count_num_features(self):
        """Returns number of features used as input to count model.
        """
        return self.config.getint('Count', 'NumFeatures')

    def count_batch_size(self):
        """Returns batch size used for count training.
        """
        return self.config.getint('Count', 'BatchSize')

    def count_val_batch_size(self):
        """Returns batch size used for count validation.
        """
        return self.config.getint('Count', 'ValBatchSize')

    def count_num_epochs(self):
        """Returns number of epochs used for count training.
        """
        return self.config.getint('Count', 'NumEpochs')

    def count_num_res_steps(self):
        """Returns number of timesteps after cropping.
        """
        return self.count_num_steps() - self.count_num_steps_crop() * 2

    def train_vids(self):
        """Returns list of paths to videos in training data.
        """
        patt = os.path.join(self.train_dir(), 'videos', '*.mp4')
        return glob.glob(patt)

    def all_video_ids(self):
        """Gets all video IDs as a list.
        """
        video_ids = []
        for vid in self.train_vids():
            _, f = os.path.split(vid)
            vid_id, _ = os.path.splitext(f)
            if vid_id not in video_ids:
                video_ids.append(vid_id)
        return video_ids

    def length_path(self):
        """Returns path to length annotations.
        """
        return os.path.join(self.train_dir(), 'length.csv')

    def cover_path(self):
        """Returns path to cover annotations.
        """
        return os.path.join(self.train_dir(), 'cover.csv')

    def ruler_position_path(self):
        """Returns path to ruler position annotations.
        """
        return os.path.join(self.train_dir(), 'ruler_position.csv')

    def train_imgs_dir(self):
        """Returns path to training images directory.
        """
        return os.path.join(self.work_dir(), 'train_imgs')

    def train_rois_dir(self):
        """Returns path to training roi images directory.
        """
        return os.path.join(self.work_dir(), 'train_rois')

    def train_dets_dir(self):
        """Returns path to training detection images directory.
        """
        return os.path.join(self.work_dir(), 'train_dets')

    def train_imgs(self):
        """Returns list of all training images.
        """
        patt = os.path.join(self.train_imgs_dir(), '**', '*.jpg')
        return glob.glob(patt, recursive=True)

    def num_frames_path(self):
        """Returns path to csv containing number of frames per video.
        """
        return os.path.join(self.train_imgs_dir(), 'num_frames.csv')

    def train_roi_img(self, video_id, frame):
        """Returns a specific image.
        """
        return os.path.join(
            self.train_rois_dir(),
            video_id,
            "{:04d}.jpg".format(frame)
        )

    def train_rois(self):
        """Returns list of all training roi images.
        """
        patt = os.path.join(self.train_rois_dir(), '**', '*.jpg')
        return glob.glob(patt, recursive=True)

    def train_dets(self):
        """Returns list of all training detection images.
        """
        patt = os.path.join(self.train_dets_dir(), '**', '*.jpg')
        return glob.glob(patt, recursive=True)

    def checkpoints_dir(self, model):
        """Returns path to checkpoints directory.

        # Arguments
            model: Which model this corresponds to, one of find_ruler,
            detect, classify, count.
        """
        return os.path.join(self.work_dir(), 'checkpoints', model)

    def checkpoint_best(self, model):
        """Returns path to best checkpoint file.

        The path is meant to be formatted with epoch and validation loss.

        # Arguments
            model: Which model this corresponds to, one of find_ruler,
            detect, classify, count.
        """
        fname = "checkpoint-best-{epoch:03d}-{val_loss:.4f}.hdf5"
        return os.path.join(self.checkpoints_dir(model), fname)

    def checkpoint_periodic(self, model):
        """Returns path to periodic checkpoint file.

        The path is meant to be formatted with epoch and validation loss.

        # Arguments
            model: Which model this corresponds to, one of find_ruler,
            detect, classify, count.
        """
        fname = "checkpoint-{epoch:03d}-{val_loss:.4f}.hdf5"
        return os.path.join(self.checkpoints_dir(model), fname)

    def tensorboard_dir(self):
        """Returns path to tensorboard directory.
        """
        return os.path.join(self.work_dir(), 'tensorboard')

    def inference_dir(self):
        """Returns output path for inference results.
        """
        return os.path.join(self.work_dir(), 'inference')

    def detect_inference_path(self):
        """Returns path to detection inference results.
        """
        return os.path.join(self.inference_dir(), 'detect.csv')

    def classify_inference_path(self):
        """Returns path to classification inference results.
        """
        return os.path.join(self.inference_dir(), 'classify.csv')
