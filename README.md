# Jischurr 🖐️🚀

Jischurr is a lightweight, AI-powered Windows utility that allows you to trigger system actions (such as launching programs, scripts, or opening files) using real-time hand gestures. 

It features a modern, dark-themed native Windows GUI built with CustomTkinter, and performs efficient, local Edge AI hand tracking via Google's MediaPipe.

---

## ✨ Features

- **Push-to-Gesture Activation**: Press and hold the activation hotkey (default: `Caps Lock`) to start tracking. Releasing it immediately turns off your webcam, keeping idle CPU/GPU usage at **0%** and ensuring your privacy.
- **Visualizer Overlay**: A real-time camera display that renders a wireframe of your hand skeleton when tracking is active.
- **Finger LED Indicators**: Instant UI feedback displaying which fingers are detected as extended (Green) or folded (Red).
- **Flexible Mapping Config**: Easily map custom finger configurations to executable paths (e.g. extending your index finger launches `notepad.exe`).
- **Scale and Rotation Invariant**: Uses a distance-based landmark heuristic to accurately detect finger states regardless of hand distance or tilt.
- **Debounced Triggers**: Custom trigger delays prevent accidental activations and double-launches.

---

## 🛠️ Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/iamstrix/jischurr.git
   cd jischurr
   ```

2. **Install Dependencies**:
   Ensure you have Python 3.10+ installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

Start the application by running:
```bash
python app.py
```

### Quick Start:
1. Hold down your **`Caps Lock`** key. You will see your webcam feed activate.
2. Present your hand to the camera.
3. Try raising **only your Index finger** (all other fingers closed). Hold it for **1 second**.
4. **Notepad** will open automatically!
5. Release `Caps Lock` to stop tracking and turn off the camera.

---

## ⚙️ Customizing Mappings

You can add, edit, or delete action mappings directly in the GUI:
1. Click **+ Add Action**.
2. Give your action a name (e.g. `Launch Browser`).
3. Click **Browse...** to select your target program (e.g. `C:/Program Files/Google/Chrome/Application/chrome.exe`).
4. Select which fingers must be **extended** to trigger the action.
5. Click **Save Action**.

Mappings are stored locally in `config.json`.
