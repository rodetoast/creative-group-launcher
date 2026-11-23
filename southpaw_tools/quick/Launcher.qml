import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    objectName: "southpawQuickLauncher"
    width: 1200
    height: 780

    readonly property var dataView: launcher.view
    // Shared visual vocabulary for the library, detail view and dialogs.
    readonly property color canvas: launcher.dark ? "#151822" : "#f4f4f8"
    readonly property color sidebar: launcher.dark ? "#1b1e2b" : "#f1eff8"
    readonly property color card: launcher.dark ? "#202432" : "#ffffff"
    readonly property color line: launcher.dark ? "#393e51" : "#d9d9e6"
    readonly property color ink: launcher.dark ? "#f5f3ff" : "#222335"
    readonly property color muted: launcher.dark ? "#b7b9cb" : "#565a70"
    readonly property color accent: launcher.dark ? "#c5b6ff" : "#5034a4"
    readonly property color accentPad: launcher.dark ? "#302743" : "#e8dfff"
    readonly property color primaryFill: launcher.dark ? "#7146bd" : "#7048bc"
    readonly property color primaryHover: launcher.dark ? "#7b50c9" : "#603aa8"
    readonly property color primaryPressed: launcher.dark ? "#6039a6" : "#553294"
    readonly property color primaryText: "#ffffff"
    readonly property color disabledPrimary: launcher.dark ? "#342d47" : "#ede6f7"
    readonly property color installedPad: launcher.dark ? "#253b36" : "#ddf1e8"
    readonly property int cardRadius: 13
    property Item detailOrigin: null
    property bool detailOpen: false
    property bool notesExpanded: false
    property bool managementExpanded: false
    readonly property bool dockDetail: width >= 1210
    readonly property bool wideHeader: width >= 1100
    readonly property color selectedCard: launcher.dark ? "#28233b" : "#f5effd"
    readonly property color softPanel: launcher.dark ? "#191c2a" : "#f9f8fd"
    onDockDetailChanged: {
        if (!detailOpen) return
        if (dockDetail) detail.close()
        else detail.open()
    }
    readonly property color hover: launcher.dark ? "#292d3e" : "#e2e2ed"
    readonly property color green: launcher.dark ? "#8ed4b4" : "#126044"
    readonly property color amber: launcher.dark ? "#ffd29b" : "#80522c"
    readonly property color danger: launcher.dark ? "#ffc0c5" : "#a02137"
    readonly property color dangerLine: launcher.dark ? "#79505b" : "#d4a0aa"
    readonly property color dangerHover: launcher.dark ? "#402934" : "#fae9ed"
    readonly property color warningPad: launcher.dark ? "#332a25" : "#f6eadd"
    readonly property int small: 12
    readonly property int bodyText: 14
    readonly property int heading: 17
    readonly property int tightGap: 8
    readonly property int gap: 16
    readonly property int radius: 10
    readonly property int controlHeight: 43
    readonly property string productFont: launcher.uiFont
    readonly property bool compact: width < 820
    readonly property int cardWidth: 280
    readonly property int inset: compact ? 16 : 30
    readonly property int transitionMs: 140
    readonly property bool working: dataView.busy || dataView.bridgeBusy
    readonly property bool checkFailed: dataView.catalogError || dataView.lastCheck === "failed"
    readonly property string connectionText: {
        if (dataView.checking) return "확인 중…"
        if (checkFailed) return "업데이트 확인 실패"
        if (dataView.online && dataView.launcher_update_button.visible)
            return dataView.verifiedVersion ? "업데이트 가능 · v" + dataView.verifiedVersion : "업데이트 가능"
        if (dataView.online && dataView.latestVerified) return "최신 버전 사용 중"
        if (dataView.online && dataView.verifiedVersion) return "운영 버전 v" + dataView.verifiedVersion
        if (dataView.online) return "앱 목록 확인 완료"
        if (dataView.lastCheck === "" && dataView.server_status.text === "오프라인 · 미확인")
            return "업데이트 확인 전"
        return dataView.server_status.text || "업데이트 확인 전"
    }

    function stateTone(state) {
        if (state === "설치됨" || state === "설치 완료" || state === "최신 버전")
            return green
        if (state === "업데이트 가능" || state === "이전 버전 사용 중 · 업데이트 가능")
            return accent
        if (state === "복구 필요" || state === "설치 확인 필요"
                || state === "작업 실패" || state === "설치 완료 · 목록 오류(업데이트 차단)")
            return amber
        return muted
    }

    component Caption: Label {
        color: root.muted
        font.family: root.productFont
        font.pixelSize: root.bodyText
        textFormat: Text.PlainText
    }

    function actionIcon(label) {
        if (label === "설치") return "download"
        if (label === "실행" || label === "실행 중") return "play"
        if (label.indexOf("업데이트") >= 0) return "refresh"
        return "info"
    }

    component Glyph: Canvas {
        id: glyph
        property string kind: ""
        property color ink: root.ink
        implicitWidth: 20
        implicitHeight: 20
        onInkChanged: requestPaint()
        onKindChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            ctx.scale(width / 20, height / 20)
            ctx.strokeStyle = ink
            ctx.fillStyle = ink
            ctx.lineWidth = 1.65
            ctx.lineCap = "round"
            ctx.lineJoin = "round"
            ctx.beginPath()
            switch (kind) {
            case "refresh":
                ctx.arc(10, 10, 6.4, 3.45, 5.93)
                ctx.moveTo(16.6, 3.6); ctx.lineTo(16.6, 7.8); ctx.lineTo(12.3, 7.8)
                ctx.moveTo(16.1, 12); ctx.arc(10, 10, 6.4, 0.32, 2.8)
                ctx.moveTo(3.4, 16.4); ctx.lineTo(3.4, 12.2); ctx.lineTo(7.7, 12.2)
                break
            case "play":
                ctx.moveTo(6, 3.8); ctx.lineTo(16, 10); ctx.lineTo(6, 16.2)
                ctx.closePath(); ctx.fill(); return
            case "download":
                ctx.moveTo(10, 3); ctx.lineTo(10, 12)
                ctx.moveTo(6.4, 8.8); ctx.lineTo(10, 12.4); ctx.lineTo(13.6, 8.8)
                ctx.moveTo(3, 13); ctx.lineTo(3, 16); ctx.lineTo(17, 16); ctx.lineTo(17, 13)
                break
            case "check":
                ctx.moveTo(4, 10); ctx.lineTo(8, 14); ctx.lineTo(16, 6)
                break
            case "close":
                ctx.moveTo(5, 5); ctx.lineTo(15, 15)
                ctx.moveTo(15, 5); ctx.lineTo(5, 15)
                break
            case "settings":
                for (let tooth = 0; tooth < 32; ++tooth) {
                    const angle = tooth * Math.PI / 16
                    const distance = tooth % 4 === 1 || tooth % 4 === 2 ? 8 : 6
                    const x = 10 + distance * Math.cos(angle)
                    const y = 10 + distance * Math.sin(angle)
                    if (tooth === 0) ctx.moveTo(x, y)
                    else ctx.lineTo(x, y)
                }
                ctx.closePath()
                ctx.moveTo(12.6, 10); ctx.arc(10, 10, 2.6, 0, Math.PI * 2)
                break
            case "up":
            case "down":
                const offset = kind === "up" ? 3 : -3
                ctx.moveTo(5, 10 + offset); ctx.lineTo(10, 10 - offset); ctx.lineTo(15, 10 + offset)
                break
            default:
                ctx.arc(10, 10, 7.4, 0, Math.PI * 2)
                ctx.moveTo(10, 9.5); ctx.lineTo(10, 13.8)
                ctx.moveTo(10, 6.6); ctx.lineTo(10, 6.8)
            }
            ctx.stroke()
        }
    }

    component StatusPill: Rectangle {
        property alias text: pillText.text
        property color tone: root.muted
        property color backgroundColor: root.hover
        property string glyph: ""
        property bool outlined: false
        implicitWidth: pillRow.implicitWidth + 20
        implicitHeight: Math.max(23, pillText.implicitHeight + 6)
        radius: height / 2
        color: backgroundColor
        border.width: outlined ? 1 : 0
        border.color: outlined ? Qt.alpha(tone, 0.45) : "transparent"
        Row {
            id: pillRow
            anchors.centerIn: parent
            spacing: 5
            Glyph {
                anchors.verticalCenter: parent.verticalCenter
                width: 13; height: 13
                visible: kind !== ""
                kind: pillRow.parent.glyph
                ink: pillRow.parent.tone
            }
            Caption {
                id: pillText
                anchors.verticalCenter: parent.verticalCenter
                font.pixelSize: root.small
                font.weight: Font.DemiBold
                color: pillRow.parent.tone
            }
        }
    }

    component LauncherButton: Button {
        id: button
        property string command: ""
        property bool emphasis: false
        property bool destructive: false
        property bool selected: false
        property bool quiet: false
        property string glyph: ""
        implicitHeight: root.controlHeight
        implicitWidth: Math.max(78, contentItem.implicitWidth + 28)
        leftPadding: 12
        rightPadding: 12
        font.pixelSize: root.bodyText
        font.family: root.productFont
        font.bold: emphasis
        hoverEnabled: true
        onClicked: if (command) launcher.act(command)
        contentItem: Item {
            implicitWidth: Math.ceil(actionLabel.implicitWidth) + 3 + (button.glyph ? 25 : 0)
            implicitHeight: Math.max(20, actionLabel.implicitHeight)
            Row {
                anchors.centerIn: parent
                spacing: 5
                Glyph {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 20
                    height: 20
                    visible: kind !== ""
                    kind: button.glyph
                    ink: actionLabel.color
                }
                Label {
                    id: actionLabel
                    anchors.verticalCenter: parent.verticalCenter
                    // Fractional DPI can round glyph advances differently from implicitWidth.
                    width: Math.min(Math.ceil(implicitWidth) + 3,
                                    Math.max(0, button.availableWidth - (button.glyph ? 25 : 0)))
                    text: button.text
                    textFormat: Text.PlainText
                    color: !button.enabled ? root.muted : button.emphasis ? root.primaryText
                                            : button.destructive ? root.danger
                                            : button.selected ? root.accent : root.ink
                    font: button.font
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
        background: Rectangle {
            radius: root.radius
            color: button.emphasis
                   ? (!button.enabled ? root.disabledPrimary : button.down ? root.primaryPressed
                                       : button.hovered ? root.primaryHover : root.primaryFill)
                   : button.enabled && (button.hovered || button.down)
                     ? (button.destructive ? root.dangerHover : root.hover)
                   : button.selected ? root.accentPad
                   : button.quiet ? "transparent" : root.card
            border.color: button.activeFocus || button.selected ? root.accent
                          : button.quiet || button.emphasis ? "transparent"
                          : button.destructive && button.enabled ? root.dangerLine : root.line
            border.width: button.activeFocus ? 2 : 1
            gradient: button.emphasis && button.enabled ? actionGradient : null
            Gradient {
                id: actionGradient
                GradientStop { position: 0; color: button.down ? root.primaryPressed : button.hovered ? root.primaryHover : root.primaryFill }
                GradientStop { position: 1; color: root.primaryPressed }
            }
            Behavior on color { ColorAnimation { duration: 95 } }
        }
    }

    component AppIcon: Image {
        property string appId: ""
        source: appId ? "image://southpaw/" + appId : ""
        sourceSize.width: 72
        sourceSize.height: 72
        fillMode: Image.PreserveAspectFit
    }

    component WorkProgress: ProgressBar {
        from: 0
        to: 100
        value: root.dataView.progress.value
        indeterminate: !root.dataView.knownProgress
        palette.highlight: root.accent
    }

    component ToolCard: Rectangle {
        id: card
        required property var modelData
        readonly property bool active: root.dataView.activeApp === modelData.id
        readonly property bool running: root.dataView.selectedId === modelData.id
                                        && root.dataView["설치 상태"] === "실행 중 · 업데이트 보류"
        readonly property bool canUpdate: modelData.update && root.dataView.online && !root.dataView.catalogError
        readonly property bool canDownload: modelData.published && root.dataView.online && !root.dataView.catalogError
        readonly property bool runnable: modelData.installed && !root.dataView.testing && !modelData.problem
        readonly property string statusText: {
            if (active) return root.dataView.message.text
            if (root.dataView.issues[modelData.id]) return "작업 실패"
            if (running) return "실행 중"
            if (modelData.problem || modelData.pending) return "설치 확인 필요"
            if (canUpdate) return "업데이트 가능"
            return modelData.installed ? "설치됨" : "미설치"
        }
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        readonly property bool selected: root.detailOpen && root.dataView.selectedId === modelData.id
        implicitHeight: root.compact ? 218 : 232
        radius: root.cardRadius
        color: selected ? root.selectedCard : mouse.hovered ? root.hover : root.card
        border.width: selected ? 2 : 1
        border.color: detailsButton.activeFocus || primary.activeFocus || active || selected ? root.accent : root.line
        HoverHandler { id: mouse }
        Behavior on color { ColorAnimation { duration: 110 } }
        MouseArea {
            anchors.fill: parent
            enabled: !root.working || card.active
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openDetails(card.modelData.id, detailsButton)
        }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.gap
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 54
                    Layout.preferredHeight: 54
                    radius: root.radius
                    color: root.accentPad
                    AppIcon { anchors.fill: parent; anchors.margins: 6; appId: card.modelData.id }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Caption {
                        Layout.fillWidth: true
                        color: root.ink
                        font.pixelSize: 20
                        font.bold: true
                        elide: Text.ElideRight
                        text: card.modelData.title
                        Accessible.name: text
                    }
                }
            }
            Caption {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 40
                Layout.alignment: Qt.AlignTop
                maximumLineCount: 3
                elide: Text.ElideRight
                wrapMode: Text.Wrap
                lineHeight: 1.14
                text: card.modelData.description
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: root.tightGap
                StatusPill {
                    visible: !card.active
                    text: card.statusText
                    tone: root.stateTone(text)
                    glyph: text === "설치됨" ? "check" : text === "업데이트 가능" ? "refresh"
                           : text === "미설치" ? "download" : ""
                    backgroundColor: card.statusText === "설치됨" ? root.installedPad
                                     : card.canUpdate && !root.dataView.issues[card.modelData.id] ? root.accentPad
                                     : tone === root.amber ? root.warningPad : root.hover
                }
                Rectangle {
                    visible: !card.active && (card.modelData.version !== "" || card.canDownload)
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 14
                    color: root.line
                }
                Caption {
                    Layout.fillWidth: true
                    font.pixelSize: root.small
                    color: root.ink
                    elide: Text.ElideRight
                    text: card.active ? card.statusText
                          : card.canUpdate ? card.modelData.version + " → " + card.modelData.providedVersion
                          : card.modelData.version ? "v" + card.modelData.version
                          : card.canDownload ? "최신 버전 " + card.modelData.providedVersion : ""
                }
            }
            WorkProgress {
                Layout.fillWidth: true
                visible: card.active
            }
            RowLayout {
                Layout.fillWidth: true
                LauncherButton {
                    id: primary
                    objectName: "primaryAction"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 115
                    Layout.minimumWidth: 0
                    glyph: root.actionIcon(text)
                    emphasis: true
                    text: card.running ? "실행 중" : card.modelData.problem ? "확인" : card.modelData.pending ? "복구 확인" : card.canUpdate ? "업데이트"
                          : card.modelData.installed ? "실행" : "설치"
                    enabled: !root.working && !card.running
                             && (card.modelData.problem || card.modelData.pending || card.canDownload || card.runnable)
                    onClicked: {
                        if (card.modelData.problem) root.openDetails(card.modelData.id, primary)
                        else launcher.actOnApp(card.modelData.id, "primary")
                    }
                }
                LauncherButton {
                    id: detailsButton
                    objectName: "detailsAction"
                    text: "상세 정보"
                    glyph: "info"
                    Layout.fillWidth: true
                    Layout.preferredWidth: 101
                    Layout.minimumWidth: 0
                    enabled: !root.working || card.active
                    Accessible.name: card.modelData.title + " 상세 정보"
                    onClicked: root.openDetails(card.modelData.id, detailsButton)
                }
            }
        }
    }

    function openDetails(appId, origin) {
        if (launcher.selectApp(appId)) {
            root.detailOrigin = origin
            notesExpanded = false
            managementExpanded = false
            detailOpen = true
            if (dockDetail) {
                if (dockLoader.item) dockLoader.item.focusClose()
            } else detail.open()
        }
    }

    function finishDetails() {
        detailOpen = false
        const origin = detailOrigin
        detailOrigin = null
        if (origin && origin.enabled) origin.forceActiveFocus()
    }

    function closeDetails() {
        if (dockDetail) finishDetails()
        else detail.close()
    }

    Rectangle {
        anchors.fill: parent
        color: root.canvas
        gradient: launcher.dark ? workspaceTone : null
        Gradient {
            id: workspaceTone
            GradientStop { position: 0; color: root.canvas }
            GradientStop { position: 1; color: "#11131f" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: toolbar.implicitHeight + 2 * root.inset
            color: root.sidebar
            GridLayout {
                id: toolbar
                anchors.fill: parent
                anchors.margins: root.inset
                columnSpacing: root.compact ? 8 : 18
                rowSpacing: 10
                columns: root.wideHeader ? 4 : 2
                RowLayout {
                    Layout.row: 0
                    Layout.column: 0
                    Layout.fillWidth: !root.wideHeader
                    spacing: root.compact ? 8 : 12
                    Image {
                        source: launcher.brandIcon
                        Layout.preferredWidth: root.compact ? 34 : 46
                        Layout.preferredHeight: width
                        fillMode: Image.PreserveAspectFit
                    }
                    Caption {
                        visible: root.wideHeader
                        text: "SOUTHPAW\nGAMES"
                        color: root.ink
                        font.pixelSize: 15
                        font.bold: true
                        font.letterSpacing: 0.8
                    }
                    Rectangle {
                        visible: root.wideHeader
                        Layout.preferredWidth: 1
                        Layout.preferredHeight: 44
                        color: root.line
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Caption {
                            Layout.fillWidth: true
                            text: "Southpaw Tools"
                            color: root.ink
                            font.bold: true
                            font.pixelSize: root.compact ? 23 : 31
                            elide: Text.ElideRight
                        }
                        Caption {
                            text: "Creative Workspace"
                            color: root.accent
                            font.pixelSize: root.compact ? 12 : 14
                            font.letterSpacing: root.compact ? 0.3 : 0.9
                        }
                    }
                }
                Flow {
                    Layout.row: root.wideHeader ? 0 : 1
                    Layout.column: root.wideHeader ? 1 : 0
                    Layout.columnSpan: root.wideHeader ? 1 : 2
                    Layout.fillWidth: true
                    spacing: 9
                    StatusPill {
                        text: "런처 v" + launcher.productVersion
                        tone: root.accent
                        backgroundColor: root.accentPad
                        outlined: true
                    }
                    Row {
                        height: 24
                        spacing: 6
                        Glyph {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 16; height: 16
                            kind: root.dataView.checking ? "refresh" : root.dataView.latestVerified && root.dataView.online ? "check" : "info"
                            ink: connection.color
                        }
                        Caption {
                            id: connection
                            objectName: "connectionState"
                            anchors.verticalCenter: parent.verticalCenter
                            font.pixelSize: root.small
                            text: root.connectionText
                            color: root.dataView.checking ? root.accent : root.checkFailed ? root.amber
                                   : root.dataView.online && root.dataView.latestVerified ? root.green : root.ink
                            ToolTip.visible: statusHover.hovered
                            ToolTip.text: root.dataView.server_status.tip
                            HoverHandler { id: statusHover }
                        }
                    }
                }
                Flow {
                    Layout.row: 0
                    Layout.column: root.wideHeader ? 3 : 1
                    Layout.preferredWidth: implicitWidth
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignRight
                    spacing: root.tightGap
                    LauncherButton {
                        objectName: "refreshAction"
                        text: root.dataView.refresh_button.text
                        enabled: root.dataView.refresh_button.enabled
                        command: "refresh"
                        glyph: "refresh"
                    }
                    LauncherButton {
                        id: settingsButton
                        objectName: "settingsAction"
                        text: "환경 설정"
                        glyph: "settings"
                        selected: settings.visible
                        onClicked: settings.visible ? settings.close() : settings.open()
                    }
                }
                LauncherButton {
                    objectName: "updateLauncherAction"
                    Layout.row: root.wideHeader ? 0 : 2
                    Layout.column: root.wideHeader ? 2 : 0
                    Layout.columnSpan: root.wideHeader ? 1 : 2
                    Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
                    text: root.dataView.launcher_update_button.text
                    visible: root.dataView.launcher_update_button.visible
                    enabled: root.dataView.launcher_update_button.enabled
                    command: "launcher"
                    glyph: "download"
                    emphasis: true
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.line }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            ScrollView {
                id: library
                objectName: "library"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                Item {
                    width: library.availableWidth
                    implicitHeight: workspace.implicitHeight + 2 * root.inset
                    ColumnLayout {
                        id: workspace
                        width: Math.min(parent.width - 2 * root.inset, 1460)
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: root.inset
                        spacing: root.gap
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 13
                            Rectangle {
                                Layout.alignment: Qt.AlignTop
                                Layout.topMargin: 4
                                Layout.preferredWidth: 5
                                Layout.preferredHeight: root.compact ? 26 : 33
                                radius: 2.5
                                color: root.primaryFill
                            }
                            ColumnLayout {
                                spacing: 5
                                Caption { text: "내 작업 도구"; color: root.ink; font.pixelSize: root.compact ? 27 : 35; font.bold: true }
                                Caption { text: "필요한 제작 도구를 설치하고 실행하세요."; font.pixelSize: root.compact ? 14 : 17 }
                            }
                        }
                        GridLayout {
                            objectName: "toolGrid"
                            Layout.fillWidth: true
                            columns: root.width < 660 ? 1
                                    : Math.max(1, Math.min(3, Math.floor((workspace.width + root.gap)
                                                                       / (root.cardWidth + root.gap))))
                            rowSpacing: root.gap
                            columnSpacing: root.gap
                            Repeater { model: launcher.rows; delegate: ToolCard {} }
                        }
                        Caption {
                            Layout.fillWidth: true
                            visible: launcher.rows.length === 0
                            text: "표시할 프로그램이 없습니다. 업데이트 확인을 눌러 목록을 가져오세요."
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
            Rectangle {
                objectName: "dockedDetail"
                visible: root.detailOpen && root.dockDetail
                Layout.fillHeight: true
                Layout.preferredWidth: Math.min(470, root.width * 0.335)
                color: root.softPanel
                Rectangle { width: 1; height: parent.height; color: root.line }
                Loader {
                    id: dockLoader
                    anchors.fill: parent
                    active: parent.visible
                    opacity: active ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: root.transitionMs } }
                    sourceComponent: detailContent
                    onLoaded: item.focusClose()
                }
            }
        }

        Rectangle {
            objectName: "activityPanel"
            Layout.fillWidth: true
            visible: root.working || root.dataView.message.text.length > 0
            implicitHeight: banner.implicitHeight + 24
            color: root.checkFailed ? root.warningPad : root.sidebar
            RowLayout {
                id: banner
                anchors.fill: parent
                anchors.margins: 12
                spacing: root.tightGap
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Caption {
                        Layout.fillWidth: true
                        text: root.dataView.message.text
                        color: root.checkFailed ? root.amber : root.ink
                        wrapMode: Text.Wrap
                        maximumLineCount: 4
                        elide: Text.ElideRight
                        ToolTip.visible: activityHover.hovered
                        ToolTip.text: text
                        HoverHandler { id: activityHover }
                    }
                    WorkProgress {
                        objectName: "downloadProgress"
                        Layout.fillWidth: true
                        visible: root.working && root.dataView.activeApp === ""
                    }
                }
                LauncherButton {
                    objectName: "cancelAction"
                    text: "취소"
                    command: "cancel"
                    visible: root.dataView.cancel_button.visible
                    enabled: root.dataView.cancel_button.enabled
                }
            }
        }
    }

    Drawer {
        id: detail
        objectName: "toolDetail"
        edge: Qt.RightEdge
        width: root.width < 700 ? root.width : Math.min(root.width, 448)
        height: root.height
        modal: true
        focus: true
        interactive: false
        z: 10
        onOpened: if (contentItem.item) contentItem.item.focusClose()
        onClosed: if (!root.dockDetail) root.finishDetails()
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: root.softPanel; border.color: root.line }
        enter: Transition { NumberAnimation { property: "position"; duration: root.transitionMs; easing.type: Easing.OutCubic } }
        exit: Transition { NumberAnimation { property: "position"; duration: root.transitionMs; easing.type: Easing.InCubic } }
        contentItem: Loader {
            active: detail.visible
            sourceComponent: detailContent
        }
    }

    Component {
        id: detailContent
        Item {
            function focusClose() { closeDetail.forceActiveFocus() }
            Keys.onEscapePressed: {
                if (managementDisclosure.visible && root.managementExpanded) {
                    root.managementExpanded = false
                    managementDisclosure.forceActiveFocus()
                } else root.closeDetails()
            }
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: root.inset
                spacing: root.gap
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: "프로그램 정보"; color: root.ink; font.pixelSize: root.heading; font.bold: true }
                    Item { Layout.fillWidth: true }
                    LauncherButton {
                        id: closeDetail
                        objectName: "closeDetailAction"
                        text: "닫기"
                        glyph: "close"
                        onClicked: root.closeDetails()
                    }
                }
                ScrollView {
                    id: detailBody
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ColumnLayout {
                        width: detailBody.availableWidth
                        spacing: root.gap
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 14
                            Rectangle {
                                Layout.alignment: Qt.AlignTop
                                Layout.preferredWidth: 60
                                Layout.preferredHeight: 60
                                color: root.accentPad
                                radius: root.radius
                                AppIcon { anchors.fill: parent; anchors.margins: 7; appId: root.dataView.selectedId }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 5
                                Caption {
                                    objectName: "appTitle"
                                    Layout.fillWidth: true
                                    text: root.dataView.title.text
                                    color: root.ink
                                    font.pixelSize: 25
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                }
                                Caption {
                                    Layout.fillWidth: true
                                    text: root.dataView.description.text
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            rowSpacing: 9
                            columnSpacing: 14
                            Caption { text: "설치 상태" }
                            StatusPill {
                                text: root.dataView["설치 상태"] || "—"
                                tone: root.stateTone(text)
                                backgroundColor: tone === root.green ? root.installedPad
                                                 : tone === root.amber ? root.warningPad
                                                 : tone === root.accent ? root.accentPad : root.hover
                            }
                            Caption { text: "설치된 버전" }
                            Caption { Layout.fillWidth: true; text: root.dataView["설치 버전"] || "—"; color: root.ink; font.bold: true }
                            Caption { text: root.dataView.online ? "최신 버전 (카탈로그)" : "카탈로그 등록 버전" }
                            Caption { Layout.fillWidth: true; text: root.dataView["승인 버전"] || "—"; color: root.ink; font.bold: true; wrapMode: Text.Wrap }
                            Caption { text: "다운로드 용량" }
                            Caption { Layout.fillWidth: true; text: root.dataView["다운로드"] || "—"; color: root.ink; font.bold: true }
                        }
                        Caption {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: root.dataView.issues[root.dataView.selectedId] || ""
                            color: root.amber
                            wrapMode: Text.Wrap
                        }
                        LauncherButton {
                            objectName: "detailPrimaryAction"
                            Layout.fillWidth: true
                            text: root.dataView.primary.text
                            glyph: root.actionIcon(text)
                            command: "primary"
                            enabled: root.dataView.primary.enabled
                            emphasis: true
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.line }
                        RowLayout {
                            Layout.fillWidth: true
                            LauncherButton {
                                objectName: "notesDisclosure"
                                text: "변경 내역"
                                glyph: root.notesExpanded ? "up" : "down"
                                quiet: true
                                onClicked: root.notesExpanded = !root.notesExpanded
                            }
                            Item { Layout.fillWidth: true }
                            LauncherButton {
                                text: "진단 정보"
                                glyph: "info"
                                quiet: true
                                command: "details"
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.notesExpanded || opacity > 0
                            opacity: root.notesExpanded ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: root.transitionMs } }
                            spacing: root.tightGap
                            Repeater {
                                model: parent.visible ? root.dataView.noteGroups : []
                                delegate: Rectangle {
                                    id: releaseGroup
                                    required property var modelData
                                    Layout.fillWidth: true
                                    implicitHeight: releaseBody.implicitHeight + 22
                                    color: root.card
                                    radius: root.radius
                                    border.color: root.line
                                    ColumnLayout {
                                        id: releaseBody
                                        anchors.fill: parent
                                        anchors.margins: 11
                                        spacing: 6
                                        Flow {
                                            Layout.fillWidth: true
                                            visible: modelData.version !== ""
                                            spacing: 8
                                            StatusPill {
                                                text: modelData.version
                                                tone: root.accent
                                                backgroundColor: root.accentPad
                                            }
                                            Caption {
                                                width: Math.min(implicitWidth, parent.width)
                                                height: Math.max(23, implicitHeight)
                                                wrapMode: Text.Wrap
                                                verticalAlignment: Text.AlignVCenter
                                                text: modelData.title
                                                visible: text.length > 0
                                                color: root.ink
                                                font.bold: true
                                            }
                                        }
                                        Repeater {
                                            model: releaseGroup.modelData.blocks
                                            delegate: RowLayout {
                                                required property var modelData
                                                Layout.fillWidth: true
                                                spacing: 6
                                                Caption {
                                                    visible: modelData.bullet
                                                    text: "•"
                                                    color: root.accent
                                                    Layout.alignment: Qt.AlignTop
                                                }
                                                Caption {
                                                    Layout.fillWidth: true
                                                    text: modelData.text
                                                    color: modelData.level ? root.ink : root.muted
                                                    font.bold: modelData.level > 0
                                                    wrapMode: Text.Wrap
                                                    lineHeight: 1.16
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: root.dataView.selectedInstalled
                            spacing: root.tightGap
                            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.line }
                            LauncherButton {
                                id: managementDisclosure
                                objectName: "managementAction"
                                Layout.fillWidth: true
                                text: root.managementExpanded ? "고급 관리 접기" : "고급 관리"
                                glyph: root.managementExpanded ? "up" : "down"
                                onClicked: {
                                    root.managementExpanded = !root.managementExpanded
                                    if (root.managementExpanded) {
                                        Qt.callLater(function() {
                                            const flick = detailBody.contentItem
                                            const bottom = managementActions.mapToItem(
                                                flick.contentItem, 0, managementActions.height).y
                                            flick.contentY = Math.max(flick.contentY, bottom - flick.height)
                                        })
                                    }
                                }
                            }
                            ColumnLayout {
                                id: managementActions
                                objectName: "managementActions"
                                Layout.fillWidth: true
                                visible: root.managementExpanded
                                spacing: root.tightGap
                                readonly property string versionNotice:
                                    visible && !root.working && root.dataView.versions_button.enabled
                                    ? launcher.versionNotice() : ""
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: root.tightGap
                                    LauncherButton {
                                        objectName: "folderAction"
                                        text: "설치 위치 열기"
                                        command: "folder"
                                        enabled: !root.working && root.dataView.folder_button.enabled
                                    }
                                    LauncherButton {
                                        objectName: "versionsAction"
                                        text: "설치된 버전 선택"
                                        command: "versions"
                                        enabled: !root.working && root.dataView.versions_button.enabled
                                                 && managementActions.versionNotice === ""
                                    }
                                    Item { Layout.fillWidth: true }
                                }
                                Caption {
                                    Layout.fillWidth: true
                                    visible: text !== ""
                                    text: root.working ? "작업이 끝난 뒤 관리할 수 있습니다."
                                          : !root.dataView.versions_button.enabled
                                            ? "실행 중이거나 복구가 필요한 프로그램은 버전을 전환할 수 없습니다."
                                            : managementActions.versionNotice
                                    font.pixelSize: root.small
                                    wrapMode: Text.WordWrap
                                }
                                LauncherButton {
                                    objectName: "removeAction"
                                    text: "프로그램 제거"
                                    destructive: true
                                    command: "remove"
                                    enabled: !root.working && root.dataView.remove_button.enabled
                                }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: root.dataView.launch_current.visible
                    Item { Layout.fillWidth: true }
                    LauncherButton {
                        id: currentLaunch
                        text: "실행"
                        glyph: "play"
                        command: "launch"
                        visible: root.dataView.launch_current.visible
                        enabled: root.dataView.launch_current.enabled
                    }
                }
            }
        }
    }

    component Panel: Dialog {
        parent: root
        z: 30
        anchors.centerIn: parent
        width: Math.min(480, root.width - 48)
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape
        font.family: root.productFont
        palette.highlight: root.accent
        palette.window: root.card
        palette.windowText: root.ink
        palette.text: root.ink
        palette.buttonText: root.ink
        palette.base: root.sidebar
        palette.button: root.card
        background: Rectangle { color: root.card; radius: root.radius; border.color: root.line }
    }

    Popup {
        id: settings
        objectName: "settingsDialog"
        parent: root
        z: 25
        modal: true
        dim: false
        focus: true
        padding: root.gap
        width: Math.min(388, root.width - 2 * root.tightGap)
        function place() {
            const anchor = settingsButton.mapToItem(root, settingsButton.width, settingsButton.height)
            x = Math.max(root.tightGap, Math.min(anchor.x - width, root.width - width - root.tightGap))
            y = Math.max(root.tightGap, Math.min(anchor.y + root.tightGap, root.height - height - root.tightGap))
        }
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnReleaseOutside
        onAboutToShow: {
            sourceDisclosure.expanded = false
            place()
        }
        onHeightChanged: if (visible) place()
        Connections {
            target: root
            function onWidthChanged() { if (settings.visible) Qt.callLater(settings.place) }
            function onHeightChanged() { if (settings.visible) Qt.callLater(settings.place) }
        }
        onOpened: (launcher.dark ? darkTheme : lightTheme).forceActiveFocus()
        onClosed: settingsButton.forceActiveFocus()
        background: Rectangle { color: root.card; radius: root.radius; border.color: root.line }
        contentItem: ColumnLayout {
            spacing: root.tightGap
            RowLayout {
                Layout.fillWidth: true
                Caption { text: "환경 설정"; color: root.ink; font.pixelSize: root.heading; font.bold: true }
                Item { Layout.fillWidth: true }
                LauncherButton {
                    objectName: "closeSettingsAction"
                    text: "닫기"
                    glyph: "close"
                    quiet: true
                    onClicked: settings.close()
                }
            }
            Caption { text: "화면"; color: root.ink; font.weight: Font.DemiBold }
            Caption { text: "테마"; font.pixelSize: root.small }
            RowLayout {
                Layout.fillWidth: true
                spacing: 4
                LauncherButton {
                    id: darkTheme
                    objectName: "darkThemeAction"
                    Layout.fillWidth: true
                    text: "다크"
                    selected: launcher.dark
                    Accessible.checkable: true
                    Accessible.checked: selected
                    onClicked: launcher.setDark(true)
                }
                LauncherButton {
                    id: lightTheme
                    objectName: "lightThemeAction"
                    Layout.fillWidth: true
                    text: "라이트"
                    selected: !launcher.dark
                    Accessible.checkable: true
                    Accessible.checked: selected
                    onClicked: launcher.setDark(false)
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: root.tightGap
                Layout.preferredHeight: 1
                color: root.line
            }
            LauncherButton {
                id: sourceDisclosure
                objectName: "updateSourceAction"
                property bool expanded: false
                text: "업데이트 출처"
                glyph: expanded ? "up" : "down"
                quiet: true
                onClicked: expanded = !expanded
            }
            Caption {
                objectName: "updateSourceValue"
                Layout.fillWidth: true
                visible: sourceDisclosure.expanded
                text: root.dataView.connectedRepo || "배포 저장소 미지정"
                wrapMode: Text.Wrap
            }
            LauncherButton {
                text: "연결 설정"
                visible: sourceDisclosure.expanded && root.dataView.connection_button.visible
                enabled: root.dataView.connection_button.enabled
                onClicked: { settings.close(); launcher.act("configure") }
            }
        }
    }

    Panel {
        id: approval
        objectName: "approvalDialog"
        property Item returnFocus: null
        readonly property bool removal: launcher.prompt.title === "프로그램 제거"
        closePolicy: Popup.CloseOnEscape
                     | (launcher.prompt.information ? Popup.CloseOnReleaseOutside : Popup.NoAutoClose)
        title: launcher.prompt.title || ""
        onOpened: cancelApproval.forceActiveFocus()
        onClosed: {
            if (launcher.prompt.title) launcher.reply(false, -1)
            if (returnFocus && returnFocus.visible && returnFocus.enabled) returnFocus.forceActiveFocus()
            else if (root.detailOpen) {
                const panel = root.dockDetail ? dockLoader.item : detail.contentItem.item
                if (panel) panel.focusClose()
            }
            returnFocus = null
        }
        header: Item {
            implicitHeight: approvalHeading.implicitHeight + root.tightGap
            RowLayout {
                id: approvalHeading
                anchors.fill: parent
                anchors.leftMargin: root.gap
                anchors.rightMargin: root.gap
                anchors.topMargin: root.tightGap
                Caption {
                    Layout.fillWidth: true
                    text: approval.title
                    color: root.ink
                    font.pixelSize: root.heading
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                LauncherButton {
                    objectName: "closeApprovalAction"
                    text: "닫기"
                    glyph: "close"
                    quiet: true
                    onClicked: approval.close()
                }
            }
        }
        contentItem: ColumnLayout {
            spacing: 10
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: launcher.prompt.information ? 270 : Math.min(185, Math.max(60, dialogText.contentHeight + 6))
                contentWidth: availableWidth
                TextArea {
                    id: dialogText
                    text: launcher.prompt.text || ""
                    textFormat: TextEdit.PlainText
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.Wrap
                    color: root.ink
                    font.pixelSize: root.bodyText
                    background: null
                }
            }
            ComboBox {
                id: choices
                objectName: "versionChoices"
                Layout.fillWidth: true
                model: launcher.prompt.choices || []
                visible: count > 0
            }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                LauncherButton {
                    id: cancelApproval
                    objectName: "cancelApprovalAction"
                    text: launcher.prompt.information ? "닫기" : "취소"
                    onClicked: { launcher.reply(false, -1); approval.close() }
                }
                LauncherButton {
                    objectName: "confirmAction"
                    text: approval.removal ? "제거" : "확인"
                    destructive: approval.removal
                    emphasis: !approval.removal
                    visible: !launcher.prompt.information
                    onClicked: { launcher.reply(true, choices.currentIndex); approval.close() }
                }
            }
        }
    }

    Connections {
        target: launcher
        function onPromptChanged() {
            if (launcher.prompt.title) {
                if (!approval.visible) approval.returnFocus = root.Window.window.activeFocusItem
                approval.open()
            } else approval.close()
        }
    }
}
