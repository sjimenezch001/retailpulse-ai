# Arquitectura objetivo

CSV público → Python → Bronze/Silver/Gold → DuckDB → Power BI

Python preparará los datos públicos en capas de datos crudos, depurados y
analíticos. DuckDB permitirá consultar los resultados y Power BI presentará
las métricas de negocio.

RP-01 establece únicamente el repositorio, el entorno y los estándares; este
flujo todavía no está implementado. ML, API, agente y AWS se incorporarán en
etapas posteriores.
