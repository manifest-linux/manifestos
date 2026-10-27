#!/usr/bin/env python3
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_art as art

PLUM = "#2B1438"


def pills(cx, y, size, members, anchor_center=True):
    gap = size * 0.5
    widths = [len(m["short"]) * size * 0.66 + size * 1.4 for m in members]
    total = sum(widths) + gap * (len(widths) - 1)
    x = cx - total / 2 if anchor_center else cx
    parts = []
    for width, m in zip(widths, members):
        height = size * 1.9
        parts.append(
            f'<rect x="{x:.1f}" y="{y - height / 2:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'rx="{height / 2:.1f}" fill="#FFFFFF" fill-opacity="0.95"/>'
        )
        parts.append(art.text(x + width / 2, y + size * 0.36, size, m["short"], anchor="middle", color=m["color"]))
        x += width + gap
    return "".join(parts)


def banner(data, colors, group):
    width, height = 2560, 800
    defs, body = art.background(width, height, group, random.Random("banner"), bokeh=18, sparkles=46)
    body += f'<g filter="url(#shadow)">{art.logo(440, 400, 290, colors, group, disk_opacity=0.95)}</g>'
    body += f'<g filter="url(#shadow)">{art.text(860, 380, 170, "ManifestOS")}</g>'
    body += art.text(866, 480, 56, "A fan-made Linux for manifest fans", weight=400, opacity=0.95)
    body += pills(866, 610, 40, data["members"], anchor_center=False)
    return art.svg_doc(width, height, body, defs)


def social_preview(data, colors, group):
    width, height = 1280, 640
    defs, body = art.background(width, height, group, random.Random("social"), bokeh=12, sparkles=30)
    body += f'<g filter="url(#shadow)">{art.logo(640, 200, 130, colors, group, disk_opacity=0.95)}</g>'
    body += f'<g filter="url(#shadow)">{art.text(640, 420, 96, "ManifestOS", anchor="middle")}</g>'
    body += art.text(640, 478, 32, "A fan-made Linux for manifest fans", weight=400, opacity=0.95, anchor="middle")
    body += pills(640, 560, 24, data["members"])
    return art.svg_doc(width, height, body, defs)


def avatar(colors, group):
    body = f'<rect width="1024" height="1024" rx="230" fill="{PLUM}"/>' + art.logo(512, 512, 400, colors, group)
    return art.svg_doc(1024, 1024, body)


def main():
    parser = argparse.ArgumentParser(description="Generate ManifestOS brand images for the README and GitHub")
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    data = json.loads((art.REPO / "data/members.json").read_text(encoding="utf-8"))
    colors = [m["color"] for m in data["members"]]
    group = data["group"]["color"]
    out = args.out
    plain = art.svg_doc(512, 512, art.logo(256, 256, 240, colors, group))
    white = art.svg_doc(512, 512, art.logo(256, 256, 240, [art.WHITE] * 6, art.WHITE, disk=art.WHITE, disk_opacity=0.18))
    art.write(out / "logo.svg", plain)
    art.write(out / "logo-white.svg", white)
    for size in (256, 512, 1024):
        art.render(plain, out / f"logo-{size}.png", size, size)
    art.render(avatar(colors, group), out / "avatar.png", 1024, 1024)
    art.render(banner(data, colors, group), out / "banner.png", 1280, 400)
    art.render(social_preview(data, colors, group), out / "social-preview.png", 1280, 640)


if __name__ == "__main__":
    main()
