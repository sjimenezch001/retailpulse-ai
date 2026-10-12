# Minimal independent quick-start check

Status: **PREPARED / NOT RUN BY AN INDEPENDENT PERSON**.
This is a short handoff for another person, not a new implementation sprint.
The [existing automated reproduction](evidence/rp13/reproduction.json) already
passed. Reuse its supported synthetic launch; no M5, Ollama, AWS, Power BI
Desktop, training, recording or Docker is required for this check.

## Preparation

Have an independent person run the steps. Another automated run by the owner or
assistant does not satisfy independent human acceptance.

Use another person's machine or a separate clean checkout and new Python 3.12
environment. Installation needs internet for pinned packages. Ask the owner
which candidate revision to check and record the actual `git rev-parse HEAD`.
Unpublished local changes cannot be verified by cloning the older public main.
If the approved candidate is not published, the owner can supply a sanitized
candidate checkout; do not copy their `.venv`, `.env`, data, models or artifacts.

Choose two unused ports. This example uses **8023 / 8523**; occupied ports are a
STOP, not permission to kill another person's demo. Expect roughly 10 minutes
of interaction after installation; the prior fresh install took about 10 minutes,
but installation time depends on the machine and network.

## Run once — Windows PowerShell

For an authorized, published candidate, clone to a new directory:

```powershell
git clone https://github.com/sjimenezch001/retailpulse-ai.git retailpulse-independent-check
cd retailpulse-independent-check
git rev-parse HEAD
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe scripts/tasks.py setup
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic --api-port 8023 --ui-port 8523
```

Compare the printed revision with the owner's nominated candidate before setup.
If using an owner-supplied checkout, start at `git rev-parse HEAD` in that checkout;
record any uncommitted differences and do not call it an immutable commit test.
If `py` is unavailable, use an explicitly verified Python 3.12 executable to
create the environment. Do not reuse the owner's existing environment.

In a second terminal, these read-only local requests should return successfully:

```powershell
Invoke-RestMethod http://127.0.0.1:8023/health
Invoke-RestMethod http://127.0.0.1:8023/ready
```

For this explicit deterministic demo, `/ready` may report `degraded` when
optional Ollama discovery is unavailable. Require `dataset_available`,
`synthetic_available` and `deterministic_available` to be true. An unavailable
dataset is a failure; optional Ollama availability is not required for this check.

Open [Streamlit](http://127.0.0.1:8523) and
[API documentation](http://127.0.0.1:8023/docs). Check:

- Overview renders **1,386 synthetic units** and its chart.
- Forecast renders its illustrative comparison and synthetic-data notice;
  these figures are not real LightGBM performance.
- Ask RetailPulse accepts **How many units did SYN_A sell during all observed dates?**
  and returns **378 synthetic units**, with source/grounding and an explicitly
  deterministic provider. Do not count this as live Ollama validation.
- Language/theme controls work and no traceback appears.

Press physical **Ctrl+C** in the original launcher terminal. Both owned servers
should stop. In the second terminal:

```powershell
Get-NetTCPConnection -LocalPort 8023,8523 -State Listen -ErrorAction SilentlyContinue
```

No listener should remain on either selected port. If shutdown fails, record
the failure and inform the owner; do not terminate unrelated processes.

## Record an actual outcome

All items remain unchecked until the independent tester performs them:

- [ ] Date, OS, Python version and tested revision recorded.
- [ ] New environment installed; pip check passed.
- [ ] Health/readiness successful; Overview and Forecast rendered.
- [ ] Exact 378-unit answer and deterministic/synthetic labels confirmed.
- [ ] Physical Ctrl+C stopped both servers and released selected ports.
- [ ] Failures, timings and screenshots recorded only if actually observed.

Keep the tester's identity/consent private unless they approve publication.
Do not include credentials, local profile paths or real data. A PASS applies to
the tested revision and machine; it does not complete a release or validate
unpublished AWS documentation. See the [RP-13 gate](evidence/rp13_gate.md).
