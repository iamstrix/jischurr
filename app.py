import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import keyboard
import os
import time

from gesture_engine import GestureEngine

# Set appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("Jischurr - Gesture Launcher")
        self.geometry("1000x650")
        self.resizable(False, False)

        # Initialize gesture engine
        self.engine = GestureEngine()
        self.engine.start()

        # Build UI layout
        self.setup_layout()

        # Start GUI update loop
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
            gesture = mapping.get("gesture", [False]*5)
            gesture_text = ""
            for i, finger in enumerate(["T", "I", "M", "R", "P"]):
                if gesture[i]:
                    gesture_text += f"[{finger}] "
                else:
                    gesture_text += f" _  "
            
            gesture_lbl = ctk.CTkLabel(
                row_frame, 
                text=gesture_text.strip(),
                font=ctk.CTkFont(family="Courier", size=12, weight="bold"),
                text_color="#10b981"
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
        # 1. Check hotkey state to activate/deactivate camera stream
        hotkey = self.engine.settings.get("hotkey", "caps lock")
        try:
            is_active = keyboard.is_pressed(hotkey)
        except Exception:
            is_active = False

        self.engine.set_camera_active(is_active)

        # 2. Update camera frame in the GUI
        frame = None
        with self.engine.lock:
            if self.engine.latest_frame is not None:
                frame = self.engine.latest_frame.copy()
            current_gesture = self.engine.current_gesture
            is_monitoring = self.engine.camera_active

        if is_monitoring and frame is not None:
            # Resize frame to fit camera label (approx. 540x405 to keep 4:3 aspect ratio)
            frame_resized = cv2.resize(frame, (540, 405))
            # Convert BGR (OpenCV) to RGB (Tkinter/PIL)
            rgb_image = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(540, 405))
            
            self.camera_label.configure(image=img, text="")
            self.camera_label.image = img  # keep reference
        else:
            # Display Idle screen
            self.camera_label.configure(
                image=None, 
                text=f"CAMERA IDLE\n\nHOLD [ {hotkey.upper()} ] TO CAPTURE GESTURES",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#4b5563"
            )

        # 3. Update hand finger indicators
        for idx, is_open in enumerate(current_gesture):
            if not is_monitoring:
                self.indicators[idx].configure(fg_color="#374151", text_color="#9ca3af")
            elif is_open:
                self.indicators[idx].configure(fg_color="#10b981", text_color="#ffffff")  # Green for active
            else:
                self.indicators[idx].configure(fg_color="#ef4444", text_color="#ffffff")  # Red for inactive

        # Schedule next update tick (approx 30 FPS)
        self.after(33, self.update_loop)

    def destroy(self):
        # Make sure engine stops when GUI is closed
        self.engine.stop()
        super().destroy()


class MappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        
        self.callback = callback
        self.title("Add Gesture Action")
        self.geometry("450x480")
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
        self.gesture_lbl = ctk.CTkLabel(self, text="Gesture Definition (Select Extended Fingers)", font=ctk.CTkFont(size=12, weight="bold"))
        self.gesture_lbl.grid(row=5, column=0, padx=20, pady=(5, 5), sticky="w")

        self.checkbox_frame = ctk.CTkFrame(self, fg_color="#1e1e24", corner_radius=8, width=410)
        self.checkbox_frame.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.checkbox_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.finger_vars = []
        finger_labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        for i, label in enumerate(finger_labels):
            var = tk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(self.checkbox_frame, text=label, variable=var, font=ctk.CTkFont(size=11))
            chk.grid(row=0, column=i, padx=5, pady=15)
            self.finger_vars.append(var)

        # --- BUTTONS ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=7, column=0, padx=20, pady=(10, 20), sticky="e")

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
        gesture = [var.get() for var in self.finger_vars]

        if not name:
            messagebox.showerror("Error", "Please enter a name for the action.")
            return
        if not path:
            messagebox.showerror("Error", "Please provide a valid file/program path.")
            return
        if not any(gesture):
            messagebox.showerror("Error", "Please select at least one extended finger for the gesture.")
            return

        new_mapping = {
            "name": name,
            "gesture": gesture,
            "action_type": "executable",
            "path": path
        }
        
        self.callback(new_mapping)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
