"""Transform raw MID JSON into schema: series_id | settlement_datetime | published_at | published_at_source | value | source."""

from datetime import datetime, timedelta

# Empirically measured API publication lag; used for backfilled (estimated) rows.
MEASURED_MID_PUBLICATION_LAG = timedelta(minutes=5)  # TODO: replace with a measured value


def _settlement_period_end(start_time_str: str) -> datetime:
    start = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
    return start + timedelta(minutes=30)


def _volume_weighted_price(rows_for_period: list[dict]) -> tuple[float, float]:
    """Combine APXMIDP/N2EXMIDP by volume, since a zero-liquidity provider reports price=0."""
    total_value = sum(r["price"] * r["volume"] for r in rows_for_period)
    total_volume = sum(r["volume"] for r in rows_for_period)
    if total_volume == 0:
        return None, 0.0
    return total_value / total_volume, total_volume


def transform_mid_response(raw_json: dict, is_live_pull: bool, request_time: datetime = None) -> list[dict]:
    """
    is_live_pull=True: published_at = observed request time (live pipeline).
    is_live_pull=False: published_at = settlement period end + measured lag (backfill).
    """
    if is_live_pull and request_time is None:
        raise ValueError("Live pulls must pass request_time.")

    grouped: dict[tuple, list[dict]] = {}
    for row in raw_json.get("data", []):
        key = (row["settlementDate"], row["settlementPeriod"], row["startTime"])
        grouped.setdefault(key, []).append(row)

    output_rows = []
    for (settlement_date, settlement_period, start_time), rows in grouped.items():
        price, volume = _volume_weighted_price(rows)
        if price is None:
            continue

        period_end = _settlement_period_end(start_time)

        if is_live_pull:
            published_at = request_time
            published_at_source = "observed"
        else:
            published_at = period_end + MEASURED_MID_PUBLICATION_LAG
            published_at_source = "estimated"

        output_rows.append({
            "series_id": "gb_day_ahead_price",
            "settlement_datetime": start_time,
            "settlement_date": settlement_date,
            "settlement_period": settlement_period,
            "published_at": published_at.isoformat(),
            "published_at_source": published_at_source,
            "value": round(price, 2),
            "volume_mwh": round(volume, 2),
            "source": "elexon_mid",
        })

    return output_rows

def transform_disebsp_response(raw_json: dict) -> list[dict]:
    """
    Unlike MID, DISEBSP gives a real publish timestamp (createdDateTime), so
    published_at is always 'observed' here — no estimation needed, live or backfill.

    settlement_run_type is 'unknown': the API response has no field distinguishing
    initial vs. final settlement runs, so we flag that honestly rather than assume
    the value we got is final.
    """
    output_rows = []
    for row in raw_json.get("data", []):
        output_rows.append({
            "series_id": "gb_imbalance_price",
            "settlement_datetime": row["startTime"],
            "settlement_date": row["settlementDate"],
            "settlement_period": row["settlementPeriod"],
            "published_at": row["createdDateTime"],
            "published_at_source": "observed",
            "settlement_run_type": "unknown",
            "value": round(row["systemSellPrice"], 2),
            "volume_mwh": None,
            "source": "elexon_disebsp",
        })
    return output_rows