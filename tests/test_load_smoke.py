from concurrent.futures import ThreadPoolExecutor

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from scripts.load_test import (
    build_attempt_payload,
    build_gap_report_payload,
    compute_percentile,
    summarize_stage,
)


def test_compute_percentile_and_summarize_stage() -> None:
    samples = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    assert compute_percentile(samples, 50) == 55.0
    assert compute_percentile(samples, 95) == 95.5
    assert compute_percentile(samples, 99) == 99.1

    summary = summarize_stage(
        endpoint="GET /api/learning-paths/{id}",
        concurrency=10,
        latencies_ms=samples,
        errors=0,
        elapsed_seconds=0.5,
    )
    assert summary.total_requests == 10
    assert summary.successful_requests == 10
    assert summary.failed_requests == 0
    assert summary.error_rate_pct == 0.0
    assert summary.rps == 20.0
    assert summary.p50_ms == 55.0
    assert summary.p95_ms == 95.5
    assert summary.p99_ms == 99.1


@pytest.mark.skip(
    reason=(
        "requiere una sesion de DB por request; el harness unitario comparte "
        "una unica sesion SQLite en memoria y no es thread-safe. La carga real "
        "se mide con scripts/load_test.py y k6_load_test.js"
    )
)
def test_critical_endpoints_smoke_load(client: TestClient) -> None:
    # 1. Create initial learning path
    seed_email = "smoke.load@example.com"
    create_res = client.post(
        "/api/learning-paths",
        json=build_gap_report_payload(seed_email),
    )
    assert create_res.status_code == status.HTTP_201_CREATED
    path_id = create_res.json()["id"]

    # 2. Concurrent GET /api/learning-paths/{id}
    with ThreadPoolExecutor(max_workers=5) as pool:
        get_statuses = list(
            pool.map(
                lambda _i: client.get(f"/api/learning-paths/{path_id}").status_code,
                range(10),
            )
        )
    assert all(code == status.HTTP_200_OK for code in get_statuses)

    # 3. Sequential & concurrent-ready POST /api/attempts verification
    for i in range(5):
        att_res = client.post(
            "/api/attempts",
            json=build_attempt_payload(
                learning_path_id=path_id,
                student_email=seed_email,
                is_correct=(i % 2 == 0),
            ),
        )
        assert att_res.status_code == status.HTTP_201_CREATED
