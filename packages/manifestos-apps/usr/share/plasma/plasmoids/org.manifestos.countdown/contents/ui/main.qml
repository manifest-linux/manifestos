import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    property var items: []
    property var labels: ({})
    property double now: Date.now()
    readonly property var nextItem: items.length > 0 ? items[0] : null

    switchWidth: Kirigami.Units.gridUnit * 10
    switchHeight: Kirigami.Units.gridUnit * 6
    Plasmoid.icon: "manifestos"
    toolTipMainText: nextItem ? nextItem.title : (labels.title || "Manifest Countdown")
    toolTipSubText: nextItem ? remaining(nextItem) : ""

    function format(template, values) {
        let result = template || "";
        for (const key in values) {
            result = result.replace("{" + key + "}", values[key]);
        }
        return result;
    }

    function remaining(item) {
        if (!item) {
            return "";
        }
        if (item.all_day) {
            const today = new Date(now);
            today.setHours(0, 0, 0, 0);
            const days = Math.round((item.epoch - today.getTime()) / 86400000);
            if (days <= 0) {
                return labels.today || "Today!";
            }
            if (days === 1) {
                return labels.tomorrow || "Tomorrow";
            }
            return format(labels.days || "in {days} days", { days: days });
        }
        const diff = item.epoch - now;
        if (diff <= 0) {
            return labels.now || "Now!";
        }
        const d = Math.floor(diff / 86400000);
        const h = Math.floor(diff % 86400000 / 3600000);
        const m = Math.floor(diff % 3600000 / 60000);
        const s = Math.floor(diff % 60000 / 1000);
        if (d > 0) {
            return format(labels.dhm || "{d}d {h}h {m}m", { d: d, h: h, m: m });
        }
        return format(labels.hms || "{h}h {m}m {s}s", { h: h, m: m, s: s });
    }

    function refresh() {
        executable.connectSource("manifest events --json --limit 5");
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            disconnectSource(sourceName);
            if (sourceName.indexOf("manifest events") !== 0) {
                return;
            }
            try {
                const parsed = JSON.parse(data["stdout"]);
                root.items = parsed.items;
                root.labels = parsed.labels;
            } catch (error) {
                root.items = [];
            }
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: root.now = Date.now()
    }

    Timer {
        interval: 10 * 60 * 1000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    compactRepresentation: MouseArea {
        Layout.minimumWidth: row.implicitWidth
        onClicked: root.expanded = !root.expanded

        RowLayout {
            id: row
            anchors.fill: parent
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: "manifestos"
                Layout.preferredWidth: Kirigami.Units.iconSizes.small
                Layout.preferredHeight: Kirigami.Units.iconSizes.small
            }

            PlasmaComponents.Label {
                text: root.nextItem ? root.remaining(root.nextItem) : ""
                visible: text.length > 0
            }
        }
    }

    fullRepresentation: ColumnLayout {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 14
        Layout.minimumHeight: implicitHeight
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Heading {
            Layout.fillWidth: true
            level: 3
            text: root.labels.title || "Manifest Countdown"
            opacity: 0.7
        }

        Kirigami.Heading {
            Layout.fillWidth: true
            level: 2
            wrapMode: Text.Wrap
            text: root.nextItem ? root.nextItem.title : (root.labels.empty_title || "")
        }

        PlasmaComponents.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: root.nextItem ? root.remaining(root.nextItem) : (root.labels.empty_body || "")
            color: root.nextItem ? root.nextItem.color : Kirigami.Theme.textColor
            font.pointSize: root.nextItem ? Kirigami.Theme.defaultFont.pointSize * 2 : Kirigami.Theme.defaultFont.pointSize
            font.bold: root.nextItem !== null
        }

        Repeater {
            model: root.items.slice(1)

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Rectangle {
                    width: Kirigami.Units.smallSpacing * 2
                    height: width
                    radius: width / 2
                    color: modelData.color
                }

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    text: modelData.title
                }

                PlasmaComponents.Label {
                    text: root.remaining(modelData)
                    opacity: 0.8
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }

        PlasmaComponents.Button {
            Layout.alignment: Qt.AlignRight
            icon.name: "manifest-hub"
            text: root.labels.open_hub || "Open Manifest Hub"
            onClicked: executable.connectSource("manifest hub")
        }
    }
}
