#!/usr/bin/env python3
"""Generate an animated SVG heatmap matching the red ASCII terminal theme.

Faithfully implements the ascii.rest heatmap contribution calendar:
- Seed-based noise generation for realistic activity clusters
- Day-by-day filling in with weekly horizontal scrolling
- Red ASCII theme matching abhinxvz/profile-card.svg (#ff5f5f, #0d1117, etc.)
- SMIL discrete frame animation for seamless GitHub README rendering
"""
import math
import os
import sys

# Styling constants matching scripts/cardlib.py
USERNAME = "abhinxvz"
FONT_SIZE = 15
LINE_HEIGHT = 20
CHAR_WIDTH = 9.0  # FONT_SIZE * 0.6
WIDTH = 802
HEIGHT = 284
COLS = 66
ROWS = 12

BG_COLOR = "#0d1117"
BORDER_COLOR = "#30363d"
ART_COLOR = "#ff5f5f"        # Red ASCII grid blocks
HEADER_COLOR = "#ff3b3b"
LABEL_COLOR = "#ff8c69"      # Month labels
VALUE_COLOR = "#f2d0c9"      # Count summary
CONNECTOR_COLOR = "#c05656"  # Key labels
PROMPT_COLOR = "#8a4a4a"     # Prompt text & day labels
FONT_FAMILY = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"

WEEKS = 30
STEP = 0.5  # seconds per day
START = 20150  # today at t = 0, as days since 1970-01-01
LEVELS = "·░▒▓█"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DAYS = ["mon", "", "wed", "", "fri", "", ""]


def to_int32(x: int) -> int:
    x = x & 0xffffffff
    return x - 0x100000000 if x >= 0x80000000 else x


def imul(a: int, b: int) -> int:
    a = to_int32(a)
    b = to_int32(b)
    res = (a * b) & 0xffffffff
    return to_int32(res)


def mulberry32(a: int):
    a = to_int32(a)

    def rand():
        nonlocal a
        a = to_int32(a + 0x6d2b79f5)
        u_a = a & 0xffffffff
        t = imul(u_a ^ (u_a >> 15), 1 | u_a)
        u_t = t & 0xffffffff
        t = to_int32(to_int32(t + imul(u_t ^ (u_t >> 7), 61 | u_t)) ^ t)
        u_t = t & 0xffffffff
        res = (u_t ^ (u_t >> 14)) & 0xffffffff
        return res / 4294967296.0

    return rand


def month_of(z: int) -> int:
    doe = (((z + 719468) % 146097) + 146097) % 146097
    yoe = (doe - (doe // 1460) + (doe // 36524) - (doe // 146096)) // 365
    doy = doe - (365 * yoe + (yoe // 4) - (yoe // 100))
    mp = (5 * doy + 2) // 153
    return (mp + 2) % 12


def create_heatmap_renderer(unit: str = "contributions", seed: int = 7):
    left = 6

    def hash_fn(d: int, k: int):
        return mulberry32(to_int32(seed * 7919 + d * 104729 + k * 15485863))()

    def busy(d: int):
        w = d / 7.0 / 3.0
        i = int(w)
        f = w - i
        e = f * f * (3 - 2 * f)
        return hash_fn(i, 9) * (1 - e) + hash_fn(i + 1, 9) * e

    def count(d: int):
        weekend = ((d + 3) % 7) >= 5
        a = (0.08 + 1.05 * (busy(d) ** 1.4)) * (0.3 if weekend else 1.0)
        if hash_fn(d, 1) > a + 0.08:
            return 0
        return max(1, round(a * (3 + 14 * hash_fn(d, 2))))

    def level(n: int) -> int:
        return 0 if n == 0 else 1 if n < 4 else 2 if n < 8 else 3 if n < 12 else 4

    def render(t: float):
        today = START + int(t / STEP)
        monday = today - ((today + 3) % 7)
        first = monday - (WEEKS - 1) * 7
        grid = [list(DAYS[r].ljust(left - 2) + "  ") for r in range(7)]
        total = 0
        for w in range(WEEKS):
            for r in range(7):
                d = first + w * 7 + r
                ch = " "
                if d <= today:
                    n = count(d)
                    total += n
                    ch = LEVELS[level(n)]
                grid[r].extend([ch, " "])

        head = [" "] * COLS
        free = 0
        for w in range(WEEKS):
            m = month_of(first + w * 7)
            if w > 0 and m == month_of(first + (w - 1) * 7):
                continue
            x = left + w * 2
            if x < free or x + 3 > COLS:
                continue
            if w == 0 and month_of(first + 14) != m:
                continue
            for k in range(3):
                head[x + k] = MONTHS[m][k]
            free = x + 5

        lines = ["", "".join(head)]
        for r in range(7):
            lines.append("".join(grid[r]))
        lines.append("")
        sum_str = f"{total:,} {unit} in the last {WEEKS} weeks"
        key = "less " + " ".join(list(LEVELS)) + " more"
        lines.append(" " * left + sum_str.ljust(COLS - left - len(key) - 1) + key)
        lines.append("")
        return [l[:COLS].ljust(COLS) for l in lines], total

    return render


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_heatmap_svg(
    unit: str = "contributions",
    seed: int = 7,
    num_frames: int = 14,
    step_duration: float = 0.5,
) -> str:
    """Generate the animated SVG heatmap string."""
    render = create_heatmap_renderer(unit=unit, seed=seed)
    total_dur = num_frames * step_duration
    x_offset = round((WIDTH - COLS * CHAR_WIDTH) / 2)  # 104
    grid_x = x_offset + round(6 * CHAR_WIDTH)          # 158

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT_FAMILY}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="12" fill="{BG_COLOR}" stroke="{BORDER_COLOR}"/>',
        f'<text x="20" y="39.0" font-size="{FONT_SIZE}" fill="{PROMPT_COLOR}" '
        f'xml:space="preserve">{USERNAME}@github:~$ gitfetch --heatmap</text>',
        f'<line x1="20" y1="47.0" x2="{WIDTH - 20}.0" y2="47.0" stroke="{BORDER_COLOR}"/>',
    ]

    for frame_idx in range(num_frames):
        lines, total = render(frame_idx * step_duration)
        values = ["1" if k == frame_idx else "0" for k in range(num_frames)] + ["0"]
        key_times = [k / num_frames for k in range(num_frames + 1)]
        opacity = "1" if frame_idx == 0 else "0"

        frame_parts = [f'<g opacity="{opacity}">']

        # Line 1: Month labels
        frame_parts.append(
            f'<text x="{x_offset}" y="74.0" font-size="{FONT_SIZE}" fill="{LABEL_COLOR}" '
            f'xml:space="preserve">{escape_xml(lines[1])}</text>'
        )

        # Lines 2 to 8: Days Mon-Sun
        y_pos = 94.0
        for r in range(2, 9):
            row_str = lines[r]
            day_label = escape_xml(row_str[:6])
            grid_cells = escape_xml(row_str[6:])
            frame_parts.append(
                f'<text x="{x_offset}" y="{y_pos:.1f}" font-size="{FONT_SIZE}" fill="{PROMPT_COLOR}" '
                f'xml:space="preserve">{day_label}</text>'
            )
            frame_parts.append(
                f'<text x="{grid_x}" y="{y_pos:.1f}" font-size="{FONT_SIZE}" fill="{ART_COLOR}" '
                f'xml:space="preserve">{grid_cells}</text>'
            )
            y_pos += 20.0

        # Summary line
        sum_str = f"{total:,} {unit} in the last {WEEKS} weeks"
        key_str = "less · ░ ▒ ▓ █ more"
        key_x = x_offset + round((COLS - len(key_str)) * CHAR_WIDTH)

        frame_parts.append(
            f'<text x="{grid_x}" y="246.0" font-size="{FONT_SIZE}" fill="{VALUE_COLOR}" '
            f'xml:space="preserve">{escape_xml(sum_str)}</text>'
        )
        frame_parts.append(
            f'<text x="{key_x}" y="246.0" font-size="{FONT_SIZE}" fill="{CONNECTOR_COLOR}" '
            f'xml:space="preserve">less </text>'
        )
        frame_parts.append(
            f'<text x="{key_x + round(5 * CHAR_WIDTH)}" y="246.0" font-size="{FONT_SIZE}" '
            f'fill="{ART_COLOR}" xml:space="preserve">· ░ ▒ ▓ █</text>'
        )
        frame_parts.append(
            f'<text x="{key_x + round(15 * CHAR_WIDTH) + 3}" y="246.0" font-size="{FONT_SIZE}" '
            f'fill="{CONNECTOR_COLOR}">more</text>'
        )

        if num_frames > 1:
            frame_parts.append(
                f'<animate attributeName="opacity" calcMode="discrete" '
                f'begin="0s" dur="{total_dur:.1f}s" repeatCount="indefinite" '
                f'keyTimes="{";".join(f"{t:.4f}" for t in key_times)}" '
                f'values="{";".join(values)}"/>'
            )

        frame_parts.append("</g>")
        svg.extend(frame_parts)

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = os.path.join(repo_root, "heatmap.svg")

    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    svg_content = generate_heatmap_svg()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {output_path} ({len(svg_content)} bytes)")


if __name__ == "__main__":
    main()
