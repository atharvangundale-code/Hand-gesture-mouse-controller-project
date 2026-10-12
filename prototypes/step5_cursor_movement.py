"""
Step 5 Prototype: Cursor Movement with Coordinate Mapping & Smoothing
======================================================================
Purpose:
Verifies index finger coordinate mapping and exponential moving average smoothing.
Starts in DISARMED mode; requires pressing 'P' to enable mouse movement.
Clicking is strictly disabled in this step.

Controls:
- Press 'P' to toggle cursor movement (Arm / Disarm).
- Press 'Q' or 'Esc' to exit.
"""

import os
import sys
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import Config, HandDetector, SmoothingFilter, map_camera_to_screen, MouseController


def main():
    config = Config()
    config.model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))

    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Could not open camera {config.camera_index}.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)

    detector = None
    try:
        detector = HandDetector(config)
        mouse = MouseController()
        smoother = SmoothingFilter(alpha=config.smoothing_factor)

        print("[STEP 5] Initialized in DISARMED mode.")
        print("[STEP 5] Press 'P' in the video window to enable/disable cursor movement.")
        print("[STEP 5] Press 'Q' or 'Esc' to quit.")

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Draw active box
            cv2.rectangle(
                frame,
                (config.margin_x, config.margin_y),
                (w - config.margin_x, h - config.margin_y),
                (0, 220, 255),
                2,
            )

            landmarks = detector.find_landmarks(frame)

            if landmarks:
                index_pt = landmarks[8]
                cv2.circle(frame, index_pt, 8, (0, 255, 0), -1)

                screen_x, screen_y = map_camera_to_screen(
                    cam_x=index_pt[0],
                    cam_y=index_pt[1],
                    frame_w=w,
                    frame_h=h,
                    margin_x=config.margin_x,
                    margin_y=config.margin_y,
                    screen_w=mouse.screen_w,
                    screen_h=mouse.screen_h,
                )

                smooth_x, smooth_y = smoother.update(screen_x, screen_y)

                if mouse.is_armed:
                    mouse.move_to(smooth_x, smooth_y)
            else:
                smoother.reset()

            status_str = "ARMED (Moving)" if mouse.is_armed else "DISARMED (Press 'P')"
            status_color = (0, 255, 0) if mouse.is_armed else (0, 140, 255)
            cv2.putText(frame, f"State: {status_str}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            cv2.putText(frame, "Step 5: Movement Only (Clicking Disabled) | [P] Toggle | [Q] Quit", (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

            cv2.imshow("Step 5 - Cursor Movement Prototype", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            elif key in (ord("p"), ord("P")):
                new_state = mouse.toggle()
                print(f"[STEP 5] Mouse movement: {'ARMED' if new_state else 'DISARMED'}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if detector:
            detector.close()
        print("[STEP 5] Resources cleanly released.")


if __name__ == "__main__":
    main()
