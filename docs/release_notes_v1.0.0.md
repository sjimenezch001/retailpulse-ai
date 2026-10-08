# Draft release notes — target v1.0.0

**PREPARED — NOT PUBLISHED.** No tag exists as a result of RP-13 work.
Package metadata, API contract version and version assertions remain `0.1.0`.
Publication requires the [release checklist](release_checklist.md), an owner
license decision and explicit approval for the coordinated version/tag steps.

## Scope

RetailPulse AI packages a personal portfolio around reproducible retail demand
analytics: M5 source contracts, Bronze/Silver/Gold, fixed-origin forecasting,
local MLflow, a native Power BI project, approved assistant tools and a bilingual
FastAPI/Streamlit demo. The portable synthetic mode needs no competition download,
Ollama installation, training or cloud account.

RP-13 adds the recruiter README, Portuguese summary, implemented architecture,
claim-to-evidence map, public demo walkthrough/captions and acceptance
evidence. It does not add product features or redesign the application.

## Measured evidence

- [Historical pilot](evidence/rp09_real_acceptance.json): 4,530,250 observed units.
- [Frozen model](model_card.md): test WMAPE 74.825958% vs 79.482353% rolling mean;
  MAE improves and RMSE worsens. No measured business uplift claimed.
- [Live assistant evaluation](evidence/rp09_live_evaluation.json): 36 expected
  outcomes, 22 validated Ollama calls, 14 preflight outcomes, zero fallback.
- [Corrected RP-11](evidence/rp11_gate.md): 254 tests, 88.15% combined coverage,
  85% minimum; genuine Windows/Linux/Docker remote acceptance.
- [RP-13 acceptance](evidence/rp13_gate.md): current reproduction, validation,
  video status and unresolved human checks. New local commits have no remote CI claim.

## Distribution and limitations

Versioned material contains source, synthetic fixtures, definitions, screenshots
and aggregate evidence. Real M5 rows, populated DuckDB files, model binaries,
MLflow artifacts, data-filled PBIX and the large demo MP4 remain local and ignored.
Follow [real-data instructions](web_demo.md#real-data-build-and-entry-points) and
the [Power BI build guide](../dashboards/powerbi/BUILD_GUIDE.md) to generate them.

The snapshot is historical, has no actual inventory, and does not establish
causality or revenue impact. The assistant is bounded and stateless; this is a
local application without public-service authentication. Synthetic forecast
figures are simulated. RP-12 AWS is optional and deferred.

No root LICENSE file or `[project].license` declaration was found. The code owner
must choose and approve a license before representing this as licensed open-source
distribution. No license has been invented. M5 competition rules are a separate
data-permission boundary; public availability does not establish redistribution rights.
