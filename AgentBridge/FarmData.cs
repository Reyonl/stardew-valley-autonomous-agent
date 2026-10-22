using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;
using StardewValley.TerrainFeatures;

namespace AgentBridge;

public static class FarmData
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false
    };

    public static string BuildFarmJson()
    {
        if (!Context.IsWorldReady || Game1.currentLocation == null)
        {
            return "[]";
        }

        var loc = Game1.currentLocation;
        var list = new List<object>();

        foreach (var pair in loc.terrainFeatures.Pairs)
        {
            if (pair.Value is HoeDirt dirt)
            {
                int x = (int)pair.Key.X;
                int y = (int)pair.Key.Y;
                bool wet = dirt.state.Value == HoeDirt.watered;
                string cropName = "";
                int phase = 0;
                bool ready = false;
                bool dead = false;

                if (dirt.crop != null)
                {
                    phase = dirt.crop.currentPhase.Value;
                    ready = dirt.readyForHarvest();
                    dead = dirt.crop.dead.Value;

                    // Get crop produce name if possible
                    string harvestId = dirt.crop.indexOfHarvest.Value;
                    var parsedItem = ItemRegistry.GetData(harvestId);
                    cropName = parsedItem?.DisplayName ?? harvestId ?? "Unknown";
                }

                list.Add(new
                {
                    x = x,
                    y = y,
                    wet = wet,
                    crop = string.IsNullOrEmpty(cropName) ? null : cropName,
                    phase = phase,
                    ready = ready,
                    dead = dead
                });
            }
        }

        return JsonSerializer.Serialize(list, JsonOptions);
    }
}
