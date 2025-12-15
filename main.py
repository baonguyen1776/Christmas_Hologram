import pygame
import math
import random

# 1. Khởi tạo Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cây Thông Noel 3D Lung Linh")

# Màu sắc (Hồng/Tím/Đỏ như video)
BLACK = (0, 0, 0)
COLORS = [
    (255, 0, 0),    # Đỏ
    (255, 105, 180), # Hồng đậm
    (255, 182, 193), # Hồng nhạt
    (255, 215, 0),   # Vàng (để điểm xuyết)
    (230, 230, 250)  # Tím nhạt
]

# 2. Thông số cây thông
clock = pygame.time.Clock()
rotation_speed = 0  # Góc xoay khởi đầu

def project_3d_to_2d(x, y, z):
    """Chuyển đổi toạ độ 3D sang màn hình 2D"""
    fov = 300  # Độ trường nhìn
    viewer_distance = 600
    
    # Nếu điểm ở quá gần mắt hoặc sau lưng thì không vẽ
    if z + viewer_distance <= 0:
        return None
        
    factor = fov / (viewer_distance + z)
    x_2d = x * factor + WIDTH / 2
    y_2d = -y * factor + HEIGHT / 2 + 100 # +100 để đẩy cây xuống giữa
    return (int(x_2d), int(y_2d), factor)

# 3. Vòng lặp chính
running = True
while running:
    # Xử lý nút tắt
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK) # Xóa màn hình đen
    
    # Tăng góc xoay để cây tự quay
    rotation_speed += 0.02

    # --- THUẬT TOÁN VẼ CÂY THÔNG ---
    # Vẽ từ đỉnh (y cao) xuống gốc (y thấp)
    # y chạy từ 200 xuống -200
    for i in range(1500): # 1500 hạt sáng tạo nên cây
        # Tính toán hình dáng (Hình nón xoắn ốc)
        t = i / 1500 # Tỉ lệ từ 0 đến 1
        
        # y: Chiều cao
        y = 200 - t * 400 
        
        # r: Bán kính (càng xuống thấp bán kính càng to)
        r = t * 150 
        
        # Góc xoắn ốc (Spiral)
        angle = t * 20 * math.pi + rotation_speed
        
        # Toạ độ 3D ban đầu
        x = r * math.cos(angle)
        z = r * math.sin(angle)
        
        # --- Tạo hiệu ứng lấp lánh ngẫu nhiên ---
        if random.random() > 0.95: 
            color = (255, 255, 255) # Hạt nhấp nháy trắng
            size = 3
        else:
            # Chọn màu dựa theo độ cao (trên đỏ dưới hồng)
            color_index = int(t * (len(COLORS) - 1))
            color = COLORS[color_index]
            size = 2

        # --- Chiếu lên màn hình ---
        pos = project_3d_to_2d(x, y, z)
        
        if pos:
            px, py, scale = pos
            # Vẽ chấm sáng
            # scale giúp hạt ở gần thì to, ở xa thì nhỏ (hiệu ứng 3D)
            final_size = max(1, int(size * scale * 1.5))
            pygame.draw.circle(screen, color, (px, py), final_size)

    # Vẽ ngôi sao trên đỉnh
    star_pos = project_3d_to_2d(0, 210, 0)
    if star_pos:
        pygame.draw.circle(screen, (255, 255, 0), (star_pos[0], star_pos[1]), 6)
        
    # Vẽ chữ
    font = pygame.font.SysFont('Arial', 30, bold=True)
    text = font.render("MERRY CHRISTMAS", True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH/2, HEIGHT - 50))
    screen.blit(text, text_rect)

    # Cập nhật màn hình (60 FPS)
    pygame.display.flip()
    clock.tick(60)

pygame.quit()