/// @file
/// @brief Implementation for detecting fish in images.
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

#include "detect.h"

#include <opencv2/imgproc.hpp>
#include "detail/model.h"
#include "detail/util.h"

namespace openem {
namespace detect {

namespace tf = tensorflow;

namespace {

/// Decodes bounding box.
/// @param loc Bounding box parameters, one box per row.
/// @param anchors Anchor box parameters, one box per row.
/// @param variances Variances corresponding to each anchor box param.
/// @return Decoded bounding boxes.
std::vector<cv::Rect> DecodeBoxes(
    const cv::Mat& loc, 
    const cv::Mat& anchors, 
    const cv::Mat& variances,
    const cv::Size& img_size);
  
/// Does non-maximum suppression.
/// @param ram bboxes a set of bounding boxes to apply NMS.
/// @param scores a set of corresponding confidences.
/// @param score_threshold a threshold used to filter boxes by score.
/// @param nms_threshold a threshold used in non maximum suppression.
/// @param indices the kept indices of bboxes after NMS.
/// @param top_k if `>0`, keep at most @p top_k picked indices.
void NmsBoxes(
    const std::vector<cv::Rect>& bboxes,
    const std::vector<float>& scores,
    const float score_threshold,
    const float nms_threshold,
    std::vector<int>& indices,
    const int top_k = 0);

} // namespace

/// Implementation details for Detector.
class Detector::DetectorImpl {
 public:
  /// Stores and processes the model.
  detail::ImageModel model_;

  /// Stores image scale factors.
  std::vector<std::pair<double, double>> img_scale_;
};

namespace {

std::vector<cv::Rect> DecodeBoxes(
    const cv::Mat& loc, 
    const cv::Mat& anchors, 
    const cv::Mat& variances,
    const cv::Size& img_size) {
  std::vector<cv::Rect> decoded;
  cv::Mat anchor_width, anchor_height, anchor_center_x, anchor_center_y;
  cv::Mat decode_width, decode_height, decode_center_x, decode_center_y;
  cv::Mat decode_x0, decode_y0, decode_x1, decode_y1;
  anchor_width = anchors.col(2) - anchors.col(0);
  anchor_height = anchors.col(3) - anchors.col(1);
  anchor_center_x = 0.5 * (anchors.col(2) + anchors.col(0));
  anchor_center_y = 0.5 * (anchors.col(3) + anchors.col(1));
  decode_center_x = loc.col(0).mul(anchor_width).mul(variances.col(0));
  decode_center_x += anchor_center_x;
  decode_center_y = loc.col(1).mul(anchor_height).mul(variances.col(1));
  decode_center_y += anchor_center_y;
  cv::exp(loc.col(2).mul(variances.col(2)), decode_width);
  decode_width = decode_width.mul(anchor_width);
  cv::exp(loc.col(3).mul(variances.col(3)), decode_height);
  decode_height = decode_height.mul(anchor_height);
  decode_x0 = (decode_center_x - 0.5 * decode_width) * img_size.width;
  decode_y0 = (decode_center_y - 0.5 * decode_height) * img_size.height;
  decode_x1 = (decode_center_x + 0.5 * decode_width) * img_size.width;
  decode_y1 = (decode_center_y + 0.5 * decode_height) * img_size.height;
  decode_x0.setTo(0, decode_x0 < 0);
  decode_x0.setTo(img_size.width, decode_x0 >= img_size.width);
  decode_y0.setTo(0, decode_y0 < 0);
  decode_y0.setTo(img_size.height, decode_y0 >= img_size.height);
  decode_x1.setTo(0, decode_x1 < 0);
  decode_x1.setTo(img_size.width, decode_x1 >= img_size.width);
  decode_y1.setTo(0, decode_y1 < 0);
  decode_y1.setTo(img_size.height, decode_y1 >= img_size.height);
  for (int i = 0; i < loc.rows; ++i) {
    decoded.emplace_back(
        decode_x0.at<float>(i),
        decode_y0.at<float>(i),
        decode_x1.at<float>(i) - decode_x0.at<float>(i) + 1,
        decode_y1.at<float>(i) - decode_y0.at<float>(i) + 1);
  }
  return decoded;
}

void NmsBoxes(
    const std::vector<cv::Rect>& bboxes,
    const std::vector<float>& scores,
    const float score_threshold,
    const float nms_threshold,
    std::vector<int>& indices,
    const int top_k) {
  CV_Assert(bboxes.size() == scores.size());
  CV_Assert(score_threshold >= 0);
  CV_Assert(nms_threshold >= 0);
  std::vector<std::pair<float, int>> score_index_vec;
  for (auto i = 0; i < scores.size(); ++i) {
    if (scores[i] > score_threshold) {
      score_index_vec.push_back(std::make_pair(scores[i], i));
    }
  }
  std::stable_sort(
      score_index_vec.begin(),
      score_index_vec.end(),
      [](
          const std::pair<float, int>& pair1,
          const std::pair<float, int>& pair2) {
        return pair1.first > pair2.first;
      }
  );
  if (top_k > 0 && top_k < static_cast<int>(score_index_vec.size())) {
    score_index_vec.resize(top_k);
  }
  indices.clear();
  for (size_t i = 0; i < score_index_vec.size(); ++i) {
    const int idx = score_index_vec[i].second;
    bool keep = true;
    for (int k = 0; k < (int)indices.size() && keep; ++k) {
      const int kept_idx = indices[k];
      float overlap = 1.0f - cv::jaccardDistance(bboxes[idx], bboxes[kept_idx]);
      keep = overlap <= nms_threshold;
    }
    if (keep) {
      indices.push_back(idx);
    }
  }
}

} // namespace

Detector::Detector() : impl_(new DetectorImpl()) {}

Detector::~Detector() {}

ErrorCode Detector::Init(
    const std::string& model_path, double gpu_fraction) {
  return impl_->model_.Init(model_path, gpu_fraction);
}

std::pair<int, int> Detector::ImageSize() {
  cv::Size size = impl_->model_.ImageSize();
  return {size.width, size.height};
}

ErrorCode Detector::AddImage(const Image& image) {
  const cv::Mat* mat = detail::MatFromImage(&image);
  auto preprocess = std::bind(
      &detail::Preprocess,
      std::placeholders::_1,
      std::placeholders::_2,
      std::placeholders::_3,
      1.0,
      cv::Scalar(-103.939, -116.779, -123.68),
      false);
  auto size = ImageSize();
  impl_->img_scale_.emplace_back(
      double(image.Width()) / double(size.first),
      double(image.Height()) / double(size.second));
  return impl_->model_.AddImage(*mat, preprocess);
}

ErrorCode Detector::Process(std::vector<std::vector<Detection>>* detections) {
  // Run the model.
  std::vector<tensorflow::Tensor> outputs;
  ErrorCode status = impl_->model_.Process(
      "input_1",
      {"output_node0:0"},
      &outputs);
  if (status != kSuccess) return status;

  // Convert to mat vector.
  std::vector<cv::Mat> pred;
  detail::TensorToMatVec(outputs.back(), &pred, 1.0, 0.0, CV_32F);

  // Iterate through results for each image.
  int pred_stop = 4;
  int conf_stop = outputs.back().dim_size(2) - 8;
  int anc_stop = conf_stop + 4;
  int var_stop = anc_stop + 4;
  cv::Mat loc, conf, variances, anchors;
  std::vector<cv::Rect> boxes;
  std::vector<int> indices;
  std::vector<float> scores;
  std::vector<int> class_index;
  cv::Point max_index;
  for (int i = 0; i < pred.size(); ++i) {
    auto& p = pred[i];
    loc = p(cv::Range::all(), cv::Range(0, pred_stop));
    conf = p(cv::Range::all(), cv::Range(pred_stop, conf_stop));
    anchors = p(cv::Range::all(), cv::Range(conf_stop, anc_stop));
    variances = p(cv::Range::all(), cv::Range(anc_stop, var_stop));
    boxes = DecodeBoxes(loc, anchors, variances, impl_->model_.ImageSize());
    std::vector<Detection> dets;
    // Find the class with highest confidence for each region proposal.
    double max_score;
    scores.resize(conf.rows);
    class_index.resize(conf.rows);
    for (int r = 0; r < conf.rows; ++r) {
      cv::minMaxLoc(
        conf(
          cv::Range(r, r+1),
          cv::Range(1, conf.cols)), // exclude background class
        nullptr,
        &max_score,
        nullptr,
        &max_index);
      scores[r] = max_score;
      class_index[r] = max_index.x + 1; // +1 for background class
    }
    NmsBoxes(boxes, scores, 0.01, 0.45, indices, 200);
    for (int idx : indices) {
      Detection det;
      det.location = {
        int(boxes[idx].x * impl_->img_scale_[i].first),
        int(boxes[idx].y * impl_->img_scale_[i].second),
        int(boxes[idx].width * impl_->img_scale_[i].first),
        int(boxes[idx].height * impl_->img_scale_[i].second)};
      det.confidence = scores[idx];
      det.species = class_index[idx];
      dets.push_back(std::move(det));
    }
    // Sort detections by confidence (high to low).
    std::sort(dets.begin(), dets.end(),
      [](const Detection& left, const Detection& right) -> bool {
      return left.confidence > right.confidence;
    });
    impl_->img_scale_.clear();
    detections->push_back(std::move(dets));
  }
  return kSuccess;
}

Image GetDetImage(const Image& image, const Rect& det) {
  int x = det[0];
  int y = det[1];
  int w = det[2];
  int h = det[3];
  int diff = w - h;
  y -= diff / 2;
  h = w;
  if (x < 0) x = 0;
  if (y < 0) y = 0;
  if ((x + w) > image.Width()) w = image.Width() - x;
  if ((y + h) > image.Height()) h = image.Height() - y;
  return image.GetSub({x, y, w, h});
}

} // namespace detect
} // namespace openem

