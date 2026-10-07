"""Small fail-fast data quality checks shared across stages."""
import pandas as pd


class QualityError(ValueError):
    """A data contract was violated; downstream results must not be published."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QualityError(message)


def unique(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    require(not frame[keys].isna().any().any(), f"{label}: null key")
    require(not frame.duplicated(keys).any(), f"{label}: duplicate key {keys}")


def numeric(series: pd.Series, label: str, *, positive=False, integral=False) -> pd.Series:
    result = pd.to_numeric(series, errors="coerce")
    finite = result.notna() & result.ne(float("inf")) & result.ne(float("-inf"))
    require(bool(finite.all()), f"{label}: null or non-finite numeric value")
    require(bool((result > 0).all() if positive else (result >= 0).all()),
            f"{label}: invalid negative or zero value")
    if integral:
        require(bool((result % 1 == 0).all()), f"{label}: non-integer value")
    return result
