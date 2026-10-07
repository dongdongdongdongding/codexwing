#!/usr/bin/env python3
"""Install a short poller and three independent session workers on this Mac."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess

ROLES = ("kr_scan", "us_scan", "daily_ops")


def worker_plist(role, home):
    support = home / "Library/Application Support/CodexSwing"
    label = "com.codex.swing.primary-worker-" + role.replace("_", "-")
    return {
        "Label": label,
        "ProgramArguments": [str(support / "bin/codex_swing_launch.sh"), "/usr/bin/python3",
                             "multi_agent/tools/primary_session_dispatch.py", "--worker", role],
        "WorkingDirectory": str(support), "StartInterval": 60, "RunAtLoad": True,
        "StandardOutPath": str(support / "logs/ops" / (label + ".log")),
        "StandardErrorPath": str(support / "logs/ops" / (label + ".err.log")),
        "EnvironmentVariables": {"TZ": "Asia/Seoul", "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
    }


def poller_plist(home):
    data = worker_plist("dispatch", home)
    data["Label"] = "com.codex.swing.primary-dispatch"
    data["ProgramArguments"][-3:] = ["multi_agent/tools/run_primary_market_session_ops.py", "--run-due"]
    for key in ("StandardOutPath", "StandardErrorPath"):
        data[key] = data[key].replace("primary-worker-dispatch", "primary-dispatch")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    home = Path.home()
    plists = [worker_plist(role, home) for role in ROLES] + [poller_plist(home)]
    if not args.install:
        print(json.dumps(plists, indent=2))
        return
    domain = f"gui/{os.getuid()}"
    for data in plists:
        path = home / "Library/LaunchAgents" / (data["Label"] + ".plist")
        raw = plistlib.dumps(data)
        loaded = subprocess.run(["launchctl", "print", domain + "/" + data["Label"]],
                                capture_output=True).returncode == 0
        if loaded:
            if not path.exists() or plistlib.loads(path.read_bytes()) != data:
                raise RuntimeError("loaded worker configuration differs; preserve running job")
            print(data["Label"] + " already installed")
            continue
        if path.exists() and plistlib.loads(path.read_bytes()) != data:
            raise RuntimeError("existing worker plist differs; preserve configuration")
        path.parent.mkdir(parents=True, exist_ok=True)
        Path(data["StandardOutPath"]).parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        subprocess.run(["plutil", "-lint", str(path)], check=True)
        subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
        print(data["Label"] + " installed")


if __name__ == "__main__":
    main()
