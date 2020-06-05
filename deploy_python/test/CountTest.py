import unittest
import os
from openem.Count import KeyframeFinder

import openem.Detect
import openem.Classify

import cv2
import numpy as np
import tensorflow as tf

class CountTest(tf.test.TestCase):
    def setUp(self):
        self.deploy_dir = os.getenv('deploy_dir')
        if self.deploy_dir == None:
            raise 'Must set ENV:deploy_dir'

        self.classify_dir = os.path.join(self.deploy_dir, "count")
        self.pb_file = os.path.join(self.classify_dir,"count.pb")
        self.detections_csv = os.path.join(self.classify_dir,
                                           "test_detect_sequence.csv")
        self.classification_csv = os.path.join(self.classify_dir,
                                           "test_classify_sequence.csv")

    def test_correctness(self):
        # Test files have dims of 720,360
        finder=KeyframeFinder(self.pb_file, 720, 360)
        self.assertIsNotNone(finder)
        detections = openem.Detect.IO.from_csv(self.detections_csv)
        classifications = openem.Classify.IO.from_csv(self.classification_csv)
        last_frame = detections[-1][0].frame

        # Assert we have a 2d array of frame to detections and
        # frame to classification
        self.assertEqual(len(detections), last_frame+1)
        self.assertEqual(len(detections), len(classifications))

        keyframes = finder.process(classifications,detections)

        # There should be 5 unique fish in this video
        self.assertEqual(len(keyframes), 5)

    def test_errorChecks(self):
        finder=KeyframeFinder(self.pb_file, 720, 360)
        raised=False
        try:
            finder.process([1,2,3],[1,2])
        except Exception as e:
            raised=True
        self.assertTrue(raised)
