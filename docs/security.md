# Security scope and verification

RetailPulse is a local portfolio demo, not an authenticated public service.
Loopback Host/Origin checks, bounded bodies/queries, four request slots, closed
Pydantic contracts, approved tools, read-only DuckDB and grounded outputs remain
enforced. Docker is synthetic-only. No external model endpoint, credential or
real-data redistribution is required.

## Dependency audit

[pip-audit](https://github.com/pypa/pip-audit) 2.10.1 scans the complete pinned
application and developer dependency graph through the public PyPI advisory API.
`--strict` makes lookup failures nonzero. `--no-deps --disable-pip` is used only
because transitive versions are already listed; it does not omit those pins.
Both lock files are supplied explicitly: the scanner's no-resolution mode did
not expand the nested `-r` include during the initial run. A post-scan assertion
now requires exact equality with every expected package/version; skips or missing
runtime entries fail even if the scanner itself returns success.
The local editable project is first-party code, covered by tests/static review,
not a PyPI distribution. The initial environment audit rejected that editable
entry, so acceptance uses the explicit complete lock and separately runs pip check.

The initial toolchain audit returned 12 records representing six unique pip advisories:

| Advisory | Severity | Affected | Remediation |
| --- | --- | --- | --- |
| [GHSA-4xh5-x5gv-qwph](https://github.com/advisories/GHSA-4xh5-x5gv-qwph) | Medium | pip 25.0.1 | pip 26.2.1 |
| [GHSA-58qw-9mgm-455v](https://github.com/advisories/GHSA-58qw-9mgm-455v) | Medium | pip 25.0.1 | pip 26.2.1 |
| [GHSA-6vgw-5pg2-w6jp](https://github.com/advisories/GHSA-6vgw-5pg2-w6jp) | Low | pip 25.0.1 | pip 26.2.1 |
| [GHSA-jp4c-xjxw-mgf9](https://github.com/advisories/GHSA-jp4c-xjxw-mgf9) | Medium | pip 25.0.1 | pip 26.2.1 |
| [GHSA-qwm4-qh6w-59xr](https://github.com/advisories/GHSA-qwm4-qh6w-59xr) | Medium | pip 25.0.1 | pip 26.2.1 |
| [GHSA-wf93-45jw-7689](https://github.com/advisories/GHSA-wf93-45jw-7689) | Medium | pip 25.0.1 | pip 26.2.1 |

Severity was retrieved from the linked GitHub advisories. No application dependency
was upgraded. The final audit has no known findings; this is not proof against
unknown vulnerabilities. OS/image-layer scanning is not claimed: no local Docker
image was built. Dependency pins are exact versions, not hash-locked wheel files;
PyPI availability and platform wheel integrity remain supply-chain dependencies.

## Secret scanning

[detect-secrets](https://github.com/Yelp/detect-secrets) 1.5.0 scans **every tracked
working-tree file**, plus non-ignored new files, with its default detectors.
No source/fixture/documentation directory is excluded. Binary handling and
heuristics are the scanner's normal behavior. Git history is not claimed scanned.
Unreadable files and links outside the repository fail the wrapper.

The reviewed baseline contains exact path/type/fingerprint exceptions: 135 public
hashes or Power BI identifiers, one deliberately invalid loopback credential test,
six synthetic CSV checksums verified against their contents, and six individually
recomputed real M5 source/Bronze provenance hashes: 148 reviewed entries in total.
The CLI enforces UTF-8 because locale decoding previously caused a Windows scan
to omit a document. See the [correction](evidence/rp11_gate.md#b-six-provenance-hashes-were-absent-from-the-reviewed-baseline).
These are false
positives with no credential severity. There are no pattern-wide entropy exclusions
or disabled detectors. The baseline is scanned too; only its exact machine-readable
fingerprint values count as metadata. New candidates fail until individually
reviewed. A regression test injects a disposable invalid token shape into an
arbitrary tracked file and verifies failure without disclosing it in the report.

Do not add a real finding to the baseline. Revoke the credential, remove it from
the working tree/history as appropriate, and rerun the scan. Runtime logs, reports,
data and model artifacts stay ignored. Read [observability](observability.md) for
the closed logging schema and redaction boundaries.

## CI and manual branch protection

The existing `validate.yml` uses immutable action revisions, `contents: read`,
untrusted `pull_request` execution without credentials, and no `pull_request_target`.
No repository secrets or cloud accounts are passed. Every critical command fails
the job on error; artifacts contain only coverage and sanitized scan/acceptance
reports. No raw runtime logs are published.

Read-only verification on **2026-10-08** confirmed the active
[Protect main - require CI ruleset](https://github.com/sjimenezch001/retailpulse-ai/rules/24699291)
for the default branch. It requires a pull request, linear history and strict
up-to-date successful `validate (ubuntu-latest)`, `validate (windows-latest)` and
`container` checks. Branch deletion and non-fast-forward updates are blocked.

The actual configuration requires **zero approving reviews** and does not require
stale-review dismissal, code-owner review, last-push approval or conversation
resolution. Do not describe these stronger review policies as enabled. The public
response did not enumerate bypass actors; it cannot substantiate a no-bypass claim.
No protection setting was changed during this verification. The successful
[PR and main runs](evidence/rp11_gate.md#verified-closure--2026-10-08) establish
the recorded CI acceptance; they do not certify new unpublished commits.
