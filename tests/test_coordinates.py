"""
Unit tests for coordinate mapping, boundary clamping, and cursor smoothing.
Verifies pure mathematical operations and stability filters without requiring
camera or desktop access.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import clamp_coordinates, map_camera_to_screen, SmoothingFilter


class TestCoordinateOperations(unittest.TestCase):
    def test_clamp_coordinates_within_bounds(self):
        """Values within valid boundaries should remain unchanged."""
        cx, cy = clamp_coordinates(100.0, 150.0, 50.0, 200.0, 50.0, 300.0)
        self.assertEqual(cx, 100.0)
        self.assertEqual(cy, 150.0)

    def test_clamp_coordinates_exceeding_bounds(self):
        """Values outside boundary range must be strictly clamped to min and max."""
        cx1, cy1 = clamp_coordinates(10.0, 20.0, 50.0, 200.0, 50.0, 300.0)
        self.assertEqual(cx1, 50.0)
        self.assertEqual(cy1, 50.0)

        cx2, cy2 = clamp_coordinates(350.0, 500.0, 50.0, 200.0, 50.0, 300.0)
        self.assertEqual(cx2, 200.0)
        self.assertEqual(cy2, 300.0)

    def test_map_camera_to_screen_center(self):
        """Center of camera interaction box must map directly to the center of the screen."""
        frame_w, frame_h = 640, 480
        margin_x, margin_y = 80, 60
        screen_w, screen_h = 1920, 1080

        center_cam_x = frame_w / 2.0
        center_cam_y = frame_h / 2.0

        sx, sy = map_camera_to_screen(
            cam_x=center_cam_x,
            cam_y=center_cam_y,
            frame_w=frame_w,
            frame_h=frame_h,
            margin_x=margin_x,
            margin_y=margin_y,
            screen_w=screen_w,
            screen_h=screen_h,
        )

        self.assertAlmostEqual(sx, screen_w // 2, delta=2)
        self.assertAlmostEqual(sy, screen_h // 2, delta=2)

    def test_map_camera_to_screen_edges_and_clamping(self):
        """Points at or beyond the margins must clamp cleanly to screen boundaries."""
        frame_w, frame_h = 640, 480
        margin_x, margin_y = 80, 60
        screen_w, screen_h = 1920, 1080

        sx_tl, sy_tl = map_camera_to_screen(
            cam_x=margin_x,
            cam_y=margin_y,
            frame_w=frame_w,
            frame_h=frame_h,
            margin_x=margin_x,
            margin_y=margin_y,
            screen_w=screen_w,
            screen_h=screen_h,
        )
        self.assertEqual(sx_tl, 0)
        self.assertEqual(sy_tl, 0)

        sx_neg, sy_neg = map_camera_to_screen(
            cam_x=-50.0,
            cam_y=-50.0,
            frame_w=frame_w,
            frame_h=frame_h,
            margin_x=margin_x,
            margin_y=margin_y,
            screen_w=screen_w,
            screen_h=screen_h,
        )
        self.assertEqual(sx_neg, 0)
        self.assertEqual(sy_neg, 0)

        sx_br, sy_br = map_camera_to_screen(
            cam_x=frame_w - margin_x,
            cam_y=frame_h - margin_y,
            frame_w=frame_w,
            frame_h=frame_h,
            margin_x=margin_x,
            margin_y=margin_y,
            screen_w=screen_w,
            screen_h=screen_h,
        )
        self.assertGreaterEqual(sx_br, screen_w - 2)
        self.assertGreaterEqual(sy_br, screen_h - 2)
        self.assertLess(sx_br, screen_w)
        self.assertLess(sy_br, screen_h)


class TestSmoothingFilter(unittest.TestCase):
    def test_smoothing_filter_initialization(self):
        """The first update must set the smoothed position immediately without lag."""
        smoother = SmoothingFilter(alpha=0.25)
        x, y = smoother.update(500, 300)
        self.assertEqual(x, 500)
        self.assertEqual(y, 300)

    def test_smoothing_filter_interpolation(self):
        """Subsequent updates must apply Exponential Moving Average (EMA)."""
        smoother = SmoothingFilter(alpha=0.50)
        smoother.update(0, 0)
        x, y = smoother.update(100, 200)

        self.assertEqual(x, 50)
        self.assertEqual(y, 100)

    def test_deadzone_eliminates_micro_jitter(self):
        """Movements below deadzone threshold must freeze the cursor completely."""
        smoother = SmoothingFilter(alpha=0.30, deadzone_px=5.0)
        smoother.update(500, 500)

        # Micro jitter of 2-3 pixels should not alter cursor position
        x1, y1 = smoother.update(502, 501)
        self.assertEqual(x1, 500)
        self.assertEqual(y1, 500)

        # Deliberate movement exceeding 5px deadzone should update cursor
        x2, y2 = smoother.update(520, 520)
        self.assertGreater(x2, 500)
        self.assertGreater(y2, 500)

    def test_adaptive_smoothing_acceleration(self):
        """Fast hand movements must dynamically scale alpha for responsive tracking."""
        # Non-adaptive slow filter
        slow_smoother = SmoothingFilter(alpha=0.10, adaptive=False)
        slow_smoother.update(0, 0)
        slow_x, _ = slow_smoother.update(200, 0)

        # Adaptive filter with alpha_min=0.10, alpha_max=0.80
        fast_smoother = SmoothingFilter(
            alpha=0.10,
            adaptive=True,
            alpha_max=0.80,
            speed_threshold_px=50.0,
        )
        fast_smoother.update(0, 0)
        fast_x, _ = fast_smoother.update(200, 0)

        self.assertGreater(fast_x, slow_x, "Adaptive filter should respond faster on large sweeps")

    def test_smoothing_filter_reset_on_tracking_loss(self):
        """Resetting the filter prevents teleportation jumps when tracking is restored."""
        smoother = SmoothingFilter(alpha=0.25)
        smoother.update(100, 100)
        smoother.update(120, 120)

        smoother.reset()
        self.assertIsNone(smoother.smoothed_x)
        self.assertIsNone(smoother.smoothed_y)

        new_x, new_y = smoother.update(900, 800)
        self.assertEqual(new_x, 900)
        self.assertEqual(new_y, 800)

    def test_smoothing_filter_invalid_alpha(self):
        """Alpha values <= 0 or > 1 must raise ValueError."""
        with self.assertRaises(ValueError):
            SmoothingFilter(alpha=0.0)
        with self.assertRaises(ValueError):
            SmoothingFilter(alpha=-0.5)
        with self.assertRaises(ValueError):
            SmoothingFilter(alpha=1.5)


if __name__ == "__main__":
    unittest.main()
