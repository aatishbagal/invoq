from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import psutil


class GPUType(Enum):
    NONE = "none"
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL_INTEGRATED = "intel_integrated"
    INTEL_ARC = "intel_arc"
    APPLE_SILICON = "apple_silicon"


@dataclass
class GPUInfo:
    gpu_type: GPUType
    name: str
    vram_mb: Optional[int]
    is_integrated: bool
    driver_version: Optional[str]
    cuda_available: bool
    rocm_available: bool


@dataclass
class SystemSpecs:
    # RAM
    total_ram_mb: int

    # CPU
    cpu_name: str
    cpu_cores: int
    cpu_threads: int

    # GPU
    gpus: List[GPUInfo] = field(default_factory=list)
    primary_gpu: Optional[GPUInfo] = None

    # Disk
    ollama_dir_free_mb: int = 0

    # OS
    os_name: str = "Unknown"
    os_version: str = "Unknown"
    kernel_version: str = "Unknown"

    @property
    def ram_tier(self) -> str:
        if self.total_ram_mb >= 16000:
            return "high"
        if self.total_ram_mb >= 8000:
            return "medium"
        if self.total_ram_mb >= 4000:
            return "low"
        return "very_low"


def detect_total_ram() -> int:
    """Get total physical RAM in MB. Never checks available/free."""
    return psutil.virtual_memory().total // (1024 * 1024)


def detect_cpu() -> tuple[str, int, int]:
    name = "Unknown"
    try:
        cpuinfo_path = Path("/proc/cpuinfo")
        if cpuinfo_path.exists():
            text = cpuinfo_path.read_text(encoding="utf-8")
            match = re.search(r"model name\s*:\s*(.+)", text)
            if match:
                name = match.group(1).strip()
    except OSError:
        pass

    if name == "Unknown":
        name = platform.processor() or "Unknown"

    cores = psutil.cpu_count(logical=False) or 1
    threads = psutil.cpu_count(logical=True) or 1
    return name, cores, threads


def detect_nvidia_gpu() -> Optional[GPUInfo]:
    if not shutil.which("nvidia-smi"):
        return None

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None

        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            return None

        gpu_name = parts[0]
        vram_mb = int(float(parts[1]))
        driver_version = parts[2]

        cuda_available = bool(
            shutil.which("nvcc") or Path("/usr/local/cuda").exists()
        )

        return GPUInfo(
            gpu_type=GPUType.NVIDIA,
            name=gpu_name,
            vram_mb=vram_mb,
            is_integrated=False,
            driver_version=driver_version,
            cuda_available=cuda_available,
            rocm_available=False,
        )
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return None


def detect_amd_gpu() -> Optional[GPUInfo]:
    # Check via sysfs
    drm_path = Path("/sys/class/drm")
    if not drm_path.exists():
        return None

    amd_found = False
    gpu_name = "AMD GPU"
    for card_dir in sorted(drm_path.glob("card[0-9]*")):
        vendor_path = card_dir / "device" / "vendor"
        if vendor_path.exists():
            try:
                vendor_id = vendor_path.read_text().strip()
                if vendor_id == "0x1002":
                    amd_found = True
                    # Try to get name from uevent
                    uevent_path = card_dir / "device" / "uevent"
                    if uevent_path.exists():
                        uevent = uevent_path.read_text()
                        match = re.search(r"PCI_SLOT_NAME=(.+)", uevent)
                        if match:
                            gpu_name = f"AMD GPU ({match.group(1).strip()})"
                    break
            except OSError:
                continue

    if not amd_found:
        return None

    vram_mb = None
    is_integrated = False
    rocm_available = Path("/opt/rocm").exists()

    # Try rocm-smi for details
    if shutil.which("rocm-smi"):
        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                match = re.search(r"Total\s+.*?:\s*(\d+)", result.stdout)
                if match:
                    vram_mb = int(match.group(1)) // (1024 * 1024)
        except (subprocess.TimeoutExpired, OSError):
            pass

    # Check if integrated (APU)
    try:
        result = subprocess.run(
            ["lspci"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "1002" in line or "AMD" in line.upper():
                    if "Radeon Graphics" in line and "VGA" in line:
                        is_integrated = True
                        gpu_name = "AMD Radeon Graphics (Integrated)"
                    elif "AMD" in line and ("Radeon RX" in line or "Radeon PRO" in line):
                        # Extract name
                        match = re.search(r"(Radeon\s+\S+\s*\S*)", line)
                        if match:
                            gpu_name = f"AMD {match.group(1).strip()}"
    except (subprocess.TimeoutExpired, OSError):
        pass

    return GPUInfo(
        gpu_type=GPUType.AMD,
        name=gpu_name,
        vram_mb=vram_mb,
        is_integrated=is_integrated,
        driver_version=None,
        cuda_available=False,
        rocm_available=rocm_available,
    )


def detect_intel_gpu() -> Optional[GPUInfo]:
    drm_path = Path("/sys/class/drm")
    if not drm_path.exists():
        return None

    for card_dir in sorted(drm_path.glob("card[0-9]*")):
        vendor_path = card_dir / "device" / "vendor"
        if not vendor_path.exists():
            continue

        try:
            vendor_id = vendor_path.read_text().strip()
            if vendor_id != "0x8086":
                continue

            device_path = card_dir / "device" / "device"
            device_id = ""
            if device_path.exists():
                device_id = device_path.read_text().strip()

            # Intel Arc discrete GPUs: 0x56xx range
            is_arc = device_id.startswith("0x56")
            gpu_type = GPUType.INTEL_ARC if is_arc else GPUType.INTEL_INTEGRATED
            name = "Intel Arc GPU" if is_arc else "Intel Integrated Graphics"

            return GPUInfo(
                gpu_type=gpu_type,
                name=name,
                vram_mb=None,
                is_integrated=not is_arc,
                driver_version=None,
                cuda_available=False,
                rocm_available=False,
            )
        except OSError:
            continue

    return None


def detect_gpus() -> List[GPUInfo]:
    gpus: List[GPUInfo] = []
    for detect_fn in (detect_nvidia_gpu, detect_amd_gpu, detect_intel_gpu):
        gpu = detect_fn()
        if gpu is not None:
            gpus.append(gpu)
    return gpus


def select_primary_gpu(gpus: List[GPUInfo]) -> Optional[GPUInfo]:
    if not gpus:
        return None

    # Priority: NVIDIA+CUDA > AMD+ROCm > Intel Arc > discrete > integrated
    def priority(gpu: GPUInfo) -> int:
        if gpu.gpu_type == GPUType.NVIDIA and gpu.cuda_available:
            return 0
        if gpu.gpu_type == GPUType.AMD and gpu.rocm_available:
            return 1
        if gpu.gpu_type == GPUType.INTEL_ARC:
            return 2
        if not gpu.is_integrated:
            return 3
        return 4

    return min(gpus, key=priority)


def detect_ollama_disk_space() -> int:
    models_dir = os.environ.get("OLLAMA_MODELS", str(Path.home() / ".ollama"))
    path = Path(models_dir)

    # Walk up to an existing parent
    while not path.exists() and path.parent != path:
        path = path.parent

    try:
        usage = psutil.disk_usage(str(path))
        return int(usage.free / (1024 * 1024))
    except OSError:
        return 0


def detect_os() -> tuple[str, str, str]:
    os_name = "Unknown"
    os_version = "Unknown"

    try:
        os_release = Path("/etc/os-release")
        if os_release.exists():
            text = os_release.read_text(encoding="utf-8")
            name_match = re.search(r'^NAME="?([^"\n]+)"?', text, re.MULTILINE)
            ver_match = re.search(r'^VERSION="?([^"\n]+)"?', text, re.MULTILINE)
            if name_match:
                os_name = name_match.group(1).strip()
            if ver_match:
                os_version = ver_match.group(1).strip()
    except OSError:
        pass

    if os_name == "Unknown":
        os_name = platform.system()

    kernel_version = platform.release()
    return os_name, os_version, kernel_version


def get_system_specs() -> SystemSpecs:
    total_ram = detect_total_ram()
    cpu_name, cpu_cores, cpu_threads = detect_cpu()
    gpus = detect_gpus()
    primary_gpu = select_primary_gpu(gpus)
    disk_free = detect_ollama_disk_space()
    os_name, os_version, kernel_version = detect_os()

    return SystemSpecs(
        total_ram_mb=total_ram,
        cpu_name=cpu_name,
        cpu_cores=cpu_cores,
        cpu_threads=cpu_threads,
        gpus=gpus,
        primary_gpu=primary_gpu,
        ollama_dir_free_mb=disk_free,
        os_name=os_name,
        os_version=os_version,
        kernel_version=kernel_version,
    )
