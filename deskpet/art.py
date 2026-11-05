"""Render the supplied original artwork without replacing its face or proportions.

The source PNG is copied byte-for-byte into assets. Cropping, pose transforms,
and nearest-neighbor scaling happen at render time; no low-resolution redraw.
"""
from functools import lru_cache
import math
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QImage, QPainter, QPixmap

POSES = {"idle": 6, "walk-left": 6, "walk-right": 6, "happy": 6,
         "held": 2, "land": 4, "sleep": 4}
CANVAS = (288, 352)
# Exact opaque bounds of the two characters in the supplied 1620 x 2025 PNG.
FRONT = QRect(78, 1013, 875, 947)
SIDE = QRect(29, 60, 770, 836)


def asset_root():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "assets"


@lru_cache(maxsize=2)
def source_pose(side=False):
    source = QImage(str(asset_root() / "mandu-reference.png"))
    if source.isNull() or source.size().width() != 1620 or source.size().height() != 2025:
        raise RuntimeError("원본 캐릭터 이미지 assets/mandu-reference.png를 읽을 수 없습니다.")
    return source.copy(SIDE if side else FRONT)


def draw_frame(pose, frame):
    if pose not in POSES or not 0 <= frame < POSES[pose]:
        raise ValueError("Unknown sprite frame")
    walk = pose.startswith("walk")
    source = source_pose(walk)
    # Close only the eyes, keeping the original glasses, brows and mouth.
    if pose == "sleep" or (pose == "idle" and frame == 5):
        source = source.copy()
        eyes = QPainter(source)
        for x in (132, 578):
            eyes.fillRect(x, 332, 172, 155, source.pixelColor(x + 180, 390))
            eyes.fillRect(x + 13, 403, 135, 15, source.pixelColor(420, 605))
        eyes.end()
    sprite = source.scaled(272, 288, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.FastTransformation)
    if pose == "walk-right":
        sprite = sprite.mirrored(True, False)
    image = QImage(*CANVAS, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
    bottom = 320
    offset = 0
    if pose == "happy":
        offset = -round(25 * math.sin(frame / 5 * math.pi))
    elif pose == "idle":
        offset = -2 if frame in (1, 2) else 0
    elif walk:
        offset = -4 if frame in (1, 4) else 0
    elif pose == "held":
        offset = -5
    elif pose == "sleep":
        offset = 2 if frame % 2 else 0
    scale_x, scale_y = 1.0, 1.0
    if pose == "land":
        scale_x = (1.035, 1.02, 1.01, 1)[frame]
        scale_y = (0.95, 0.97, 0.99, 1)[frame]
    elif pose == "held":
        scale_x, scale_y = 0.98, 1.015
    painter.translate(144, bottom + offset)
    painter.scale(scale_x, scale_y)
    painter.drawImage(-sprite.width() // 2, -sprite.height(), sprite)
    painter.end()
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
