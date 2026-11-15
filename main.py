"""
Weighted Decision Maker - Pygame Desktop Edition
A complete, physics-driven balance scale with drag-and-drop weight blocks,
argument text entry, contributor tags, and dynamic beam tilting.
"""

import math
import sys
import pygame as pg

# Initialize Pygame
pg.init()
pg.font.init()

WIDTH, HEIGHT = 1400, 750
screen = pg.display.set_mode((WIDTH, HEIGHT))
pg.display.set_caption("Weighted Decision Maker - Retro Physics")
clock = pg.time.Clock()

# Palettes & Colors
BG_DARK = (14, 17, 24)
PANEL_BG = (22, 27, 38)
WHITE = (240, 244, 252)
GRAY = (120, 135, 155)
GOLD = (255, 209, 102)
CYAN = (0, 245, 212)
RED = (239, 71, 111)
GREEN = (6, 214, 160)
BLUE = (17, 138, 178)
BRASS = (195, 145, 50)
BEAM_COLOR = (212, 160, 45)

TAG_COLORS = {
    "Blue": (17, 138, 178),
    "Green": (6, 214, 160),
    "Red": (239, 71, 111),
    "Purple": (157, 78, 221),
    "Yellow": (255, 209, 102)
}

# Pre-cached Fonts
FONT_TITLE = pg.font.SysFont('Arial', 24, bold=True)
FONT_BOLD = pg.font.SysFont('Arial', 18, bold=True)
FONT_REGULAR = pg.font.SysFont('Arial', 15)
FONT_SMALL = pg.font.SysFont('Arial', 12)
FONT_SCORE = pg.font.SysFont('Consolas', 28, bold=True)


class WeightBlock:
    def __init__(self, x, y, weight, text, tag="Yellow"):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.weight = max(1, int(weight))
        self.text = text
        self.tag = tag
        self.color = TAG_COLORS.get(tag, TAG_COLORS["Yellow"])
        
        # Dimensions scale with numerical weight
        self.w = 40 + min(35, self.weight * 3)
        self.h = 30 + min(25, self.weight * 2)
        
        self.is_dragging = False
        self.settled = False
        self.side = None  # 'left' or 'right'

    @property
    def rect(self):
        return pg.Rect(int(self.x - self.w / 2), int(self.y - self.h / 2), int(self.w), int(self.h))

    def update_physics(self, dt, tray_left, tray_right):
        if self.is_dragging:
            return

        # Gravity
        self.vy += 900.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Air resistance
        self.vx *= 0.98
        self.vy *= 0.99

        # Detect closer tray
        dist_left = abs(self.x - tray_left['x'])
        dist_right = abs(self.x - tray_right['x'])
        active_tray = tray_left if dist_left < dist_right else tray_right
        assigned_side = 'left' if active_tray == tray_left else 'right'

        floor_y = active_tray['y']
        tray_left_wall = active_tray['x'] - active_tray['w'] / 2 + self.w / 2
        tray_right_wall = active_tray['x'] + active_tray['w'] / 2 - self.w / 2
        self.side = assigned_side
        if self.y > 750:
            if assigned_side == 'left':
                self.y = 0
                self.x = 400
            if assigned_side == 'right':
                    self.y = 0
                    self.x = 1000
        
        # Tray floor collision
        if (self.y + self.h / 2 >= floor_y and 
            active_tray['x'] - active_tray['w'] / 2 - 15 <= self.x <= active_tray['x'] + active_tray['w'] / 2 + 15):
            self.y = floor_y - self.h / 2
            self.vy = -self.vy * 0.25  # Bounce restitution
            self.vx *= 0.80           # Floor friction
            if abs(self.vy) < 15:
                self.vy = 0
            if abs(self.vx) < 5:
                self.vx = 0
            self.settled = True
            
        
        else:
            self.settled = False

        # Tray side lip containment
        if self.y + self.h / 2 > floor_y - active_tray['lip_h']:
            if self.x < tray_left_wall and self.x > tray_left_wall - 30:
                self.x = tray_left_wall
                self.vx = -self.vx * 0.3
            elif self.x > tray_right_wall and self.x < tray_right_wall + 30:
                self.x = tray_right_wall
                self.vx = -self.vx * 0.3

    def draw(self, surface, is_hovered=False):
        r = self.rect

        # Drop shadow
        shadow_rect = pg.Rect(r.x + 3, r.y + 3, r.w, r.h)
        pg.draw.rect(surface, (0, 0, 0, 100), shadow_rect)

        # Block body
        pg.draw.rect(surface, self.color, r)

        # 3D Bevel
        pg.draw.line(surface, (255, 255, 255), (r.left, r.top), (r.right, r.top), 2)
        pg.draw.line(surface, (255, 255, 255), (r.left, r.top), (r.left, r.bottom), 2)
        pg.draw.line(surface, (0, 0, 0), (r.left, r.bottom), (r.right, r.bottom), 2)
        pg.draw.line(surface, (0, 0, 0), (r.right, r.top), (r.right, r.bottom), 2)

        if is_hovered:
            pg.draw.rect(surface, WHITE, r, 2)
        elif self.is_dragging:
            pg.draw.rect(surface, CYAN, r, 2)

        # Weight number stamp
        lbl = FONT_BOLD.render(str(self.weight), True, (0, 0, 0))
        surface.blit(lbl, lbl.get_rect(center=r.center))


class BalanceScale:
    def __init__(self, pivot_x, pivot_y, beam_length=500, chain_len=170, tray_w=190):
        self.pivot_x = pivot_x
        self.pivot_y = pivot_y
        self.beam_length = beam_length
        self.chain_len = chain_len
        self.tray_w = tray_w
        self.tray_h = 18
        self.lip_h = 35

        self.angle = 0.0
        self.angular_velocity = 0.0
        self.max_angle = math.radians(22)

        self.spring_k = 4.5
        self.damping = 3.2

    def update_physics(self, dt, left_weight, right_weight):
        total_w = left_weight + right_weight
        diff = right_weight - left_weight

        target_angle = 0.0
        if total_w > 0:
            ratio = diff / max(total_w, 8)
            target_angle = max(-self.max_angle, min(self.max_angle, ratio * self.max_angle * 1.4))

        spring_torque = -self.spring_k * (self.angle - target_angle)
        damp_torque = -self.damping * self.angular_velocity
        ang_acc = spring_torque + damp_torque

        self.angular_velocity += ang_acc * dt
        self.angle += self.angular_velocity * dt

    def get_geometry(self):
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)
        half_l = self.beam_length / 2

        left_tip = (self.pivot_x - half_l * cos_a, self.pivot_y - half_l * sin_a)
        right_tip = (self.pivot_x + half_l * cos_a, self.pivot_y + half_l * sin_a)

        left_tray = {
            'x': left_tip[0],
            'y': left_tip[1] + self.chain_len,
            'w': self.tray_w,
            'h': self.tray_h,
            'lip_h': self.lip_h
        }
        right_tray = {
            'x': right_tip[0],
            'y': right_tip[1] + self.chain_len,
            'w': self.tray_w,
            'h': self.tray_h,
            'lip_h': self.lip_h
        }
        return left_tip, right_tip, left_tray, right_tray

    def draw(self, surface):
        left_tip, right_tip, left_tray, right_tray = self.get_geometry()

        # 1. Pedestal Base & Pillar
        base_w, base_h = 100, 24
        pg.draw.rect(surface, (30, 25, 20), (self.pivot_x - base_w // 2, HEIGHT - 50, base_w, base_h))
        pg.draw.rect(surface, (10, 8, 6), (self.pivot_x - base_w // 2, HEIGHT - 50, base_w, base_h), 2)
        pg.draw.rect(surface, (45, 38, 30), (self.pivot_x - 10, self.pivot_y, 20, HEIGHT - 50 - self.pivot_y))
        pg.draw.rect(surface, (15, 12, 10), (self.pivot_x - 10, self.pivot_y, 20, HEIGHT - 50 - self.pivot_y), 2)

        # 2. Chains
        def draw_chain(start, end):
            pg.draw.line(surface, GRAY, start, end, 2)
            for t in [0.2, 0.4, 0.6, 0.8]:
                cx = start[0] + (end[0] - start[0]) * t
                cy = start[1] + (end[1] - start[1]) * t
                pg.draw.circle(surface, (180, 190, 210), (int(cx), int(cy)), 3)

        draw_chain(left_tip, (left_tray['x'] - left_tray['w'] / 2 + 10, left_tray['y'] - left_tray['lip_h']))
        draw_chain(left_tip, (left_tray['x'] + left_tray['w'] / 2 - 10, left_tray['y'] - left_tray['lip_h']))
        draw_chain(right_tip, (right_tray['x'] - right_tray['w'] / 2 + 10, right_tray['y'] - right_tray['lip_h']))
        draw_chain(right_tip, (right_tray['x'] + right_tray['w'] / 2 - 10, right_tray['y'] - right_tray['lip_h']))

        # 3. Trays
        def draw_tray(tray, accent_color):
            px = tray['x'] - tray['w'] / 2
            py = tray['y']
            pg.draw.rect(surface, (30, 38, 55), (px, py, tray['w'], tray['h']))
            pg.draw.rect(surface, (0, 0, 0), (px, py, tray['w'], tray['h']), 2)
            pg.draw.line(surface, accent_color, (px + 4, py + 2), (px + tray['w'] - 4, py + 2), 3)
            pg.draw.rect(surface, (40, 50, 75), (px - 4, py - tray['lip_h'], 6, tray['lip_h'] + tray['h']))
            pg.draw.rect(surface, (40, 50, 75), (px + tray['w'] - 2, py - tray['lip_h'], 6, tray['lip_h'] + tray['h']))

        draw_tray(left_tray, CYAN)
        draw_tray(right_tray, GOLD)

        # 4. Tilting Beam & Pivot
        pg.draw.line(surface, BEAM_COLOR, left_tip, right_tip, 12)
        pg.draw.line(surface, (255, 230, 150), (left_tip[0], left_tip[1] - 2), (right_tip[0], right_tip[1] - 2), 2)
        pg.draw.circle(surface, GOLD, (int(left_tip[0]), int(left_tip[1])), 6)
        pg.draw.circle(surface, GOLD, (int(right_tip[0]), int(right_tip[1])), 6)

        pg.draw.circle(surface, RED, (self.pivot_x, self.pivot_y), 10)
        pg.draw.circle(surface, (0, 0, 0), (self.pivot_x, self.pivot_y), 10, 2)
        pg.draw.circle(surface, GOLD, (self.pivot_x, self.pivot_y), 4)


def main():
    scale = BalanceScale(pivot_x=WIDTH // 2, pivot_y=200)
    blocks = [

    ]

    active_side = "left"
    typed_text = ""
    current_weight = 5
    current_tag = "Yellow"
    tag_keys = list(TAG_COLORS.keys())
    tag_idx = 0

    dragged_block = None
    drag_offset = (0, 0)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mouse_pos = pg.mouse.get_pos()

        

        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False
                elif event.key == pg.K_BACKSPACE:
                    typed_text = typed_text[:-1]
                elif event.key == pg.K_TAB:
                    active_side = "right" if active_side == "left" else "left"
                elif event.key == pg.K_UP:
                    current_weight = min(10, current_weight + 1)
                elif event.key == pg.K_DOWN:
                    current_weight = max(1, current_weight - 1)
                elif event.key == pg.K_LEFT:
                    tag_idx = (tag_idx + 1) % len(tag_keys)
                    current_tag = tag_keys[tag_idx]
                elif event.key == pg.K_RETURN:
                    if typed_text.strip():
                        spawn_x = scale.pivot_x - 220 if active_side == "left" else scale.pivot_x + 220
                        new_b = WeightBlock(spawn_x, 80, current_weight, typed_text.strip(), current_tag)
                        new_b.side = active_side
                        blocks.append(new_b)
                        typed_text = ""
                else:
                    if len(typed_text) < 45:
                        typed_text += event.unicode

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click: drag block
                    for b in reversed(blocks):
                        if b.rect.collidepoint(mouse_pos):
                            dragged_block = b
                            b.is_dragging = True
                            b.vx = 0
                            b.vy = 0
                            drag_offset = (b.x - mouse_pos[0], b.y - mouse_pos[1])
                            break
                elif event.button == 3:  # Right click: delete block
                    for b in reversed(blocks):
                        if b.rect.collidepoint(mouse_pos):
                            blocks.remove(b)
                            break

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1 and dragged_block:
                    dragged_block.is_dragging = False
                    dragged_block = None

        if dragged_block:
            dragged_block.x = mouse_pos[0] + drag_offset[0]
            dragged_block.y = mouse_pos[1] + drag_offset[1]

        # Physics updates
        _, _, left_tray, right_tray = scale.get_geometry()
        for b in blocks:
            b.update_physics(dt, left_tray, right_tray)

        # Block stacking collisions
        for i in range(len(blocks)):
            for j in range(i + 1, len(blocks)):
                b1, b2 = blocks[i], blocks[j]
                if b1.is_dragging or b2.is_dragging:
                    continue
                r1, r2 = b1.rect, b2.rect
                if r1.colliderect(r2):
                    overlap_y = (r1.height + r2.height) / 2 - abs(b1.y - b2.y)
                    if b1.y < b2.y:
                        b1.y -= overlap_y * 0.5
                        b2.y += overlap_y * 0.5
                    else:
                        b1.y += overlap_y * 0.5
                        b2.y -= overlap_y * 0.5
                    b1.vy *= 0.5
                    b2.vy *= 0.5

        # Tally settled weights
        left_total = sum(b.weight for b in blocks if b.side == 'left')
        right_total = sum(b.weight for b in blocks if b.side == 'right')
        left_count = sum(1 for b in blocks if b.side == 'left')
        right_count = sum(1 for b in blocks if b.side == 'right')

        scale.update_physics(dt, left_total, right_total)

        # Rendering
        screen.fill(BG_DARK)

        # 1. Scoreboard HUD
        hud_rect = pg.Rect(WIDTH // 2 - 380, 15, 760, 80)
        pg.draw.rect(screen, PANEL_BG, hud_rect)
        pg.draw.rect(screen, (0, 0, 0), hud_rect, 3)

        l_txt = FONT_SCORE.render(f"{left_total} PTS", True, CYAN)
        l_cnt = FONT_REGULAR.render(f"[{left_count} args]", True, GRAY)
        screen.blit(l_txt, (hud_rect.left + 25, hud_rect.top + 15))
        screen.blit(l_cnt, (hud_rect.left + 25, hud_rect.top + 50))

        diff = abs(left_total - right_total)
        if left_total > right_total:
            verdict = f"<-- LEFT LEADS (+{diff} PTS)"
            v_color = CYAN
        elif right_total > left_total:
            verdict = f"RIGHT LEADS (+{diff} PTS) -->"
            v_color = GOLD
        else:
            verdict = "== PERFECT EQUILIBRIUM =="
            v_color = GREEN
        v_surf = FONT_BOLD.render(verdict, True, v_color)
        screen.blit(v_surf, v_surf.get_rect(center=(WIDTH // 2, hud_rect.centery)))

        r_txt = FONT_SCORE.render(f"{right_total} PTS", True, GOLD)
        r_cnt = FONT_REGULAR.render(f"[{right_count} args]", True, GRAY)
        screen.blit(r_txt, (hud_rect.right - 140, hud_rect.top + 15))
        screen.blit(r_cnt, (hud_rect.right - 140, hud_rect.top + 50))

        # 2. Scale & Blocks
        scale.draw(screen)

        hovered_block = None
        for b in blocks:
            is_h = b.rect.collidepoint(mouse_pos)
            if is_h and not hovered_block:
                hovered_block = b
            b.draw(screen, is_hovered=is_h)

        # 3. Hover Tooltip
        if hovered_block:
            tip_w, tip_h = 280, 68
            tx = min(mouse_pos[0] + 15, WIDTH - tip_w - 15)
            ty = min(mouse_pos[1] + 15, HEIGHT - tip_h - 15)
            t_rect = pg.Rect(tx, ty, tip_w, tip_h)
            pg.draw.rect(screen, (10, 13, 20), t_rect)
            pg.draw.rect(screen, hovered_block.color, t_rect, 2)

            t_tag = FONT_SMALL.render(f"[{hovered_block.tag.upper()}] - {hovered_block.weight} PTS", True, hovered_block.color)
            t_text = FONT_REGULAR.render(f'"{hovered_block.text}"', True, WHITE)
            screen.blit(t_tag, (tx + 8, ty + 8))
            screen.blit(t_text, (tx + 8, ty + 30))

        # 4. Input Console
        bottom_bar = pg.Rect(50, HEIGHT - 70, WIDTH - 100, 55)
        pg.draw.rect(screen, PANEL_BG, bottom_bar)
        pg.draw.rect(screen, (0, 0, 0), bottom_bar, 2)

        side_badge_color = CYAN if active_side == "left" else GOLD
        side_lbl = FONT_BOLD.render(f"TARGET: {active_side.upper()} (TAB to switch)", True, side_badge_color)
        weight_lbl = FONT_REGULAR.render(f"Weight: {current_weight} (UP/DOWN)", True, GOLD)
        tag_lbl = FONT_REGULAR.render(f"Color: {current_tag} (T to cycle)", True, TAG_COLORS[current_tag])
        
        screen.blit(side_lbl, (bottom_bar.left + 15, bottom_bar.top + 8))
        screen.blit(weight_lbl, (bottom_bar.left + 350, bottom_bar.top + 8))
        screen.blit(tag_lbl, (bottom_bar.left + 540, bottom_bar.top + 8))

        prompt_str = f"Type Argument & Press ENTER: {typed_text}_"
        inp_surf = FONT_REGULAR.render(prompt_str, True, WHITE)
        screen.blit(inp_surf, (bottom_bar.left + 15, bottom_bar.top + 30))

        pg.display.flip()
    
    pg.quit()
    sys.exit()


if __name__ == "__main__":
    main()