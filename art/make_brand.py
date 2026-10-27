#!/usr/bin/env python3
import argparse
import json
import random
import shutil
import subprocess
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


def portrait_svg(color, colors, highlight, kicker, title, subtitle, seed, party=False):
    width, height = 1080, 1920
    rnd = random.Random(seed)
    defs, body = art.background(width, height, color, rnd, bokeh=22, sparkles=50)
    if party:
        body += art.confetti(width, height, colors, rnd, count=140)
    if highlight is not None:
        colors = [c if i == highlight else art.mix(c, art.WHITE, 0.6) for i, c in enumerate(colors)]
    body += f'<g filter="url(#shadow)">{art.logo(540, 620, 330, colors, color, disk_opacity=0.94)}</g>'
    body += art.text(540, 1120, 58, kicker, weight=400, opacity=0.9, anchor="middle", spacing=4)
    title_size = min(220, 960 / (len(title) * 0.62))
    body += f'<g filter="url(#shadow)">{art.text(540, 1120 + title_size * 1.05, title_size, title, anchor="middle")}</g>'
    subtitle_size = min(46, 980 / (max(len(subtitle), 1) * 0.56))
    body += art.text(540, 1120 + title_size * 1.05 + 110, subtitle_size, subtitle, weight=400, opacity=0.9, anchor="middle")
    return art.svg_doc(width, height, body, defs)


def render_jpeg(svg, out, width, height):
    png = out.with_suffix(".png")
    art.render(svg, png, width, height)
    subprocess.run(["convert", str(png), "-quality", "82", str(out)], check=True)
    png.unlink()


def demo(out, data, colors, group):
    wallpapers = out / "wallpapers"
    names = " · ".join(m["short"] for m in data["members"])
    render_jpeg(art.wallpaper_svg(2560, 1440, group, colors, None, "ManifestOS", "manifest", names, seed="Group"), wallpapers / "group.jpg", 1600, 900)
    render_jpeg(portrait_svg(group, colors, None, "ManifestOS", "manifest", names, seed="Group"), wallpapers / "group-portrait.jpg", 720, 1280)
    for index, m in enumerate(data["members"]):
        render_jpeg(art.wallpaper_svg(2560, 1440, m["color"], colors, index, "manifest", m["short"], m["name"], seed=m["id"].capitalize()), wallpapers / f"{m['id']}.jpg", 1600, 900)
        render_jpeg(art.wallpaper_svg(2560, 1440, m["color"], colors, index, "Happy Birthday", m["short"], "Wishing you the happiest day", seed=f"party-{m['id']}", party=True), wallpapers / f"{m['id']}-birthday.jpg", 1600, 900)
        render_jpeg(portrait_svg(m["color"], colors, index, "manifest", m["short"], m["name"], seed=m["id"].capitalize()), wallpapers / f"{m['id']}-portrait.jpg", 720, 1280)
        render_jpeg(portrait_svg(m["color"], colors, index, "Happy Birthday", m["short"], "Wishing you the happiest day", seed=f"party-{m['id']}", party=True), wallpapers / f"{m['id']}-birthday-portrait.jpg", 720, 1280)
    (out / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy(art.REPO / "data/members.json", out / "data/members.json")
    shutil.copy(art.REPO / "data/i18n/tr.json", out / "data/tr.json")


def main():
    parser = argparse.ArgumentParser(description="Generate ManifestOS brand images for the README and GitHub")
    parser.add_argument("out", type=Path)
    parser.add_argument("--demo", type=Path, help="also build wallpapers and data for the web demo here")
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
    if args.demo:
        demo(args.demo, data, colors, group)


if __name__ == "__main__":
    main()
