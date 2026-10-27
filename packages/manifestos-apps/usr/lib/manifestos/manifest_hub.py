import datetime as dt
import sys
import urllib.parse
import uuid
import xml.etree.ElementTree as ET

from PyQt6.QtCore import QDateTime, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import manifestos_common as mc

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
HEADING_FONT = "Comfortaa"


def readable_on(color):
    r, g, b = mc.hex_rgb(color)
    return "#1B1020" if 0.299 * r + 0.587 * g + 0.114 * b > 170 else "#FFFFFF"


def heading(content, size=18):
    label = QLabel(content)
    font = QFont(HEADING_FONT, size)
    font.setBold(True)
    label.setFont(font)
    label.setWordWrap(True)
    return label


def dot_icon(color, size=16):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


def color_button(text, color, height=44):
    button = QPushButton(text)
    button.setMinimumHeight(height)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    hover = QColor(color).lighter(112).name()
    button.setStyleSheet(
        f"QPushButton {{ background: {color}; color: {readable_on(color)}; border: none; border-radius: 12px;"
        f" padding: 6px 16px; font-weight: bold; }}"
        f"QPushButton:hover {{ background: {hover}; }}"
    )
    return button


def busy(callback):
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        callback()
    finally:
        QApplication.restoreOverrideCursor()


def apply_bias(member_id):
    busy(lambda: mc.apply_look(member_id))
    mc.notify(
        mc.tr("Bias updated"),
        mc.tr("Your desktop now wears {name}'s colors.").format(name=mc.display_name(member_id)),
    )


class MemberCard(QFrame):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        color = data["color"]
        self.setObjectName("card")
        self.setStyleSheet(f"#card {{ border: 2px solid {color}; border-radius: 16px; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        header = heading(data["short"], 20)
        header.setStyleSheet(f"background: {color}; color: {readable_on(color)}; border-radius: 10px; padding: 8px 12px;")
        layout.addWidget(header)
        layout.addWidget(QLabel(f"<b>{data['name']}</b>"))
        today = dt.date.today()
        born = mc.parse_date(data["birthday"])
        days = (mc.next_occurrence(born.month, born.day, today) - today).days
        age = mc.tr("{age} years old").format(age=mc.age_on(born, today))
        layout.addWidget(QLabel(f"🎂 {mc.format_date(born)}, {age}"))
        if data.get("role"):
            layout.addWidget(QLabel(f"⭐ {mc.tr(data['role'])}"))
        soon = mc.tr("Birthday is today!") if days == 0 else mc.tr("Next birthday in {days} days").format(days=days)
        layout.addWidget(QLabel(f"⏳ {soon}"))
        layout.addStretch(1)
        button = color_button(mc.tr("Make her my bias"), color, 38)
        button.clicked.connect(lambda: apply_bias(data["id"]))
        layout.addWidget(button)


class MembersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        settings = mc.load_settings()
        toggles = QHBoxLayout()
        self.night = QCheckBox(mc.tr("Night mode"))
        self.night.setChecked(settings.get("night", False))
        self.night.toggled.connect(self.toggle_night)
        self.party = QCheckBox(mc.tr("Birthday wallpaper on her birthday"))
        self.party.setChecked(settings.get("birthday_wallpaper", True))
        self.party.toggled.connect(self.toggle_party)
        toggles.addWidget(self.night)
        toggles.addWidget(self.party)
        toggles.addStretch(1)
        group = color_button(mc.tr("Whole group"), mc.band()["group"]["color"], 36)
        group.clicked.connect(lambda: apply_bias(mc.GROUP_ID))
        toggles.addWidget(group)
        outer.addLayout(toggles)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setSpacing(14)
        for index, data in enumerate(mc.members()):
            grid.addWidget(MemberCard(data), index // 3, index % 3)
        scroll.setWidget(holder)
        outer.addWidget(scroll)

    def toggle_night(self, checked):
        busy(lambda: mc.apply_look(mc.load_settings().get("bias", mc.GROUP_ID), night=checked))

    def toggle_party(self, checked):
        settings = mc.load_settings()
        settings["birthday_wallpaper"] = checked
        mc.save_settings(settings)


class VideosTab(QWidget):
    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.status = QLabel(mc.tr("Loading the latest videos..."))
        refresh = QPushButton(mc.tr("Refresh"))
        refresh.clicked.connect(self.load)
        top.addWidget(self.status, 1)
        top.addWidget(refresh)
        layout.addLayout(top)
        self.list = QListWidget()
        self.list.setIconSize(QSize(192, 108))
        self.list.setSpacing(6)
        self.list.itemActivated.connect(lambda item: mc.open_url(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.list)
        self.load()

    def load(self):
        channel = mc.band()["group"]["links"].get("youtube_channel_id")
        if not channel:
            self.status.setText(mc.tr("No video channel configured."))
            return
        self.list.clear()
        self.status.setText(mc.tr("Loading the latest videos..."))
        url = QUrl(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}")
        reply = self.network.get(QNetworkRequest(url))
        reply.finished.connect(lambda: self.loaded(reply))

    def loaded(self, reply):
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.status.setText(mc.tr("Could not load videos. Check your internet connection."))
            return
        try:
            root = ET.fromstring(bytes(reply.readAll()))
        except ET.ParseError:
            self.status.setText(mc.tr("Could not load videos. Check your internet connection."))
            return
        for entry in root.findall(f"{ATOM}entry"):
            link = entry.find(f"{ATOM}link")
            if link is None:
                continue
            published = (entry.findtext(f"{ATOM}published") or "")[:10]
            item = QListWidgetItem(f"{entry.findtext(f'{ATOM}title')}\n{published}")
            item.setData(Qt.ItemDataRole.UserRole, link.get("href"))
            self.list.addItem(item)
            thumb = entry.find(f"{MEDIA}group/{MEDIA}thumbnail")
            if thumb is not None:
                self.load_thumbnail(item, thumb.get("url"))
        self.status.setText(mc.tr("Double-click a video to watch it."))

    def load_thumbnail(self, item, url):
        reply = self.network.get(QNetworkRequest(QUrl(url)))

        def done():
            reply.deleteLater()
            pixmap = QPixmap()
            if reply.error() == QNetworkReply.NetworkError.NoError and pixmap.loadFromData(bytes(reply.readAll())):
                try:
                    item.setIcon(QIcon(pixmap.scaled(192, 108, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)))
                except RuntimeError:
                    pass

        reply.finished.connect(done)


class MusicTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(mc.tr("Double-click a song to play it on YouTube Music.")))
        self.list = QListWidget()
        group_color = mc.band()["group"]["color"]
        for album in mc.band().get("albums", []):
            day = mc.parse_date(album["date"])
            item = QListWidgetItem(dot_icon(group_color), f"💿 {album['title']}  ·  {mc.format_date(day)}")
            item.setData(Qt.ItemDataRole.UserRole, album["title"])
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            self.list.addItem(item)
        for index, song in enumerate(mc.band().get("songs", [])):
            label = song["title"]
            if song.get("featuring"):
                label += f"  (feat. {song['featuring']})"
            if song.get("year"):
                label += f"  ·  {song['year']}"
            color = mc.members()[index % len(mc.members())]["color"] if mc.members() else group_color
            item = QListWidgetItem(dot_icon(color), label)
            item.setData(Qt.ItemDataRole.UserRole, song["title"])
            self.list.addItem(item)
        self.list.itemActivated.connect(self.play)
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        spotify = color_button(mc.tr("Get Spotify"), "#1DB954", 38)
        spotify.clicked.connect(lambda: mc.open_url("appstream://com.spotify.Client"))
        search = QPushButton(mc.tr("Open manifest on Spotify"))
        search.clicked.connect(lambda: mc.open_url(mc.band()["group"]["links"]["spotify_search"]))
        buttons.addWidget(spotify)
        buttons.addWidget(search)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def play(self, item):
        query = urllib.parse.quote(f"manifest {item.data(Qt.ItemDataRole.UserRole)}")
        mc.open_url(f"https://music.youtube.com/search?q={query}")


class EventDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(mc.tr("Add event"))
        form = QFormLayout(self)
        self.title = QLineEdit()
        self.title.setPlaceholderText(mc.tr("Concert, release, livestream..."))
        self.when = QDateTimeEdit(QDateTime.currentDateTime().addDays(7))
        self.when.setCalendarPopup(True)
        self.when.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.all_day = QCheckBox(mc.tr("All day"))
        self.all_day.toggled.connect(lambda on: self.when.setDisplayFormat("yyyy-MM-dd" if on else "yyyy-MM-dd HH:mm"))
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://")
        form.addRow(mc.tr("Title"), self.title)
        form.addRow(mc.tr("When"), self.when)
        form.addRow("", self.all_day)
        form.addRow(mc.tr("Link"), self.url)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self):
        if self.title.text().strip():
            super().accept()

    def event_data(self):
        moment = self.when.dateTime().toPyDateTime()
        when = moment.date().isoformat() if self.all_day.isChecked() else moment.strftime("%Y-%m-%dT%H:%M")
        event = {"id": uuid.uuid4().hex, "title": self.title.text().strip(), "when": when}
        if self.url.text().strip():
            event["url"] = self.url.text().strip()
        return event


class CountdownTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.next_title = heading("", 18)
        self.next_count = heading("", 28)
        layout.addWidget(self.next_title)
        layout.addWidget(self.next_count)
        self.list = QListWidget()
        self.list.itemActivated.connect(self.open_link)
        layout.addWidget(self.list)
        buttons = QHBoxLayout()
        add = color_button(mc.tr("Add event"), mc.band()["group"]["color"], 36)
        add.clicked.connect(self.add)
        self.remove = QPushButton(mc.tr("Remove"))
        self.remove.clicked.connect(self.delete)
        buttons.addWidget(add)
        buttons.addWidget(self.remove)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        tip = QLabel(mc.tr("Tip: right-click the desktop, choose Add Widgets and drop Manifest Countdown anywhere."))
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.items = []
        self.reload()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)

    def reload(self):
        self.items = mc.upcoming()
        self.list.clear()
        for item in self.items:
            row = QListWidgetItem(dot_icon(item["color"]), "")
            self.list.addItem(row)
        self.tick()

    def tick(self):
        now = dt.datetime.now()
        if self.items and self.items[0]["when"].date() < now.date():
            self.reload()
            return
        for index, item in enumerate(self.items):
            row = self.list.item(index)
            if row is not None:
                row.setText(f"{item['when']:%Y-%m-%d}  ·  {item['title']}  ·  {mc.countdown(item, now)}")
        if self.items:
            first = self.items[0]
            self.next_title.setText(first["title"])
            self.next_count.setText(mc.countdown(first, now))
            self.next_count.setStyleSheet(f"color: {first['color']};")
        else:
            self.next_title.setText(mc.tr("Nothing planned yet"))
            self.next_count.setText("")

    def add(self):
        dialog = EventDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            events = mc.user_events()
            events.append(dialog.event_data())
            mc.save_user_events(events)
            self.reload()

    def delete(self):
        row = self.list.currentRow()
        if row < 0 or not self.items[row].get("user"):
            return
        target = self.items[row].get("id")
        mc.save_user_events([e for e in mc.user_events() if e.get("id") != target])
        self.reload()

    def open_link(self, row):
        item = self.items[self.list.row(row)]
        if item.get("url"):
            mc.open_url(item["url"])


class LinksTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        links = mc.band()["group"]["links"]
        colors = [m["color"] for m in mc.members()] or [mc.band()["group"]["color"]]
        entries = [
            ("YouTube", links.get("youtube")),
            ("Instagram", links.get("instagram")),
            ("TikTok", links.get("tiktok")),
            (mc.tr("Website"), links.get("website")),
            ("Spotify", links.get("spotify_search")),
        ]
        grid = QGridLayout()
        for index, (label, url) in enumerate(e for e in entries if e[1]):
            button = color_button(label, colors[index % len(colors)], 52)
            button.clicked.connect(lambda _checked=False, target=url: mc.open_url(target))
            grid.addWidget(button, index // 2, index % 2)
        layout.addLayout(grid)
        layout.addSpacing(20)
        layout.addWidget(heading(mc.tr("Fan art"), 16))
        info = QLabel(mc.tr("Drop your favorite fan art into this folder and it will show up on your lock screen."))
        info.setWordWrap(True)
        layout.addWidget(info)
        folder = QPushButton(mc.tr("Open fan art folder"))
        folder.clicked.connect(self.open_fanart)
        layout.addWidget(folder, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

    def open_fanart(self):
        path = mc.fanart_dir()
        path.mkdir(parents=True, exist_ok=True)
        mc.open_url(path.as_uri())


class HubWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manifest Hub")
        self.setWindowIcon(QIcon.fromTheme("manifest-hub"))
        self.resize(980, 700)
        self.network = QNetworkAccessManager(self)
        central = QWidget()
        layout = QVBoxLayout(central)
        title = heading("manifest hub", 26)
        title.setStyleSheet(f"color: {mc.band()['group']['color']};")
        layout.addWidget(title)
        tabs = QTabWidget()
        tabs.addTab(MembersTab(), mc.tr("Members"))
        tabs.addTab(VideosTab(self.network), mc.tr("Videos"))
        tabs.addTab(MusicTab(), mc.tr("Music"))
        tabs.addTab(CountdownTab(), mc.tr("Countdown"))
        tabs.addTab(LinksTab(), mc.tr("Links"))
        layout.addWidget(tabs)
        footer = QLabel(mc.tr("Unofficial fan project. Not affiliated with manifest or Hypers New Media."))
        footer.setStyleSheet("color: gray;")
        layout.addWidget(footer)
        self.setCentralWidget(central)


class BiasPicker(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(mc.tr("Pick your bias"))
        self.setWindowIcon(QIcon.fromTheme("manifestos"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.addWidget(heading(mc.tr("Who's your bias?"), 24))
        hint = QLabel(mc.tr("Your wallpaper and colors will match her. You can change this any time in Manifest Hub."))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        grid = QGridLayout()
        grid.setSpacing(12)
        for index, data in enumerate(mc.members()):
            label = data["short"] + (f"\n{mc.tr(data['role'])}" if data.get("role") else "")
            button = color_button(label, data["color"], 84)
            button.clicked.connect(lambda _checked=False, member_id=data["id"]: self.choose(member_id))
            grid.addWidget(button, index // 3, index % 3)
        layout.addLayout(grid)
        group = color_button(mc.tr("I love them all"), mc.band()["group"]["color"], 52)
        group.clicked.connect(lambda: self.choose(mc.GROUP_ID))
        layout.addWidget(group)
        layout.addStretch(1)
        bottom = QHBoxLayout()
        self.night = QCheckBox(mc.tr("Night mode"))
        self.night.setChecked(mc.load_settings().get("night", False))
        later = QPushButton(mc.tr("Maybe later"))
        later.clicked.connect(self.reject)
        bottom.addWidget(self.night)
        bottom.addStretch(1)
        bottom.addWidget(later)
        layout.addLayout(bottom)

    def choose(self, member_id):
        busy(lambda: mc.apply_look(member_id, night=self.night.isChecked()))
        mc.notify(
            mc.tr("Bias updated"),
            mc.tr("Your desktop now wears {name}'s colors.").format(name=mc.display_name(member_id)),
        )
        self.accept()


def main(argv):
    app = QApplication(argv)
    app.setApplicationName("Manifest Hub")
    app.setDesktopFileName("manifest-hub")
    if "--pick-bias" in argv:
        window = BiasPicker()
        window.show()
        return app.exec()
    window = HubWindow()
    window.show()
    return app.exec()
