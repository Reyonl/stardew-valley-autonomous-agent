using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text.Json;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;
using StardewValley.Menus;
using StardewValley.Pathfinding;
using StardewValley.TerrainFeatures;
using StardewValley.Tools;

namespace AgentBridge;

public class PlanStep
{
    public string Skill { get; set; } = "";
    public Dictionary<string, JsonElement>? Args { get; set; }
}

public class PlanRequest
{
    public string Id { get; set; } = "";
    public List<PlanStep> Steps { get; set; } = new();
    public bool Interrupt { get; set; } = false;
}

public class PlanResult
{
    public string Id { get; set; } = "";
    public string Status { get; set; } = "idle";
    public int Step { get; set; } = 0;
    public int StepsTotal { get; set; } = 0;
    public string? Error { get; set; }
    public string Detail { get; set; } = "";
    public double ElapsedS { get; set; } = 0.0;
    public object? State { get; set; }
}

public class PlanExecutor
{
    private readonly IMonitor _monitor;
    private PlanRequest? _currentPlan;
    private int _currentStepIndex = 0;
    private Stopwatch _stopwatch = new();
    private PlanResult _lastResult = new();

    // Step execution state
    private bool _stepInitialized = false;
    private bool _isWarping = false;
    private int _waitTicksRemaining = 0;
    private Point _lastTile = Point.Zero;
    private int _stuckTicks = 0;

    public PlanResult CurrentStatus => _lastResult;

    public PlanExecutor(IMonitor monitor)
    {
        _monitor = monitor;
    }

    public bool AcceptPlan(PlanRequest plan)
    {
        if (_lastResult.Status == "running" && !plan.Interrupt)
        {
            return false;
        }

        _currentPlan = plan;
        _currentStepIndex = 0;
        _stepInitialized = false;
        _isWarping = false;
        _waitTicksRemaining = 0;
        _stuckTicks = 0;
        _stopwatch.Restart();

        _lastResult = new PlanResult
        {
            Id = plan.Id,
            Status = "running",
            Step = 0,
            StepsTotal = plan.Steps.Count,
            Error = null,
            Detail = "Plan started",
            ElapsedS = 0
        };

        _monitor.Log($"[PlanExecutor] Accepted plan '{plan.Id}' with {plan.Steps.Count} steps.", LogLevel.Info);
        return true;
    }

    public void CancelPlan()
    {
        if (_lastResult.Status == "running")
        {
            _stopwatch.Stop();
            _lastResult.Status = "interrupted";
            _lastResult.Detail = "Plan cancelled by user/API request";
            _lastResult.ElapsedS = Math.Round(_stopwatch.Elapsed.TotalSeconds, 2);
            _currentPlan = null;
            _isWarping = false;
            if (Game1.player != null)
                Game1.player.controller = null;
            _monitor.Log("[PlanExecutor] Plan cancelled.", LogLevel.Info);
        }
    }

    public void Update()
    {
        if (_currentPlan == null || _lastResult.Status != "running")
            return;

        if (!Context.IsWorldReady || Game1.player == null)
            return;

        // Auto-skip blocking cutscenes/events and dismiss dialogues during automated plan execution
        if (Game1.eventUp && Game1.CurrentEvent != null)
        {
            try
            {
                _monitor.Log("[PlanExecutor] Auto-skipping active event cutscene...", LogLevel.Info);
                Game1.CurrentEvent.skipEvent();
                Game1.eventUp = false;
            }
            catch { }
            Game1.player.CanMove = true;
        }

        if (Game1.dialogueUp || Game1.activeClickableMenu is DialogueBox)
        {
            try
            {
                Game1.dialogueUp = false;
                Game1.currentSpeaker = null;
                Game1.exitActiveMenu();
            }
            catch { }
            Game1.player.CanMove = true;
        }

        _lastResult.ElapsedS = Math.Round(_stopwatch.Elapsed.TotalSeconds, 2);

        if (_currentStepIndex >= _currentPlan.Steps.Count)
        {
            _stopwatch.Stop();
            _lastResult.Status = "done";
            _lastResult.Step = _currentPlan.Steps.Count;
            _lastResult.Detail = "All steps completed successfully";
            _currentPlan = null;
            _isWarping = false;
            _monitor.Log($"[PlanExecutor] Plan '{_lastResult.Id}' completed in {_lastResult.ElapsedS}s.", LogLevel.Info);
            return;
        }

        var step = _currentPlan.Steps[_currentStepIndex];
        _lastResult.Step = _currentStepIndex + 1;

        try
        {
            ExecuteStep(step);
        }
        catch (Exception ex)
        {
            FailStep("EXCEPTION", ex.Message);
        }
    }

    private void ExecuteStep(PlanStep step)
    {
        string skill = step.Skill.ToLowerInvariant();

        switch (skill)
        {
            case "goto":
                ExecuteGoto(step);
                break;
            case "face":
                ExecuteFace(step);
                break;
            case "select_item":
                ExecuteSelectItem(step);
                break;
            case "till":
                ExecuteTill(step);
                break;
            case "plant":
                ExecutePlant(step);
                break;
            case "water":
                ExecuteWater(step);
                break;
            case "harvest":
                ExecuteHarvest(step);
                break;
            case "sleep":
                ExecuteSleep(step);
                break;
            case "close_menu":
                ExecuteCloseMenu(step);
                break;
            case "wait":
                ExecuteWait(step);
                break;
            default:
                FailStep("BAD_ARGS", $"Unknown skill: {step.Skill}");
                break;
        }
    }

    private void AdvanceStep()
    {
        _currentStepIndex++;
        _stepInitialized = false;
        _isWarping = false;
        _stuckTicks = 0;
        if (Game1.player != null)
            Game1.player.controller = null;
    }

    private void FailStep(string errorCode, string detail)
    {
        _stopwatch.Stop();
        _lastResult.Status = "failed";
        _lastResult.Error = errorCode;
        _lastResult.Detail = detail;
        _lastResult.ElapsedS = Math.Round(_stopwatch.Elapsed.TotalSeconds, 2);
        _currentPlan = null;
        _isWarping = false;
        if (Game1.player != null)
            Game1.player.controller = null;
        _monitor.Log($"[PlanExecutor] Plan failed at step {_lastResult.Step} ({errorCode}): {detail}", LogLevel.Warn);
    }

    private void ExecuteGoto(PlanStep step)
    {
        var player = Game1.player;
        string targetLoc = step.Args != null && step.Args.TryGetValue("location", out var locElem) ? locElem.GetString() ?? "" : "";
        int targetX = step.Args != null && step.Args.TryGetValue("x", out var xElem) ? xElem.GetInt32() : player.TilePoint.X;
        int targetY = step.Args != null && step.Args.TryGetValue("y", out var yElem) ? yElem.GetInt32() : player.TilePoint.Y;

        string currentLoc = player.currentLocation?.NameOrUniqueName ?? player.currentLocation?.Name ?? "";

        // Check cross-location warp
        if (!string.IsNullOrEmpty(targetLoc) && !string.Equals(currentLoc, targetLoc, StringComparison.OrdinalIgnoreCase))
        {
            if (_isWarping)
            {
                return;
            }

            Warp? warp = null;
            if (player.currentLocation?.warps != null)
            {
                foreach (var w in player.currentLocation.warps)
                {
                    if (string.Equals(w.TargetName, targetLoc, StringComparison.OrdinalIgnoreCase))
                    {
                        warp = w;
                        break;
                    }
                }
            }

            if (warp == null)
            {
                if (currentLoc == "FarmHouse" && targetLoc == "Farm")
                {
                    warp = new Warp(3, 12, "Farm", 64, 15, false);
                }
                else if (currentLoc == "Farm" && targetLoc == "FarmHouse")
                {
                    warp = new Warp(64, 15, "FarmHouse", 9, 9, false);
                }
                else
                {
                    warp = new Warp(player.TilePoint.X, player.TilePoint.Y, targetLoc, targetX, targetY, false);
                }
            }

            int distToWarp = Math.Abs(player.TilePoint.X - warp.X) + Math.Abs(player.TilePoint.Y - warp.Y);
            if (distToWarp <= 1)
            {
                _isWarping = true;
                _monitor.Log($"[PlanExecutor] Warping from {currentLoc} to {warp.TargetName} at ({warp.TargetX}, {warp.TargetY})", LogLevel.Info);
                Game1.warpFarmer(warp.TargetName, warp.TargetX, warp.TargetY, false);
                return;
            }

            if (player.controller == null)
            {
                player.controller = new PathFindController(player, player.currentLocation, new Point(warp.X, warp.Y - 1), -1);
                if (player.controller.pathToEndPoint == null)
                {
                    _isWarping = true;
                    Game1.warpFarmer(warp.TargetName, warp.TargetX, warp.TargetY, false);
                }
            }
            return;
        }

        // We are in the target location
        _isWarping = false;
        int dist = Math.Abs(player.TilePoint.X - targetX) + Math.Abs(player.TilePoint.Y - targetY);
        if (dist <= 1)
        {
            AdvanceStep();
            return;
        }

        if (!_stepInitialized)
        {
            _stepInitialized = true;
            _lastTile = player.TilePoint;
            _stuckTicks = 0;
            player.controller = new PathFindController(player, player.currentLocation, new Point(targetX, targetY), -1);
            if (player.controller.pathToEndPoint == null)
            {
                Point[] adj = new Point[] {
                    new Point(targetX, targetY - 1),
                    new Point(targetX, targetY + 1),
                    new Point(targetX - 1, targetY),
                    new Point(targetX + 1, targetY)
                };
                foreach (var p in adj)
                {
                    player.controller = new PathFindController(player, player.currentLocation, p, -1);
                    if (player.controller.pathToEndPoint != null) break;
                }

                if (player.controller?.pathToEndPoint == null && dist > 1)
                {
                    FailStep("NO_PATH", $"No walkable path to ({targetX}, {targetY}) in {currentLoc}");
                    return;
                }
            }
        }
        else
        {
            if (player.TilePoint == _lastTile)
            {
                _stuckTicks++;
                if (_stuckTicks > 120) // ~2 seconds without tile change
                {
                    FailStep("STUCK", $"Player stuck at tile {player.TilePoint} while trying to reach ({targetX}, {targetY})");
                    return;
                }
            }
            else
            {
                _lastTile = player.TilePoint;
                _stuckTicks = 0;
            }

            if (player.controller == null || dist <= 1)
            {
                AdvanceStep();
            }
        }
    }

    private void ExecuteFace(PlanStep step)
    {
        int dir = step.Args != null && step.Args.TryGetValue("dir", out var dirElem) ? dirElem.GetInt32() : 2;
        Game1.player.faceDirection(dir);
        AdvanceStep();
    }

    private void ExecuteSelectItem(PlanStep step)
    {
        string name = step.Args != null && step.Args.TryGetValue("name", out var nameElem) ? nameElem.GetString() ?? "" : "";
        int foundSlot = -1;

        for (int i = 0; i < Game1.player.Items.Count; i++)
        {
            var item = Game1.player.Items[i];
            if (item != null)
            {
                if (string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(item.DisplayName, name, StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(item.QualifiedItemId, name, StringComparison.OrdinalIgnoreCase))
                {
                    foundSlot = i;
                    break;
                }
            }
        }

        if (foundSlot >= 0)
        {
            Game1.player.CurrentToolIndex = foundSlot;
            AdvanceStep();
        }
        else
        {
            FailStep("ITEM_NOT_FOUND", $"Item '{name}' not found in inventory");
        }
    }

    private List<Point> ParseTiles(PlanStep step)
    {
        var result = new List<Point>();
        if (step.Args == null) return result;

        if (step.Args.TryGetValue("tiles", out var tilesElem))
        {
            if (tilesElem.ValueKind == JsonValueKind.Array)
            {
                foreach (var t in tilesElem.EnumerateArray())
                {
                    if (t.ValueKind == JsonValueKind.Array)
                    {
                        var arr = t.EnumerateArray();
                        arr.MoveNext(); int x = arr.Current.GetInt32();
                        arr.MoveNext(); int y = arr.Current.GetInt32();
                        result.Add(new Point(x, y));
                    }
                }
            }
            else if (tilesElem.ValueKind == JsonValueKind.Object && tilesElem.TryGetProperty("rect", out var rectElem))
            {
                var arr = rectElem.EnumerateArray();
                arr.MoveNext(); int x1 = arr.Current.GetInt32();
                arr.MoveNext(); int y1 = arr.Current.GetInt32();
                arr.MoveNext(); int x2 = arr.Current.GetInt32();
                arr.MoveNext(); int y2 = arr.Current.GetInt32();

                for (int y = y1; y <= y2; y++)
                {
                    bool ltr = (y - y1) % 2 == 0;
                    if (ltr)
                    {
                        for (int x = x1; x <= x2; x++) result.Add(new Point(x, y));
                    }
                    else
                    {
                        for (int x = x2; x >= x1; x--) result.Add(new Point(x, y));
                    }
                }
            }
        }

        return result;
    }

    private void ExecuteTill(PlanStep step)
    {
        var player = Game1.player;
        if (player.Stamina < 15.0f)
        {
            FailStep("LOW_ENERGY", "Player stamina below 15; cannot till");
            return;
        }

        Tool? hoe = null;
        for (int i = 0; i < player.Items.Count; i++)
        {
            if (player.Items[i] is Hoe h)
            {
                hoe = h;
                player.CurrentToolIndex = i;
                break;
            }
        }

        if (hoe == null)
        {
            FailStep("ITEM_NOT_FOUND", "Hoe not found in inventory");
            return;
        }

        var tiles = ParseTiles(step);
        foreach (var t in tiles)
        {
            Vector2 tileVec = new Vector2(t.X, t.Y);
            if (!player.currentLocation.terrainFeatures.ContainsKey(tileVec))
            {
                hoe.DoFunction(player.currentLocation, t.X * 64, t.Y * 64, 1, player);
                if (!player.currentLocation.terrainFeatures.ContainsKey(tileVec))
                {
                    player.currentLocation.terrainFeatures[tileVec] = new HoeDirt(0);
                }
                player.Stamina -= 2.0f;
            }
        }

        AdvanceStep();
    }

    private void ExecutePlant(PlanStep step)
    {
        var player = Game1.player;
        string itemName = step.Args != null && step.Args.TryGetValue("item", out var itemElem) ? itemElem.GetString() ?? "" : "";
        Item? seedItem = null;
        int seedSlot = -1;

        for (int i = 0; i < player.Items.Count; i++)
        {
            var item = player.Items[i];
            if (item != null && (string.Equals(item.Name, itemName, StringComparison.OrdinalIgnoreCase) ||
                                string.Equals(item.QualifiedItemId, itemName, StringComparison.OrdinalIgnoreCase) ||
                                item.Name.Contains("Seeds", StringComparison.OrdinalIgnoreCase)))
            {
                seedItem = item;
                seedSlot = i;
                player.CurrentToolIndex = i;
                break;
            }
        }

        if (seedItem == null)
        {
            FailStep("ITEM_NOT_FOUND", $"Seed item '{itemName}' not found in inventory");
            return;
        }

        var tiles = ParseTiles(step);
        foreach (var t in tiles)
        {
            Vector2 tileVec = new Vector2(t.X, t.Y);
            if (player.currentLocation.terrainFeatures.TryGetValue(tileVec, out var tf) && tf is HoeDirt dirt)
            {
                if (dirt.crop == null && seedItem.Stack > 0)
                {
                    dirt.plant(seedItem.QualifiedItemId, player, false);
                    seedItem.Stack--;
                    if (seedItem.Stack <= 0)
                    {
                        player.Items[seedSlot] = null;
                        break;
                    }
                }
            }
        }

        AdvanceStep();
    }

    private void ExecuteWater(PlanStep step)
    {
        var player = Game1.player;
        if (player.Stamina < 10.0f)
        {
            FailStep("LOW_ENERGY", "Player stamina below 10; cannot water");
            return;
        }

        Tool? can = null;
        for (int i = 0; i < player.Items.Count; i++)
        {
            if (player.Items[i] is WateringCan c)
            {
                can = c;
                player.CurrentToolIndex = i;
                break;
            }
        }

        if (can == null)
        {
            FailStep("ITEM_NOT_FOUND", "Watering Can not found in inventory");
            return;
        }

        var tiles = ParseTiles(step);
        foreach (var t in tiles)
        {
            Vector2 tileVec = new Vector2(t.X, t.Y);
            if (player.currentLocation.terrainFeatures.TryGetValue(tileVec, out var tf) && tf is HoeDirt dirt)
            {
                if (dirt.state.Value != HoeDirt.watered)
                {
                    dirt.state.Value = HoeDirt.watered;
                    player.Stamina -= 2.0f;
                }
            }
        }

        AdvanceStep();
    }

    private void ExecuteHarvest(PlanStep step)
    {
        var player = Game1.player;
        var tiles = ParseTiles(step);

        foreach (var t in tiles)
        {
            Vector2 tileVec = new Vector2(t.X, t.Y);
            if (player.currentLocation.terrainFeatures.TryGetValue(tileVec, out var tf) && tf is HoeDirt dirt)
            {
                if (dirt.crop != null && dirt.readyForHarvest())
                {
                    dirt.performUseAction(tileVec);
                    _monitor.Log($"[PlanExecutor] Harvested crop at ({t.X}, {t.Y})", LogLevel.Info);
                }
            }
        }

        AdvanceStep();
    }

    private void ExecuteSleep(PlanStep step)
    {
        _monitor.Log("[PlanExecutor] Ending day via answerDialogueAction('Sleep_Yes')...", LogLevel.Info);
        if (Game1.currentLocation != null)
        {
            Game1.currentLocation.answerDialogueAction("Sleep_Yes", null);
        }
        AdvanceStep();
    }

    private void ExecuteCloseMenu(PlanStep step)
    {
        if (Game1.activeClickableMenu != null)
        {
            try { Game1.exitActiveMenu(); } catch { }
        }
        if (Game1.dialogueUp)
        {
            Game1.dialogueUp = false;
            Game1.currentSpeaker = null;
        }
        if (Game1.eventUp && Game1.CurrentEvent != null)
        {
            try { Game1.CurrentEvent.skipEvent(); } catch { }
            Game1.eventUp = false;
        }
        Game1.player.CanMove = true;
        AdvanceStep();
    }

    private void ExecuteWait(PlanStep step)
    {
        if (!_stepInitialized)
        {
            double sec = step.Args != null && step.Args.TryGetValue("seconds", out var secElem) ? secElem.GetDouble() : 1.0;
            _waitTicksRemaining = (int)(sec * 60);
            _stepInitialized = true;
        }

        _waitTicksRemaining--;
        if (_waitTicksRemaining <= 0)
        {
            AdvanceStep();
        }
    }
}
