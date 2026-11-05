"""Qt와 독립적인 이동·상호작용 모델. 시간은 monotonic 초 단위."""
from dataclasses import dataclass
import random

SIZES = {"small": 90, "normal": 120, "large": 180}
FREQUENCIES = {"low": (18, 35), "normal": (10, 22), "high": (7, 13)}


def clamp_position(x, y, width, height, bounds):
    left, top, right, bottom = bounds  # exclusive right/bottom
    return (max(left, min(x, right - width)),
            max(top, min(y, bottom - height)))


@dataclass
class Behavior:
    rng: random.Random
    state: str = "idle"
    deadline: float = 0
    last_interaction: float = 0
    direction: int = 1
    moving: bool = True
    frequency: str = "normal"
    action_started: float = 0

    def idle(self, now):
        self.state = "idle"
        self.action_started = now
        self.deadline = now + self.rng.uniform(*FREQUENCIES[self.frequency])

    def react(self, now, landing=False):
        self.last_interaction = now
        self.state = "land" if landing else "happy"
        self.action_started = now
        self.deadline = now + (0.35 if landing else 0.65)

    def drag(self, now):
        self.last_interaction = now
        self.state = "held"
        self.action_started = now

    def step(self, now, dt):
        if self.state == "held":
            return 0
        if self.state in ("happy", "land"):
            if now >= self.deadline:
                self.idle(now)
            return 0
        if now - self.last_interaction >= 180:
            self.state = "sleep"
            return 0
        if now >= self.deadline:
            if self.state == "walk" or not self.moving:
                self.idle(now)
            else:
                self.state = "walk"
                self.direction = self.rng.choice((-1, 1))
                self.action_started = now
                self.deadline = now + self.rng.uniform(2, 4)
        return self.direction * 22 * min(dt, 0.1) if self.state == "walk" else 0
