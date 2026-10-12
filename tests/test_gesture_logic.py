"""
Unit tests for pinch gesture recognition, click edge detection, cooldown logic,
right-click support, drag-and-drop state machine, and safe mouse controller.
Uses unittest.mock to ensure zero desktop interference.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import PinchDetector, DragManager, MouseController
import pyautogui


class TestPinchGestureLogic(unittest.TestCase):
    def setUp(self):
        self.detector = PinchDetector(
            threshold=30.0,
            cooldown_sec=0.30,
            stability_frames=2,
        )

    def test_euclidean_distance_calculation(self):
        """Calculates correct Euclidean distance between two points."""
        dist = self.detector.compute_distance((0.0, 0.0), (3.0, 4.0))
        self.assertAlmostEqual(dist, 5.0)

    def test_fingers_apart_no_click(self):
        """Fingers wider than threshold should never trigger a click."""
        thumb = (100.0, 100.0)
        index = (160.0, 100.0)
        should_click, dist = self.detector.update(thumb, index, current_time=1.0)
        self.assertFalse(should_click)
        self.assertEqual(dist, 60.0)
        self.assertFalse(self.detector.is_pinching)

    def test_gesture_stability_debounce(self):
        """A pinch must persist for minimum stability frames before triggering a click."""
        thumb = (100.0, 100.0)
        index = (120.0, 100.0)

        should_click1, dist1 = self.detector.update(thumb, index, current_time=1.0)
        self.assertFalse(should_click1, "Click triggered prematurely on first frame")
        self.assertTrue(self.detector.is_pinching)

        should_click2, dist2 = self.detector.update(thumb, index, current_time=1.03)
        self.assertTrue(should_click2, "Click should trigger once stability requirement is met")
        self.assertTrue(self.detector.is_pinch_active)
        self.assertTrue(self.detector.is_pinching)

    def test_edge_triggered_click_prevents_spam_while_holding(self):
        """Holding fingers pinched together across many frames must NOT generate repeated clicks."""
        thumb = (100.0, 100.0)
        index = (120.0, 100.0)

        self.detector.update(thumb, index, current_time=1.0)
        should_click_trigger, _ = self.detector.update(thumb, index, current_time=1.03)
        self.assertTrue(should_click_trigger)

        for frame_idx in range(3, 11):
            simulated_time = 1.03 + (frame_idx * 0.03)
            should_click_hold, _ = self.detector.update(thumb, index, current_time=simulated_time)
            self.assertFalse(
                should_click_hold,
                f"Repeated click falsely generated on frame {frame_idx} while holding pinch",
            )

    def test_click_cooldown_enforcement(self):
        """Rapidly releasing and re-pinching before cooldown expires must be blocked."""
        thumb = (100.0, 100.0)
        index_pinched = (120.0, 100.0)
        index_released = (180.0, 100.0)

        self.detector.update(thumb, index_pinched, current_time=1.0)
        click1, _ = self.detector.update(thumb, index_pinched, current_time=1.03)
        self.assertTrue(click1)

        self.detector.update(thumb, index_released, current_time=1.06)

        self.detector.update(thumb, index_pinched, current_time=1.10)
        click2_early, _ = self.detector.update(thumb, index_pinched, current_time=1.13)
        self.assertFalse(click2_early, "Click was registered before cooldown period expired")

        self.detector.update(thumb, index_released, current_time=1.35)
        self.detector.update(thumb, index_pinched, current_time=1.38)
        click2_valid, _ = self.detector.update(thumb, index_pinched, current_time=1.42)
        self.assertTrue(click2_valid, "Click should be permitted once cooldown period has elapsed")

    def test_effective_threshold_scaling(self):
        """Dynamic effective threshold must override base threshold when passed."""
        thumb = (100.0, 100.0)
        index = (145.0, 100.0)

        c1, _ = self.detector.update(thumb, index, current_time=1.0)
        self.assertFalse(c1)

        self.detector.update(thumb, index, current_time=1.0, effective_threshold=50.0)
        c2, _ = self.detector.update(thumb, index, current_time=1.03, effective_threshold=50.0)
        self.assertTrue(c2)

    def test_hand_loss_resets_state(self):
        """Losing hand tracking immediately resets active pinch and counters."""
        thumb = (100.0, 100.0)
        index = (120.0, 100.0)

        self.detector.update(thumb, index, current_time=1.0)
        self.detector.update(thumb, index, current_time=1.03)
        self.assertTrue(self.detector.is_pinch_active)

        should_click, dist = self.detector.update(None, None)
        self.assertFalse(should_click)
        self.assertEqual(dist, float("inf"))
        self.assertFalse(self.detector.is_pinch_active)
        self.assertEqual(self.detector.consecutive_pinched_frames, 0)


class TestDragManager(unittest.TestCase):
    def setUp(self):
        self.drag_mgr = DragManager(drag_hold_sec=0.50, cooldown_sec=0.50)

    def test_tap_triggers_click(self):
        """Pinch held under half a second (< 0.50s) then released triggers click."""
        # Pinch begins at t=1.00s
        click1, start_drag1, stop_drag1, override1 = self.drag_mgr.process(
            is_pinched=True, current_screen_pos=(500, 300), now=1.00
        )
        self.assertFalse(click1)
        self.assertFalse(start_drag1)
        self.assertEqual(override1, (500, 300), "Should anchor cursor during tap")

        # Pinch released at t=1.30s (held for 0.30s < 0.50s)
        click2, start_drag2, stop_drag2, override2 = self.drag_mgr.process(
            is_pinched=False, current_screen_pos=(500, 300), now=1.30
        )
        self.assertTrue(click2, "Releasing pinch under 0.50s should trigger click")
        self.assertFalse(start_drag2)
        self.assertFalse(stop_drag2)

    def test_hold_triggers_drag_and_release(self):
        """Holding pinch for half a second (>= 0.50s) triggers drag mode, and releasing triggers stop_drag."""
        # Pinch begins at t=1.00s
        self.drag_mgr.process(is_pinched=True, current_screen_pos=(500, 300), now=1.00)

        # Still holding at t=1.55s (held for 0.55s >= 0.50s)
        click, start_drag, stop_drag, override = self.drag_mgr.process(
            is_pinched=True, current_screen_pos=(600, 400), now=1.55
        )
        self.assertFalse(click)
        self.assertTrue(start_drag, "Holding pinch >= 0.50s should enter drag mode")
        self.assertFalse(stop_drag)
        self.assertIsNone(override, "Anchor should be released so cursor can drag")
        self.assertTrue(self.drag_mgr.is_dragging)

        # Release pinch at t=1.90s
        click_rel, start_rel, stop_rel, override_rel = self.drag_mgr.process(
            is_pinched=False, current_screen_pos=(700, 500), now=1.90
        )
        self.assertFalse(click_rel, "Releasing from a drag should NOT trigger another click")
        self.assertFalse(start_rel)
        self.assertTrue(stop_rel, "Releasing drag should emit stop_drag")
        self.assertFalse(self.drag_mgr.is_dragging)


class TestMouseControllerSafety(unittest.TestCase):
    @patch("pyautogui.size", return_value=(1920, 1080))
    def setUp(self, mock_size):
        self.controller = MouseController()

    def test_controller_disarmed_by_default(self):
        """Security Protocol: Controller MUST initialize in a disarmed state."""
        self.assertFalse(self.controller.is_armed)

    @patch("pyautogui.moveTo")
    @patch("pyautogui.click")
    @patch("pyautogui.rightClick")
    @patch("pyautogui.mouseDown")
    @patch("pyautogui.mouseUp")
    @patch("pyautogui.scroll")
    def test_actions_blocked_when_disarmed(self, mock_scroll, mock_mu, mock_md, mock_rc, mock_click, mock_moveTo):
        """No cursor actions may execute while disarmed."""
        self.assertFalse(self.controller.move_to(500, 400))
        self.assertFalse(self.controller.click())
        self.assertFalse(self.controller.right_click())
        self.assertFalse(self.controller.mouse_down())
        self.assertFalse(self.controller.mouse_up())
        self.assertFalse(self.controller.scroll(100))

        mock_moveTo.assert_not_called()
        mock_click.assert_not_called()
        mock_rc.assert_not_called()
        mock_md.assert_not_called()
        mock_mu.assert_not_called()
        mock_scroll.assert_not_called()

    def test_arm_and_disarm_state_transitions(self):
        """Arming, disarming, and toggling must transition state predictably."""
        self.controller.arm()
        self.assertTrue(self.controller.is_armed)

        self.controller.disarm()
        self.assertFalse(self.controller.is_armed)

        new_state = self.controller.toggle()
        self.assertTrue(new_state)
        self.assertTrue(self.controller.is_armed)

    @patch("pyautogui.moveTo")
    @patch("pyautogui.click")
    @patch("pyautogui.rightClick")
    @patch("pyautogui.mouseDown")
    @patch("pyautogui.mouseUp")
    @patch("pyautogui.scroll")
    def test_actions_executed_when_armed(self, mock_scroll, mock_mu, mock_md, mock_rc, mock_click, mock_moveTo):
        """All mouse actions must execute when armed."""
        self.controller.arm()

        self.assertTrue(self.controller.move_to(500, 400))
        self.assertTrue(self.controller.click())
        self.assertTrue(self.controller.right_click())
        self.assertTrue(self.controller.mouse_down())
        self.assertTrue(self.controller.mouse_up())
        self.assertTrue(self.controller.scroll(120))

        mock_moveTo.assert_called_once_with(500, 400, _pause=False)
        mock_click.assert_called_once_with(_pause=False)
        mock_rc.assert_called_once_with(_pause=False)
        mock_md.assert_called_once_with(_pause=False)
        mock_mu.assert_called_once_with(_pause=False)
        mock_scroll.assert_called_once_with(120, _pause=False)

    @patch("pyautogui.moveTo", side_effect=pyautogui.FailSafeException("Corner hit"))
    def test_failsafe_exception_safely_disarms(self, mock_moveTo):
        """Triggering PyAutoGUI failsafe must disarm controller immediately."""
        self.controller.arm()
        self.assertTrue(self.controller.is_armed)

        result = self.controller.move_to(0, 0)
        self.assertFalse(result)
        self.assertFalse(self.controller.is_armed)


if __name__ == "__main__":
    unittest.main()
