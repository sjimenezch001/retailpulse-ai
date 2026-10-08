# Synthetic demonstration glossary

## Synthetic source

This mode contains explicitly synthetic, repository-authored observations.
Model comparison series are illustrative and do not measure a trained model.
No real M5 observations or real model scores appear in this corpus.

## units

units means observed nonnegative demand. Sum units over an explicit period
and selected synthetic stores or departments.

## revenue_proxy and prices

revenue_proxy is units multiplied by selling price, not audited revenue.
Its aggregate is unknown if any selected price is missing.
known_revenue_proxy sums only priced observations; price_coverage is the
share of observations with a known price. Missing prices remain unknown.

## WMAPE, MAE and RMSE

WMAPE is summed absolute forecast error divided by summed absolute actual
units, never an average of subgroup percentages. A zero denominator is
undefined. MAE is mean absolute error; RMSE is root mean squared error.
Synthetic predictions illustrate these definitions, not operational accuracy.

## rolling_7d, rolling_28d and spikes

rolling_7d and rolling_28d average preceding observations, excluding the
current day. They are not additive across dates. demand_spike_flag is a
heuristic review signal, never proof of causality or inventory availability.

## data_freshness

data_freshness counts calendar days between the final observed sales date
and the explicit snapshot as-of date. This is a global dataset measure.
