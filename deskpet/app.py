import logging
import math
import random
import sys
import time

from PySide6.QtCore import QPoint, QLockFile, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPainter, QRegion
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFormLayout, QMenu, QMessageBox, QSystemTrayIcon, QWidget)

from . import platforms, settings
from .art import Sprites
from .model import Behavior, SIZES, clamp_position


class PetWindow(QWidget):
    def __init__(self, settings_path=None, create_tray=True):
        super().__init__()
        self.settings_path = settings_path
        self.options = settings.load(settings_path)
        self.sprites = Sprites()
        self.behavior = Behavior(random.Random(), moving=self.options["moving"],
                                 frequency=self.options["frequency"])
        now = time.monotonic()
        self.behavior.last_interaction = now
        self.behavior.idle(now)
        self.previous = now
        self.x_float = 0.0
        self.press_global = None
        self.press_origin = None
        self.dragging = False
        self.manually_hidden = False
        self.fullscreen_hidden = False
        self.menu_open = False
        self.dialog = None
        self.tray = None
        self._pixmap_key = None
        self.setWindowTitle("안경만두")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.set_flags()
        self.apply_size()
        area = QApplication.primaryScreen().availableGeometry()
        x, y = self.options["x"], self.options["y"]
        if x is None or y is None:
            x, y = area.right() - self.width() - 20, area.bottom() - self.height()
        self.move_bounded(x, y)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(600)
        self.save_timer.timeout.connect(self.persist)
        if create_tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(QIcon(self.sprites.frames["idle"][0]), self)
            self.tray.setToolTip("안경만두 · 두 번 클릭하면 다시 나타나요")
            self.tray.activated.connect(self.tray_activated)
            self.tray_menu = QMenu()
            self.tray_menu.aboutToShow.connect(self.refresh_tray_menu)
            self.tray.setContextMenu(self.tray_menu)
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.screen_timer = QTimer(self)
        self.screen_timer.setInterval(1000)
        self.screen_timer.timeout.connect(self.check_fullscreen)
        self.screen_timer.start()
        QApplication.instance().screenAdded.connect(self.recheck_bounds)
        QApplication.instance().screenRemoved.connect(self.recheck_bounds)
        for screen in QApplication.screens():
            screen.availableGeometryChanged.connect(self.recheck_bounds)
        self.refresh_frame(now)

    def set_flags(self):
        flags = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                 | Qt.WindowType.WindowDoesNotAcceptFocus)
        if self.options["topmost"]:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        platforms.no_activate(self)

    def apply_size(self):
        # 72 pixels of character plus transparent headroom for the click hop.
        scale = SIZES[self.options["size"]] / 72
        self.setFixedSize(round(64 * scale), round(88 * scale))
        self._pixmap_key = None

    def bounds(self, x, y):
        center = QPoint(round(x + self.width() / 2), round(y + self.height() / 2))
        screen = QApplication.screenAt(center)
        if screen is None:
            screens = QApplication.screens()
            screen = min(screens, key=lambda s: (s.availableGeometry().center().x() - center.x()) ** 2
                         + (s.availableGeometry().center().y() - center.y()) ** 2)
        area = screen.availableGeometry()
        return area.left(), area.top(), area.right() + 1, area.bottom() + 1

    def move_bounded(self, x, y):
        x, y = clamp_position(x, y, self.width(), self.height(), self.bounds(x, y))
        self.move(round(x), round(y))
        self.x_float = float(x)

    def recheck_bounds(self, *_):
        self.move_bounded(self.x(), self.y())
        self.save_timer.start()

    def refresh_frame(self, now):
        pixmap = self.sprites.get(self.behavior.state,
                                  now - self.behavior.action_started,
                                  self.behavior.direction, now)
        key = (pixmap.cacheKey(), self.width(), self.height())
        if key != self._pixmap_key:
            self.frame = pixmap.scaled(self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                       Qt.TransformationMode.FastTransformation)
            # Window region follows actual opaque pixels, including gaps between limbs.
            self.setMask(QRegion(self.frame.mask()))
            self._pixmap_key = key
            self.update()

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.previous, 0.1)
        self.previous = now
        if self.manually_hidden or self.fullscreen_hidden or self.menu_open or self.dialog:
            return
        old = self.behavior.state
        # Holding a mouse press must never allow autonomous walking underneath it.
        dx = 0 if self.press_global is not None else self.behavior.step(now, dt)
        if dx:
            candidate = self.x_float + dx
            left, top, right, bottom = self.bounds(self.x(), self.y())
            bounded, _ = clamp_position(candidate, self.y(), self.width(), self.height(),
                                        (left, top, right, bottom))
            self.x_float = bounded
            self.move(round(bounded), self.y())
            if candidate != bounded:
                self.behavior.idle(now)
        if old == "walk" and self.behavior.state != "walk":
            self.save_timer.start()
        self.refresh_frame(now)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.frame)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_global = event.globalPosition().toPoint()
            self.press_origin = self.pos()
            self.dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self.press_global is None:
            return
        delta = event.globalPosition().toPoint() - self.press_global
        if not self.dragging and delta.manhattanLength() >= QApplication.startDragDistance():
            self.dragging = True
            self.behavior.drag(time.monotonic())
        if self.dragging:
            target = self.press_origin + delta
            self.move_bounded(target.x(), target.y())
            self.refresh_frame(time.monotonic())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.press_global is not None:
            self.behavior.react(time.monotonic(), landing=self.dragging)
            self.press_global = None
            self.press_origin = None
            self.dragging = False
            self.save_timer.start()
            self.refresh_frame(time.monotonic())

    def contextMenuEvent(self, event):
        self.menu_open = True
        try:
            menu = self.make_menu()
            menu.exec(event.globalPos())
            menu.deleteLater()
        finally:
            self.menu_open = False
            self.behavior.idle(time.monotonic())

    def make_menu(self, menu=None):
        menu = menu or QMenu()
        menu.clear()
        show = menu.addAction("안경만두 다시 보기")
        show.triggered.connect(self.reveal)
        show.setVisible(self.manually_hidden)
        move = menu.addAction("산책하기")
        move.setCheckable(True)
        move.setChecked(self.options["moving"])
        move.triggered.connect(lambda value: self.change("moving", value))
        size_menu = menu.addMenu("크기")
        group = QActionGroup(size_menu)
        for key, label in (("small", "작게 · 90px"), ("normal", "보통 · 120px"), ("large", "크게 · 180px")):
            action = size_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.options["size"] == key)
            group.addAction(action)
            action.triggered.connect(lambda checked, k=key: self.change("size", k))
        top = menu.addAction("항상 위에 표시")
        top.setCheckable(True)
        top.setChecked(self.options["topmost"])
        top.triggered.connect(lambda value: self.change("topmost", value))
        menu.addSeparator()
        hide = menu.addAction("잠깐 숨기기")
        hide.setEnabled(self.tray is not None and not self.manually_hidden)
        if self.tray is None:
            hide.setToolTip("알림 영역을 사용할 수 없어 숨기기를 비활성화했습니다.")
        hide.triggered.connect(self.hide_manually)
        menu.addAction("설정…", self.open_settings)
        menu.addSeparator()
        menu.addAction("종료", QApplication.instance().quit)
        return menu

    def refresh_tray_menu(self):
        self.make_menu(self.tray_menu)

    def change(self, key, value):
        self.options[key] = value
        now = time.monotonic()
        if key == "moving":
            self.behavior.moving = value
            self.behavior.idle(now)
        elif key == "size":
            bottom = self.y() + self.height()
            center = self.x() + self.width() / 2
            self.apply_size()
            self.move_bounded(center - self.width() / 2, bottom - self.height())
        elif key == "topmost":
            self.set_flags()
            if not self.manually_hidden and not self.fullscreen_hidden:
                self.show()
        self.refresh_frame(now)
        self.save_timer.start()

    def hide_manually(self):
        if self.tray is not None:
            self.manually_hidden = True
            self.hide()
            self.persist()

    def reveal(self):
        self.manually_hidden = False
        self.check_fullscreen()
        if not self.fullscreen_hidden:
            self.show()
        self.behavior.last_interaction = time.monotonic()
        self.behavior.idle(time.monotonic())

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.reveal()

    def check_fullscreen(self):
        # If there is no tray, always retain a reachable pet/menu.
        hidden = bool(self.tray and self.options["hide_fullscreen"]
                      and platforms.foreground_fullscreen(int(self.winId())))
        if hidden != self.fullscreen_hidden:
            self.fullscreen_hidden = hidden
            if hidden:
                self.hide()
            elif not self.manually_hidden:
                self.show()

    def open_settings(self):
        if self.dialog is not None:
            self.dialog.raise_()
            return
        dialog = QDialog()
        self.dialog = dialog
        dialog.setWindowTitle("안경만두 설정")
        dialog.setMinimumWidth(310)
        layout = QFormLayout(dialog)
        frequency = QComboBox()
        for label, value in (("느긋하게", "low"), ("보통", "normal"), ("조금 더 자주", "high")):
            frequency.addItem(label, value)
        frequency.setCurrentIndex(frequency.findData(self.options["frequency"]))
        layout.addRow("산책 빈도", frequency)
        fullscreen = QCheckBox("전체 화면 앱 사용 중 자동 숨기기")
        fullscreen.setChecked(self.options["hide_fullscreen"])
        fullscreen.setEnabled(sys.platform == "win32" and self.tray is not None)
        layout.addRow(fullscreen)
        autostart = QCheckBox("Windows 로그인 시 실행")
        autostart.setChecked(self.options["autostart"])
        autostart.setEnabled(sys.platform == "win32")
        layout.addRow(autostart)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if autostart.isChecked() != self.options["autostart"]:
                    platforms.set_autostart(autostart.isChecked())
                self.options.update(frequency=frequency.currentData(),
                                    hide_fullscreen=fullscreen.isChecked(),
                                    autostart=autostart.isChecked())
                self.behavior.frequency = self.options["frequency"]
                self.behavior.idle(time.monotonic())
                self.persist()
                self.check_fullscreen()
            except OSError as exc:
                QMessageBox.warning(dialog, "설정을 저장하지 못했어요", str(exc))
        self.dialog = None
        dialog.deleteLater()

    def persist(self):
        self.options.update(x=self.x(), y=self.y())
        try:
            settings.save(self.options, self.settings_path)
        except OSError:
            logging.exception("설정을 저장하지 못했습니다")
            if self.tray:
                self.tray.showMessage("안경만두", "설정을 저장하지 못했습니다. 저장 폴더 권한을 확인해 주세요.")

    def shutdown(self):
        self.timer.stop()
        self.screen_timer.stop()
        self.save_timer.stop()
        self.persist()
        if self.tray:
            self.tray.hide()

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GlassesMandu")
    app.setOrganizationName("GlassesMandu")
    app.setQuitOnLastWindowClosed(False)
    path = settings.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=path.parent / "deskpet.log", level=logging.WARNING)
    lock = QLockFile(str(path.parent / "instance.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "안경만두", "이미 실행 중입니다. 알림 영역에서 안경만두를 찾아 주세요.")
        return 0
    window = PetWindow()
    app.aboutToQuit.connect(window.shutdown)
    window.show()
    platforms.no_activate(window)
    result = app.exec()
    lock.unlock()
    return result
