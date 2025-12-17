"""
Interactive Christmas Hologram with Hand Tracking
==================================================
Features:
- 3D Christmas Tree from tree_3d.py
- Hand tracking for explosion/collapse effects
- Particles explode into cosmic sphere
- Floating photos in slow elliptical orbits
- Swipe to rotate photos, pinch to zoom selected photo
"""

import pygame
import cv2
import math
import random
import threading
import queue
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import time  # Add for twinkling effect

# Import tree từ scenes
from scenes.tree_3d import HologramTree, BLACK, WHITE, TREE_COLORS

# Import hand tracking
from core.core_hand_tracking import HandDetector

# Import config
from config import (
    TITLE_TEXT, TITLE_FONT_SIZE, TITLE_FONT_BOLD, TITLE_FONT_ITALIC, TITLE_FONT_PATH,
    SUBTITLE_TEXT, SUBTITLE_FONT_SIZE, SUBTITLE_FONT_PATH,
    TITLE_SHADOW_COLOR, TITLE_MAIN_COLOR, SUBTITLE_COLOR, TITLE_SHADOW_OFFSET, SHOW_SHADOW,
    DEBUG_FONT_SIZE, DEBUG_FONT_NAME,
    LOVE_LETTER_HEADER, LOVE_LETTER_CONTENT, LOVE_LETTER_FONT_PATH,
    LOVE_LETTER_HEADER_SIZE, LOVE_LETTER_CONTENT_SIZE,
    LOVE_LETTER_HEADER_COLOR, LOVE_LETTER_CONTENT_COLOR
)

# ============================================================================
# FLOATING PHOTO CLASS
# ============================================================================

@dataclass
class FloatingPhoto:
    """Photo frame orbiting in 3D space"""
    image: pygame.Surface
    original_image: pygame.Surface  # Keep original for zoom
    angle: float
    orbit_radius: float  # Single radius for circular orbit
    orbit_speed: float
    y_offset: float
    scale: float
    fade_alpha: float = 0.0
    is_selected: bool = False
    zoom_scale: float = 1.0  # For fullscreen zoom


# ============================================================================
# COSMIC PARTICLE (Sphere distribution)
# ============================================================================

@dataclass 
class CosmicParticle:
    """Particle in cosmic sphere"""
    # Tree base position (KHÔNG rotate) - để tính toán động
    base_x: float
    base_y: float
    base_z: float
    # Sphere position (target)
    sphere_theta: float  # Latitude angle
    sphere_phi: float    # Longitude angle  
    sphere_radius: float
    # Visual
    color: Tuple[int, int, int]
    size: float
    twinkle_phase: float
    orbit_speed: float  # Speed of rotation in sphere


# ============================================================================
# LOVE LETTER CLASS - Bắn tim mở thư tình
# ============================================================================

class LoveLetter:
    """Love letter with envelope opening animation"""
    
    # States
    HIDDEN = 0
    ENVELOPE = 1
    OPENING = 2
    LETTER = 3
    ZOOMED = 4  # Letter đang được zoom full screen
    COLLAPSING = 5  # Thu thư về cây
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.state = self.HIDDEN
        self.progress = 0.0  # 0-1 animation progress
        self.time_elapsed = 0.0
        self.is_zoomed = False  # Track if letter is currently zoomed
        self.fly_progress = 0.0  # Animation bay từ center cây ra
        
        # Colors
        self.envelope_color = (255, 182, 193)  # Light pink
        self.envelope_dark = (255, 160, 180)   # Darker pink for flap
        self.paper_color = (255, 250, 250)     # Floral white
        
        # Font - use config
        try:
            self.font_large = pygame.font.Font(LOVE_LETTER_FONT_PATH, LOVE_LETTER_HEADER_SIZE)
            self.font_small = pygame.font.Font(LOVE_LETTER_FONT_PATH, LOVE_LETTER_CONTENT_SIZE)
            # Larger fonts for zoomed view
            self.font_zoomed_large = pygame.font.Font(LOVE_LETTER_FONT_PATH, 72)
            self.font_zoomed_small = pygame.font.Font(LOVE_LETTER_FONT_PATH, 48)
        except:
            self.font_large = pygame.font.Font(None, LOVE_LETTER_HEADER_SIZE)
            self.font_small = pygame.font.Font(None, LOVE_LETTER_CONTENT_SIZE)
            self.font_zoomed_large = pygame.font.Font(None, 72)
            self.font_zoomed_small = pygame.font.Font(None, 48)
        
        # Text from config
        self.main_text = LOVE_LETTER_HEADER
        self.sub_text = LOVE_LETTER_CONTENT
        self.header_color = LOVE_LETTER_HEADER_COLOR
        self.content_color = LOVE_LETTER_CONTENT_COLOR
        self.heart_text = "💖"
    
    def trigger(self):
        """Start the love letter animation"""
        self.state = self.ENVELOPE
        self.progress = 0.0
        self.time_elapsed = 0.0
        self.fly_progress = 0.0  # Animation bay từ center ra
    
    def update(self, dt: float):
        """Update animation (dt in seconds)"""
        if self.state == self.HIDDEN:
            return
        
        self.time_elapsed += dt
        
        if self.state == self.ENVELOPE:
            # Bay từ center cây ra (0.5 giây) - NHANH HƠN
            self.fly_progress = min(1.0, self.time_elapsed / 0.5)
            if self.time_elapsed > 0.8:
                self.state = self.OPENING
                self.progress = 0.0
                self.time_elapsed = 0.0
        
        elif self.state == self.OPENING:
            # Opening animation (0.5 seconds) - NHANH HƠN rồi tự động zoom full
            self.progress = min(1.0, self.time_elapsed / 0.5)
            if self.progress >= 1.0:
                # TỰ ĐỘNG CHUYỂN SANG ZOOMED (full content) NGAY LẬP TỨC
                self.state = self.ZOOMED
                self.is_zoomed = True
                self.progress = 1.0
                self.time_elapsed = 0.0
        
        elif self.state == self.LETTER:
            # Letter hiển thị full ngay, không animation
            self.progress = 1.0
        
        elif self.state == self.ZOOMED:
            # Zoomed state - letter content displayed full, stable (no animation)
            pass
        
        elif self.state == self.COLLAPSING:
            # Animation thu thư về cây (0.1 giây)
            self.fly_progress = max(0.0, 1.0 - self.time_elapsed / 0.1)
            if self.time_elapsed > 0.1:
                self.state = self.HIDDEN
                self.fly_progress = 0.0
    
    def set_zoomed(self, zoomed: bool):
        """Set zoomed state for stable full-screen letter view"""
        if zoomed and self.state == self.LETTER:
            self.state = self.ZOOMED
            self.is_zoomed = True
        elif not zoomed and self.state == self.ZOOMED:
            self.state = self.LETTER
            self.is_zoomed = False
    
    def draw(self, surface: pygame.Surface):
        """Draw the love letter"""
        if self.state == self.HIDDEN:
            return
        
        # If ZOOMED, don't draw here (will be drawn by _draw_zoomed_love_letter)
        if self.state == self.ZOOMED:
            return
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        # Vị trí cây (nơi thư bay ra từ đó)
        tree_center_y = int(self.height * 0.45)  # Giữa cây
        
        if self.state == self.ENVELOPE:
            # Animation bay từ center cây ra
            # Smooth easing: ease-out cubic
            t = self.fly_progress
            ease_t = 1 - (1 - t) ** 3  # Ease-out cubic
            
            # Scale từ nhỏ -> lớn
            fly_scale = 0.1 + ease_t * 0.9  # 0.1 -> 1.0
            
            # Position bay từ center cây -> center màn hình
            fly_y = tree_center_y + (center_y - tree_center_y) * ease_t
            
            # Alpha fade in
            fly_alpha = int(255 * min(1.0, ease_t * 2))  # Fade in nhanh hơn
            
            self._draw_envelope(surface, center_x, int(fly_y), alpha=fly_alpha, scale=fly_scale)
        
        elif self.state == self.OPENING:
            # Fade envelope out
            alpha = int(255 * (1 - self.progress))
            self._draw_envelope(surface, center_x, center_y, alpha=alpha)
            # Show paper zooming in
            paper_scale = 0.3 + self.progress * 0.7  # 0.3 -> 1.0
            paper_alpha = int(255 * self.progress)
            self._draw_paper(surface, center_x, center_y, scale=paper_scale, alpha=paper_alpha)
        
        elif self.state == self.LETTER:
            # Show full paper with text - FULL SIZE NGAY LẬP TỨC
            self._draw_paper(surface, center_x, center_y, scale=1.0, alpha=255)
        
        elif self.state == self.COLLAPSING:
            # Animation thu thư về cây (ngược lại với ENVELOPE)
            t = self.fly_progress  # 1.0 -> 0.0
            ease_t = t ** 2  # Ease-in quadratic (chậm đầu, nhanh cuối)
            
            # Scale từ lớn -> nhỏ
            fly_scale = 0.1 + ease_t * 0.9  # 1.0 -> 0.1
            
            # Position bay từ center màn hình -> center cây
            fly_y = tree_center_y + (center_y - tree_center_y) * ease_t
            
            # Alpha fade out
            fly_alpha = int(255 * min(1.0, ease_t * 2))
            
            self._draw_paper(surface, center_x, int(fly_y), scale=fly_scale, alpha=fly_alpha)
    
    def _draw_envelope(self, surface: pygame.Surface, cx: int, cy: int, alpha: int = 255, scale: float = 1.0):
        """Draw pink envelope with paper inside (like image design)"""
        base_w, base_h = 300, 220
        w = int(base_w * scale)
        h = int(base_h * scale)
        
        # Create envelope surface with alpha
        envelope_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        
        # Envelope back (pink)
        envelope_back = (255, 182, 193)  # Light pink
        pygame.draw.rect(envelope_surf, (*envelope_back, alpha), (0, int(60 * scale), w, int(160 * scale)))
        
        # Envelope flap (darker pink) - triangular fold
        flap_points = [(0, int(60 * scale)), (w // 2, 0), (w, int(60 * scale))]
        pygame.draw.polygon(envelope_surf, (*self.envelope_dark, alpha), flap_points)
        
        # Paper inside (cream/beige) - showing from inside envelope
        paper_margin = int(15 * scale)
        paper_w = w - paper_margin * 2
        paper_h = int(100 * scale)
        paper_y = int(70 * scale)
        pygame.draw.rect(envelope_surf, (*self.paper_color, alpha), (paper_margin, paper_y, paper_w, paper_h))
        
        # Paper border
        pygame.draw.rect(envelope_surf, (200, 180, 180, alpha), (paper_margin, paper_y, paper_w, paper_h), max(1, int(2 * scale)))
        
        # Envelope border
        pygame.draw.rect(envelope_surf, (255, 150, 180, alpha), (0, int(60 * scale), w, int(160 * scale)), max(1, int(2 * scale)))
        
        # Draw on main surface centered
        surface.blit(envelope_surf, (cx - w // 2, cy - h // 2))
    
    def _draw_paper(self, surface: pygame.Surface, cx: int, cy: int, scale: float = 1.0, alpha: int = 255):
        """Draw love letter paper (blank, no text - only show in zoom)"""
        width = int(280 * scale)
        height = int(180 * scale)
        
        # Create paper surface
        paper_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Paper background
        pygame.draw.rect(paper_surf, (*self.paper_color, alpha), (0, 0, width, height))
        pygame.draw.rect(paper_surf, (200, 200, 200, alpha), (0, 0, width, height), 2)
        
        # Add decorative lines only
        line_color = (255, 182, 193, alpha)
        for i in range(3):
            y = int(30 + i * 45)
            pygame.draw.line(paper_surf, line_color, (20, y), (width - 20, y), 1)
        
        # Text will only show when zoomed, not here
        
        # Draw on main surface
        surface.blit(paper_surf, (cx - width // 2, cy - height // 2))
    
    def draw_zoomed(self, surface: pygame.Surface, zoom_progress: float):
        """Draw love letter in ZOOMED state - stable, no flickering"""
        if self.state != self.ZOOMED:
            return
        
        # Fixed full size (no animation, stable)
        width = int(self.width * 0.7)
        height = int(self.height * 0.65)
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        # Dark overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        
        # Create paper surface
        paper_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Paper background with nice shadow
        pygame.draw.rect(paper_surf, (30, 30, 30, 100), (5, 5, width, height))  # Shadow
        pygame.draw.rect(paper_surf, self.paper_color, (0, 0, width, height))
        pygame.draw.rect(paper_surf, (200, 180, 180), (0, 0, width, height), 3)  # Border
        
        # Header text (larger)
        header_surf = self.font_zoomed_large.render(self.main_text, True, self.header_color)
        header_rect = header_surf.get_rect(center=(width // 2, height // 3))
        paper_surf.blit(header_surf, header_rect)
        
        # Content text
        content_surf = self.font_zoomed_small.render(self.sub_text, True, self.content_color)
        content_rect = content_surf.get_rect(center=(width // 2, height // 2 + 30))
        paper_surf.blit(content_surf, content_rect)
        
        # Heart decorations
        try:
            heart_font = pygame.font.Font(None, 60)
            hearts = "💖 💕 💖"
            heart_surf = heart_font.render(hearts, True, (255, 100, 150))
            heart_rect = heart_surf.get_rect(center=(width // 2, height - 80))
            paper_surf.blit(heart_surf, heart_rect)
        except:
            pass
        
        # Draw paper centered
        surface.blit(paper_surf, (center_x - width // 2, center_y - height // 2))


# ============================================================================
# ENHANCED HAND TRACKING THREAD
# ============================================================================

class HandTrackingThread(threading.Thread):
    """Separate thread for hand tracking with position tracking"""
    
    def __init__(self, camera_id=1):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.data_queue = queue.Queue(maxsize=5)
        self.running = True
        self.current_distance = 0
        self.current_x = 0  # X position of index finger
        self.prev_x = 0
        self.current_y = 0  # Y position for swipe down detection
        self.prev_y = 0
        self.finger_count = 0  # Number of fingers up
        self.hand_span = 0  # Khoảng cách từ ngón cái đến ngón út
        self.prev_hand_span = 0  # Để track thay đổi
        self.fingers_up = [False] * 5  # Track each finger individually
        self.heart_gesture = False  # Detect trái tim gesture
        self.results = None  # Lưu detector.results để dùng sau
        
    def _detect_heart_gesture(self, detector, img):
        """
        Detect heart gesture (trái tim) bằng 2 tay
        Kiểm tra: ngón trỏ + giữa xoè ra ở cả 2 tay, 2 đầu ngón chéo nhau
        """
        try:
            if not detector.results or not detector.results.multi_hand_landmarks:  # type: ignore
                return False
            
            hands = detector.results.multi_hand_landmarks  # type: ignore
            if len(hands) < 2:
                return False
            
            if img is None:
                return False
            
            h, w, c = img.shape
            
            # Lấy 2 bàn tay
            hand_left = hands[0]
            hand_right = hands[1]
            
            # Kiểm tra ngón trỏ + giữa xoè ra
            # Index tip=8, Middle tip=12
            def check_fingers_up(hand):
                """Check if index + middle up"""
                index_up = hand.landmark[8].y < hand.landmark[6].y  # Index tip < knuckle
                middle_up = hand.landmark[12].y < hand.landmark[10].y  # Middle tip < knuckle
                return index_up and middle_up
            
            # Cả 2 tay phải có index + middle xoè
            if not (check_fingers_up(hand_left) and check_fingers_up(hand_right)):
                return False
            
            # Lấy tọa độ ngón trỏ + giữa của mỗi tay
            # Left hand
            index_left = (hand_left.landmark[8].x * w, hand_left.landmark[8].y * h)
            middle_left = (hand_left.landmark[12].x * w, hand_left.landmark[12].y * h)
            
            # Right hand
            index_right = (hand_right.landmark[8].x * w, hand_right.landmark[8].y * h)
            middle_right = (hand_right.landmark[12].x * w, hand_right.landmark[12].y * h)
            
            # Kiểm tra chéo nhau:
            # Ngón trỏ trái + giữa phải: trái < phải (x), hoặc
            # Ngón giữa trái + trỏ phải: trái < phải (x)
            cross_condition = (
                (index_left[0] < middle_right[0] and middle_left[0] > index_right[0]) or
                (index_right[0] < middle_left[0] and middle_right[0] > index_left[0])
            )
            
            if not cross_condition:
                return False
            
            # Kiểm tra ở vị trí trên màn hình (y < 300)
            avg_y = (index_left[1] + middle_left[1] + index_right[1] + middle_right[1]) / 4
            
            if avg_y < 350:  # Ở trên
                return True
            
            return False
        except Exception as e:
            return False
        
    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Set max_num_hands=2 để detect cả 2 bàn tay
        detector = HandDetector(detection_con=0.7, track_con=0.5)
        # Tái tạo hands object với max_num_hands=2
        from mediapipe.python.solutions import hands as mp_hands
        detector.hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Nhận diện tối đa 2 bàn tay
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        while self.running:
            success, img = cap.read()
            if not success:
                continue
            
            img = cv2.flip(img, 1)
            img = detector.find_hands(img, draw=False)
            dist = detector.get_distance(img, draw=False)
            
            # Get finger positions and count
            index_x = 0
            index_y = 0
            finger_count = 0
            fingers_up = [False] * 5  # Track each finger: thumb, index, middle, ring, pinky
            heart_gesture = False  # Detect trái tim gesture
            
            if detector.results and detector.results.multi_hand_landmarks:  # type: ignore
                # Check heart gesture using improved detector method
                heart_result = detector.detect_heart_style(img)
                if heart_result == "Finger_Heart":
                    heart_gesture = True
                
                hand_lms = detector.results.multi_hand_landmarks[0]  # type: ignore
                h, w, c = img.shape
                index_x = int(hand_lms.landmark[8].x * w)
                index_y = int(hand_lms.landmark[8].y * h)
                
                # Count fingers up (simple: check if fingertip is above knuckle)
                # Thumb: landmark 4 vs 3
                # Index: landmark 8 vs 6
                # Middle: landmark 12 vs 10
                # Ring: landmark 16 vs 14
                # Pinky: landmark 20 vs 18
                tips = [4, 8, 12, 16, 20]
                knuckles = [3, 6, 10, 14, 18]
                
                for i, (tip_id, knuckle_id) in enumerate(zip(tips, knuckles)):
                    tip_y = hand_lms.landmark[tip_id].y
                    knuckle_y = hand_lms.landmark[knuckle_id].y
                    if tip_y < knuckle_y:  # Tip higher than knuckle = finger up
                        finger_count += 1
                        fingers_up[i] = True
                
                # Tính hand span (khoảng cách từ ngón cái đến ngón út)
                thumb = hand_lms.landmark[4]
                pinky = hand_lms.landmark[20]
                hand_span = math.hypot((pinky.x - thumb.x) * w, (pinky.y - thumb.y) * h)
            else:
                hand_span = 0
                fingers_up = [False] * 5
            
            try:
                self.data_queue.put_nowait((dist, index_x, index_y, finger_count, hand_span, fingers_up, heart_gesture))
            except queue.Full:
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait((dist, index_x, index_y, finger_count, hand_span, fingers_up, heart_gesture))
                except:
                    pass
        
        cap.release()
    
    def get_data(self):
        try:
            self.current_distance, new_x, new_y, self.finger_count, new_span, self.fingers_up, self.heart_gesture = self.data_queue.get_nowait()
            self.prev_x = self.current_x
            self.prev_y = self.current_y
            self.current_x = new_x
            self.current_y = new_y
            self.prev_hand_span = self.hand_span
            self.hand_span = new_span
        except queue.Empty:
            pass
        return self.current_distance, self.current_x, self.prev_x, self.current_y, self.prev_y, self.finger_count, self.hand_span, self.prev_hand_span
    
    def stop(self):
        self.running = False


# ============================================================================
# INTERACTIVE HOLOGRAM
# ============================================================================

class InteractiveHologram:
    """Wraps HologramTree with cosmic explosion and photo interaction"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Use existing HologramTree
        self.tree = HologramTree(width, height)
        
        # Explosion state
        self.explosion_progress = 0.0
        self.target_explosion = 0.0
        self.explosion_speed = 0.015  # Chậm hơn nữa để mượt (từ 0.02)
        
        # Cosmic sphere rotation
        self.sphere_rotation = 0.0
        self.sphere_rotation_speed = 0.002  # Chậm hơn một chút
        
        # Create cosmic particles from tree
        self.cosmic_particles: List[CosmicParticle] = []
        self._create_cosmic_particles()
        
        # Photos
        self.photos: List[FloatingPhoto] = []
        self.photos_visible = False
        self.photo_orbit_angle = 0.0  # Global orbit angle
        self.photo_orbit_speed = 0.002  # Slow rotation speed (từ từ)
        self.selected_photo_index = -1  # -1 = none selected
        self.photo_zoom_progress = 0.0  # 0 = normal, 1 = fullscreen
        self.photo_extraction_progress = 0.0  # 0-1: animation kéo ảnh ra khỏi quỹ đạo
        self.photo_extraction_start_time = 0
        self.photo_extraction_duration = 0.25  
        self._load_photos()
        
        # Hand tracking state - ĐƠN GIẢN HÓA
        self.zoom_in_threshold = 120    # Bung ngón để zoom in (distance > 80)
        self.zoom_out_threshold = 50   # Chụm ngón để zoom out (distance < 50)
        
        # Gesture debounce
        self.last_gesture_time = 0
        self.gesture_cooldown = 15  # 0.25 giây @ 60fps - NHANH HƠN
        
        # Protection cooldown sau khi TREE -> PHOTOS (3 giây không nhận gesture)
        self.explosion_start_time = 0
        self.explosion_protection_duration = 60  # 1 giây @ 60fps (để zoom ảnh sớm hơn)
        
        # Zoom-out hold timer (cần giữ 3 giây liên tục)
        self.zoom_out_hold_start = 0
        self.zoom_out_hold_duration = 180  # 3 giây @ 60fps
        
        # Track previous distance
        self.prev_distance = 0
        
        # Base hand span for zoom calculation
        self.base_hand_span = 0
        
        # Interaction mode: "tree", "photos", "zoom_photo", "heart_photos", "zoom_letter"
        self.interaction_mode = "tree"
        
        # HEART MODE - khi user bắn tim, tắt hoàn toàn ảnh
        self.heart_mode = False  # True = đang ở chế độ trái tim (chỉ có thư, không có ảnh)
        
        # Love letter animation
        self.love_letter = LoveLetter(width, height)
        self.heart_detected_cooldown = 0
        self.love_letter_zoom_progress = 0.0  # Zoom state cho love letter (0.0 - 1.0)
        
        # Time for animation
        self.time = 0
    
    def _create_cosmic_particles(self):
        """Create particles distributed on a cosmic sphere"""
        self.cosmic_particles = []
        
        # From tree particles - distribute on sphere
        # Lưu BASE position (không rotate) để có thể tính toán động theo rotation
        # Lấy TẤT CẢ particles để giữ mật độ
        for p in self.tree.tree_particles:
            # Random position on sphere (uniform distribution)
            theta = random.uniform(0, math.pi)  # 0 to π
            phi = random.uniform(0, 2 * math.pi)  # 0 to 2π
            radius = random.uniform(400, 800)  # Large cosmic sphere
            
            self.cosmic_particles.append(CosmicParticle(
                base_x=p.base_x,  # Lưu base position (không rotate)
                base_y=p.y,
                base_z=p.base_z,
                sphere_theta=theta,
                sphere_phi=phi,
                sphere_radius=radius,
                color=p.color,
                size=p.size,
                twinkle_phase=p.twinkle_phase,
                orbit_speed=random.uniform(0.001, 0.004)  # Individual orbit speeds
            ))
        
        # From heart particles - LẤY TẤT CẢ
        for p in self.tree.heart_particles:
            theta = random.uniform(0, math.pi)
            phi = random.uniform(0, 2 * math.pi)
            radius = random.uniform(450, 850)
            
            self.cosmic_particles.append(CosmicParticle(
                base_x=p.base_x,  # Lưu base position
                base_y=p.y,
                base_z=p.base_z,
                sphere_theta=theta,
                sphere_phi=phi,
                sphere_radius=radius,
                color=p.color,
                size=p.size,
                twinkle_phase=p.pulse_phase,
                orbit_speed=random.uniform(0.001, 0.005)
            ))
    
    def _load_photos(self):
        """Load all image files from assets folder automatically"""
        import os
        import glob
        
        # Auto-detect all image files in assets/
        assets_dir = "assets"
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp"]
        
        photo_paths = []
        for ext in image_extensions:
            photo_paths.extend(glob.glob(os.path.join(assets_dir, ext)))
        
        # Sort for consistent ordering
        photo_paths.sort()
        
        num_photos = len(photo_paths)
        for i, path in enumerate(photo_paths):
            try:
                original = pygame.image.load(path)
                # Keep original for fullscreen zoom
                thumb = pygame.transform.scale(original, (140, 175))
                
                self.photos.append(FloatingPhoto(
                    image=thumb,
                    original_image=original,
                    angle=(i / max(1, num_photos)) * 2 * math.pi,  # Evenly distributed
                    orbit_radius=380,
                    orbit_speed=0.0015,
                    y_offset=0,
                    scale=1.0,
                    fade_alpha=0.0
                ))
            except Exception as e:
                print(f"Could not load {path}: {e}")
        
        print(f"Loaded {len(self.photos)} photos from {assets_dir}/")
    
    def update_hand_tracking(self, distance: float, index_x: int, prev_x: int, index_y: int, prev_y: int, finger_count: int, hand_span: float = 0, prev_hand_span: float = 0, fingers_up: list = []):
        """
        Update based on hand tracking data
        
        Logic:
        - TREE: Chỉ nhận zoom_in (bung ngón) -> chuyển sang PHOTOS
        - PHOTOS: zoom_in (bung rộng) -> zoom ảnh (5 ngón), zoom_out (chụm) -> về TREE
        - ZOOM_PHOTO: Dùng hand_span để điều khiển độ zoom, chụm ngón -> thoát
        """
        
        # Set default fingers_up if not provided
        if fingers_up is None:
            fingers_up = [False] * 5
        
        # Check cooldown
        can_gesture = (self.time - self.last_gesture_time) > self.gesture_cooldown
        
        # PHOTOS mode xử lý ngay cả khi distance = 0 (zoom-out hold timer)
        if not can_gesture:
            # Nếu không được gesture, bỏ qua TRỪ PHOTOS mode (vẫn cần xử lý hold timer)
            if self.interaction_mode != "photos":
                return
        
        # TREE mode bỏ qua khi distance = 0
        if self.interaction_mode == "tree" and distance <= 0:
            return
        
        # === MODE: TREE ===
        if self.interaction_mode == "tree":
            # Chỉ nhận diện ZOOM IN (bung ngón) để mở vũ trụ
            if distance > self.zoom_in_threshold:
                # Tạo lại cosmic particles với rotation hiện tại
                self._create_cosmic_particles()
                self.target_explosion = 1.0
                self.photos_visible = True
                self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                self.explosion_start_time = self.time  # BẮT ĐẦU PROTECTION
                self.zoom_out_hold_start = 0  # Reset hold timer
                print(f"[GESTURE] TREE -> PHOTOS (distance={distance:.0f})")
        
        # === MODE: PHOTOS (vũ trụ với ảnh xoay) ===
        elif self.interaction_mode == "photos":
            # CHECK PROTECTION: Không nhận gesture trong 3 giây đầu
            if (self.time - self.explosion_start_time) < self.explosion_protection_duration:
                return  # Bỏ qua mọi gesture
            
            # XÒE 5 NGÓN -> zoom NGAY LẬP TỨC (ảnh hoặc thư tình)
            if finger_count >= 5 and hand_span > 100:  # 5 ngón giơ rộng
                # Nếu thư tình đang hiển thị (LETTER state), zoom thư lên ZOOMED state
                if self.love_letter.state == LoveLetter.LETTER:
                    self.love_letter.set_zoomed(True)  # Switch to ZOOMED state
                    self.interaction_mode = "zoom_letter"  # New mode for letter zoom
                    self.last_gesture_time = self.time
                    self.zoom_out_hold_start = 0
                    print(f"[GESTURE] PHOTOS -> ZOOM_LETTER (Love Letter, 5 fingers, hand_span={hand_span:.0f})")
                # Nếu không có thư, zoom ảnh
                elif self.love_letter.state == LoveLetter.HIDDEN:
                    self._select_closest_photo()
                    if self.selected_photo_index >= 0:
                        self.interaction_mode = "zoom_photo"
                        self.photo_zoom_progress = 0.0
                        self.photo_extraction_start_time = self.time
                        self.photo_extraction_progress = 0.0
                        self.last_gesture_time = self.time
                        self.zoom_out_hold_start = 0  # Reset collapse timer
                        print(f"[GESTURE] PHOTOS -> ZOOM_PHOTO (Photo, 5 fingers, hand_span={hand_span:.0f})")
            
            # ĐÚng 2 NGÓN XÒE RA (THUMB + INDEX) -> COLLAPSE NGAY VỀ TREE
            # Điều kiện: Chỉ thumb lên + index lên, các ngón khác xuống + hand_span lớn (xoè)
            elif fingers_up[0] and fingers_up[1] and not (fingers_up[2] or fingers_up[3] or fingers_up[4]) and hand_span > 100:
                # Không set target_explosion ngay, để thư collapse trước
                self.photos_visible = False
                self.interaction_mode = "collapsing"
                self.last_gesture_time = self.time
                self.zoom_out_hold_start = 0
                print(f"[GESTURE] PHOTOS -> COLLAPSING (2 fingers spread: thumb+index open, hand_span={hand_span:.0f})")
            
            # 2 NGÓN CHỤM (THUMB + INDEX CHỤM LẠI) -> NHƯ CŨ (BẢO LƯU CHO SAU)
            # Hiện tại không dùng vì 2 ngón chụm dùng ở ZOOM_PHOTO mode
            elif fingers_up[0] and fingers_up[1] and not (fingers_up[2] or fingers_up[3] or fingers_up[4]) and hand_span <= 80:
                # 2 ngón chụm lại - bỏ qua (không làm gì)
                pass
            else:
                # Không còn chụm hoặc xoè -> reset timer
                if self.zoom_out_hold_start > 0:
                    print(f"[GESTURE] Pinch hold cancelled ({finger_count} fingers, hand_span={hand_span:.0f})")
                self.zoom_out_hold_start = 0
        
        # === MODE: COLLAPSING (đang thu về cây) ===
        elif self.interaction_mode == "collapsing":
            # Bắt đầu animation thu thư về cây (nếu đang hiển thị)
            if self.love_letter.state in [LoveLetter.ZOOMED, LoveLetter.LETTER]:
                self.love_letter.state = LoveLetter.COLLAPSING
                self.love_letter.time_elapsed = 0.0
                self.love_letter.fly_progress = 1.0
            
            # Khi thư xong collapse, mới bắt đầu collapse particles
            if self.love_letter.state == LoveLetter.HIDDEN and self.target_explosion > 0:
                self.target_explosion = 0.0
            
            # Chờ cả thư và particles xong mới chuyển về tree
            if self.explosion_progress == 0 and self.love_letter.state == LoveLetter.HIDDEN:
                self.interaction_mode = "tree"
                self.heart_mode = False  # Tắt heart mode
                print(f"[GESTURE] COLLAPSING -> TREE (animation done)")
        
        # === MODE: HEART_PHOTOS (vũ trụ với THƯ, KHÔNG CÓ ẢNH) ===
        elif self.interaction_mode == "heart_photos":
            # CHECK PROTECTION: Không nhận gesture trong thời gian đầu
            if (self.time - self.explosion_start_time) < self.explosion_protection_duration:
                return  # Bỏ qua mọi gesture
            
            # XÒE 5 NGÓN -> zoom THƯ lên full screen
            if finger_count >= 5 and hand_span > 100:
                if self.love_letter.state == LoveLetter.LETTER:
                    self.love_letter.set_zoomed(True)
                    self.interaction_mode = "zoom_letter"
                    self.last_gesture_time = self.time
                    print(f"[GESTURE] HEART_PHOTOS -> ZOOM_LETTER (5 fingers)")
            
            # 2 NGÓN XÒE RA -> COLLAPSE VỀ TREE
            elif fingers_up[0] and fingers_up[1] and not (fingers_up[2] or fingers_up[3] or fingers_up[4]) and hand_span > 100:
                # Không set target_explosion ngay, để thư collapse trước
                self.interaction_mode = "collapsing"
                self.last_gesture_time = self.time
                print(f"[GESTURE] HEART_PHOTOS -> COLLAPSING")
        
        # === MODE: ZOOM_LETTER (đang xem thư phóng to - CỐ ĐỊNH, KHÔNG GIẬT) ===
        elif self.interaction_mode == "zoom_letter":
            # 2 ngón chụm -> thoát zoom letter, về lại heart_photos hoặc photos
            if finger_count <= 2:
                self.love_letter.set_zoomed(False)  # Back to LETTER state
                # Trả về mode phù hợp
                if self.heart_mode:
                    self.interaction_mode = "heart_photos"
                else:
                    self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                print(f"[GESTURE] ZOOM_LETTER -> {'HEART_PHOTOS' if self.heart_mode else 'PHOTOS'} (pinch detected, exit)")
        
        # === MODE: ZOOM_PHOTO (đang xem ảnh phóng to) ===
        elif self.interaction_mode == "zoom_photo":
            # Dùng finger_count + hand_span để điều khiển zoom động
            # - 2 NGÓN CHỤM (finger_count <= 2) -> EXIT NGAY LẬP TỨC
            # - 4-5 NGÓN XÒE -> Map hand_span sang zoom level (càng xoè rộng càng to)
            
            # TASK 1: 2 ngón chụm -> exit ngay lập tức
            if finger_count <= 2:
                self.photo_zoom_progress = 0
                self.selected_photo_index = -1
                self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                print(f"[GESTURE] ZOOM_PHOTO -> PHOTOS (pinch detected, exit immediately)")
                return
            
            # TASK 2: Zoom theo hand_span cho ảnh
            if finger_count >= 4 and hand_span > 0:
                if self.selected_photo_index >= 0:
                    # Map hand_span sang zoom level cho ảnh
                    # hand_span: 100 (chụm) -> 300 (xoè rộng)
                    # zoom: 0.1 (nhỏ) -> 1.0 (to)
                    min_span = 100
                    max_span = 350
                    target_zoom = (hand_span - min_span) / (max_span - min_span)
                    target_zoom = max(0.1, min(1.0, target_zoom))  # Clamp 0.1-1.0
                    
                    # Smooth interpolation
                    self.photo_zoom_progress += (target_zoom - self.photo_zoom_progress) * 0.15
            else:
                # 3 ngón hoặc không detect hand -> giữ zoom hiện tại
                pass
        
        self.prev_distance = distance
    
    def _select_closest_photo(self):
        """Select photo closest to screen center (larger detection area)"""
        if not self.photos or len(self.photos) == 0:
            self.selected_photo_index = -1
            return
        
        best_idx = -1
        best_score = -float('inf')
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        # Ellipse parameters (must match _draw_photos)
        ellipse_a = 580
        ellipse_b = 300
        tilt_angle = math.radians(15)
        loop_amplitude = 120
        y_offset_base = 80
        
        for i, photo in enumerate(self.photos):
            if photo.fade_alpha < 100:  # Bỏ qua ảnh chưa hiện đủ
                continue
            
            # Calculate ellipse orbit position
            time_offset = (i / len(self.photos)) * 2 * math.pi
            angle = self.photo_orbit_angle + time_offset
            
            # Base ellipse coordinates với vòng lặp
            x_base = ellipse_a * math.cos(angle)
            z_base = ellipse_b * math.sin(angle)
            y_wave = -loop_amplitude * math.sin(angle) * (0.3 + 0.7 * max(0, -math.cos(angle)))
            y_base = y_wave + y_offset_base
            
            # Apply tilt
            x = x_base
            y = y_base * math.cos(tilt_angle) - z_base * math.sin(tilt_angle)
            z = y_base * math.sin(tilt_angle) + z_base * math.cos(tilt_angle)
            
            # Project to screen
            pos = self.tree.project_3d(x, y, z, 1.0)
            if pos:
                # Tính khoảng cách từ ảnh đến tâm màn hình
                dist_to_center = math.hypot(pos[0] - center_x, pos[1] - center_y)
                
                # Score = z (front bonus) - distance penalty
                # Ảnh gần tâm hơn và phía trước sẽ có score cao hơn
                # Mở rộng vùng nhận diện bằng cách giảm penalty distance
                score = z * 2 - dist_to_center * 0.3
                
                if score > best_score:
                    best_score = score
                    best_idx = i
        
        self.selected_photo_index = best_idx
    
    def _get_sphere_position(self, particle: CosmicParticle) -> Tuple[float, float, float]:
        """Get current position on rotating sphere"""
        theta = particle.sphere_theta
        phi = particle.sphere_phi + self.sphere_rotation + self.time * particle.orbit_speed
        r = particle.sphere_radius
        
        x = r * math.sin(theta) * math.cos(phi)
        y = r * math.cos(theta)
        z = r * math.sin(theta) * math.sin(phi)
        
        return x, y, z
    
    def _draw_cosmic_particles(self, surface: pygame.Surface, zoom: float):
        """Draw particles in cosmic sphere state với smooth transition (optimized)"""
        exp = self.explosion_progress
        
        # Skip expensive rendering if not needed
        if len(self.cosmic_particles) == 0:
            return
        
        # Giảm số particles vẽ khi explosion_progress thấp để tăng FPS
        # Khi exp < 0.3: chỉ vẽ 50% particles
        skip_step = 1 if exp > 0.3 else 2
        
        # Quintic smoothstep easing cho cực kỳ mượt
        smooth_exp = exp * exp * exp * (exp * (exp * 6 - 15) + 10)
        
        # Lấy rotation HIỆN TẠI của tree để tính target position động
        current_rot = self.tree.rotation
        cos_rot = math.cos(current_rot)
        sin_rot = math.sin(current_rot)
        
        render_list = []
        
        for idx, p in enumerate(self.cosmic_particles):
            # Skip some particles for performance
            if idx % skip_step != 0:
                continue
            
            # Get sphere target position
            sphere_x, sphere_y, sphere_z = self._get_sphere_position(p)
            
            # Tính tree target position dựa trên rotation HIỆN TẠI
            tree_x = p.base_x * cos_rot - p.base_z * sin_rot
            tree_y = p.base_y
            tree_z = p.base_x * sin_rot + p.base_z * cos_rot
            
            # Interpolate giữa tree position (động theo rotation) và sphere position
            curr_x = tree_x * (1 - smooth_exp) + sphere_x * smooth_exp
            curr_y = tree_y * (1 - smooth_exp) + sphere_y * smooth_exp
            curr_z = tree_z * (1 - smooth_exp) + sphere_z * smooth_exp
            
            render_list.append((p, curr_x, curr_y, curr_z))
        
        # Sort by Z (far to near)
        render_list.sort(key=lambda item: item[3], reverse=True)
        
        for p, curr_x, curr_y, curr_z in render_list:
            pos = self.tree.project_3d(curr_x, curr_y, curr_z, zoom)
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                # Twinkle effect - giống tree gốc
                twinkle = 0.55 + 0.45 * math.sin(self.time * 0.04 + p.twinkle_phase)
                
                # Depth-based brightness (closer = brighter)
                depth_brightness = 0.6 + 0.4 * min(1.0, pos[2] / 0.8)
                
                final_brightness = twinkle * depth_brightness
                size = p.size * pos[2] * zoom * 1.4
                
                # SỬ DỤNG GLOW PARTICLE METHOD TỪ TREE GỐC để giữ màu sắc đẹp
                self.tree._draw_glow_particle(surface, (pos[0], pos[1]), p.color, size, final_brightness)
    
    def _draw_snow_particles(self, surface: pygame.Surface, zoom: float):
        """Draw floating snow/star particles in background (optimized)"""
        # Chỉ vẽ 70% snow particles để tăng FPS
        skip_step = 2 if len(self.tree.snow_particles) > 200 else 1
        
        for idx, snow in enumerate(self.tree.snow_particles):
            if idx % skip_step != 0:
                continue
            
            # Project 3D position to 2D
            pos = self.tree.project_3d(snow.x, snow.y, snow.z, zoom)
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                # Twinkle effect (simpler calculation)
                twinkle = 0.5 + 0.5 * math.sin(self.time * 0.05 + snow.twinkle_phase)
                brightness = int(snow.brightness * twinkle)
                
                # Draw white/light blue stars
                color = (brightness, brightness, min(255, brightness + 20))
                size = max(1, int(snow.size * pos[2] * zoom))
                
                pygame.draw.circle(surface, color, (pos[0], pos[1]), size)
    
    def _draw_photos(self, surface: pygame.Surface, zoom: float):
        """Draw orbiting photos in tilted 3D ellipse orbit - from center animation"""
        
        # Collect all photos with their positions for z-sorting
        render_list = []
        
        center_x = self.width // 2
        center_y = self.height // 2
        
        for i, photo in enumerate(self.photos):
            if photo.fade_alpha < 5:
                continue
            
            # Elliptical orbit với vòng lặp xuống dưới (figure-8 style)
            # Each photo offset on the ellipse
            time_offset = (i / len(self.photos)) * 2 * math.pi
            angle = self.photo_orbit_angle + time_offset
            
            # Ellipse parameters - hạ thấp và rộng hơn
            ellipse_a = 580  # Semi-major axis (horizontal) - rộng hơn
            ellipse_b = 300  # Semi-minor axis (depth) - hẹp hơn để elip rõ hơn
            
            # Tilt lên trên một chút (nghiêng về phía người xem)
            tilt_angle = math.radians(15)  # Nghiêng lên 15 độ
            
            # Base ellipse coordinates (in XZ plane)
            x_base = ellipse_a * math.cos(angle)
            z_base = ellipse_b * math.sin(angle)
            
            # Tạo quỹ đạo có vòng xuống dưới (sinusoidal wave)
            loop_amplitude = 120
            y_wave = -loop_amplitude * math.sin(angle) * (0.3 + 0.7 * max(0, -math.cos(angle)))
            
            # Offset xuống dưới để hạ thấp quỹ đạo tổng thể
            y_offset_base = 80
            y_base = y_wave + y_offset_base
            
            # Apply tilt transformation (rotate around X axis) - nghiêng lên
            x = x_base
            y = y_base * math.cos(tilt_angle) - z_base * math.sin(tilt_angle)
            z = y_base * math.sin(tilt_angle) + z_base * math.cos(tilt_angle)
            
            # Project to screen coordinates (FINAL position on orbit)
            final_pos = self.tree.project_3d(x, y, z, zoom)
            if not final_pos:
                continue
            
            # Interpolate position from center to orbit position based on fade_alpha
            progress = photo.fade_alpha / 255.0  # 0 to 1
            ease_progress = progress * progress * (3 - 2 * progress)  # Smoothstep
            
            # === APPLY EXTRACTION EFFECT ===
            # Nếu ảnh này đang được kéo ra, interpolate từ vị trí quỹ đạo về tâm + scale up
            if i == self.selected_photo_index and self.photo_extraction_progress > 0:
                extraction = self.photo_extraction_progress
                # Lerp position từ orbit_pos về center
                curr_x = final_pos[0] + (center_x - final_pos[0]) * extraction
                curr_y = final_pos[1] + (center_y - final_pos[1]) * extraction
                # Ảnh được chọn sẽ lớn hơn (scale up)
                ease_progress = ease_progress * (1 + extraction * 0.5)
            else:
                # Các ảnh khác vẫn quay bình thường nhưng fade ra khi có ảnh được chọn
                curr_x = center_x + (final_pos[0] - center_x) * ease_progress
                curr_y = center_y + (final_pos[1] - center_y) * ease_progress
            
            render_list.append((i, photo, x, y, z, (curr_x, curr_y), angle, ease_progress, final_pos))
        
        # Sort by Z (draw far photos first, near photos last - painter's algorithm)
        render_list.sort(key=lambda item: item[4])
        
        for i, photo, x, y, z, pos, angle, ease_progress, final_pos in render_list:
            # Perspective scaling
            ellipse_b = 300
            depth_factor = 0.55 + 0.45 * ((z + ellipse_b) / (2 * ellipse_b))
            base_scaled_w = int(photo.image.get_width() * depth_factor * zoom * 1.2)
            base_scaled_h = int(photo.image.get_height() * depth_factor * zoom * 1.2)
            
            # Scale from small (0.3) to full size based on progress
            scaled_w = int(base_scaled_w * (0.3 + 0.7 * ease_progress))
            scaled_h = int(base_scaled_h * (0.3 + 0.7 * ease_progress))
            
            if scaled_w > 20 and scaled_h > 20:
                scaled_img = pygame.transform.scale(photo.image, (scaled_w, scaled_h))
                
                # Apply alpha: giảm alpha cho ảnh không được chọn khi có extraction
                alpha = int(photo.fade_alpha)
                if i != self.selected_photo_index and self.photo_extraction_progress > 0:
                    # Fade out các ảnh khác khi ảnh được chọn đang được kéo ra
                    alpha = int(photo.fade_alpha * (1 - self.photo_extraction_progress * 0.5))
                
                if alpha < 255:
                    scaled_img.set_alpha(alpha)
                
                # Draw photo at interpolated position
                surface.blit(scaled_img, (pos[0] - scaled_w // 2, pos[1] - scaled_h // 2))
    
    def _draw_zoomed_photo(self, surface: pygame.Surface):
        """Draw selected photo in fullscreen zoom"""
        if self.selected_photo_index < 0 or self.selected_photo_index >= len(self.photos):
            return
        
        photo = self.photos[self.selected_photo_index]
        progress = self.photo_zoom_progress
        
        if progress < 0.01:
            return
        
        # Use original high-res image
        orig = photo.original_image
        orig_w, orig_h = orig.get_size()
        
        # Calculate target size (fit screen with padding)
        max_w = int(self.width * 0.8)
        max_h = int(self.height * 0.8)
        
        # Maintain aspect ratio
        scale = min(max_w / orig_w, max_h / orig_h)
        target_w = int(orig_w * scale)
        target_h = int(orig_h * scale)
        
        # Interpolate size based on zoom progress
        small_w = int(photo.image.get_width() * 1.5)
        small_h = int(photo.image.get_height() * 1.5)
        
        curr_w = int(small_w + (target_w - small_w) * progress)
        curr_h = int(small_h + (target_h - small_h) * progress)
        
        # Dark overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(180 * progress)))
        surface.blit(overlay, (0, 0))
        
        # Scale and draw photo (no frame)
        scaled = pygame.transform.scale(orig, (curr_w, curr_h))
        x = (self.width - curr_w) // 2
        y = (self.height - curr_h) // 2
        
        surface.blit(scaled, (x, y))
    
    def update(self):
        """Update animation"""
        self.time += 1
        
        # Smooth explosion transition
        diff = self.target_explosion - self.explosion_progress
        
        if diff > 0:
            # Expanding: smooth ease-out
            easing = 0.06 + abs(diff) * 0.08
        else:
            # Collapsing: khớp với thư (0.1 giây ~ 6 frames at 60fps)
            easing = 0.4 + abs(diff) * 0.4
        
        self.explosion_progress += diff * easing
        
        # Snap to 0 khi đã gần để chuyển về tree.draw() gốc
        if self.explosion_progress < 0.05 and self.target_explosion == 0:
            self.explosion_progress = 0
        
        self.explosion_progress = max(0, min(1, self.explosion_progress))
        
        # Update love letter
        self.love_letter.update(1/60.0)  # 60 FPS
        
        # Nếu love letter vừa tự động chuyển sang ZOOMED, cập nhật interaction_mode
        if self.love_letter.state == LoveLetter.ZOOMED and self.interaction_mode != "zoom_letter":
            self.interaction_mode = "zoom_letter"
        
        # Sphere rotation
        self.sphere_rotation += self.sphere_rotation_speed
        
        # Auto-rotate photos around ellipse orbit when visible
        if self.photos_visible:
            self.photo_orbit_angle += self.photo_orbit_speed * 3.5  # NHANH HƠN 1 CHÚT
        
        # Update photo extraction animation (kéo ảnh ra khỏi quỹ đạo) + zoom
        if self.interaction_mode == "zoom_photo":
            elapsed = (self.time - self.photo_extraction_start_time) / 60.0  # Convert to seconds
            extraction_progress = min(1.0, elapsed / self.photo_extraction_duration)
            # Smoothstep easing cho animation mượt
            self.photo_extraction_progress = extraction_progress * extraction_progress * (3 - 2 * extraction_progress)
            # Auto-zoom during extraction phase (0->0.7)
            if self.photo_extraction_progress < 1.0:
                self.photo_zoom_progress = self.photo_extraction_progress * 0.7  # Quick zoom to 0.7
        else:
            self.photo_extraction_progress = 0.0
        
        # Update photo visibility
        for i, photo in enumerate(self.photos):
            if self.photos_visible:
                # Fade in tuần tự từng ảnh (stagger effect)
                delay = i * 3  # Mỗi ảnh delay 3 frame
                if self.time > delay:
                    photo.fade_alpha = min(255, photo.fade_alpha + 4)
            else:
                # Fade out NHANH HƠN khi thu về cây
                photo.fade_alpha = max(0, photo.fade_alpha - 12)
    
    def draw(self, surface: pygame.Surface, zoom: float = 1.0):
        """Main draw method với crossfade mượt mà"""
        
        # Khi explosion_progress = 0, vẽ cây từ cosmic state + tuyết (không vẽ tree.draw() gốc)
        # Cây sau zoom out sẽ trở thành cây "ban đầu" cho lần tiếp theo
        
        # Vẽ snow particles (background stars) trước
        self._draw_snow_particles(surface, zoom)
        
        # Vẽ cosmic particles (bao gồm cây + trái tim)
        self._draw_cosmic_particles(surface, zoom)
        
        # Draw photos nếu còn hiển thị VÀ KHÔNG phải heart_mode
        # Trong heart_mode, chỉ có thư, KHÔNG có ảnh!
        if self.explosion_progress > 0.1 and not self.heart_mode:
            self._draw_photos(surface, zoom)
        
        # CÂY TIẾP TỤC XOAY - particles sẽ động theo rotation
        self.tree.update()
        
        # Draw zoomed photo on top (chỉ khi KHÔNG phải heart_mode)
        if self.interaction_mode == "zoom_photo" and not self.heart_mode:
            self._draw_zoomed_photo(surface)
        
        # Draw zoomed love letter (stable, no flickering)
        if self.interaction_mode == "zoom_letter":
            self.love_letter.draw_zoomed(surface, 1.0)
        
        # Draw love letter on top (non-zoomed states: ENVELOPE, OPENING, LETTER)
        self.love_letter.draw(surface)
        
        self.update()


# ============================================================================
# HELPER FUNCTION - GLOW TEXT EFFECT
# ============================================================================

def draw_glowing_text(surface, text, font, color, pos, glow_color=(255, 200, 100), glow_size=3):
    """Draw text with glowing halo effect"""
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=pos)
    
    # Draw glow layers (outer to inner)
    for glow_layer in range(glow_size, 0, -1):
        alpha = int(50 * (1 - glow_layer / glow_size))  # Fade out
        glow_surf = font.render(text, True, glow_color)
        glow_surf.set_alpha(alpha)
        glow_rect = glow_surf.get_rect(center=(pos[0], pos[1]))
        
        # Draw glow in multiple directions
        for offset in range(0, 360, 45):
            rad = math.radians(offset)
            ox = int(math.cos(rad) * glow_layer)
            oy = int(math.sin(rad) * glow_layer)
            surface.blit(glow_surf, (glow_rect.x + ox, glow_rect.y + oy))
    
    # Draw main text
    surface.blit(text_surf, text_rect)


def draw_twinkling_text(surface, text, font, color, pos, time_offset=0, twinkle_speed=0.1):
    """Draw text with twinkling/shimmer effect"""
    current_time = time.time() * twinkle_speed + time_offset
    shimmer = (math.sin(current_time * 3) + 1) / 2  # 0 to 1
    
    # Create shimmer color
    shimmer_color = tuple(int(c + (255 - c) * shimmer * 0.5) for c in color)
    
    text_surf = font.render(text, True, shimmer_color)
    text_rect = text_surf.get_rect(center=pos)
    
    # Add slight alpha variation
    alpha = int(200 + shimmer * 55)
    text_surf.set_alpha(alpha)
    surface.blit(text_surf, text_rect)
    text_surf.set_alpha(255)


# ============================================================================
# MAIN
# ============================================================================

def main():
    pygame.init()
    
    WIDTH, HEIGHT = 1200, 850
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("✨ Interactive Christmas Hologram ✨")
    clock = pygame.time.Clock()
    
    # Create interactive hologram
    hologram = InteractiveHologram(WIDTH, HEIGHT)
    
    # Start hand tracking
    print("Starting hand tracking...")
    hand_tracker = HandTrackingThread(camera_id=1)
    hand_tracker.start()
    
    # Fonts
    try:
        font = pygame.font.SysFont(DEBUG_FONT_NAME, DEBUG_FONT_SIZE)
        title_font = pygame.font.Font(TITLE_FONT_PATH, TITLE_FONT_SIZE)
        subtitle_font = pygame.font.Font(SUBTITLE_FONT_PATH, SUBTITLE_FONT_SIZE)
    except:
        font = pygame.font.Font(None, DEBUG_FONT_SIZE)
        title_font = pygame.font.Font(None, TITLE_FONT_SIZE)
        subtitle_font = pygame.font.Font(None, SUBTITLE_FONT_SIZE)
    
    zoom = 1.0
    running = True
    show_debug = False
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if hologram.interaction_mode == "zoom_photo":
                        hologram.interaction_mode = "photos"
                        hologram.photo_zoom_progress = 0
                        hologram.selected_photo_index = -1
                    else:
                        running = False
                elif event.key == pygame.K_d:
                    show_debug = not show_debug
                elif event.key == pygame.K_UP:
                    zoom = min(2.0, zoom + 0.1)
                elif event.key == pygame.K_DOWN:
                    zoom = max(0.5, zoom - 0.1)
                elif event.key == pygame.K_LEFT:
                    hologram.photo_orbit_angle -= 0.3
                elif event.key == pygame.K_RIGHT:
                    hologram.photo_orbit_angle += 0.3
                elif event.key == pygame.K_SPACE:
                    # Manual toggle explosion
                    hologram.target_explosion = 1.0 if hologram.target_explosion < 0.5 else 0.0
                    hologram.photos_visible = hologram.target_explosion > 0.5
                    hologram.interaction_mode = "photos" if hologram.target_explosion > 0.5 else "tree"
                elif event.key == pygame.K_RETURN:
                    # Manual zoom photo
                    if hologram.interaction_mode == "photos":
                        hologram._select_closest_photo()
                        if hologram.selected_photo_index >= 0:
                            hologram.interaction_mode = "zoom_photo"
                            hologram.photo_zoom_progress = 1.0
        
        # Get hand tracking data
        hand_dist, index_x, prev_x, index_y, prev_y, finger_count, hand_span, prev_hand_span = hand_tracker.get_data()
        
        # ========================================================================
        # DETECT HEART SHAPE GESTURE (LOVE LETTER EASTER EGG)
        # ========================================================================
        if hologram.heart_detected_cooldown <= 0 and hologram.interaction_mode == "tree":
            # Heart gesture detected inside HandTrackingThread
            if hand_tracker.heart_gesture:
                print("💕 BẮN TIM THÀNH CÔNG! ĐỦ ĐIỀU KIỆN MỞ THƯ TÌNH! 💕")
                # Trigger HEART MODE - particles bung ra, thư di chuyển từ cây
                hologram.heart_mode = True  # Bật chế độ trái tim (TẮT ảnh!)
                hologram.target_explosion = 1.0
                hologram.explosion_start_time = hologram.time
                hologram.photos_visible = False  # TẮT ảnh hoàn toàn
                hologram.interaction_mode = "heart_photos"  # Mode mới cho heart
                hologram.love_letter.trigger()
                hologram.love_letter_zoom_progress = 0.0
                hologram.heart_detected_cooldown = 300  # 5 giây cooldown
        
        if hologram.heart_detected_cooldown > 0:
            hologram.heart_detected_cooldown -= 1
        
        hologram.update_hand_tracking(hand_dist, index_x, prev_x, index_y, prev_y, finger_count, hand_span, prev_hand_span, hand_tracker.fingers_up)
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw hologram
        hologram.draw(screen, zoom)
        
        # Text (show only in tree mode, hide in universe & zoom screens)
        if hologram.interaction_mode == "tree":
            # Glow effect for title
            draw_glowing_text(
                screen, TITLE_TEXT, title_font, TITLE_MAIN_COLOR,
                (WIDTH // 2, HEIGHT - 80),
                glow_color=(255, 200, 100), glow_size=4
            )
            
            # Add twinkling effect
            draw_twinkling_text(
                screen, TITLE_TEXT, title_font, TITLE_MAIN_COLOR,
                (WIDTH // 2, HEIGHT - 80),
                time_offset=0, twinkle_speed=0.15
            )
            
            # Subtitle (if any)
            if SUBTITLE_TEXT:
                draw_glowing_text(
                    screen, SUBTITLE_TEXT, subtitle_font, SUBTITLE_COLOR,
                    (WIDTH // 2, HEIGHT - 40),
                    glow_color=(255, 180, 100), glow_size=3
                )
        
        # Debug
        if show_debug:
            debug_texts = [
                f"FPS: {int(clock.get_fps())}",
                f"Hand Distance: {int(hand_dist)}",
                f"Explosion: {hologram.explosion_progress:.2f}",
                f"Mode: {hologram.interaction_mode}",
                f"Selected Photo: {hologram.selected_photo_index}",
            ]
            for i, txt in enumerate(debug_texts):
                surf = font.render(txt, True, WHITE)
                screen.blit(surf, (10, 10 + i * 20))
        
        pygame.display.flip()
        clock.tick(60)
    
    hand_tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
