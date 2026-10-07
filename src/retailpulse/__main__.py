"""Local stage commands; failures propagate and return a nonzero exit code."""
import argparse
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
    args = parser.parse_args()
    settings, root = load_config(args.config)
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
