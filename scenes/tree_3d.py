"""
Christmas Tree 3D Particle System
==================================
A magical particle-based Christmas tree with:
- Multiple stacked conical layers of glowing particles
- Soft, fluffy pine needle edges with noise
- 3D volumetric heart topper emitting pink-white light
- Deep space background with floating snow/stars
- Curved dome ground with concentric energy rings

Style: Abstract, generative art, particle system, cinematic lighting,
soft glow, high contrast, ethereal and magical Christmas atmosphere.
"""

import pygame
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional

# ============================================================================
# COLORS & CONSTANTS
# ============================================================================

# Deep space black
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Tree particle colors (light pink with rare golden yellow accents)
TREE_COLORS = [
    (255, 200, 220),   # Soft pink
    (255, 210, 225),   # Light pink
    (255, 220, 230),   # Lighter pink
    (255, 230, 240),   # Very light pink
    (255, 235, 245),   # Pale pink
    (255, 240, 248),   # Nearly white pink
    (240, 220, 235),   # Muted light pink
    (255, 215, 235),   # Soft blush pink
    (255, 225, 242),   # Gentle pink
    (248, 210, 230),   # Dusty pink
    (255, 245, 250),   # Almost white pink
    (255, 220, 100),   # Golden yellow (rare accent)
    (255, 230, 120),   # Bright golden yellow (rare accent)
]

# Heart colors (intense pink-white glow - darker/more saturated)
HEART_COLORS = [
    (255, 60, 110),    # Hot pink core (darker)
    (255, 100, 140),   # Bright pink (darker)
    (255, 140, 170),   # Soft pink (darker)
    (255, 180, 210),   # Light pink (darker)
    (255, 220, 235),   # Near white pink
    (255, 255, 255),   # Pure white center
]

# Energy ring colors for ground
RING_COLORS = [
    (80, 180, 255),    # Cyan blue
    (140, 100, 255),   # Purple
    (255, 100, 180),   # Magenta
    (100, 255, 200),   # Teal
    (200, 150, 255),   # Lavender
]

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class TreeParticle:
    """A single glowing particle that forms the tree structure"""
    x: float
    y: float
    z: float
    base_x: float  # Original x for rotation
    base_z: float  # Original z for rotation
    color: Tuple[int, int, int]
    size: float
    twinkle_speed: float
    twinkle_phase: float
    layer: int


@dataclass
class HeartParticle:
    """A particle that forms the 3D volumetric heart"""
    x: float
    y: float
    z: float
    base_x: float
    base_z: float
    color: Tuple[int, int, int]
    size: float
    brightness: float
    pulse_speed: float
    pulse_phase: float


@dataclass
class SnowParticle:
    """Floating snow/star particle in the background"""
    x: float
    y: float
    z: float
    size: float
    fall_speed: float
    drift_speed: float
    brightness: float
    twinkle_phase: float


@dataclass
class GroundRing:
    """Concentric energy ring on the curved ground"""
    base_radius: float
    color: Tuple[int, int, int]
    phase: float
    pulse_speed: float
    thickness: float


# ============================================================================
# MAIN HOLOGRAM TREE CLASS
# ============================================================================

class HologramTree:
    """
    Magical 3D Christmas Tree Hologram
    
    Creates an ethereal particle-based Christmas tree with:
    - Layered conical structure with fluffy, noisy edges
    - 3D volumetric glowing heart at the top
    - Floating snow/star particles in deep space background
    - Curved dome ground with spreading energy rings
    """
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        
        # Animation state
        self.time = 0
        self.rotation = 0.0
        self.rotation_speed = 0.012
        
        # Tree geometry parameters (BIGGER TREE)
        self.tree_height = 550  # Increased from 480
        self.tree_base_radius = 220
        self.num_layers = 16  # Fewer layers for clearer separation
        self.particles_per_layer = 70
        
        # Particle collections
        self.tree_particles: List[TreeParticle] = []
        self.heart_particles: List[HeartParticle] = []
        self.snow_particles: List[SnowParticle] = []
        self.ground_rings: List[GroundRing] = []
        
        # Generate all elements
        self._generate_tree()
        self._generate_heart()
        self._generate_snow()
        self._generate_ground()
    
    # ------------------------------------------------------------------------
    # GENERATION METHODS
    # ------------------------------------------------------------------------
    
    def _generate_tree(self):
        """Generate conical tree layers with soft, fluffy edges like pine needles"""
        self.tree_particles = []
        
        # Layer spacing for clear separation (gap between layers)
        layer_gap = self.tree_height / self.num_layers
        layer_thickness = layer_gap * 0.6  # 60% filled, 40% gap
        
        # Create multiple conical layers from bottom to top
        for layer_idx in range(self.num_layers):
            layer_ratio = layer_idx / self.num_layers
            
            # Y position: bottom to top (with clear gaps)
            layer_y = -self.tree_height / 2 + layer_idx * layer_gap
            
            # Radius decreases as we go up (cone shape)
            layer_radius = self.tree_base_radius * (1 - layer_ratio * 0.92)
            
            # More particles at bottom, fewer at top
            num_particles = int(self.particles_per_layer * (1 - layer_ratio * 0.4))
            
            for i in range(num_particles):
                # Base angle around the circle
                base_angle = (i / num_particles) * 2 * math.pi
                
                # Add Gaussian noise for fluffy pine needle effect
                radius_noise = random.gauss(0, layer_radius * 0.15)
                angle_noise = random.gauss(0, 0.1)
                # Y noise confined within layer thickness (creates gaps)
                y_noise = random.uniform(-layer_thickness/2, layer_thickness/2)
                
                r = max(0, layer_radius + radius_noise)
                angle = base_angle + angle_noise
                
                x = r * math.cos(angle)
                z = r * math.sin(angle)
                y = layer_y + y_noise
                
                # Choose color with slight randomization
                color = random.choice(TREE_COLORS)
                
                # Vary size for depth and visual interest
                size = random.uniform(1.5, 3.5)
                
                self.tree_particles.append(TreeParticle(
                    x=x, y=y, z=z,
                    base_x=x, base_z=z,
                    color=color,
                    size=size,
                    twinkle_speed=random.uniform(0.03, 0.1),
                    twinkle_phase=random.uniform(0, 2 * math.pi),
                    layer=layer_idx
                ))
        
        # Add internal glow particles (inside the cone, respecting layer gaps)
        for _ in range(300):
            # Pick a random layer to place internal particle
            layer_idx = random.randint(0, self.num_layers - 1)
            layer_ratio = layer_idx / self.num_layers
            layer_y_base = -self.tree_height / 2 + layer_idx * layer_gap
            
            # Stay within layer thickness
            y = layer_y_base + random.uniform(-layer_thickness/2, layer_thickness/2)
            max_r = self.tree_base_radius * (1 - layer_ratio * 0.92) * 0.5
            
            r = random.uniform(0, max_r)
            angle = random.uniform(0, 2 * math.pi)
            
            x = r * math.cos(angle)
            z = r * math.sin(angle)
            
            self.tree_particles.append(TreeParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=random.choice(TREE_COLORS),
                size=random.uniform(1, 2.5),
                twinkle_speed=random.uniform(0.04, 0.12),
                twinkle_phase=random.uniform(0, 2 * math.pi),
                layer=-1  # Internal particle
            ))
    
    def _generate_heart(self):
        """
        Generate a TRUE 3D heart shape with recognizable silhouette.
        
        Strategy: Create heart shape in XY plane, then extrude into Z depth.
        This preserves the heart shape when viewed from front/back.
        """
        self.heart_particles = []
        
        heart_center_y = self.tree_height / 2 + 60
        scale = 2.8  # Larger size
        depth_scale = 2.4  # Z-depth relative to XY - MUCH THICKER for fuller appearance
        
        # =====================================================================
        # HEART CURVE DEFINITION (2D)
        # Using: x = 16*sin³(t), y = 13*cos(t) - 5*cos(2t) - 2*cos(3t) - cos(4t)
        # =====================================================================
        
        def heart_2d(t):
            """Returns (x, y) for heart curve at parameter t"""
            sin_t = math.sin(t)
            cos_t = math.cos(t)
            x = 16 * (sin_t ** 3)
            y = 13 * cos_t - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)
            return x, y
        
        # =====================================================================
        # 1. FRONT SURFACE - Dense heart outline at Z=0 (front face)
        # =====================================================================
        
        for i in range(200):
            t = (i / 200) * 2 * math.pi
            hx, hy = heart_2d(t)
            
            # Multiple layers at this outline point
            for _ in range(3):
                noise_x = random.gauss(0, 0.3)
                noise_y = random.gauss(0, 0.3)
                
                x = (hx + noise_x) * scale
                y = (hy + noise_y) * scale + heart_center_y
                z = random.uniform(-2, 2)
                
                color = random.choice(HEART_COLORS[:4])  # Brighter pinks
                size = random.uniform(1.8, 3.0)
                
                self.heart_particles.append(HeartParticle(
                    x=x, y=y, z=z,
                    base_x=x, base_z=z,
                    color=color,
                    size=size,
                    brightness=1.0,
                    pulse_speed=random.uniform(0.06, 0.13),
                    pulse_phase=random.uniform(0, 2 * math.pi)
                ))
        
        # =====================================================================
        # 2. FILLED HEART SURFACE - Interior with depth
        # =====================================================================
        
        # Sample many points inside the heart outline
        for _ in range(2800):  # INCREASED from 2200 for fuller interior
            t = random.uniform(0, 2 * math.pi)
            hx, hy = heart_2d(t)
            
            # Random point inside (scale down from outline)
            fill_factor = random.uniform(0.15, 0.98)  # INCREASED range
            x = hx * fill_factor * scale
            y = hy * fill_factor * scale + heart_center_y
            
            # Z depth: thicker in middle, thinner at edges - INCREASED MORE
            max_z = depth_scale * scale * math.sqrt(fill_factor) * 1.5
            z = random.uniform(-max_z, max_z)
            
            color = random.choice(HEART_COLORS)
            size = random.uniform(1.3, 2.5)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=color,
                size=size,
                brightness=random.uniform(0.75, 1.0),
                pulse_speed=random.uniform(0.05, 0.12),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
        
        # =====================================================================
        # 3. BACK SURFACE - Create depth with back face
        # =====================================================================
        
        for i in range(280):  # INCREASED from 200
            t = (i / 280) * 2 * math.pi
            hx, hy = heart_2d(t)
            
            x = hx * scale
            y = hy * scale + heart_center_y
            z_back = -depth_scale * scale * 1.0 + random.uniform(-3, 3)  # THICKER back
            
            color = random.choice(HEART_COLORS[2:])  # Darker for back
            size = random.uniform(1.5, 2.5)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z_back,
                base_x=x, base_z=z_back,
                color=color,
                size=size,
                brightness=random.uniform(0.6, 0.9),
                pulse_speed=random.uniform(0.05, 0.11),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
        
        # =====================================================================
        # 4. EMPHASIZED FEATURES - V-indent, lobes, and tip
        # =====================================================================
        
        # Top V-indent (t near π)
        for _ in range(700):  # INCREASED from 550
            t = math.pi + random.gauss(0, 0.12)
            hx, hy = heart_2d(t)
            
            depth = random.uniform(0.6, 1.1)
            x = hx * depth * scale
            y = hy * depth * scale + heart_center_y
            max_z = depth_scale * scale * 1.1  # INCREASED from 0.9
            z = random.uniform(-max_z, max_z)
            
            color = random.choice([WHITE, HEART_COLORS[0], HEART_COLORS[-1]])
            size = random.uniform(2.0, 3.5)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=color,
                size=size,
                brightness=1.0,
                pulse_speed=random.uniform(0.07, 0.14),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
        
        # Two lobes (t near π/2 and 3π/2)
        for _ in range(1000):  # INCREASED from 800
            if random.random() < 0.5:
                t = math.pi/2 + random.gauss(0, 0.2)
            else:
                t = 3*math.pi/2 + random.gauss(0, 0.2)
            
            hx, hy = heart_2d(t)
            
            depth = random.uniform(0.5, 1.05)
            x = hx * depth * scale
            y = hy * depth * scale + heart_center_y
            max_z = depth_scale * scale * 1.2  # INCREASED from 1.0
            z = random.uniform(-max_z, max_z)
            
            color = random.choice(HEART_COLORS[:4])
            size = random.uniform(1.8, 3.0)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=color,
                size=size,
                brightness=random.uniform(0.9, 1.0),
                pulse_speed=random.uniform(0.06, 0.13),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
        
        # Bottom tip (t near 0)
        for _ in range(650):  # INCREASED from 500
            t = random.gauss(0, 0.1)
            hx, hy = heart_2d(t)
            
            depth = random.uniform(0.5, 1.1)
            x = hx * depth * scale
            y = hy * depth * scale + heart_center_y
            max_z = depth_scale * scale * 0.95  # INCREASED from 0.75
            z = random.uniform(-max_z, max_z)
            
            color = random.choice([WHITE, HEART_COLORS[0], HEART_COLORS[-1]])
            size = random.uniform(1.6, 2.8)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=color,
                size=size,
                brightness=1.0,
                pulse_speed=random.uniform(0.08, 0.16),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
        
        # =====================================================================
        # 5. OUTER GLOW HALO
        # =====================================================================
        
        for _ in range(350):  # INCREASED from 250
            t = random.uniform(0, 2 * math.pi)
            hx, hy = heart_2d(t)
            
            halo_factor = random.uniform(1.15, 1.45)
            x = hx * halo_factor * scale
            y = hy * halo_factor * scale + heart_center_y
            max_z = depth_scale * scale * 1.4  # INCREASED from 1.2
            z = random.uniform(-max_z, max_z)
            
            color = random.choice(HEART_COLORS[3:])
            size = random.uniform(3.5, 6.0)
            
            self.heart_particles.append(HeartParticle(
                x=x, y=y, z=z,
                base_x=x, base_z=z,
                color=color,
                size=size,
                brightness=random.uniform(0.15, 0.35),
                pulse_speed=random.uniform(0.03, 0.08),
                pulse_phase=random.uniform(0, 2 * math.pi)
            ))
    
    def _generate_snow(self):
        """Generate floating particles like snow or distant stars"""
        self.snow_particles = []
        
        for _ in range(350):
            # Spread across entire visible space
            x = random.uniform(-self.width * 0.8, self.width * 0.8)
            y = random.uniform(-self.height * 0.6, self.height * 0.6)
            z = random.uniform(-400, 400)
            
            self.snow_particles.append(SnowParticle(
                x=x, y=y, z=z,
                size=random.uniform(0.5, 2.5),
                fall_speed=random.uniform(0.05, 0.25),  # Much slower falling
                drift_speed=random.uniform(0.2, 0.8),   # Slower drifting
                brightness=random.uniform(0.2, 0.9),
                twinkle_phase=random.uniform(0, 2 * math.pi)
            ))
    
    def _generate_ground(self):
        """Generate concentric energy rings on curved dome ground"""
        self.ground_rings = []
        
        num_rings = 7
        for i in range(num_rings):
            self.ground_rings.append(GroundRing(
                base_radius=80 + i * 45,
                color=RING_COLORS[i % len(RING_COLORS)],
                phase=i * 0.8,
                pulse_speed=0.025 + i * 0.008,
                thickness=2.5 - i * 0.2
            ))
    
    # ------------------------------------------------------------------------
    # PROJECTION & ROTATION
    # ------------------------------------------------------------------------
    
    def project_3d(self, x: float, y: float, z: float, zoom: float = 1.0,
                   fov: float = 350, viewer_dist: float = 650) -> Optional[Tuple[int, int, float]]:
        """Transform 3D coordinates to 2D screen with perspective projection"""
        x *= zoom
        y *= zoom
        z *= zoom
        
        if z + viewer_dist <= 0:
            return None
        
        factor = fov / (viewer_dist + z)
        x_2d = x * factor + self.width / 2
        y_2d = -y * factor + self.height / 2 - (40 * zoom)  # Adjusted for front-facing view (slightly top-down)
        
        return int(x_2d), int(y_2d), factor
    
    def rotate_y(self, x: float, z: float, angle: float) -> Tuple[float, float]:
        """Rotate point around Y axis by given angle"""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return x * cos_a - z * sin_a, x * sin_a + z * cos_a
    
    # ------------------------------------------------------------------------
    # DRAWING METHODS
    # ------------------------------------------------------------------------
    
    def _draw_glow_particle(self, surface: pygame.Surface, pos: Tuple[int, int],
                            color: Tuple[int, int, int], size: float, 
                            brightness: float = 1.0):
        """Draw a particle with soft glow effect"""
        if size < 0.5:
            return
        
        # Outer glow layers
        for i in range(3, 0, -1):
            glow_radius = int(size * (1 + i * 0.6))
            alpha = int(80 * brightness / i)
            
            glow_color = (
                min(255, int(color[0] * brightness * 0.8)),
                min(255, int(color[1] * brightness * 0.8)),
                min(255, int(color[2] * brightness * 0.8))
            )
            
            glow_surface = pygame.Surface((glow_radius * 2 + 4, glow_radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, (*glow_color, alpha),
                             (glow_radius + 2, glow_radius + 2), glow_radius)
            surface.blit(glow_surface, (pos[0] - glow_radius - 2, pos[1] - glow_radius - 2))
        
        # Bright core
        core_color = (
            min(255, int(color[0] * min(1.3, brightness * 1.2))),
            min(255, int(color[1] * min(1.3, brightness * 1.2))),
            min(255, int(color[2] * min(1.3, brightness * 1.2)))
        )
        pygame.draw.circle(surface, core_color, pos, max(1, int(size)))
    
    def _draw_snow(self, surface: pygame.Surface, zoom: float):
        """Draw floating snow/star particles"""
        for snow in self.snow_particles:
            rx, rz = self.rotate_y(snow.x, snow.z, self.rotation * 0.3)
            
            pos = self.project_3d(rx, snow.y, rz, zoom)
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                # Twinkle effect
                twinkle = 0.5 + 0.5 * math.sin(self.time * 0.04 + snow.twinkle_phase)
                brightness = snow.brightness * twinkle
                
                size = max(0.5, snow.size * pos[2] * zoom * 0.6)
                alpha = int(200 * brightness)
                
                if size >= 0.5:
                    pygame.draw.circle(surface, (255, 255, 255), (pos[0], pos[1]), max(1, int(size)))
    
    def _draw_ground(self, surface: pygame.Surface, zoom: float):
        """Draw curved dome ground with energy rings"""
        ground_y = -self.tree_height / 2 - 25
        
        for ring in self.ground_rings:
            # Animate ring
            ring.phase += ring.pulse_speed
            
            # Pulsing radius
            pulse = 1 + 0.12 * math.sin(ring.phase)
            current_radius = ring.base_radius * pulse * zoom
            
            # Draw ring as connected points on curved dome
            num_points = 80
            points = []
            
            for i in range(num_points + 1):
                angle = (i / num_points) * 2 * math.pi
                
                x = current_radius * math.cos(angle)
                z = current_radius * math.sin(angle)
                
                # Dome curvature: edges lower than center
                dome_factor = (ring.base_radius / 400) ** 2
                dome_y = -25 * dome_factor
                y = ground_y + dome_y
                
                rx, rz = self.rotate_y(x, z, self.rotation)
                pos = self.project_3d(rx, y, rz, zoom)
                
                if pos:
                    points.append((pos[0], pos[1]))
            
            if len(points) > 2:
                # Pulsing brightness
                brightness = 0.35 + 0.35 * math.sin(ring.phase * 1.5)
                draw_color = (
                    int(ring.color[0] * brightness),
                    int(ring.color[1] * brightness),
                    int(ring.color[2] * brightness)
                )
                
                thickness = max(1, int(ring.thickness * zoom))
                pygame.draw.lines(surface, draw_color, False, points, thickness)
    
    def _draw_tree(self, surface: pygame.Surface, zoom: float):
        """Draw the particle tree with depth sorting"""
        # Prepare particles with rotated positions for sorting
        render_list = []
        
        for p in self.tree_particles:
            rx, rz = self.rotate_y(p.base_x, p.base_z, self.rotation)
            render_list.append((p, rx, rz))
        
        # Sort by Z (far to near) for proper depth
        render_list.sort(key=lambda item: item[2], reverse=True)
        
        for p, rx, rz in render_list:
            pos = self.project_3d(rx, p.y, rz, zoom)
            
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                # Twinkle animation
                twinkle = 0.55 + 0.45 * math.sin(self.time * p.twinkle_speed + p.twinkle_phase)
                
                # Depth-based brightness (closer = brighter)
                depth_brightness = 0.6 + 0.4 * min(1.0, pos[2] / 0.8)
                
                final_brightness = twinkle * depth_brightness
                size = p.size * pos[2] * zoom * 1.4
                
                self._draw_glow_particle(surface, (pos[0], pos[1]), p.color, size, final_brightness)
    
    def _draw_heart(self, surface: pygame.Surface, zoom: float):
        """Draw the 3D volumetric glowing heart"""
        # Heart pulsing animation
        heart_pulse = 1 + 0.08 * math.sin(self.time * 0.06)
        
        # Prepare and sort heart particles
        render_list = []
        
        for p in self.heart_particles:
            # Apply pulse scaling
            px = p.base_x * heart_pulse
            pz = p.base_z * heart_pulse
            
            rx, rz = self.rotate_y(px, pz, self.rotation)
            render_list.append((p, rx, rz))
        
        render_list.sort(key=lambda item: item[2], reverse=True)
        
        for p, rx, rz in render_list:
            pos = self.project_3d(rx, p.y, rz, zoom)
            
            if pos and 0 <= pos[0] < self.width and 0 <= pos[1] < self.height:
                # Intense twinkle for heart
                twinkle = 0.65 + 0.35 * math.sin(self.time * p.pulse_speed + p.pulse_phase)
                
                final_brightness = twinkle * p.brightness * heart_pulse
                size = p.size * pos[2] * zoom * 1.25  # Slightly tighter
                
                self._draw_glow_particle(surface, (pos[0], pos[1]), p.color, size, final_brightness * 1.3)
        
        # Central heart glow (bright focal point)
        heart_center_y = self.tree_height / 2 + 60
        center_pos = self.project_3d(0, heart_center_y, 0, zoom)
        
        if center_pos:
            glow_pulse = 0.7 + 0.3 * math.sin(self.time * 0.08)
            glow_size = 35 * zoom * glow_pulse
            
            # Large soft glow layers
            for i in range(6, 0, -1):
                alpha = int(40 * (7 - i) / 6)
                radius = int(glow_size * i * 0.6)
                
                glow_surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (255, 180, 210, alpha), (radius + 2, radius + 2), radius)
                surface.blit(glow_surf, (center_pos[0] - radius - 2, center_pos[1] - radius - 2))
    
    # ------------------------------------------------------------------------
    # UPDATE & DRAW
    # ------------------------------------------------------------------------
    
    def update(self):
        """Update animation state each frame"""
        self.time += 1
        self.rotation += self.rotation_speed
        
        # Update snow particles (falling + drifting)
        for snow in self.snow_particles:
            snow.y -= snow.fall_speed
            snow.x += math.sin(self.time * 0.008 + snow.twinkle_phase) * snow.drift_speed * 0.1
            
            # Reset if below screen
            if snow.y < -self.height * 0.6:
                snow.y = self.height * 0.6
                snow.x = random.uniform(-self.width * 0.8, self.width * 0.8)
    
    def draw(self, surface: pygame.Surface, zoom_level: float = 1.0, 
             rotation_angle: Optional[float] = None):
        """
        Main draw method - renders the complete hologram scene
        
        Args:
            surface: Pygame surface to draw on
            zoom_level: Zoom factor (1.0 = normal)
            rotation_angle: Optional manual rotation angle (overrides auto-rotation)
        """
        # Allow external rotation control
        if rotation_angle is not None:
            self.rotation = rotation_angle
        
        # Draw layers in order (back to front)
        self._draw_snow(surface, zoom_level)
        # Ground rings removed
        self._draw_tree(surface, zoom_level)
        self._draw_heart(surface, zoom_level)
        
        # Update for next frame
        self.update()


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    pygame.init()
    
    WIDTH, HEIGHT = 1200, 850
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("✨ Magical Christmas Tree Hologram ✨")
    clock = pygame.time.Clock()
    
    # Create the hologram tree
    tree = HologramTree(WIDTH, HEIGHT)
    
    # Animation state
    zoom = 1.0
    auto_zoom = False
    zoom_direction = 0.005
    paused = False
    show_fps = False
    
    # Fonts
    try:
        font = pygame.font.SysFont("Arial", 18)
        title_font = pygame.font.SysFont("Arial", 14)
    except:
        font = pygame.font.Font(None, 18)
        title_font = pygame.font.Font(None, 14)
    
    running = True
    while running:
        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_f:
                    show_fps = not show_fps
                elif event.key == pygame.K_z:
                    auto_zoom = not auto_zoom
                elif event.key == pygame.K_LEFT:
                    tree.rotation_speed = max(-0.05, tree.rotation_speed - 0.003)
                elif event.key == pygame.K_RIGHT:
                    tree.rotation_speed = min(0.05, tree.rotation_speed + 0.003)
                elif event.key == pygame.K_UP:
                    zoom = min(2.5, zoom + 0.1)
                elif event.key == pygame.K_DOWN:
                    zoom = max(0.3, zoom - 0.1)
                elif event.key == pygame.K_r:
                    # Reset
                    tree.rotation_speed = 0.012
                    zoom = 1.0
                    auto_zoom = False
        
        # Clear screen to deep black
        screen.fill(BLACK)
        
        # Auto zoom effect
        if auto_zoom:
            zoom += zoom_direction
            if zoom > 1.8 or zoom < 0.6:
                zoom_direction *= -1
        
        # Draw the hologram (passing None for rotation to use internal auto-rotation)
        if not paused:
            tree.draw(screen, zoom)
        else:
            # When paused, don't update but still draw
            tree._draw_snow(screen, zoom)
            tree._draw_tree(screen, zoom)
            tree._draw_heart(screen, zoom)
        
        # UI overlay
        if show_fps:
            fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
            screen.blit(fps_text, (10, 10))
            
            zoom_text = font.render(f"Zoom: {zoom:.2f}", True, WHITE)
            screen.blit(zoom_text, (10, 30))
            
            speed_text = font.render(f"Rotation: {tree.rotation_speed:.3f}", True, WHITE)
            screen.blit(speed_text, (10, 50))
        
        # Controls hint
        hint = "← → : Speed | ↑ ↓ : Zoom | Z: Auto-Zoom | SPACE: Pause | F: FPS | R: Reset | ESC: Exit"
        hint_text = title_font.render(hint, True, (80, 80, 80))
        screen.blit(hint_text, (WIDTH // 2 - hint_text.get_width() // 2, HEIGHT - 25))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()