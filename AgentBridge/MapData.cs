using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Xna.Framework;
using StardewModdingAPI;
using StardewValley;

namespace AgentBridge;

public static class MapData
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = false
    };

    public static string BuildMapJson()
    {
        if (!Context.IsWorldReady || Game1.currentLocation == null)
        {
            return "{}";
        }

        var loc = Game1.currentLocation;
        int width = loc.Map.Layers[0].LayerWidth;
        int height = loc.Map.Layers[0].LayerHeight;

        // Cap reasonable dimensions for very large outdoor maps
        int mapW = Math.Min(width, 160);
        int mapH = Math.Min(height, 160);

        var rows = new List<string>(mapH);
        for (int y = 0; y < mapH; y++)
        {
            char[] row = new char[mapW];
            for (int x = 0; x < mapW; x++)
            {
                bool passable = loc.isTilePassable(new xTile.Dimensions.Location(x, y), Game1.viewport);
                bool colliding = loc.isCollidingPosition(new Rectangle(x * 64, y * 64, 64, 64), Game1.viewport, Game1.player);
                row[x] = (passable && !colliding) ? '.' : '#';
            }
            rows.Add(new string(row));
        }

        var warps = new List<object>();
        if (loc.warps != null)
        {
            foreach (var w in loc.warps)
            {
                warps.Add(new
                {
                    x = w.X,
                    y = w.Y,
                    target_location = w.TargetName,
                    target_x = w.TargetX,
                    target_y = w.TargetY
                });
            }
        }

        var result = new
        {
            location = loc.NameOrUniqueName ?? loc.Name,
            width = mapW,
            height = mapH,
            walkable = rows,
            warps = warps
        };

        return JsonSerializer.Serialize(result, JsonOptions);
    }
}
