# M5 source and acquisition

Use the official [M5 Forecasting — Accuracy data page](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data).
The [competition organizers' methods repository](https://github.com/Mcompetitions/M5-methods)
also identifies the evaluation source files. Sign in to Kaggle and accept the
competition rules if prompted. Download the competition data using the website,
then extract exactly these files into the ignored `data/raw/m5/` directory:

- `calendar.csv`
- `sell_prices.csv`
- `sales_train_evaluation.csv`

`sales_train_validation.csv` is not required. No Kaggle credentials, downloader,
or additional dependency is needed by this project. Do not commit the download,
archive, extracted datasets, or real row-level samples. Until redistribution
rights are explicitly verified, real M5 observations are kept local and are not
distributed in this repository. Hashes, aggregate evidence and provenance
metadata remain versioned.

From the repository root in PowerShell, after extraction:

```powershell
.\.venv\Scripts\python.exe -m retailpulse profile --select-pilot --sample
```

This inspects local files, writes SHA-256 checksums, sizes, row/column counts,
missing values, cardinalities, duplicate counts, date ranges and weekly price
coverage to `data/contracts/raw_manifest.json`. The logical source version is
`m5-accuracy-evaluation-v1`; checksums identify the actual file contents.
Timestamps are UTC, and reruns reproduce checksums for unchanged files.
Missing files produce a pending manifest, never invented statistics.
Invalid required schema fails loudly. Profiling loads the three files in memory;
allow memory for the full source tables. Identifiers use categorical dtypes.

The deterministic pilot uses the first 3 lexicographically sorted store IDs and
the first 2 sorted departments common to those stores. `--select-pilot` updates
configuration only after real source inspection. `--sample` exports the first
item in each pilot store/department locally and records its source checksum.
Generated samples under `data/sample/` are Git-ignored; only its README and
metadata-only `provenance.json` are tracked. Without real files, pilot lists
stay empty and no sample is created.

## Source contracts and joins

| Source | Grain / key | Required fields |
| --- | --- | --- |
| Calendar | `d`, unique `date` | `d`, `date`, `wm_yr_wk` |
| Prices | store × item × retail week | `store_id`, `item_id`, `wm_yr_wk`, `sell_price` |
| Sales | item × store, daily quantities in wide columns | `id`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`, `d_1`…`d_n` |

Calendar carries event names/types and SNAP indicators when present; null event
names are normal. Sales day labels join to calendar `d`; prices join on
`store_id`, `item_id`, `wm_yr_wk`. Calendar can extend beyond observed sales.
Price coverage is measured over observed sales series × observed retail weeks,
not over future calendar dates. Missing prices must not erase sales rows.
The pipeline rejects duplicate keys, missing required keys and invalid domains.

## Limitations and current evidence

M5 has no actual inventory or stockout observations. Zero sales are not proof
of zero demand or a stockout. `revenue_proxy = units × sell_price` is a proxy,
not audited revenue. Event associations do not establish causality. This is
historical retail data, not a live feed or a representative sample of all retail.

Real M5 files were inspected on 2026-10-07. The manifest records 1,969 calendar
rows, 6,841,121 price rows and 30,490 wide sales rows. The selected pilot uses
`CA_1`, `CA_2`, `CA_3` and `FOODS_1`, `FOODS_2`. Six genuine sample series were
generated locally in `data/sample/`, with every field verified against the
source CSV. The sample and full input files remain ignored and are not
distributed; source-checksum provenance metadata is retained in Git. All
automated fixtures under `tests/fixtures/` remain explicitly synthetic and
require no real dataset. See
[RP-02 evidence](evidence/rp02_gate.md) for checksums and measured findings.
