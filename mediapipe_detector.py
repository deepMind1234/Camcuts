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
        # Landmark indices
        # Index: 5(mcp), 6(pip), 8(tip)
        # Middle: 9(mcp), 10(pip), 12(tip)
        # Ring: 13(mcp), 14(pip), 16(tip)
        # Pinky: 17(mcp), 18(pip), 20(tip)
        # Wrist: 0

        def is_extended_up(mcp, pip, tip):
            # Tip must be significantly above pip AND pip above mcp
            return tip.y < pip.y - 0.04 and pip.y < mcp.y - 0.01
            
        def is_extended_down(mcp, pip, tip):
            # Tip must be significantly below pip AND pip below mcp
            return tip.y > pip.y + 0.05 and pip.y > mcp.y + 0.01

        def is_curled(mcp, pip, tip):
            # Distance from tip to wrist or MCP is small
            return abs(tip.y - mcp.y) < 0.04
            
        def is_tightly_curled(mcp, pip, tip):
            # Even more strict for ensuring a finger is totally closed
            return abs(tip.y - mcp.y) < 0.03

        # Check states for each finger
        f_index_up = is_extended_up(hand_landmarks.landmark[5], hand_landmarks.landmark[6], hand_landmarks.landmark[8])
        f_index_down = is_extended_down(hand_landmarks.landmark[5], hand_landmarks.landmark[6], hand_landmarks.landmark[8])
        
        # Check others for extension/tight curl
        others_extended = []
        for m, p, t in [(9, 10, 12), (13, 14, 16), (17, 18, 20)]:
            others_extended.append(is_extended_up(hand_landmarks.landmark[m], hand_landmarks.landmark[p], hand_landmarks.landmark[t]))
        
        others_tightly_curled = []
        for m, p, t in [(9, 10, 12), (13, 14, 16), (17, 18, 20)]:
            others_tightly_curled.append(is_tightly_curled(hand_landmarks.landmark[m], hand_landmarks.landmark[p], hand_landmarks.landmark[t]))

        # --- GESTURE LOGIC (STRICT) ---
        
        # 1. INDEX_UP: Index is up, others are TIGHTLY curled
        if f_index_up and all(others_tightly_curled):
            return "INDEX_UP"
            
        # 2. INDEX_DOWN: Index is down, others are TIGHTLY curled
        if f_index_down and all(others_tightly_curled):
            return "INDEX_DOWN"
            
        # 3. OPEN_PALM: All 4 fingers are extended up (and thumb is outside)
        if f_index_up and all(others_extended):
            return "OPEN_PALM"
            
        # 4. FIST: All fingers (including index) are curled
        index_curled = is_curled(hand_landmarks.landmark[5], hand_landmarks.landmark[6], hand_landmarks.landmark[8])
        if index_curled and all(others_tightly_curled):
            return "FIST"

        return None

    def _recognize_face_gestures_multi(self, face_landmarks) -> List[str]:
        gestures = []
        
        # Mouth Open: deliberate wide opening
        upper_lip = face_landmarks.landmark[13]
        lower_lip = face_landmarks.landmark[14]
        # Nose to Chin distance for scale neutralization
        nose = face_landmarks.landmark[1]
        chin = face_landmarks.landmark[152]
        face_scale = abs(nose.y - chin.y)
        
        mouth_dist = abs(upper_lip.y - lower_lip.y)
        if mouth_dist > 0.4 * face_scale: # Proportional check
            gestures.append("MOUTH_OPEN")
        
        return gestures

    def release(self):
        self.hands.close()
        self.face_mesh.close()
