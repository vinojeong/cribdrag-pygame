"""
Two-time pad crib-dragging workspace.
Loads citext49 and citext192 from the same folder and falls back to embedded default copies.
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

import pygame
from pygame.locals import *


# ----------------------------------------------------------------------
# Byte helpers
# ----------------------------------------------------------------------

def xor(a, b):
    """Bytewise XOR of two lists, truncated to shorter length."""
    n = min(len(a), len(b))
    s = [a[i] ^ b[i] for i in range(n)]
    if len(a) > n:
        s.extend(a[n:])
    elif len(b) > n:
        s.extend(b[n:])
    return s


def cribpend(a, crib, loc):
    """Place crib at loc, padding with zeros."""
    s = [0] * len(a)
    for i, ch in enumerate(crib):
        if 0 <= loc + i < len(a):
            s[loc + i] = ch
    return s


def bit(a):
    """8‑bit binary string."""
    return format(a & 0xFF, '08b')


def s_to_ints(s):
    return [ord(c) for c in s]


# Allowed plaintext bytes (assignment spec)
def is_allowed(b):
    return (32 <= b <= 41) or (44 <= b <= 59) or b == 63 or b in (91, 93) \
        or (65 <= b <= 90) or (97 <= b <= 122)


def display_char(b, crib_mode=False):
    """Render one byte as a character."""
    if b == 0:
        return ' ' if crib_mode else '\u2588'
    if is_allowed(b):
        return chr(b)
    if b in (10, 13):
        return '\u21b5'
    return '.'


# ----------------------------------------------------------------------
# Load ciphertexts
# ----------------------------------------------------------------------

def load_ciphertexts():
    here = os.path.dirname(os.path.abspath(__file__))
    p1 = os.path.join(here, 'citext49')
    p2 = os.path.join(here, 'citext192')
    if os.path.exists(p1) and os.path.exists(p2):
        c1 = list(open(p1, 'rb').read())
        c2 = list(open(p2, 'rb').read())
        return c1, c2, "loaded from citext49 / citext192"
    else:
        return _BACKUP_C1[:], _BACKUP_C2[:], "loaded from embedded backup (files not found)"


# ----------------------------------------------------------------------
# Layout constants
# ----------------------------------------------------------------------

LEFT_MARGIN = 30
LABEL_WIDTH = 70
CHAR_W = 11
ROW_HEIGHT = 24
CHARS_PER_ROW = 100
GRID_X = LEFT_MARGIN + LABEL_WIDTH


def rows_needed(n):
    return (n + CHARS_PER_ROW - 1) // CHARS_PER_ROW


def index_from_mouse(mx, my, section_top_y, n):
    if mx < GRID_X or my < section_top_y:
        return None
    col = (mx - GRID_X) // CHAR_W
    row = (my - section_top_y) // ROW_HEIGHT
    if col < 0 or col >= CHARS_PER_ROW or row < 0:
        return None
    idx = row * CHARS_PER_ROW + col
    if idx >= n:
        return None
    return idx


def max_valid_loc(n, crib_len):
    if crib_len == 0:
        return max(0, n - 1)
    return max(0, n - crib_len)


def delete_last_word(s):
    stripped = s.rstrip(' ')
    idx = stripped.rfind(' ')
    return stripped[:idx + 1] if idx != -1 else ''


def get_clipboard_text():
    """Read clipboard using OS tools; returns None on failure."""
    import subprocess
    import platform
    system = platform.system()
    try:
        if system == "Darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            return result.stdout if result.returncode == 0 else None
        elif system == "Windows":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=2)
            return result.stdout if result.returncode == 0 else None
        else:
            for cmd in (["xclip", "-selection", "clipboard", "-o"],
                        ["xsel", "--clipboard", "--output"],
                        ["wl-paste"]):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        return result.stdout
                except FileNotFoundError:
                    continue
            return None
    except Exception:
        return None


def wrap_text(text, font, max_width):
    """Greedy word wrap for a given font and width."""
    words = text.split(' ')
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def main():
    c1, c2, source_msg = load_ciphertexts()
    n = min(len(c1), len(c2))
    x = xor(c1, c2)

    pygame.init()
    pygame.key.set_repeat(250, 30)

    win_w = GRID_X + CHARS_PER_ROW * CHAR_W + 30
    FOOTER_H = 55

    font_title = pygame.font.SysFont("Arial", 20, bold=True)
    font_label = pygame.font.SysFont("Arial", 16, italic=True)
    font_mono = pygame.font.SysFont("Courier New", 18)
    font_small = pygame.font.SysFont("Arial", 15)

    info_line = f"{source_msg}  |  {n} bytes"
    tips_text = ("Tips:  drag or click in the crib (R) row to place it  --  click any byte in any "
                 "row to inspect it  --  Ctrl/Cmd+V to paste  --  Ctrl/Cmd+Z to undo  --  "
                 "Ctrl/Option+Backspace to delete the last word  --  Esc clears the crib  --  "
                 "scroll with the mouse wheel, arrow keys, or Page Up/Down")
    tip_lines = wrap_text(tips_text, font_small, win_w - 2 * LEFT_MARGIN)

    TITLE_Y, INFO_Y = 10, 34
    TIP_START_Y = 54
    TIP_LINE_H = 18
    HEADER_H = TIP_START_Y + len(tip_lines) * TIP_LINE_H + 8

    section_height = 30 + rows_needed(n) * ROW_HEIGHT + 20
    content_h = section_height * 5 + 20

    desired_win_h = HEADER_H + content_h + FOOTER_H
    try:
        display_info = pygame.display.Info()
        screen_room = max(400, display_info.current_h - 120)
    except Exception:
        screen_room = desired_win_h
    win_h = min(desired_win_h, screen_room)

    viewport_h = win_h - HEADER_H - FOOTER_H
    max_scroll = max(0, content_h - viewport_h)
    scroll_y = 0
    SCROLL_STEP = ROW_HEIGHT * 2

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Crib-Dragging Workspace")
    clock = pygame.time.Clock()

    content_surface = pygame.Surface((win_w, content_h))

    BG = (250, 250, 250)
    C_TEXT = (20, 20, 20)
    C_LABEL = (0, 110, 0)
    C_CRIB = (200, 30, 30)
    C_RESULT = (0, 70, 160)
    C_INDEX = (160, 160, 160)

    crib_str = ""
    loc = 0
    is_dragging = False
    inspect_idx = None
    done = False
    undo_stack = []
    MAX_UNDO = 100

    y = 5
    section_tops = {}
    for name in ["C1", "C2", "X", "R", "XR"]:
        section_tops[name] = y + 26
        y += section_height

    def push_undo():
        undo_stack.append((crib_str, loc))
        if len(undo_stack) > MAX_UNDO:
            undo_stack.pop(0)

    def draw_grid(surface, data, top_y, color, crib_mode=False):
        for i in range(n):
            row, col = divmod(i, CHARS_PER_ROW)
            if col == 0:
                idxlabel = font_small.render(f"[{i:03d}]", True, C_INDEX)
                surface.blit(idxlabel, (LEFT_MARGIN, top_y + row * ROW_HEIGHT))
            ch = display_char(data[i], crib_mode=crib_mode)
            glyph = font_mono.render(ch, True, color)
            surface.blit(glyph, (GRID_X + col * CHAR_W, top_y + row * ROW_HEIGHT))

    def draw_active_range_highlight(surface, top_y, start, end):
        if end < start:
            return
        overlay_color = (255, 221, 130, 90)
        border_color = (235, 160, 40)
        row_start, col_start = divmod(start, CHARS_PER_ROW)
        row_end, col_end = divmod(end, CHARS_PER_ROW)
        for row in range(row_start, row_end + 1):
            c0 = col_start if row == row_start else 0
            c1 = col_end if row == row_end else CHARS_PER_ROW - 1
            rx = GRID_X + c0 * CHAR_W
            ry = top_y + row * ROW_HEIGHT
            rw = (c1 - c0 + 1) * CHAR_W
            rh = ROW_HEIGHT
            band = pygame.Surface((rw, rh), pygame.SRCALPHA)
            band.fill(overlay_color)
            surface.blit(band, (rx, ry))
            pygame.draw.rect(surface, border_color, (rx, ry, rw, rh), 1)

    def screen_y_to_content_y(my):
        if my < HEADER_H or my > HEADER_H + viewport_h:
            return None
        return my - HEADER_H + scroll_y

    while not done:
        for event in pygame.event.get():
            if event.type == QUIT:
                done = True

            elif event.type == MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button in (4, 5):
                    scroll_y += (-SCROLL_STEP if event.button == 4 else SCROLL_STEP)
                    scroll_y = max(0, min(scroll_y, max_scroll))
                    continue
                cy = screen_y_to_content_y(my)
                if cy is None:
                    continue
                r_top = section_tops["R"]
                r_bottom = r_top + rows_needed(n) * ROW_HEIGHT
                if r_top <= cy <= r_bottom:
                    is_dragging = True
                    idx = index_from_mouse(mx, cy, r_top, n)
                    if idx is not None:
                        loc = min(idx, max_valid_loc(n, len(crib_str)))
                else:
                    for name in ["C1", "C2", "X", "R", "XR"]:
                        top = section_tops[name]
                        bottom = top + rows_needed(n) * ROW_HEIGHT
                        if top <= cy <= bottom:
                            idx = index_from_mouse(mx, cy, top, n)
                            if idx is not None:
                                inspect_idx = idx

            elif event.type == MOUSEBUTTONUP:
                is_dragging = False

            elif event.type == MOUSEMOTION and is_dragging:
                cy = screen_y_to_content_y(event.pos[1])
                if cy is not None:
                    idx = index_from_mouse(event.pos[0], cy, section_tops["R"], n)
                    if idx is not None:
                        loc = min(idx, max_valid_loc(n, len(crib_str)))

            elif event.type == MOUSEWHEEL:
                scroll_y -= event.y * SCROLL_STEP
                scroll_y = max(0, min(scroll_y, max_scroll))

            elif event.type == KEYDOWN:
                mods = pygame.key.get_mods()
                ctrl_or_cmd = bool(mods & (KMOD_CTRL | KMOD_META))
                word_delete_mod = bool(mods & (KMOD_CTRL | KMOD_ALT | KMOD_META))

                if event.key == K_z and ctrl_or_cmd:
                    if undo_stack:
                        crib_str, loc = undo_stack.pop()
                        loc = min(loc, max_valid_loc(n, len(crib_str)))
                elif event.key == K_ESCAPE:
                    if crib_str:
                        push_undo()
                    crib_str = ""
                    loc = 0
                elif event.key == K_LEFT and loc > 0:
                    loc -= 1
                elif event.key == K_RIGHT and loc < max_valid_loc(n, len(crib_str)):
                    loc += 1
                elif event.key == K_UP:
                    scroll_y = max(0, scroll_y - SCROLL_STEP)
                elif event.key == K_DOWN:
                    scroll_y = min(max_scroll, scroll_y + SCROLL_STEP)
                elif event.key == K_PAGEUP:
                    scroll_y = max(0, scroll_y - viewport_h)
                elif event.key == K_PAGEDOWN:
                    scroll_y = min(max_scroll, scroll_y + viewport_h)
                elif event.key == K_v and ctrl_or_cmd:
                    pasted = get_clipboard_text()
                    if pasted:
                        pasted = "".join(c for c in pasted if ord(c) <= 255 and c not in ('\n', '\r'))
                        room = max(0, n - loc - len(crib_str))
                        if pasted[:room]:
                            push_undo()
                            crib_str += pasted[:room]
                elif event.key == K_BACKSPACE and word_delete_mod:
                    if crib_str:
                        push_undo()
                    crib_str = delete_last_word(crib_str)
                    loc = min(loc, max_valid_loc(n, len(crib_str)))
                elif event.key == K_BACKSPACE:
                    if crib_str:
                        push_undo()
                    crib_str = crib_str[:-1]
                    loc = min(loc, max_valid_loc(n, len(crib_str)))
                elif event.unicode and event.unicode.isprintable() and not ctrl_or_cmd:
                    if ord(event.unicode) <= 255 and loc + len(crib_str) < n:
                        push_undo()
                        crib_str += event.unicode

        # Drawing
        screen.fill(BG)

        # Header
        screen.blit(font_title.render(
            "Crib-Dragging Workspace -- two-time pad", True, (0, 0, 0)), (LEFT_MARGIN, TITLE_Y))
        screen.blit(font_small.render(info_line, True, (90, 90, 90)), (LEFT_MARGIN, INFO_Y))
        for i, line in enumerate(tip_lines):
            screen.blit(font_small.render(line, True, (130, 130, 130)),
                        (LEFT_MARGIN, TIP_START_Y + i * TIP_LINE_H))

        # Build content
        content_surface.fill(BG)

        crib_bytes = cribpend(c1, s_to_ints(crib_str), loc)
        xr = xor(x, crib_bytes)

        sections = [
            ("C1", "Ciphertext 1 (C1):", c1, C_TEXT, False),
            ("C2", "Ciphertext 2 (C2):", c2, C_TEXT, False),
            ("X", "Xortext (X = C1 XOR C2):", x, C_TEXT, False),
            ("R", "Crib (R) -- drag or type here:", crib_bytes, C_CRIB, True),
            ("XR", "Recovered plaintext candidate (X XOR R):", xr, C_RESULT, False),
        ]

        active_start = loc
        active_end = loc + len(crib_str) - 1

        for name, label, data, color, crib_mode in sections:
            top = section_tops[name]
            label_surf = font_label.render(label, True, C_LABEL if name != "R" else C_CRIB)
            content_surface.blit(label_surf, (LEFT_MARGIN, top - 24))

            if active_end >= active_start:
                draw_active_range_highlight(content_surface, top, active_start, active_end)

            draw_grid(content_surface, data, top, color, crib_mode=crib_mode)

            if name == "R":
                info_x = LEFT_MARGIN + label_surf.get_width() + 20
                available_w = win_w - info_x - 65
                crib_disp = crib_str.replace('\n', '\u21b5')
                full_text = f'loc={loc}  len={len(crib_str)}  crib="{crib_disp}"'
                if font_small.size(full_text)[0] > available_w:
                    while crib_disp and font_small.size(
                            f'loc={loc}  len={len(crib_str)}  crib="{crib_disp}..."')[0] > available_w:
                        crib_disp = crib_disp[:-1]
                    full_text = f'loc={loc}  len={len(crib_str)}  crib="{crib_disp}..."'
                content_surface.blit(font_small.render(full_text, True, C_CRIB), (info_x, top - 24))

        # Cursor
        r_top = section_tops["R"]
        cursor_pos = min(loc + len(crib_str), n - 1)
        row, col = divmod(cursor_pos, CHARS_PER_ROW)
        cx = GRID_X + col * CHAR_W
        cy = r_top + row * ROW_HEIGHT
        pygame.draw.line(content_surface, C_CRIB, (cx, cy), (cx, cy + ROW_HEIGHT - 4), 2)

        # Blit visible part
        screen.blit(content_surface, (0, HEADER_H),
                    area=pygame.Rect(0, scroll_y, win_w, viewport_h))

        # Scrollbar
        if max_scroll > 0:
            bar_track_h = viewport_h
            bar_h = max(20, int(bar_track_h * viewport_h / content_h))
            bar_y = HEADER_H + int((bar_track_h - bar_h) * (scroll_y / max_scroll))
            pygame.draw.rect(screen, (220, 220, 220), (win_w - 10, HEADER_H, 8, bar_track_h))
            pygame.draw.rect(screen, (140, 140, 140), (win_w - 10, bar_y, 8, bar_h))

        # Footer: inspection panel
        pygame.draw.line(screen, (200, 200, 200), (0, win_h - FOOTER_H), (win_w, win_h - FOOTER_H), 1)
        if inspect_idx is not None and inspect_idx < n:
            i = inspect_idx
            eq = (f"C1[{i}]={c1[i]}({bit(c1[i])})  XOR  C2[{i}]={c2[i]}({bit(c2[i])})"
                  f"  =  X[{i}]={x[i]}({bit(x[i])})")
            eq2 = (f"X[{i}]={x[i]}({bit(x[i])})  XOR  R[{i}]={crib_bytes[i]}({bit(crib_bytes[i])})"
                   f"  =  XR[{i}]={xr[i]}({bit(xr[i])})")
            panel_y = win_h - FOOTER_H + 6
            screen.blit(font_small.render(eq, True, (120, 0, 0)), (LEFT_MARGIN, panel_y))
            screen.blit(font_small.render(eq2, True, (0, 60, 140)), (LEFT_MARGIN, panel_y + 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


# ----------------------------------------------------------------------
# Embedded backup bytes (used if files are missing)
# ----------------------------------------------------------------------

_BACKUP_C1 = [
    125, 195, 250, 247, 246, 89, 111, 126, 189, 229, 133, 184, 67, 73, 90, 44, 23, 80, 12, 232,
    149, 10, 45, 201, 7, 191, 100, 98, 85, 252, 149, 93, 111, 79, 26, 174, 206, 164, 41, 80,
    8, 49, 92, 249, 38, 157, 187, 128, 244, 72, 158, 185, 51, 168, 99, 72, 28, 47, 209, 9,
    147, 251, 0, 210, 137, 148, 186, 190, 127, 160, 201, 147, 68, 168, 156, 196, 108, 203, 45, 105,
    5, 233, 67, 200, 68, 32, 40, 16, 122, 164, 114, 146, 168, 234, 190, 194, 127, 130, 46, 35,
    178, 188, 45, 72, 70, 177, 72, 244, 37, 119, 16, 77, 120, 145, 238, 165, 96, 97, 235, 91,
    144, 77, 58, 72, 53, 79, 63, 187, 172, 137, 35, 80, 191, 115, 229, 114, 214, 27, 185, 47,
    31, 156, 182, 162, 79, 22, 87, 133, 25, 158, 158, 114, 47, 251, 231, 71, 14, 135, 112, 53,
    62, 206, 103, 234, 39, 33, 172, 100, 254, 86, 241, 177, 64, 242, 223, 168, 230, 248, 197, 158,
    184, 65, 59, 176, 114, 128, 171, 19, 75, 44, 168, 37, 44, 125, 94, 249, 194, 29, 113, 61,
    244, 209, 55, 255, 249, 234, 158, 71, 156, 14, 207, 227, 140, 35, 52, 101, 65, 127, 91, 204,
    94, 54, 172, 227, 213, 1, 31, 207, 172, 75, 106, 131, 126, 175, 11, 2, 78, 53, 153, 144,
    84, 198, 143, 7, 7, 228, 238, 75, 230, 156, 19, 13, 63, 249, 163, 119, 205, 154, 242, 181,
    54, 254, 78, 95, 138, 40, 32, 195, 65, 132, 238, 137, 63, 179, 218, 3, 249, 43, 97, 121,
    32, 199, 54, 142, 86, 234, 93, 62, 215, 93, 139, 167, 240, 45, 213, 5, 123, 57, 155, 47,
    39, 25, 101, 64, 13, 79, 247, 146, 26, 215, 107, 92, 84, 211, 20, 86, 160, 28, 178, 187,
    245, 145, 74, 25, 223, 163, 249, 39, 111, 189, 129, 73, 160, 5, 218, 139, 78, 17, 100, 133,
    63, 126, 181, 11, 238, 90, 47, 114, 15, 10, 206, 130, 22, 78, 141, 205, 132, 46, 197, 41,
    215, 223, 0, 205, 197, 155, 212, 211, 226, 63, 89, 44, 209, 138, 22, 204, 158, 110, 121, 252,
    4, 58, 225, 175, 91, 246, 117, 214, 245, 42, 204, 190, 204, 27, 69, 79, 75, 40, 163, 140,
    201, 43, 112, 86, 106, 130, 51, 241, 168, 107, 9, 32, 237, 71, 112, 11, 46, 237, 113, 36,
    3, 162, 170, 199, 14, 254, 207, 142, 24, 149, 129, 133, 148, 33, 120, 145, 2, 50, 85, 54,
    36, 169, 81, 231, 200, 106, 50, 191, 6, 45, 136, 173, 197, 82, 234, 46, 38, 177, 120, 129,
    11, 73, 17, 102, 40, 47, 6, 200, 57, 20, 1, 33, 122, 242, 234, 120, 32, 125, 60, 188,
    78, 154, 198, 108, 25, 252, 102, 145, 154, 35, 163, 22, 7, 114, 247, 159, 22, 47, 214, 25,
    177, 159, 6, 2, 187, 130, 15, 30, 19, 41, 40, 4, 17, 47, 245, 34, 83, 85, 173, 7,
    237, 147, 138, 255, 81, 140, 181, 219, 177, 87, 191, 170, 33, 236, 235, 179, 95, 178, 238, 116,
    44, 180, 145, 238, 142, 187, 95, 203, 12, 174, 103, 39, 204, 48, 233, 58, 154, 48, 183, 172,
    254, 121, 41, 121, 18, 152, 90, 23, 82, 114, 126, 158, 91, 134, 182, 15, 63, 191, 173, 42,
    21, 221, 106, 243, 31, 28, 23, 109, 179, 137, 161, 112, 209, 154, 221, 209, 41, 13, 57, 168,
]

_BACKUP_C2 = [
    104, 207, 240, 187, 245, 67, 126, 104, 167, 166, 147, 253, 71, 83, 87, 36, 17, 74, 8, 224,
    149, 24, 45, 212, 76, 246, 96, 125, 20, 250, 136, 9, 101, 79, 73, 246, 139, 225, 68, 68,
    2, 116, 78, 166, 114, 136, 244, 143, 229, 69, 223, 224, 102, 236, 115, 14, 54, 6, 239, 52,
    211, 188, 106, 155, 142, 147, 255, 190, 112, 227, 194, 220, 84, 182, 129, 197, 106, 202, 59, 105,
    15, 245, 14, 203, 73, 59, 57, 84, 51, 163, 60, 221, 178, 231, 251, 150, 120, 128, 57, 112,
    164, 229, 126, 78, 66, 182, 0, 255, 45, 109, 30, 70, 36, 208, 202, 165, 106, 96, 174, 54,
    146, 86, 59, 78, 36, 74, 118, 146, 186, 222, 58, 79, 228, 32, 150, 83, 205, 21, 161, 63,
    93, 219, 197, 165, 79, 12, 25, 213, 20, 145, 148, 60, 25, 232, 174, 71, 28, 144, 109, 44,
    56, 200, 35, 171, 114, 44, 171, 45, 249, 95, 248, 253, 18, 246, 196, 237, 233, 229, 216, 210,
    164, 83, 105, 166, 110, 138, 174, 7, 67, 54, 166, 107, 62, 45, 29, 226, 216, 83, 99, 58,
    241, 216, 100, 171, 233, 231, 146, 76, 135, 77, 207, 225, 140, 48, 38, 108, 30, 110, 84, 223,
    69, 38, 175, 171, 132, 127, 90, 216, 173, 25, 108, 139, 57, 251, 20, 15, 7, 1, 158, 194,
    76, 202, 200, 7, 21, 226, 232, 75, 169, 200, 10, 16, 107, 243, 161, 119, 212, 156, 189, 181,
    49, 240, 79, 30, 137, 37, 52, 138, 27, 141, 242, 139, 58, 255, 132, 79, 204, 45, 36, 58,
    51, 223, 61, 146, 94, 164, 87, 113, 206, 74, 130, 167, 236, 121, 142, 121, 116, 51, 211, 108,
    56, 88, 121, 14, 12, 7, 235, 152, 29, 200, 34, 87, 65, 222, 71, 91, 189, 89, 230, 164,
    241, 194, 9, 5, 217, 184, 232, 116, 122, 239, 158, 78, 161, 5, 143, 217, 27, 67, 99, 204,
    51, 117, 162, 7, 185, 76, 53, 38, 6, 68, 212, 154, 12, 0, 154, 201, 139, 107, 198, 124,
    197, 214, 27, 142, 205, 131, 141, 146, 172, 90, 27, 114, 130, 168, 19, 219, 142, 38, 32, 185,
    63, 49, 225, 189, 87, 253, 107, 204, 188, 36, 209, 190, 219, 27, 8, 75, 79, 40, 247, 138,
    194, 102, 105, 93, 62, 132, 51, 243, 168, 122, 6, 63, 250, 2, 53, 15, 107, 185, 74, 116,
    12, 164, 228, 136, 91, 195, 200, 207, 27, 158, 129, 134, 150, 32, 54, 166, 28, 53, 70, 108,
    46, 189, 29, 245, 206, 97, 102, 188, 67, 43, 129, 165, 210, 75, 231, 47, 116, 229, 103, 141,
    22, 83, 17, 64, 1, 18, 90, 129, 27, 21, 64, 45, 110, 237, 163, 101, 38, 52, 44, 244,
    95, 210, 212, 112, 86, 238, 43, 210, 147, 115, 182, 3, 15, 115, 241, 149, 20, 47, 205, 24,
    254, 135, 82, 23, 180, 149, 74, 26, 85, 42, 40, 19, 90, 40, 189, 46, 29, 16, 183, 28,
    235, 155, 131, 162, 81, 190, 175, 209, 252, 3, 155, 178, 48, 240, 165, 175, 77, 251, 170, 22,
    62, 189, 132, 226, 219, 183, 12, 138, 4, 165, 43, 8, 209, 40, 251, 116, 211, 55, 242, 254,
    255, 104, 122, 108, 7, 146, 93, 17, 64, 114, 62, 199, 71, 200, 135, 68, 57, 191, 175, 33,
    75, 221, 110, 247, 15, 83, 24, 126, 242, 158, 181, 124, 198, 213, 205, 220, 96, 13, 101, 244,
]

if __name__ == "__main__":
    main()
