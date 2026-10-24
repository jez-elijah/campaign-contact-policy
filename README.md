# Campaign Contact-Policy Simulation

A small, tested Python project that models how a **Contact Policy** (consent, quiet hours, frequency caps, cooldowns) changes the outcomes of multi-channel marketing campaigns, and how **KPI monitoring** can flag problems week by week.

> **All data is synthetic.** Customers, consent, campaigns and the fictional "Example Bank" policy are invented for this project. Customer behaviour (response, opt-out, complaint) comes from an *assumed* outcome model, so the results show how the policy mechanics behave under those assumptions. They are **not** empirical findings about real customers.

## What it does

| Part | Description |
|---|---|
| `policy.py` | Rule engine: returns allow/suppress with a reason code. Rules are checked in a fixed order: consent, complaint cooldown, quiet hours, minimum gap, per-channel weekly cap, per-channel monthly cap, total weekly cap. |
| `config/policy.yaml` | Policy and monitoring thresholds as validated config (Pydantic), so rules change without code changes. |
| `config/campaigns.yaml` | Five overlapping campaigns across SMS, email and push, split into `portfolio` (account-management offers) and `usage` (card-usage promos). Portfolio campaigns take priority on the same day. |
| `simulate.py` | Day-by-day simulation of 56 days under three sending modes: `naive` (send everything), `consent_only`, `full_policy`. |
| `kpi.py` | Weekly KPIs (sent, suppression rate, response / opt-out / complaint rate), suppression breakdown by rule, and threshold alerts. |
| `api.py` | Stateless FastAPI service: `POST /check-contact` returns whether a proposed contact is allowed and why; `GET /policy`, `GET /health`. |

## Quick start

```bash
pip install -r requirements.txt
PYTHONPATH=src python -m ccp.cli --customers 5000 --seed 42   # writes reports to outputs/
pytest -q
PYTHONPATH=src uvicorn ccp.api:app --reload                   # API docs at /docs
```

Example API call:

```bash
curl -X POST localhost:8000/check-contact -H 'content-type: application/json' -d '{
  "consent": {"sms": true, "email": true, "push": true},
  "history": [{"day": 9, "hour": 12, "channel": "push"}],
  "proposed": {"day": 10, "hour": 12, "channel": "sms"}
}'
# {"allowed": false, "reason": "min_gap", "policy_version": 1}
```

## Results (5,000 synthetic customers, 56 days, seed 42)

| Mode | Contacts sent | Responses | Response rate | Opt-outs | Complaints |
|---|---:|---:|---:|---:|---:|
| naive | 344,684 | 3,568 | 1.04% | 5,652 | 3,074 |
| consent_only | 206,235 | 4,185 | 2.03% | 2,537 | 778 |
| full_policy | 77,791 | 3,994 | 5.13% | 373 | 66 |

Versus `consent_only`, the full policy sent **62% fewer contacts**, produced **85% fewer opt-outs** and **92% fewer complaints**, at the cost of **4.6% fewer total responses**. Versus `naive`, it produced 12% *more* responses from 77% fewer contacts, because the assumed model penalises over-contact (fatigue).

**Robustness:** repeating with 2,000 customers on seeds 1 to 5, full policy versus consent-only gave contacts -62% to -62.5%, opt-outs -85% to -86%, complaints -88% to -92%, and responses -1.9% to -8.6%. The direction and rough size held across seeds, but all five runs share the same outcome-model assumptions.

**Monitoring finding:** the `max_suppression_rate` alert (60%) fired in every one of the 8 weeks under the full policy, with 75% to 79% of attempted contacts suppressed. The alert was not tuned after seeing the data. It reads as a signal that the campaign calendar is far more aggressive than the policy allows (most suppressions: no consent 42%, quiet hours 24%, minimum gap 22%), not as a policy failure.

## Limitations

- The outcome model (response, fatigue, opt-out and complaint probabilities in `OutcomeModel`) is assumed, not fitted to real data. Changing it changes the numbers.
- Time is simulated at day and hour granularity with no time zones, delivery failures or bounces.
- The naive baseline is a deliberately extreme "blast everyone every campaign" scenario (about 69 contacts per customer over 8 weeks).
- Customers are independent; there is no learning, A/B testing or channel preference modelling.
- The API is stateless: the caller supplies contact history. There is no database or authentication.

## Tests

42 tests cover each rule and its boundary conditions, rule ordering, determinism, KPI calculations and alert logic, API validation, and simulation invariants. The invariant tests check that, in `full_policy` runs, no sent contact ever breaks consent, quiet hours, minimum gap, any cap or the complaint cooldown. CI (GitHub Actions) runs lint and tests on Python 3.10 to 3.12 and smoke-runs the simulation.

## Layout

```
config/            policy.yaml, campaigns.yaml
src/ccp/           models, generate, policy, simulate, kpi, api, cli
tests/             policy, generate, simulate, kpi, api, config
.github/workflows/ ci.yml
```
