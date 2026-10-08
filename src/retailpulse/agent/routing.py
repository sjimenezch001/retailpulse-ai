"""Conservative English routing. Unexpressed or unsupported filters never become guesses."""
import calendar
import re
import unicodedata
from datetime import date

from retailpulse.agent.contracts import (
    DocsCall,
    DocsRequest,
    ForecastCall,
    ForecastRequest,
    KpiCall,
    KpiRequest,
    Plan,
)
from retailpulse.agent.errors import AgentError

MODELS = {"last_value": r"last[_ ]value", "rolling_mean": r"rolling[_ ]mean",
          "seasonal_naive_7": r"seasonal[_ ]naive(?:[_ ]7)?", "lightgbm_global_v1": r"lightgbm(?:_global_v1)?"}
ALIASES = {
    "known_revenue_proxy": r"known[_ ](?:price[_ ]|revenue[_ ])?(?:revenue(?:[_ ]proxy)?|proxy)|known_revenue_proxy",
    "revenue_proxy": r"revenue(?:[_ ]proxy)?",
    "price_coverage": r"price[_ ]coverage",
    "rolling_7d": r"rolling[_ ]7d|7[- ]day (?:rolling )?demand",
    "rolling_28d": r"rolling[_ ]28d|28[- ]day (?:rolling )?demand",
    "demand_spike_flag": r"demand_spike_flag|(?:demand )?spike(?: flags?|s)?",
    "data_freshness": r"data_freshness|freshness|how (?:old|fresh) is (?:the )?data",
    "units": r"\bunits\b",
}
FORBIDDEN = re.compile(r"\b(drop|alter|truncate|attach|detach|delete|insert|update)\s+(table|database|from|into)|\b(select|pragma)\b|\bcopy\b.{0,60}\bto\b|read_(csv|parquet|text)|\b(execute|run)\s+(sql|shell|commands?)|\.env\b|\b(secrets?|passwords?|credentials?)\b|ignore.{0,80}(instructions|previous|rules)|system\s*(prompt|message)|bypass|\b(dump|unrestricted)\b|without (?:row )?limits|all (?:raw )?(?:rows|records)|[A-Za-z]:[\\/]|https?://|;|--|/\*", re.I)


def preflight(question):
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise AgentError("question_size", "Use a nonempty question of at most 1000 characters.")
    text = unicodedata.normalize("NFKC", question)
    if any(unicodedata.category(c) == "Cf" for c in text) or FORBIDDEN.search(text):
        raise AgentError("unsafe_request", "Only approved read-only aggregate tools and metric documents are available. SQL, database changes, file access and instruction bypasses are not supported.", "refused")
    if re.search(r"\b(today|yesterday|now|current sales|this (?:week|month|year)|real[- ]time)\b", text, re.I):
        raise AgentError("current_period", "This project contains historical M5 observations, not live sales. Choose an explicit observed period; freshness is measured against the Gold snapshot date.", "refused")
    if re.search(r"\b(inventory|stockouts?|out of stock|reorder|replenish)\b", text, re.I):
        raise AgentError("no_inventory", "M5 contains no actual inventory data. Zero sales do not prove stockouts, and this assistant cannot recommend inventory quantities.", "refused")
    if re.search(r"\b(caused?|causality|prove.{0,20}(price|event)|why did)\b", text, re.I):
        raise AgentError("no_causal_evidence", "Price/event associations and spike flags do not establish causation. Request a descriptive metric over an explicit period.", "refused")
    if re.search(r"\b(profit|margin|payroll|budget|roi|audited revenue|actual revenue)\b", text, re.I):
        raise AgentError("unsupported_business_metric", "That business measure is unavailable. revenue_proxy is a price-based proxy, not audited revenue or profit.", "refused")
    if re.search(r"\b(except|excluding|exclude|not in|either|percentile|median|top|bottom)\b", text, re.I):
        raise AgentError("unsupported_filter", "That filter or ranking is not supported. Use one store/department/item or an approved aggregate grouping.")
    if re.search(r"\blimit\s+\d+|\bmillion\b", text, re.I):
        raise AgentError("row_limit", "Arbitrary row-limit overrides and record dumps are not supported.", "refused")
    return text


def extract_filters(text):
    values = {}
    patterns = {
        "store": r"\b(?:CA|TX|WI)_\d+\b|\bSYN_[AB]\b",
        "department": r"\b(?:FOODS|HOBBIES|HOUSEHOLD)_\d+\b|\bD[12]\b",
        "item": r"\b(?:FOODS|HOBBIES|HOUSEHOLD)_\d+_\d+\b|\bSYN_[12]\b",
    }
    for key, pattern in patterns.items():
        found = {value.upper() for value in re.findall(pattern, text, re.I)}
        label = {"store": "store", "department": "(?:department|dept)", "item": "(?:item|product)"}[key]
        explicit = re.findall(rf"(?<!by )\b{label}\s+([A-Za-z0-9_]+)", text, re.I)
        found.update(v.upper() for v in explicit if v.lower() not in {"from", "in", "during", "for", "and", "on", "changes", "units"})
        if len(found) > 1:
            raise AgentError("multiple_filters", f"Select one {key} or request grouping by that dimension.")
        if found:
            values[key] = found.pop()
    return values


def extract_dates(text):
    dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
    try:
        if len(dates) == 2:
            if not re.search(r"\d{4}-\d{2}-\d{2}\s+(?:to|through)\s+\d{4}-\d{2}-\d{2}", text, re.I) or re.search(r"\b(" + "|".join(calendar.month_name[1:]) + r")\s+\d{4}\b", text, re.I):
                raise AgentError("ambiguous_period", "Use a single continuous ISO date interval with 'to' or 'through'.")
            return date.fromisoformat(dates[0]), date.fromisoformat(dates[1])
        if len(dates) == 1 and re.search(r"\bon\s+\d{4}-", text, re.I):
            return date.fromisoformat(dates[0]), date.fromisoformat(dates[0])
        if dates:
            raise AgentError("ambiguous_period", "Specify both ISO date bounds, or one date after 'on'.")
        month_pattern = "|".join(calendar.month_name[1:])
        months = re.findall(rf"\b({month_pattern})\s+(\d{{4}})\b", text, re.I)
        if len(months) == 1:
            month_name, year = months[0]
            month = [m.casefold() for m in calendar.month_name].index(month_name.casefold())
            year = int(year)
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        if len(months) > 1 or re.search(r"\b\d{4}\b", text):
            raise AgentError("ambiguous_period", "Use one named month and year, or an explicit ISO date interval.")
    except ValueError as exc:
        raise AgentError("invalid_dates", "The requested calendar dates are invalid.") from exc
    return None, None


def supported_language(text, filters, models=(), metric=None):
    """Reject remaining conditions instead of ignoring unimplemented business scope."""
    remaining = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)
    remaining = re.sub(r"\b(" + "|".join(calendar.month_name[1:]) + r")\s+\d{4}\b", " ", remaining, flags=re.I)
    for value in filters.values():
        remaining = re.sub(r"\b" + re.escape(value) + r"\b", " ", remaining, flags=re.I)
    for model in models:
        remaining = re.sub(r"\b(?:" + MODELS[model] + r")\b", " ", remaining, flags=re.I)
    if metric:
        remaining = re.sub(r"\b(?:" + ALIASES[metric] + r")\b", " ", remaining, flags=re.I)
    if models:
        remaining = re.sub(r"\bhorizon\s+-?\d+\b", " ", remaining, flags=re.I)
    allowed = set("how many much did do does is are were was what the a an show give tell me can you please thanks total sum count observed historical units sales sell sold demand mean get report compare comparison change changes from to through during in on for of and with over all full history dates date entire period previous comparable equal length by per store stores department departments dept item product day week month daily weekly monthly forecast forecasts predicted predictions actual actuals validation test future models model wmape mae rmse horizon low high medium zero level levels data fresh freshness".split())
    if metric:
        allowed -= set("forecast forecasts predicted predictions actual actuals validation test future models model wmape mae rmse horizon low high medium zero level levels".split())
    else:
        allowed -= set("week month weekly monthly previous change changes comparison".split())
    if set(re.findall(r"[\w]+", remaining.casefold())) - allowed:
        raise AgentError("unsupported_language", "Part of the question specifies an unsupported or unclear condition. Use an approved metric, explicit period and store/department/item filters; ask one question at a time.")


def route(question, observed_period):
    text = preflight(question)
    if re.search(r"\b(what (?:does|is|are)|define|explain|definition)\b", text, re.I) and not re.search(r"\b(from|during|test|validation|future|sold|total)\b", text, re.I) and not re.search(ALIASES["data_freshness"], text, re.I):
        return Plan(call=DocsCall(tool="search_metric_docs", arguments=DocsRequest(query=text)))
    filters = extract_filters(text)
    start, end = extract_dates(text)
    models = tuple(name for name, pattern in MODELS.items() if re.search(r"\b(?:" + pattern + r")\b", text, re.I))
    if re.search(r"\ball models\b", text, re.I):
        models = tuple(MODELS)
    is_forecast = models or re.search(r"\b(WMAPE|MAE|RMSE|forecast|predicted|predictions)\b", text, re.I)
    if is_forecast:
        splits = re.findall(r"\b(validation|test|future)\b", text, re.I)
        if len(set(s.casefold() for s in splits)) != 1 or not models:
            raise AgentError("ambiguous_forecast", "Specify an approved model (or comparison models) and one split: validation, test or future.")
        horizons = re.findall(r"\bhorizon\s+(-?\d+)\b", text, re.I)
        levels = re.findall(r"\b(zero|low|medium|high)[- ]demand\b", text, re.I)
        if len(horizons) > 1 or len(levels) > 1:
            raise AgentError("multiple_filters", "Choose one horizon and one demand level.")
        horizon = int(horizons[0]) if horizons else None
        level = levels[0].casefold() if levels else None
        segmentation = "overall"
        for word, key in (("store", "store"), ("department", "department"), ("horizon", "horizon"), ("demand level", "demand_level"), ("day", "day")):
            if re.search(rf"\b(?:by|per) {word}s?\b", text, re.I) or (word == "day" and re.search(r"\bdaily\b", text, re.I)):
                if segmentation != "overall":
                    raise AgentError("ambiguous_grain", "Choose one forecast segmentation.")
                segmentation = key
        if re.search(r"\b(?:by|per) (?:items?|products?|weeks?|months?)\b", text, re.I):
            raise AgentError("unsupported_grain", "Forecast segmentation supports day, store, department, horizon or demand level.")
        if (re.search(r"\bhorizon\b", text, re.I) and horizon is None and segmentation != "horizon") or (re.search(r"\b(low|medium|high|zero)\b", text, re.I) and level is None):
            raise AgentError("ambiguous_filter", "Use 'horizon N' or a named demand level such as 'low demand'.")
        supported_language(text, filters, models)
        return Plan(call=ForecastCall(tool="get_forecast", arguments=ForecastRequest(models=models, split=splits[0].casefold(), start_date=start, end_date=end,
            horizon=horizon, demand_level=level, segmentation=segmentation, **filters)))
    metrics = [name for name, pattern in ALIASES.items() if re.search(r"\b(?:" + pattern + r")\b", text, re.I)]
    if "known_revenue_proxy" in metrics:
        metrics = [m for m in metrics if m != "revenue_proxy"]
    if len(metrics) != 1:
        raise AgentError("ambiguous_metric", "Specify one approved metric, such as units, revenue_proxy, price coverage, rolling_7d, spike flags or data freshness. 'Sales' alone could mean units or revenue.")
    metric = metrics[0]
    if metric != "data_freshness" and not start:
        if re.search(r"\b(full history|all observed dates|entire observed period)\b", text, re.I):
            period = observed_period()
            start, end = period.start, period.end
        else:
            raise AgentError("ambiguous_period", "Specify an observed date interval, a named month/year, or 'all observed dates'.")
    granularity = "total"
    for word, key in (("store", "store"), ("department", "department"), ("day", "day"), ("month", "month"), ("week", "week")):
        if re.search(rf"\b(?:by|per) {word}s?\b", text, re.I) or (word in ("day", "week", "month") and re.search(r"\b" + {"day":"daily", "week":"weekly", "month":"monthly"}[word] + r"\b", text, re.I)):
            if granularity != "total":
                raise AgentError("ambiguous_grain", "Choose one aggregation grain.")
            granularity = key
    supported_language(text, filters, metric=metric)
    comparison = "previous_period" if re.search(r"\bprevious (?:comparable |equal-length )?period\b", text, re.I) else None
    if re.search(r"\b(?:by|per) (?:items?|products?)\b", text, re.I):
        raise AgentError("unsupported_grain", "KPI grouping supports day, week, month, store or department; item is a filter only.")
    if re.search(r"\b(compare|comparison|changes?|previous)\b", text, re.I) and not comparison:
        raise AgentError("ambiguous_comparison", "For units changes, specify 'previous period' for an equal-length comparison.")
    return Plan(call=KpiCall(tool="get_kpi", arguments=KpiRequest(metric=metric, start_date=start, end_date=end, granularity=granularity, comparison=comparison, **filters)))
