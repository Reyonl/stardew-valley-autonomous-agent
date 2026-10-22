import os
import subprocess
import time

def launch_smapi():
    dotnet_exe = r"C:\Users\ThinkPad\.dotnet\dotnet.exe"
    smapi_dll = r"D:\Download\Stardew.Valley.v1.6.15.kuyhAa\Stardew Valley\StardewModdingAPI.dll"
    cwd = r"D:\Download\Stardew.Valley.v1.6.15.kuyhAa\Stardew Valley"

    env = os.environ.copy()
    env["DOTNET_ROOT"] = r"C:\Users\ThinkPad\.dotnet"
    env["PATH"] = r"C:\Users\ThinkPad\.dotnet;" + env.get("PATH", "")

    si = subprocess.STARTUPINFO()
    si.lpDesktop = "WinSta0\\Default"

    # DETACHED_PROCESS = 0x00000008, CREATE_NEW_PROCESS_GROUP = 0x00000200
    flags = 0x00000008 | 0x00000200

    p = subprocess.Popen(
        [dotnet_exe, smapi_dll],
        cwd=cwd,
        env=env,
        startupinfo=si,
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True
    )
    print(f"Launched detached SMAPI on WinSta0\\Default with PID: {p.pid}")
    return p.pid

if __name__ == "__main__":
    launch_smapi()
