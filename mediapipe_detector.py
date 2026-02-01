import cv2
import mediapipe.python.solutions.hands as mp_hands
import mediapipe.python.solutions.face_mesh as mp_face_mesh
import mediapipe.python.solutions.drawing_utils as mp_drawing
from detector_base import BaseDetector
from typing import List, Dict, Any

class MediaPipeDetector(BaseDetector):
    def __init__(self, min_detection_confidence=0.7, min_tracking_confidence=0.5):
        self.mp_hands = mp_hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_face_mesh = mp_face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mp_draw = mp_drawing

    def process_frame(self, frame) -> List[Dict[str, Any]]:
        # Convert the BGR image to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        detections = []
        
        # Process Hands
        hand_results = self.hands.process(image_rgb)
        hands_list = []
        if hand_results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(hand_results.multi_hand_landmarks, hand_results.multi_handedness):
                hands_list.append(hand_landmarks)
                gesture = self._recognize_hand_gesture(hand_landmarks)
                if gesture:
                    detections.append({
                        'label': gesture,
                        'confidence': handedness.classification[0].score,
                        'landmarks': hand_landmarks,
                        'type': 'hand'
                    })
            
            # Check for two-handed X-CROSS
            if len(hands_list) == 2:
                wrist1 = hands_list[0].landmark[0]
                wrist2 = hands_list[1].landmark[0]
                if abs(wrist1.x - wrist2.x) < 0.1: # Wrists are close together
                    detections.append({'label': 'HANDS_X', 'confidence': 1.0, 'landmarks': None, 'type': 'hand'})

        # Process Face
        face_results = self.face_mesh.process(image_rgb)
        if face_results.multi_face_landmarks:
            for face_landmarks in face_results.multi_face_landmarks:
                gestures = self._recognize_face_gestures_multi(face_landmarks)
                for g in gestures:
                    detections.append({
                        'label': g,
                        'confidence': 0.9,
                        'landmarks': face_landmarks,
                        'type': 'face'
                    })
        
        return detections

    def _recognize_hand_gesture(self, hand_landmarks) -> str:
        # Simple definition of "Open" vs "Closed"
        # Finger is OPEN if Tip [8, 12, 16, 20] is above Pip [6, 10, 14, 18]
        # In MediaPipe, lower Y is higher on the screen.
        
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        is_open = []
        for tip, pip in zip(tips, pips):
            is_open.append(hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y)

        # 1. OPEN_PALM: All 4 major fingers are open
        if all(is_open):
            return "OPEN_PALM"
            
        # 2. FIST vs INDEX_DOWN: All 4 major fingers are closed
        if not any(is_open):
            # Special check for INDEX_DOWN vs FIST using distance
            # Tip (8) vs MCP (5) base
            idx_tip = hand_landmarks.landmark[8]
            idx_pip = hand_landmarks.landmark[6]
            idx_mcp = hand_landmarks.landmark[5]
            
            # Calculate 3D Euclidean distance for "extension strength"
            dist_tip_mcp = ((idx_tip.x - idx_mcp.x)**2 + (idx_tip.y - idx_mcp.y)**2 + (idx_tip.z - idx_mcp.z)**2)**0.5
            
            # Index is down only if it's pointing DOWN and is EXTENDED (not curled)
            if idx_tip.y > idx_pip.y + 0.05 and dist_tip_mcp > 0.08:
                return "INDEX_DOWN"
            
            # Confirm FIST by checking if index tip is close to MCP (tucked in)
            if dist_tip_mcp < 0.05:
                return "FIST"
            
            return None
            
        # 3. INDEX_UP / INDEX_LEFT / INDEX_RIGHT: Only index is open
        if is_open[0] and not any(is_open[1:]):
            idx_tip = hand_landmarks.landmark[8]
            idx_mcp = hand_landmarks.landmark[5]
            
            # Check horizontal vs vertical dominance
            dx = idx_tip.x - idx_mcp.x
            dy = idx_tip.y - idx_mcp.y
            
            if abs(dx) > abs(dy) * 1.5: # Horizontally dominant
                if dx < -0.1: return "INDEX_LEFT"
                if dx > 0.1: return "INDEX_RIGHT"
            
            # Fallback to INDEX_UP if vertical and tip is above pip
            if idx_tip.y < hand_landmarks.landmark[6].y:
                return "INDEX_UP"
                
        # 4. PEACE: Index and Middle are open, others are closed
        if is_open[0] and is_open[1] and not is_open[2] and not is_open[3]:
            return "PEACE"

        return None

    def _recognize_face_gestures_multi(self, face_landmarks) -> List[str]:
        gestures = []
        
        # Simple Mouth Open check
        upper_lip = face_landmarks.landmark[13]
        lower_lip = face_landmarks.landmark[14]
        if abs(upper_lip.y - lower_lip.y) > 0.06:
            gestures.append("MOUTH_OPEN")
        
        return gestures

    def release(self):
        self.hands.close()
        self.face_mesh.close()
