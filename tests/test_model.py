import json
from pathlib import Path
import random
import tempfile
import unittest

from deskpet.model import Behavior, clamp_position
from deskpet.settings import DEFAULTS, load, save


class BehaviorTests(unittest.TestCase):
    def setUp(self):
        self.pet = Behavior(random.Random(12), last_interaction=100)
        self.pet.idle(100)

    def test_waits_longer_than_walks(self):
        self.assertGreaterEqual(self.pet.deadline - 100, 10)
        start = self.pet.deadline
        self.pet.step(start, .03)
        self.assertEqual(self.pet.state, "walk")
        self.assertLessEqual(self.pet.deadline - start, 4)
        self.pet.step(self.pet.deadline, .03)
        self.assertEqual(self.pet.state, "idle")

    def test_disabled_walking(self):
        self.pet.moving = False
        self.assertEqual(self.pet.step(self.pet.deadline, 1), 0)
        self.assertEqual(self.pet.state, "idle")

    def test_click_and_landing_are_distinct(self):
        self.pet.react(101)
        self.assertEqual(self.pet.state, "happy")
        self.pet.step(102, .03)
        self.assertEqual(self.pet.state, "idle")
        self.pet.drag(103)
        self.assertEqual(self.pet.step(104, .03), 0)
        self.assertEqual(self.pet.state, "held")
        self.pet.react(105, landing=True)
        self.assertEqual(self.pet.state, "land")

    def test_sleeps_and_wakes(self):
        self.pet.step(281, .03)
        self.assertEqual(self.pet.state, "sleep")
        self.pet.react(282)
        self.assertEqual(self.pet.state, "happy")
        self.assertEqual(self.pet.last_interaction, 282)

    def test_bounds_negative_monitor_and_taskbar(self):
        self.assertEqual(clamp_position(-2000, 1100, 100, 120,
                                      (-1920, 0, 0, 1040)), (-1920, 920))
        self.assertEqual(clamp_position(1900, -10, 100, 120,
                                      (0, 0, 1920, 1040)), (1820, 0))

    def test_stall_does_not_teleport(self):
        self.pet.state = "walk"
        self.pet.deadline = 150
        self.assertLessEqual(abs(self.pet.step(110, 100)), 2.2)


class SettingsTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "settings.json"
            data = dict(DEFAULTS, size="large", x=-300, y=400, moving=False)
            save(data, path)
            self.assertEqual(load(path), data)
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_bad_or_missing_settings_use_defaults(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "settings.json"
            self.assertEqual(load(path), DEFAULTS)
            for value in ("not json", "[]", '{"size":"huge","x":true,"moving":"false"}'):
                path.write_text(value)
                self.assertEqual(load(path), DEFAULTS)
