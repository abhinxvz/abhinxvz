#!/usr/bin/env python3
"""Regenerate the repo-hosted fallback profile-card.svg and README.md.

The live, wall-clock-synced card can also be served on Cloudflare Pages / Workers
(see scripts/build_cf_function.py); this script keeps a static, self-animating copy
in the repo as an always-accessible card for GitHub.
"""
import os
import sys

# Ensure scripts dir is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cardlib

CARD_URL = os.environ.get(
    "CARD_URL",
    "https://raw.githubusercontent.com/abhinxvz/abhinxvz/main/profile-card.svg",
)
HEATMAP_URL = os.environ.get(
    "HEATMAP_URL",
    "https://raw.githubusercontent.com/abhinxvz/abhinxvz/main/heatmap.svg",
)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    readme_path = os.path.join(repo_root, "README.md")
    svg_path = os.path.join(repo_root, "profile-card.svg")

    ascii_art_sets = cardlib.load_ascii_art_sets(repo_root)

    headers = cardlib.make_headers(os.environ.get("GITHUB_TOKEN"))
    try:
        user = cardlib.get_user(headers)
        repos = cardlib.get_repos(headers)
        sections = cardlib.build_sections(user, repos, headers)
    except Exception as e:
        if os.path.exists(svg_path):
            print(f"Notice: GitHub API fetch failed ({e}). Preserving existing stats from SVG.")
            sections = cardlib.load_existing_sections(svg_path)
        else:
            raise
    svg = cardlib.build_svg_animated(ascii_art_sets, sections)

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated {svg_path}")

    # Generate animated heatmap SVG
    try:
        import generate_heatmap
        heatmap_path = os.path.join(repo_root, "heatmap.svg")
        heatmap_svg = generate_heatmap.generate_heatmap_svg()
        with open(heatmap_path, "w", encoding="utf-8") as f:
            f.write(heatmap_svg)
        print(f"Generated {heatmap_path}")
    except Exception as e:
        print(f"Notice: Heatmap generation failed ({e})")

    start_marker = "<!--STATS:START-->"
    end_marker = "<!--STATS:END-->"

    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            readme = f.read()
    else:
        readme = f"{start_marker}\n{end_marker}\n"

    if start_marker not in readme or end_marker not in readme:
        readme = f"{start_marker}\n{end_marker}\n"

    if "heatmap.svg" not in readme:
        heatmap_block = (
            f'<a href="https://github.com/{cardlib.USERNAME}"><img src="{HEATMAP_URL}" '
            'alt="abhinxvz contribution heatmap" width="100%" /></a>\n\n'
        )
        readme = heatmap_block + readme

    start_idx = readme.index(start_marker) + len(start_marker)
    end_idx = readme.index(end_marker)

    block = (
        f'<a href="https://abhinav-singh.tech"><img src="{CARD_URL}" alt="abhinxvz GitHub stats" '
        'width="100%" /></a>'
    )
    new_readme = readme[:start_idx] + "\n" + block + "\n" + readme[end_idx:]

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_readme)
    print(f"Updated {readme_path}")


if __name__ == "__main__":
    main()
