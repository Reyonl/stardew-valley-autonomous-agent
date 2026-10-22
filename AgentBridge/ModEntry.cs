using System;
using StardewModdingAPI;
using StardewModdingAPI.Events;
using StardewValley;
using StardewValley.Menus;

namespace AgentBridge;

public class ModEntry : Mod
{
    private WebServer? _webServer;
    private PlanExecutor? _planExecutor;
    private int _tickCounter = 0;

    public override void Entry(IModHelper helper)
    {
        _planExecutor = new PlanExecutor(this.Monitor);
        _webServer = new WebServer(this.Monitor, _planExecutor);
        _webServer.Start();

        helper.Events.GameLoop.UpdateTicked += OnUpdateTicked;

        helper.ConsoleCommands.Add("agent_load", "Loads latest or named save", (cmd, args) =>
        {
            string saveName = args.Length > 0 ? args[0] : "LauS_426336281";
            _webServer.CommandQueue.Enqueue(() =>
            {
                this.Monitor.Log($"Attempting to load save: {saveName}...", LogLevel.Info);
                SaveGame.Load(saveName);
            });
        });

        this.Monitor.Log("AgentBridge initialized and ready on http://127.0.0.1:8765/", LogLevel.Info);
    }

    private void OnUpdateTicked(object? sender, UpdateTickedEventArgs e)
    {
        // 0. Ensure game never pauses when window is unfocused in background
        if (Game1.options != null)
        {
            Game1.options.pauseWhenOutOfFocus = false;
        }

        // 1. Drain command queue on main game thread
        if (_webServer != null)
        {
            while (_webServer.CommandQueue.TryDequeue(out var action))
            {
                try
                {
                    action();
                }
                catch (Exception ex)
                {
                    this.Monitor.Log($"Error executing queued action: {ex.Message}", LogLevel.Error);
                }
            }
        }

        // 2. Dismiss TitleMenu after load finishes
        if (Game1.hasLoadedGame && Game1.activeClickableMenu is TitleMenu)
        {
            try
            {
                Game1.exitActiveMenu();
            }
            catch { }
        }

        // 3. Update active plan
        _planExecutor?.Update();

        // 4. Update cached telemetry snapshots ~10 Hz (every 6 ticks)
        _tickCounter++;
        if (_tickCounter % 6 == 0 && _webServer != null && _planExecutor != null)
        {
            try
            {
                _webServer.CachedStateJson = StateSnapshot.BuildSnapshot(_planExecutor.CurrentStatus);
                _webServer.CachedMapJson = MapData.BuildMapJson();
                _webServer.CachedFarmJson = FarmData.BuildFarmJson();
            }
            catch (Exception ex)
            {
                this.Monitor.Log($"Error caching telemetry: {ex.Message}", LogLevel.Trace);
            }
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _webServer?.Stop();
        }
        base.Dispose(disposing);
    }
}
