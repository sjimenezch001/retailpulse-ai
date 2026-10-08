# Portfolio claims and evidence

Reviewed on 2026-10-08. English is canonical. This is a personal portfolio project,
not an employer engagement, customer deployment or measured commercial intervention.
RP-12 AWS is optional and deferred. The [RP-13 gate](evidence/rp13_gate.md) distinguishes
packaging from independent human verification and release publication.

## Claim-to-evidence map

| Claim | Actual source | Interpretation and limit |
| --- | --- | --- |
| 4,530,250 observed pilot units | [Independent aggregate acceptance](evidence/rp09_real_acceptance.json), `full_units` example; [RP-10 API](evidence/rp10/real_api.json), overview | Real M5, three California stores and two food departments; 2011-01-29–2016-05-22. Not present-day sales. |
| CA_1 sold 25,307 units in April 2016 | [Acceptance](evidence/rp09_real_acceptance.json), `april_store`; [live API](evidence/rp10/real_api.json) | Aggregate result from Gold. The earlier acceptance file contains fallback providers; it establishes numerical reconciliation, not live-model validation. |
| LightGBM WMAPE 74.825958% vs rolling mean 79.482353% | [Aggregate metrics CSV](evidence/rp07_metrics.csv), `test,overall,all`; [model card](model_card.md#final-one-time-test) | Fixed-origin 28-day test, 51,576 observations. A 4.656394 percentage-point reduction; no revenue-impact claim. |
| MAE improves, RMSE worsens | [Same test row](evidence/rp07_metrics.csv) | MAE 1.268324 vs 1.347252; RMSE 2.431177 vs 2.361194. Large errors remain a weakness. |
| Selection used validation only | [Freeze chronology and leakage evidence](evidence/rp07_gate.md#evidence-of-isolation-and-freeze), [protocol](modeling.md) | Three predeclared candidates; final test opened once. No post-test tuning claimed. |
| 36 live-evaluation expected outcomes passed | [Final live evaluation](evidence/rp09_live_evaluation.json), `total`, `passing`, `provider_usage`, `live_model` | 22 validated Ollama calls, 14 preflight outcomes, zero fallback. Twenty grounded answers and 16 correct refusals/clarifications; not 36 model-generated answers or universal accuracy. |
| 254 tests and 88.15% coverage, minimum 85% | [Corrected RP-11 results](evidence/rp11/ci_corrections.json), `tests`, `coverage`; [current RP-13 validation](evidence/rp13_gate.md) | Combined lines/branches across `src/retailpulse` and `app`; scoped mypy is not whole-project type coverage. |
| Genuine Windows/Linux/Docker CI succeeded | [Corrected PR](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/37732985345), [post-merge main](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/37734804078), [closure](evidence/rp11_gate.md#verified-closure--2026-10-08) | Applies to `bb2a0c9` and `593dc50`. No remote pass claimed for unpublished RP-13 commits. |
| Portable mode needs no M5 or Ollama | [Packaged snapshot manifest](../src/retailpulse/api/synthetic/manifest.json), [isolated reproduction](evidence/rp13_gate.md#clean-environment-reproduction) | 1,386 total synthetic units; 378 for SYN_A. The simulated forecast series is demonstration content, not trained-model evidence. |

Live RP-09 latency was a median **8,398.5 ms** and maximum **12,156 ms** for
successful provider selections, excluding discovery. The 36-case end-to-end
median was **3,707.073 ms**, including preflight and independent reconciliation.
The model was already loaded; a separate cold request took **14,594 ms**. See
[live evaluation](evidence/rp09_live_evaluation.json) and
[diagnostics](evidence/rp09_live_ollama.md). These are local observations, not
production latency guarantees or edited video timings.

## Genuine screenshot gallery

These existing captures were reviewed directly. No figures or answers were inserted
into images. All show real browser/Desktop renders and aggregate historical data.

| View | Capture | Acceptance |
| --- | --- | --- |
| Web Overview, light / English | [Open screenshot](evidence/rp10_ui/overview_light_en.png) | [UI browser report](evidence/rp10_ui/browser.json) |
| Forecast comparison, dark / Spanish | [Open screenshot](evidence/rp10_ui/forecast_dark_es.png) | Same report; RMSE trade-off remains visible |
| Structured assistant answer, dark / English presentation | [Open screenshot](evidence/rp10_ui/assistant_dark_en.png) | A Spanish question remains in the history after switching the UI; genuine provider and timing are preserved |
| Overview, dark / Spanish | [Open screenshot](evidence/rp10_ui/overview_dark_es.png) | Same report; session language and theme validation |
| Power BI Executive Overview | [Open screenshot](<evidence/rp08/Executive Overview.png>) | [Desktop, save/reopen and DAX checks](evidence/rp08_gate.md) |

The [150-second script](web_demo.md#150-second-product-walkthrough) and
[English captions](demo_captions.en.srt) accompany the completed local English
recording, whose content and presentation the owner approved on 2026-10-08.
Its original bytes are preserved. [Spanish captions](demo_captions.es.srt) now
accompany a genuine Spanish-interface recording; [Brazilian Portuguese captions](demo_captions.pt-BR.srt)
accompany a separate export of the English walkthrough. Both were fully decoded
and inspected across all six scenes and 14 caption cues per export; see
[localization evidence](evidence/rp13/localization.json) and
[recording status](evidence/rp13_gate.md#demo-localization--2026-10-08).
The videos remain local and ignored. This does not establish independent human
quick-start verification, which is PENDING and deferred by the owner, or authorize
public hosting, a license, a version change or a release.

## Scope of the proof

The router first establishes an approved scope; optional Ollama confirms that
structured selection; approved tools retrieve figures; deterministic rendering
presents them. [Code](../src/retailpulse/agent/orchestrator.py) and
[safety contract](agent_safety.md) establish this boundary. Neither provider text
nor unrestricted SQL supplies the displayed numbers.

Historical M5, synthetic fixtures, prior live-model validation and deterministic
offline operation are separate evidence categories. No measured commercial
revenue uplift, actual inventory, production customers or AWS deployment is claimed.
Real rows, model binaries, populated databases and data-filled PBIX are local-only.
The owner still needs to choose a code license; competition-data rights are separate.
