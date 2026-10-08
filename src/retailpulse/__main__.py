"""Local stage commands; failures propagate and return a nonzero exit code."""
import argparse
from datetime import date
from pathlib import Path

import yaml

from retailpulse.data.config import load_config
from retailpulse.data.source import inspect_sources, read_sources, write_json


def main():
    parser = argparse.ArgumentParser(description="RetailPulse AI local data pipeline")
    parser.add_argument("--config", type=Path, default=Path("config/local.yaml"))
    commands = parser.add_subparsers(dest="command", required=True)
    profile = commands.add_parser("profile", help="Inspect local real M5 source files")
    profile.add_argument("--select-pilot", action="store_true")
    profile.add_argument("--sample", action="store_true", help="Export a small real pilot sample")
    commands.add_parser("bronze", help="Ingest configured CSV sources into Parquet")
    commands.add_parser("silver", help="Build validated daily sales and dimensions")
    gold = commands.add_parser("gold", help="Build the canonical DuckDB analytics layer")
    gold.add_argument("--as-of", type=date.fromisoformat)
    query = commands.add_parser("query", help="Run a named repository business query")
    query.add_argument("name", choices=["01_sales_trend", "02_segment_changes", "03_forecast_errors",
                                      "04_events_and_prices", "05_metric_provenance"])
    baseline = commands.add_parser("baseline", help="Evaluate baselines and write Gold forecasts")
    baseline.add_argument("--validation-days", type=int, default=28)
    baseline.add_argument("--test-days", type=int, default=28)
    baseline.add_argument("--rolling-window", type=int, default=7)
    baseline.add_argument("--future-horizon", type=int, default=28)
    model = commands.add_parser("model", help="Compare LightGBM on validation, freeze and evaluate once")
    model.add_argument("--validation-only", action="store_true", help="Freeze selection without reading test actuals")
    commands.add_parser("export-bi", help="Export reconciled, local Power BI datasets from Gold")
    ask = commands.add_parser("ask", help="Ask a grounded historical retail question")
    ask.add_argument("question")
    ask.add_argument("--json", dest="json_output", action="store_true")
    evaluate = commands.add_parser("agent-eval", help="Evaluate golden questions against local Gold")
    for command in (ask, evaluate):
        command.add_argument("--provider", choices=["auto", "deterministic", "ollama"], default="auto")
        command.add_argument("--ollama-model", help="Use an already installed local model; never downloads one")
    args = parser.parse_args()
    settings, root = load_config(args.config)
    if args.command in ("ask", "agent-eval"):
        from retailpulse.agent.cli import run

        raise SystemExit(run(args, settings, root))
    if args.command == "export-bi":
        import json

        from retailpulse.bi.export import export_bi

        result = export_bi(settings.output_path, root / "artifacts/powerbi/data", root / "sql")
        print(json.dumps({"source_run_id": result["source_run_id"], "reconciliation": result["reconciliation"],
                          "rows": {name: table["rows"] for name, table in result["tables"].items()}}, indent=2))
    if args.command == "model":
        import json

        from retailpulse.models.workflow import run_model

        result = run_model(settings.output_path, root / "artifacts", validation_only=args.validation_only)
        summary = {"status": result["status"], "winner": result["winner"]["configuration"]["name"],
                   "validation": result["winner"]["validation_metrics"],
                   "test": result.get("test", {}).get("metrics"),
                   "reused": result.get("reused", False), "artifacts": result["artifact_path"]}
        print(json.dumps(summary, indent=2))
    if args.command == "baseline":
        from retailpulse.models.baseline import run_baselines

        print(run_baselines(settings.output_path, validation_days=args.validation_days,
                            test_days=args.test_days, rolling_window=args.rolling_window,
                            future_horizon=args.future_horizon))
    if args.command == "gold":
        from retailpulse.transforms.gold import run_gold

        print(run_gold(settings.output_path, root / "sql", args.as_of))
    if args.command == "query":
        import duckdb

        with duckdb.connect(str(settings.output_path / "gold/retailpulse.duckdb"), read_only=True) as db:
            sql = (root / "sql/queries" / f"{args.name}.sql").read_text(encoding="utf-8")
            print(db.execute(sql).fetchdf().to_csv(index=False))
    if args.command == "silver":
        from retailpulse.transforms.silver import run_silver

        print(run_silver(settings.output_path, settings.pilot.stores, settings.pilot.departments))
    if args.command == "bronze":
        from retailpulse.ingestion.bronze import ingest

        result = ingest(settings.dataset_path, settings.output_path / "bronze")
        print(result)
    if args.command == "profile":
        manifest = inspect_sources(settings.dataset_path)
        write_json(root / "data/contracts/raw_manifest.json", manifest)
        if manifest["status"] != "INSPECTED":
            print(manifest["status"] + ": " + ", ".join(manifest["missing_files"]))
            return
        if args.select_pilot:
            config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
            config["pilot"] = manifest["pilot"]
            args.config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        if args.sample:
            frames = read_sources(settings.dataset_path)
            pilot = manifest["pilot"]
            sales = frames["sales"]
            sample = sales.loc[sales["store_id"].isin(pilot["stores"])
                               & sales["dept_id"].isin(pilot["departments"])]
            sample = sample.sort_values(["store_id", "dept_id", "item_id"]).groupby(
                ["store_id", "dept_id"], observed=True).head(1)
            target = root / "data/sample"
            target.mkdir(parents=True, exist_ok=True)
            sample.to_csv(target / "real_m5_sales_sample.csv", index=False)
            write_json(target / "provenance.json", {
                "synthetic": False, "selection": "First item per pilot store/department",
                "source_manifest": "data/contracts/raw_manifest.json",
                "source_sha256": next(f["sha256"] for f in manifest["files"]
                                      if f["source_filename"] == "sales_train_evaluation.csv"),
            })
        print("Source inspection complete; see data/contracts/raw_manifest.json")


if __name__ == "__main__":
    main()
