# MediaPipe Hand Landmarker Model Asset

This folder contains the official machine learning model asset required by the MediaPipe Tasks API for real-time hand landmark detection.

## Model Details

- **Model Name:** `hand_landmarker.task` (Float16 Quantized)
- **Model Provider:** Google MediaPipe Official Repository
- **Expected File Location:** `assets/hand_landmarker.task`
- **File Size:** ~7.8 MB (7,819,105 bytes)
- **Official Download URL:**  
  [https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)

## Automatic Acquisition

When you run `python main.py` for the first time, the application automatically verifies whether `assets/hand_landmarker.task` exists. If the file is missing, it will automatically download it directly from Google's official repository and display the download progress.

## Manual Acquisition (Offline / Air-Gapped Environments)

If your computer is behind a strict proxy, firewall, or offline:
1. Download the file directly in your browser from the official URL above.
2. Verify the filename is exactly `hand_landmarker.task`.
3. Save or copy it into this `assets/` directory.

## Privacy & Security

The model asset is a pre-trained, read-only TensorFlow Lite bundle executed entirely on your local CPU. It performs zero external network calls during inference and sends no user imagery, video, or data off your machine.
