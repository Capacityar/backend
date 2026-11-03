"""
CapacityAR — Ejecutor de Pruebas de Carga ([S6.6][E1+E2])

Ejecuta pruebas de carga escalonadas (1, 5, 10 y 25 usuarios concurrentes)
sobre los tres endpoints críticos del backend con PLAN_GENERATOR=mock:
  1. POST /api/learning-paths
  2. GET  /api/learning-paths/{id}
  3. POST /api/attempts

Uso:
  # Levantar servidor aislado automáticamente (sin tocar capacity_ar_local.db):
  .venv\\Scripts\\python scripts/load_test.py --spawn-server

  # Contra un servidor ya levantado:
  .venv\\Scripts\\python scripts/load_test.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

import httpx


DEFAULT_CONCURRENCY_LEVELS = (1, 5, 10, 25)


@dataclass
class StageMetrics:
    endpoint: str
    concurrency: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate_pct: float
    elapsed_seconds: float
    rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    min_ms: float
    avg_ms: float


def compute_percentile(sorted_samples: list[float], percentile: float) -> float:
    """Compute percentile (0-100) from a sorted list of latency samples in ms."""
    if not sorted_samples:
        return 0.0
    if len(sorted_samples) == 1:
        return round(sorted_samples[0], 2)
    rank = (percentile / 100.0) * (len(sorted_samples) - 1)
    lower_idx = int(math.floor(rank))
    upper_idx = int(math.ceil(rank))
    if lower_idx == upper_idx:
        return round(sorted_samples[lower_idx], 2)
    weight = rank - lower_idx
    interpolated = (
        sorted_samples[lower_idx] * (1.0 - weight)
        + sorted_samples[upper_idx] * weight
    )
    return round(interpolated, 2)


def summarize_stage(
    endpoint: str,
    concurrency: int,
    latencies_ms: list[float],
    errors: int,
    elapsed_seconds: float,
) -> StageMetrics:
    total = len(latencies_ms) + errors
    successes = len(latencies_ms)
    sorted_lat = sorted(latencies_ms)
    error_rate = (errors / total * 100.0) if total > 0 else 0.0
    rps = (total / elapsed_seconds) if elapsed_seconds > 0 else 0.0
    avg_ms = (sum(sorted_lat) / len(sorted_lat)) if sorted_lat else 0.0

    return StageMetrics(
        endpoint=endpoint,
        concurrency=concurrency,
        total_requests=total,
        successful_requests=successes,
        failed_requests=errors,
        error_rate_pct=round(error_rate, 2),
        elapsed_seconds=round(elapsed_seconds, 3),
        rps=round(rps, 2),
        p50_ms=compute_percentile(sorted_lat, 50),
        p95_ms=compute_percentile(sorted_lat, 95),
        p99_ms=compute_percentile(sorted_lat, 99),
        max_ms=round(sorted_lat[-1], 2) if sorted_lat else 0.0,
        min_ms=round(sorted_lat[0], 2) if sorted_lat else 0.0,
        avg_ms=round(avg_ms, 2),
    )


def build_gap_report_payload(student_email: str = "ana.load@example.com") -> dict[str, Any]:
    return {
        "student": {
            "name": "Ana Perez",
            "email": student_email,
            "skills": [
                {"name": "Git", "level": 1},
                {"name": "SQL", "level": 2},
            ],
            "interests": ["backend", "logistica"],
        },
        "company": {"name": "Empresa Logistica SA"},
        "target_role": {
            "title": "Backend Developer Junior",
            "required_skills": [
                {"name": "Git", "level": 3, "priority": "HIGH"},
                {"name": "SQL", "level": 3, "priority": "HIGH"},
            ],
        },
        "summary": "Ana necesita reforzar Git y SQL.",
        "readiness_score": 45,
        "skills": [
            {
                "name": "Git",
                "current_level": 1,
                "required_level": 3,
                "gap_level": 2,
                "priority": "HIGH",
                "status": "MISSING",
            },
            {
                "name": "SQL",
                "current_level": 2,
                "required_level": 3,
                "gap_level": 1,
                "priority": "HIGH",
                "status": "NEEDS_WORK",
            },
        ],
    }


def build_attempt_payload(
    learning_path_id: int,
    student_email: str = "ana.load@example.com",
    is_correct: bool = True,
) -> dict[str, Any]:
    return {
        "student_email": student_email,
        "learning_path_id": learning_path_id,
        "module_index": 0,
        "unit_index": 2,
        "exercise_index": 0,
        "answer": "respuesta de ejemplo" if is_correct else "respuesta equivocada",
        "time_spent_seconds": 25,
    }


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        try:
            r = httpx.get(f"{base_url}/api/health", timeout=1.0)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.15)
    raise RuntimeError(f"Server at {base_url} did not become healthy within {timeout_seconds}s")


def run_stage(
    endpoint_label: str,
    concurrency: int,
    requests_per_vu: int,
    task_fn: Callable[[httpx.Client, int], bool],
    base_url: str,
) -> StageMetrics:
    total_tasks = concurrency * requests_per_vu
    latencies_ms: list[float] = []
    errors = 0

    limits = httpx.Limits(
        max_connections=max(concurrency * 2, 50),
        max_keepalive_connections=max(concurrency, 25),
    )

    with httpx.Client(base_url=base_url, timeout=30.0, limits=limits) as http_client:
        start_wall = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [
                pool.submit(_timed_call, task_fn, http_client, idx)
                for idx in range(total_tasks)
            ]
            for fut in as_completed(futures):
                ok, elapsed_ms = fut.result()
                if ok:
                    latencies_ms.append(elapsed_ms)
                else:
                    errors += 1
        elapsed_wall = time.perf_counter() - start_wall

    return summarize_stage(
        endpoint=endpoint_label,
        concurrency=concurrency,
        latencies_ms=latencies_ms,
        errors=errors,
        elapsed_seconds=elapsed_wall,
    )


def _timed_call(
    task_fn: Callable[[httpx.Client, int], bool],
    http_client: httpx.Client,
    idx: int,
) -> tuple[bool, float]:
    t0 = time.perf_counter()
    try:
        ok = task_fn(http_client, idx)
    except Exception:
        ok = False
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return ok, elapsed_ms


def execute_load_suite(
    base_url: str,
    concurrency_levels: tuple[int, ...] = DEFAULT_CONCURRENCY_LEVELS,
    requests_per_vu: int = 4,
) -> list[StageMetrics]:
    results: list[StageMetrics] = []

    # Warm-up & seed initial learning path for GET and POST /attempts benchmarks
    seed_email = "seed.load@example.com"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        seed_res = client.post(
            "/api/learning-paths",
            json=build_gap_report_payload(seed_email),
        )
        seed_res.raise_for_status()
        seed_path_id = seed_res.json()["id"]

    # 1. GET /api/learning-paths/{id}
    for vu in concurrency_levels:
        metrics = run_stage(
            endpoint_label="GET /api/learning-paths/{id}",
            concurrency=vu,
            requests_per_vu=requests_per_vu,
            task_fn=lambda c, _i: c.get(f"/api/learning-paths/{seed_path_id}").status_code == 200,
            base_url=base_url,
        )
        results.append(metrics)

    # 2. POST /api/learning-paths
    for vu in concurrency_levels:
        metrics = run_stage(
            endpoint_label="POST /api/learning-paths",
            concurrency=vu,
            requests_per_vu=requests_per_vu,
            task_fn=lambda c, i, v=vu: (
                c.post(
                    "/api/learning-paths",
                    json=build_gap_report_payload(f"lp_vu{v}_{i}@example.com"),
                ).status_code
                == 201
            ),
            base_url=base_url,
        )
        results.append(metrics)

    # 3. POST /api/attempts
    for vu in concurrency_levels:
        metrics = run_stage(
            endpoint_label="POST /api/attempts",
            concurrency=vu,
            requests_per_vu=requests_per_vu,
            task_fn=lambda c, i: (
                c.post(
                    "/api/attempts",
                    json=build_attempt_payload(
                        learning_path_id=seed_path_id,
                        student_email=seed_email,
                        is_correct=(i % 2 == 0),
                    ),
                ).status_code
                == 201
            ),
            base_url=base_url,
        )
        results.append(metrics)

    return results


def format_markdown_table(metrics_list: list[StageMetrics]) -> str:
    lines = [
        "| Endpoint | VUs | Total Req | Éxitos | % Error | RPS (req/s) | P50 (ms) | P95 (ms) | P99 (ms) | Máx (ms) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for m in metrics_list:
        lines.append(
            f"| `{m.endpoint}` | {m.concurrency} | {m.total_requests} | "
            f"{m.successful_requests} | {m.error_rate_pct:.1f}% | "
            f"**{m.rps:.2f}** | {m.p50_ms:.2f} | **{m.p95_ms:.2f}** | "
            f"{m.p99_ms:.2f} | {m.max_ms:.2f} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CapacityAR load tests on critical endpoints."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Target base URL when running against an existing server.",
    )
    parser.add_argument(
        "--spawn-server",
        action="store_true",
        help="Automatically spawn an isolated local uvicorn server with a temporary SQLite DB.",
    )
    parser.add_argument(
        "--requests-per-vu",
        type=int,
        default=4,
        help="Number of sequential requests executed per virtual user in each stage.",
    )
    parser.add_argument(
        "--json-out",
        type=str,
        default="",
        help="Optional file path to save raw JSON metrics.",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent
    server_proc: subprocess.Popen[Any] | None = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    base_url = args.base_url

    try:
        if args.spawn_server:
            temp_dir = tempfile.TemporaryDirectory(prefix="capacityar_load_")
            db_file = Path(temp_dir.name) / "load_test.db"
            port = _find_free_port()
            base_url = f"http://127.0.0.1:{port}"

            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
            env["PLAN_GENERATOR"] = "mock"
            env["LLM_TIMEOUT_SECONDS"] = "30.0"

            server_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--log-level",
                    "warning",
                ],
                cwd=str(backend_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _wait_for_server(base_url)

        results = execute_load_suite(
            base_url=base_url,
            concurrency_levels=DEFAULT_CONCURRENCY_LEVELS,
            requests_per_vu=args.requests_per_vu,
        )

        print("\n=== Resultados de Pruebas de Carga CapacityAR (PLAN_GENERATOR=mock) ===\n")
        print(format_markdown_table(results))
        print()

        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps([asdict(r) for r in results], indent=2),
                encoding="utf-8",
            )

        return 0
    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except Exception:
                server_proc.kill()
        if temp_dir is not None:
            try:
                temp_dir.cleanup()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
