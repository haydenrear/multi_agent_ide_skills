#!/usr/bin/env python3
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent))

from _client import request_json
from _result import failure, success


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restart multi_agent_ide on port 8080, then wait for /actuator/health status UP"
    )
    parser.add_argument("--project-root", default=None,
                        help="Path to the cloned repo. Defaults to path stored in tmp_repo.txt.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--wait-seconds", type=int, default=180)
    parser.add_argument("--health-url", default="http://localhost:8080/actuator/health")
    parser.add_argument(
        "--profile",
        choices=["claudellama", "claude", "codex"],
        default="claude",
        help="Sets SPRING_PROFILES_ACTIVE for application startup.",
    )
    parser.add_argument("--pid-file")
    parser.add_argument("--log-file")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def runtime_dir() -> Path:
    d = Path("/private/tmp/multi_agent_ide_parent")
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_root(args: argparse.Namespace) -> Path:
    return Path(args.project_root)


def build_log(args: argparse.Namespace) -> Path:
    root_proj = project_root(args)
    build_log_file = (
        Path(args.log_file) if args.log_file else root_proj / "build-log.log"
    )
    return build_log_file


def log_file(args: argparse.Namespace) -> Path:
    root_proj = project_root(args)
    root_log_file = (
        Path(args.log_file) if args.log_file else root_proj / "multi-agent-ide.log"
    )
    return root_log_file


def runtime_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    default_dir = runtime_dir()
    pid_file = (
        Path(args.pid_file) if args.pid_file else default_dir / "multi_agent_ide.pid"
    )
    root_log_file = log_file(args)
    return pid_file, root_log_file


def tmp_repo_file() -> Path:
    return runtime_dir() / "tmp_repo.txt"


def save_tmp_repo(project_root: str) -> None:
    """Persist the project root path so subsequent runs can reuse it."""
    tmp_repo_file().write_text(project_root.strip(), encoding="utf-8")


def load_tmp_repo() -> str | None:
    """Read a previously saved tmp repo path, or None if not set."""
    f = tmp_repo_file()
    if f.exists():
        text = f.read_text(encoding="utf-8").strip()
        if text and Path(text).is_dir():
            return text
    return None


def pids_on_port(port: int) -> list[int]:
    result = subprocess.run(
        ["lsof", "-ti", f"tcp:{port}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        return []
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    pids: list[int] = []
    for line in lines:
        try:
            pids.append(int(line))
        except ValueError:
            continue
    return sorted(set(pids))


def terminate_port(port: int) -> dict:
    initial = pids_on_port(port)
    killed_term: list[int] = []
    killed_kill: list[int] = []
    if not initial:
        return {
            "initialPids": [],
            "terminated": [],
            "killed": [],
            "remaining": [],
        }

    for pid in initial:
        try:
            os.kill(pid, signal.SIGTERM)
            killed_term.append(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            continue

    deadline = time.time() + 12
    while time.time() < deadline:
        remaining = pids_on_port(port)
        if not remaining:
            return {
                "initialPids": initial,
                "terminated": killed_term,
                "killed": killed_kill,
                "remaining": [],
            }
        time.sleep(0.5)

    remaining = pids_on_port(port)
    for pid in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
            killed_kill.append(pid)
        except ProcessLookupError:
            continue
        except PermissionError:
            continue

    return {
        "initialPids": initial,
        "terminated": killed_term,
        "killed": killed_kill,
        "remaining": pids_on_port(port),
    }


def run_command(
    command: list[str],
    cwd: Path,
    log_file: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    if log_file is None:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode, output

    with log_file.open("ab") as handle:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=env,
        )
    return process.pid, "started"


def runtime_environment(profile: str) -> tuple[dict[str, str], dict[str, object]]:
    env = os.environ.copy()
    extra_path_dirs = ["/Users/hayde/.docker/bin", "/opt/homebrew/bin"]
    current_path = env.get("PATH", "")
    path_parts = [part for part in current_path.split(":") if part]
    for extra_dir in extra_path_dirs:
        if extra_dir not in path_parts:
            path_parts.insert(0, extra_dir)
    env["PATH"] = ":".join(path_parts)

    java_current = Path("/Users/hayde/.sdkman/candidates/java/current")
    java_home = env.get("JAVA_HOME")
    java_home_valid = bool(java_home and Path(java_home).exists())
    if (not java_home_valid) and java_current.exists():
        env["JAVA_HOME"] = str(java_current)

    # Default profile is claude; callers may override to claudellama or codex.
    env["SPRING_PROFILES_ACTIVE"] = profile

    meta = {
        "extraPathDirs": [
            d for d in extra_path_dirs if d in env.get("PATH", "").split(":")
        ],
        "javaHome": env.get("JAVA_HOME"),
        "javaHomeSource": "env"
        if java_home_valid
        else ("sdkman-current" if java_current.exists() else "unset"),
        "springProfilesActive": env.get("SPRING_PROFILES_ACTIVE"),
    }
    return env, meta


def resolve_jar_path(root: Path) -> Path | None:
    libs_dir = (
        root / "multi_agent_ide_java_parent" / "multi_agent_ide" / "build" / "libs"
    )
    if not libs_dir.exists():
        return None
    preferred = sorted(
        [
            path
            for path in libs_dir.glob("*.jar")
            if not path.name.endswith("-plain.jar")
        ],
        key=lambda path: path.stat().st_mtime,
    )
    if preferred:
        return preferred[-1]
    all_jars = sorted(libs_dir.glob("*.jar"), key=lambda path: path.stat().st_mtime)
    return all_jars[-1] if all_jars else None


def read_log_tail(log_file: Path, max_lines: int = 40) -> list[str]:
    if not log_file.exists():
        return []
    try:
        lines = log_file.read_text(errors="replace").splitlines()
    except Exception:
        return []
    return lines[-max_lines:]


def read_gradle_error_highlights(
    log_file: Path, max_lines: int = 200, max_matches: int = 80
) -> dict:
    if not log_file.exists():
        return {"logTail": [], "errorLines": []}
    try:
        lines = log_file.read_text(errors="replace").splitlines()
    except Exception:
        return {"logTail": [], "errorLines": []}

    pattern = re.compile(
        r"(FAILURE:|BUILD FAILED|ERROR|Exception|Caused by:|\* What went wrong:)"
    )
    matches = [line for line in lines if pattern.search(line)]
    return {"logTail": lines[-max_lines:], "errorLines": matches[-max_matches:]}


def check_health(health_url: str) -> tuple[bool, dict]:
    try:
        with urllib.request.urlopen(health_url, timeout=2) as response:
            raw = response.read().decode("utf-8")
            body = json.loads(raw) if raw else {}
            status = str(body.get("status", "")).upper()
            return status == "UP", {
                "httpStatus": response.status,
                "status": status,
                "body": body,
            }
    except urllib.error.HTTPError as error:
        return False, {
            "httpStatus": error.code,
            "status": "HTTP_ERROR",
            "body": str(error),
        }
    except urllib.error.URLError as error:
        return False, {
            "httpStatus": None,
            "status": "UNREACHABLE",
            "body": str(error.reason),
        }
    except json.JSONDecodeError as error:
        return False, {"httpStatus": 200, "status": "INVALID_JSON", "body": str(error)}


def stop_process(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            return


def ensure_ollama_serving() -> None:
    """Start ollama serve in the background if not already running.

    Ignores errors (e.g. if ollama is already serving or not installed).
    """
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def start_application(
    args: argparse.Namespace, root: Path, log_file: Path, env: dict[str, str]
) -> tuple[int, list[str]]:
    # Ensure ollama is serving before starting the application (needed for claudellama profile).
    ensure_ollama_serving()

    gradle_bootrun = [
        "./gradlew",
        ":multi_agent_ide_java_parent:multi_agent_ide:bootRun",
    ]
    execution_steps: list[str] = []

    pid, _ = run_command(gradle_bootrun, cwd=root, log_file=build_log(args), env=env)
    execution_steps.append(" ".join(gradle_bootrun))
    return pid, execution_steps


def wait_until_up(
    pid: int, health_url: str, wait_seconds: int, log_file: Path
) -> tuple[bool, dict]:
    deadline = time.time() + wait_seconds
    latest_health: dict = {"status": "UNKNOWN"}

    while time.time() < deadline:
        alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True

        if not alive:
            highlights = read_gradle_error_highlights(log_file)
            return False, {
                "reason": "process_exited",
                "health": latest_health,
                "logTail": highlights["logTail"],
                "errorLines": highlights["errorLines"],
            }

        ok, health = check_health(health_url)
        latest_health = health
        if ok:
            return True, {"health": health}
        time.sleep(1)

    highlights = read_gradle_error_highlights(log_file)
    return False, {
        "reason": "health_timeout",
        "health": latest_health,
        "logTail": highlights["logTail"],
        "errorLines": highlights["errorLines"],
    }


DEFAULT_FILTER_LAYERS = ["controller-ui-event-poll", "controller"]


def fetch_active_policies(
    base_url: str, layers: list[str] | None = None
) -> dict[str, dict]:
    """Fetch active filter policies for each layer. Non-fatal on failure."""
    result: dict[str, dict] = {}
    for layer in layers or DEFAULT_FILTER_LAYERS:
        resp = request_json(
            "POST",
            "/api/filters/layers/policies",
            payload={"layerId": layer, "status": "ACTIVE"},
            base_url=base_url,
            timeout=5,
        )
        if resp.get("ok"):
            result[layer] = resp.get("data") or {}
        else:
            result[layer] = {"error": resp.get("error", "unknown")}
    return result


def resolve_project_root(args: argparse.Namespace) -> Path:
    if args.project_root:
        return Path(args.project_root).resolve()
    saved = load_tmp_repo()
    if saved:
        return Path(saved).resolve()
    tmp_file = tmp_repo_file()
    if not tmp_file.exists():
        print(
            f"ERROR: {tmp_file} does not exist. "
            "Run clone_or_pull.py first to clone the repo and set tmp_repo.txt.",
            file=sys.stderr,
        )
    else:
        print(
            f"ERROR: {tmp_file} exists but points to a missing directory. "
            "Run clone_or_pull.py to re-clone the repo.",
            file=sys.stderr,
        )
    sys.exit(1)


def main() -> int:
    args = parse_args()
    root = resolve_project_root(args)
    args.project_root = str(root)  # ensure helpers that read args.project_root see the resolved path
    pid_file, root_log_file = runtime_paths(args)
    env, env_meta = runtime_environment(args.profile)

    if args.dry_run:
        payload = {
            "projectRoot": str(root),
            "port": args.port,
            "healthUrl": args.health_url,
            "waitSeconds": args.wait_seconds,
            "profile": args.profile,
            "pidFile": str(pid_file),
            "buildLogFile": str(build_log(args)),
            "logFile": str(root_log_file),
            "environment": env_meta,
            "commands": {
                "bootrun": "./gradlew :multi_agent_ide_java_parent:multi_agent_ide:bootRun",
                "bootjar": "./gradlew :multi_agent_ide_java_parent:multi_agent_ide:bootJar",
                "jar": "java -jar multi_agent_ide_java_parent/multi_agent_ide/build/libs/<artifact>.jar",
            },
        }
        return success(payload)

    port_cleanup = terminate_port(args.port)
    if port_cleanup.get("remaining"):
        return failure(
            {
                "message": f"Failed to clear port {args.port}",
                "portCleanup": port_cleanup,
            }
        )

    try:
        pid, steps = start_application(args, root, root_log_file, env)
    except Exception as error:
        return failure(
            {
                "message": str(error),
                "portCleanup": port_cleanup,
                "environment": env_meta,
            }
        )

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid), encoding="utf-8")

    ready, info = wait_until_up(pid, args.health_url, args.wait_seconds, root_log_file)
    if not ready:
        stop_process(pid)
        return failure(
            {
                "message": "Application failed health check",
                "pid": pid,
                "steps": steps,
                "portCleanup": port_cleanup,
                "details": info,
                "buildLogFile": str(build_log(args)),
                "logFile": str(root_log_file),
                "environment": env_meta,
            }
        )

    save_tmp_repo(str(root))

    active_policies = fetch_active_policies(f"http://localhost:{args.port}")

    return success(
        {
            "pid": pid,
            "pidFile": str(pid_file),
            "buildLogFile": str(build_log(args)),
            "logFile": str(root_log_file),
            "tmpRepoFile": str(tmp_repo_file()),
            "projectRoot": str(root),
            "steps": steps,
            "portCleanup": port_cleanup,
            "health": info["health"],
            "environment": env_meta,
            "activeFilterPolicies": active_policies,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
