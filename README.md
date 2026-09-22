# RetailPulse AI

Plataforma de analítica de demanda para retail. Busca convertir ventas
históricas, calendario y precios en métricas verificables para comparar
tiendas y departamentos, reduciendo análisis dispersos y definiciones
inconsistentes de negocio.

**Estado: RP-01 — Repository, environment and standards.** Base Python con
packaging, configuración local, prueba de importación y lint. El dataset M5
todavía no se incluye ni se descarga; la ingesta no está implementada.

Stack inicial: Python 3.12, pandas, PyArrow, DuckDB, Pydantic y PyYAML.
Desarrollo: pytest y Ruff. Packaging: setuptools y pip.

## Estructura

```text
config/local.yaml      Rutas relativas y selección de piloto pendiente
data/sample/           Muestras pequeñas versionables
data/contracts/        Contratos de datos
notebooks/             Exploración
sql/{silver,gold,checks}/
src/retailpulse/        Paquete Python (versión 0.1.0)
  ingestion/ transforms/ quality/ features/ models/ api/ agent/
tests/                 Smoke test; unit/ e integration/ reservados
docs/                  Producto, alcance, arquitectura y evidence/
pyproject.toml         Metadatos, dependencias y configuración de herramientas
requirements.txt       Versiones exactas del entorno validado
.env.example           Plantilla sin credenciales
```

Los subpaquetes y directorios reservados aún no contienen funcionalidad.
Los datos crudos, procesados y artefactos generados se excluyen de Git.

## Quick Start — Windows PowerShell

Desde la raíz del repositorio, usar Python 3.12 (validado con 3.12.10).
Solo si todavía no existe `.venv`, crearlo con `py -3.12 -m venv .venv`.
Los comandos siguientes usan directamente ese entorno, sin activación:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

`pyproject.toml` es la fuente principal de configuración. `requirements.txt`
fija las dependencias directas y transitivas validadas en Windows con Python
3.12; instalarlo primero permite reproducir esas versiones. El paquete local
se instala después en modo editable. pytest usa el paquete instalado desde
`src/` y descubre las pruebas en `tests/`.

`config/local.yaml` reserva las rutas `data/raw` y `data/processed`, relativas
a la raíz del repositorio. Tiendas y departamentos permanecen sin seleccionar.
No se necesitan secretos ni un archivo `.env` en esta etapa.

Ver el [producto](docs/product_brief.md), el [alcance](docs/scope.md) y la
[arquitectura objetivo](docs/architecture.md).
