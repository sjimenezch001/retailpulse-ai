"""Application-owned sources. Synthetic snapshots never replace missing real data."""

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import duckdb

from retailpulse.agent.database import gold_session
from retailpulse.agent.errors import AgentError
from retailpulse.agent.tools import HISTORICAL, GoldTools, metadata
from retailpulse.api.contracts import Dataset, ForecastWindow, Mode, ProviderMode

SYNTHETIC = Path(__file__).parent / "synthetic"
NOTICE = "Explicitly synthetic portfolio data; no real M5 observations or measured LightGBM performance."


@dataclass(frozen=True)
class ApiSettings:
    root: Path
    database: Path
    mode: Mode = "real"
    provider: ProviderMode = "ollama"
    model: str = "qwen2.5:1.5b"
    ui_port: int = 8501


def portable_database(directory: Path) -> Path:
    """Load versioned synthetic CSVs into a disposable, ignored serving database."""
    manifest = json.loads((SYNTHETIC / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((SYNTHETIC / "manifest.json").read_bytes())
    for table in manifest["tables"]:
        content = (SYNTHETIC / f"{table}.csv").read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest["sha256"][table]:
            raise ValueError("The packaged synthetic snapshot failed integrity validation.")
        digest.update(content)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"synthetic-{digest.hexdigest()[:16]}.duckdb"
    if not target.exists():
        # The manifest is trusted package data, not supplied by an HTTP request.
        import tempfile

        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            staged = Path(temporary) / "snapshot.duckdb"
            with duckdb.connect(str(staged)) as db:
                for table, schema in manifest["tables"].items():
                    if not table.isidentifier():
                        raise ValueError("Invalid packaged table")
                    db.execute(f'CREATE TABLE "{table}" ({schema})')
                    db.execute(
                        f'INSERT INTO "{table}" SELECT * FROM read_csv(?, header=true, auto_detect=true)',
                        [str(SYNTHETIC / f"{table}.csv")],
                    )
            # Copy out of TemporaryDirectory: on Windows its private ACL would
            # otherwise follow the renamed file into the shared workspace.
            publish = directory / f".snapshot-{uuid4().hex}.tmp"
            try:
                shutil.copyfile(staged, publish)
                publish.replace(target)
            finally:
                publish.unlink(missing_ok=True)
    return target


class DemoTools(GoldTools):
    def get_kpi(self, request):
        result = super().get_kpi(request)
        return result.model_copy(
            update={
                "warnings": [NOTICE if w == HISTORICAL else w for w in result.warnings]
            }
        )

    def get_forecast(self, request):
        result = super().get_forecast(request)
        return result.model_copy(
            update={
                "warnings": [NOTICE if w == HISTORICAL else w for w in result.warnings]
            }
        )


class Source:
    def __init__(self, settings: ApiSettings):
        self.settings = settings
        self.tools = (DemoTools if settings.mode == "synthetic" else GoldTools)(
            settings.database
        )

    def signature(self):
        try:
            stat = self.settings.database.stat()
            return (stat.st_mtime_ns, stat.st_size, stat.st_ino)
        except OSError as exc:
            raise AgentError(
                "missing_gold",
                "Real Gold is unavailable. Start with --mode synthetic for the explicitly synthetic portable demo.",
                "unavailable",
            ) from exc

    def describe(self) -> Dataset:
        before = self.signature()
        with gold_session(self.settings.database) as db:
            lineage = metadata(db, "pipeline_metadata")
            stores = [
                r[0]
                for r in db.execute(
                    "SELECT store_id FROM dim_store ORDER BY store_id LIMIT 101"
                ).fetchall()
            ]
            departments = [
                r[0]
                for r in db.execute(
                    "SELECT DISTINCT dept_id FROM dim_product ORDER BY dept_id LIMIT 101"
                ).fetchall()
            ]
            windows = db.execute(
                "SELECT model,split,min(target_date),max(target_date),max(horizon) FROM fact_forecast GROUP BY model,split ORDER BY model,split LIMIT 20"
            ).fetchall()
        if len(stores) > 100 or len(departments) > 100:
            raise AgentError(
                "pilot_limit",
                "The source exceeds the supported pilot dimensions.",
                "unavailable",
            )
        if before != self.signature():
            raise AgentError(
                "source_changed",
                "The dataset changed during the request. Retry against the new version.",
                "unavailable",
            )
        is_synthetic = lineage.gold_run_id.startswith("synthetic-")
        if is_synthetic != (self.settings.mode == "synthetic"):
            raise AgentError(
                "mode_mismatch",
                "The configured dataset does not match the selected demonstration mode.",
                "unavailable",
            )
        token = hashlib.sha256(
            json.dumps(
                [self.settings.mode, lineage.model_dump(mode="json"), before],
                sort_keys=True,
            ).encode()
        ).hexdigest()[:20]
        return Dataset(
            mode=self.settings.mode,
            label="Synthetic portfolio demo"
            if is_synthetic
            else "Real M5 historical pilot",
            dataset_version=f"{self.settings.mode}:{lineage.gold_run_id}:{token}",
            generation_timestamp=lineage.generated_at,
            lineage=lineage,
            stores=stores,
            departments=departments,
            forecast_windows=[
                ForecastWindow(model=m, split=s, start=a, end=b, max_horizon=h)
                for m, s, a, b, h in windows
            ],
        )
