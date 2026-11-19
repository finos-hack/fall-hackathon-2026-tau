```python file=tests/unit/test_unit_calculation_contract.py
import math
import random
import struct

import pytest

from risk_service.core import (
    InsufficientHistoryError,
    Params,
    ZeroVolatilityError,
    backtest,
    basel_zone,
    ewma_sigmas,
    finite_sample_rate,
    interp_quantile,
    kupiec,
    pnl_series,
    var_forecasts,
)


def test_v1_hand_example_and_changed_day_variant():
    params = Params(lam=0.94, pool=5, warmup=2, p=0.01)
    closes = {"XYZ": [100, 101, 99, 100, 97, 98, 99, 96, 93]}

    pnl = pnl_series(closes, {"XYZ": 10})
    # spec V1
    assert pnl == [10, -20, 10, -30, 10, 10, -30, -30]

    result = backtest(pnl, params)
    # calculation-api.md Indexing convention
    assert len(result.rows) == 1
    # spec V1
    assert result.rows[0].t == 8
    # spec V1, SC-003
    assert abs(result.rows[0].forecast_var - 33.3085) <= 0.0001
    # spec V1
    assert result.rows[0].pnl == -30
    # spec V1
    assert result.rows[0].breach is False

    variant_closes = {"XYZ": [100, 101, 99, 100, 97, 98, 99, 96, 92]}
    variant = backtest(pnl_series(variant_closes, {"XYZ": 10}), params)

    # spec V1 variant
    assert struct.pack("!d", variant.rows[0].forecast_var) == struct.pack(
        "!d", result.rows[0].forecast_var
    )
    # spec V1 variant
    assert variant.rows[0].pnl == -40
    # spec V1 variant
    assert variant.rows[0].breach is True


def _ewma_consistent_pnl(seed, params, observations):
    rng = random.Random(seed)
    pnl = [rng.gauss(0.0, 1.0) for _ in range(params.warmup)]
    sigma_squared = sum(value * value for value in pnl) / params.warmup

    for _ in range(params.warmup + 1, observations + 1):
        value = math.sqrt(sigma_squared) * rng.gauss(0.0, 1.0)
        pnl.append(value)
        sigma_squared = (
            params.lam * sigma_squared + (1.0 - params.lam) * value * value
        )

    return pnl


def test_v2_known_answer_coverage_uses_preregistered_seeded_series():
    params = Params(lam=0.94, pool=250, warmup=100, p=0.01)
    observations = 600
    breaches = 0

    for seed in range(400):
        pnl = _ewma_consistent_pnl(seed, params, observations)
        forecasts = var_forecasts(pnl, params)

        for day in range(351, 601):
            if pnl[day - 1] < -forecasts[day]:
                breaches += 1

    breach_rate = breaches / 100_000

    # spec V2, SC-003
    assert 0.0124 <= breach_rate <= 0.0154


def test_v4_price_perturbations_cannot_change_forecasts_for_their_day():
    params = Params(lam=0.94, pool=250, warmup=100, p=0.01)
    closes = [100.0 + 0.17 * day + 0.31 * (day % 7) for day in range(601)]
    original_pnl = pnl_series({"XYZ": closes}, {"XYZ": 10})
    original_forecasts = var_forecasts(original_pnl, params)
    perturbations = random.Random(20261117)

    for day in (351, 475, 600):
        changed_closes = list(closes)
        for close_index in range(day, len(changed_closes)):
            changed_closes[close_index] *= perturbations.uniform(0.5, 1.5)

        changed_pnl = pnl_series({"XYZ": changed_closes}, {"XYZ": 10})
        changed_forecasts = var_forecasts(changed_pnl, params)

        # spec V4, SC-005
        assert struct.pack("!d", changed_forecasts[day]) == struct.pack(
            "!d", original_forecasts[day]
        )


@pytest.mark.parametrize(
    "breaches, expected_lr, expected_p_value, expected_reject, expected_direction, expected_zone",
    [
        (0, 5.0252, 0.0250, True, "too_few", "green"),
        (1, 1.1765, 0.2781, False, None, "green"),
        (2, 0.1084, 0.7419, False, None, "green"),
        (3, 0.0949, 0.7580, False, None, "green"),
        (4, 0.7691, 0.3805, False, None, "green"),
        (5, 1.9568, 0.1619, False, None, "amber"),
        (6, 3.5554, 0.0594, False, None, "amber"),
        (7, 5.4970, 0.0190, True, "too_many", "amber"),
        (10, 12.9555, 0.0003, True, "too_many", "red"),
    ],
)
def test_v5_kupiec_and_basel_reference_table(
    breaches,
    expected_lr,
    expected_p_value,
    expected_reject,
    expected_direction,
    expected_zone,
):
    result = kupiec(breaches, T=250, p=0.01)

    # spec V5
    assert abs(result.lr - expected_lr) <= 0.00005
    # spec V5
    assert abs(result.p_value - expected_p_value) <= 0.00005
    # spec V5
    assert result.reject is expected_reject
    # spec V5
    assert result.direction == expected_direction
    # spec V5
    assert basel_zone(breaches) == expected_zone


def test_indexing_current_forecast_and_determinism():
    params = Params(lam=0.94, pool=2, warmup=2, p=0.01)
    pnl = [1.0, -2.0, 3.0, -4.0, 5.0]

    first = var_forecasts(pnl, params)
    second = var_forecasts(pnl, params)
    result = backtest(pnl, params)

    # calculation-api.md Indexing convention
    assert list(first) == [5, 6]
    # calculation-api.md Indexing convention
    assert [row.t for row in result.rows] == [5]
    # calculation-api.md Indexing convention
    assert result.current_var == first[6]
    # calculation-api.md Guarantees the tests may rely on, Determinism
    assert first == second


def test_pnl_series_uses_spec_day_numbers_sorted_tickers_and_missing_ticker_keyerror():
    closes = {
        "A": [10.0, 11.0],
        "B": [20.0, 21.0],
        "C": [30.0, 31.0],
    }
    positions = {"C": 1.0, "B": -1.0e16, "A": 1.0e16}

    result = pnl_series(closes, positions)

    # calculation-api.md pnl_series, M2
    assert result == [1.0]

    # calculation-api.md pnl_series
    with pytest.raises(KeyError):
        pnl_series({"A": [1.0, 2.0]}, {"MISSING": 1.0})


def test_parameters_quantile_edge_and_no_flooring_are_honoured():
    params = Params(lam=0.5, pool=2, warmup=1, p=0.5)
    pnl = [1.0, 3.0, 2.0]

    sigmas = ewma_sigmas(pnl, params)
    forecasts = var_forecasts(pnl, params)

    # calculation-api.md Guarantees the tests may rely on, Parameters are honoured; spec M3
    assert sigmas[3] == math.sqrt(5.0)
    # calculation-api.md Guarantees the tests may rely on, Parameters are honoured; spec M4-M5
    assert forecasts[4] == -math.sqrt(4.5) * ((3.0 + 2.0 / math.sqrt(5.0)) / 2.0)

    # calculation-api.md M4, unsorted input allowed
    assert interp_quantile([5.0, 1.0, 4.0, 2.0, 3.0], 0.01) == 1.04
    # calculation-api.md Guarantees the tests may rely on, Quantile edge
    assert interp_quantile([4.0, 1.0], 1.0) == 4.0
    # calculation-api.md Guarantees the tests may rely on, No flooring
    assert forecasts[4] < 0.0


def test_backtest_requires_strict_inequality_for_a_breach():
    params = Params(lam=0.5, pool=1, warmup=1, p=0.01)
    equal_to_threshold_pnl = 2.0 * math.sqrt(2.5)
    result = backtest([1.0, 2.0, equal_to_threshold_pnl], params)
    row = result.rows[0]

    # calculation-api.md Backtest, FR-005
    assert row.pnl == -row.forecast_var
    # calculation-api.md Backtest, FR-005
    assert row.breach is False


def test_named_errors_are_raised_at_the_contract_conditions():
    insufficient = Params(lam=0.94, pool=2, warmup=2, p=0.01)

    # calculation-api.md var_forecasts, InsufficientHistoryError
    with pytest.raises(InsufficientHistoryError):
        var_forecasts([1.0, 2.0, 3.0], insufficient)

    # calculation-api.md ewma_sigmas, ZeroVolatilityError; spec M3
    with pytest.raises(ZeroVolatilityError):
        ewma_sigmas([0.0, 0.0, 1.0, -1.0], insufficient)

    # calculation-api.md var_forecasts, ZeroVolatilityError; spec M3
    with pytest.raises(ZeroVolatilityError):
        var_forecasts([0.0, 0.0, 1.0, -1.0], insufficient)


def test_finite_sample_rate_and_remaining_basel_boundary():
    # spec M7
    assert finite_sample_rate(250, 0.01) == 3.49 / 251.0
    # calculation-api.md basel_zone; FR-007
    assert basel_zone(9) == "amber"
```

Open questions

- The calculation contract requires equal close-list lengths but does not specify which exception is raised for unequal lengths.
- The contract does not define behavior for an empty quantile pool, out-of-range quantile probabilities, or P&L shorter than the EWMA warm-up outside `var_forecasts`’ documented insufficient-history condition.