"""
Autonomous Stardew Valley Grinding Agent Runner
Executes autonomous daily farming, harvesting, watering, and overnight cycles via AgentBridge.
"""

import json
import os
import subprocess
import time
from typing import Any, Dict, List
from agent_lib.bridge import BridgeClient


class AutonomousGrinder:
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.client = BridgeClient(base_url)

    def is_bridge_ready(self) -> bool:
        try:
            state = self.client.get_state()
            return state.get("world_ready", False)
        except Exception:
            return False

    def ensure_game_running(self, save_name: str = "LauS_426336281"):
        try:
            state = self.client.get_state()
            if state.get("world_ready", False):
                print("Game is already running and world is ready.")
                return
        except Exception:
            pass

        print("Launching Stardew Valley with SMAPI...")
        dotnet_exe = r"C:\Users\ThinkPad\.dotnet\dotnet.exe"
        smapi_dll = r"D:\Download\Stardew.Valley.v1.6.15.kuyhAa\Stardew Valley\StardewModdingAPI.dll"
        cwd = r"D:\Download\Stardew.Valley.v1.6.15.kuyhAa\Stardew Valley"

        env = os.environ.copy()
        env["DOTNET_ROOT"] = r"C:\Users\ThinkPad\.dotnet"
        env["PATH"] = r"C:\Users\ThinkPad\.dotnet;" + env.get("PATH", "")

        subprocess.Popen(
            [dotnet_exe, smapi_dll],
            cwd=cwd,
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        print("Waiting for AgentBridge HTTP server to start...")
        for _ in range(30):
            time.sleep(1)
            try:
                s = self.client.get_state()
                if "world_ready" in s:
                    print("AgentBridge HTTP server online!")
                    break
            except Exception:
                pass

        print(f"Loading save {save_name}...")
        self.client.load_save(save_name)
        for _ in range(30):
            time.sleep(1)
            try:
                s = self.client.get_state()
                if s.get("world_ready", False):
                    print("Save loaded successfully! World ready.")
                    break
            except Exception:
                pass

    def run_day_cycle(self) -> bool:
        state = self.client.get_state()
        if not state.get("world_ready", False):
            print("World not ready.")
            return False

        t = state["time"]
        p = state["player"]
        print(f"\n=== Day {t['day']} of {t['season'].title()}, Year {t['year']} ===")
        print(f"Clock: {t['clock']} | Weather: {t['weather']} | Energy: {p['energy']}/{p['max_energy']} | Gold: {p['gold']}g")

        # 1. Close any lingering menu or event
        if state["ui"]["dialogue"] or state["ui"]["event"] or state["ui"]["menu"]:
            self.client.execute("close_ui", [{"skill": "close_menu"}])

        # 2. If in FarmHouse, walk outside to Farm
        if p["location"] != "Farm":
            print("Walking outside to Farm...")
            res = self.client.execute(
                "exit_house",
                [
                    {"skill": "close_menu"},
                    {"skill": "goto", "args": {"location": "Farm", "x": 66, "y": 20}},
                ],
            )
            if res.get("status") != "done":
                print(f"Warning: Navigation status: {res.get('error')} - {res.get('detail')}")

        # 3. Check Farm crops
        crops = self.client.get_farm()
        ready_to_harvest = [c for c in crops if c.get("ready")]
        unwatered = [c for c in crops if not c.get("wet") and not c.get("dead") and t.get("weather") != "rain"]

        print(f"Field Status: {len(crops)} total plots | {len(ready_to_harvest)} ready to harvest | {len(unwatered)} need water")

        # Harvest ready crops
        if ready_to_harvest:
            harvest_tiles = [[c["x"], c["y"]] for c in ready_to_harvest]
            print(f"Harvesting {len(harvest_tiles)} mature crops...")
            self.client.execute(
                "harvest_crops",
                [
                    {"skill": "goto", "args": {"location": "Farm", "x": harvest_tiles[0][0], "y": harvest_tiles[0][1] - 1}},
                    {"skill": "harvest", "args": {"tiles": harvest_tiles}},
                ],
            )

        # Water unwatered crops (unless raining)
        if unwatered and t.get("weather") != "rain":
            water_tiles = [[c["x"], c["y"]] for c in unwatered]
            print(f"Watering {len(water_tiles)} crop plots...")
            self.client.execute(
                "water_crops",
                [
                    {"skill": "goto", "args": {"location": "Farm", "x": water_tiles[0][0], "y": water_tiles[0][1] - 1}},
                    {"skill": "water", "args": {"tiles": water_tiles}},
                ],
            )
        elif t.get("weather") == "rain":
            print("Rainy day! No watering required.")

        # 4. Check inventory seeds for planting
        state = self.client.get_state()
        crops = self.client.get_farm()
        empty_plots = [c for c in crops if not c.get("crop")]

        seeds_in_inv = [
            item
            for item in state.get("inventory", [])
            if "seed" in item.get("name", "").lower() and item.get("stack", 0) > 0
        ]

        if empty_plots and seeds_in_inv:
            seed = seeds_in_inv[0]
            count_to_plant = min(len(empty_plots), seed["stack"])
            plant_tiles = [[c["x"], c["y"]] for c in empty_plots[:count_to_plant]]
            print(f"Planting {count_to_plant}x {seed['name']} on empty tilled plots...")
            self.client.execute(
                "plant_seeds",
                [
                    {"skill": "goto", "args": {"location": "Farm", "x": plant_tiles[0][0], "y": plant_tiles[0][1] - 1}},
                    {"skill": "plant", "args": {"item": seed["name"], "tiles": plant_tiles}},
                    {"skill": "water", "args": {"tiles": plant_tiles}},
                ],
            )

        # 5. Return to FarmHouse and sleep
        print("Daily chores completed. Returning to FarmHouse to sleep...")
        sleep_res = self.client.execute(
            "return_and_sleep",
            [
                {"skill": "goto", "args": {"location": "FarmHouse", "x": 9, "y": 9}},
                {"skill": "sleep"},
            ],
        )
        print(f"Sleep execution: {sleep_res.get('status')}")
        time.sleep(3)

        new_state = self.client.get_state()
        new_t = new_state.get("time", {})
        print(f"Advanced to Day {new_t.get('day')} of {new_t.get('season', '').title()}! Stamina fully restored.")
        return True

    def run_multi_day(self, days: int = 1):
        self.ensure_game_running()
        for i in range(days):
            print(f"\n>>> Starting Automated Day {i + 1}/{days} <<<")
            success = self.run_day_cycle()
            if not success:
                print("Failed to run day cycle.")
                break
            time.sleep(1)


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    grinder = AutonomousGrinder()
    grinder.run_multi_day(days=days)
