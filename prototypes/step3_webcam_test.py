"""
Step 3 Prototype: Minimal Webcam Viewer
=======================================
Purpose:
Verify camera hardware connectivity and frame reading before introducing
computer vision models or mouse control.

Controls:
- Press 'Q' or 'Esc' to exit.
"""

import sys
import cv2


def main():
    camera_index = 0
    print(f"[STEP 3] Opening webcam (index={camera_index})...")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {camera_index}.")
        print("Please check camera connections and Windows privacy permissions.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[STEP 3] Camera active. Press 'Q' or 'Esc' in the video window to quit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[ERROR] Failed to read frame from camera.")
                break

            # Mirror horizontally for natural view
            frame = cv2.flip(frame, 1)

            # Draw status text
            cv2.putText(
                frame,
                "Webcam Diagnostic Feed (Step 3)",
                (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                "Press 'Q' or 'Esc' to close",
                (15, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )

            cv2.imshow("Step 3 - Webcam Diagnostic", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                print("[STEP 3] Exit shortcut pressed.")
                break
    finally:
        print("[STEP 3] Releasing camera and closing windows...")
        cap.release()
        cv2.destroyAllWindows()
        print("[STEP 3] Shutdown complete.")


if __name__ == "__main__":
    main()
