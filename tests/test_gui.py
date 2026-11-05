"""Run with QT_QPA_PLATFORM=offscreen on Linux; Windows native checks remain manual."""
from pathlib import Path
import tempfile
import time
import unittest

from PySide6.QtCore import QPoint, QPointF, QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from deskpet.app import PetWindow
from deskpet.art import CANVAS, FRONT, SIDE, POSES, draw_frame, source_pose
from deskpet.settings import load

app = QApplication.instance() or QApplication([])
app.setQuitOnLastWindowClosed(False)


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "settings.json"
        self.pet = PetWindow(self.path, create_tray=False)
        self.pet.show()
        app.processEvents()

    def tearDown(self):
        self.pet.shutdown()
        self.pet.hide()
        self.pet.deleteLater()
        app.processEvents()
        self.temp.cleanup()

    def test_frames_are_transparent_and_mask_excludes_background(self):
        for pose, count in POSES.items():
            for index in range(count):
                image = draw_frame(pose, index)
                self.assertEqual((image.width(), image.height()), CANVAS)
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                self.assertGreater(image.pixelColor(128, 140).alpha(), 0)
        self.assertFalse(self.pet.mask().contains(QPoint(0, 0)))
        self.assertTrue(self.pet.mask().contains(QPoint(self.pet.width() // 2, self.pet.height() // 2)))

    def test_source_is_exact_uploaded_artwork(self):
        from deskpet.art import asset_root
        root = Path(__file__).resolve().parent.parent
        self.assertEqual((asset_root() / "mandu-reference.png").read_bytes(),
                         (root / "1.png").read_bytes())
        from PySide6.QtGui import QImage
        original = QImage(str(root / "1.png"))
        self.assertEqual(source_pose(False), original.copy(FRONT))
        self.assertEqual(source_pose(True), original.copy(SIDE))

    def test_blink_preserves_glasses_and_returns_to_original_face(self):
        opened = draw_frame("idle", 0)
        closed = draw_frame("idle", 5)
        self.assertNotEqual(opened, closed)
        # Blink affects only the eyes; lower glasses rims, mouth and body stay exact.
        from PySide6.QtCore import QRect
        lower = QRect(0, 225, CANVAS[0], CANVAS[1] - 225)
        self.assertEqual(opened.copy(lower), closed.copy(lower))
        self.assertEqual(opened, draw_frame("idle", 0))

    def test_click_reacts_then_returns_to_front(self):
        QTest.mouseClick(self.pet, Qt.MouseButton.LeftButton, pos=self.pet.rect().center())
        self.assertEqual(self.pet.behavior.state, "happy")
        QTest.qWait(750)
        self.assertEqual(self.pet.behavior.state, "idle")

    def test_drag_uses_threshold_and_lands(self):
        pos = self.pet.rect().center()
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=pos)
        global_pos = self.pet.mapToGlobal(pos) + QPoint(-50, -30)
        event = QMouseEvent(QEvent.Type.MouseMove, QPointF(pos + QPoint(-50, -30)),
                            QPointF(global_pos), Qt.MouseButton.NoButton,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.pet, event)
        self.assertTrue(self.pet.dragging)
        self.assertEqual(self.pet.behavior.state, "held")
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=pos)
        self.assertEqual(self.pet.behavior.state, "land")
        QTest.qWait(450)
        self.assertEqual(self.pet.behavior.state, "idle")

    def test_size_position_and_options_survive_restart(self):
        self.pet.change("size", "large")
        self.pet.change("moving", False)
        self.pet.change("topmost", False)
        self.pet.move_bounded(100, 100)
        self.pet.persist()
        second = PetWindow(self.path, create_tray=False)
        try:
            self.assertEqual(second.options["size"], "large")
            self.assertFalse(second.behavior.moving)
            self.assertFalse(second.options["topmost"])
            self.assertEqual(second.pos(), self.pet.pos())
            self.assertEqual(second.height(), 220)
        finally:
            second.shutdown()
            second.deleteLater()

    def test_screen_boundaries_and_no_tray_hide_guard(self):
        self.pet.move_bounded(100000, 100000)
        area = self.pet.screen().availableGeometry()
        self.assertLessEqual(self.pet.x() + self.pet.width(), area.right() + 1)
        self.assertLessEqual(self.pet.y() + self.pet.height(), area.bottom() + 1)
        self.pet.hide_manually()
        self.assertTrue(self.pet.isVisible())
        menu = self.pet.make_menu()
        self.assertFalse(next(a for a in menu.actions() if a.text() == "잠깐 숨기기").isEnabled())
        menu.deleteLater()

    def test_timer_runs_and_front_idle_does_not_move(self):
        self.pet.change("moving", False)
        origin = self.pet.pos()
        QTest.qWait(100)
        self.assertTrue(self.pet.timer.isActive())
        self.assertEqual(self.pet.pos(), origin)
        self.assertEqual(self.pet.behavior.state, "idle")
