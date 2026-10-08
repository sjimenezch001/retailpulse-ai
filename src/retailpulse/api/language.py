"""Closed Spanish surface forms; the unchanged RP-09 router validates the result.

Full-string matching prevents dropping extra conditions. No model translation,
free-form rewriting, SQL generation or additional tools are involved.
"""

import calendar
import re
import unicodedata

MONTHS = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
FIXED = {
    "cual fue el wmape de lightgbm en el conjunto de prueba": "Show LightGBM WMAPE on the test period",
    "compara lightgbm y la media movil en el conjunto de prueba": "Compare LightGBM and rolling mean WMAPE on the test period",
    "que significa revenue_proxy": "What does revenue_proxy mean?",
    "que tan antiguos son los datos": "How old is the data?",
}


def normalize_spanish(question: str) -> str:
    # Do not remove hidden control characters or unrecognized suffixes.
    normalized = unicodedata.normalize("NFD", question)
    text = (
        "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        .casefold()
        .strip()
    )
    if text.startswith("¿"):
        text = text[1:]
    if text.endswith("?"):
        text = text[:-1]
    if text in FIXED:
        return FIXED[text]
    match = re.fullmatch(
        r"cuantas unidades vendio ([a-z0-9_]{1,64}) durante ("
        + "|".join(MONTHS)
        + r") de (\d{4})",
        text,
    )
    if match:
        store, month, year = match.groups()
        return f"Show units for store {store.upper()} during {calendar.month_name[MONTHS.index(month) + 1]} {year}"
    match = re.fullmatch(
        r"cuantas unidades vendio ([a-z0-9_]{1,64}) del (\d{4}-\d{2}-\d{2}) al (\d{4}-\d{2}-\d{2})",
        text,
    )
    if match:
        store, start, end = match.groups()
        return f"Show units for store {store.upper()} from {start} to {end}"
    return question
