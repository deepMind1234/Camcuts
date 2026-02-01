import cv2
import queue
import threading
import time
from mediapipe_detector import MediaPipeDetector
from logic import LogicLayer
from actions import ActionExecutor

import json

# Load configuration
try:
    with open('config.json', 'r') as f:
        CONF = json.load(f)
except Exception as e:
    print(f"Warning: Could not load config.json ({e}). Using empty mapping.")
    CONF = {"gestures": {}, "settings": {"confidence_threshold": 0.8, "default_hold_duration": 1.0}}

ACTION_MAP = CONF["gestures"]

class CamcutsApp:
    def __init__(self):
        self.detector = MediaPipeDetector()
        self.logic = LogicLayer(
            ACTION_MAP, 
            default_duration=CONF["settings"].get("default_hold_duration", 1.0),
            confidence_threshold=CONF["settings"].get("confidence_threshold", 0.8)
        )
        self.executor = ActionExecutor()
        self.cap = cv2.VideoCapture(0)
        self.running = True

    def run(self):
        print("Camcuts started. Press 'q' to quit, 's' to SELECT, 'l' to LIST windows.")
        
        while self.cap.isOpened() and self.running:
            success, frame = self.cap.read()
            if not success:
                break

            # Mirror the frame
            frame = cv2.flip(frame, 1)

            # Process detection
            detections = self.detector.process_frame(frame)
            
            # Logic update
            action = self.logic.update(detections)
            if action:
                if action.get('type') == 'app' and action.get('command') == 'quit':
                    print("Emergency Quit Triggered!")
                    self.running = False
                else:
                    self.executor.execute(action['type'], action['command'])

            # UI Overlay
            self._draw_overlay(frame, detections)

            # Resize for a "small screen" feel
            display_frame = cv2.resize(frame, (480, 270))

            cv2.imshow('Camcuts Overlay', display_frame)
            cv2.setWindowProperty('Camcuts Overlay', cv2.WND_PROP_TOPMOST, 1)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Handle window picking in a separate thread to avoid freezing the camera
                threading.Thread(target=self.executor.pick_target_window, daemon=True).start()
            elif key == ord('l'):
                # List all windows in the terminal
                windows = self.executor.list_all_windows()
                print("\n--- Available Windows ---")
                for wid, name in windows:
                    print(f"ID: {wid} | Name: {name}")
                print("--------------------------\n")

        self.cap.release()
        self.detector.release()
        cv2.destroyAllWindows()

    def _draw_overlay(self, frame, detections):
        # Draw detected symbol status
        status_text = "Status: Monitoring..."
        
        # Display selection mode status
        if self.executor.manual_window_id:
            cv2.putText(frame, f"Target: Locked ({self.executor.manual_window_id})", (50, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "Target: Auto-detecting", (50, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        if self.logic.current_symbol:
            # Dynamically calculate progress based on the required duration for this gesture
            required = self.logic.durations.get(self.logic.current_symbol, self.logic.default_duration)
            duration = time.time() - self.logic.symbol_start_time
            progress = min(1.0, duration / required)
            
            status_text = f"Symbol: {self.logic.current_symbol} ({int(progress*100)}%)"
            
            # Draw progress bar
            cv2.rectangle(frame, (50, 50), (350, 80), (50, 50, 50), -1)
            cv2.rectangle(frame, (51, 51), (51 + int(298 * progress), 79), (0, 255, 0), -1)
            
            # Visual feedback for cycling
            if progress >= 1.0 and ACTION_MAP.get(self.logic.current_symbol, {}).get('behavior') == 'cycle':
                cv2.putText(frame, "CYCLING ACTION...", (360, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        cv2.putText(frame, status_text, (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Draw landmarks if present
        if detections:
            for det in detections:
                if 'landmarks' in det:
                    if det.get('type') == 'hand':
                        self.detector.mp_draw.draw_landmarks(
                            frame, det['landmarks'], self.detector.mp_hands.HAND_CONNECTIONS
                        )
                    elif det.get('type') == 'face':
                        # Draw generic face landmarks or specific subset
                        self.detector.mp_draw.draw_landmarks(
                            frame, det['landmarks'], self.detector.mp_face_mesh.FACEMESH_CONTOURS,
                            landmark_drawing_spec=None,
                            connection_drawing_spec=self.detector.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                        )

    def stop(self):
        self.running = False

if __name__ == "__main__":
    app = CamcutsApp()
    app.run()
