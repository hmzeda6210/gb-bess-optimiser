"""Thin client for Elexon's BMRS Insights API (Market Index Data)."""

from datetime import datetime, timezone
import requests

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"


def fetch_mid(from_time: datetime, to_time: datetime) -> dict:
    """Fetch raw MID (day-ahead reference price) data for a UTC time window."""
    if from_time.tzinfo is None or to_time.tzinfo is None:
        raise ValueError("from_time/to_time must be timezone-aware UTC datetimes.")

    params = {
        "from": from_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": to_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "format": "json",
    }
    url = f"{BASE_URL}/balancing/pricing/market-index"

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def now_utc() -> datetime:
    """Current UTC time, centralised so it can be mocked in tests/backtests."""
    return datetime.now(timezone.utc)

def fetch_disebsp(settlement_date: str) -> dict:
    """Fetch imbalance/system prices for a single settlement date (YYYY-MM-DD)."""
    url = f"{BASE_URL}/balancing/settlement/system-prices/{settlement_date}"
    
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()