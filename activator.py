"""
AI-Based Hand Gesture Mouse Controller — Activation Application (GUI)
======================================================================
A sleek, modern desktop activation dashboard to configure and launch
the hand gesture controller with a single click.
"""

import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox


class ActivatorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Gesture Mouse — Activation Panel")
        self.root.geometry("520x620")
        self.root.resizable(False, False)

        self.base_dir = os.path.abspath(os.path.dirname(__file__))
        self.icon_path = os.path.join(self.base_dir, "app_icon.ico")

        # Set window icon
        if os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        # Dark theme color palette
        self.bg_color = "#121826"       # Deep dark background
        self.card_color = "#1b2336"     # Card panel
        self.accent_cyan = "#00d2ff"    # Primary cyan glow
        self.accent_green = "#00e676"   # Active / running green
        self.accent_red = "#ff3d71"     # Stop / error red
        self.text_main = "#ffffff"      # High contrast text
        self.text_dim = "#9aa5b8"       # Secondary text

        self.root.configure(bg=self.bg_color)

        self.process: subprocess.Popen | None = None
        self.is_running = False

        self._build_ui()

    def _build_ui(self):
        # 1. Header Section
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=15)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="AI Gesture Mouse Controller",
            font=("Segoe UI", 16, "bold"),
            fg=self.accent_cyan,
            bg=self.bg_color,
        )
        title_lbl.pack()

        subtitle_lbl = tk.Label(
            header_frame,
            text="Touchless Webcam Laptop Control — Version 1.0",
            font=("Segoe UI", 9),
            fg=self.text_dim,
            bg=self.bg_color,
        )
        subtitle_lbl.pack(pady=(2, 0))

        # 2. Main Control Card
        control_card = tk.Frame(
            self.root, bg=self.card_color, bd=1, relief=tk.SOLID, padx=20, pady=18
        )
        control_card.pack(fill=tk.X, padx=24, pady=8)

        # Status row
        status_row = tk.Frame(control_card, bg=self.card_color)
        status_row.pack(fill=tk.X, pady=(0, 14))

        status_tag = tk.Label(
            status_row, text="STATUS:", font=("Segoe UI", 10, "bold"), fg=self.text_dim, bg=self.card_color
        )
        status_tag.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            status_row,
            text="● READY TO ACTIVATE",
            font=("Segoe UI", 10, "bold"),
            fg=self.accent_cyan,
            bg=self.card_color,
        )
        self.status_lbl.pack(side=tk.LEFT, padx=10)

        # Big Activate / Stop Button
        self.action_btn = tk.Button(
            control_card,
            text="▶  ACTIVATE CONTROLLER",
            font=("Segoe UI", 12, "bold"),
            bg=self.accent_cyan,
            fg="#0b111e",
            activebackground="#33ddff",
            activeforeground="#0b111e",
            bd=0,
            padx=20,
            pady=12,
            cursor="hand2",
            command=self.toggle_activation,
        )
        self.action_btn.pack(fill=tk.X)

        # Secondary Quick Diagnostic Button
        diag_btn = tk.Button(
            control_card,
            text="🔍  Test Webcam Hardware Feed",
            font=("Segoe UI", 9),
            bg=self.card_color,
            fg=self.text_dim,
            activebackground="#26314a",
            activeforeground=self.text_main,
            bd=1,
            relief=tk.SOLID,
            pady=6,
            cursor="hand2",
            command=self.run_webcam_test,
        )
        diag_btn.pack(fill=tk.X, pady=(10, 0))

        # 3. Settings Configuration Card
        settings_card = tk.Frame(
            self.root, bg=self.card_color, bd=1, relief=tk.SOLID, padx=20, pady=14
        )
        settings_card.pack(fill=tk.X, padx=24, pady=8)

        settings_title = tk.Label(
            settings_card,
            text="QUICK PREFERENCES",
            font=("Segoe UI", 9, "bold"),
            fg=self.accent_cyan,
            bg=self.card_color,
        )
        settings_title.pack(anchor=tk.W, pady=(0, 8))

        # Camera Index
        cam_row = tk.Frame(settings_card, bg=self.card_color)
        cam_row.pack(fill=tk.X, pady=4)
        tk.Label(
            cam_row, text="Camera Index:", font=("Segoe UI", 9), fg=self.text_main, bg=self.card_color
        ).pack(side=tk.LEFT)
        self.cam_var = tk.StringVar(value="0")
        cam_spin = ttk.Combobox(cam_row, textvariable=self.cam_var, values=["0 (Default)", "1 (External)", "2"], width=14, state="readonly")
        cam_spin.pack(side=tk.RIGHT)

        # Sensitivity Mode
        sens_row = tk.Frame(settings_card, bg=self.card_color)
        sens_row.pack(fill=tk.X, pady=4)
        tk.Label(
            sens_row, text="Initial Sensitivity:", font=("Segoe UI", 9), fg=self.text_main, bg=self.card_color
        ).pack(side=tk.LEFT)
        self.sens_var = tk.StringVar(value="Normal (Standard)")
        sens_combo = ttk.Combobox(
            sens_row, textvariable=self.sens_var, values=["Normal (Standard)", "High (Low-Fatigue Wrist)"], width=14, state="readonly"
        )
        sens_combo.pack(side=tk.RIGHT)

        # Click Hold Timing
        click_row = tk.Frame(settings_card, bg=self.card_color)
        click_row.pack(fill=tk.X, pady=4)
        tk.Label(
            click_row, text="Click Timing:", font=("Segoe UI", 9), fg=self.text_main, bg=self.card_color
        ).pack(side=tk.LEFT)
        self.click_var = tk.StringVar(value="0.50s (Relaxed)")
        click_combo = ttk.Combobox(
            click_row, textvariable=self.click_var, values=["0.50s (Relaxed)", "0.25s (Fast)"], width=14, state="readonly"
        )
        click_combo.pack(side=tk.RIGHT)

        # 4. Keyboard & Gestures Quick Guide
        guide_card = tk.Frame(
            self.root, bg=self.card_color, bd=1, relief=tk.SOLID, padx=20, pady=12
        )
        guide_card.pack(fill=tk.X, padx=24, pady=8)

        guide_title = tk.Label(
            guide_card,
            text="GESTURE CHEAT SHEET",
            font=("Segoe UI", 9, "bold"),
            fg=self.accent_cyan,
            bg=self.card_color,
        )
        guide_title.pack(anchor=tk.W, pady=(0, 6))

        cheats = [
            ("P", "Arm / Pause mouse control"),
            ("S", "Toggle Sensitivity (Low-Fatigue Mode)"),
            ("Q / Esc", "Emergency clean exit"),
            ("Pinch (< 0.5s)", "Left Click"),
            ("Hold Pinch (> 0.5s)", "Drag window / slider / text"),
            ("Thumb + Middle", "Right Click"),
            ("Two Fingers Up/Down", "Vertical Page Scroll"),
        ]

        for key, desc in cheats:
            row = tk.Frame(guide_card, bg=self.card_color)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row, text=key, font=("Segoe UI", 8, "bold"), fg=self.accent_green, bg=self.card_color, width=16, anchor=tk.W
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=desc, font=("Segoe UI", 8), fg=self.text_dim, bg=self.card_color
            ).pack(side=tk.LEFT)

        # 5. Footer info
        footer_lbl = tk.Label(
            self.root,
            text="Safety Active: PyAutoGUI Failsafe (Screen Corner to Stop)",
            font=("Segoe UI", 8),
            fg=self.text_dim,
            bg=self.bg_color,
        )
        footer_lbl.pack(side=tk.BOTTOM, pady=10)

        # Clean exit hook
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _get_python_path(self) -> str:
        venv_py = os.path.join(self.base_dir, ".venv", "Scripts", "python.exe")
        if os.path.exists(venv_py):
            return venv_py
        return sys.executable

    def toggle_activation(self):
        if not self.is_running:
            self._start_controller()
        else:
            self._stop_controller()

    def _start_controller(self):
        main_script = os.path.join(self.base_dir, "main.py")
        if not os.path.exists(main_script):
            messagebox.showerror("Error", f"main.py not found in {self.base_dir}")
            return

        py_cmd = self._get_python_path()

        try:
            self.process = subprocess.Popen(
                [py_cmd, main_script],
                cwd=self.base_dir,
            )
            self.is_running = True
            self.status_lbl.configure(text="● CONTROLLER ACTIVE", fg=self.accent_green)
            self.action_btn.configure(
                text="⏹  STOP CONTROLLER",
                bg=self.accent_red,
                activebackground="#ff6690",
            )

            # Monitor process completion in background thread
            threading.Thread(target=self._monitor_process, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch controller:\n{e}")

    def _monitor_process(self):
        if self.process:
            self.process.wait()
            self.root.after(0, self._on_process_finished)

    def _on_process_finished(self):
        self.is_running = False
        self.process = None
        self.status_lbl.configure(text="● READY TO ACTIVATE", fg=self.accent_cyan)
        self.action_btn.configure(
            text="▶  ACTIVATE CONTROLLER",
            bg=self.accent_cyan,
            activebackground="#33ddff",
        )

    def _stop_controller(self):
        if self.process and self.is_running:
            try:
                self.process.terminate()
            except Exception:
                pass
            self._on_process_finished()

    def run_webcam_test(self):
        test_script = os.path.join(self.base_dir, "prototypes", "step3_webcam_test.py")
        if not os.path.exists(test_script):
            messagebox.showinfo("Diagnostic", "Webcam diagnostic script not found.")
            return

        py_cmd = self._get_python_path()
        subprocess.Popen([py_cmd, test_script], cwd=self.base_dir)

    def on_close(self):
        if self.is_running and self.process:
            self._stop_controller()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ActivatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
