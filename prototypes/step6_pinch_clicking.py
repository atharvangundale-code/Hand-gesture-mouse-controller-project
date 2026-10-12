"""
Step 6 Prototype: Stable Pinch Gesture & Click Edge Detection
=============================================================
Purpose:
Verifies Euclidean pinch distance calculation, frame debounce stability (2 frames),
edge detection (single click on transition), and cooldown timer (0.35s).
Cursor movement is disabled so you can focus entirely on clicking accuracy.

Controls:
- Press 'P' to toggle click execution (Arm / Disarm).
- Press 'Q' or 'Esc' to exit.
"""

import os
import sys
import time
import cv2

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import Config, HandDetector, PinchDetector, MouseController


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
        pinch_detector = PinchDetector(
            threshold=config.pinch_threshold,
            cooldown_sec=config.click_cooldown_sec,
            stability_frames=config.pinch_stability_frames,
        )

        click_counter = 0

        print("[STEP 6] Initialized in DISARMED mode.")
        print("[STEP 6] Press 'P' to toggle click triggering.")
        print("[STEP 6] Bring thumb and index fingertips together to pinch.")

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            landmarks = detector.find_landmarks(frame)
            should_click = False
            dist = float("inf")

            if landmarks:
                thumb_pt = landmarks[4]
                index_pt = landmarks[8]

                now = time.time()
                should_click, dist = pinch_detector.update(thumb_pt, index_pt, current_time=now)

                is_pinched = dist <= config.pinch_threshold
                color = (0, 255, 0) if is_pinched else (0, 140, 255)
                cv2.line(frame, thumb_pt, index_pt, color, 2)
                cv2.circle(frame, thumb_pt, 7, (255, 200, 0), -1)
                cv2.circle(frame, index_pt, 7, (0, 255, 0), -1)

                cv2.putText(
                    frame,
                    f"Dist: {int(dist)}px (Thresh: {int(config.pinch_threshold)}px)",
                    (15, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

                if should_click:
                    click_counter += 1
                    print(f"[STEP 6] Pinch click #{click_counter} detected! (Dist: {int(dist)}px)")
                    if mouse.is_armed:
                        mouse.click()
            else:
                pinch_detector.reset()

            status_str = "ARMED (Clicking Enabled)" if mouse.is_armed else "DISARMED (Testing Visually)"
            status_color = (0, 255, 0) if mouse.is_armed else (0, 140, 255)
            cv2.putText(frame, f"State: {status_str}", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
            cv2.putText(frame, f"Total Clicks Registered: {click_counter}", (15, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "Step 6: Pinch Only (Movement Disabled) | [P] Toggle | [Q] Quit", (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

            cv2.imshow("Step 6 - Pinch Click Prototype", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            elif key in (ord("p"), ord("P")):
                new_state = mouse.toggle()
                print(f"[STEP 6] Mouse click execution: {'ARMED' if new_state else 'DISARMED'}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if detector:
            detector.close()
        print("[STEP 6] Clean shutdown complete.")


if __name__ == "__main__":
    main()
