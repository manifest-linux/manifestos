var panel = new Panel
var panelScreen = panel.screen

panel.location = "bottom"
panel.height = 2 * Math.floor(gridUnit * 2.5 / 2)

panel.addWidget("org.kde.plasma.panelspacer")

var kickoff = panel.addWidget("org.kde.plasma.kickoff")
kickoff.currentConfigGroup = ["Shortcuts"]
kickoff.writeConfig("global", "Alt+F1")
kickoff.currentConfigGroup = ["General"]
kickoff.writeConfig("icon", "manifestos")

var tasks = panel.addWidget("org.kde.plasma.icontasks")
tasks.currentConfigGroup = ["General"]
tasks.writeConfig("fill", false)
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:firefox-esr.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:manifest-hub.desktop"
])

panel.addWidget("org.kde.plasma.panelspacer")
panel.addWidget("org.kde.plasma.systemtray")
panel.addWidget("org.kde.plasma.digitalclock")
panel.addWidget("org.kde.plasma.showdesktop")

desktops().forEach(function (desktop) {
    desktop.wallpaperPlugin = "org.kde.image"
    desktop.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"]
    desktop.writeConfig("Image", "file:///usr/share/wallpapers/ManifestOS-Group/")
    if (desktop.screen === panelScreen) {
        var geometry = screenGeometry(desktop.screen)
        desktop.addWidget("org.manifestos.countdown", geometry.width - gridUnit * 22, gridUnit * 2, gridUnit * 20, gridUnit * 16)
    }
})
