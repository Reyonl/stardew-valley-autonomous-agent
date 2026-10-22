using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using StardewModdingAPI;
using StardewValley;

namespace AgentBridge;

public static class StateSnapshot
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
        WriteIndented = false
    };

    public static string BuildSnapshot(object? planStatus = null)
    {
        if (Game1.player == null || (!Context.IsWorldReady && !Game1.hasLoadedGame))
        {
            return "{\"world_ready\":false}";
        }

        var player = Game1.player;
        var location = player.currentLocation;
        string locName = location?.NameOrUniqueName ?? location?.Name ?? "Unknown";

        string weather = "sunny";
        try
        {
            if (Game1.isRaining)
                weather = Game1.isLightning ? "storm" : "rain";
            else if (Game1.isDebrisWeather)
                weather = "wind";
            else if (Game1.isSnowing)
                weather = "snow";
        }
        catch { }

        var inventory = new List<object>();
        try
        {
            for (int i = 0; i < player.Items.Count; i++)
            {
                var item = player.Items[i];
                if (item != null)
                {
                    inventory.Add(new
                    {
                        slot = i,
                        id = item.QualifiedItemId ?? "",
                        name = item.DisplayName ?? item.Name ?? "",
                        stack = item.Stack
                    });
                }
            }
        }
        catch { }

        var state = new
        {
            world_ready = true,
            time = new
            {
                day = Game1.dayOfMonth,
                season = Game1.currentSeason ?? "spring",
                year = Game1.year,
                clock = Game1.timeOfDay,
                weather = weather
            },
            player = new
            {
                location = locName,
                tile = new[] { player.TilePoint.X, player.TilePoint.Y },
                facing = player.FacingDirection,
                energy = Math.Round((double)player.Stamina, 1),
                max_energy = player.MaxStamina,
                gold = player.Money,
                holding = player.CurrentItem?.DisplayName ?? player.CurrentItem?.Name ?? "",
                slot = player.CurrentToolIndex,
                moving = player.isMoving(),
                can_move = player.CanMove
            },
            ui = new
            {
                menu = Game1.activeClickableMenu?.GetType().Name,
                dialogue = Game1.dialogueUp,
                @event = Game1.eventUp
            },
            inventory = inventory,
            plan = planStatus
        };

        return JsonSerializer.Serialize(state, JsonOptions);
    }
}
