"""
Step 4 Prototype: Real-Time Hand Tracking Overlay
==================================================
Purpose:
Verifies MediaPipe Hand Landmarker detection and visual overlay
without performing any mouse movements or OS interactions.

Controls:
- Press 'Q' or 'Esc' to exit.
"""

import os
import sys
import cv2
import numpy as np

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import Config, HandDetector


def main():
    config = Config()
    # Ensure model path resolves relative to project root
    config.model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

    print(f"[STEP 4] Opening camera (index={config.camera_index})...")
    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {config.camera_index}.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)

    detector = None
    try:
        print("[STEP 4] Initializing MediaPipe HandLandmarker...")
        detector = HandDetector(config)
        print("[STEP 4] HandLandmarker ready. Showing video feed...")

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            # Mirror frame
            frame = cv2.flip(frame, 1)

            # Detect landmarks
            landmarks = detector.find_landmarks(frame)

            # Draw status
            status_text = "Hand Detected" if landmarks else "Searching for Hand..."
            status_color = (0, 255, 0) if landmarks else (0, 0, 255)
            cv2.putText(
                frame,
                f"Status: {status_text}",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                status_color,
                2,
                cv2.LINE_AA,
            )

            if landmarks:
                # Draw skeleton connections
                for start_idx, end_idx in HandDetector.CONNECTIONS:
                    cv2.line(frame, landmarks[start_idx], landmarks[end_idx], (200, 200, 200), 2)

                # Draw landmark points
                for pt in landmarks:
                    cv2.circle(frame, pt, 4, (240, 240, 240), -1)

                # Highlight index tip (ID 8) and thumb tip (ID 4)
                cv2.circle(frame, landmarks[8], 8, (0, 255, 0), -1)  # Index tip
                cv2.circle(frame, landmarks[4], 8, (255, 200, 0), -1)  # Thumb tip

            cv2.putText(
                frame,
                "Step 4: Tracking Only (No Mouse Control) | [Q] to Quit",
                (15, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

            cv2.imshow("Step 4 - Hand Tracking Diagnostic", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
    finally:
        print("[STEP 4] Cleaning up...")
        cap.release()
        cv2.destroyAllWindows()
        if detector:
            detector.close()
        print("[STEP 4] Finished.")


if __name__ == "__main__":
    main()
