"""
Save File Reader & Analytics
Parses Stardew Valley XML save data for accurate ground-truth progression tracking.
"""

import os
import xml.etree.ElementTree as ET


def parse_save_xml(xml_source):
    """
    Parses Stardew Valley XML save data (file path, raw XML string, or ElementTree root)
    and returns a structured dictionary of telemetry.
    """
    if isinstance(xml_source, ET.Element):
        root = xml_source
    elif isinstance(xml_source, str) and (xml_source.strip().startswith('<') or '\n' in xml_source):
        root = ET.fromstring(xml_source)
    else:
        tree = ET.parse(xml_source)
        root = tree.getroot()

    player = root.find('player')
    if player is None:
        return None

    # Read crops count & watering status
    crops_total = 0
    crops_watered = 0
    for loc in root.findall('.//locations/GameLocation'):
        name = loc.find('name')
        if name is not None and name.text == 'Farm':
            terrain = loc.find('terrainFeatures')
            if terrain is not None:
                for item in terrain.findall('item'):
                    val = item.find('value')
                    tf = val.find('TerrainFeature') if val is not None else None
                    if tf is not None and tf.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'HoeDirt':
                        crop = tf.find('crop')
                        if crop is not None:
                            crops_total += 1
                            state = tf.find('state').text if tf.find('state') is not None else '0'
                            if state == '1':
                                crops_watered += 1

    day_elem = root.find('dayOfMonth')
    season_elem = root.find('currentSeason')
    year_elem = root.find('year')
    weather_elem = root.find('weatherForTomorrow')

    return {
        'player_name': player.find('name').text if player.find('name') is not None else '',
        'farm_name': player.find('farmName').text if player.find('farmName') is not None else '',
        'day': int(day_elem.text) if day_elem is not None else 1,
        'season': season_elem.text if season_elem is not None else 'spring',
        'year': int(year_elem.text) if year_elem is not None else 1,
        'money': int(player.find('money').text) if player.find('money') is not None else 0,
        'stamina': float(player.find('stamina').text) if player.find('stamina') is not None else 0.0,
        'max_stamina': float(player.find('maxStamina').text) if player.find('maxStamina') is not None else 0.0,
        'weather_tomorrow': weather_elem.text if weather_elem is not None else '',
        'crops_total': crops_total,
        'crops_watered': crops_watered,
    }


def get_latest_save(saves_dir=None):
    """
    Finds and parses the most recently modified save file in %APPDATA%/StardewValley/Saves.
    """
    if saves_dir is None:
        appdata = os.environ.get('APPDATA', '')
        saves_dir = os.path.join(appdata, 'StardewValley', 'Saves')

    if not os.path.isdir(saves_dir):
        return None

    folders = [os.path.join(saves_dir, d) for d in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, d))]
    if not folders:
        return None
    save_folder = max(folders, key=os.path.getmtime)
    save_name = os.path.basename(save_folder)
    save_file = os.path.join(save_folder, save_name)

    if not os.path.isfile(save_file):
        return None

    return parse_save_xml(save_file)
