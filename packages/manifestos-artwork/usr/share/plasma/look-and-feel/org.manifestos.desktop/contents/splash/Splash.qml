import QtQuick
import "colors.js" as Palette

Rectangle {
    id: root

    property int stage

    gradient: Gradient {
        GradientStop { position: 0.0; color: "#2B1438" }
        GradientStop { position: 1.0; color: "#5A1F4F" }
    }

    Image {
        id: logo
        anchors.centerIn: parent
        anchors.verticalCenterOffset: -30
        source: "images/logo.svg"
        sourceSize.width: 180
        sourceSize.height: 180

        NumberAnimation on opacity {
            from: 0
            to: 1
            duration: 600
        }
    }

    Row {
        anchors.top: logo.bottom
        anchors.topMargin: 48
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 14

        Repeater {
            model: Palette.dots

            Rectangle {
                width: 14
                height: 14
                radius: 7
                color: modelData
                opacity: 0.3

                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    PauseAnimation { duration: index * 120 }
                    NumberAnimation { from: 0.3; to: 1.0; duration: 360 }
                    NumberAnimation { from: 1.0; to: 0.3; duration: 360 }
                    PauseAnimation { duration: (Palette.dots.length - 1 - index) * 120 }
                }
            }
        }
    }

    Text {
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 48
        anchors.horizontalCenter: parent.horizontalCenter
        text: "ManifestOS"
        color: "white"
        opacity: 0.85
        font.family: "Comfortaa"
        font.pixelSize: 22
    }
}
