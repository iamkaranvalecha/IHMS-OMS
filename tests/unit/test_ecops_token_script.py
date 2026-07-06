"""Regression tests for the EC-OPS token helper."""

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ecops-token.sh"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


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


def _run_token_helper(
    tmp_path: Path,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl_log = tmp_path / "curl.log"

    _write_executable(
        fake_bin / "curl",
        """#!/usr/bin/env bash
printf 'args:' >> "$CURL_LOG"
for arg in "$@"; do
  printf '<%s>' "$arg" >> "$CURL_LOG"
done
printf '\\n' >> "$CURL_LOG"
printf '{"access_token":"test-token"}'
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["CURL_LOG"] = str(curl_log)
    env.update(extra_env or {})

    result = subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return result, curl_log.read_text(encoding="utf-8") if curl_log.exists() else ""


def test_env_example_configures_real_upstream_compose_path() -> None:
    """The documented real-upstream flow copies this file directly to .env."""
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()

    assert "IHMS_BASE_URL=http://host.docker.internal:5000" in lines
    assert "ECOPS_BASE_URL=http://host.docker.internal:8002" in lines
    assert "CATALOG_SOURCE=ihms" in lines
    assert "ECOPS_BEARER_TOKEN=" in lines
    assert "UI_PORT=5180" in lines


def test_ecops_token_uses_localhost_for_host_docker_internal_env(
    tmp_path: Path,
    repo_env_file: Path,
) -> None:
    repo_env_file.write_text(
        "\n".join(
            [
                "ECOPS_BASE_URL=http://host.docker.internal:8002",
                "ECOPS_BEARER_TOKEN=",
                "ECOPS_USERNAME=admin",
                "ECOPS_PASSWORD=secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result, curl_log = _run_token_helper(tmp_path)

    assert result.returncode == 0, result.stderr + result.stdout
    assert "<http://localhost:8002/auth/token>" in curl_log
    assert "ECOPS_BEARER_TOKEN=test-token" in repo_env_file.read_text(encoding="utf-8")


def test_ecops_token_url_override_is_used_for_host_fetch(
    tmp_path: Path,
    repo_env_file: Path,
) -> None:
    repo_env_file.write_text(
        "\n".join(
            [
                "ECOPS_BASE_URL=http://host.docker.internal:8002",
                "ECOPS_USERNAME=admin",
                "ECOPS_PASSWORD=secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result, curl_log = _run_token_helper(
        tmp_path,
        "--print",
        extra_env={"ECOPS_TOKEN_URL": "http://ecops.local:9000"},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "<http://ecops.local:9000/auth/token>" in curl_log
    assert result.stdout.strip() == "test-token"
