"""Top level script for training new OpenEM models.
"""

import argparse
import sys
from openem_train import preprocess
from openem_train import detect
from openem_train import classify
from openem_train import count
from openem_train.util.config_interface import ConfigInterface

def main():
    """Parses command line args and trains models.
    """
    # Add the deployment library to path.
    sys.path.append('../python')
    parser = argparse.ArgumentParser(description='Top level training script.')
    parser.add_argument('config_file',
                        help="Path to config file.")
    parser.add_argument('task',
                        help="What task to do, one of: preprocess, detect.")
    args = parser.parse_args()

    # Read in the config file.
    config = ConfigInterface(args.config_file)

    if args.task == 'extract_images':
        preprocess.extract_images(config)

    #TODO: find_ruler_train and find_ruler_infer go here

    if args.task == 'extract_rois':
        preprocess.extract_rois(config)

    if args.task == 'detect_train':
        detect.train(config)

    if args.task == 'detect_infer':
        detect.infer(config)

    if args.task == 'extract_dets':
        preprocess.extract_dets(config)

    if args.task == 'classify_train':
        classify.train(config)

    if args.task == 'classify_infer':
        classify.infer(config)

    if args.task == 'count_train':
        count.train(config)

if __name__ == '__main__':
    main()
