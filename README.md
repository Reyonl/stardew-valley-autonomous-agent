# Autonomous Stardew Valley Grinding Agent

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform Windows](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey.svg)](https://microsoft.com/windows)
[![Stardew Valley 1.6](https://img.shields.io/badge/Stardew%20Valley-1.6%2B-brightgreen.svg)](https://www.stardewvalley.net/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An open-source autonomous agent framework designed to control and grind **Stardew Valley 1.6+** on Windows. Operates directly on the running game window through Win32 Desktop API switching, DirectInput hardware scan codes, DPI-aware GDI screen capture, and ground-truth XML save telemetry.

Designed for AI researchers, game automation developers, and the Stardew Valley community exploring autonomous gameplay, speedrunning assistance, and farming state optimization.

---

## 🌟 Key Engineering Highlights

Game automation in modern DirectX/XNA games like Stardew Valley often encounters barriers with traditional tools (such as standard `pyautogui` or virtual desktops). This framework solves these fundamental hurdles:

1. **Win32 Desktop Isolation Bypass (`WinSta0\\Default`)**  
   Background agents and terminal workers often run under separate Windows session desktops (e.g. `exebox-*`). The controller explicitly attaches to the interactive desktop (`SetThreadDesktop`) and acquires the active `Stardew Valley` window handle (`HWND`) dynamically.

2. **DPI-Aware Physical Cursor & DirectInput Keyboard**  
   Windows display scaling often misaligns mouse clicks. By declaring process DPI awareness (`SetProcessDPIAware()`) and translating coordinates relative to the game window bounding rectangle (`GetWindowRect`), clicks land accurately on UI buttons and inventory slots. Keystrokes are sent via DirectInput hardware scan codes (`pydirectinput`) with calibrated hold times matching Stardew's 60 FPS input polling cycle.

3. **Background GDI Frame Capture (`PW_RENDERFULLCONTENT`)**  
   Captures full-resolution game frames directly from the window Device Context (`PrintWindow` with flag `PW_RENDERFULLCONTENT = 2`) without needing to occlude or take over the entire computer display.

4. **Dual Verification: Ground-Truth Save Telemetry**  
   Unlike pure computer vision agents that may hallucinate values, this framework combines visual observation with ground-truth XML telemetry from `%APPDATA%\StardewValley\Saves\<FarmName>_<Id>\<SaveFile>`. It tracks:
   - In-game date, time, season, and weather forecasts.
   - Exact gold, stamina, health, and max stamina.
   - Farm tile grid coordinates, HoeDirt status, crop types, growth phases, and whether crops are watered today.

---

## 🏗️ Architecture & Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── controller.py       # Core Win32 desktop switching, window capture & DirectInput control
│   └── save_reader.py      # Ground-truth XML parser for farm tiles, crops & player state
├── tests/
│   ├── __init__.py
│   └── test_agent.py       # Deterministic unit & integration test suite (with fixtures)
├── stardew_controller.py   # High-level vision & autonomous state machine helper
├── requirements.txt        # Python package dependencies
├── LICENSE                 # MIT License
└── README.md               # Documentation & community guide
```

---

## 🔄 Autonomous Execution Loop

The agent follows a closed-loop perception-action-verification cycle:

```
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│    OBSERVE     │ ───> │    ANALYZE     │ ───> │     PLAN       │
│ Screen + Save  │      │ Weather, Crops │      │ Highest Value  │
└────────────────┘      └────────────────┘      └────────────────┘
        ▲                                                │
        │                                                ▼
┌────────────────┐      ┌────────────────┐      ┌────────────────┐
│    OPTIMIZE    │ <─── │     VERIFY     │ <─── │      ACT       │
│ Sleep & Save   │      │ Inspect Result │      │ DirectInput    │
└────────────────┘      └────────────────┘      └────────────────┘
```

1. **Observe**: Captures high-resolution frame via `PrintWindow` and reads ground-truth save XML.
2. **Analyze**: Determines in-game day, season, gold, energy, crop status, weather, and active quests.
3. **Plan**: Prioritizes daily tasks (crop watering, tree chopping, chest crafting, beach rod unlock, mines progression).
4. **Act**: Dispatches DirectInput keystrokes and mouse clicks to the active game window.
5. **Verify**: Captures new frames to confirm successful animations and state transitions.
6. **Optimize**: Balances energy consumption and sleeps before cutoff to preserve progress without exhaustion.

---

## 🚀 Getting Started

### Prerequisites
- **Operating System**: Windows 10 or 11
- **Python**: 3.10 or higher
- **Game**: Stardew Valley 1.6+ (installed and launchable)

### 1. Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/Reyonl/stardew-valley-autonomous-agent.git
cd stardew-valley-autonomous-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Running Unit Tests

Run the deterministic test suite:

```bash
python -m unittest discover tests
```

Expected output:
```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.45s

OK
```

### 3. Usage Examples

#### Reading Live Game Telemetry

```python
from src.save_reader import get_latest_save

save = get_latest_save()
if save:
    print(f"Farmer: {save['player_name']} on {save['farm_name']} Farm")
    print(f"Date: Day {save['day']} of {save['season'].title()}, Year {save['year']}")
    print(f"Gold: {save['money']}g | Stamina: {save['stamina']}/{save['max_stamina']}")
    print(f"Crops: {save['crops_watered']}/{save['crops_total']} watered today")
    print(f"Tomorrow's Weather: {save['weather_tomorrow']}")
```

#### Controlling the Game Window

```python
from src.controller import GameController

# Connects to running Stardew Valley window
ctrl = GameController()

# Focus and capture current frame
im = ctrl.capture(save_path="current_state.png")

# Move character (w=Up, a=Left, s=Down, d=Right)
ctrl.move('w', duration=0.8)

# Select inventory slot (1-10) and use tool ('c')
ctrl.select_slot(3)  # Watering can
ctrl.use_tool()

# Interact with NPC / harvest crop / read dialogue ('x')
ctrl.interact()
```

---

## 🗺️ Community Roadmap & Future Work

- [x] Win32 desktop switching & DPI-aware cursor alignment
- [x] Ground-truth XML save file parsing (crops, player state, season)
- [x] Automatic parsnip harvest & quest reward claiming
- [ ] Automated fishing minigame solver with OpenCV green bar tracking
- [ ] A* pathfinding across Farm, Pelican Town, Beach, and Mountains
- [ ] Mines progression automation (ore mining, monster combat, ladder detection)
- [ ] Community Center bundle tracker & auto-turn-in planner

---

## 🤝 Contributing

Contributions, issues, and feature requests from the Stardew Valley and AI gaming community are welcome!
Feel free to check the [issues page](https://github.com/Reyonl/stardew-valley-autonomous-agent/issues) or submit a Pull Request:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feat/amazing-feature`)
3. Commit your Changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the Branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Disclaimer: This project is an independent open-source tool for research and automation education. Stardew Valley is developed by ConcernedApe.*
