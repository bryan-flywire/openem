import unittest
import os
from openem.Detect import RetinaNet
import cv2
import numpy as np
import tensorflow as tf

class DetectionTest(tf.test.TestCase):
    def setUp(self):
        self.deploy_dir = os.getenv('deploy_dir')
        if self.deploy_dir == None:
            raise 'Must set ENV:deploy_dir'

        self.image_dir = os.path.join(self.deploy_dir, "detect")
        self.pb_file = os.path.join(self.image_dir,"detect_retinanet.pb")

        # Test image definitions and expected values
        self.images=['test_image_000.jpg',
                     'test_image_001.jpg',
                     'test_image_002.jpg']
        self.fishLocations=[
            [138, 108, 169, 89],
            [318,138,164,91],
            [120,83,315,201]
        ]

    def test_correctness(self):
        image_dims=(360,720,3)
        finder=RetinaNet.RetinaNetDetector(self.pb_file,
                                           imageShape=image_dims,
                                           batch_size=len(self.images))
        for idx,image in enumerate(self.images):
            image_data=cv2.imread(os.path.join(self.image_dir,
                                  image))
            finder.addImage(image_data)

        # Verify the same thing but in batch mode
        raw_result, cookies = finder.process()
        sizes = [cookie["size"] for cookie in cookies]
        batch_result = finder.format_results(raw_result, sizes, 0.0)
        self.assertIsNotNone(batch_result)
        self.assertEqual(len(batch_result),len(self.images))
        for idx in range(len(self.images)):
            with self.subTest(idx=idx):
                # Retinanet will return 300 boxes need to use keep threshold
                # to keep out bad ones.
                self.assertEqual(len(batch_result[idx]), 300)
                location=batch_result[idx][0].location
                print(location)
                self.assertAllClose(location,
                                    np.array(self.fishLocations[idx]),
                                    msg=f"Failed image: {location}",
                                    atol=1)
