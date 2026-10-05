import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "ashis.bikram"
  ipcTarget: "ashis.bikram"
  manageIpc: false

  property var anchorItem: null
  property bool openedFromHotkey: false
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root

  property string label: "…"
  property string mark: "…"
  property string status: ""
  property string noticeLine: ""
  property var todayInfo: ({})
  property var monthInfo: ({})
  property int viewYear: 0
  property int viewMonth: 0
  property int selectedDay: 0
  property string eraNow: "both"
  property string scriptNow: "ne"
  property bool todayAgain: false
  property bool monthAgain: false

  readonly property color ink: bar ? bar.foreground : Color.foreground
  readonly property string face: bar ? bar.fontFamily : Style.font.family
  readonly property var cells: monthInfo && monthInfo.cells ? monthInfo.cells : []
  readonly property var picked: {
    for (var i = 0; i < cells.length; i++) {
      if (cells[i].day === selectedDay) return cells[i]
    }
    return null
  }

  function scriptPath() {
    var url = String(Qt.resolvedUrl("bikram.py"))
    if (url.indexOf("file://") === 0) url = url.slice(7)
    return decodeURIComponent(url)
  }

  function pythonCommand(args) {
    var command = ["/usr/bin/python3", "-I", "-B", scriptPath()]
    for (var i = 0; i < args.length; i++) command.push(args[i])
    return command
  }

  function open() {
    openedFromHotkey = false
    setCenterHoverRevealSuppressed(false)
    root.controller.show()
    refresh(setting("era", "both"), setting("script", "ne"))
    checkNotice()
  }

  function openFromHotkey() {
    openedFromHotkey = true
    root.controller.show()
    refresh(setting("era", "both"), setting("script", "ne"))
    checkNotice()
    Qt.callLater(function() {
      if (root.opened) setCenterHoverRevealSuppressed(true)
    })
  }

  function close() {
    setCenterHoverRevealSuppressed(false)
    root.controller.hide()
  }

  function toggle() {
    if (root.opened) root.close()
    else root.openFromHotkey()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  function setCenterHoverRevealSuppressed(value) {
    if (root.bar && typeof root.bar.setCenterHoverRevealSuppressed === "function")
      root.bar.setCenterHoverRevealSuppressed(value)
    else if (root.bar && "centerHoverRevealSuppressed" in root.bar)
      root.bar.centerHoverRevealSuppressed = value
  }

  function refresh(era, script) {
    eraNow = era || "both"
    scriptNow = script || "ne"
    if (todayProc.running) {
      todayAgain = true
      return
    }
    todayProc.command = pythonCommand(["today", "--era", eraNow, "--script", scriptNow])
    todayProc.running = true
  }

  function loadMonth() {
    if (viewYear < 1975 || viewMonth < 1) return
    if (monthProc.running) {
      monthAgain = true
      return
    }
    monthProc.command = pythonCommand(["month", "--year", String(viewYear), "--month", String(viewMonth), "--script", scriptNow])
    monthProc.running = true
  }

  function shiftMonth(delta) {
    var month = viewMonth + delta
    var year = viewYear
    if (month < 1) {
      month = 12
      year -= 1
    } else if (month > 12) {
      month = 1
      year += 1
    }
    if (year < 1975 || year > 2100) return
    viewYear = year
    viewMonth = month
    selectedDay = 0
    loadMonth()
  }

  function checkNotice() {
    if (noticeProc.running) return
    noticeProc.command = pythonCommand(["notice"])
    noticeProc.running = true
  }

  function applyNotice(raw) {
    var parsed
    try {
      parsed = JSON.parse(raw)
    } catch (e) {
      noticeLine = ""
      return
    }
    noticeLine = parsed.line || ""
  }

  function choose(key, value) {
    if (hostWidget && hostWidget.store) hostWidget.store(key, value)
  }

  function applyToday(raw) {
    var parsed
    try {
      parsed = JSON.parse(raw)
    } catch (e) {
      status = "Calendar returned something unreadable"
      return
    }
    if (parsed.error) {
      status = parsed.error
      return
    }
    todayInfo = parsed
    label = parsed.label || "…"
    mark = parsed.mark || "…"
    status = ""
    if (viewYear === 0 && parsed.bs) {
      viewYear = parsed.bs.year
      viewMonth = parsed.bs.month
      selectedDay = parsed.bs.day
    }
    if (viewYear !== 0) loadMonth()
  }

  function applyMonth(raw) {
    var parsed
    try {
      parsed = JSON.parse(raw)
    } catch (e) {
      status = "Month returned something unreadable"
      return
    }
    if (parsed.error) {
      status = parsed.error
      return
    }
    monthInfo = parsed
    if (selectedDay === 0 && parsed.cells) {
      var fallback = 1
      for (var i = 0; i < parsed.cells.length; i++) {
        if (parsed.cells[i].today) fallback = parsed.cells[i].day
      }
      selectedDay = fallback
    }
  }

  function hasHoliday(cell) {
    return !!(cell && cell.holidays && cell.holidays.length > 0)
  }

  function holidayLines(cell) {
    if (!cell || !cell.holidays) return ""
    var lines = []
    for (var i = 0; i < cell.holidays.length; i++) {
      var item = cell.holidays[i]
      lines.push(item.scope ? item.name + " · " + item.scope : item.name)
    }
    return lines.join("\n")
  }

  IpcHandler {
    target: root.ipcTarget
    function open(): void { root.openFromHotkey() }
    function close(): void { root.close() }
    function show(): void { root.openFromHotkey() }
    function hide(): void { root.close() }
    function toggle(): void { root.toggle() }
    function refresh(): void { root.refresh(root.setting("era", "both"), root.setting("script", "ne")) }
  }

  Process {
    id: todayProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyToday(text || "")
    }
    onExited: function(code) {
      if (code !== 0 && root.status === "") root.status = "Calendar stopped"
      if (root.todayAgain) {
        root.todayAgain = false
        root.refresh(root.eraNow, root.scriptNow)
      }
    }
  }

  Process {
    id: monthProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyMonth(text || "")
    }
    onExited: function(code) {
      if (code !== 0 && root.status === "") root.status = "Month stopped"
      if (root.monthAgain) {
        root.monthAgain = false
        root.loadMonth()
      }
    }
  }

  Process {
    id: noticeProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyNotice(text || "")
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(300))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        interactive: contentHeight > height

        Column {
          id: column
          width: parent.width
          spacing: Style.space(10)
          topPadding: Style.space(4)

          Row {
            width: parent.width - Style.space(8)
            x: Style.space(4)
            spacing: Style.space(8)

            Text {
              text: "‹"
              color: root.ink
              font.family: root.face
              font.pixelSize: Style.font.title
              anchors.verticalCenter: parent.verticalCenter
              MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.shiftMonth(-1)
              }
            }

            Column {
              width: parent.width - Style.space(48)
              spacing: 2
              Text {
                width: parent.width
                text: root.monthInfo.title || "Bikram Sambat"
                color: root.ink
                font.family: root.face
                font.pixelSize: Style.font.heading
                elide: Text.ElideRight
              }
              Text {
                width: parent.width
                text: root.picked && root.picked.ad_short
                      ? root.picked.weekday_en + " · " + root.picked.ad_short
                      : root.status
                color: root.ink
                opacity: 0.6
                font.family: root.face
                font.pixelSize: Style.font.bodySmall
                elide: Text.ElideRight
              }
            }

            Text {
              text: "›"
              color: root.ink
              font.family: root.face
              font.pixelSize: Style.font.title
              anchors.verticalCenter: parent.verticalCenter
              MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.shiftMonth(1)
              }
            }
          }

          Row {
            x: Style.space(4)
            spacing: Style.space(6)
            Repeater {
              model: [
                { key: "bs", text: "BS" },
                { key: "both", text: "Both" },
                { key: "ad", text: "AD" },
                { key: "script", text: root.scriptNow === "ne" ? "अ" : "A" }
              ]
              delegate: Item {
                required property var modelData
                width: label.implicitWidth + Style.space(16)
                height: Style.space(24)
                Rectangle {
                  anchors.fill: parent
                  radius: Style.space(6)
                  color: root.ink
                  opacity: modelData.key === "script" ? 0.08 : (modelData.key === root.eraNow ? 0.16 : 0.06)
                }
                Text {
                  id: label
                  anchors.centerIn: parent
                  text: modelData.text
                  color: root.ink
                  font.family: root.face
                  font.pixelSize: Style.font.bodySmall
                }
                MouseArea {
                  anchors.fill: parent
                  cursorShape: Qt.PointingHandCursor
                  onClicked: {
                    if (modelData.key === "script") root.choose("script", root.scriptNow === "ne" ? "en" : "ne")
                    else root.choose("era", modelData.key)
                  }
                }
              }
            }
          }

          Grid {
            x: Style.space(4)
            columns: 7
            columnSpacing: Style.space(2)
            rowSpacing: Style.space(2)

            Repeater {
              model: root.monthInfo.headers || ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
              delegate: Text {
                required property string modelData
                width: Style.space(36)
                height: Style.space(16)
                text: modelData
                color: root.ink
                opacity: 0.45
                font.family: root.face
                font.pixelSize: Style.font.caption
                horizontalAlignment: Text.AlignHCenter
              }
            }
          }

          Grid {
            x: Style.space(4)
            columns: 7
            columnSpacing: Style.space(2)
            rowSpacing: Style.space(2)

            Repeater {
              model: root.cells
              delegate: Item {
                required property var modelData
                width: Style.space(36)
                height: Style.space(32)

                Rectangle {
                  anchors.fill: parent
                  radius: Style.space(6)
                  color: root.ink
                  opacity: !modelData.day ? 0 : (modelData.today ? 0.16 : (modelData.day === root.selectedDay ? 0.1 : 0))
                }

                Text {
                  anchors.centerIn: parent
                  anchors.verticalCenterOffset: root.hasHoliday(modelData) ? -2 : 0
                  text: modelData.day ? modelData.text : ""
                  color: root.ink
                  opacity: modelData.saturday ? 0.55 : 1
                  font.family: root.face
                  font.pixelSize: Style.font.bodySmall
                }

                Rectangle {
                  visible: root.hasHoliday(modelData)
                  width: 4
                  height: 4
                  radius: 2
                  color: root.ink
                  anchors.horizontalCenter: parent.horizontalCenter
                  anchors.bottom: parent.bottom
                  anchors.bottomMargin: 3
                }

                MouseArea {
                  anchors.fill: parent
                  enabled: modelData.day > 0
                  onClicked: root.selectedDay = modelData.day
                }
              }
            }
          }

          Column {
            width: parent.width - Style.space(8)
            x: Style.space(4)
            spacing: 2

            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              text: {
                var lines = root.holidayLines(root.picked)
                if (lines !== "") return lines
                if (root.picked && root.picked.saturday) return "Saturday"
                return "No government holiday"
              }
              color: root.ink
              font.family: root.face
              font.pixelSize: Style.font.bodySmall
            }

            Text {
              width: parent.width
              elide: Text.ElideRight
              text: {
                var nxt = root.todayInfo.next
                if (!nxt) return ""
                var when = nxt.in_days === 0 ? "today" : "in " + nxt.in_days + "d"
                return "Next · " + nxt.name + " · " + when
              }
              color: root.ink
              opacity: 0.55
              font.family: root.face
              font.pixelSize: Style.font.caption
            }

            Text {
              width: parent.width
              wrapMode: Text.WordWrap
              visible: root.noticeLine !== ""
              text: root.noticeLine
              color: root.ink
              opacity: 0.75
              font.family: root.face
              font.pixelSize: Style.font.caption
            }

            Text {
              width: parent.width
              visible: root.status !== ""
              text: root.status
              color: root.ink
              opacity: 0.7
              font.family: root.face
              font.pixelSize: Style.font.caption
              wrapMode: Text.WordWrap
            }
          }
        }
      }
    }
  }
}
