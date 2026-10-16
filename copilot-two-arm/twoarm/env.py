import os, platform, subprocess, sys


def hardware() -> str:
    cpu = platform.processor() or platform.machine()
    try:
        for line in open("/proc/cpuinfo"):
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError:
        pass
    mem = ""
    try:
        kb = int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal")).split()[1])
        mem = f", {kb / 1024 / 1024:.0f} GiB RAM"
    except (OSError, StopIteration):
        pass
    return f"{cpu}, {os.cpu_count()} vCPU{mem}, {platform.system()} {platform.release()}"


def python_version() -> str:
    return sys.version.split()[0]
