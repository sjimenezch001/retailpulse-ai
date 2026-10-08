# Build and refresh RetailPulse Power BI

The public project contains native PBIR report definitions, a portable TMDL
semantic model and no embedded observations. Use the existing RP-07 Gold
database; rebuilding Bronze/Silver/Gold or retraining LightGBM is unnecessary.
The real-data-filled `RetailPulse.pbix`, exports and Desktop caches stay ignored.

## Open locally

Run from the repository root with the validated Python 3.12 environment:

```powershell
.\.venv\Scripts\python.exe -m retailpulse export-bi
.\.venv\Scripts\python.exe dashboards/powerbi/prepare_desktop.py
```

Open `artifacts/powerbi/project/RetailPulse.pbip` in Power BI Desktop. The
preparation script copies the reusable definitions and sets the `DataFolder`
Power Query parameter **only in the ignored copy**. The parameter points at the
absolute CSV export directory on this machine. The versioned model keeps it
empty. Alternatively, open the versioned PBIP and set `DataFolder` through
Transform data > Manage parameters, taking care not to commit that local path.

Choose Home > Refresh. No sign-in, cloud workspace, DuckDB driver, AWS account
or Power BI Service publication is required. The CSV connector is built in.
Use File > Save as, choose **Power BI file (*.pbix)** and save
`dashboards/powerbi/RetailPulse.pbix`. Close and reopen that file to verify its
embedded import data. The checked report has exactly three pages.

For another refresh, rerun `export-bi`, wait for its successful completion,
then refresh Desktop. Do not refresh while exports are being published.
The command validates source contracts, keys, canonical metrics and lineage
before publishing; `manifest.json` is published last. Files use the destination
directory's permissions so Windows Desktop can read them. An interrupted
publication requires a successful rerun before refresh.

Save and close the generated Desktop project before rerunning the preparation
script: it replaces local report/model definitions while preserving caches.
Keep any intentional Desktop edits in a separate copy before regenerating.
No local data is needed for the repository's synthetic tests.

## Rebuild definitions

The committed definitions can be opened directly. Rebuilding them additionally
uses Node.js/npm and Microsoft's TOM library under ignored local tooling.
Validated versions: Desktop **2.158.1304.0**, Node **24.11.1**, report authoring
CLI **0.5.0**, Desktop Bridge CLI **1.0.0**, TOM **19.117.0**.

```powershell
npm install --prefix artifacts/rp08-tools --no-save @microsoft/powerbi-report-authoring-cli@0.5.0 @microsoft/powerbi-desktop-bridge-cli@1.0.0
```

Download the official [Microsoft.AnalysisServices 19.117.0 NuGet package](https://www.nuget.org/packages/Microsoft.AnalysisServices/19.117.0)
and extract its `lib/net8.0/*.dll` files into `artifacts/rp08-tools/tom/`.
PowerShell 7.4+ supplies a compatible .NET runtime. This tooling is local and
does not change the project's Python dependency pins.

```powershell
.\.venv\Scripts\python.exe dashboards/powerbi/build_model.py
.\dashboards\powerbi\serialize_model.ps1
.\.venv\Scripts\python.exe dashboards/powerbi/build_report.py
.\.venv\Scripts\python.exe dashboards/powerbi/validate_project.py
.\artifacts\rp08-tools\node_modules\.bin\powerbi-report-author.cmd validate dashboards/powerbi/RetailPulse.pbip --format text
```

`build_model.py` reads the checked export schema and generates TOM JSON in
ignored storage plus the measure documentation. The PowerShell script uses
Microsoft's serializer and round-trips the TMDL. `build_report.py` uses stable
page/visual identities and Microsoft's published native visual schema; it
does not create images of charts. `validate_project.py` checks page names,
49 native visual bindings, geometry, relationships and the portable parameter.
Microsoft's validator checks the actual JSON schemas and formatting.

## Desktop Bridge and live verification

Microsoft's [Desktop Bridge](https://learn.microsoft.com/en-us/power-bi/developer/agentic/power-bi-desktop-bridge-overview)
provides report state, supported reloads and genuine page capture. It does not
provide general mouse control or a PBIX writer. If disabled, the relevant
setting is File > Options and settings > Options > Security > Desktop Bridge >
Enable external tool access. Normal local authoring still works without it.

```powershell
$author = '.\artifacts\rp08-tools\node_modules\.bin\powerbi-report-author.cmd'
$project = 'artifacts/powerbi/project/RetailPulse.pbip'
& $author preview $project --host desktop --status
& $author preview $project --host desktop
```

Run Desktop and bridge commands as the same Windows user. In restricted agent
environments, Desktop must be launched outside the child-process sandbox.
Check the exact project path and `hasUnsavedChanges=false` before replacing
definitions or reloading. Save existing work first. For report-only edits use
`--reload`; for model edits use `--reload-with-model`, followed by Refresh.
Reloading definitions alone does not process import partitions.

The build was processed through the supported local Tabular Object Model API;
Home > Refresh is the equivalent normal Desktop workflow. Desktop's local
Analysis Services workspace contains `Data/msmdsrv.port.txt`. Inspect the
workspace for **this** open report; the port changes on each launch.

```powershell
.\.venv\Scripts\python.exe dashboards/powerbi/audit_data.py
.\.venv\Scripts\python.exe dashboards/powerbi/build_dax_checks.py
# Replace the example port with this report's current local model port.
.\dashboards\powerbi\validate_desktop.ps1 -Port 50000
& $author preview $project --host desktop --screenshot docs/evidence/rp08 --all-pages --scale 2
```

The live validation script uses the ADOMD client shipped with Desktop and
compares 16 aggregate DAX queries to independent SQL expectations. It never
refreshes or alters the model. The real audit assumes the documented M5 pilot
and its frozen evaluation dates. Synthetic tests remain portable.

Use Ctrl+click on native navigation buttons while editing in Desktop; normal
click works in reading mode. Slicers are page-local and can be cleared with
their eraser. Diagnostics use whole observed weeks, including partial boundary
weeks. A product or bar selection cross-filters the diagnostics page.

## Validation and data policy

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts/verify.py
git diff --check
git status
```

Public evidence consists of aggregate findings, hashes, validation outputs and
genuine dashboard screenshots. Do not commit CSV imports, M5 samples, PBIX/PBIT,
`.pbi/`, model caches or configured local paths. The [RP-08 gate](../../docs/evidence/rp08_gate.md)
records what was actually rendered, tested, saved and reopened.

Authoring references: Microsoft's [Power BI Report skill](https://learn.microsoft.com/en-us/power-bi/developer/agentic/power-bi-report-skill-overview),
[external project editing](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-external-editing)
and [TMDL serializer](https://learn.microsoft.com/en-us/analysis-services/tmdl/tmdl-how-to?view=asallproducts-allversions).
