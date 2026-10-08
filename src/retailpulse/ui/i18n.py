"""Central UI copy and deterministic locale formatting; no process-wide locale."""

import calendar
from datetime import date

ES = {
    "How many units did CA_1 sell during April 2016?": "¿Cuántas unidades vendió CA_1 durante abril de 2016?",
    "Show units for {store} from {start} to {end}": "¿Cuántas unidades vendió {store} del {start} al {end}?",
    "Compare LightGBM and rolling mean WMAPE on the test period": "Compara LightGBM y la media móvil en el conjunto de prueba",
    "What does revenue_proxy mean?": "¿Qué significa revenue_proxy?",
    "How old is the data?": "¿Qué tan antiguos son los datos?",
    "Language": "Idioma",
    "Theme": "Tema",
    "Light": "Claro",
    "Dark": "Oscuro",
    "Overview": "Resumen",
    "Forecast": "Pronóstico",
    "Ask RetailPulse": "Pregúntale a RetailPulse",
    "Architecture": "Arquitectura",
    "DEMAND INTELLIGENCE": "ANÁLISIS DE DEMANDA",
    "See demand. Understand the evidence.": "Comprende la demanda. Conoce la evidencia.",
    "Retail analytics, honest forecasts and answers you can trace.": "Análisis comercial, pronósticos transparentes y respuestas verificables.",
    "Real M5 historical pilot": "Piloto histórico real de M5",
    "Synthetic portfolio demo": "Demo sintética de portafolio",
    "REAL M5 · HISTORICAL PILOT · Local and read-only": "M5 REAL · PILOTO HISTÓRICO · Local y de solo lectura",
    "SYNTHETIC PORTFOLIO DEMO · All observations and comparison series are illustrative. No real M5 data or trained-model performance.": "DEMO SINTÉTICA DE PORTAFOLIO · Todas las observaciones y series son ilustrativas. No contienen datos reales de M5 ni resultados de un modelo entrenado.",
    "Observed {period} · Snapshot: {as_of}": "Observaciones: {period} · Corte: {as_of}",
    "Your analysis scope": "Alcance del análisis",
    "Sales date range": "Período de ventas",
    "Start date": "Fecha inicial",
    "End date": "Fecha final",
    "Use {format}.": "Usa {format}.",
    "Use valid, ordered dates within the observed period.": "Usa fechas válidas y ordenadas dentro del período observado.",
    "Store": "Tienda",
    "Department": "Departamento",
    "Item": "Producto",
    "All stores": "Todas las tiendas",
    "All departments": "Todos los departamentos",
    "Snapshot freshness": "Antigüedad de los datos",
    "{value} days": "{value} días",
    "Measured at {date}; not pipeline latency.": "Calculada al {date}; no es la demora del procesamiento.",
    "No current sales or inventory claims.": "No representa ventas actuales ni existencias.",
    "The demand picture": "La demanda en perspectiva",
    "Observed sales, transparent price coverage and signals worth investigating.": "Ventas observadas, cobertura de precios y señales para investigar.",
    "Observed units": "Unidades observadas",
    "Price coverage": "Cobertura de precios",
    "Known-price revenue proxy": "Ingresos estimados con precio conocido",
    "Revenue proxy": "Ingresos estimados",
    "Demand spike flags": "Señales de aumento de demanda",
    "Historical freshness": "Antigüedad histórica",
    "7-day rolling demand": "Demanda móvil de 7 días",
    "28-day rolling demand": "Demanda móvil de 28 días",
    "Price change": "Cambio de precio",
    "Unknown": "Desconocido",
    "Undefined": "No definido",
    "units": "unidades",
    "days": "días",
    "Partial proxy: {count} observations lack prices. Complete revenue is unknown; this is not audited revenue.": "Estimación parcial: {count} observaciones no tienen precio. Los ingresos completos se desconocen; no son ingresos auditados.",
    "Revenue is a price-based proxy, not audited revenue. Spike flags do not prove stockouts or causes.": "Los ingresos son una estimación basada en precios, no ingresos auditados. Las señales no prueban faltantes ni causas.",
    "Daily demand": "Demanda diaria",
    "By store": "Por tienda",
    "By department": "Por departamento",
    "Last 90 days of the selected range; cards and comparisons use the entire range.": "Últimos 90 días del período seleccionado; las tarjetas y comparaciones usan el período completo.",
    "Date": "Fecha",
    "Units": "Unidades",
    "Segment": "Segmento",
    "Daily units": "Unidades diarias",
    "Series": "Serie",
    "Source & metric definitions": "Fuente y definiciones",
    "Technical details": "Detalles técnicos",
    "Forecasts with an honest scorecard": "Pronósticos con resultados transparentes",
    "Full-pilot historical test: LightGBM improves WMAPE and MAE, but has worse RMSE than rolling mean. Filtered segments can differ. No future LightGBM forecast is available.": "Prueba histórica del piloto completo: LightGBM mejora WMAPE y MAE, pero tiene peor RMSE que la media móvil. Los segmentos pueden diferir. No hay pronósticos futuros de LightGBM.",
    "Synthetic comparison: the LightGBM series is simulated, not trained. These scores do not measure real model performance.": "Comparación sintética: la serie de LightGBM es simulada, no entrenada. Estas métricas no miden el rendimiento real de un modelo.",
    "Models to compare": "Modelos a comparar",
    "Historical split": "Conjunto histórico",
    "Test": "Prueba",
    "Validation": "Validación",
    "Future": "Futuro",
    "Forecast horizon": "Horizonte del pronóstico",
    "All horizons": "Todos los horizontes",
    "Day {n}": "Día {n}",
    "Store and department filters apply here. Sales dates apply to Overview; forecasts use the selected historical split.": "Los filtros de tienda y departamento se aplican aquí. Las fechas de ventas corresponden al Resumen; los pronósticos usan el conjunto histórico seleccionado.",
    "Choose a model to view historical performance.": "Elige un modelo para ver los resultados históricos.",
    "No predictions match the selected scope.": "No hay predicciones para el alcance seleccionado.",
    "Rolling mean": "Media móvil",
    "Last value": "Último valor",
    "Seasonal naive (7)": "Ingenuo estacional (7)",
    "LightGBM": "LightGBM",
    "WMAPE": "WMAPE",
    "MAE": "MAE",
    "RMSE": "RMSE",
    "Observed vs predicted demand": "Demanda observada y pronosticada",
    "Observed actuals": "Valores observados",
    "Forecast scope & provenance": "Alcance y procedencia del pronóstico",
    "Accuracy describes historical backtests. Each model is compared separately; predictions are never added across models.": "La precisión corresponde a evaluaciones históricas. Cada modelo se compara por separado; sus predicciones nunca se suman entre modelos.",
    "Weighted absolute error as a share of observed units; lower is better.": "Error absoluto ponderado como proporción de las unidades observadas; cuanto menor, mejor.",
    "Average absolute error in units; lower is better.": "Error absoluto medio en unidades; cuanto menor, mejor.",
    "Root mean squared error in units; more sensitive to large errors.": "Raíz del error cuadrático medio en unidades; más sensible a errores grandes.",
    "One clear question. Approved tools. Verifiable answers.": "Una pregunta clara. Herramientas autorizadas. Respuestas verificables.",
    "Answer provider": "Proveedor de respuesta",
    "Ollama · local model": "Ollama · modelo local",
    "Deterministic · offline": "Determinista · sin conexión",
    "Ollama is unavailable. Start the local service or choose deterministic mode. Any fallback is explicitly disclosed.": "Ollama no está disponible. Inicia el servicio local o elige el modo determinista. Cualquier respuesta de respaldo se identifica explícitamente.",
    "Explore store demand": "Consultar demanda por tienda",
    "Compare forecast models": "Comparar modelos",
    "Explain revenue proxy": "Explicar ingresos estimados",
    "Check data freshness": "Consultar antigüedad",
    "Each question is independent. Chat history is not sent to the assistant. Spanish support is limited to the suggested forms and explicit store/month or ISO date ranges.": "Cada pregunta es independiente. El historial no se envía al asistente. El español admite las formulaciones sugeridas y consultas de tienda con mes o intervalo de fechas ISO explícito.",
    "Ask about historical units, metrics or forecast accuracy": "Pregunta por unidades históricas, métricas o precisión del pronóstico",
    "Consulting approved tools. A cold local model may take up to 30 seconds.": "Consultando herramientas autorizadas. La primera respuesta del modelo local puede tardar hasta 30 segundos.",
    "Grounded in approved data": "Verificado con datos autorizados",
    "Grounding not validated": "Fundamentación no validada",
    "Live local model": "Modelo local en vivo",
    "Deterministic fallback": "Respuesta determinista de respaldo",
    "The local model did not complete this answer. Approved deterministic tools provided the result.": "El modelo local no completó esta respuesta. El resultado proviene de herramientas deterministas autorizadas.",
    "Local model not called": "No se llamó al modelo local",
    "Execution": "Ejecución",
    "Sources, scope & provider diagnostics": "Fuentes, alcance y diagnóstico del proveedor",
    "Period": "Período",
    "Source": "Fuente",
    "All selected observations": "Todas las observaciones seleccionadas",
    "Store {store} sold {value} units during {period}.": "La tienda {store} vendió {value} unidades durante {period}.",
    "The selected scope recorded {value} units during {period}.": "El alcance seleccionado registró {value} unidades durante {period}.",
    "{metric}: {value} for the selected scope.": "{metric}: {value} para el alcance seleccionado.",
    "Data is {value} days old at the snapshot date {date}.": "Los datos tienen {value} días de antigüedad a la fecha de corte {date}.",
    "Previous period": "Período anterior",
    "Change": "Cambio",
    "Observed": "Observado",
    "Predicted": "Pronosticado",
    "Historical forecast comparison": "Comparación histórica de pronósticos",
    "No accuracy score is available without observed actuals.": "No se puede calcular la precisión sin valores observados.",
    "This scope has lower LightGBM WMAPE and MAE, but higher RMSE than rolling mean.": "En este alcance, LightGBM tiene menor WMAPE y MAE, pero mayor RMSE que la media móvil.",
    "Compare each error measure; the results do not establish a universal winner.": "Compara cada medida de error; los resultados no establecen un ganador universal.",
    "From the approved metric documentation": "De la documentación autorizada de métricas",
    "Original source excerpt (English)": "Extracto original de la fuente (inglés)",
    "Translated excerpt": "Extracto traducido",
    "lines": "líneas",
    "This is an original, unmodified source excerpt. Repository documents remain in English.": "Este es un extracto original sin modificar. La documentación del repositorio permanece en inglés.",
    "Please clarify the metric, observed period and scope. Try one of the supported example questions.": "Aclara la métrica, el período observado y el alcance. Prueba una de las preguntas de ejemplo admitidas.",
    "This request is outside the approved read-only analytical tools. Choose a supported historical question.": "La solicitud está fuera de las herramientas analíticas autorizadas de solo lectura. Elige una pregunta histórica admitida.",
    "This snapshot contains historical observations, not current sales.": "Este conjunto contiene observaciones históricas, no ventas actuales.",
    "Inventory data is unavailable; zero sales do not establish a stockout.": "No hay datos de existencias; ventas nulas no demuestran un faltante.",
    "These observations do not establish causation.": "Estas observaciones no demuestran causalidad.",
    "The requested data is unavailable. Check the local demo service and selected scope.": "Los datos solicitados no están disponibles. Revisa el servicio local y el alcance seleccionado.",
    "The answer could not be completed safely. Please retry or use a supported example.": "No se pudo completar la respuesta de forma segura. Reintenta o usa un ejemplo admitido.",
    "The local API is unavailable or timed out. Start the demo and retry.": "La API local no está disponible o agotó el tiempo de espera. Inicia la demo y vuelve a intentarlo.",
    "The request could not be completed. Check the filters or retry shortly.": "No se pudo completar la solicitud. Revisa los filtros o vuelve a intentarlo en unos instantes.",
    "The real dataset is unavailable. Choose explicit synthetic mode for the portable demo.": "Los datos reales no están disponibles. Elige explícitamente el modo sintético para la demo portable.",
    "The synthetic snapshot is unavailable. Check the local demo files and restart.": "El conjunto sintético no está disponible. Revisa los archivos locales de la demo y reinicia.",
    "Trace every answer back to its source": "Sigue cada respuesta hasta su origen",
    "A local analytical product, from observations to a grounded business answer.": "Un producto analítico local, desde las observaciones hasta una respuesta comercial fundamentada.",
    "Source data": "Datos de origen",
    "Validated data": "Datos validados",
    "Business metrics": "Métricas de negocio",
    "Models & decisions": "Modelos y decisiones",
    "M5 CSV inputs, content hashes and immutable ingestion provenance.": "Entradas CSV de M5, hashes del contenido y procedencia inmutable de la ingesta.",
    "Validated daily sales, calendar and prices; explicit missing data.": "Ventas diarias, calendario y precios validados; datos faltantes explícitos.",
    "Canonical KPIs and read-only analytical tools, with source lineage.": "Métricas canónicas y herramientas analíticas de solo lectura, con trazabilidad.",
    "Frozen forecasting / MLflow → Power BI, FastAPI, Streamlit and the grounded assistant.": "Pronósticos congelados / MLflow → Power BI, FastAPI, Streamlit y el asistente fundamentado.",
    "Built to be checked": "Diseñado para verificarse",
    "Know the limits": "Conoce las limitaciones",
    "Synthetic tests run without Kaggle or Ollama. Real acceptance reconciles API results with Gold. Frozen artifacts and source hashes are preserved.": "Las pruebas sintéticas funcionan sin Kaggle ni Ollama. La validación real concilia la API con Gold. Se preservan los artefactos congelados y hashes de origen.",
    "Historical data is not current sales. M5 has no inventory data. Revenue is a proxy; spikes are heuristic. No AWS deployment is claimed.": "Los datos históricos no representan ventas actuales. M5 no incluye existencias. Los ingresos son una estimación y los picos son heurísticos. No se afirma un despliegue en AWS.",
    "Explore the metric catalog": "Consultar catálogo de métricas",
    "Open the API documentation": "Abrir documentación de la API",
    "Read the model card": "Leer ficha del modelo",
    "Download the demo guide": "Descargar guía de la demo",
    "Documentation is maintained in English.": "La documentación se mantiene en inglés.",
    "Dataset lineage": "Procedencia de los datos",
    "Historical evidence · Reproducible results · Local portfolio demo": "Evidencia histórica · Resultados reproducibles · Demo local de portafolio",
}
MONTH_NAMES = {
    "en": list(calendar.month_name)[1:],
    "es": "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),
}

# Exact reviewed source translations; unknown excerpts remain original quotes.
EXCERPT_ES = {
    "`revenue_proxy` is units multiplied by selling price, not audited revenue.\nIts canonical aggregate is unknown if any selected price is missing.\n`known_revenue_proxy` is the separate partial sum of priced observations.\n`price_coverage` is the share of observations with known prices, including\nzero-sales observations. Missing prices are not replaced with known zeros.": "`revenue_proxy` es el producto de las unidades por el precio de venta, no ingresos auditados. Su agregado canónico es desconocido si falta algún precio seleccionado. `known_revenue_proxy` es la suma parcial separada de observaciones con precio. `price_coverage` es la proporción de observaciones con precio conocido, incluidas las de ventas nulas. Los precios faltantes no se sustituyen por ceros.",
    "revenue_proxy is units multiplied by selling price, not audited revenue.\nIts aggregate is unknown if any selected price is missing.\nknown_revenue_proxy sums only priced observations; price_coverage is the\nshare of observations with a known price. Missing prices remain unknown.": "`revenue_proxy` es el producto de las unidades por el precio de venta, no ingresos auditados. Su agregado es desconocido si falta algún precio seleccionado. `known_revenue_proxy` suma solo observaciones con precio; `price_coverage` es la proporción con precio conocido. Los precios faltantes siguen siendo desconocidos.",
    "| revenue_proxy | `units * sell_price`; unknown if price is missing | same grain; sum only with complete price coverage; a proxy, not audited revenue |": "`revenue_proxy` = `units * sell_price`. Es desconocido si falta el precio. Mantiene el mismo nivel de detalle y solo se suma con cobertura completa de precios; es una estimación, no ingresos auditados.",
    "`mart_store_weekly` groups by store, department and M5 `wm_yr_wk`, which is not\nan ISO week number. Partial boundary weeks expose `observed_days`. Its canonical\n`revenue_proxy` is NULL if any included daily price is missing. The separate\n`known_revenue_proxy` is a partial sum and must never be presented as a complete\ntotal; `missing_price_rows` and `price_coverage` expose this limitation.": "`mart_store_weekly` agrupa por tienda, departamento y `wm_yr_wk` de M5, que no es un número de semana ISO. Las semanas parciales exponen `observed_days`. Su `revenue_proxy` canónico es NULL si falta algún precio diario incluido. `known_revenue_proxy` es una suma parcial separada y nunca debe presentarse como un total completo; `missing_price_rows` y `price_coverage` muestran esta limitación.",
}


def translate(text, language="en", **values):
    return (ES[text] if language == "es" else text).format(**values)


def number(value, language="en", decimals=0):
    if value is None:
        return translate("Unknown", language)
    result = f"{value:,.{decimals}f}"
    return (
        result.translate(str.maketrans({",": ".", ".": ","}))
        if language == "es"
        else result
    )


def date_label(value, language="en"):
    day = date.fromisoformat(str(value))
    return day.strftime("%d/%m/%Y" if language == "es" else "%m/%d/%Y")


def period_label(period, language="en"):
    start, end = (date.fromisoformat(str(period[k])) for k in ("start", "end"))
    if (
        start.day == 1
        and start.year == end.year
        and start.month == end.month
        and end.day == calendar.monthrange(end.year, end.month)[1]
    ):
        month = MONTH_NAMES[language][start.month - 1]
        return (
            f"{month} de {start.year}" if language == "es" else f"{month} {start.year}"
        )
    return date_label(start, language) + " – " + date_label(end, language)
