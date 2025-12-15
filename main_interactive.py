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
    DEBUG_FONT_SIZE, DEBUG_FONT_NAME
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
        
    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        detector = HandDetector(detection_con=0.7, track_con=0.5)
        
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
            
            if detector.results and detector.results.multi_hand_landmarks:  # type: ignore
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
                
                for tip_id, knuckle_id in zip(tips, knuckles):
                    tip_y = hand_lms.landmark[tip_id].y
                    knuckle_y = hand_lms.landmark[knuckle_id].y
                    if tip_y < knuckle_y:  # Tip higher than knuckle = finger up
                        finger_count += 1
                
                # Tính hand span (khoảng cách từ ngón cái đến ngón út)
                thumb = hand_lms.landmark[4]
                pinky = hand_lms.landmark[20]
                hand_span = math.hypot((pinky.x - thumb.x) * w, (pinky.y - thumb.y) * h)
            else:
                hand_span = 0
            
            try:
                self.data_queue.put_nowait((dist, index_x, index_y, finger_count, hand_span))
            except queue.Full:
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait((dist, index_x, index_y, finger_count, hand_span))
                except:
                    pass
        
        cap.release()
    
    def get_data(self):
        try:
            self.current_distance, new_x, new_y, self.finger_count, new_span = self.data_queue.get_nowait()
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
        
        # Interaction mode: "tree", "photos", "zoom_photo"
        self.interaction_mode = "tree"
        
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
    
    def update_hand_tracking(self, distance: float, index_x: int, prev_x: int, index_y: int, prev_y: int, finger_count: int, hand_span: float = 0, prev_hand_span: float = 0):
        """
        Update based on hand tracking data
        
        Logic:
        - TREE: Chỉ nhận zoom_in (bung ngón) -> chuyển sang PHOTOS
        - PHOTOS: zoom_in (bung rộng) -> zoom ảnh (5 ngón), zoom_out (chụm) -> về TREE
        - ZOOM_PHOTO: Dùng hand_span để điều khiển độ zoom, chụm ngón -> thoát
        """
        
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
            
            # 2 NGÓN CHỤM (hand_span <= 80) -> CẦN GIỮ 2 GIÂY ĐỂ COLLAPSE VỀ TREE
            if hand_span <= 80 and hand_span > 0:
                # Bắt đầu đếm hoặc tiếp tục đếm
                if self.zoom_out_hold_start == 0:
                    self.zoom_out_hold_start = self.time
                    print(f"[GESTURE] Starting pinch hold to collapse (hand_span={hand_span:.0f})...")
                
                # Check nếu đã giữ đủ 2 giây
                hold_time = self.time - self.zoom_out_hold_start
                if hold_time >= 90:  # 1.5 giây @ 60fps
                    self.target_explosion = 0.0
                    self.photos_visible = False
                    self.interaction_mode = "collapsing"
                    self.last_gesture_time = self.time
                    self.zoom_out_hold_start = 0  # Reset
                    print(f"[GESTURE] PHOTOS -> COLLAPSING (pinch held {hold_time/60:.1f}s)")
            else:
                # Không còn chụm -> reset timer
                if self.zoom_out_hold_start > 0:
                    print(f"[GESTURE] Pinch hold cancelled (hand_span={hand_span:.0f})")
                self.zoom_out_hold_start = 0
            
            # XÒE 5 NGÓN (hand_span lớn) -> zoom ảnh NGAY LẬP TỨC
            if hand_span > 120:  # Đơn giản: chỉ check hand_span
                self._select_closest_photo()
                if self.selected_photo_index >= 0:
                    self.interaction_mode = "zoom_photo"
                    self.photo_zoom_progress = 0.0  # Bắt đầu từ 0%, zoom + extraction cùng lúc
                    self.photo_extraction_start_time = self.time
                    self.photo_extraction_progress = 0.0  # Start extraction animation
                    self.last_gesture_time = self.time
                    print(f"[GESTURE] PHOTOS -> ZOOM_PHOTO (hand_span={hand_span:.0f})")
        
        # === MODE: COLLAPSING (đang thu về cây) ===
        elif self.interaction_mode == "collapsing":
            # Chờ animation xong mới chuyển về tree
            if self.explosion_progress == 0:
                self.interaction_mode = "tree"
                print(f"[GESTURE] COLLAPSING -> TREE (animation done)")
        
        # === MODE: ZOOM_PHOTO (đang xem ảnh phóng to) ===
        elif self.interaction_mode == "zoom_photo":
            # Dùng hand_span TUYỆT ĐỐI để điều khiển zoom
            # Ngưỡng: 
            # - hand_span < 80: nắm tay -> thoát zoom
            # - hand_span 80-250: zoom từ 0 đến 1
            # - hand_span > 250: full zoom
            
            if hand_span > 80:
                # Tay đang xoè -> map hand_span sang zoom progress
                target_zoom = (hand_span - 60) / 140.0
                target_zoom = max(0.1, min(1.0, target_zoom))
                self.photo_zoom_progress += (target_zoom - self.photo_zoom_progress) * 0.2
            else:
                # hand_span <= 80 hoặc = 0: Nắm tay / không detect -> THOÁT ZOOM
                self.photo_zoom_progress = 0
                self.selected_photo_index = -1
                self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                print(f"[GESTURE] ZOOM_PHOTO -> PHOTOS (closed/no hand, span={hand_span:.0f})")
        
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
            # Expanding (zoom in): ease-out (nhanh đầu, chậm cuối)
            easing = 0.025 + abs(diff) * 0.03
        else:
            # Collapsing (zoom out): NHANH HƠN để về tree mode sớm
            easing = 0.08 + abs(diff) * 0.05
        
        self.explosion_progress += diff * easing
        
        # Snap to 0 khi đã gần để chuyển về tree.draw() gốc
        if self.explosion_progress < 0.05 and self.target_explosion == 0:
            self.explosion_progress = 0
        
        self.explosion_progress = max(0, min(1, self.explosion_progress))
        
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
        
        # Draw photos nếu còn hiển thị
        if self.explosion_progress > 0.1:
            self._draw_photos(surface, zoom)
        
        # CÂY TIẾP TỤC XOAY - particles sẽ động theo rotation
        self.tree.update()
        
        # Draw zoomed photo on top
        if self.interaction_mode == "zoom_photo":
            self._draw_zoomed_photo(surface)
        
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
        hologram.update_hand_tracking(hand_dist, index_x, prev_x, index_y, prev_y, finger_count, hand_span, prev_hand_span)
        
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
        
        # Hints based on mode
        if hologram.interaction_mode == "tree":
            hint = "Bung 2 ngón để mở vũ trụ | SPACE: Toggle | D: Debug | ESC: Exit"
        elif hologram.interaction_mode == "photos":
            hint = "Lướt ngón trỏ để xoay ảnh | Bung ngón để zoom ảnh | ←→: Xoay | ENTER: Zoom"
        else:
            hint = "Khép 2 ngón để thu nhỏ | ESC: Đóng ảnh"
        
        hint_surf = font.render(hint, True, (80, 80, 80))
        screen.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT - 25))
        
        pygame.display.flip()
        clock.tick(60)
    
    hand_tracker.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
