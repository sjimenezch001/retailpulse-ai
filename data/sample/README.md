# Local M5 samples

Real M5 samples are generated locally with:

```powershell
.\.venv\Scripts\python.exe -m retailpulse profile --select-pilot --sample
```

Generated row-level samples are Git-ignored and are not distributed in this
repository while redistribution rights remain unverified. Existing local
samples and raw inputs are preserved.

Only this README and `provenance.json` are tracked here. Provenance records
the selection rule, source-manifest path and source checksum; it contains no
M5 observations. Keep other generated files local.

The clearly synthetic fixtures under `tests/fixtures/` remain available for
reproducible tests without real M5 data.
