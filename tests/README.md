# Automated Unit Testing Suite

This directory contains automated unit tests for the **AI-Based Hand Gesture Mouse Controller (Version 1.0)**.

All automated tests run in a completely isolated environment without requiring access to a webcam and without controlling your real desktop cursor.

---

## Test Suites

1. **`test_coordinates.py`**:
   - Boundary clamping (`clamp_coordinates`)
   - Camera-to-screen coordinate normalization and scaling (`map_camera_to_screen`)
   - Screen edge clamping beyond the interaction box
   - Exponential Moving Average (EMA) cursor smoothing (`SmoothingFilter`)
   - Tracking-loss filter reset to prevent sudden cursor jumps

2. **`test_gesture_logic.py`**:
   - Euclidean distance calculations
   - Threshold pinch detection
   - Frame debounce stability requirements (filters out momentary noise)
   - Edge-triggered click generation (holding a pinch produces exactly one click)
   - Click cooldown timer enforcement
   - Immediate reset on tracking loss
   - `MouseController` disarmed default state
   - Pause/resume state transitions (`P` toggle)
   - PyAutoGUI failsafe recovery and auto-disarming

---

## Running the Automated Tests

From the `hand-gesture-mouse-controller` directory:

```bash
# Run all unit tests
python -m unittest discover tests -v

# Or run individual test modules:
python -m unittest tests/test_coordinates.py -v
python -m unittest tests/test_gesture_logic.py -v
```

---

## Manual Hardware Validation Checklist

When testing with a physical webcam and live mouse control:

1. **Camera Feed:** Verify the OpenCV window opens with a live mirrored video feed.
2. **Disarmed State:** Confirm the status overlay shows `CONTROL: DISARMED / PAUSED` and the mouse pointer does not move when waving your hand.
3. **Arm Control:** Press `P` and verify the status shifts to `CONTROL: ARMED (Active)`.
4. **Smooth Tracking:** Move your index finger across the camera frame and confirm the cursor moves smoothly without severe jitter.
5. **Screen Edges:** Move your finger to the corners of the yellow boundary box and verify the cursor reaches the screen edges.
6. **Single Left Click:** Bring your thumb tip and index fingertip together to pinch. Confirm a single left click triggers.
7. **Hold Protection:** Keep fingers pinched together for 3 seconds. Confirm that rapid repeated clicking does NOT occur.
8. **Pause (`P`):** Press `P` again. Confirm mouse control halts immediately.
9. **Emergency Exit (`Q` / `Esc`):** Press `Q` or `Esc` while the OpenCV window is focused. Confirm the window closes and terminal exits cleanly.
10. **Corner Failsafe:** While armed, physically grab your physical mouse and slam it into the extreme top-left corner (0, 0). Confirm the app catches the failsafe and automatically disarms.
