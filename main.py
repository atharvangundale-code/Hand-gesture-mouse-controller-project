

from __future__ import annotations

import os
import sys
import time
import math
import urllib.request
from dataclasses import dataclass
from typing import Tuple, Optional, List

import cv2
import numpy as np
import pyautogui

# Enable PyAutoGUI Failsafe unconditionally (Security Rule 4F)
pyautogui.FAILSAFE = True
# Set minimal internal pause to keep cursor movement responsive
pyautogui.PAUSE = 0.001


# ============================================================================
# 1. Centralized Configuration
# ============================================================================
@dataclass
class Config:
    """Central configuration for camera, detection, smoothing, dragging, and scrolling."""

    # Webcam settings
    camera_index: int = 0
    camera_width: int = 1000
    camera_height: int = 800

    # Model asset path and official download source
    model_dir: str = "assets"
    model_filename: str = "hand_landmarker.task"
    model_url: str = (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    )

    # MediaPipe detection parameters
    num_hands: int = 1
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.6
    min_presence_confidence: float = 0.6

    # Interaction box margins (pixels inside webcam frame)
    margin_x: int = 80
    margin_y: int = 60

    # ------------------------------------------------------------------------
    # Ultra-Smooth Movement Settings
    # ------------------------------------------------------------------------
    adaptive_smoothing: bool = True
    smoothing_factor: float = 0.20       # Base smoothing (alpha_min) for subtle aiming
    alpha_max: float = 0.72              # Max responsiveness for swift sweeps
    jitter_cutoff_px: float = 7.5        # Continuous non-linear damping radius
    deadzone_px: float = 0.0             # Continuous damping replaces rigid deadzone

    # ------------------------------------------------------------------------
    # Drag & Click Settings
    # ------------------------------------------------------------------------
    pinch_threshold: float = 32.0        # Baseline pinch distance (pixels)
    drag_hold_sec: float = 0.50          # Hold duration to transition to drag (0.5s)
    click_cooldown_sec: float = 0.50     # Cooldown before subsequent click (0.5s)
    scale_adaptive_pinch: bool = True    # Normalize by palm size
    baseline_palm_px: float = 95.0

    enable_right_click: bool = True
    right_click_cooldown_sec: float = 0.50 # Cooldown for right-click (0.5s)

    
    # Two-Finger Scroll Settings
    
    enable_scroll: bool = True
    scroll_deadzone_px: float = 4.0      # Min vertical movement to trigger scroll
    scroll_speed_multiplier: float = 16.0 # Proportional scroll speed

    target_fps: int = 30                 # Frame rate limiter (prevents CPU busy-spin & fan noise)
    eco_idle_mode: bool = True           # Reduces CPU and battery consumption when hand is away
    idle_timeout_sec: float = 2.0        # Inactive duration before entering eco idle mode

    high_sensitivity: bool = False       # Toggle anytime via 'S' key
    normal_margin_x: int = 80
    normal_margin_y: int = 60
    compact_margin_x: int = 140
    compact_margin_y: int = 105

    # Visual display options
    window_name: str = "AI Hand Gesture Mouse Controller v1.0 [EFFICIENCY & SMOOTH]"
    flip_camera: bool = True             # Mirror video horizontally


def clamp_coordinates(
    x: float,
    y: float,
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
) -> Tuple[float, float]:
    """Clamps coordinates (x, y) to stay strictly within specified boundaries."""
    clamped_x = max(min_x, min(x, max_x))
    clamped_y = max(min_y, min(y, max_y))
    return clamped_x, clamped_y


def map_camera_to_screen(
    cam_x: float,
    cam_y: float,
    frame_w: int,
    frame_h: int,
    margin_x: int,
    margin_y: int,
    screen_w: int,
    screen_h: int,
) -> Tuple[int, int]:
    """Maps webcam pixel coordinates into screen coordinates with margin clamping."""
    box_x_min = float(margin_x)
    box_x_max = float(max(margin_x + 1, frame_w - margin_x))
    box_y_min = float(margin_y)
    box_y_max = float(max(margin_y + 1, frame_h - margin_y))

    clamped_x, clamped_y = clamp_coordinates(
        cam_x, cam_y, box_x_min, box_x_max, box_y_min, box_y_max
    )

    norm_x = (clamped_x - box_x_min) / (box_x_max - box_x_min)
    norm_y = (clamped_y - box_y_min) / (box_y_max - box_y_min)

    screen_x = int(norm_x * screen_w)
    screen_y = int(norm_y * screen_h)

    final_x = max(0, min(screen_x, screen_w - 1))
    final_y = max(0, min(screen_y, screen_h - 1))

    return final_x, final_y


class SmoothingFilter:
    """
    Continuous non-linear cursor filter:
    - Micro-movements (< 3px): smoothly dampened to absorb resting hand tremor.
    - Medium movements (3-20px): smooth continuous acceleration with zero threshold friction.
    - Fast movements (> 25px): full responsiveness with zero lag.
    """

    def __init__(
        self,
        alpha: float = 0.20,
        deadzone_px: float = 0.0,
        adaptive: bool = False,
        alpha_max: float = 0.72,
        speed_threshold_px: float = 35.0,
        jitter_cutoff_px: float = 7.5,
    ):
        if not (0.0 < alpha <= 1.0):
            raise ValueError("alpha must be strictly between 0.0 and 1.0")
        self.alpha = alpha
        self.deadzone_px = deadzone_px
        self.adaptive = adaptive
        self.alpha_max = alpha_max
        self.speed_threshold_px = speed_threshold_px
        self.jitter_cutoff_px = jitter_cutoff_px

        self.smoothed_x: Optional[float] = None
        self.smoothed_y: Optional[float] = None

    def update(self, target_x: float, target_y: float) -> Tuple[int, int]:
        """Updates filter state and returns smoothed integer coordinates."""
        if self.smoothed_x is None or self.smoothed_y is None:
            self.smoothed_x = float(target_x)
            self.smoothed_y = float(target_y)
            return int(round(self.smoothed_x)), int(round(self.smoothed_y))

        dx = float(target_x) - self.smoothed_x
        dy = float(target_y) - self.smoothed_y
        dist = math.hypot(dx, dy)

        # Legacy discrete deadzone support if requested
        if self.deadzone_px > 0.0 and dist < self.deadzone_px:
            return int(round(self.smoothed_x)), int(round(self.smoothed_y))

        if self.adaptive:
            # Continuous non-linear response: completely removes threshold stickiness
            weight = (dist / (dist + self.jitter_cutoff_px)) ** 1.35
            current_alpha = self.alpha + (self.alpha_max - self.alpha) * weight
        else:
            current_alpha = self.alpha

        self.smoothed_x += current_alpha * dx
        self.smoothed_y += current_alpha * dy

        return int(round(self.smoothed_x)), int(round(self.smoothed_y))

    def reset(self) -> None:
        """Resets filter memory when tracking is lost."""
        self.smoothed_x = None
        self.smoothed_y = None


# ============================================================================
# 3. Gesture Detection Modules (Pinch, Drag, Right-Click, Scroll)
# ============================================================================
class PinchDetector:
    """Detects distance between two fingertips with threshold and stability tracking."""

    def __init__(
        self,
        threshold: float = 32.0,
        cooldown_sec: float = 0.30,
        stability_frames: int = 2,
    ):
        self.threshold = threshold
        self.cooldown_sec = cooldown_sec
        self.stability_frames = stability_frames

        self.consecutive_pinched_frames: int = 0
        self.is_pinch_active: bool = False
        self.last_click_time: float = 0.0

    @property
    def is_pinching(self) -> bool:
        """True if fingers are currently within pinch distance."""
        return self.is_pinch_active or self.consecutive_pinched_frames > 0

    def compute_distance(
        self, pt1: Tuple[float, float], pt2: Tuple[float, float]
    ) -> float:
        """Calculates 2D Euclidean distance."""
        return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

    def update(
        self,
        thumb_tip: Optional[Tuple[float, float]],
        finger_tip: Optional[Tuple[float, float]],
        current_time: Optional[float] = None,
        effective_threshold: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """Evaluates pinch and returns (should_click, distance)."""
        if thumb_tip is None or finger_tip is None:
            self.reset()
            return False, float("inf")

        if current_time is None:
            current_time = time.time()

        thresh = effective_threshold if effective_threshold is not None else self.threshold
        distance = self.compute_distance(thumb_tip, finger_tip)
        is_physically_pinched = distance <= thresh

        should_click = False

        if is_physically_pinched:
            self.consecutive_pinched_frames += 1
            if (
                self.consecutive_pinched_frames >= self.stability_frames
                and not self.is_pinch_active
            ):
                if (current_time - self.last_click_time) >= self.cooldown_sec:
                    should_click = True
                    self.is_pinch_active = True
                    self.last_click_time = current_time
        else:
            self.consecutive_pinched_frames = 0
            self.is_pinch_active = False

        return should_click, distance

    def reset(self) -> None:
        """Resets gesture state immediately."""
        self.consecutive_pinched_frames = 0
        self.is_pinch_active = False


class DragManager:
    """
    Manages Tap-to-Click vs Hold-to-Drag:
    - Short pinch (< drag_hold_sec): keeps cursor anchored so the click doesn't slip.
    - Long pinch (>= drag_hold_sec): enters Drag Mode (mouseDown), releases anchor,
      and smoothly drags with hand movement.
    - Pinch release: drops cleanly (mouseUp).
    """

    def __init__(self, drag_hold_sec: float = 0.50, cooldown_sec: float = 0.50):
        self.drag_hold_sec = drag_hold_sec
        self.cooldown_sec = cooldown_sec

        self.pinch_start_time: Optional[float] = None
        self.anchor_screen_pos: Optional[Tuple[int, int]] = None
        self.is_dragging: bool = False
        self.last_action_time: float = 0.0

    def process(
        self,
        is_pinched: bool,
        current_screen_pos: Tuple[int, int],
        now: float,
    ) -> Tuple[bool, bool, bool, Optional[Tuple[int, int]]]:
        """
        Processes pinch state.
        Returns:
            trigger_left_click: True if a tap-click should execute
            start_drag: True if drag should begin (mouseDown)
            stop_drag: True if drag should end (mouseUp)
            override_pos: Position to override cursor during click anchor
        """
        trigger_left_click = False
        start_drag = False
        stop_drag = False
        override_pos = None

        if is_pinched:
            if self.pinch_start_time is None:
                # Pinch just began
                self.pinch_start_time = now
                self.anchor_screen_pos = current_screen_pos

            hold_duration = now - self.pinch_start_time

            if hold_duration >= self.drag_hold_sec:
                # Transition to Dragging!
                if not self.is_dragging:
                    self.is_dragging = True
                    start_drag = True
                # While dragging, anchor is released so cursor follows hand
                override_pos = None
            else:
                # Initial tap window: freeze cursor on anchor to prevent slip
                override_pos = self.anchor_screen_pos

        else:
            # Pinch released
            if self.pinch_start_time is not None:
                hold_duration = now - self.pinch_start_time

                if self.is_dragging:
                    # End drag cleanly
                    self.is_dragging = False
                    stop_drag = True
                    self.last_action_time = now
                else:
                    # Released before drag threshold -> Clean Click!
                    if (now - self.last_action_time) >= self.cooldown_sec:
                        trigger_left_click = True
                        self.last_action_time = now

                self.pinch_start_time = None
                self.anchor_screen_pos = None

        return trigger_left_click, start_drag, stop_drag, override_pos

    def reset(self) -> bool:
        """Resets drag state and returns True if drag was active and needs mouseUp."""
        was_dragging = self.is_dragging
        self.pinch_start_time = None
        self.anchor_screen_pos = None
        self.is_dragging = False
        return was_dragging


# ============================================================================
# 4. Safe Mouse Controller Wrapper
# ============================================================================
class MouseController:
    """
    Safely executes mouse movements, left/right clicks, dragging, and scrolling via PyAutoGUI.
    Enforces armed/disarmed states, failsafe protection, and screen bounds.
    """

    def __init__(self):
        self.screen_w, self.screen_h = pyautogui.size()
        self.is_armed: bool = False
        self.is_dragging: bool = False

    def arm(self) -> None:
        """Enables active mouse control."""
        self.is_armed = True

    def disarm(self) -> None:
        """Disables active mouse control and releases any active drag."""
        if self.is_dragging:
            self.mouse_up()
        self.is_armed = False

    def toggle(self) -> bool:
        """Toggles between armed and disarmed states. Returns new state."""
        if self.is_armed and self.is_dragging:
            self.mouse_up()
        self.is_armed = not self.is_armed
        return self.is_armed

    def move_to(self, target_x: int, target_y: int) -> bool:
        """Moves cursor to target coordinates if armed."""
        if not self.is_armed:
            return False

        try:
            clamped_x = max(0, min(target_x, self.screen_w - 1))
            clamped_y = max(0, min(target_y, self.screen_h - 1))
            pyautogui.moveTo(clamped_x, clamped_y, _pause=False)
            return True
        except pyautogui.FailSafeException:
            self.disarm()
            print("\n[SAFETY ALERT] PyAutoGUI Failsafe triggered by corner mouse position! Mouse DISARMED.")
            return False

    def click(self) -> bool:
        """Executes a single left click if armed."""
        if not self.is_armed:
            return False

        try:
            pyautogui.click(_pause=False)
            return True
        except pyautogui.FailSafeException:
            self.disarm()
            print("\n[SAFETY ALERT] PyAutoGUI Failsafe triggered during left click! Mouse DISARMED.")
            return False

    def right_click(self) -> bool:
        """Executes a single right click if armed."""
        if not self.is_armed:
            return False

        try:
            pyautogui.rightClick(_pause=False)
            return True
        except pyautogui.FailSafeException:
            self.disarm()
            print("\n[SAFETY ALERT] PyAutoGUI Failsafe triggered during right click! Mouse DISARMED.")
            return False

    def mouse_down(self) -> bool:
        """Presses and holds the left mouse button (initiates drag)."""
        if not self.is_armed or self.is_dragging:
            return False

        try:
            pyautogui.mouseDown(_pause=False)
            self.is_dragging = True
            return True
        except pyautogui.FailSafeException:
            self.disarm()
            return False

    def mouse_up(self) -> bool:
        """Releases the held left mouse button (drops dragged item)."""
        if not self.is_armed or not self.is_dragging:
            return False

        try:
            pyautogui.mouseUp(_pause=False)
            self.is_dragging = False
            return True
        except pyautogui.FailSafeException:
            self.is_dragging = False
            self.disarm()
            return False

    def scroll(self, amount: int) -> bool:
        """Scrolls the active window vertically."""
        if not self.is_armed:
            return False

        try:
            pyautogui.scroll(amount, _pause=False)
            return True
        except pyautogui.FailSafeException:
            self.disarm()
            return False


# ============================================================================
# 5. MediaPipe Hand Landmarker Wrapper
# ============================================================================
def ensure_model_asset(model_dir: str, model_filename: str, model_url: str) -> str:
    """Ensures official MediaPipe Hand Landmarker model exists locally."""
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, model_filename)

    if not os.path.exists(model_path):
        print(f"[MODEL SETUP] Official model asset not found at '{model_path}'.")
        print(f"[MODEL SETUP] Downloading official MediaPipe model from:\n  {model_url}")
        try:
            def _progress_hook(count, block_size, total_size):
                if total_size > 0:
                    percent = min(100, int(count * block_size * 100 / total_size))
                    sys.stdout.write(f"\r[MODEL SETUP] Downloading: {percent}%")
                    sys.stdout.flush()

            urllib.request.urlretrieve(model_url, model_path, reporthook=_progress_hook)
            sys.stdout.write("\n")
            print(f"[MODEL SETUP] Download completed successfully ({os.path.getsize(model_path)} bytes).")
        except Exception as e:
            raise FileNotFoundError(
                f"Failed to download MediaPipe model asset from '{model_url}'.\n"
                f"Please manually download 'hand_landmarker.task' and place it in '{model_dir}/'.\n"
                f"Original error: {e}"
            ) from e

    return model_path


class HandDetector:
    """Encapsulates MediaPipe Tasks HandLandmarker for real-time single-hand tracking."""

    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),        # Index finger
        (5, 9), (9, 10), (10, 11), (11, 12),   # Middle finger
        (9, 13), (13, 14), (14, 15), (15, 16), # Ring finger
        (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
        (0, 17)                                # Palm base
    ]

    def __init__(self, config: Config):
        self.config = config
        model_path = ensure_model_asset(
            config.model_dir, config.model_filename, config.model_url
        )

        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_hands=config.num_hands,
            min_hand_detection_confidence=config.min_detection_confidence,
            min_hand_presence_confidence=config.min_presence_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self.landmarker = mp_vision.HandLandmarker.create_from_options(options)

    def find_landmarks(
        self, frame_bgr: np.ndarray
    ) -> Optional[List[Tuple[int, int]]]:
        """Runs hand landmark detection on a BGR frame."""
        import mediapipe as mp

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        detection_result = self.landmarker.detect(mp_image)

        if not detection_result.hand_landmarks:
            return None

        primary_hand = detection_result.hand_landmarks[0]
        h, w, _ = frame_bgr.shape
        pixel_landmarks: List[Tuple[int, int]] = []

        for lm in primary_hand:
            px = int(lm.x * w)
            py = int(lm.y * h)
            pixel_landmarks.append((px, py))

        return pixel_landmarks

    def close(self) -> None:
        """Releases MediaPipe landmarker resources."""
        if hasattr(self, "landmarker") and self.landmarker is not None:
            self.landmarker.close()


# ============================================================================
# 6. Heads-Up Display (HUD) and Visualization Overlay
# ============================================================================
def draw_overlay(
    frame: np.ndarray,
    landmarks: Optional[List[Tuple[int, int]]],
    config: Config,
    is_armed: bool,
    mode_text: str,
    left_dist: float,
    right_dist: float,
    is_left_pinched: bool,
    is_right_pinched: bool,
    is_dragging: bool,
    fps: float,
    is_eco: bool = False,
) -> None:
    """Renders user interface guidelines, active bounds, hand skeleton, and status banners."""
    h, w, _ = frame.shape

    # 1. Active Interaction Box
    box_x1 = config.margin_x
    box_y1 = config.margin_y
    box_x2 = w - config.margin_x
    box_y2 = h - config.margin_y
    box_color = (0, 220, 255) if is_armed else (100, 100, 100)
    cv2.rectangle(frame, (box_x1, box_y1), (box_x2, box_y2), box_color, 2)
    region_title = "Active Box (High Sens)" if config.high_sensitivity else "Active Box (Normal)"
    cv2.putText(
        frame,
        region_title,
        (box_x1 + 6, box_y1 + 18),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        box_color,
        1,
        cv2.LINE_AA,
    )

    # 2. Hand Skeleton & Keypoints
    if landmarks:
        for start_idx, end_idx in HandDetector.CONNECTIONS:
            cv2.line(frame, landmarks[start_idx], landmarks[end_idx], (160, 160, 160), 2, cv2.LINE_AA)

        for pt in landmarks:
            cv2.circle(frame, pt, 3, (220, 220, 220), -1, cv2.LINE_AA)

        thumb_pt = landmarks[4]
        index_pt = landmarks[8]
        middle_pt = landmarks[12]

        # Draw Left-Click / Drag Line (Thumb to Index)
        left_color = (0, 0, 255) if is_dragging else ((0, 255, 0) if is_left_pinched else (0, 140, 255))
        cv2.line(frame, thumb_pt, index_pt, left_color, 2, cv2.LINE_AA)

        if left_dist != float("inf"):
            mid_lx = (thumb_pt[0] + index_pt[0]) // 2
            mid_ly = (thumb_pt[1] + index_pt[1]) // 2
            tag = "DRAG" if is_dragging else f"L:{int(left_dist)}px"
            cv2.putText(
                frame,
                tag,
                (mid_lx + 6, mid_ly - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                left_color,
                1,
                cv2.LINE_AA,
            )

        # Draw Right-Click Line (Thumb to Middle)
        if config.enable_right_click:
            right_color = (255, 0, 255) if is_right_pinched else (180, 80, 160)
            cv2.line(frame, thumb_pt, middle_pt, right_color, 2, cv2.LINE_AA)
            if right_dist != float("inf"):
                mid_rx = (thumb_pt[0] + middle_pt[0]) // 2
                mid_ry = (thumb_pt[1] + middle_pt[1]) // 2
                cv2.putText(
                    frame,
                    f"R:{int(right_dist)}px",
                    (mid_rx + 6, mid_ry + 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.40,
                    right_color,
                    1,
                    cv2.LINE_AA,
                )
            cv2.circle(frame, middle_pt, 7, (255, 0, 255) if is_right_pinched else (180, 50, 180), -1, cv2.LINE_AA)

        # Highlights
        cv2.circle(frame, thumb_pt, 7, (255, 200, 0), -1, cv2.LINE_AA)
        cursor_color = (0, 0, 255) if is_dragging else ((0, 255, 0) if is_armed else (0, 165, 255))
        cv2.circle(frame, index_pt, 8, cursor_color, -1, cv2.LINE_AA)
        cv2.circle(frame, index_pt, 12, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Top Status Banner (HUD Background)
    cv2.rectangle(frame, (0, 0), (w, 54), (20, 20, 20), -1)
    cv2.line(frame, (0, 54), (w, 54), (50, 50, 50), 1)

    state_label = "ARMED" if is_armed else "DISARMED / PAUSED"
    state_color = (0, 255, 0) if is_armed else (0, 140, 255)
    cv2.putText(
        frame,
        f"CONTROL: {state_label}",
        (12, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        state_color,
        2,
        cv2.LINE_AA,
    )

    # Mode / Action readout
    cv2.putText(
        frame,
        f"MODE: {mode_text}",
        (12, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (0, 255, 255) if is_dragging else (200, 200, 200),
        1,
        cv2.LINE_AA,
    )

    # Sensitivity indicator in middle of top bar
    sens_label = "[S] SENS: HIGH" if config.high_sensitivity else "[S] SENS: NORM"
    cv2.putText(
        frame,
        sens_label,
        (w // 2 - 50, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (0, 220, 255) if config.high_sensitivity else (180, 180, 180),
        1,
        cv2.LINE_AA,
    )

    # Tracking & FPS
    tracking_label = "HAND DETECTED" if landmarks else ("IDLE (ECO)" if is_eco else "SEARCHING...")
    tracking_color = (0, 255, 0) if landmarks else ((100, 200, 255) if is_eco else (0, 0, 255))
    cv2.putText(
        frame,
        tracking_label,
        (w - 180, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        tracking_color,
        1,
        cv2.LINE_AA,
    )

    fps_label = f"FPS: {fps:.0f} (ECO)" if is_eco else f"FPS: {fps:.0f}"
    cv2.putText(
        frame,
        fps_label,
        (w - 105, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )

    # 4. Bottom Controls and Safety Helper Bar
    cv2.rectangle(frame, (0, h - 30), (w, h), (20, 20, 20), -1)
    cv2.line(frame, (0, h - 30), (w, h - 30), (50, 50, 50), 1)
    helper_msg = "[P] Arm/Pause | [S] Sens | [Q/Esc] Exit | Tap=Click | Hold=Drag | 2-Fingers=Scroll"
    cv2.putText(
        frame,
        helper_msg,
        (8, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.35,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )


# ============================================================================
# 7. Main Application Controller
# ============================================================================
def run_controller() -> None:
    """Main execution loop with ultra-smooth tracking, drag-and-drop, right click, and scroll."""
    config = Config()

    print("=" * 70)
    print(" AI-Based Hand Gesture Mouse Controller (Ultra-Smooth Edition)")
    print("=" * 70)
    print(" Core Features:")
    print("  * Ultra-Smooth Tracking: Continuous non-linear anti-jitter filter")
    print("  * Tap-to-Click: Quick pinch (< 0.25s) executes Left Click without slip")
    print("  * Hold-to-Drag: Hold pinch (> 0.25s) enters Drag Mode; open to drop")
    print("  * Right-Click: Pinch Thumb+Middle (or tap Index+Middle)")
    print("  * Two-Finger Scroll: Extend Index+Middle upright and move hand up/down")
    print(" Safety Protocol:")
    print("  * Initial State: DISARMED / PAUSED (Press 'P' to activate)")
    print("  * Emergency Exit: Press 'Q' or 'Esc'")
    print("  * Corner Failsafe: Move physical mouse to any screen corner to abort")
    print("=" * 70)

    print(f"[CAM SETUP] Connecting to camera device (index={config.camera_index})...")
    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        print(f"[ERROR] Unable to open camera index {config.camera_index}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera_height)

    detector: Optional[HandDetector] = None
    try:
        print("[AI SETUP] Initializing MediaPipe HandLandmarker...")
        detector = HandDetector(config)
    except Exception as e:
        print(f"[ERROR] Failed to initialize MediaPipe HandLandmarker: {e}")
        cap.release()
        return

    mouse = MouseController()
    smoother = SmoothingFilter(
        alpha=config.smoothing_factor,
        deadzone_px=config.deadzone_px,
        adaptive=config.adaptive_smoothing,
        alpha_max=config.alpha_max,
        jitter_cutoff_px=config.jitter_cutoff_px,
    )

    drag_mgr = DragManager(
        drag_hold_sec=config.drag_hold_sec,
        cooldown_sec=config.click_cooldown_sec,
    )

    right_pinch_detector = PinchDetector(
        threshold=config.pinch_threshold,
        cooldown_sec=config.right_click_cooldown_sec,
        stability_frames=2,
    )

    prev_scroll_y: Optional[float] = None
    frame_count = 0
    start_time = time.time()
    last_hand_seen_time = time.time()
    fps = 0.0

    try:
        while True:
            frame_start = time.time()
            success, frame = cap.read()
            if not success or frame is None:
                print("\n[WARNING] Camera frame dropped or disconnected.")
                break

            if config.flip_camera:
                frame = cv2.flip(frame, 1)

            frame_count += 1
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0.0

            landmarks = detector.find_landmarks(frame)

            left_dist = float("inf")
            right_dist = float("inf")
            is_left_pinched = False
            is_right_pinched = False
            mode_text = "Idle"

            if landmarks is not None:
                last_hand_seen_time = time.time()
                thumb_pt = landmarks[4]
                index_pt = landmarks[8]
                middle_pt = landmarks[12]
                palm_pt = landmarks[0]
                mcp_pt = landmarks[9]

                # Hand scale normalization
                palm_size = math.hypot(palm_pt[0] - mcp_pt[0], palm_pt[1] - mcp_pt[1])
                scale_ratio = max(0.5, min(1.8, palm_size / config.baseline_palm_px)) if config.scale_adaptive_pinch else 1.0
                effective_thresh = config.pinch_threshold * scale_ratio

                now = time.time()

                # Calculate fingertip distances
                left_dist = math.hypot(thumb_pt[0] - index_pt[0], thumb_pt[1] - index_pt[1])
                right_dist = math.hypot(thumb_pt[0] - middle_pt[0], thumb_pt[1] - middle_pt[1])
                index_middle_dist = math.hypot(index_pt[0] - middle_pt[0], index_pt[1] - middle_pt[1])

                # Check Two-Finger Upright Gesture (Scroll Mode)
                # Index tip 8 above PIP 6, Middle tip 12 above PIP 10, Ring 16 below PIP 14, Pinky 20 below PIP 18
                is_index_extended = index_pt[1] < landmarks[6][1]
                is_middle_extended = middle_pt[1] < landmarks[10][1]
                is_ring_curled = landmarks[16][1] > landmarks[14][1]
                is_pinky_curled = landmarks[20][1] > landmarks[18][1]

                is_two_finger_scroll = (
                    config.enable_scroll
                    and is_index_extended
                    and is_middle_extended
                    and is_ring_curled
                    and is_pinky_curled
                    and left_dist > effective_thresh * 1.3
                    and right_dist > effective_thresh * 1.3
                )

                # Evaluate Right-Click (Thumb+Middle pinch OR Index+Middle tap)
                is_right_pinch_candidate = (
                    config.enable_right_click
                    and not is_two_finger_scroll
                    and (
                        (right_dist <= effective_thresh and right_dist < left_dist + 6.0)
                        or (index_middle_dist <= effective_thresh * 0.95 and left_dist > effective_thresh * 1.2)
                    )
                )

                should_right_click = False
                if is_right_pinch_candidate:
                    is_right_pinched = True
                    should_right_click, _ = right_pinch_detector.update(
                        thumb_tip=thumb_pt,
                        finger_tip=middle_pt,
                        current_time=now,
                        effective_threshold=effective_thresh,
                    )
                else:
                    right_pinch_detector.reset()

                # Evaluate Left-Click / Drag (Thumb + Index pinch)
                # Only if not actively right-clicking or scrolling
                is_left_pinched = (
                    (left_dist <= effective_thresh)
                    and not is_right_pinched
                    and not is_two_finger_scroll
                )

                # Map index fingertip to screen
                screen_x, screen_y = map_camera_to_screen(
                    cam_x=index_pt[0],
                    cam_y=index_pt[1],
                    frame_w=frame.shape[1],
                    frame_h=frame.shape[0],
                    margin_x=config.margin_x,
                    margin_y=config.margin_y,
                    screen_w=mouse.screen_w,
                    screen_h=mouse.screen_h,
                )

                # 1. Handle Scrolling Mode
                if is_two_finger_scroll:
                    drag_mgr.reset()
                    if mouse.is_dragging:
                        mouse.mouse_up()

                    current_mid_y = (index_pt[1] + middle_pt[1]) / 2.0
                    if prev_scroll_y is not None:
                        dy = current_mid_y - prev_scroll_y
                        if abs(dy) >= config.scroll_deadzone_px:
                            scroll_amount = int(-dy * config.scroll_speed_multiplier)
                            mouse.scroll(scroll_amount)
                            mode_text = "Scroll UP" if scroll_amount > 0 else "Scroll DOWN"
                        else:
                            mode_text = "Scroll Ready"
                    else:
                        mode_text = "Scroll Ready"
                    prev_scroll_y = current_mid_y

                else:
                    prev_scroll_y = None

                    # 2. Process Drag and Tap-Click State Machine
                    (
                        trigger_click,
                        start_drag,
                        stop_drag,
                        override_pos,
                    ) = drag_mgr.process(
                        is_pinched=is_left_pinched,
                        current_screen_pos=(screen_x, screen_y),
                        now=now,
                    )

                    # Determine target cursor coordinates
                    if override_pos is not None:
                        # Tap anchor: freeze cursor temporarily during tap
                        final_x, final_y = override_pos
                        mode_text = "Target Lock"
                    else:
                        # Smooth glide
                        final_x, final_y = smoother.update(screen_x, screen_y)
                        mode_text = "Dragging" if drag_mgr.is_dragging else "Tracking"

                    # 3. Execute Mouse Actions (if armed)
                    if mouse.is_armed:
                        # Move cursor
                        mouse.move_to(final_x, final_y)

                        # Handle Drag start/stop
                        if start_drag:
                            mouse.mouse_down()
                            print("[ACTION] Drag Mode Started (mouseDown)")
                        elif stop_drag:
                            mouse.mouse_up()
                            print("[ACTION] Drag Mode Released (mouseUp)")

                        # Handle Clicks
                        if trigger_click:
                            mouse.click()
                            mode_text = "Left Click!"
                            print("[ACTION] Left Click executed")
                        elif should_right_click:
                            mouse.right_click()
                            mode_text = "Right Click!"
                            print("[ACTION] Right Click executed")

            else:
                # Tracking lost: Reset all states safely
                smoother.reset()
                was_dragging = drag_mgr.reset()
                if was_dragging and mouse.is_armed:
                    mouse.mouse_up()
                right_pinch_detector.reset()
                prev_scroll_y = None
                mode_text = "Searching..."

            # Check Eco Idle Mode
            is_eco = (
                config.eco_idle_mode
                and (time.time() - last_hand_seen_time > config.idle_timeout_sec)
            )

            # Render HUD
            draw_overlay(
                frame=frame,
                landmarks=landmarks,
                config=config,
                is_armed=mouse.is_armed,
                mode_text=mode_text,
                left_dist=left_dist,
                right_dist=right_dist,
                is_left_pinched=is_left_pinched,
                is_right_pinched=is_right_pinched,
                is_dragging=drag_mgr.is_dragging,
                fps=fps,
                is_eco=is_eco,
            )

            cv2.imshow(config.window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                print("\n[USER ACTION] Emergency exit key pressed. Shutting down cleanly...")
                break
            elif key in (ord("p"), ord("P")):
                new_state = mouse.toggle()
                status_str = "ARMED (Active)" if new_state else "DISARMED / PAUSED"
                print(f"[USER ACTION] Mouse control toggled: {status_str}")
            elif key in (ord("s"), ord("S")):
                config.high_sensitivity = not config.high_sensitivity
                if config.high_sensitivity:
                    config.margin_x = config.compact_margin_x
                    config.margin_y = config.compact_margin_y
                    print("[EFFICIENCY] Sensitivity Mode: HIGH (Low-Fatigue Wrist Mode)")
                else:
                    config.margin_x = config.normal_margin_x
                    config.margin_y = config.normal_margin_y
                    print("[EFFICIENCY] Sensitivity Mode: NORMAL (Standard Mode)")

            # Frame Rate Governor (Limits CPU busy-spin & preserves laptop battery)
            elapsed_frame = time.time() - frame_start
            target_fps = 15.0 if is_eco else float(config.target_fps)
            target_interval = 1.0 / target_fps
            if elapsed_frame < target_interval:
                time.sleep(target_interval - elapsed_frame)

    except KeyboardInterrupt:
        print("\n[USER ACTION] Keyboard interrupt received (Ctrl+C). Exiting...")
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] An error occurred during execution: {e}")
    finally:
        print("[CLEANUP] Ensuring mouse button is released...")
        if mouse.is_dragging:
            mouse.mouse_up()
        print("[CLEANUP] Releasing webcam...")
        cap.release()
        print("[CLEANUP] Closing OpenCV windows...")
        cv2.destroyAllWindows()
        if detector is not None:
            print("[CLEANUP] Closing MediaPipe detector...")
            detector.close()
        print("[CLEANUP] All resources released cleanly. Process complete.")


if __name__ == "__main__":
    run_controller()
