"""What this machine is: OS, RAM, NVIDIA GPUs, and the first tier it satisfies."""

import ctypes
import json
import platform
import shutil
import subprocess
from pathlib import Path

from .catalog import current_os, default_roots


def ram_mb() -> int:
    if current_os() == "windows":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return status.ullTotalPhys // (1024 * 1024)
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            return int(line.split()[1]) // 1024
    return 0


def gpus() -> list[dict]:
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    proc = subprocess.run(
        [smi, "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return []
    found = []
    for line in proc.stdout.strip().splitlines():
        name, vram, sm = (part.strip() for part in line.split(","))
        found.append({"name": name, "vram_mb": int(float(vram)), "sm": sm})
    return found


def load_tiers(roots: list[Path] | None = None) -> list[dict]:
    """Tiers from the last root that has inference/tiers.json (the private fleet repo)."""
    tiers: list[dict] = []
    for root in roots or default_roots():
        path = root / "inference" / "tiers.json"
        if path.is_file():
            tiers = json.loads(path.read_text(encoding="utf-8"))["tiers"]
    return tiers


def match_tier(tiers: list[dict], vram_mb: int, ram: int) -> str | None:
    """First tier, best-first, whose floors the machine meets. Tiers describe; they never route."""
    for tier in tiers:
        needs = tier.get("requires", {})
        if vram_mb >= needs.get("vram_mb", 0) and ram >= needs.get("ram_mb", 0):
            return tier["id"]
    return None


def probe() -> dict:
    found = gpus()
    ram = ram_mb()
    # Total across cards: llama.cpp splits one model over every GPU in the box.
    vram = sum(g["vram_mb"] for g in found)
    return {
        "os": current_os(),
        "os_version": platform.platform(),
        "ram_mb": ram,
        "gpus": found,
        "vram_mb": vram,
        "tier": match_tier(load_tiers(), vram, ram) if found else None,
    }
