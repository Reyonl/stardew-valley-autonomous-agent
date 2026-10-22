"""
Autonomous Stardew Valley Grinding Agent Runner
Executes autonomous daily farming, harvesting, watering, shipping, quest unlocking, and overnight cycles via AgentBridge.
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

    def check_and_unlock_quests(self, state: Dict[str, Any]):
        """Unlocks major game milestones (Willy's Fishing Rod, Mines Sword, Community Center)"""
        t = state.get("time", {})
        inv = state.get("inventory", [])
        has_rod = any("pole" in (item.get("name") or "").lower() for item in inv)
        has_sword = any("sword" in (item.get("name") or "").lower() for item in inv)

        # 1. Willy's Fishing Rod (Beach)
        if not has_rod:
            print("Checking Quest: Visiting Beach for Willy's fishing rod...")
            self.client.execute(
                "quest_beach",
                [
                    {"skill": "goto", "args": {"location": "Beach", "x": 30, "y": 30}},
                    {"skill": "close_menu"},
                ],
            )
        else:
            print("Fishing Rod already in inventory, skipping Beach quest.")

        # 2. Mines Entrance & Marlon's Sword
        if not has_sword:
            print("Checking Quest: Visiting Mountain for Marlon's sword...")
            self.client.execute(
                "quest_mine",
                [
                    {"skill": "goto", "args": {"location": "Mountain", "x": 54, "y": 9}},
                    {"skill": "close_menu"},
                ],
            )
        else:
            print("Weapon already acquired, skipping Mine quest.")

        # 3. Community Center (only on sunny days between 8am and 1pm)
        if t.get("weather") != "rain" and 800 <= t.get("clock", 600) <= 1300:
            print("Checking Quest: Visiting Town for Community Center event...")
            self.client.execute(
                "quest_cc",
                [
                    {"skill": "goto", "args": {"location": "Town", "x": 35, "y": 55}},
                    {"skill": "close_menu"},
                ],
            )

    def run_day_cycle(self, check_quests: bool = False) -> bool:
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

        # Check key quest milestones if requested or at start of season
        if check_quests:
            self.check_and_unlock_quests(state)

        # 2. If not at Farm, walk to Farm
        state = self.client.get_state()
        p = state["player"]
        if p["location"] != "Farm":
            print("Walking to Farm...")
            res = self.client.execute(
                "go_to_farm",
                [
                    {"skill": "close_menu"},
                    {"skill": "goto", "args": {"location": "Farm", "x": 66, "y": 20}},
                ],
            )
            if res.get("status") != "done":
                print(f"Warning: Navigation status: {res.get('error')} - {res.get('detail')}")

        # 3. Check Farm crops & clear dead ones (seasonal rollover)
        crops = self.client.get_farm()
        dead_crops = [c for c in crops if c.get("dead")]
        if dead_crops:
            print(f"Clearing {len(dead_crops)} withered crops from seasonal transition...")
            self.client.execute("clear_dead", [{"skill": "clear_dead"}])
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

        # 4. Check inventory seeds for planting / buy seeds if empty
        state = self.client.get_state()
        crops = self.client.get_farm()
        empty_plots = [c for c in crops if not c.get("crop")]

        seeds_in_inv = [
            item
            for item in state.get("inventory", [])
            if "seed" in item.get("name", "").lower() and item.get("stack", 0) > 0
        ]

        if empty_plots and not seeds_in_inv and t.get("season") != "winter":
            print(f"Empty plots detected ({len(empty_plots)}). Purchasing seasonal seeds...")
            self.client.execute("buy_seeds", [{"skill": "buy_seeds", "args": {"count": len(empty_plots)}}])
            state = self.client.get_state()
            seeds_in_inv = [
                item
                for item in state.get("inventory", [])
                if "seed" in item.get("name", "").lower() and item.get("stack", 0) > 0
            ]

        if empty_plots and seeds_in_inv:
            seed = seeds_in_inv[0]
            count_to_plant = min(len(empty_plots), seed["stack"])
            plant_tiles = [[c["x"], c["y"]] for c in empty_plots[:count_to_plant]]
            print(f"Planting {count_to_plant}x {seed['name']} on empty plots...")
            self.client.execute(
                "plant_seeds",
                [
                    {"skill": "goto", "args": {"location": "Farm", "x": plant_tiles[0][0], "y": plant_tiles[0][1] - 1}},
                    {"skill": "plant", "args": {"item": seed["name"], "tiles": plant_tiles}},
                    {"skill": "water", "args": {"tiles": plant_tiles}},
                ],
            )

        # 5. Deposit produce and forage into Shipping Bin
        print("Depositing sellable produce into Shipping Bin...")
        self.client.execute("ship_items", [{"skill": "ship"}])

        # 6. Return to FarmHouse and sleep
        print("Daily chores completed. Returning to FarmHouse to sleep...")
        sleep_res = self.client.execute(
            "return_and_sleep",
            [
                {"skill": "goto", "args": {"location": "FarmHouse", "x": 8, "y": 9}},
                {"skill": "sleep"},
            ],
        )
        print(f"Sleep execution: {sleep_res.get('status')}")

        # Wait for the night transition and save writing to complete
        initial_day = t["day"]
        print(f"Waiting for night transition from Day {initial_day}...")
        for _ in range(40):
            time.sleep(1)
            try:
                s = self.client.get_state()
                if not s.get("world_ready", False):
                    continue
                # Dismiss overnight menus if any (e.g. shipping tally, level up screen)
                menu_name = s.get("ui", {}).get("menu") or ""
                if menu_name:
                    print(f"Overnight menu detected: {menu_name}")
                if (menu_name and "save" not in menu_name.lower()) or s.get("ui", {}).get("dialogue"):
                    self.client.execute("dismiss_night_menu", [{"skill": "close_menu"}])

                current_day = s.get("time", {}).get("day")
                if current_day != initial_day:
                    new_t = s.get("time", {})
                    p_new = s.get("player", {})
                    print(f"Advanced to Day {new_t.get('day')} of {new_t.get('season', '').title()}! Gold: {p_new.get('gold')}g. Stamina restored.")
                    print("Allowing save file to finish flushing to disk...")
                    time.sleep(3)
                    return True
            except Exception:
                pass

        print("Warning: Day transition timed out or save still in progress.")
        return True

    def run_multi_day(self, days: int = 1):
        self.ensure_game_running()
        for i in range(days):
            print(f"\n>>> Starting Automated Day {i + 1}/{days} <<<")
            # Check quests on day 1 or every 7 days
            check_q = (i == 0 or (i + 1) % 7 == 0)
            success = self.run_day_cycle(check_quests=check_q)
            if not success:
                print("Failed to run day cycle.")
                break
            time.sleep(1)


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    grinder = AutonomousGrinder()
    grinder.run_multi_day(days=days)
