# Autonomous Stardew Valley Grinding Agent

An advanced autonomous AI gaming agent for Stardew Valley 1.6 on Windows. Operates directly on the running game window through Win32 Desktop API, DirectInput hardware scan codes, and GDI screen capture.

## Architecture

- `src/controller.py`: `GameController` handles window detection across Win32 desktops (`WinSta0\\Default`), window geometry, DPI-aware physical cursor positioning, mouse events, and DirectInput keyboard events (`pydirectinput`).
- `src/save_reader.py`: Ground-truth state verification directly from `%APPDATA%\StardewValley\Saves\<FarmName>_<Id>\<SaveFile>`.
- `tests/test_agent.py`: Verification test suite.

## Execution Cycle

`OBSERVE -> ANALYZE -> PLAN -> ACT -> VERIFY -> OPTIMIZE`

1. **Observe**: Captures high-resolution frame via `PrintWindow` and reads ground-truth save XML.
2. **Analyze**: Determines in-game day, season, gold, energy, crop status, weather, and active quests.
3. **Plan**: Schedules daily tasks (crop watering, tree chopping, chest crafting, beach rod unlock, mines progression).
4. **Act**: Dispatches DirectInput keystrokes and mouse clicks to the active game window.
5. **Verify**: Captures new frames to confirm successful animations and state transitions.
6. **Optimize**: Balances energy consumption and sleeps before cutoff to preserve progress without exhaustion.
