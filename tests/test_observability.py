import pytest
from httpx import AsyncClient


# Liveness + readiness probes
@pytest.mark.asyncio
async def test_health_live(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_reports_shape(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    # DB may be absent in CI — degraded is acceptable, but shape must be present
    assert "status" in data
    assert "db" in data
    assert "pool" in data


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.headers.get("x-request-id") is not None


@pytest.mark.asyncio
async def test_request_id_echoed_when_provided(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "test-123"})
    assert response.headers.get("x-request-id") == "test-123"
