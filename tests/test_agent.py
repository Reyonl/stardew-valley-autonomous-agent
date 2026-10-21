import unittest
from src.controller import GameController
from src.save_reader import get_latest_save


class TestStardewAgent(unittest.TestCase):
    def test_save_reader(self):
        save = get_latest_save()
        self.assertIsNotNone(save)
        self.assertEqual(save['player_name'], 'Reyon')
        self.assertEqual(save['farm_name'], 'LauS')
        self.assertEqual(save['season'], 'spring')
        self.assertEqual(save['day'], 5)
        self.assertGreaterEqual(save['money'], 0)

    def test_controller_geometry(self):
        ctrl = GameController()
        self.assertIsNotNone(ctrl.hwnd)
        self.assertIsNotNone(ctrl.rect)
        self.assertGreater(ctrl.width, 500)
        self.assertGreater(ctrl.height, 400)


if __name__ == '__main__':
    unittest.main()
