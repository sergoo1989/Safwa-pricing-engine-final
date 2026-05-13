from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd


AUDIT_COLUMNS = [
    "event_time",
    "event_type",
    "scope",
    "sku",
    "item_name",
    "item_type",
    "channel",
    "cogs",
    "list_price",
    "net_price",
    "discount_rate",
    "margin_pct",
    "profit",
    "breakeven_price",
    "status",
    "details_json",
]


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _normalise_record(record: Dict[str, Any]) -> Dict[str, Any]:
    margin_pct = _safe_float(record.get("margin_pct", record.get("هامش الربح %", 0)))
    if margin_pct and abs(margin_pct) <= 1:
        margin_pct *= 100

    return {
        "event_time": record.get("event_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": record.get("event_type", "pricing_saved"),
        "scope": record.get("scope", "single"),
        "sku": record.get("sku") or record.get("SKU", ""),
        "item_name": record.get("item_name") or record.get("اسم المنتج/البكج", ""),
        "item_type": record.get("item_type") or record.get("النوع", ""),
        "channel": record.get("channel") or record.get("المنصة", ""),
        "cogs": _safe_float(record.get("cogs", record.get("التكلفة", 0))),
        "list_price": _safe_float(record.get("list_price", record.get("سعر القائمة", 0))),
        "net_price": _safe_float(record.get("net_price", record.get("صافي السعر", 0))),
        "discount_rate": _safe_float(record.get("discount_rate", record.get("نسبة الخصم", 0))),
        "margin_pct": margin_pct,
        "profit": _safe_float(record.get("profit", record.get("الربح", 0))),
        "breakeven_price": _safe_float(record.get("breakeven_price", record.get("نقطة التعادل", 0))),
        "status": record.get("status", "saved"),
        "details_json": json.dumps(record.get("details", {}), ensure_ascii=False, default=str),
    }


def append_audit_event(data_dir: str | Path, record: Dict[str, Any]) -> Path:
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    audit_path = data_path / "pricing_audit_log.csv"

    audit_record = _normalise_record(record)

    if audit_path.exists():
        audit_df = pd.read_csv(audit_path, encoding="utf-8-sig")
        audit_df = pd.concat([audit_df, pd.DataFrame([audit_record])], ignore_index=True)
    else:
        audit_df = pd.DataFrame([audit_record], columns=AUDIT_COLUMNS)

    for column in AUDIT_COLUMNS:
        if column not in audit_df.columns:
            audit_df[column] = ""

    audit_df[AUDIT_COLUMNS].to_csv(audit_path, index=False, encoding="utf-8-sig")
    return audit_path


def append_audit_events(data_dir: str | Path, records: Iterable[Dict[str, Any]]) -> Path:
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    audit_path = data_path / "pricing_audit_log.csv"

    new_records = [_normalise_record(record) for record in records]
    if not new_records:
        return audit_path

    if audit_path.exists():
        audit_df = pd.read_csv(audit_path, encoding="utf-8-sig")
        audit_df = pd.concat([audit_df, pd.DataFrame(new_records)], ignore_index=True)
    else:
        audit_df = pd.DataFrame(new_records, columns=AUDIT_COLUMNS)

    for column in AUDIT_COLUMNS:
        if column not in audit_df.columns:
            audit_df[column] = ""

    audit_df[AUDIT_COLUMNS].to_csv(audit_path, index=False, encoding="utf-8-sig")
    return audit_path
