import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: root
    objectName: "southpawQuickLauncher"
    width: 1200
    height: 780

    readonly property var dataView: launcher.view
    // Shared visual vocabulary for the library, detail view and dialogs.
    readonly property color canvas: launcher.dark ? "#151822" : "#f4f4f8"
    readonly property color sidebar: launcher.dark ? "#1b1e2b" : "#eaeaf2"
    readonly property color card: launcher.dark ? "#202432" : "#ffffff"
    readonly property color line: launcher.dark ? "#393e51" : "#d9d9e6"
    readonly property color ink: launcher.dark ? "#f5f3ff" : "#222335"
    readonly property color muted: launcher.dark ? "#b7b9cb" : "#565a70"
    readonly property color accent: launcher.dark ? "#c5b6ff" : "#5034a4"
    readonly property color accentPad: launcher.dark ? "#302743" : "#e8dfff"
    readonly property color accentInk: launcher.dark ? "#201633" : "#ffffff"
    readonly property color hover: launcher.dark ? "#292d3e" : "#e2e2ed"
    readonly property color green: launcher.dark ? "#8ed4b4" : "#126044"
    readonly property color amber: launcher.dark ? "#ffd29b" : "#80522c"
    readonly property color warningPad: launcher.dark ? "#332a25" : "#f6eadd"
    readonly property int small: 12
    readonly property int bodyText: 14
    readonly property int heading: 17
    readonly property int tightGap: 8
    readonly property int gap: 16
    readonly property int radius: 10
    readonly property int controlHeight: 40
    readonly property string productFont: "Malgun Gothic"
    readonly property bool compact: width < 820
    readonly property int cardWidth: 300
    readonly property int inset: compact ? 16 : 24
    readonly property int transitionMs: 140
    readonly property bool working: dataView.busy || dataView.bridgeBusy
    readonly property string connectionText: {
        if (dataView.checking) return "업데이트 확인 중"
        if (dataView.catalogError || dataView.lastCheck === "failed") return dataView.server_status.text
        if (dataView.online) return dataView.latestVerified ? "최신 런처 사용 중" : "업데이트 확인 완료"
        if (dataView.lastCheck === "" && dataView.server_status.text === "오프라인 · 미확인") return "아직 확인하지 않음"
        return dataView.server_status.text
    }

    function stateTone(state) {
        if (state === "설치됨" || state === "설치 완료" || state === "최신 버전")
            return green
        if (state === "업데이트 가능" || state === "이전 버전 사용 중 · 업데이트 가능")
            return accent
        if (state === "복구 필요" || state === "설치 확인 필요"
                || state === "설치 완료 · 목록 오류(업데이트 차단)")
            return amber
        return muted
    }

    component Caption: Label {
        color: root.muted
        font.family: root.productFont
        font.pixelSize: root.bodyText
        textFormat: Text.PlainText
    }

    component Action: Button {
        id: button
        property string command: ""
        property bool emphasis: false
        property bool destructive: false
        property bool quiet: false
        implicitHeight: root.controlHeight
        implicitWidth: Math.max(78, contentItem.implicitWidth + 28)
        leftPadding: 12
        rightPadding: 12
        font.pixelSize: root.bodyText
        font.family: root.productFont
        font.bold: emphasis
        hoverEnabled: true
        onClicked: if (command) launcher.act(command)
        contentItem: Label {
            text: button.text
            textFormat: Text.PlainText
            color: !button.enabled ? root.muted : button.emphasis ? root.accentInk : button.destructive ? root.amber : root.ink
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            font: button.font
        }
        background: Rectangle {
            radius: root.radius
            color: button.enabled && button.emphasis
                   ? (button.down ? Qt.darker(root.accent, 1.15) : root.accent)
                   : button.enabled && (button.hovered || button.down) ? root.hover
                   : button.quiet ? "transparent" : root.card
            border.color: button.activeFocus ? root.accent
                          : button.quiet || (button.emphasis && button.enabled) ? "transparent" : root.line
            border.width: button.activeFocus ? 2 : 1
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
            if (running) return "실행 중"
            if (modelData.problem || modelData.pending) return "설치 확인 필요"
            if (canUpdate) return "업데이트 가능"
            return modelData.installed ? "설치됨" : "미설치"
        }
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        implicitHeight: 205
        radius: root.radius
        color: mouse.hovered ? root.hover : root.card
        border.width: 1
        border.color: detailsButton.activeFocus || primary.activeFocus || active
                      || (detail.visible && root.dataView.selectedId === modelData.id) ? root.accent : root.line
        HoverHandler { id: mouse }
        Behavior on color { ColorAnimation { duration: 110 } }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.gap
            spacing: root.tightGap
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 43
                    Layout.preferredHeight: 43
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
                        font.pixelSize: root.heading
                        font.bold: true
                        elide: Text.ElideRight
                        text: card.modelData.title
                    }
                    Caption {
                        Layout.fillWidth: true
                        font.pixelSize: root.small
                        elide: Text.ElideRight
                        color: root.stateTone(card.statusText)
                        text: card.statusText + (card.modelData.version && !card.active ? "  ·  " + card.modelData.version : "")
                    }
                }
            }
            Caption {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 39
                Layout.alignment: Qt.AlignTop
                maximumLineCount: 2
                elide: Text.ElideRight
                wrapMode: Text.Wrap
                lineHeight: 1.14
                text: card.modelData.description
            }
            WorkProgress {
                Layout.fillWidth: true
                visible: card.active
            }
            RowLayout {
                Layout.fillWidth: true
                Action {
                    id: primary
                    objectName: "primaryAction"
                    Layout.preferredWidth: 86
                    emphasis: true
                    text: card.running ? "실행 중" : card.modelData.problem ? "확인" : card.modelData.pending ? "복구 확인" : card.canUpdate ? "업데이트"
                          : card.modelData.installed ? "실행" : "설치"
                    enabled: !root.working && !card.running
                             && (card.modelData.problem || card.modelData.pending || card.canDownload || card.runnable)
                    onClicked: {
                        if (card.modelData.problem) root.openDetails(card.modelData.id)
                        else launcher.actOnApp(card.modelData.id, "primary")
                    }
                }
                Action {
                    quiet: true
                    text: "실행"
                    visible: card.canUpdate && card.runnable
                    enabled: !root.working && !card.running
                    onClicked: launcher.actOnApp(card.modelData.id, "launch")
                }
                Item { Layout.fillWidth: true }
                Action {
                    id: detailsButton
                    objectName: "detailsAction"
                    quiet: true
                    text: "자세히"
                    enabled: !root.working || card.active
                    Accessible.name: card.modelData.title + " 자세히"
                    onClicked: root.openDetails(card.modelData.id)
                }
            }
        }
    }

    function openDetails(appId) {
        if (launcher.selectApp(appId)) {
            notesDisclosure.checked = false
            detail.open()
        }
    }

    Rectangle { anchors.fill: parent; color: root.canvas }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: toolbar.implicitHeight + 2 * root.inset
            color: root.sidebar
            RowLayout {
                id: toolbar
                anchors.fill: parent
                anchors.margins: root.inset
                spacing: 12
                Image {
                    source: launcher.brandIcon
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    fillMode: Image.PreserveAspectFit
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Caption {
                        text: "Southpaw Tools"
                        color: root.ink
                        font.bold: true
                        font.pixelSize: 21
                    }
                    Caption {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        font.pixelSize: root.small
                        text: root.dataView.launcher_versions.text
                    }
                    Caption {
                        objectName: "connectionState"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        font.pixelSize: root.small
                        text: root.connectionText
                        color: root.dataView.checking ? root.accent : root.dataView.online ? root.green
                               : root.dataView.catalogError || root.dataView.lastCheck === "failed" ? root.amber : root.muted
                        ToolTip.visible: statusHover.hovered
                        ToolTip.text: root.dataView.server_status.tip
                        HoverHandler { id: statusHover }
                    }
                }
                Flow {
                    Layout.preferredWidth: root.compact ? 140 : implicitWidth
                    Layout.alignment: Qt.AlignVCenter
                    layoutDirection: Qt.RightToLeft
                    spacing: root.tightGap
                    Action {
                        objectName: "settingsAction"
                        quiet: true
                        text: "환경 설정"
                        onClicked: settings.open()
                    }
                    Action {
                        objectName: "refreshAction"
                        text: root.dataView.refresh_button.text
                        enabled: root.dataView.refresh_button.enabled
                        command: "refresh"
                    }
                    Action {
                        objectName: "updateLauncherAction"
                        text: root.dataView.launcher_update_button.text
                        visible: root.dataView.launcher_update_button.visible
                        enabled: root.dataView.launcher_update_button.enabled
                        command: "launcher"
                        emphasis: true
                    }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: root.line }

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
                    width: Math.min(parent.width - 2 * root.inset, 1240)
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: root.inset
                    spacing: root.gap
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        Caption { text: "내 작업 도구"; color: root.ink; font.pixelSize: 28; font.bold: true }
                        Caption { text: "필요한 제작 도구를 설치하고 실행하세요." }
                    }
                    GridLayout {
                        objectName: "toolGrid"
                        Layout.fillWidth: true
                        columns: Math.max(1, Math.min(3, Math.floor((workspace.width + root.gap) / (root.cardWidth + root.gap))))
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
            objectName: "activityPanel"
            Layout.fillWidth: true
            visible: root.working || root.dataView.message.text.length > 0
            implicitHeight: banner.implicitHeight + 24
            color: root.dataView.catalogError ? root.warningPad : root.sidebar
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
                        color: root.dataView.catalogError ? root.amber : root.ink
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
                Action {
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
        width: Math.min(root.width, 440)
        height: root.height
        modal: true
        focus: true
        interactive: false
        z: 10
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: root.sidebar; border.color: root.line }
        enter: Transition { NumberAnimation { property: "position"; duration: root.transitionMs; easing.type: Easing.OutCubic } }
        exit: Transition { NumberAnimation { property: "position"; duration: root.transitionMs; easing.type: Easing.InCubic } }
        contentItem: Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: root.inset
                spacing: root.gap
                RowLayout {
                    Layout.fillWidth: true
                    Caption { text: "프로그램 정보"; color: root.ink; font.pixelSize: root.heading; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Action { objectName: "closeDetailAction"; text: "닫기"; quiet: true; onClicked: detail.close() }
                }
                ScrollView {
                    id: detailBody
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ColumnLayout {
                        width: detailBody.availableWidth
                        spacing: root.gap
                        AppIcon {
                            Layout.preferredWidth: 56
                            Layout.preferredHeight: 56
                            appId: root.dataView.selectedId
                        }
                        Caption {
                            objectName: "appTitle"
                            Layout.fillWidth: true
                            text: root.dataView.title.text
                            color: root.ink
                            font.pixelSize: 27
                            font.bold: true
                            wrapMode: Text.Wrap
                        }
                        Caption {
                            Layout.fillWidth: true
                            text: root.dataView.description.text
                            wrapMode: Text.Wrap
                        }
                        Repeater {
                            model: [
                                {label: "설치 상태", value: root.dataView["설치 상태"]},
                                {label: "설치 버전", value: root.dataView["설치 버전"]},
                                {label: root.dataView.latest_app_label.text, value: root.dataView["승인 버전"]},
                                {label: "다운로드", value: root.dataView["다운로드"]}
                            ]
                            delegate: RowLayout {
                                required property var modelData
                                Layout.fillWidth: true
                                Caption { Layout.preferredWidth: 125; text: modelData.label; wrapMode: Text.Wrap }
                                Caption {
                                    Layout.fillWidth: true
                                    text: modelData.value || "—"
                                    color: root.ink
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                        Action {
                            id: notesDisclosure
                            objectName: "notesDisclosure"
                            text: checked ? "변경 내역 접기" : "변경 내역 보기"
                            checkable: true
                        }
                        Caption {
                            Layout.fillWidth: true
                            visible: notesDisclosure.checked
                            text: root.dataView.notes.text
                            wrapMode: Text.Wrap
                            lineHeight: 1.22
                            leftPadding: 4
                            rightPadding: 4
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Action {
                        objectName: "managementAction"
                        text: "프로그램 관리"
                        enabled: !root.working
                        onClicked: management.open()
                    }
                    Item { Layout.fillWidth: true }
                    Action {
                        text: "실행"
                        command: "launch"
                        visible: root.dataView.launch_current.visible
                        enabled: root.dataView.launch_current.enabled
                    }
                    Action {
                        objectName: "detailPrimaryAction"
                        text: root.dataView.primary.text
                        command: "primary"
                        enabled: root.dataView.primary.enabled
                        emphasis: true
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

    Panel {
        id: settings
        objectName: "settingsDialog"
        title: "환경 설정"
        contentItem: ColumnLayout {
            spacing: 10
            Switch {
                objectName: "themeSwitch"
                text: "라이트 테마"
                checked: !launcher.dark
                onToggled: launcher.setDark(!checked)
            }
            Caption {
                Layout.fillWidth: true
                text: root.dataView.connectedRepo || "배포 저장소 미지정"
                wrapMode: Text.WordWrap
            }
            Action {
                text: "연결 설정"
                visible: root.dataView.connection_button.visible
                enabled: root.dataView.connection_button.enabled
                onClicked: { settings.close(); launcher.act("configure") }
            }
            Action { text: "닫기"; onClicked: settings.close() }
        }
    }

    Panel {
        id: management
        objectName: "managementDialog"
        title: "프로그램 관리"
        contentItem: ColumnLayout {
            spacing: 8
            Action {
                Layout.fillWidth: true
                text: "설치 위치 열기"
                enabled: root.dataView.folder_button.enabled
                onClicked: { management.close(); launcher.act("folder") }
            }
            Action {
                Layout.fillWidth: true
                text: "설치된 버전 선택"
                enabled: root.dataView.versions_button.enabled
                onClicked: { management.close(); launcher.act("versions") }
            }
            Action {
                Layout.fillWidth: true
                text: "상세 정보"
                onClicked: { management.close(); launcher.act("details") }
            }
            Action {
                objectName: "removeAction"
                Layout.fillWidth: true
                text: "제거"
                destructive: true
                enabled: root.dataView.remove_button.enabled
                onClicked: { management.close(); launcher.act("remove") }
            }
        }
    }

    Panel {
        id: approval
        objectName: "approvalDialog"
        title: launcher.prompt.title || ""
        onClosed: if (launcher.prompt.title) launcher.reply(false, -1)
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
                Action {
                    text: launcher.prompt.information ? "닫기" : "취소"
                    onClicked: { launcher.reply(false, -1); approval.close() }
                }
                Action {
                    objectName: "confirmAction"
                    text: "확인"
                    emphasis: true
                    visible: !launcher.prompt.information
                    onClicked: { launcher.reply(true, choices.currentIndex); approval.close() }
                }
            }
        }
    }

    Connections {
        target: launcher
        function onPromptChanged() {
            if (launcher.prompt.title) approval.open()
            else approval.close()
        }
    }
}
