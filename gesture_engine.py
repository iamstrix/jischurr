import cv2
import mediapipe as mp
import threading
import time
import subprocess
import os
import json
import numpy as np

class GestureEngine:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.settings = {}
        self.mappings = []
        self.load_config()

        # MediaPipe initialization
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Threading and camera control
        self.lock = threading.Lock()
        self.running = False
        self.camera_active = False
        self.thread = None
        self.cap = None

        # Live data shared with the GUI
        self.latest_frame = None
        self.latest_landmarks = None
        self.current_gesture = [False, False, False, False, False]
        self.detected_handedness = "Right"

        # Action execution states
        self.last_detected_gesture = None
        self.gesture_start_time = 0
        self.action_executed = False
        self.last_action_time = 0

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.settings = config.get("settings", {})
                    self.mappings = config.get("mappings", [])
            else:
                self.settings = {
                    "activation_mode": "hold_hotkey",
                    "hotkey": "caps lock",
                    "continuous_tracking": False,
                    "confidence_threshold": 0.5,
                    "debounce_duration_ms": 1000
                }
                self.mappings = []
                self.save_config()
        except Exception as e:
            print(f"Error loading config: {e}")

    def save_config(self):
        try:
            config = {
                "settings": self.settings,
                "mappings": self.mappings
            }
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def start(self):
        with self.lock:
            if not self.running:
                self.running = True
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()

    def stop(self):
        with self.lock:
            self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self._release_camera()

    def set_camera_active(self, active):
        with self.lock:
            self.camera_active = active
            if not active:
                self._release_camera()

    def _release_camera(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        with self.lock:
            self.latest_frame = None
            self.latest_landmarks = None

    def calculate_distance(self, p1, p2):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

    def classify_gesture(self, landmarks, handedness):
        """
        Classifies current hand landmarks into a 5-element boolean array:
        [Thumb, Index, Middle, Ring, Pinky]
        True = Extended/Open, False = Folded/Closed
        """
        # Wrist (0)
        wrist = landmarks.landmark[0]
        
        # Fingers tips and PIPs
        # Index: Tip (8), PIP (6)
        # Middle: Tip (12), PIP (10)
        # Ring: Tip (16), PIP (14)
        # Pinky: Tip (20), PIP (18)
        
        index_open = landmarks.landmark[8].y < landmarks.landmark[6].y
        middle_open = landmarks.landmark[12].y < landmarks.landmark[10].y
        ring_open = landmarks.landmark[16].y < landmarks.landmark[14].y
        pinky_open = landmarks.landmark[20].y < landmarks.landmark[18].y

        # Thumb logic: rotation and scale-invariant heuristic
        # If the thumb is extended, the tip (4) is far from the Index MCP (5).
        # We compare distance(thumb_tip, index_mcp) with distance(thumb_ip, index_mcp).
        # When folded, the tip goes closer to index_mcp than the IP joint.
        thumb_tip = landmarks.landmark[4]
        thumb_ip = landmarks.landmark[3]
        index_mcp = landmarks.landmark[5]
        
        thumb_open = self.calculate_distance(thumb_tip, index_mcp) > self.calculate_distance(thumb_ip, index_mcp)

        return [thumb_open, index_open, middle_open, ring_open, pinky_open]

    def execute_action(self, mapping):
        path = mapping.get("path")
        if not path:
            return
        
        action_name = mapping.get("name", "Action")
        print(f"Executing: {action_name} ({path})")
        
        try:
            # os.startfile is Windows specific and handles executables, paths, files, and URLs cleanly
            os.startfile(path)
        except Exception as e:
            # Fallback to subprocess if startfile fails
            try:
                subprocess.Popen(path, shell=True)
            except Exception as ex:
                print(f"Failed to execute {path}: {e} | Fallback failed: {ex}")

    def process_gesture_trigger(self, current_gesture):
        """
        Debounces gesture inputs and triggers mapped actions.
        """
        # If no hand is detected, reset gesture tracking
        if current_gesture is None:
            self.last_detected_gesture = None
            self.action_executed = False
            return

        # Find if the gesture matches any mapped gesture
        matched_mapping = None
        for mapping in self.mappings:
            if mapping.get("gesture") == current_gesture:
                matched_mapping = mapping
                break

        if matched_mapping:
            # If it's a new gesture, start timer
            if self.last_detected_gesture != tuple(current_gesture):
                self.last_detected_gesture = tuple(current_gesture)
                self.gesture_start_time = time.time()
                self.action_executed = False
            else:
                # If gesture is held, check if debounce duration has passed
                debounce_duration = self.settings.get("debounce_duration_ms", 1000) / 1000.0
                elapsed = time.time() - self.gesture_start_time
                if elapsed >= debounce_duration and not self.action_executed:
                    self.execute_action(matched_mapping)
                    self.action_executed = True
        else:
            # Reset if no mapping matches the current gesture
            self.last_detected_gesture = None
            self.action_executed = False

    def _run_loop(self):
        """
        Background thread camera capture and MediaPipe processing.
        """
        while True:
            # Thread-safe check for running status
            with self.lock:
                if not self.running:
                    break
                active = self.camera_active

            if not active:
                self._release_camera()
                time.sleep(0.1)
                continue

            # Initialize camera if not open
            if self.cap is None:
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # CAP_DSHOW is faster on Windows
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            success, frame = self.cap.read()
            if not success:
                print("Failed to capture frame from webcam.")
                time.sleep(0.1)
                continue

            # Mirror the frame horizontally for a more natural preview
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            detected_gesture = None
            handedness_label = "Right"

            if results.multi_hand_landmarks:
                for hand_landmarks, hand_class in zip(results.multi_hand_landmarks, results.multi_handedness):
                    handedness_label = hand_class.classification[0].label
                    
                    # Draw landmarks on the OpenCV BGR frame
                    self.mp_drawing.draw_landmarks(
                        frame, 
                        hand_landmarks, 
                        self.mp_hands.HAND_CONNECTIONS,
                        self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                        self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                    )
                    
                    # Classify the gesture
                    detected_gesture = self.classify_gesture(hand_landmarks, handedness_label)
                    
                    # We process only the first detected hand for actions
                    break

            # Handle triggers and debouncing
            self.process_gesture_trigger(detected_gesture)

            # Store the frame and tracking details for the GUI
            with self.lock:
                self.latest_frame = frame
                self.current_gesture = detected_gesture if detected_gesture else [False, False, False, False, False]
                self.detected_handedness = handedness_label

            # Limit thread loop speed (approx. 30 FPS)
            time.sleep(0.033)

        self._release_camera()
