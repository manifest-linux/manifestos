#!/usr/bin/env python3
import argparse
import configparser
import io
import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages" / "manifestos-apps" / "usr" / "lib" / "manifestos"))

import manifestos_common as mc

PLUM = "#2B1438"
PLUM_LIGHT = "#5A1F4F"
NIGHT_TINT = "#3A1F47"
INK = "#1A0B24"
WHITE = "#FFFFFF"
FONT = "Comfortaa, 'Noto Sans', sans-serif"
BREEZE_BLUE = "61,174,233"
BREEZE_BLUE_LIGHT = "163,212,250"
BREEZE_LINKS = ("41,128,185", "29,153,243")

TINTS_DAY = {
    "Colors:Window": 0.07,
    "Colors:Header": 0.10,
    "Colors:Header][Inactive": 0.08,
    "Colors:Button": 0.04,
    "Colors:Tooltip": 0.05,
    "Colors:View": 0.02,
}
TINTS_NIGHT = {
    "Colors:Window": 0.30,
    "Colors:Header": 0.34,
    "Colors:Header][Inactive": 0.30,
    "Colors:Button": 0.26,
    "Colors:Tooltip": 0.30,
    "Colors:View": 0.22,
    "Colors:Complementary": 0.30,
}

SLIDES = [
    ("Welcome to ManifestOS", "A fan-made Linux for manifest fans"),
    ("Pick your bias", "Your whole desktop changes to her color"),
    ("Manifest Hub", "Members, videos, music and links in one place"),
    ("Never miss a birthday", "Reminders and a countdown widget on your desktop"),
    ("Unofficial fan project", "Not affiliated with manifest or Hypers New Media"),
]


def mix(a, b, t):
    ca, cb = mc.hex_rgb(a), mc.hex_rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def rgb_csv(color):
    return ",".join(str(v) for v in mc.hex_rgb(color))


def csv_hex(value):
    parts = [int(v) for v in value.split(",")[:3]]
    return "#" + "".join(f"{v:02X}" for v in parts)


def svg_doc(width, height, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><defs>{defs}</defs>{body}</svg>'
    )


def ring(cx, cy, outer, inner, colors, opacities=None, gap=4.0):
    paths = []
    for i, color in enumerate(colors):
        a0 = math.radians(-90 + i * 60 + gap / 2)
        a1 = math.radians(-90 + (i + 1) * 60 - gap / 2)
        ox0, oy0 = cx + outer * math.cos(a0), cy + outer * math.sin(a0)
        ox1, oy1 = cx + outer * math.cos(a1), cy + outer * math.sin(a1)
        ix0, iy0 = cx + inner * math.cos(a0), cy + inner * math.sin(a0)
        ix1, iy1 = cx + inner * math.cos(a1), cy + inner * math.sin(a1)
        opacity = 1 if opacities is None else opacities[i]
        paths.append(
            f'<path d="M{ox0:.2f},{oy0:.2f} A{outer:.2f},{outer:.2f} 0 0 1 {ox1:.2f},{oy1:.2f} '
            f'L{ix1:.2f},{iy1:.2f} A{inner:.2f},{inner:.2f} 0 0 0 {ix0:.2f},{iy0:.2f} Z" '
            f'fill="{color}" fill-opacity="{opacity}"/>'
        )
    return "".join(paths)


def heart(cx, cy, size, color, opacity=1.0):
    s = size
    y = cy + 0.08 * s
    d = (
        f"M{cx:.2f},{y + 0.42 * s:.2f} "
        f"C{cx - 1.05 * s:.2f},{y - 0.20 * s:.2f} {cx - 0.55 * s:.2f},{y - 0.95 * s:.2f} {cx:.2f},{y - 0.42 * s:.2f} "
        f"C{cx + 0.55 * s:.2f},{y - 0.95 * s:.2f} {cx + 1.05 * s:.2f},{y - 0.20 * s:.2f} {cx:.2f},{y + 0.42 * s:.2f} Z"
    )
    return f'<path d="{d}" fill="{color}" fill-opacity="{opacity}"/>'


def logo(cx, cy, radius, colors, heart_color, disk=WHITE, disk_opacity=1.0, opacities=None):
    return (
        ring(cx, cy, radius, radius * 0.72, colors, opacities)
        + f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius * 0.62:.2f}" fill="{disk}" fill-opacity="{disk_opacity}"/>'
        + heart(cx, cy, radius * 0.40, heart_color)
    )


def sparkle(x, y, size, opacity):
    s, t = size, size * 0.22
    d = f"M{x},{y - s} L{x + t},{y - t} L{x + s},{y} L{x + t},{y + t} L{x},{y + s} L{x - t},{y + t} L{x - s},{y} L{x - t},{y - t} Z"
    return f'<path d="{d}" fill="{WHITE}" fill-opacity="{opacity:.2f}"/>'


def text(x, y, size, content, weight=700, opacity=1.0, anchor="start", color=WHITE, spacing=0, extra=""):
    content = content.replace("&", "&amp;").replace("<", "&lt;")
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size:.1f}" font-weight="{weight}" '
        f'fill="{color}" fill-opacity="{opacity}" text-anchor="{anchor}" letter-spacing="{spacing}" {extra}>{content}</text>'
    )


def background(width, height, color, rnd, bokeh=26, sparkles=48):
    top, bottom = mix(color, WHITE, 0.45), mix(color, INK, 0.55)
    defs = (
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{top}"/>'
        f'<stop offset="0.55" stop-color="{color}"/><stop offset="1" stop-color="{bottom}"/></linearGradient>'
        '<radialGradient id="glow"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.5"/>'
        '<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>'
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">'
        '<feDropShadow dx="0" dy="6" stdDeviation="12" flood-color="#000000" flood-opacity="0.22"/></filter>'
    )
    body = [f'<rect width="{width}" height="{height}" fill="url(#bg)"/>']
    body.append(f'<ellipse cx="{width * 0.72:.0f}" cy="{height * 0.45:.0f}" rx="{width * 0.34:.0f}" ry="{height * 0.55:.0f}" fill="url(#glow)"/>')
    for _ in range(bokeh):
        r = rnd.uniform(0.02, 0.15) * height
        body.append(
            f'<circle cx="{rnd.uniform(0, width):.0f}" cy="{rnd.uniform(0, height):.0f}" r="{r:.0f}" '
            f'fill="{WHITE}" fill-opacity="{rnd.uniform(0.04, 0.12):.2f}"/>'
        )
    for _ in range(sparkles):
        body.append(sparkle(rnd.uniform(0, width), rnd.uniform(0, height), rnd.uniform(0.004, 0.015) * height, rnd.uniform(0.3, 0.9)))
    return defs, "".join(body)


def confetti(width, height, colors, rnd, count=110):
    pieces = []
    for _ in range(count):
        w, h = rnd.uniform(0.006, 0.014) * height, rnd.uniform(0.012, 0.03) * height
        x, y = rnd.uniform(0, width), rnd.uniform(0, height)
        pieces.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{w / 3:.0f}" fill="{rnd.choice(colors + [WHITE])}" '
            f'fill-opacity="0.9" transform="rotate({rnd.uniform(0, 360):.0f} {x:.0f} {y:.0f})"/>'
        )
    return "".join(pieces)


def wallpaper_svg(width, height, color, colors, highlight, kicker, title, subtitle, seed, party=False):
    rnd = random.Random(seed)
    defs, body = background(width, height, color, rnd)
    if party:
        body += confetti(width, height, colors, rnd)
    if highlight is not None:
        colors = [c if i == highlight else mix(c, WHITE, 0.6) for i, c in enumerate(colors)]
    radius = height * 0.27
    body += f'<g filter="url(#shadow)">{logo(width * 0.72, height * 0.46, radius, colors, color, disk_opacity=0.94)}</g>'
    x, y = width * 0.08, height * 0.42
    body += text(x, y, height * 0.05, kicker, weight=400, opacity=0.9, spacing=height * 0.004)
    body += f'<g filter="url(#shadow)">{text(x, y + height * 0.19, height * 0.17, title)}</g>'
    body += text(x, y + height * 0.28, height * 0.036, subtitle, weight=400, opacity=0.9)
    return svg_doc(width, height, body, defs)


def render(svg, out, width=None, height=None):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False, encoding="utf-8") as handle:
        handle.write(svg)
        source = handle.name
    args = ["rsvg-convert", "-o", str(out)]
    if width:
        args += ["-w", str(width)]
    if height:
        args += ["-h", str(height)]
    subprocess.run(args + [source], check=True)
    os.unlink(source)


def write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_logos(out, colors, group_color):
    plain = svg_doc(512, 512, logo(256, 256, 240, colors, group_color))
    white = svg_doc(512, 512, logo(256, 256, 240, [WHITE] * 6, WHITE, disk=WHITE, disk_opacity=0.18))
    write(out / "usr/share/manifestos/logo.svg", plain)
    write(out / "usr/share/manifestos/logo-white.svg", white)
    write(out / "usr/share/icons/hicolor/scalable/apps/manifestos.svg", plain)
    hub = svg_doc(512, 512, f'<rect x="16" y="16" width="480" height="480" rx="120" fill="{PLUM}"/>' + logo(256, 256, 200, colors, group_color))
    write(out / "usr/share/icons/hicolor/scalable/apps/manifest-hub.svg", hub)
    for size in (48, 128, 256):
        render(plain, out / f"usr/share/icons/hicolor/{size}x{size}/apps/manifestos.png", size, size)
        render(hub, out / f"usr/share/icons/hicolor/{size}x{size}/apps/manifest-hub.png", size, size)
    write(out / "usr/share/plasma/look-and-feel/org.manifestos.desktop/contents/splash/images/logo.svg", white)
    write(
        out / "usr/share/plasma/look-and-feel/org.manifestos.desktop/contents/splash/colors.js",
        ".pragma library\n\nvar dots = " + json.dumps(colors) + ";\n",
    )


def make_wallpapers(out, data, colors):
    group = data["group"]
    entries = [("Group", group["color"], None, "ManifestOS", "manifest", " · ".join(m["short"] for m in data["members"]))]
    for index, m in enumerate(data["members"]):
        entries.append((m["id"].capitalize(), m["color"], index, "manifest", m["short"], m["name"]))
    lockscreen = out / "usr/share/manifestos/lockscreen"
    lockscreen.mkdir(parents=True, exist_ok=True)
    for key, color, highlight, kicker, title, subtitle in entries:
        package = out / f"usr/share/wallpapers/ManifestOS-{key}"
        svg = wallpaper_svg(2560, 1440, color, colors, highlight, kicker, title, subtitle, seed=key)
        image = package / "contents/images" / f"{mc.WALLPAPER_SIZE}.png"
        render(svg, image)
        render(svg, package / "contents/screenshot.png", 400, 225)
        metadata = {"KPlugin": {"Authors": [{"Name": "ManifestOS"}], "Id": f"ManifestOS-{key}", "License": "CC-BY-SA-4.0", "Name": f"ManifestOS {title}"}}
        write(package / "metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        link = lockscreen / f"{key.lower()}.png"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(os.path.relpath(image, lockscreen))
    for index, m in enumerate(data["members"]):
        svg = wallpaper_svg(2560, 1440, m["color"], colors, index, "Happy Birthday", m["short"], "Wishing you the happiest day", seed=f"party-{m['id']}", party=True)
        render(svg, out / f"usr/share/manifestos/birthday/{m['id']}.png")


def make_plymouth(out, colors, group_color):
    theme = out / "usr/share/plymouth/themes/manifestos"
    render(svg_doc(512, 512, logo(256, 256, 240, colors, group_color)), theme / "logo.png", 200, 200)
    for index, color in enumerate(colors):
        render(svg_doc(32, 32, f'<circle cx="16" cy="16" r="14" fill="{color}"/>'), theme / f"dot{index}.png", 18, 18)
    render(svg_doc(420, 56, f'<rect width="420" height="56" rx="28" fill="{WHITE}" fill-opacity="0.16"/>'), theme / "box.png")


def nine_slice(theme, color, size=12):
    r = size
    pieces = {
        "nw": f'<path d="M{r},{r} L0,{r} A{r},{r} 0 0 1 {r},0 Z" fill="{color}"/>',
        "ne": f'<path d="M0,{r} L0,0 A{r},{r} 0 0 1 {r},{r} Z" fill="{color}"/>',
        "sw": f'<path d="M{r},0 L0,0 A{r},{r} 0 0 0 {r},{r} Z" fill="{color}"/>',
        "se": f'<path d="M0,0 L{r},0 A{r},{r} 0 0 1 0,{r} Z" fill="{color}"/>',
    }
    for name in ("n", "s", "e", "w", "c"):
        pieces[name] = f'<rect width="{r}" height="{r}" fill="{color}"/>'
    for name, body in pieces.items():
        render(svg_doc(r, r, body), theme / f"select_{name}.png")


def make_grub(out, colors, group_color):
    theme = out / "usr/share/grub/themes/manifestos"
    rnd = random.Random("grub")
    defs, body = background(1920, 1080, PLUM_LIGHT, rnd, bokeh=18, sparkles=30)
    body += logo(960, 300, 150, colors, group_color, disk_opacity=0.95)
    body += text(960, 520, 64, "ManifestOS", anchor="middle")
    render(svg_doc(1920, 1080, body, defs), theme / "background.png")
    nine_slice(theme, mix(group_color, WHITE, 0.1))
    mkfont = shutil.which("grub-mkfont")
    if not mkfont:
        print("grub-mkfont not found, skipping GRUB fonts", file=sys.stderr)
        return
    for style, size in (("Regular", 16), ("Regular", 20), ("Bold", 20)):
        font = subprocess.run(["fc-match", "-f", "%{file}", f"Comfortaa:style={style}"], capture_output=True, text=True, check=True).stdout
        subprocess.run([mkfont, "-s", str(size), "-n", f"Manifest {style} {size}", "-o", str(theme / f"manifest-{style.lower()}-{size}.pf2"), font], check=True)


def make_calamares(out, colors, group_color):
    branding = out / "etc/calamares/branding/manifestos"
    render(svg_doc(512, 512, logo(256, 256, 240, colors, group_color)), branding / "logo.png", 128, 128)
    rnd = random.Random("welcome")
    defs, body = background(1040, 600, group_color, rnd, bokeh=10, sparkles=20)
    body += logo(520, 250, 150, colors, group_color, disk_opacity=0.95)
    body += text(520, 500, 54, "Welcome to ManifestOS", anchor="middle")
    render(svg_doc(1040, 600, body, defs), branding / "welcome.png", 520, 300)
    slide_colors = [group_color] + colors
    for index, (title, subtitle) in enumerate(SLIDES, start=1):
        color = slide_colors[(index - 1) % len(slide_colors)]
        defs, body = background(1600, 900, color, random.Random(f"slide{index}"), bokeh=14, sparkles=26)
        body += logo(1200, 450, 230, colors, color, disk_opacity=0.94)
        body += text(110, 420, 84, title)
        body += text(110, 500, 40, subtitle, weight=400, opacity=0.92)
        render(svg_doc(1600, 900, body, defs), branding / f"slide{index}.png", 800, 450)


def make_preview(out, colors, group_color):
    svg = wallpaper_svg(2560, 1440, group_color, colors, None, "ManifestOS", "manifest", "", seed="Group")
    bar = (
        '<rect x="0" y="1340" width="2560" height="100" fill="#FFFFFF" fill-opacity="0.75"/>'
        + "".join(f'<rect x="{1080 + i * 70}" y="1362" width="56" height="56" rx="14" fill="{c}"/>' for i, c in enumerate([PLUM] + colors))
    )
    svg = svg.replace("</svg>", bar + "</svg>")
    render(svg, out / "usr/share/plasma/look-and-feel/org.manifestos.desktop/contents/previews/preview.png", 600, 338)


def read_scheme(path):
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read(path, encoding="utf-8")
    return parser


def tint_scheme(parser, accent, tint, tints, name, scheme_id):
    accent_csv = rgb_csv(accent)
    replacements = {
        BREEZE_BLUE: accent_csv,
        BREEZE_BLUE_LIGHT: rgb_csv(mix(accent, WHITE, 0.55)),
    }
    for link in BREEZE_LINKS:
        replacements[link] = rgb_csv(mix(accent, INK, 0.15))
    for section in parser.sections():
        for key, value in parser.items(section):
            if value in replacements:
                parser.set(section, key, replacements[value])
        factor = tints.get(section)
        if factor:
            for key in ("BackgroundNormal", "BackgroundAlternate"):
                if parser.has_option(section, key):
                    parser.set(section, key, rgb_csv(mix(csv_hex(parser.get(section, key)), tint, factor)))
    if parser.has_section("WM"):
        factor = tints.get("Colors:Header", 0)
        for key in ("activeBackground", "activeBlend", "inactiveBackground", "inactiveBlend"):
            if parser.has_option("WM", key):
                parser.set("WM", key, rgb_csv(mix(csv_hex(parser.get("WM", key)), tint, factor)))
    for key in list(parser["General"].keys()):
        if key.startswith("Name["):
            parser.remove_option("General", key)
    parser.set("General", "ColorScheme", scheme_id)
    parser.set("General", "Name", name)
    return parser


def dump(parser):
    buffer = io.StringIO()
    parser.write(buffer, space_around_delimiters=False)
    return buffer.getvalue()


def make_color_schemes(out, breeze_dir, group_color):
    light, dark = breeze_dir / "BreezeLight.colors", breeze_dir / "BreezeDark.colors"
    if not (light.exists() and dark.exists()):
        print(f"Breeze color schemes not found in {breeze_dir}, skipping", file=sys.stderr)
        return
    day = tint_scheme(read_scheme(light), group_color, group_color, TINTS_DAY, "ManifestOS", mc.SCHEME_DAY)
    night = tint_scheme(read_scheme(dark), group_color, NIGHT_TINT, TINTS_NIGHT, "ManifestOS Night", mc.SCHEME_NIGHT)
    write(out / f"usr/share/color-schemes/{mc.SCHEME_DAY}.colors", dump(day))
    write(out / f"usr/share/color-schemes/{mc.SCHEME_NIGHT}.colors", dump(night))
    defaults = read_scheme(light)
    defaults = tint_scheme(defaults, group_color, group_color, TINTS_DAY, "ManifestOS", mc.SCHEME_DAY)
    if not defaults.has_section("Icons"):
        defaults.add_section("Icons")
    defaults.set("Icons", "Theme", "breeze")
    if not defaults.has_section("KDE"):
        defaults.add_section("KDE")
    defaults.set("KDE", "LookAndFeelPackage", "org.manifestos.desktop")
    defaults.set("KDE", "widgetStyle", "Breeze")
    for key in list(defaults["General"].keys()):
        if key not in ("ColorScheme", "shadeSortColumn"):
            defaults.remove_option("General", key)
    write(out / "etc/xdg/kdeglobals", dump(defaults))


def make_fastfetch(out, colors):
    write(out / "usr/share/manifestos/fastfetch-logo.txt", mc.ring_fastfetch() + "\n")
    logo_colors = {str(i + 1): "38;2;" + ";".join(str(v) for v in mc.hex_rgb(c)) for i, c in enumerate(colors)}
    logo_colors["7"] = "97"
    config = {
        "$schema": "https://github.com/fastfetch-cli/fastfetch/raw/dev/doc/json_schema.json",
        "logo": {"type": "file", "source": "/usr/share/manifestos/fastfetch-logo.txt", "color": logo_colors, "padding": {"right": 3}},
        "display": {"color": {"keys": "38;2;" + ";".join(str(v) for v in mc.hex_rgb(colors[0]))}, "separator": "  "},
        "modules": ["title", "separator", "os", "kernel", "uptime", "packages", "de", "wm", "terminal", "cpu", "gpu", "memory", "disk", "break", "colors"],
    }
    write(out / "etc/xdg/fastfetch/config.jsonc", json.dumps(config, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate ManifestOS artwork")
    parser.add_argument("out", type=Path)
    parser.add_argument("--breeze-dir", type=Path, default=Path("/usr/share/color-schemes"))
    args = parser.parse_args()
    data = json.loads((REPO / "data/members.json").read_text(encoding="utf-8"))
    colors = [m["color"] for m in data["members"]]
    group_color = data["group"]["color"]
    make_logos(args.out, colors, group_color)
    make_wallpapers(args.out, data, colors)
    make_plymouth(args.out, colors, group_color)
    make_grub(args.out, colors, group_color)
    make_calamares(args.out, colors, group_color)
    make_preview(args.out, colors, group_color)
    make_color_schemes(args.out, args.breeze_dir, group_color)
    make_fastfetch(args.out, colors)


if __name__ == "__main__":
    main()
