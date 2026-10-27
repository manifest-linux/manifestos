import datetime as dt
import functools
import json
import math
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

DATA_DIR = Path(os.environ.get("MANIFESTOS_DATA_DIR", "/usr/share/manifestos"))
WALLPAPER_DIR = Path(os.environ.get("MANIFESTOS_WALLPAPER_DIR", "/usr/share/wallpapers"))
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "manifestos"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "manifestos"

GROUP_ID = "group"
SCHEME_DAY = "ManifestOS"
SCHEME_NIGHT = "ManifestOSNight"
WALLPAPER_SIZE = "2560x1440"
FANART_FOLDER = "Manifest Fan Art"

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _language():
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return value.split(":")[0].split(".")[0].split("_")[0]
    return ""


@functools.lru_cache(maxsize=1)
def _catalog():
    lang = _language()
    if not lang.isalpha() or lang == "en":
        return {}
    return load_json(DATA_DIR / "i18n" / f"{lang}.json", {})


def tr(text):
    return _catalog().get(text, text)


@functools.lru_cache(maxsize=1)
def band():
    return load_json(DATA_DIR / "members.json", {"group": {"color": "#E0479E", "links": {}}, "members": []})


def members():
    return band().get("members", [])


def member(member_id):
    return next((m for m in members() if m["id"] == member_id), None)


def color_of(member_id):
    found = member(member_id)
    return found["color"] if found else band()["group"]["color"]


def display_name(member_id):
    found = member(member_id)
    return found["short"] if found else tr("Whole group")


def hex_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def parse_date(value):
    return dt.date.fromisoformat(value)


def format_date(day):
    return f"{day.day} {tr(MONTHS[day.month - 1])} {day.year}"


def occurrence(month, day, year):
    try:
        return dt.date(year, month, day)
    except ValueError:
        return dt.date(year, 2, 28)


def next_occurrence(month, day, today):
    this_year = occurrence(month, day, today.year)
    return this_year if this_year >= today else occurrence(month, day, today.year + 1)


def age_on(birthday, day):
    return day.year - birthday.year - ((day.month, day.day) < (birthday.month, birthday.day))


def birthdays_on(day):
    found = []
    for m in members():
        born = parse_date(m["birthday"])
        if occurrence(born.month, born.day, day.year) == day:
            found.append(m)
    return found


def parse_when(value):
    try:
        if "T" in value:
            return dt.datetime.fromisoformat(value), False
        return dt.datetime.combine(dt.date.fromisoformat(value), dt.time()), True
    except (TypeError, ValueError):
        return None, False


def load_settings():
    return load_json(CONFIG_DIR / "settings.json", {})


def save_settings(settings):
    save_json(CONFIG_DIR / "settings.json", settings)


def user_events():
    return load_json(CONFIG_DIR / "events.json", [])


def save_user_events(events):
    save_json(CONFIG_DIR / "events.json", events)


def _item(title, when, all_day, kind, color, **extra):
    if not isinstance(when, dt.datetime):
        when = dt.datetime.combine(when, dt.time())
    item = {"title": title, "when": when, "all_day": all_day, "kind": kind, "color": color}
    item.update({key: value for key, value in extra.items() if value is not None})
    return item


def upcoming(now=None):
    now = now or dt.datetime.now()
    today = now.date()
    data = band()
    group_color = data["group"]["color"]
    items = []
    for m in data.get("members", []):
        born = parse_date(m["birthday"])
        day = next_occurrence(born.month, born.day, today)
        title = tr("{name}'s birthday").format(name=m["short"])
        items.append(_item(title, day, True, "birthday", m["color"], member=m["id"], age=age_on(born, day)))
    for anniversary in data.get("anniversaries", []):
        first = parse_date(anniversary["date"])
        day = next_occurrence(first.month, first.day, today)
        years = day.year - first.year
        if years < 1:
            continue
        items.append(_item(tr(anniversary["title"]), day, True, "anniversary", group_color, years=years))
    sources = [(load_json(DATA_DIR / "events.json", []), False), (user_events(), True)]
    for events, mine in sources:
        for event in events:
            when, all_day = parse_when(event.get("when"))
            if when is None or not event.get("title"):
                continue
            if (when.date() < today) if all_day else (when < now):
                continue
            items.append(_item(
                event["title"], when, all_day, event.get("kind", "event"), event.get("color", group_color),
                url=event.get("url"), id=event.get("id"), user=mine or None,
            ))
    items.sort(key=lambda item: item["when"])
    return items


def countdown(item, now=None):
    now = now or dt.datetime.now()
    if item["all_day"]:
        days = (item["when"].date() - now.date()).days
        if days <= 0:
            return tr("Today!")
        if days == 1:
            return tr("Tomorrow")
        return tr("in {days} days").format(days=days)
    seconds = int((item["when"] - now).total_seconds())
    if seconds <= 0:
        return tr("Now!")
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return tr("{d}d {h}h {m}m").format(d=days, h=hours, m=minutes)
    return tr("{h}h {m}m {s}s").format(h=hours, m=minutes, s=secs)


def upcoming_json(limit=None, now=None):
    now = now or dt.datetime.now()
    items = upcoming(now)
    if limit:
        items = items[:limit]
    return {
        "items": [
            {
                "title": item["title"],
                "epoch": int(item["when"].timestamp() * 1000),
                "all_day": item["all_day"],
                "kind": item["kind"],
                "color": item["color"],
            }
            for item in items
        ],
        "labels": {
            "title": tr("Manifest Countdown"),
            "today": tr("Today!"),
            "tomorrow": tr("Tomorrow"),
            "now": tr("Now!"),
            "days": tr("in {days} days"),
            "dhm": tr("{d}d {h}h {m}m"),
            "hms": tr("{h}h {m}m {s}s"),
            "empty_title": tr("Nothing planned yet"),
            "empty_body": tr("Add concerts and releases in Manifest Hub"),
            "open_hub": tr("Open Manifest Hub"),
        },
    }


def random_fact(rng=None):
    rng = rng or random.Random()
    facts = [tr(fact) for fact in band().get("facts", [])]
    for m in members():
        born = parse_date(m["birthday"])
        facts.append(tr("{name} was born on {date}.").format(name=m["short"], date=format_date(born)))
    return rng.choice(facts) if facts else ""


def _run(args, attempts=1, delay=2.0):
    if shutil.which(args[0]) is None:
        return False
    for attempt in range(attempts):
        result = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if result.returncode == 0:
            return True
        if attempt + 1 < attempts:
            time.sleep(delay)
    return False


def launch(args):
    if shutil.which(args[0]) is None:
        return False
    subprocess.Popen(
        args, start_new_session=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return True


def open_url(url):
    return launch(["xdg-open", url])


def notify(title, body, icon="manifestos"):
    return _run(["notify-send", "--app-name=ManifestOS", f"--icon={icon}", title, body])


def wallpaper_image(member_id):
    package = f"ManifestOS-{member_id.capitalize()}" if member(member_id) else "ManifestOS-Group"
    return WALLPAPER_DIR / package / "contents" / "images" / f"{WALLPAPER_SIZE}.png"


def birthday_image(member_id):
    return DATA_DIR / "birthday" / f"{member_id}.png"


def set_wallpaper(path, attempts=1):
    return _run(["plasma-apply-wallpaperimage", str(path)], attempts=attempts)


def apply_look(member_id, night=None, attempts=1):
    settings = load_settings()
    if night is None:
        night = settings.get("night", False)
    _run(["plasma-apply-colorscheme", SCHEME_NIGHT if night else SCHEME_DAY])
    _run(["plasma-apply-colorscheme", "--accent-color", color_of(member_id)])
    set_wallpaper(wallpaper_image(member_id), attempts=attempts)
    settings.update(bias=member_id if member(member_id) else GROUP_ID, night=night)
    save_settings(settings)


def fanart_dir():
    pictures = ""
    if shutil.which("xdg-user-dir"):
        pictures = subprocess.run(
            ["xdg-user-dir", "PICTURES"], capture_output=True, text=True, check=False,
        ).stdout.strip()
    base = Path(pictures) if pictures and Path(pictures) != Path.home() else Path.home() / "Pictures"
    return base / FANART_FOLDER


def configure_lockscreen():
    folder = fanart_dir()
    folder.mkdir(parents=True, exist_ok=True)
    greeter = ["kwriteconfig6", "--file", "kscreenlockerrc", "--group", "Greeter"]
    slideshow = greeter + ["--group", "Wallpaper", "--group", "org.kde.slideshow", "--group", "General"]
    _run(greeter + ["--key", "WallpaperPlugin", "org.kde.slideshow"])
    _run(slideshow + ["--key", "SlidePaths", f"{DATA_DIR / 'lockscreen'}/,{folder}/"])
    _run(slideshow + ["--key", "SlideInterval", "30"])


def ring_cells(radius=6, inner=3.6, aspect=2.0, text="manifest"):
    width = int(radius * aspect)
    rows = []
    for y in range(-radius, radius + 1):
        row = []
        for x in range(-width, width + 1):
            dx = x / aspect
            distance = math.hypot(dx, y)
            if inner <= distance <= radius + 0.35:
                angle = (math.degrees(math.atan2(dx, -y)) + 360) % 360
                row.append((int(angle // 60) % 6, "█"))
            else:
                row.append((None, " "))
        rows.append(row)
    if text:
        middle = rows[radius]
        start = width - len(text) // 2
        for offset, char in enumerate(text):
            middle[start + offset] = (-1, char)
    return rows


def ring_ansi(colors, text="manifest"):
    lines = []
    for row in ring_cells(text=text):
        parts = []
        current = "unset"
        for segment, char in row:
            if segment != current:
                if segment is None:
                    parts.append("\033[0m")
                elif segment == -1:
                    parts.append("\033[1;97m")
                else:
                    r, g, b = hex_rgb(colors[segment])
                    parts.append(f"\033[38;2;{r};{g};{b}m")
                current = segment
            parts.append(char)
        parts.append("\033[0m")
        lines.append("".join(parts))
    return "\n".join(lines)


def ring_fastfetch(text="manifest"):
    lines = []
    for row in ring_cells(text=text):
        parts = []
        current = "unset"
        for segment, char in row:
            if segment is not None and segment != current:
                parts.append("$7" if segment == -1 else f"${segment + 1}")
                current = segment
            parts.append(char)
        lines.append("".join(parts).rstrip())
    return "\n".join(lines)
