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

    def get_hand_rotation(self, img):
        """Tính góc xoay của bàn tay dựa trên vector từ cổ tay đến ngón giữa"""
        angle = 0
        if self.results and self.results.multi_hand_landmarks:  # type: ignore
            hand_lms = self.results.multi_hand_landmarks[0]  # type: ignore
            h, w, c = img.shape
            
            # Lấy điểm cổ tay (landmark 0) và ngón giữa (landmark 12)
            wrist = hand_lms.landmark[0]
            middle_finger = hand_lms.landmark[12]
            
            wx, wy = wrist.x * w, wrist.y * h
            mx, my = middle_finger.x * w, middle_finger.y * h
            
            # Tính góc (radian) từ vector
            angle = math.atan2(mx - wx, wy - my)  # Đảo để 0 là hướng lên
            
        return angle

    def get_two_finger_data(self, img):
        """Lấy dữ liệu 2 ngón (trỏ và cái) để điều khiển zoom và xoay"""
        data = {
            'distance': 0,
            'angle': 0,
            'center_x': 0,
            'center_y': 0,
            'index_x': 0,
            'index_y': 0
        }
        
        if self.results and self.results.multi_hand_landmarks:  # type: ignore
            hand_lms = self.results.multi_hand_landmarks[0]  # type: ignore
            h, w, c = img.shape
            
            # Ngón cái (landmark 4) và ngón trỏ (landmark 8)
            thumb = hand_lms.landmark[4]
            index = hand_lms.landmark[8]
            
            x1, y1 = int(thumb.x * w), int(thumb.y * h)
            x2, y2 = int(index.x * w), int(index.y * h)
            
            # Khoảng cách
            data['distance'] = int(math.hypot(x2 - x1, y2 - y1))
            
            # Góc giữa 2 ngón (dùng để xoay ảnh)
            data['angle'] = int(math.atan2(y2 - y1, x2 - x1))
            
            # Tâm giữa 2 ngón
            data['center_x'] = (x1 + x2) // 2
            data['center_y'] = (y1 + y2) // 2
            
            # Vị trí ngón trỏ
            data['index_x'] = x2
            data['index_y'] = y2
            
        return data
    
    def count_fingers_up(self, img):
        """Đếm số ngón tay đang giơ lên"""
        finger_count = 0
        
        if self.results and self.results.multi_hand_landmarks:  # type: ignore
            hand_lms = self.results.multi_hand_landmarks[0]  # type: ignore
            
            # Tips và knuckles
            # Thumb: landmark 4 vs 3 (dùng x thay vì y vì ngón cái nằm ngang)
            # Index: landmark 8 vs 6
            # Middle: landmark 12 vs 10
            # Ring: landmark 16 vs 14
            # Pinky: landmark 20 vs 18
            
            # Ngón cái - so sánh x (vì nằm ngang)
            if hand_lms.landmark[4].x < hand_lms.landmark[3].x:
                finger_count += 1
            
            # 4 ngón còn lại - so sánh y
            tips = [8, 12, 16, 20]
            knuckles = [6, 10, 14, 18]
            
            for tip_id, knuckle_id in zip(tips, knuckles):
                if hand_lms.landmark[tip_id].y < hand_lms.landmark[knuckle_id].y:
                    finger_count += 1
        
        return finger_count
    
    def get_hand_span(self, img):
        """Tính độ xoè của bàn tay (khoảng cách từ ngón cái đến ngón út)
        Dùng để zoom ảnh khi có 5 ngón"""
        span = 0
        
        if self.results and self.results.multi_hand_landmarks:  # type: ignore
            hand_lms = self.results.multi_hand_landmarks[0]  # type: ignore
            h, w, c = img.shape
            
            # Ngón cái (landmark 4) và ngón út (landmark 20)
            thumb = hand_lms.landmark[4]
            pinky = hand_lms.landmark[20]
            
            x1, y1 = thumb.x * w, thumb.y * h
            x2, y2 = pinky.x * w, pinky.y * h
            
            span = math.hypot(x2 - x1, y2 - y1)
        
        return span
    
    def get_five_finger_data(self, img):
        """Lấy dữ liệu 5 ngón tay để điều khiển zoom ảnh"""
        data = {
            'finger_count': 0,
            'hand_span': 0,  # Khoảng cách từ ngón cái đến ngón út
            'is_spreading': False,  # Đang xoè ra
            'is_closing': False,  # Đang khép lại
        }
        
        if self.results and self.results.multi_hand_landmarks:  # type: ignore
            data['finger_count'] = self.count_fingers_up(img)
            data['hand_span'] = self.get_hand_span(img)
        
        return data

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