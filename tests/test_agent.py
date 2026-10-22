"""
Unit & Integration Tests for Stardew Valley Autonomous Agent
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from src.controller import GameController
from src.save_reader import get_latest_save, parse_save_xml

SAMPLE_SAVE_XML = """<?xml version="1.0" encoding="utf-8"?>
<SaveGame xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <player>
    <name>Reyon</name>
    <farmName>LauS</farmName>
    <money>505</money>
    <stamina>254.0</stamina>
    <maxStamina>270.0</maxStamina>
  </player>
  <dayOfMonth>5</dayOfMonth>
  <currentSeason>spring</currentSeason>
  <year>1</year>
  <weatherForTomorrow>Rain</weatherForTomorrow>
  <locations>
    <GameLocation xsi:type="Farm">
      <name>Farm</name>
      <terrainFeatures>
        <item>
          <key><Vector2><X>66</X><Y>22</Y></Vector2></key>
          <value>
            <TerrainFeature xsi:type="HoeDirt">
              <state>1</state>
              <crop><phaseDaysIndex>4</phaseDaysIndex></crop>
            </TerrainFeature>
          </value>
        </item>
        <item>
          <key><Vector2><X>66</X><Y>23</Y></Vector2></key>
          <value>
            <TerrainFeature xsi:type="HoeDirt">
              <state>0</state>
              <crop><phaseDaysIndex>3</phaseDaysIndex></crop>
            </TerrainFeature>
          </value>
        </item>
      </terrainFeatures>
    </GameLocation>
  </locations>
</SaveGame>
"""


class TestStardewAgent(unittest.TestCase):
    def test_parse_save_xml_fixture(self):
        """Tests parsing telemetry directly from XML source fixture."""
        save = parse_save_xml(SAMPLE_SAVE_XML)
        self.assertIsNotNone(save)
        self.assertEqual(save['player_name'], 'Reyon')
        self.assertEqual(save['farm_name'], 'LauS')
        self.assertEqual(save['season'], 'spring')
        self.assertEqual(save['day'], 5)
        self.assertEqual(save['year'], 1)
        self.assertEqual(save['money'], 505)
        self.assertEqual(save['stamina'], 254.0)
        self.assertEqual(save['max_stamina'], 270.0)
        self.assertEqual(save['weather_tomorrow'], 'Rain')
        self.assertEqual(save['crops_total'], 2)
        self.assertEqual(save['crops_watered'], 1)

    def test_live_save_reader_if_available(self):
        """Validates real system save file if Stardew Valley is installed locally."""
        save = get_latest_save()
        if save is not None:
            self.assertTrue(len(save['player_name']) > 0)
            self.assertTrue(len(save['farm_name']) > 0)
            self.assertIn(save['season'], ['spring', 'summer', 'fall', 'winter'])
            self.assertGreaterEqual(save['day'], 1)
            self.assertLessEqual(save['day'], 28)
            self.assertGreaterEqual(save['year'], 1)
            self.assertGreaterEqual(save['money'], 0)
            self.assertGreaterEqual(save['stamina'], 0.0)
            self.assertGreaterEqual(save['crops_total'], 0)
            self.assertGreaterEqual(save['crops_watered'], 0)

    def test_controller_initialization_safety(self):
        """Ensures GameController initializes safely without crashing regardless of game state."""
        ctrl = GameController()
        self.assertTrue(hasattr(ctrl, 'hwnd'))
        self.assertTrue(hasattr(ctrl, 'rect'))
        self.assertTrue(hasattr(ctrl, 'width'))
        self.assertTrue(hasattr(ctrl, 'height'))

        if ctrl.hwnd:
            self.assertIsNotNone(ctrl.rect)
            self.assertGreater(ctrl.width, 0)
            self.assertGreater(ctrl.height, 0)
        else:
            self.assertIsNone(ctrl.rect)
            self.assertEqual(ctrl.width, 0)
            self.assertEqual(ctrl.height, 0)

    @patch('src.controller.pydirectinput.keyDown')
    @patch('src.controller.pydirectinput.keyUp')
    def test_controller_input_dispatch(self, mock_key_up, mock_key_down):
        """Verifies keyboard input dispatching via mock without moving physical cursor."""
        ctrl = GameController()
        # Mock focus so it doesn't attempt Win32 calls
        ctrl.focus = MagicMock()

        ctrl.select_slot(1)
        mock_key_down.assert_called_with('1')
        mock_key_up.assert_called_with('1')

        ctrl.select_slot(10)
        mock_key_down.assert_called_with('0')
        mock_key_up.assert_called_with('0')


if __name__ == '__main__':
    unittest.main()
