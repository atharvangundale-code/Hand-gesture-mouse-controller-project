# Troubleshooting Guide (Version 1.0)

This guide covers common setup issues, operating-system permissions, and camera diagnostics.

---

## 1. Camera Initialization Errors

### Error: `[ERROR] Unable to open camera index 0.`
- **Cause 1: Webcam Privacy Settings in Windows**
  - Open Windows Settings (`Win + I`).
  - Navigate to **Privacy & Security** > **Camera**.
  - Ensure **Camera access** is set to **On**.
  - Scroll down and ensure **Let desktop apps access your camera** is set to **On**.
- **Cause 2: Camera Occupied by Another Application**
  - Verify that Microsoft Teams, Zoom, Skype, OBS Studio, or your web browser is not currently using the webcam.
  - Close background meeting applications and retry.
- **Cause 3: Multiple Cameras / External Webcams**
  - If you have an external USB webcam or virtual camera (e.g., OBS Virtual Cam), the built-in webcam may be index `1` instead of `0`.
  - In `main.py`, update `Config.camera_index = 1`.

---

## 2. Hand Landmark & Detection Issues

### Issue: Hand is in frame, but status says "SEARCHING FOR HAND..."
- **Lighting & Contrast:** Hand detection relies on clear contrast. Avoid strong backlighting (such as sitting directly in front of a bright window).
- **Hand Distance:** Position your hand 30–75 cm (1–2.5 feet) away from the webcam.
- **Orientation:** Ensure your palm or back of hand faces the camera with fingers clearly extended.
- **Confidence Threshold:** If your room has lower lighting, you can lower `min_detection_confidence` in `main.py` from `0.6` to `0.5`.

---

## 3. Mouse Movement Issues

### Issue: Hand is tracked, but the cursor does not move
- **Check Armed State:** The program begins in a **DISARMED** state.
  - Look at the top HUD bar: If it says `CONTROL: DISARMED / PAUSED`, mouse movement is intentionally stopped.
  - Click on the OpenCV video window to focus it, then press the `P` key on your keyboard to switch to `ARMED (Active)`.

### Issue: Cursor feels too jumpy or jittery
- In `main.py`, decrease `smoothing_factor` (e.g., from `0.30` to `0.15`). Lower values increase smoothing and filter out hand tremors.

### Issue: Cursor does not reach the screen edges
- Increase `margin_x` and `margin_y` in `Config` (e.g., set `margin_x = 100`, `margin_y = 80`). A larger margin means smaller hand movements cover the entire screen.

---

## 4. Click Gesture Issues

### Issue: Pinch does not register a click
- Check the distance readout rendered on the video feed.
- If your fingers cannot bring the distance below the default threshold (32 pixels), increase `pinch_threshold` to `38.0` or `42.0` in `Config`.

### Issue: Clicking triggers accidentally while moving
- Decrease `pinch_threshold` to `26.0` or `28.0`.
- Increase `pinch_stability_frames` from `2` to `3` to require a slightly more deliberate pinch.

---

## 5. Emergency Failsafe Recovery

### Alert: `PyAutoGUI Failsafe triggered by corner mouse position!`
- This occurs when the cursor hits coordinate `(0, 0)` (the top-left corner of the screen).
- The application automatically disarms mouse control to prevent unwanted behavior.
- To resume control, move your hand into the center of the camera frame, focus the OpenCV window, and press `P` to re-arm.
