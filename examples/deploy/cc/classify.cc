/// @file
/// @brief Example of classify deployment.
/// @copyright Copyright (C) 2018 CVision AI.
/// @license This file is part of OpenEM, released under GPLv3.
//  OpenEM is free software: you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation, either version 3 of the License, or
//  any later version.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with OpenEM.  If not, see <http://www.gnu.org/licenses/>.

#include <iostream>

#include "classify.h"

int main(int argc, char* argv[]) {

  // Declare namespace aliases for shorthand.
  namespace em = openem;
  namespace cl = openem::classify;

  // Check input arguments.
  if (argc < 3) {
    std::cout << "Expected at least two arguments: " << std::endl;
    std::cout << "  Path to protobuf file containing model" << std::endl;
    std::cout << "  Paths to one or more image files" << std::endl;
    return -1;
  }

  // Create and initialize classifier.
  cl::Classifier classifier;
  em::ErrorCode status = classifier.Init(argv[1]);
  if (status != em::kSuccess) {
    std::cout << "Failed to initialize classifier!" << std::endl;
    return -1;
  }

  // Load in images.
  std::vector<em::Image> imgs;
  auto size = classifier.ImageSize();
  for (int i = 2; i < argc; ++i) {
    em::Image img;
    status = img.FromFile(argv[i]);
    if (status != em::kSuccess) {
      std::cout << "Failed to load image " << argv[i] << "!" << std::endl;
      return -1;
    }
    img.Resize(size.first, size.second);
    imgs.push_back(std::move(img));
  }

  // Add images to processing queue.
  for (const auto& img : imgs) {
    status = classifier.AddImage(img);
    if (status != em::kSuccess) {
      std::cout << "Failed to add image for processing!" << std::endl;
      return -1;
    }
  }

  // Process the loaded images.
  std::vector<cl::Classification> classifications;
  status = classifier.Process(&classifications);
  if (status != em::kSuccess) {
    std::cout << "Error when attempting to do classification!" << std::endl;
    return -1;
  }

  // Display the images and print scores to console.
  for (int i = 0; i < classifications.size(); ++i) {
    const cl::Classification& classification = classifications[i];
    std::cout << "*******************************************" << std::endl;
    std::cout << "Fish cover scores:" << std::endl;
    std::cout << "No fish:        " << classification.cover[0] << std::endl;
    std::cout << "Hand over fish: " << classification.cover[1] << std::endl;
    std::cout << "Fish clear:     " << classification.cover[2] << std::endl;
    std::cout << "*******************************************" << std::endl;
    std::cout << "Fish species scores:" << std::endl;
    std::cout << "Fourspot:   " << classification.species[0] << std::endl;
    std::cout << "Grey sole:  " << classification.species[1] << std::endl;
    std::cout << "Other:      " << classification.species[2] << std::endl;
    std::cout << "Plaice:     " << classification.species[3] << std::endl;
    std::cout << "Summer:     " << classification.species[4] << std::endl;
    std::cout << "Windowpane: " << classification.species[5] << std::endl;
    std::cout << "Winter:     " << classification.species[6] << std::endl;
    std::cout << std::endl;
    imgs[i].Show();
  }
}

