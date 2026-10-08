#!/usr/bin/env python3
"""Generate a stable SVG heatmap using real GitHub contribution data.

- Fetches real contribution calendar for abhinxvz from GitHub
- Formats 30 weeks across (Mon-Sun) in 66 columns matching the ASCII style
- Styled in the red ASCII theme matching profile-card.svg (#ff5f5f, #0d1117, etc.)
- Completely stable: no fluctuating numbers or unstable animation
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta

USERNAME = "abhinxvz"
FONT_SIZE = 15
LINE_HEIGHT = 20
CHAR_WIDTH = 9.0  # FONT_SIZE * 0.6
WIDTH = 802
HEIGHT = 284
COLS = 66
WEEKS = 30
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

LEVELS = "·░▒▓█"
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
DAYS = ["mon", "", "wed", "", "fri", "", ""]


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fetch_github_contributions(username: str = USERNAME, token: str = None) -> dict:
    """Fetch user's actual GitHub contribution history from GitHub."""
    url = f"https://github.com/users/{username}/contributions"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; GithubHeatmap/1.0)"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8")

    tds = re.findall(r'<td[^>]*class="[^"]*ContributionCalendar-day[^"]*"[^>]*>', html)
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', html))

    calendar_days = {}
    for td in tds:
        date_m = re.search(r'data-date="([^"]+)"', td)
        level_m = re.search(r'data-level="([^"]+)"', td)
        id_m = re.search(r'id="([^"]+)"', td)
        if not (date_m and level_m and id_m):
            continue

        date_str = date_m.group(1)
        level = int(level_m.group(1))
        d_id = id_m.group(1)

        tip = tips.get(d_id, "")
        count = 0
        c_m = re.search(r"(\d+)\s+contribution", tip)
        if c_m:
            count = int(c_m.group(1))

        calendar_days[date_str] = {"level": level, "count": count}

    return calendar_days


def generate_heatmap_svg(
    username: str = USERNAME,
    token: str = None,
    cached_svg_path: str = None,
) -> str:
    """Generate the stable SVG heatmap string from real GitHub data."""
    try:
        calendar_days = fetch_github_contributions(username, token=token)
    except Exception as e:
        print(f"Notice: Failed to fetch live contributions ({e})", file=sys.stderr)
        if cached_svg_path and os.path.exists(cached_svg_path):
            with open(cached_svg_path, "r", encoding="utf-8") as f:
                return f.read()
        raise

    if not calendar_days:
        raise ValueError("No contribution days found from GitHub")

    all_dates = sorted(calendar_days.keys())
    today = datetime.strptime(all_dates[-1], "%Y-%m-%d").date()

    # Align to current Monday through Sunday
    monday_this_week = today - timedelta(days=today.weekday())
    first_monday = monday_this_week - timedelta(weeks=WEEKS - 1)

    left = 6
    grid = [list(DAYS[r].ljust(left - 2) + "  ") for r in range(7)]
    total_30_weeks = 0

    for w in range(WEEKS):
        for r in range(7):
            day_date = first_monday + timedelta(days=w * 7 + r)
            day_key = day_date.strftime("%Y-%m-%d")
            ch = " "
            if day_date <= today:
                data = calendar_days.get(day_key, {"level": 0, "count": 0})
                total_30_weeks += data["count"]
                ch = LEVELS[data["level"]]
            grid[r].extend([ch, " "])

    # Build month header labels
    head = [" "] * COLS
    free = 0
    for w in range(WEEKS):
        week_start = first_monday + timedelta(weeks=w)
        m = week_start.month - 1
        if w > 0:
            prev_m = (first_monday + timedelta(weeks=w - 1)).month - 1
            if m == prev_m:
                continue
        x = left + w * 2
        if x < free or x + 3 > COLS:
            continue
        for k in range(3):
            head[x + k] = MONTHS[m][k]
        free = x + 5

    head_str = "".join(head)
    sum_str = f"{total_30_weeks:,} contributions in the last {WEEKS} weeks"

    x_offset = round((WIDTH - COLS * CHAR_WIDTH) / 2)  # 104
    grid_x = x_offset + round(6 * CHAR_WIDTH)          # 158
    key_x = 540

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" font-family="{FONT_FAMILY}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="12" fill="{BG_COLOR}" stroke="{BORDER_COLOR}"/>',
        f'<text x="20" y="39.0" font-size="{FONT_SIZE}" fill="{PROMPT_COLOR}" '
        f'xml:space="preserve">{username}@github:~$ gitfetch --heatmap</text>',
        f'<line x1="20" y1="47.0" x2="{WIDTH - 20}.0" y2="47.0" stroke="{BORDER_COLOR}"/>',
        f'<text x="{x_offset}" y="74.0" font-size="{FONT_SIZE}" fill="{LABEL_COLOR}" '
        f'xml:space="preserve">{escape_xml(head_str)}</text>',
    ]

    y_pos = 94.0
    for r in range(7):
        row_str = "".join(grid[r])
        day_label = escape_xml(row_str[:6])
        grid_cells = escape_xml(row_str[6:])
        svg.append(
            f'<text x="{x_offset}" y="{y_pos:.1f}" font-size="{FONT_SIZE}" fill="{PROMPT_COLOR}" '
            f'xml:space="preserve">{day_label}</text>'
        )
        svg.append(
            f'<text x="{grid_x}" y="{y_pos:.1f}" font-size="{FONT_SIZE}" fill="{ART_COLOR}" '
            f'xml:space="preserve">{grid_cells}</text>'
        )
        y_pos += 20.0

    svg.append(
        f'<text x="{grid_x}" y="246.0" font-size="{FONT_SIZE}" fill="{VALUE_COLOR}" '
        f'xml:space="preserve">{escape_xml(sum_str)}</text>'
    )
    svg.append(
        f'<text x="{key_x}" y="246.0" font-size="{FONT_SIZE}" fill="{CONNECTOR_COLOR}" '
        f'xml:space="preserve">less </text>'
    )
    svg.append(
        f'<text x="{key_x + round(5 * CHAR_WIDTH)}" y="246.0" font-size="{FONT_SIZE}" '
        f'fill="{ART_COLOR}" xml:space="preserve">· ░ ▒ ▓ █</text>'
    )
    svg.append(
        f'<text x="{key_x + round(15 * CHAR_WIDTH) + 3}" y="246.0" font-size="{FONT_SIZE}" '
        f'fill="{CONNECTOR_COLOR}">more</text>'
    )
    svg.append("</svg>")

    return "\n".join(svg)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    output_path = os.path.join(repo_root, "heatmap.svg")

    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    token = os.environ.get("GITHUB_TOKEN")
    svg_content = generate_heatmap_svg(
        username=USERNAME,
        token=token,
        cached_svg_path=output_path,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {output_path} ({len(svg_content)} bytes)")


if __name__ == "__main__":
    main()
