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

# Import tree từ scenes
from scenes.tree_3d import HologramTree, BLACK, WHITE, TREE_COLORS

# Import hand tracking
from core.core_hand_tracking import HandDetector

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
    # Tree position
    start_x: float
    start_y: float
    start_z: float
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
            
            try:
                self.data_queue.put_nowait((dist, index_x, index_y, finger_count))
            except queue.Full:
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait((dist, index_x, index_y, finger_count))
                except:
                    pass
        
        cap.release()
    
    def get_data(self):
        try:
            self.current_distance, new_x, new_y, self.finger_count = self.data_queue.get_nowait()
            self.prev_x = self.current_x
            self.prev_y = self.current_y
            self.current_x = new_x
            self.current_y = new_y
        except queue.Empty:
            pass
        return self.current_distance, self.current_x, self.prev_x, self.current_y, self.prev_y, self.finger_count
    
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
        self.explosion_speed = 0.02  # Chậm hơn để mượt (từ 0.035)
        
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
        self._load_photos()
        
        # Hand tracking state - ĐƠN GIẢN HÓA
        self.zoom_in_threshold = 120    # Bung ngón để zoom in (distance > 80)
        self.zoom_out_threshold = 50   # Chụm ngón để zoom out (distance < 50)
        
        # Gesture debounce
        self.last_gesture_time = 0
        self.gesture_cooldown = 45  # 0.75 giây @ 60fps
        
        # Track previous distance
        self.prev_distance = 0
        
        # Interaction mode: "tree", "photos", "zoom_photo"
        self.interaction_mode = "tree"
        
        # Time for animation
        self.time = 0
    
    def _create_cosmic_particles(self):
        """Create particles distributed on a cosmic sphere"""
        self.cosmic_particles = []
        
        # From tree particles - distribute on sphere
        for p in self.tree.tree_particles[::2]:
            # Random position on sphere (uniform distribution)
            theta = random.uniform(0, math.pi)  # 0 to π
            phi = random.uniform(0, 2 * math.pi)  # 0 to 2π
            radius = random.uniform(400, 800)  # Large cosmic sphere
            
            self.cosmic_particles.append(CosmicParticle(
                start_x=p.base_x, start_y=p.y, start_z=p.base_z,
                sphere_theta=theta,
                sphere_phi=phi,
                sphere_radius=radius,
                color=p.color,
                size=p.size,
                twinkle_phase=p.twinkle_phase,
                orbit_speed=random.uniform(0.001, 0.004)  # Individual orbit speeds
            ))
        
        # From heart particles
        for p in self.tree.heart_particles[::3]:
            theta = random.uniform(0, math.pi)
            phi = random.uniform(0, 2 * math.pi)
            radius = random.uniform(450, 850)
            
            self.cosmic_particles.append(CosmicParticle(
                start_x=p.base_x, start_y=p.y, start_z=p.base_z,
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
    
    def update_hand_tracking(self, distance: float, index_x: int, prev_x: int, index_y: int, prev_y: int, finger_count: int):
        """
        Update based on hand tracking data
        
        Logic đơn giản:
        - TREE: Chỉ nhận zoom_in (bung ngón) -> chuyển sang PHOTOS
        - PHOTOS: zoom_in (bung rộng) -> zoom ảnh, zoom_out (chụm) -> về TREE
        - ZOOM_PHOTO: Chỉ nhận zoom_out (chụm) -> thoát zoom
        """
        
        # Check cooldown
        can_gesture = (self.time - self.last_gesture_time) > self.gesture_cooldown
        
        if not can_gesture or distance <= 0:
            return
        
        # === MODE: TREE ===
        if self.interaction_mode == "tree":
            # Chỉ nhận diện ZOOM IN (bung ngón) để mở vũ trụ
            if distance > self.zoom_in_threshold:
                self.target_explosion = 1.0
                self.photos_visible = True
                self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                print(f"[GESTURE] TREE -> PHOTOS (distance={distance:.0f})")
        
        # === MODE: PHOTOS (vũ trụ với ảnh xoay) ===
        elif self.interaction_mode == "photos":
            # ZOOM OUT (chụm ngón) -> bắt đầu thu về cây (chưa chuyển mode ngay)
            if distance < self.zoom_out_threshold:
                self.target_explosion = 0.0
                self.photos_visible = False
                self.interaction_mode = "collapsing"  # Mode trung gian để chờ animation
                self.last_gesture_time = self.time
                print(f"[GESTURE] PHOTOS -> COLLAPSING (distance={distance:.0f})")
            
            # ZOOM IN (bung rộng hơn) -> zoom ảnh
            elif distance > self.zoom_in_threshold + 40:  # Cần bung rộng hơn (>120)
                self._select_closest_photo()
                if self.selected_photo_index >= 0:
                    self.interaction_mode = "zoom_photo"
                    self.photo_zoom_progress = 0.1
                    self.last_gesture_time = self.time
                    print(f"[GESTURE] PHOTOS -> ZOOM_PHOTO (distance={distance:.0f})")
        
        # === MODE: COLLAPSING (đang thu về cây) ===
        elif self.interaction_mode == "collapsing":
            # Chờ animation xong mới chuyển về tree
            if self.explosion_progress < 0.05:
                self.interaction_mode = "tree"
                print(f"[GESTURE] COLLAPSING -> TREE (animation done)")
        
        # === MODE: ZOOM_PHOTO (đang xem ảnh phóng to) ===
        elif self.interaction_mode == "zoom_photo":
            # Chỉ nhận diện ZOOM OUT (chụm ngón) để thoát
            if distance < self.zoom_out_threshold:
                self.photo_zoom_progress = 0
                self.selected_photo_index = -1
                self.interaction_mode = "photos"
                self.last_gesture_time = self.time
                print(f"[GESTURE] ZOOM_PHOTO -> PHOTOS (distance={distance:.0f})")
            else:
                # Tiếp tục zoom in
                self.photo_zoom_progress = min(1.0, self.photo_zoom_progress + 0.03)
        
        self.prev_distance = distance
    
    def _select_closest_photo(self):
        """Select photo closest to center front (highest Z)"""
        if not self.photos or len(self.photos) == 0:
            self.selected_photo_index = -1
            return
        
        best_idx = -1
        best_z = -float('inf')
        
        # Ellipse parameters (must match _draw_photos)
        ellipse_a = 550
        ellipse_b = 350
        tilt_angle = math.radians(-25)
        
        for i, photo in enumerate(self.photos):
            # Calculate ellipse orbit position
            time_offset = (i / len(self.photos)) * 2 * math.pi
            angle = self.photo_orbit_angle + time_offset
            
            # Base ellipse coordinates
            x_base = ellipse_a * math.cos(angle)
            z_base = ellipse_b * math.sin(angle)
            y_base = 0
            
            # Apply tilt
            z = y_base * math.sin(tilt_angle) + z_base * math.cos(tilt_angle)
            
            # Front-most photo (highest z)
            if z > best_z:
                best_z = z
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
        """Draw particles in cosmic sphere state"""
        exp = self.explosion_progress
        
        render_list = []
        
        for p in self.cosmic_particles:
            # Get sphere target position
            sphere_x, sphere_y, sphere_z = self._get_sphere_position(p)
            
            # Interpolate between tree position and sphere position
            curr_x = p.start_x * (1 - exp) + sphere_x * exp
            curr_y = p.start_y * (1 - exp) + sphere_y * exp
            curr_z = p.start_z * (1 - exp) + sphere_z * exp
            
            render_list.append((p, curr_x, curr_y, curr_z))
        
        # Sort by Z (far to near)
        render_list.sort(key=lambda item: item[3], reverse=True)
        
        for p, curr_x, curr_y, curr_z in render_list:
            pos = self.tree.project_3d(curr_x, curr_y, curr_z, zoom)
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                twinkle = 0.5 + 0.5 * math.sin(self.time * 0.04 + p.twinkle_phase)
                size = p.size * pos[2] * zoom * 1.2
                
                # Glow effect
                if size > 1:
                    glow_color = (
                        min(255, int(p.color[0] * twinkle * 0.4)),
                        min(255, int(p.color[1] * twinkle * 0.4)),
                        min(255, int(p.color[2] * twinkle * 0.4))
                    )
                    pygame.draw.circle(surface, glow_color, (pos[0], pos[1]), int(size * 2.5))
                
                core_color = (
                    min(255, int(p.color[0] * twinkle)),
                    min(255, int(p.color[1] * twinkle)),
                    min(255, int(p.color[2] * twinkle))
                )
                pygame.draw.circle(surface, core_color, (pos[0], pos[1]), max(1, int(size)))
    
    def _draw_photos(self, surface: pygame.Surface, zoom: float):
        """Draw orbiting photos in tilted 3D ellipse orbit"""
        
        # Collect all photos with their positions for z-sorting
        render_list = []
        
        for i, photo in enumerate(self.photos):
            if photo.fade_alpha < 5:
                continue
            
            # Elliptical orbit - photos distributed along ellipse
            # Each photo offset on the ellipse
            time_offset = (i / len(self.photos)) * 2 * math.pi
            angle = self.photo_orbit_angle + time_offset
            
            # Ellipse parameters (wider than tall)
            ellipse_a = 550  # Semi-major axis (horizontal)
            ellipse_b = 350  # Semi-minor axis (depth)
            tilt_angle = math.radians(-25)  # Tilt down 25 degrees
            
            # Base ellipse coordinates (in XZ plane)
            x_base = ellipse_a * math.cos(angle)
            z_base = ellipse_b * math.sin(angle)
            y_base = 0
            
            # Apply tilt transformation (rotate around X axis)
            x = x_base
            y = y_base * math.cos(tilt_angle) - z_base * math.sin(tilt_angle)
            z = y_base * math.sin(tilt_angle) + z_base * math.cos(tilt_angle)
            
            pos = self.tree.project_3d(x, y, z, zoom)
            if pos:
                render_list.append((i, photo, x, y, z, pos, angle))
        
        # Sort by Z (draw far photos first, near photos last - painter's algorithm)
        render_list.sort(key=lambda item: item[4])  # Sort by z coordinate
        
        for i, photo, x, y, z, pos, angle in render_list:
            # Perspective scaling - photos further back (negative z) are smaller
            # Z ranges from -ellipse_b to +ellipse_b
            ellipse_b = 350
            depth_factor = 0.6 + 0.4 * ((z + ellipse_b) / (2 * ellipse_b))  # 0.6 to 1.0
            scaled_w = int(photo.image.get_width() * depth_factor * zoom * 1.2)
            scaled_h = int(photo.image.get_height() * depth_factor * zoom * 1.2)
            
            if scaled_w > 20 and scaled_h > 20:
                scaled_img = pygame.transform.scale(photo.image, (scaled_w, scaled_h))
                
                if photo.fade_alpha < 255:
                    scaled_img.set_alpha(int(photo.fade_alpha))
                
                # No frame - just draw the photo
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
        
        # Smooth explosion transition - giống nhau cho cả expand và collapse
        diff = self.target_explosion - self.explosion_progress
        # Easing mượt mà: ease-out (nhanh đầu, chậm cuối)
        easing = 0.02 + abs(diff) * 0.025
        self.explosion_progress += diff * easing
        self.explosion_progress = max(0, min(1, self.explosion_progress))
        
        # Sphere rotation
        self.sphere_rotation += self.sphere_rotation_speed
        
        # Auto-rotate photos around ellipse orbit when visible
        if self.photos_visible:
            self.photo_orbit_angle += self.photo_orbit_speed * 2  # Smooth rotation
        
        # Update photo visibility
        for i, photo in enumerate(self.photos):
            if self.photos_visible:
                # Fade in tuần tự từng ảnh (stagger effect)
                delay = i * 3  # Mỗi ảnh delay 3 frame
                if self.time > delay:
                    photo.fade_alpha = min(255, photo.fade_alpha + 4)
            else:
                # Fade out cũng mượt như fade in
                photo.fade_alpha = max(0, photo.fade_alpha - 4)
    
    def draw(self, surface: pygame.Surface, zoom: float = 1.0):
        """Main draw method"""
        if self.explosion_progress < 0.05 and self.interaction_mode == "tree":
            # Draw normal tree
            self.tree.draw(surface, zoom)
        else:
            # Draw cosmic particles (kể cả khi đang collapsing)
            self._draw_cosmic_particles(surface, zoom)
            
            # Draw photos nếu còn hiển thị
            if self.explosion_progress > 0.1:
                self._draw_photos(surface, zoom)
            
            self.tree.update()
        
        # Draw zoomed photo on top
        if self.interaction_mode == "zoom_photo":
            self._draw_zoomed_photo(surface)
        
        self.update()


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
        font = pygame.font.SysFont("Arial", 18)
        title_font = pygame.font.SysFont("Arial", 36, bold=True)
    except:
        font = pygame.font.Font(None, 18)
        title_font = pygame.font.Font(None, 36)
    
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
        hand_dist, index_x, prev_x, index_y, prev_y, finger_count = hand_tracker.get_data()
        hologram.update_hand_tracking(hand_dist, index_x, prev_x, index_y, prev_y, finger_count)
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw hologram
        hologram.draw(screen, zoom)
        
        # Text (hide when photo zoomed)
        if hologram.interaction_mode != "zoom_photo":
            text = title_font.render('Noel vui vẻ "Cô giáo"', True, (255, 200, 100))
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT - 80))
            screen.blit(text, text_rect)
        
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
