import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
from pynput import keyboard as keyboard_pynput
import os
import time

from gesture_engine import GestureEngine

# Set appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        print("[TELEMETRY-GUI] App initialization started")
        # Window settings
        self.title("Jischurr - Gesture Launcher")
        self.geometry("1000x650")
        self.resizable(False, False)

        # Initialize gesture engine (load config only, don't start yet)
        self.engine = GestureEngine()

        # Thread-safe global hotkey state
        self.hotkey_pressed = False
        self.update_count = 0

        # Build UI layout first so the window renders immediately
        self.setup_layout()

        # Local Tkinter Key Bindings as a robust fallback when GUI is focused
        self.bind("<KeyPress>", self.on_tkinter_key_press)
        self.bind("<KeyRelease>", self.on_tkinter_key_release)

        # Force the window to render before starting background threads
        print("[TELEMETRY-GUI] Forcing layout render via update_idletasks")
        self.update_idletasks()

        # Defer engine and listener startup to after the window is visible
        print("[TELEMETRY-GUI] Scheduling background services startup in 100ms")
        self.after(100, self._start_background_services)

    def _start_background_services(self):
        """Start engine and keyboard listener after the window is visible."""
        print("[TELEMETRY-GUI] _start_background_services: Starting gesture engine")
        self.engine.start()

        print("[TELEMETRY-GUI] _start_background_services: Starting pynput keyboard listener")
        self.listener = keyboard_pynput.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.listener.start()

        print("[TELEMETRY-GUI] _start_background_services: Initiating update_loop")
        self.update_loop()

    def setup_layout(self):
        # Configure grid grid weight
        self.grid_columnconfigure(0, weight=6)  # Camera column
        self.grid_columnconfigure(1, weight=4)  # Settings & Mappings column
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: CAMERA VIEW ---
        self.left_panel = ctk.CTkFrame(self, corner_radius=15, fg_color="#1e1e24")
        self.left_panel.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        # Header Title
        self.app_title = ctk.CTkLabel(
            self.left_panel, 
            text="JISCHURR", 
            font=ctk.CTkFont(family="Arial Black", size=28, weight="bold"),
            text_color="#3b82f6"
        )
        self.app_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Camera Display Label
        self.camera_label = ctk.CTkLabel(self.left_panel, text="", fg_color="#0f0f12", corner_radius=10)
        self.camera_label.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

        # Hands Visual Indicators
        self.indicator_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.indicator_frame.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="ew")
        self.indicator_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        self.indicators = []
        for i, name in enumerate(self.finger_names):
            lbl = ctk.CTkLabel(
                self.indicator_frame, 
                text=name, 
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#374151", 
                text_color="#9ca3af",
                height=30, 
                corner_radius=15
            )
            lbl.grid(row=0, column=i, padx=5, sticky="ew")
            self.indicators.append(lbl)

        # --- RIGHT PANEL: CONFIGURATION ---
        self.right_panel = ctk.CTkFrame(self, corner_radius=15, fg_color="#18181c")
        self.right_panel.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        self.right_panel.grid_rowconfigure(2, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Settings Section Header
        self.settings_title = ctk.CTkLabel(
            self.right_panel, 
            text="Settings", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e5e7eb"
        )
        self.settings_title.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        # Settings Options Frame
        self.settings_frame = ctk.CTkFrame(self.right_panel, fg_color="#27272a")
        self.settings_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.settings_frame.grid_columnconfigure(0, weight=1)

        # Hotkey Configuration Info
        self.hotkey_label = ctk.CTkLabel(
            self.settings_frame,
            text=f"Activation Hotkey: HOLD [ {self.engine.settings.get('hotkey', 'caps lock').upper()} ]",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#60a5fa"
        )
        self.hotkey_label.grid(row=0, column=0, padx=15, pady=(12, 4), sticky="w")
        
        self.hotkey_desc = ctk.CTkLabel(
            self.settings_frame,
            text="Press and hold the hotkey to activate hand tracking.",
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af"
        )
        self.hotkey_desc.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="w")

        # Mappings Section Header
        self.mappings_header_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.mappings_header_frame.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.mappings_header_frame.grid_columnconfigure(0, weight=1)

        self.mappings_title = ctk.CTkLabel(
            self.mappings_header_frame, 
            text="Gesture Mappings", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e5e7eb"
        )
        self.mappings_title.grid(row=0, column=0, sticky="w")

        self.add_btn = ctk.CTkButton(
            self.mappings_header_frame, 
            text="+ Add Action", 
            width=90, 
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_add_mapping_dialog
        )
        self.add_btn.grid(row=0, column=1, sticky="e")

        # Scrollable Mappings List
        self.mappings_list = ctk.CTkScrollableFrame(self.right_panel, fg_color="#0f0f12", corner_radius=10)
        self.mappings_list.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.mappings_list.grid_columnconfigure(0, weight=1)

        self.render_mappings()

    def render_mappings(self):
        # Clear existing elements
        for widget in self.mappings_list.winfo_children():
            widget.destroy()

        if not self.engine.mappings:
            no_mappings_lbl = ctk.CTkLabel(
                self.mappings_list, 
                text="No active mappings.\nClick '+ Add Action' to create one.",
                font=ctk.CTkFont(size=13),
                text_color="#6b7280"
            )
            no_mappings_lbl.grid(row=0, column=0, padx=20, pady=40, sticky="nsew")
            return

        for idx, mapping in enumerate(self.engine.mappings):
            row_frame = ctk.CTkFrame(self.mappings_list, fg_color="#1e1e24", corner_radius=8)
            row_frame.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            row_frame.grid_columnconfigure(0, weight=1)

            # Left side: Name and action details
            text_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            text_frame.grid(row=0, column=0, padx=12, pady=10, sticky="w")

            name_lbl = ctk.CTkLabel(
                text_frame, 
                text=mapping.get("name", "Unnamed Action"), 
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#f3f4f6"
            )
            name_lbl.grid(row=0, column=0, sticky="w")

            path_lbl = ctk.CTkLabel(
                text_frame, 
                text=os.path.basename(mapping.get("path", "")), 
                font=ctk.CTkFont(size=11),
                text_color="#9ca3af"
            )
            path_lbl.grid(row=1, column=0, sticky="w")

            # Center: Gesture visualization indicator
            gesture = mapping.get("gesture")
            gesture_text = ""
            text_color = "#10b981" # default green
            
            # Backwards compatibility check
            if isinstance(gesture, list):
                # old 5-boolean format
                for i, finger in enumerate(["T", "I", "M", "R", "P"]):
                    if i < len(gesture) and gesture[i]:
                        gesture_text += f"[{finger}] "
                    else:
                        gesture_text += f" _  "
            elif isinstance(gesture, dict):
                g_type = gesture.get("type", "fingers")
                g_data = gesture.get("data")
                if g_type == "fingers":
                    for i, finger in enumerate(["T", "I", "M", "R", "P"]):
                        if i < len(g_data) and g_data[i]:
                            gesture_text += f"[{finger}] "
                        else:
                            gesture_text += f" _  "
                elif g_type == "pinch":
                    finger_name = str(g_data).capitalize()
                    gesture_text = f"PINCH {finger_name.upper()}"
                    text_color = "#f59e0b" # Orange for pinch
            else:
                gesture_text = "UNKNOWN"
            
            gesture_lbl = ctk.CTkLabel(
                row_frame, 
                text=gesture_text.strip(),
                font=ctk.CTkFont(family="Arial" if "PINCH" in gesture_text else "Courier", size=12, weight="bold"),
                text_color=text_color
            )
            gesture_lbl.grid(row=0, column=1, padx=10)

            # Right side: Delete button
            delete_btn = ctk.CTkButton(
                row_frame, 
                text="✕", 
                width=30, 
                height=30, 
                fg_color="#ef4444", 
                hover_color="#dc2626",
                text_color="white",
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda m_idx=idx: self.delete_mapping(m_idx)
            )
            delete_btn.grid(row=0, column=2, padx=12, pady=10)

    def delete_mapping(self, idx):
        if messagebox.askyesno("Delete Mapping", "Are you sure you want to delete this action mapping?"):
            self.engine.mappings.pop(idx)
            self.engine.save_config()
            self.render_mappings()

    def open_add_mapping_dialog(self):
        # Create a popup window for adding mapping
        dialog = MappingDialog(self, callback=self.add_mapping)
        dialog.focus()

    def add_mapping(self, new_mapping):
        self.engine.mappings.append(new_mapping)
        self.engine.save_config()
        self.render_mappings()

    def update_loop(self):
        self.update_count += 1
        verbose = (self.update_count <= 15 or self.update_count % 30 == 0)

        if verbose:
            print(f"[TELEMETRY-GUI] update_loop: tick {self.update_count}, hotkey_pressed={self.hotkey_pressed}")

        # 1. Update hotkey state for gesture analysis
        hotkey = self.engine.settings.get("hotkey", "caps lock")
        is_active = self.hotkey_pressed
        
        if verbose:
            print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Calling set_analysis_active({is_active})")
        self.engine.set_analysis_active(is_active)

        # 2. Update camera frame in the GUI
        frame = None
        current_gesture = [False, False, False, False, False]
        is_monitoring = False

        if verbose:
            print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Acquiring engine lock...")
        
        t0 = time.perf_counter()
        with self.engine.lock:
            lock_time = time.perf_counter() - t0
            if verbose:
                print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Lock acquired in {lock_time:.6f}s")
            
            if self.engine.latest_frame is not None:
                frame = self.engine.latest_frame.copy()
            current_gesture = self.engine.current_gesture
            is_monitoring = self.engine.analysis_active

        if frame is not None:
            if verbose:
                print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Camera active, rendering frame...")
            t_render = time.perf_counter()
            # Resize frame to fit camera label (approx. 540x405 to keep 4:3 aspect ratio)
            frame_resized = cv2.resize(frame, (540, 405))
            # Convert BGR (OpenCV) to RGB (Tkinter/PIL)
            rgb_image = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(540, 405))
            
            self.camera_label.configure(image=img, text="")
            self.camera_label.image = img  # keep reference
            if verbose:
                print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Frame render took {time.perf_counter()-t_render:.6f}s")
        else:
            if verbose:
                print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Camera frame is None, rendering offline state")
            # Display offline screen
            self.camera_label.configure(
                image=None, 
                text="WEBCAM OFFLINE OR INITIALIZING...",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#ef4444"
            )

        # 3. Update hand finger indicators
        if verbose:
            print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Updating finger indicators: {current_gesture}")

        if not is_monitoring:
            for idx in range(5):
                self.indicators[idx].configure(fg_color="#374151", text_color="#9ca3af")
        else:
            g_type = current_gesture.get("type", "fingers") if isinstance(current_gesture, dict) else "fingers"
            if g_type == "pinch" and isinstance(current_gesture, dict):
                pinches = current_gesture.get("pinches", {})
                active_pinch_finger = None
                for key, val in pinches.items():
                    if val:
                        active_pinch_finger = key
                        break
                
                finger_indices = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4}
                for idx in range(5):
                    if idx == 0:  # Thumb is always involved in a pinch
                        self.indicators[idx].configure(fg_color="#f59e0b", text_color="#ffffff")  # Orange
                    elif active_pinch_finger and idx == finger_indices.get(active_pinch_finger):
                        self.indicators[idx].configure(fg_color="#f59e0b", text_color="#ffffff")  # Orange
                    else:
                        self.indicators[idx].configure(fg_color="#374151", text_color="#9ca3af")  # Gray
            else:
                # Normal finger extensions
                fingers_state = current_gesture.get("fingers", [False]*5) if isinstance(current_gesture, dict) else current_gesture
                for idx, is_open in enumerate(fingers_state):
                    if is_open:
                        self.indicators[idx].configure(fg_color="#10b981", text_color="#ffffff")  # Green
                    else:
                        self.indicators[idx].configure(fg_color="#ef4444", text_color="#ffffff")  # Red

        if verbose:
            print(f"[TELEMETRY-GUI] update_loop (tick {self.update_count}): Scheduling next tick")
        # Schedule next update tick (approx 30 FPS)
        self.after(33, self.update_loop)

    def on_key_press(self, key):
        print(f"[TELEMETRY-GUI] Global Keyboard Press Detected: {key}")
        if self._is_hotkey(key):
            self.hotkey_pressed = True
            print(f"[TELEMETRY-GUI] Global Hotkey Pressed! Setting hotkey_pressed = {self.hotkey_pressed}")

    def on_key_release(self, key):
        print(f"[TELEMETRY-GUI] Global Keyboard Release Detected: {key}")
        if self._is_hotkey(key):
            self.hotkey_pressed = False
            print(f"[TELEMETRY-GUI] Global Hotkey Released! Setting hotkey_pressed = {self.hotkey_pressed}")

    def _is_hotkey(self, key):
        hotkey_str = self.engine.settings.get("hotkey", "caps lock").lower().strip()
        
        # Mapping common hotkeys to pynput Key objects
        key_map = {
            "caps lock": keyboard_pynput.Key.caps_lock,
            "caps_lock": keyboard_pynput.Key.caps_lock,
            "ctrl": keyboard_pynput.Key.ctrl_l,
            "shift": keyboard_pynput.Key.shift_l,
            "alt": keyboard_pynput.Key.alt_l,
            "space": keyboard_pynput.Key.space,
        }
        
        target_key = key_map.get(hotkey_str)
        if target_key:
            if hasattr(key, 'name'):
                if hotkey_str == "ctrl" and "ctrl" in key.name:
                    return True
                if hotkey_str == "shift" and "shift" in key.name:
                    return True
                if hotkey_str == "alt" and "alt" in key.name:
                    return True
                return key == target_key
            return False
            
        # Robust check for alphanumeric keys:
        if hasattr(key, 'char') and key.char:
            if key.char.lower() == hotkey_str:
                return True
        
        # Fallback to string representation of the key
        key_str = str(key).replace("'", "").lower().strip()
        if key_str == hotkey_str:
            return True
            
        return False

    def on_tkinter_key_press(self, event):
        print(f"[TELEMETRY-GUI] Tkinter KeyPress: keysym={event.keysym}, char={event.char}")
        if self._is_tkinter_hotkey(event.keysym, event.char):
            self.hotkey_pressed = True
            print(f"[TELEMETRY-GUI] Tkinter Hotkey Pressed! Setting hotkey_pressed = {self.hotkey_pressed}")

    def on_tkinter_key_release(self, event):
        print(f"[TELEMETRY-GUI] Tkinter KeyRelease: keysym={event.keysym}, char={event.char}")
        if self._is_tkinter_hotkey(event.keysym, event.char):
            self.hotkey_pressed = False
            print(f"[TELEMETRY-GUI] Tkinter Hotkey Released! Setting hotkey_pressed = {self.hotkey_pressed}")

    def _is_tkinter_hotkey(self, keysym, char):
        hotkey_str = self.engine.settings.get("hotkey", "caps lock").lower().strip()
        
        key_map = {
            "caps lock": "caps_lock",
            "caps_lock": "caps_lock",
            "ctrl": "control_l",
            "shift": "shift_l",
            "alt": "alt_l",
            "space": "space",
        }
        
        target_keysym = key_map.get(hotkey_str)
        if target_keysym:
            keysym_lower = keysym.lower()
            if hotkey_str == "ctrl" and "control" in keysym_lower:
                return True
            if hotkey_str == "shift" and "shift" in keysym_lower:
                return True
            if hotkey_str == "alt" and "alt" in keysym_lower:
                return True
            return keysym_lower == target_keysym
            
        if char:
            if char.lower() == hotkey_str:
                return True
                
        return keysym.lower() == hotkey_str

    def destroy(self):
        # Stop pynput listener
        if hasattr(self, 'listener'):
            try:
                self.listener.stop()
            except Exception:
                pass
        # Make sure engine stops when GUI is closed
        self.engine.stop()
        super().destroy()


class MappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        
        self.callback = callback
        self.title("Add Gesture Action")
        self.geometry("450x520")
        self.resizable(False, False)
        
        # Keep window on top
        self.transient(parent)
        self.grab_set()

        # Grid config
        self.grid_columnconfigure(0, weight=1)
        
        # --- TITLE ---
        self.title_lbl = ctk.CTkLabel(
            self, 
            text="Create Gesture Mapping", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#e5e7eb"
        )
        self.title_lbl.grid(row=0, column=0, padx=20, pady=(20, 15), sticky="w")

        # --- NAME INPUT ---
        self.name_lbl = ctk.CTkLabel(self, text="Action Name (e.g. Open Browser)", font=ctk.CTkFont(size=12, weight="bold"))
        self.name_lbl.grid(row=1, column=0, padx=20, pady=(5, 2), sticky="w")
        
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Enter action name", width=410)
        self.name_entry.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")

        # --- ACTION PATH ---
        self.path_lbl = ctk.CTkLabel(self, text="Executable Path or File Shortcut", font=ctk.CTkFont(size=12, weight="bold"))
        self.path_lbl.grid(row=3, column=0, padx=20, pady=(5, 2), sticky="w")

        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.path_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(self.path_frame, placeholder_text="C:/Windows/System32/notepad.exe", width=310)
        self.path_entry.grid(row=0, column=0, sticky="ew")

        self.browse_btn = ctk.CTkButton(self.path_frame, text="Browse...", width=80, command=self.browse_file)
        self.browse_btn.grid(row=0, column=1, padx=(10, 0))

        # --- GESTURE SELECTOR ---
        self.gesture_lbl = ctk.CTkLabel(self, text="Gesture Definition", font=ctk.CTkFont(size=12, weight="bold"))
        self.gesture_lbl.grid(row=5, column=0, padx=20, pady=(5, 5), sticky="w")

        self.gesture_type_var = tk.StringVar(value="Fingers Extended")
        self.segmented_btn = ctk.CTkSegmentedButton(
            self,
            values=["Fingers Extended", "Pinch Gesture"],
            variable=self.gesture_type_var,
            command=self.toggle_gesture_type,
            width=410
        )
        self.segmented_btn.grid(row=6, column=0, padx=20, pady=(0, 10), sticky="w")

        # Options Container Frame
        self.options_container = ctk.CTkFrame(self, fg_color="transparent", width=410, height=80)
        self.options_container.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")
        self.options_container.grid_columnconfigure(0, weight=1)
        self.options_container.grid_propagate(False)

        # Fingers Checklist Panel
        self.checkbox_frame = ctk.CTkFrame(self.options_container, fg_color="#1e1e24", corner_radius=8)
        self.checkbox_frame.grid(row=0, column=0, sticky="nsew")
        self.checkbox_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.finger_vars = []
        finger_labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        for i, label in enumerate(finger_labels):
            var = tk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(self.checkbox_frame, text=label, variable=var, font=ctk.CTkFont(size=11))
            chk.grid(row=0, column=i, padx=5, pady=25)
            self.finger_vars.append(var)

        # Pinch Selector Panel (Hidden initially)
        self.pinch_frame = ctk.CTkFrame(self.options_container, fg_color="#1e1e24", corner_radius=8)
        self.pinch_lbl = ctk.CTkLabel(self.pinch_frame, text="Select finger to pinch with Thumb:", font=ctk.CTkFont(size=11, weight="bold"))
        self.pinch_lbl.grid(row=0, column=0, padx=15, pady=(15, 2), sticky="w")

        self.pinch_finger_var = tk.StringVar(value="Index")
        self.pinch_menu = ctk.CTkOptionMenu(
            self.pinch_frame,
            values=["Index", "Middle", "Ring", "Pinky"],
            variable=self.pinch_finger_var,
            width=380
        )
        self.pinch_menu.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
        self.pinch_frame.grid_columnconfigure(0, weight=1)

        # --- BUTTONS ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=8, column=0, padx=20, pady=(10, 20), sticky="e")

        self.cancel_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Cancel", 
            fg_color="#374151", 
            hover_color="#4b5563",
            width=100, 
            command=self.destroy
        )
        self.cancel_btn.grid(row=0, column=0, padx=(0, 10))

        self.save_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Save Action", 
            width=120, 
            command=self.save_action
        )
        self.save_btn.grid(row=0, column=1)

    def toggle_gesture_type(self, val):
        if val == "Fingers Extended":
            self.pinch_frame.grid_forget()
            self.checkbox_frame.grid(row=0, column=0, sticky="nsew")
        else:
            self.checkbox_frame.grid_forget()
            self.pinch_frame.grid(row=0, column=0, sticky="nsew")

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Program Executable or File",
            filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
        )
        if file_path:
            # Replace backslashes with forward slashes for cross-platform string consistency
            formatted_path = file_path.replace("\\", "/")
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, formatted_path)

    def save_action(self):
        name = self.name_entry.get().strip()
        path = self.path_entry.get().strip()
        g_type = self.gesture_type_var.get()

        if not name:
            messagebox.showerror("Error", "Please enter a name for the action.")
            return
        if not path:
            messagebox.showerror("Error", "Please provide a valid file/program path.")
            return

        gesture_config = {}
        if g_type == "Fingers Extended":
            gesture = [var.get() for var in self.finger_vars]
            if not any(gesture):
                messagebox.showerror("Error", "Please select at least one extended finger for the gesture.")
                return
            gesture_config = {
                "type": "fingers",
                "data": gesture
            }
        else:
            # Pinch Gesture
            pinch_finger = self.pinch_finger_var.get().lower()
            gesture_config = {
                "type": "pinch",
                "data": pinch_finger
            }

        new_mapping = {
            "name": name,
            "gesture": gesture_config,
            "action_type": "executable",
            "path": path
        }
        
        self.callback(new_mapping)
        self.destroy()


if __name__ == "__main__":
    import signal

    app = App()

    # Allow Ctrl+C from terminal to close the app
    def on_sigint(sig, frame):
        app.destroy()

    signal.signal(signal.SIGINT, on_sigint)

    # Tkinter swallows Ctrl+C unless we periodically yield to Python's signal handler
    def check_signals():
        app.after(500, check_signals)

    check_signals()
    app.mainloop()
