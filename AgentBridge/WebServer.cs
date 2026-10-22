using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using StardewModdingAPI;
using StardewValley;

namespace AgentBridge;

public class WebServer
{
    private readonly HttpListener _listener = new();
    private readonly IMonitor _monitor;
    private readonly PlanExecutor _planExecutor;
    private CancellationTokenSource? _cts;
    public readonly ConcurrentQueue<Action> CommandQueue = new();

    public volatile string CachedStateJson = "{\"world_ready\":false}";
    public volatile string CachedMapJson = "{}";
    public volatile string CachedFarmJson = "[]";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = false
    };

    public WebServer(IMonitor monitor, PlanExecutor planExecutor)
    {
        _monitor = monitor;
        _planExecutor = planExecutor;
        _listener.Prefixes.Add("http://127.0.0.1:8765/");
    }

    public void Start()
    {
        try
        {
            _cts = new CancellationTokenSource();
            _listener.Start();
            _monitor.Log("AgentBridge HTTP server listening on http://127.0.0.1:8765/", LogLevel.Info);
            Task.Run(() => ListenLoop(_cts.Token));
        }
        catch (Exception ex)
        {
            _monitor.Log($"Failed to start HTTP server: {ex.Message}", LogLevel.Error);
        }
    }

    public void Stop()
    {
        try
        {
            _cts?.Cancel();
            _listener.Stop();
        }
        catch (Exception ex)
        {
            _monitor.Log($"Error stopping HTTP server: {ex.Message}", LogLevel.Warn);
        }
    }

    private async Task ListenLoop(CancellationToken token)
    {
        while (!token.IsCancellationRequested && _listener.IsListening)
        {
            try
            {
                var context = await _listener.GetContextAsync();
                _ = Task.Run(() => HandleRequest(context));
            }
            catch (HttpListenerException) when (token.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                _monitor.Log($"HTTP listen loop exception: {ex.Message}", LogLevel.Trace);
            }
        }
    }

    private void HandleRequest(HttpListenerContext context)
    {
        try
        {
            var req = context.Request;
            var res = context.Response;

            res.Headers.Add("Access-Control-Allow-Origin", "*");
            res.Headers.Add("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
            res.Headers.Add("Access-Control-Allow-Headers", "Content-Type");

            if (req.HttpMethod == "OPTIONS")
            {
                res.StatusCode = 204;
                res.Close();
                return;
            }

            var path = req.Url?.AbsolutePath.ToLowerInvariant() ?? "";

            if (req.HttpMethod == "GET" && path == "/state")
            {
                byte[] data = Encoding.UTF8.GetBytes(CachedStateJson);
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "GET" && path == "/map")
            {
                byte[] data = Encoding.UTF8.GetBytes(CachedMapJson);
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "GET" && path == "/farm")
            {
                byte[] data = Encoding.UTF8.GetBytes(CachedFarmJson);
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "POST" && path == "/load")
            {
                string body = "";
                using (var reader = new StreamReader(req.InputStream, req.ContentEncoding))
                {
                    body = reader.ReadToEnd();
                }

                string saveName = "LauS_426336281";
                if (!string.IsNullOrWhiteSpace(body) && body.Contains("save"))
                {
                    saveName = body.Trim().Trim('"', '{', '}', ' ');
                    if (saveName.Contains(":"))
                    {
                        var parts = saveName.Split(':');
                        saveName = parts[1].Trim('"', ' ');
                    }
                }

                CommandQueue.Enqueue(() =>
                {
                    try
                    {
                        _monitor.Log($"Loading save file via HTTP command: {saveName}...", LogLevel.Info);
                        SaveGame.Load(saveName);
                    }
                    catch (Exception ex)
                    {
                        _monitor.Log($"Failed to load save: {ex.Message}", LogLevel.Error);
                    }
                });

                byte[] data = Encoding.UTF8.GetBytes($"{{\"accepted\":true,\"loading\":\"{saveName}\"}}");
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "POST" && path == "/run")
            {
                string body = "";
                using (var reader = new StreamReader(req.InputStream, req.ContentEncoding))
                {
                    body = reader.ReadToEnd();
                }

                var planReq = JsonSerializer.Deserialize<PlanRequest>(body, JsonOptions);
                if (planReq == null || planReq.Steps.Count == 0)
                {
                    byte[] err = Encoding.UTF8.GetBytes("{\"accepted\":false,\"error\":\"Invalid plan format or empty steps\"}");
                    res.StatusCode = 400;
                    res.OutputStream.Write(err, 0, err.Length);
                    res.Close();
                    return;
                }

                bool accepted = false;
                CommandQueue.Enqueue(() =>
                {
                    accepted = _planExecutor.AcceptPlan(planReq);
                });

                byte[] data = Encoding.UTF8.GetBytes("{\"accepted\":true}");
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "GET" && path == "/wait")
            {
                var query = req.Url?.Query ?? "";
                string targetId = "";
                int timeoutSec = 60;

                var queryParams = System.Web.HttpUtility.ParseQueryString(query);
                targetId = queryParams["id"] ?? "";
                if (int.TryParse(queryParams["timeout"], out int t))
                    timeoutSec = t;

                DateTime start = DateTime.UtcNow;
                while ((DateTime.UtcNow - start).TotalSeconds < timeoutSec)
                {
                    var status = _planExecutor.CurrentStatus;
                    if (status.Id == targetId && status.Status != "running")
                    {
                        // Plan finished/failed/interrupted
                        string json = JsonSerializer.Serialize(status, JsonOptions);
                        byte[] data = Encoding.UTF8.GetBytes(json);
                        res.ContentType = "application/json; charset=utf-8";
                        res.StatusCode = 200;
                        res.ContentLength64 = data.Length;
                        res.OutputStream.Write(data, 0, data.Length);
                        res.Close();
                        return;
                    }
                    Thread.Sleep(100);
                }

                // Timeout reached
                var timeoutRes = new PlanResult
                {
                    Id = targetId,
                    Status = "timeout",
                    Step = _planExecutor.CurrentStatus.Step,
                    StepsTotal = _planExecutor.CurrentStatus.StepsTotal,
                    Error = "TIMEOUT",
                    Detail = $"Plan timed out after {timeoutSec} seconds",
                    ElapsedS = timeoutSec
                };
                string timeoutJson = JsonSerializer.Serialize(timeoutRes, JsonOptions);
                byte[] timeoutData = Encoding.UTF8.GetBytes(timeoutJson);
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = timeoutData.Length;
                res.OutputStream.Write(timeoutData, 0, timeoutData.Length);
                res.Close();
                return;
            }

            if (req.HttpMethod == "POST" && path == "/cancel")
            {
                CommandQueue.Enqueue(() =>
                {
                    _planExecutor.CancelPlan();
                });
                byte[] data = Encoding.UTF8.GetBytes("{\"cancelled\":true}");
                res.ContentType = "application/json; charset=utf-8";
                res.StatusCode = 200;
                res.ContentLength64 = data.Length;
                res.OutputStream.Write(data, 0, data.Length);
                res.Close();
                return;
            }

            byte[] notFound = Encoding.UTF8.GetBytes("{\"error\":\"Endpoint not found or method not allowed\"}");
            res.ContentType = "application/json; charset=utf-8";
            res.StatusCode = 404;
            res.ContentLength64 = notFound.Length;
            res.OutputStream.Write(notFound, 0, notFound.Length);
            res.Close();
        }
        catch (Exception ex)
        {
            _monitor.Log($"Error handling HTTP request: {ex.Message}", LogLevel.Trace);
        }
    }
}
