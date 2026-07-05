"""Regression tests for the E2E stack wrapper."""

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "e2e-stack.sh"
ENV_FILE = ROOT / ".env"


@pytest.fixture
def repo_env_file() -> Iterator[Path]:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else None
    try:
        yield ENV_FILE
    finally:
        if original is None:
            ENV_FILE.unlink(missing_ok=True)
        else:
            ENV_FILE.write_text(original, encoding="utf-8")


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_e2e_stack_forces_mock_compose_env_over_real_upstream_dotenv(
    tmp_path: Path,
    repo_env_file: Path,
) -> None:
    repo_env_file.write_text(
        "\n".join(
            [
                "IHMS_BASE_URL=http://host.docker.internal:5000",
                "ECOPS_BASE_URL=http://host.docker.internal:8002",
                "ECOPS_BEARER_TOKEN=real-token",
                "UI_PORT=5180",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    _write_executable(
        fake_bin / "docker",
        """#!/usr/bin/env bash
{
  printf 'args:'
  for arg in "$@"; do
    printf '<%s>' "$arg"
  done
  printf '\\n'
  printf 'IHMS_BASE_URL=%s\\n' "$IHMS_BASE_URL"
  printf 'ECOPS_BASE_URL=%s\\n' "$ECOPS_BASE_URL"
  printf 'ECOPS_BEARER_TOKEN=%s\\n' "$ECOPS_BEARER_TOKEN"
  printf 'ORCHESTRATOR_PORT=%s\\n' "$ORCHESTRATOR_PORT"
  printf 'IHMS_PORT=%s\\n' "$IHMS_PORT"
  printf 'ECOPS_PORT=%s\\n' "$ECOPS_PORT"
  printf 'UI_PORT=%s\\n' "$UI_PORT"
  printf 'CATALOG_SOURCE=%s\\n' "$CATALOG_SOURCE"
} >> "$DOCKER_LOG"
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
    for key in (
        "IHMS_BASE_URL",
        "ECOPS_BASE_URL",
        "ECOPS_BEARER_TOKEN",
        "ORCHESTRATOR_PORT",
        "IHMS_PORT",
        "ECOPS_PORT",
        "UI_PORT",
    ):
        env.pop(key, None)

    result = subprocess.run(
        ["bash", str(SCRIPT), "up"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    log = docker_log.read_text(encoding="utf-8")
    assert "args:<compose><up><-d><--build><--wait>" in log
    assert "IHMS_BASE_URL=http://ihms:8080" in log
    assert "ECOPS_BASE_URL=http://ecops:8002" in log
    assert "ECOPS_BEARER_TOKEN=\n" in log
    assert "ORCHESTRATOR_PORT=8000" in log
    assert "IHMS_PORT=8080" in log
    assert "ECOPS_PORT=8012" in log
    assert "UI_PORT=5180" in log
    assert "CATALOG_SOURCE=ihms" in log
    assert "host.docker.internal" not in log
