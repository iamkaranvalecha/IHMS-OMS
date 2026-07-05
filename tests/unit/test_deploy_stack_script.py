"""Regression tests for the deploy stack helper."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "deploy-stack.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _run_stack(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"

    _write_executable(
        fake_bin / "docker",
        """#!/usr/bin/env bash
printf 'args:' >> "$DOCKER_LOG"
for arg in "$@"; do
  printf '<%s>' "$arg" >> "$DOCKER_LOG"
done
printf '\\n' >> "$DOCKER_LOG"
exit 0
""",
    )
    _write_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["DOCKER_LOG"] = str(docker_log)
    env["ECOPS_BEARER_TOKEN"] = "test-token"

    result = subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result, docker_log.read_text(encoding="utf-8") if docker_log.exists() else ""


def test_deploy_stack_uses_dev_compose(tmp_path: Path) -> None:
    result, docker_log = _run_stack(tmp_path, "up")

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Starting deploy stack" in result.stdout
    assert "<-f><docker/compose.dev.yml>" in docker_log


def test_deploy_stack_down_preserves_volumes_by_default(tmp_path: Path) -> None:
    result, docker_log = _run_stack(tmp_path, "down")

    assert result.returncode == 0, result.stderr + result.stdout
    assert "<down><--remove-orphans>" in docker_log
    assert "<-v>" not in docker_log


def test_deploy_stack_down_removes_volumes_only_when_requested(tmp_path: Path) -> None:
    result, docker_log = _run_stack(tmp_path, "down", "--volumes")

    assert result.returncode == 0, result.stderr + result.stdout
    assert "<down><--remove-orphans><-v>" in docker_log
