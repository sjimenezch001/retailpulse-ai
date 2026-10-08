"""Own both child processes; bind locally and reap them on every exit path."""

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil


def free_port(port):
    if not 1024 <= port <= 65535:
        raise ValueError("Choose a port between 1024 and 65535.")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


def stop_children(children):
    owned = []
    for child in children:
        if child.poll() is None:
            try:
                process = psutil.Process(child.pid)
                owned.extend(process.children(recursive=True))
                owned.append(process)
            except psutil.NoSuchProcess:
                pass
    for process in reversed(owned):
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(owned, timeout=4)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    for child in children:
        try:
            child.wait(timeout=4)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=4)


def launch(
    settings, root, *, mode="real", provider="ollama", api_port=8000, ui_port=8501
):
    children, logs = [], []
    if api_port == ui_port:
        raise ValueError("API and UI ports must differ.")
    for port in (api_port, ui_port):
        free_port(port)
    env = dict(os.environ)
    env.update(
        {
            "RETAILPULSE_ROOT": str(root),
            "RETAILPULSE_DATABASE": str(
                settings.output_path / "gold/retailpulse.duckdb"
            ),
            "RETAILPULSE_DEMO_MODE": mode,
            "RETAILPULSE_PROVIDER": provider,
            "RETAILPULSE_UI_PORT": str(ui_port),
            "RETAILPULSE_API_URL": f"http://127.0.0.1:{api_port}",
            "PYTHONUNBUFFERED": "1",
        }
    )
    directory = root / "artifacts/web_demo" / mode
    directory.mkdir(parents=True, exist_ok=True)
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "retailpulse.api.app:from_environment",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
            "--no-access-log",
        ],
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(root / "app/streamlit_app.py"),
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(ui_port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.fileWatcherType",
            "none",
        ],
    ]

    def interrupted(*args):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, interrupted)
    try:
        for name, command in zip(("api", "streamlit"), commands, strict=True):
            log = (directory / f"{name}.log").open("a", encoding="utf-8")
            logs.append(log)
            children.append(
                subprocess.Popen(
                    command,
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            )
        started = time.monotonic()
        urls = [
            f"http://127.0.0.1:{api_port}/health",
            f"http://127.0.0.1:{ui_port}/_stcore/health",
        ]
        with httpx.Client(timeout=3, trust_env=False) as client:
            while time.monotonic() - started < 45:
                if any(child.poll() is not None for child in children):
                    raise RuntimeError(
                        "A demo server exited during startup. Inspect the ignored local web_demo logs."
                    )
                try:
                    responses = [client.get(url) for url in urls]
                    if all(r.status_code == 200 for r in responses):
                        health = responses[0].json()
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError(
                    "Demo startup timed out. Inspect the ignored local web_demo logs."
                )
        print(f"RetailPulse AI | {mode} mode | {provider} assistant", flush=True)
        print(
            f"App: http://127.0.0.1:{ui_port}\nAPI: http://127.0.0.1:{api_port}\nDocs: http://127.0.0.1:{api_port}/docs",
            flush=True,
        )
        if not health["dataset_available"]:
            print(health["message"], flush=True)
        print("Ready. Press Ctrl+C to stop both servers.", flush=True)
        while all(child.poll() is None for child in children):
            time.sleep(0.3)
        raise RuntimeError("A demo server stopped unexpectedly.")
    except KeyboardInterrupt:
        print("Stopping RetailPulse demo servers.", flush=True)
        return 0
    finally:
        stop_children(children)
        for log in logs:
            log.close()
        signal.signal(signal.SIGTERM, previous)


def run(args, settings, root):
    try:
        return launch(
            settings,
            Path(root),
            mode=args.mode,
            provider=args.provider,
            api_port=args.api_port,
            ui_port=args.ui_port,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Demo could not start: {exc}", file=sys.stderr)
        return 1
