# Safety and Security Protocol (Version 1.0)

Controlling computer mouse cursors through artificial vision algorithms involves physical interaction with operating system desktops. The **AI-Based Hand Gesture Mouse Controller** is built from the ground up with defensive programming principles and strict cybersecurity safeguards.

---

## 1. Safety Pillars

### A. Safe Mouse Control & Disarmed by Default
- **Disarmed Initialization:** When the application starts, mouse movement and clicking are strictly disabled (`is_armed = False`).
- **Deliberate Activation:** The user must explicitly press the keyboard shortcut `P` to arm the controller.
- **Immediate Pause:** Pressing `P` at any moment immediately halts all cursor movement and clicking.
- **Fail-Closed on Tracking Loss:** The moment a hand leaves the camera's field of view, mouse movement stops instantly. No speculative or inertia-based movement occurs.
- **Zero Click Spam:** The pinch gesture uses edge-triggered state detection coupled with a minimum 2-frame stability debounce and a cooldown window (0.35s). Holding fingers together produces exactly **one** left-click.

### B. Hardware & Emergency Interrupts
- **Primary Emergency Exit:** Pressing `Q` or `Esc` while viewing the camera stream immediately terminates the main loop and runs the cleanup sequence.
- **PyAutoGUI Hardware Failsafe (`FAILSAFE = True`):** PyAutoGUI has a built-in safety mechanism that detects if the mouse pointer moves to any extreme screen corner (e.g., `(0, 0)`).
  - This application **never** disables `FAILSAFE`.
  - If a failsafe is triggered, the application catches the `FailSafeException`, immediately disarms mouse control, and logs an alert.
- **Clean Resource Deallocation:** All OpenCV video streams and MediaPipe landmarker pipelines are encapsulated in `try ... finally` blocks, guaranteeing that the webcam indicator light turns off when the application stops.

### C. Privacy & Local Execution
- **100% Local Inference:** All computer vision processing happens on the laptop's CPU.
- **No Video Recording:** Webcam frames are captured directly into volatile system memory (RAM) and overwritten each frame. No video files, images, or landmarks are written to disk.
- **No Network Telemetry:** The application contains zero telemetry, analytics, tracking, or network transmission code.
- **No Facial Recognition:** Hand tracking utilizes solely the MediaPipe hand landmark model. No face detection, biometric profiling, or identity tracking is present.

---

## 2. Operational Limitations

Version 1.0 is intentionally constrained for safety:
1. **Single Hand Only:** Tracks one primary hand (`num_hands=1`). Multiple hands will not cause conflicting cursor jumps.
2. **Left-Click Only:** Right-click, middle-click, scroll, drag-and-drop, and keyboard typing are disabled.
3. **No Background Thread Execution:** All vision and input logic runs synchronously on the main thread. No unmonitored background threads can hijack mouse controls.
4. **No Privilege Escalation:** Does not require administrator/root privileges or bypass operating-system permission boundaries.

---

## 3. Responsible Usage Guidelines

1. **Harmless Test Environment:** Always demonstrate and test the application on a clean desktop or a blank browser tab.
2. **Never Test on Sensitive Applications:** Do not operate the gesture controller when interacting with online banking, payment portals, database management consoles, or system terminals.
3. **Always Disarm Before Leaving:** If stepping away from your laptop, press `P` or `Q` to shut down or disarm control so pets, reflections, or passersby do not trigger inadvertent inputs.
