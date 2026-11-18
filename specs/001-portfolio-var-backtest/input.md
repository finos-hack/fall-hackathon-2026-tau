Feature number 001: Portfolio risk and VaR track record for TraderX accounts.

Who and why: A risk manager at a regulated firm needs, for each trading account, a one-day
99% Value-at-Risk figure and evidence that the model behind it can be trusted. Today TraderX
shows positions and live prices but no risk figure and no model track record.

What the user can do:
1. Pick an account and see its current one-day 99% VaR in dollars, with the positions and
   prices it was computed from.
2. See a backtest track record for that account: for each past day, the VaR forecast made
   before that day and the realised P&L, with breach days marked.
3. See a verdict on the track record: breach count, breach rate, Kupiec unconditional coverage
   test result, and Basel traffic-light zone.
4. See every number labelled with what it is based on: synthetic price history, the seed, the
   model settings, and the as-of date.

Method (fixed for this feature): filtered historical simulation with an EWMA volatility filter
(lambda 0.94) and a 250-observation pool; positions held constant over the backtest window.

Pre-registered expectations (written before any code):
- With a 250-observation pool and a linearly interpolated 1% quantile, the expected breach rate
  of a correct implementation is about 1.39%, not 1.00%; about 3.5 breaches per 250 days.
- The verdict must show both the nominal expectation (2.5) and the finite-sample expectation
  (3.5) next to the observed count.
- A hand-checkable example with a small pool must reproduce a VaR computed on paper.
- Changing any price on or after day t must not change the VaR forecast for day t.
- An unknown account returns a clear not-found result, not an empty risk figure.

Constraints: price history is synthetic, generated from a fixed seed, and labelled synthetic
everywhere. The existing TraderX screens and APIs are not changed. Tests and an independent
second implementation are written by a different AI model from the spec only.

Out of scope: real market data, expected shortfall, multi-day horizons, other confidence levels,
intraday recalculation, changes to the Angular front end.