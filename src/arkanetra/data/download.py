from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

USER_AGENT = "ArkaNetra/1.0.0"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0


def fetch_json(url: str, timeout_seconds: int = 30) -> list | dict:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 404:
                break
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error if last_error else RuntimeError(f"Fetch failed for {url}")


def fetch_binary(url: str, timeout_seconds: int = 60) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 404:
                break
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error if last_error else RuntimeError(f"Fetch failed for {url}")


def save_csv(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def download_list(
    urls: list[str],
    save_dir: Path,
    parse_func: callable,
    timeout_seconds: int = 60,
) -> list[Path]:
    paths = []
    for url in urls:
        try:
            data = fetch_binary(url, timeout_seconds=timeout_seconds)
            filename = url.rstrip("/").split("/")[-1] or "download"
            filepath = save_dir / filename
            filepath.write_bytes(data)
            paths.append(filepath)
        except Exception:
            continue
    return paths