"""참고 외형을 재해석한 임시 도트 아트. 원본 이미지를 편집한 자산은 아님.
assets/<pose>-<frame>.png가 있으면 동일 64×88 투명 캔버스 자산으로 교체 가능.
"""
import math
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QImage, QPainter, QPolygon, QPixmap

POSES = {"idle": 6, "walk-left": 6, "walk-right": 6, "happy": 6,
         "held": 2, "land": 4, "sleep": 4}


def asset_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"


def draw_frame(pose, frame):
    path = asset_root() / f"{pose}-{frame}.png"
    if path.is_file():
        image = QImage(str(path))
        if image.size().width() == 64 and image.size().height() == 88 and image.hasAlphaChannel():
            return image
    image = QImage(64, 88, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.setPen(Qt.PenStyle.NoPen)
    walk = pose.startswith("walk")
    held = pose == "held"
    blink = (pose == "idle" and frame == 5) or pose == "sleep"
    offset = (-1 if frame % 3 == 1 else 0) if pose == "idle" or walk else 0
    if pose == "happy":
        offset = -round(7 * math.sin(frame / 5 * math.pi))
    p.translate(0, offset + 8)
    if pose == "land":
        p.translate(32, 72)
        p.scale(1 + [0.08, 0.05, 0.02, 0][frame], [0.90, 0.94, 0.98, 1][frame])
        p.translate(-32, -72)
    if pose == "walk-right":
        p.translate(64, 0)
        p.scale(-1, 1)

    def rect(x, y, w, h, color):
        p.fillRect(x, y, w, h, QColor(color))

    def poly(points, color):
        p.setBrush(QColor(color))
        p.drawPolygon(QPolygon([QPoint(x, y) for x, y in points]))

    gold, shade, cream, light = "#edc36c", "#f6d885", "#fff0bd", "#fff4ce"
    # Feet and small body; all standing frames share the same baseline.
    foot = 1 if walk and frame % 3 == 0 else 0
    rect(23, 65 - foot, 5, 7, gold)
    rect(36, 65 + foot, 5, 7 - foot, gold)
    rect(23, 69 - foot, 3, 3, shade)
    rect(38, 69 + foot, 3, 3 - foot, shade)
    poly([(20, 51), (44, 51), (45, 61), (41, 68), (25, 68), (20, 62)], gold)
    rect(24, 52, 17, 12, shade)
    rect(27, 54, 13, 9, "#f9df91")
    if held:
        rect(19, 53, 5, 5, shade)
        rect(40, 53, 5, 5, shade)
    else:
        rect(17, 54, 5, 10, gold)
        rect(43, 54, 5, 10, gold)
        rect(17, 59, 3, 5, shade)
        rect(45, 59, 3, 5, shade)
    # Stepped silhouette instead of smoothed vector outlines.
    poly([(27, 1), (35, 1), (35, 5), (40, 5), (40, 2), (46, 2), (46, 7),
          (43, 8), (48, 9), (48, 11), (53, 13), (53, 16), (57, 19),
          (59, 23), (61, 27), (62, 40), (60, 45), (56, 49), (51, 52),
          (45, 55), (19, 55), (13, 52), (8, 49), (4, 44), (2, 40),
          (2, 28), (5, 22), (8, 18), (13, 14), (18, 11), (22, 9),
          (20, 7), (20, 3), (25, 3), (25, 7), (28, 7)], gold)
    poly([(23, 10), (41, 10), (49, 13), (56, 20), (59, 28), (59, 40),
          (55, 47), (45, 52), (19, 52), (10, 47), (5, 40), (5, 28),
          (10, 20), (17, 14)], shade)
    poly([(22, 12), (40, 12), (48, 15), (54, 21), (57, 29), (57, 40),
          (52, 46), (43, 50), (20, 50), (12, 46), (7, 39), (7, 29),
          (12, 21)], cream)
    rect(24, 2, 2, 5, "#ffe6a0")
    rect(29, 2, 3, 6, "#ffe6a0")
    rect(41, 3, 2, 4, "#ffe6a0")
    if walk:
        # Side view with visible red temple and a small front lens.
        poly([(34, 13), (43, 18), (49, 26), (51, 39), (46, 47),
              (39, 50), (45, 48), (54, 42), (55, 28), (50, 20), (42, 14)], "#f9df99")
        rect(8, 24, 9, 2, "#201d16")
        rect(6, 26, 5, 2, "#201d16")
        rect(6, 31, 6, 9, "#22211c")
        rect(7, 32, 2, 3, "#ffffff")
        rect(3, 31, 2, 12, "#c71e19")
        rect(3, 42, 8, 2, "#c71e19")
        rect(4, 34, 22, 2, "#d3221b")
        rect(25, 35, 4, 2, "#b81817")
        rect(7, 47, 4, 1, "#28271f")
    else:
        rect(12, 21, 8, 2, "#1e1d18")
        rect(10, 23, 5, 2, "#1e1d18")
        rect(43, 21, 8, 2, "#1e1d18")
        rect(49, 23, 5, 2, "#1e1d18")
        for x in (13, 43):
            if blink:
                rect(x, 33, 9, 2, "#343129")
            else:
                rect(x, 29, 8, 10, "#62615a")
                rect(x - 1, 29, 10, 2, "#191914")
                rect(x + 1, 31, 3, 3, "#ffffff")
                rect(x + 5, 36, 1, 1, "#ffffff")
                rect(x + 1, 39, 5, 1, "#62615a")
        # Lens highlights and red square rims.
        for x in (5, 35):
            rect(x, 30, 2, 12, "#c81716")
            rect(x + 22, 30, 2, 12, "#c81716")
            rect(x + 1, 41, 22, 2, "#c81716")
            rect(x + 1, 30, 3, 2, "#ec3430")
            rect(x + 3, 32, 1, 4, "#fffbed")
            rect(x + 4, 31, 2, 2, "#fffbed")
        rect(29, 32, 6, 2, "#d9201b")
        rect(29, 47, 5, 1, "#26251d")
    p.end()
    return image


class Sprites:
    def __init__(self):
        self.frames = {pose: [QPixmap.fromImage(draw_frame(pose, frame))
                              for frame in range(count)] for pose, count in POSES.items()}

    def get(self, state, age, direction, now):
        pose = ("walk-left" if direction < 0 else "walk-right") if state == "walk" else state
        frames = self.frames[pose]
        if state == "idle":
            # Brief blink about every 4.5 seconds; hold front view most of the time.
            cycle = now % 4.5
            index = 5 if cycle > 4.34 else int(now / 0.8) % 4
        elif state in ("happy", "land"):
            duration = 0.65 if state == "happy" else 0.35
            index = min(len(frames) - 1, int(age / duration * len(frames)))
        else:
            index = int(age * (8 if state == "walk" else 2)) % len(frames)
        return frames[index]
