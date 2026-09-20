"""Render a short ecosystem preview GIF. Requires ffmpeg. Frames stay local."""
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ecosystem import simulate_ecosystem
W, H = 480, 480
PALETTE = [
    (126, 182, 255), (255, 139, 122), (111, 191, 163), (230, 193, 90),
    (201, 160, 255), (240, 163, 107), (143, 211, 255), (255, 179, 198),
]


def lerp(a, b, t):
    return int(a + (b - a) * t)


def put(pixels, x, y, color, alpha=1.0):
    if x < 0 or y < 0 or x >= W or y >= H:
        return
    i = (y * W + x) * 3
    if alpha >= 1:
        pixels[i:i + 3] = bytes(color)
        return
    pixels[i] = lerp(pixels[i], color[0], alpha)
    pixels[i + 1] = lerp(pixels[i + 1], color[1], alpha)
    pixels[i + 2] = lerp(pixels[i + 2], color[2], alpha)


def disc(pixels, cx, cy, radius, color, alpha=1.0):
    r = int(math.ceil(radius))
    r2 = radius * radius
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                put(pixels, x, y, color, alpha)


def line(pixels, x0, y0, x1, y1, color, alpha=0.85):
    steps = max(1, int(math.hypot(x1 - x0, y1 - y0)))
    for i in range(steps + 1):
        t = i / steps
        put(pixels, int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), color, alpha)


def triangle(pixels, x, y, heading, color):
    canvas_h = -heading
    pts = [(11, 0), (-7, 6), (-4, 0), (-7, -6)]
    world = []
    for px, py in pts:
        rx = px * math.cos(canvas_h) - py * math.sin(canvas_h)
        ry = px * math.sin(canvas_h) + py * math.cos(canvas_h)
        world.append((int(x + rx), int(y + ry)))
    xs = [p[0] for p in world]
    ys = [p[1] for p in world]
    for yy in range(min(ys), max(ys) + 1):
        hits = []
        for i, (ax, ay) in enumerate(world):
            bx, by = world[(i + 1) % len(world)]
            if (ay <= yy < by) or (by <= yy < ay):
                t = 0 if by == ay else (yy - ay) / (by - ay)
                hits.append(int(ax + t * (bx - ax)))
        hits.sort()
        for i in range(0, len(hits) - 1, 2):
            for xx in range(hits[i], hits[i + 1] + 1):
                put(pixels, xx, yy, color)


def write_ppm(path, pixels):
    path.write_bytes(b'P6\n%d %d\n255\n' % (W, H) + pixels)


def project(x, y, half):
    m = 18
    span = 2 * half + 2
    scale = min((W - 2 * m) / span, (H - 2 * m) / span)
    ox = (W - span * scale) / 2
    oy = (H - span * scale) / 2
    return int(ox + (x + half + 1) * scale), int(H - oy - (y + half + 1) * scale)


def render(output=None):
    output = Path(output or ROOT / 'docs' / 'preview.gif')
    result = simulate_ecosystem(
        ROOT / 'circuits' / 'dng13.json', 900, 7, turn_sign=-1, turn_gain=1,
        agents=8, patches=8, food_rate=1.35, aging_rate=0.85, repro_rate=1.55)
    frames = result['ticks'][120:860:8]
    half = min(14.0, result['rules']['map_half'])
    look = {'seed': ((106, 83, 64), 2), 'growing': ((122, 154, 74), 4),
            'mature': ((230, 193, 90), 6), 'cooldown': ((59, 66, 84), 2)}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for index, tick in enumerate(frames):
            pixels = bytearray([11, 13, 18]) * (W * H)
            for g in range(int(-half), int(half) + 1, 2):
                x0, y0 = project(g, -half, half)
                x1, y1 = project(g, half, half)
                line(pixels, x0, y0, x1, y1, (29, 36, 50), 0.55)
                x0, y0 = project(-half, g, half)
                x1, y1 = project(half, g, half)
                line(pixels, x0, y0, x1, y1, (29, 36, 50), 0.55)
            for patch in tick['patches']:
                color, radius = look[patch['stage']]
                px, py = project(patch['x'], patch['y'], half)
                disc(pixels, px, py, radius, color, 0.45 if patch['stage'] == 'cooldown' else 1)
            history = result['ticks'][max(0, tick['tick'] - 40):tick['tick'] + 1]
            for agent in tick['agents']:
                color = PALETTE[agent['id'] % len(PALETTE)]
                prev = None
                for step in history:
                    body = next((row for row in step['agents'] if row['id'] == agent['id']), None)
                    if not body:
                        continue
                    point = project(body['x'], body['y'], half)
                    if prev:
                        line(pixels, prev[0], prev[1], point[0], point[1], color, 0.35)
                    prev = point
            for corpse in tick['corpses']:
                px, py = project(corpse['x'], corpse['y'], half)
                disc(pixels, px, py, 4, (138, 133, 128), 0.5)
            for agent in tick['agents']:
                if not agent['alive'] and not agent['corpse']:
                    continue
                px, py = project(agent['x'], agent['y'], half)
                color = PALETTE[agent['id'] % len(PALETTE)]
                if agent['alive']:
                    triangle(pixels, px, py, agent['heading'], color)
                else:
                    disc(pixels, px, py, 4, color, 0.4)
            write_ppm(tmp / f'frame_{index:04d}.ppm', pixels)
        palette = tmp / 'palette.png'
        subprocess.check_call([
            'ffmpeg', '-y', '-framerate', '14', '-i', str(tmp / 'frame_%04d.ppm'),
            '-vf', 'palettegen=stats_mode=diff', str(palette),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call([
            'ffmpeg', '-y', '-framerate', '14', '-i', str(tmp / 'frame_%04d.ppm'),
            '-i', str(palette),
            '-lavfi', 'paletteuse=dither=bayer:bayer_scale=5',
            str(output),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f'wrote {output} ({output.stat().st_size} bytes), births {result["final"]["births"]}')
    return output


if __name__ == '__main__':
    render()
