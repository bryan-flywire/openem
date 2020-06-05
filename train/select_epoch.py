#!/usr/bin/env python

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

"""Converts model for different epoch than the default.
"""

import argparse
import os
import glob
from openem_train.ssd import ssd
from openem_train.util.config_interface import ConfigInterface
from openem_train.util.model_utils import keras_to_tensorflow

def main():
    """Parses command line args and converts models.
    """
    # Add the deployment library to path.
    parser = argparse.ArgumentParser(description=
        "Script for selecting a different epoch from the default. "
        "The default is to use the epoch with lowest validation "
        "loss, but if this is found to be overtrained this script "
        "allows the user to select a different epoch from the "
        "training results.")
    parser.add_argument(
        'config_file',
        help="Path to config file.")
    parser.add_argument(
        'model',
        help="Which model, one of: find_ruler, detect, classify, count.")
    parser.add_argument(
        'epoch',
        help="Which epoch to convert to deployment format.",
        type=int)
    args = parser.parse_args()

    # Read in the config file.
    config = ConfigInterface(args.config_file)

    # Find checkpoint associated with user inputs.
    check_dir = config.checkpoints_dir(args.model)
    fname = "checkpoint-{:03d}-*.hdf5".format(args.epoch)
    patt = os.path.join(check_dir, fname)
    files = glob.glob(patt)
    if files:
        latest = max(files, key=os.path.getctime)
        msg = "Found checkpoint for {} model, epoch {} at {}!"
        print(msg.format(args.model, args.epoch, latest))
    else:
        msg = "Could not find {} model for epoch {}!  Searched for {}"
        raise ValueError(msg.format(args.model, args.epoch, patt))

    # Save the model.
    if args.model == 'detect':
        model = ssd.ssd_model(
            input_shape=(config.detect_height(), config.detect_width(), 3),
            num_classes=config.num_classes())
        model.load_weights(latest)
        os.makedirs(config.detect_model_dir(), exist_ok=True)
        print("Saving model to {}...".format(config.detect_model_path()))
        keras_to_tensorflow(
            model, 
            ['output_node0'], 
            config.detect_model_path())
        print("Conversion to deployment model complete.")

if __name__ == '__main__':
    main()
