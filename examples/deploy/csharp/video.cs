using System;

/// <summary>
/// End to end example on a video clip.
/// </summary>
class Program {
  /// <summary>Finds ROI in a video.</summary>
  /// <param name="mask_finder_path">Path to find_ruler model file.</param>
  /// <param name="vid_path">Path to the video.</param>
  /// <param name="roi">Rect specifying the ROI.</param>
  /// <param name="transform">
  /// Transform specifying rectification matrix.
  /// </param>
  static void FindVideoRoi(
      string mask_finder_path,
      string vid_path,
      out Rect roi,
      out VectorDouble transform) {
    // Determined by experimentation with GPU having 8GB memory.
    const int kMaxImg = 8;

    // Create and initialize the mask finder.
    RulerMaskFinder mask_finder = new RulerMaskFinder();
    ErrorCode status = mask_finder.Init(mask_finder_path);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to initialize mask finder!");
    }

    // Decode the first 100 frames and find the mask that corresponds
    // to the largest ruler area.
    VideoReader reader = new VideoReader();
    status = reader.Init(vid_path);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to open video!");
    }
    VectorImage masks = new VectorImage();
    Image best_mask = new Image();
    double max_mask_sum = 0.0;
    bool vid_end = false;
    for (int i = 0; i < 100 / kMaxImg; ++i) {
      for (int j = 0; j < kMaxImg; ++j) {
        Image img = new Image();
        status = reader.GetFrame(img);
        if (status != ErrorCode.kSuccess) {
          vid_end = true;
          break;
        }
        status = mask_finder.AddImage(img);
        if (status != ErrorCode.kSuccess) {
          throw new Exception("Failed to add frame to mask finder!");
        }
      }
      status = mask_finder.Process(masks);
      if (status != ErrorCode.kSuccess) {
        throw new Exception("Failed to process mask finder!");
      }
      foreach (var mask in masks) {
        double mask_sum = mask.Sum()[0];
        if (mask_sum > max_mask_sum) {
          max_mask_sum = mask_sum;
          best_mask = mask;
        }
      }
      if (vid_end) break;
    }

    // Now that we have the best mask, use this to compute ROI.
    best_mask.Resize(reader.Width(), reader.Height());
    transform = openem.RulerOrientation(best_mask);
    Image r_mask = openem.Rectify(best_mask, transform);
    roi = openem.FindRoi(r_mask);
  }

  /// <summary>
  /// Finds and classifies detections for all frames in a video.
  /// </summary>
  /// <param name="detect_path">Path to detect model file.</param>
  /// <param name="classify_path">Path to classify model file.</param>
  /// <param name="roi">Region of interest output from FindVideoRoi.</param>
  /// <param name="transform">Transform output from FindVideoRoi.</param>
  /// <param name="detections">Detections for each frame.</param>
  /// <param name="scores">Cover and species scores for each detection.</param>
  static void DetectAndClassify(
      string detect_path,
      string classify_path,
      string vid_path,
      Rect roi,
      VectorDouble transform,
      out VectorVectorRect detections,
      out VectorVectorVectorFloat scores) {
    // Determined by experimentation with GPU having 8GB memory.
    const int kMaxImg = 32;

    // Initialize the outputs.
    detections = new VectorVectorRect();
    scores = new VectorVectorVectorFloat();

    // Create and initialize the detector.
    Detector detector = new Detector();
    ErrorCode status = detector.Init(detect_path, 0.5);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to initialize detector!");
    }

    // Create and initialize the classifier.
    Classifier classifier = new Classifier();
    status = classifier.Init(classify_path, 0.5);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to initialize classifier!");
    }

    // Initialize the video reader.
    VideoReader reader = new VideoReader();
    status = reader.Init(vid_path);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to open video!");
    }

    // Iterate through frames.
    bool vid_end = false;
    while (true) {

      // Find detections.
      VectorVectorRect dets = new VectorVectorRect();
      VectorImage imgs = new VectorImage();
      for (int i = 0; i < kMaxImg; ++i) {
        Image img = new Image();
        status = reader.GetFrame(img);
        if (status != ErrorCode.kSuccess) {
          vid_end = true;
          break;
        }
        img = openem.Rectify(img, transform);
        img = openem.Crop(img, roi);
        imgs.Add(img);
        status = detector.AddImage(img);
        if (status != ErrorCode.kSuccess) {
          throw new Exception("Failed to add frame to detector!");
        }
      }
      status = detector.Process(dets);
      if (status != ErrorCode.kSuccess) {
        throw new Exception("Failed to process detector!");
      }
      for (int i = 0; i < dets.Count; ++i) {
      }
      detections.AddRange(dets);
      for (int i = 0; i < detections.Count; ++i) {
      }

      // Classify detections.
      for (int i = 0; i < dets.Count; ++i) {
        VectorVectorFloat score_batch = new VectorVectorFloat();
        for (int j = 0; j < dets[i].Count; ++j) {
          Image det_img = openem.GetDetImage(imgs[i], dets[i][j]);
          status = classifier.AddImage(det_img);
          if (status != ErrorCode.kSuccess) {
            throw new Exception("Failed to add frame to classifier!");
          }
        }
        status = classifier.Process(score_batch);
        if (status != ErrorCode.kSuccess) {
          throw new Exception("Failed to process classifier!");
        }
        scores.Add(score_batch);
      }
      if (vid_end) break;
    }
  }

  /// <summary>
  /// Writes a new video with bounding boxes around detections.
  /// </summary>
  /// <param name="vid_path">Path to the original video.</param>
  /// <param name="out_path">Path to the output video.</param>
  /// <param name="roi">Region of interest output from FindVideoRoi.</param>
  /// <param name="transform">Transform output from FindVideoRoi.</param>
  /// <param name="detections">Detections for each frame.</param>
  /// <param name="scores">Cover and species scores for each detection.</param>
  static void WriteVideo(
      string vid_path,
      string out_path,
      Rect roi,
      VectorDouble transform,
      VectorVectorRect detections,
      VectorVectorVectorFloat scores) {

    // Initialize the video reader.
    VideoReader reader = new VideoReader();
    ErrorCode status = reader.Init(vid_path);
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to read video!");
    }

    // Initialize the video writer.
    VideoWriter writer = new VideoWriter();
    status = writer.Init(
        out_path,
        reader.FrameRate(),
        Codec.kWmv2,
        new PairIntInt(reader.Width(), reader.Height()));
    if (status != ErrorCode.kSuccess) {
      throw new Exception("Failed to write video!");
    }

    // Iterate through frames.
    for (int i = 0; i < detections.Count; ++i) {
      Image frame = new Image();
      status = reader.GetFrame(frame);
      if (status != ErrorCode.kSuccess) {
        throw new Exception("Error retrieving video frame!");
      }
      Color blue = new Color(); blue[0] = 255; blue[1] = 0; blue[2] = 0;
      Color red = new Color(); red[0] = 0; red[1] = 0; red[2] = 255;
      Color green = new Color(); green[0] = 0; green[1] = 255; green[2] = 0;
      frame.DrawRect(roi, blue, 1, transform);
      for (int j = 0; j < detections[i].Count; ++j) {
        Color det_color = red;
        double clear = scores[i][j][2];
        double hand = scores[i][j][1];
        if (j == 0) {
          if (clear > hand) {
            frame.DrawText("Clear", new PairIntInt(0, 0), green);
            det_color = green;
          } else {
            frame.DrawText("Hand", new PairIntInt(0, 0), red);
            det_color = red;
          }
        }
        frame.DrawRect(detections[i][j], det_color, 2, transform, roi);
      }
      status = writer.AddFrame(frame);
      if (status != ErrorCode.kSuccess) {
        throw new Exception("Error adding frame to video!");
      }
    }
  }

  /// <summary>
  /// Main program.
  /// </summary>
  static void Main(string[] args) {

    // Check input arguments.
    if (args.Length < 4) {
      Console.WriteLine("Expected at least four arguments: ");
      Console.WriteLine("  Path to pb file with find_ruler model.");
      Console.WriteLine("  Path to pb file with detect model.");
      Console.WriteLine("  Path to pb file with classify model.");
      Console.WriteLine("  Path to one or more video files.");
    }

    for (int vid_idx = 3; vid_idx < args.Length; ++vid_idx) {
      // Find the roi.
      Console.WriteLine("Finding region of interest...");
      Rect roi;
      VectorDouble transform;
      FindVideoRoi(args[0], args[3], out roi, out transform);

      // Find detections and classify them.
      Console.WriteLine("Performing detection and classification...");
      VectorVectorRect detections;
      VectorVectorVectorFloat scores;
      DetectAndClassify(
          args[1], 
          args[2], 
          args[vid_idx], 
          roi, 
          transform, 
          out detections,
          out scores);

      // Write annotated video to file.
      Console.WriteLine("Writing video to file...");
      WriteVideo(
          args[vid_idx],
          String.Format("annotated_video_{0}.avi", vid_idx - 3),
          roi,
          transform,
          detections,
          scores);
    }
  }
}