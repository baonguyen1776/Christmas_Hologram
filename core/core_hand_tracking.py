import cv2
import mediapipe as mp
import math

# Import kiểu này để VS Code nhận diện được đường dẫn
from mediapipe.python.solutions import drawing_utils as mp_drawing
from mediapipe.python.solutions import hands as mp_hands

class HandDetector:
    def __init__(self, detection_con=0.7, track_con=0.5):
        self.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=detection_con,
            min_tracking_confidence=track_con
        )
        self.mp_draw = mp_drawing
        self.mp_hands = mp_hands 
        self.results = None

    def find_hands(self, img, draw=True):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

        # Thêm # type: ignore để tắt báo lỗi dòng này
        if self.results.multi_hand_landmarks: # type: ignore
            for hand_lms in self.results.multi_hand_landmarks: # type: ignore
                if draw:
                    self.mp_draw.draw_landmarks(
                        img, hand_lms, self.mp_hands.HAND_CONNECTIONS) # type: ignore
        return img

    def get_distance(self, img, draw=True):
        length = 0
        # Thêm # type: ignore vào đây nữa
        if self.results and self.results.multi_hand_landmarks: # type: ignore
            hand_lms = self.results.multi_hand_landmarks[0] # type: ignore
            h, w, c = img.shape
            
            x1, y1 = int(hand_lms.landmark[4].x * w), int(hand_lms.landmark[4].y * h)
            x2, y2 = int(hand_lms.landmark[8].x * w), int(hand_lms.landmark[8].y * h)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            if draw:
                cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
                cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
                cv2.circle(img, (cx, cy), 10, (255, 0, 255), cv2.FILLED)

            length = math.hypot(x2 - x1, y2 - y1)
            
        return length

if __name__ == "__main__":
    cap = cv2.VideoCapture(1)
    detector = HandDetector()
    print("Camera đang bật... (Nếu thấy lỗi đỏ kệ nó, cứ chạy đi!)")
    
    while True:
        success, img = cap.read()
        if not success: break
        
        img = cv2.flip(img, 1)
        img = detector.find_hands(img)
        dist = detector.get_distance(img)
        
        if dist > 0:
            print(f"Khoảng cách: {int(dist)}")

        cv2.imshow("Hand Tracking Test", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()