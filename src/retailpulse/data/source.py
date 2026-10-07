"""Inspect source files without inventing observations for missing inputs."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

FILES = {
    "calendar": "calendar.csv",
    "prices": "sell_prices.csv",
    "sales": "sales_train_evaluation.csv",
}
REQUIRED = {
    "calendar": ["date", "wm_yr_wk", "d"],
    "prices": ["store_id", "item_id", "wm_yr_wk", "sell_price"],
    "sales": ["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"],
}
DATASET_VERSION = "m5-accuracy-evaluation-v1"


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def day_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(
        (c for c in frame if re.fullmatch(r"d_[1-9][0-9]*", c)),
        key=lambda c: int(c[2:]),
    )


def schema_problems(name: str, frame: pd.DataFrame) -> list[str]:
    problems = []
    missing = set(REQUIRED[name]) - set(frame.columns)
    if missing:
        problems.append(f"Missing columns: {sorted(missing)}")
    if frame.empty:
        problems.append("Empty dataset")
    if name == "sales" and not day_columns(frame):
        problems.append("No d_1...d_n sales columns")
    for column in set(REQUIRED[name]) & set(frame):
        if frame[column].isna().any():
            problems.append(f"Null required field: {column}")
    return problems


def read_sources(directory: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for name, filename in FILES.items():
        path = directory / filename
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty required source: {filename}")
        # Categories limit memory for repeated identifiers in the full price file.
        header = pd.read_csv(path, nrows=0)
        categorical = {c: "category" for c in header if c.endswith("_id")}
        frame = pd.read_csv(path, dtype=categorical)
        problems = schema_problems(name, frame)
        if problems:
            raise ValueError(f"{filename}: {'; '.join(problems)}")
        frames[name] = frame
    return frames


def profile_frame(name: str, frame: pd.DataFrame) -> dict:
    result = {
        "rows": len(frame), "columns": len(frame.columns),
        "missing_values": {c: int(v) for c, v in frame.isna().sum().items()},
        "duplicate_rows": int(frame.duplicated().sum()),
        "cardinalities": {c: int(v) for c, v in frame.nunique().items()},
        "schema_problems": schema_problems(name, frame),
    }
    if name == "calendar" and "date" in frame:
        dates = pd.to_datetime(frame["date"], format="%Y-%m-%d", errors="coerce")
        result["date_range"] = {
            "min": str(dates.min()), "max": str(dates.max()),
            "invalid_dates": int(dates.isna().sum()),
        }
    if name == "sales":
        result["store_count"] = int(frame["store_id"].nunique())
        result["department_count"] = int(frame["dept_id"].nunique())
    return result


def price_coverage(frames: dict[str, pd.DataFrame]) -> dict:
    sales, calendar, prices = (frames[k] for k in ("sales", "calendar", "prices"))
    keys = ["store_id", "item_id", "wm_yr_wk"]
    if prices.duplicated(keys).any():
        raise ValueError("Duplicate weekly price keys")
    pairs = sales[["store_id", "item_id"]].drop_duplicates()
    weeks = calendar.loc[calendar["d"].isin(day_columns(sales)), "wm_yr_wk"].unique()
    matched = 0
    # One week at a time avoids constructing the full daily sales fact to profile.
    for week in weeks:
        available = prices.loc[(prices["wm_yr_wk"] == week) & prices["sell_price"].notna()]
        matched += len(pairs.merge(available[keys], on=keys[:2], how="inner"))
    expected = len(pairs) * len(weeks)
    return {"grain": "store_id × item_id × observed wm_yr_wk",
            "expected_keys": expected, "covered_keys": matched,
            "coverage_ratio": matched / expected if expected else None}


def select_pilot(sales: pd.DataFrame) -> dict[str, list[str]]:
    stores = sorted(sales["store_id"].unique())[:3]
    common = set(sales["dept_id"].unique())
    for store in stores:
        common &= set(sales.loc[sales["store_id"] == store, "dept_id"])
    departments = sorted(common)[:2]
    if len(stores) != 3 or len(departments) != 2:
        raise ValueError("Pilot requires 3 stores with 2 common departments")
    return {"stores": stores, "departments": departments}


def inspect_sources(directory: Path) -> dict:
    missing = [filename for filename in FILES.values() if not (directory / filename).is_file()]
    base = {"dataset_version": DATASET_VERSION, "generated_at": utc_now(),
            "source": "https://www.kaggle.com/competitions/m5-forecasting-accuracy/data"}
    if missing:
        return {**base, "status": "REAL-DATA VALIDATION PENDING",
                "missing_files": missing, "files": []}
    frames = read_sources(directory)
    entries = []
    for name, filename in FILES.items():
        path = directory / filename
        entries.append({"source_filename": filename, "sha256": checksum(path),
                        "size_bytes": path.stat().st_size,
                        **profile_frame(name, frames[name])})
    return {**base, "status": "INSPECTED", "files": entries,
            "price_coverage": price_coverage(frames), "pilot": select_pilot(frames["sales"])}


def write_json(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n", encoding="utf-8")
