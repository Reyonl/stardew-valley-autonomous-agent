"""
Save File Reader & Analytics
Parses Stardew Valley XML save data for accurate ground-truth progression tracking.
"""

import os
import xml.etree.ElementTree as ET


def get_latest_save():
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

    tree = ET.parse(save_file)
    root = tree.getroot()
    player = root.find('player')

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

    return {
        'player_name': player.find('name').text if player.find('name') is not None else '',
        'farm_name': player.find('farmName').text if player.find('farmName') is not None else '',
        'day': int(root.find('dayOfMonth').text),
        'season': root.find('currentSeason').text,
        'year': int(root.find('year').text),
        'money': int(player.find('money').text) if player.find('money') is not None else 0,
        'stamina': float(player.find('stamina').text) if player.find('stamina') is not None else 0.0,
        'max_stamina': float(player.find('maxStamina').text) if player.find('maxStamina') is not None else 0.0,
        'weather_tomorrow': root.find('weatherForTomorrow').text if root.find('weatherForTomorrow') is not None else '',
        'crops_total': crops_total,
        'crops_watered': crops_watered,
    }
