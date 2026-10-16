"""Prepare a fresh workspace for an arm and grade it with the hidden tests."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "tasks"
ARMS = {"A": TASKS / "arm_a_greenfield", "B": TASKS / "arm_b_mature"}


def _fetch_pinned(manifest: dict, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    tgz = cache / Path(manifest["source"]).name
    if not tgz.exists():
        urllib.request.urlretrieve(manifest["source"], tgz)
    digest = hashlib.sha256(tgz.read_bytes()).hexdigest()
    if digest != manifest["sha256"]:
        raise RuntimeError(f"sha256 mismatch for {tgz.name}: {digest}")
    return tgz


def apply_patch(workspace: Path, patch: Path) -> None:
    """Apply a unified diff with -p1. Uses git apply, falls back to patch(1)."""
    for cmd in (["git", "apply", "-p1", str(patch)], ["patch", "-p1", "-i", str(patch)]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, cwd=workspace, check=True, capture_output=True)
            return
    raise RuntimeError("need git or patch to seed the bug")


def prepare(arm: str, workspace: Path, cache: Path | None = None) -> Path:
    workspace = Path(workspace)
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(f"{workspace} is not empty")
    workspace.mkdir(parents=True, exist_ok=True)
    src = ARMS[arm]
    if arm == "A":
        shutil.copy(src / "SPEC.md", workspace / "SPEC.md")
        return workspace
    manifest = json.loads((src / "manifest.json").read_text())
    tgz = _fetch_pinned(manifest, cache or ROOT / ".cache")
    with tarfile.open(tgz) as tf, tempfile.TemporaryDirectory() as tmp:
        tf.extractall(tmp, filter="data")
        top = Path(tmp) / f"{manifest['project']}-{manifest['version']}"
        for item in top.iterdir():
            (shutil.copytree if item.is_dir() else shutil.copy)(item, workspace / item.name)
    apply_patch(workspace, src / manifest["seed_patch"])
    shutil.copy(src / manifest["issue"], workspace / "ISSUE.md")
    return workspace


def grade(arm: str, workspace: Path) -> tuple[int, int]:
    """Run hidden tests (and, for Arm B, the project's own suite). Returns (passed, total)."""
    workspace = Path(workspace).resolve()
    targets = [str(p) for p in sorted((ARMS[arm] / "hidden_tests").glob("test_*.py"))]
    if arm == "B":
        targets.insert(0, str(workspace / "test_inflection.py"))
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "junit.xml"
        env = {**os.environ, "TWOARM_WORKSPACE": str(workspace), "PYTHONDONTWRITEBYTECODE": "1"}
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}",
                        "--rootdir", str(workspace), *targets], cwd=workspace, env=env, capture_output=True)
        if not xml.exists():
            return 0, 0
        root = ET.parse(xml).getroot()
        suites = [root] if root.tag == "testsuite" else list(root)
        total = sum(int(s.get("tests", 0)) for s in suites)
        bad = sum(int(s.get("failures", 0)) + int(s.get("errors", 0)) + int(s.get("skipped", 0)) for s in suites)
        return total - bad, total
