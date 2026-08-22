from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable, Mapping

LABELS = {"correct", "incorrect", "uncertain"}

SAME_SEASON_POPULATION = {
    2021: 551,
    2022: 1047,
    2023: 1242,
    2024: 2017,
    2025: 3038,
    2026: 2636,
}
PRODUCTION_AUTO_RESOLUTIONS = 10_685


def _wilson_interval(p_hat: float, n_eff: float, z: float = 1.959963984540054) -> tuple[float, float]:
    if n_eff <= 0:
        raise ValueError("n_eff must be positive")
    denominator = 1.0 + (z * z / n_eff)
    center = (p_hat + (z * z / (2.0 * n_eff))) / denominator
    half = (
        z
        * (
            (p_hat * (1.0 - p_hat) / n_eff)
            + (z * z / (4.0 * n_eff * n_eff))
        )
        ** 0.5
        / denominator
    )
    return max(0.0, center - half), min(1.0, center + half)


def _kish_effective_n(strata: Mapping[int, tuple[int, int]]) -> float:
    """Return Kish effective n for unequal per-record audit weights.

    strata maps season -> (population_n, sample_n).
    """
    total_population = sum(population_n for population_n, _ in strata.values())
    if total_population <= 0:
        raise ValueError("population must be positive")

    sum_weight_sq = 0.0
    for population_n, sample_n in strata.values():
        if sample_n <= 0:
            raise ValueError("sample sizes must be positive")
        stratum_weight = population_n / total_population
        per_record_weight = stratum_weight / sample_n
        sum_weight_sq += sample_n * per_record_weight * per_record_weight

    return 1.0 / sum_weight_sq


def evaluate_precision_audit(
    rows: Iterable[Mapping[str, object]],
    *,
    same_season_population: Mapping[int, int] = SAME_SEASON_POPULATION,
    production_auto_resolutions: int = PRODUCTION_AUTO_RESOLUTIONS,
) -> dict[str, object]:
    audit_rows = [dict(row) for row in rows]
    if not audit_rows:
        raise ValueError("precision audit is empty")

    overall = Counter()
    by_group: dict[str, Counter[str]] = defaultdict(Counter)
    by_season: dict[int, Counter[str]] = defaultdict(Counter)

    for row in audit_rows:
        outcome = str(row.get("label_outcome") or "").strip().casefold()
        if outcome not in LABELS:
            raise ValueError(f"invalid or missing label_outcome: {outcome!r}")

        group = str(row.get("audit_group") or "").strip()
        overall[outcome] += 1
        by_group[group][outcome] += 1

        if group == "same_season_sample":
            season = int(row["portal_season"])
            by_season[season][outcome] += 1

        predicted = str(row.get("predicted_player_id") or "").strip()
        expected = str(row.get("expected_player_id") or "").strip()
        if outcome == "correct" and predicted != expected:
            raise ValueError("correct labels must copy predicted_player_id to expected_player_id")
        if outcome == "uncertain" and expected:
            raise ValueError("uncertain labels must leave expected_player_id blank")

    fallback = by_group["next_season_fallback_census"]
    fallback_n = sum(fallback.values())
    if fallback_n == 0:
        raise ValueError("fallback census is missing")

    strict_fallback = fallback["correct"] / fallback_n
    adjudicated_fallback_den = fallback["correct"] + fallback["incorrect"]
    adjudicated_fallback = (
        fallback["correct"] / adjudicated_fallback_den
        if adjudicated_fallback_den
        else None
    )
    possible_fallback = (fallback["correct"] + fallback["uncertain"]) / fallback_n

    expected_seasons = set(same_season_population)
    if set(by_season) != expected_seasons:
        raise ValueError(
            f"same-season strata mismatch: expected {sorted(expected_seasons)}, got {sorted(by_season)}"
        )

    same_population_n = sum(same_season_population.values())
    strict_same = 0.0
    possible_same = 0.0
    adjudicated_same = 0.0
    strata_for_neff: dict[int, tuple[int, int]] = {}
    season_detail: dict[str, object] = {}

    for season in sorted(same_season_population):
        counts = by_season[season]
        sample_n = sum(counts.values())
        if sample_n == 0:
            raise ValueError(f"empty same-season stratum: {season}")

        population_n = same_season_population[season]
        weight = population_n / same_population_n
        strict_rate = counts["correct"] / sample_n
        possible_rate = (counts["correct"] + counts["uncertain"]) / sample_n

        adjudicated_n = counts["correct"] + counts["incorrect"]
        adjudicated_rate = counts["correct"] / adjudicated_n if adjudicated_n else None

        strict_same += weight * strict_rate
        possible_same += weight * possible_rate
        if adjudicated_rate is not None:
            adjudicated_same += weight * adjudicated_rate

        strata_for_neff[season] = (population_n, sample_n)
        season_detail[str(season)] = {
            "population_n": population_n,
            "sample_n": sample_n,
            "correct": counts["correct"],
            "incorrect": counts["incorrect"],
            "uncertain": counts["uncertain"],
            "strict_verified_rate": strict_rate,
            "adjudicated_precision": adjudicated_rate,
            "possible_upper_bound": possible_rate,
        }

    effective_n = _kish_effective_n(strata_for_neff)
    same_ci_low, same_ci_high = _wilson_interval(strict_same, effective_n)

    fallback_correct = fallback["correct"]
    combined_strict = (
        same_population_n * strict_same + fallback_correct
    ) / production_auto_resolutions
    combined_ci_low = (
        same_population_n * same_ci_low + fallback_correct
    ) / production_auto_resolutions
    combined_ci_high = (
        same_population_n * same_ci_high + fallback_correct
    ) / production_auto_resolutions
    combined_possible = (
        same_population_n * possible_same
        + fallback["correct"]
        + fallback["uncertain"]
    ) / production_auto_resolutions

    return {
        "methodology": {
            "strict_verified": "uncertain labels are treated as not verified",
            "adjudicated": "uncertain labels are excluded from the correctness denominator",
            "same_season_estimator": "population-weighted stratified estimator across portal seasons",
            "sampling_interval": (
                "approximate 95% Wilson interval using Kish effective sample size "
                "for unequal per-record stratum weights"
            ),
            "fallback_interval": "none; all production next-season fallback matches are audited",
        },
        "audit": {
            "row_count": len(audit_rows),
            "correct": overall["correct"],
            "incorrect": overall["incorrect"],
            "uncertain": overall["uncertain"],
        },
        "fallback_census": {
            "n": fallback_n,
            "correct": fallback["correct"],
            "incorrect": fallback["incorrect"],
            "uncertain": fallback["uncertain"],
            "strict_verified_rate": strict_fallback,
            "adjudicated_precision": adjudicated_fallback,
            "possible_upper_bound": possible_fallback,
        },
        "same_season_sample": {
            "sample_n": sum(sum(c.values()) for c in by_season.values()),
            "population_n": same_population_n,
            "kish_effective_n": effective_n,
            "strict_verified_rate": strict_same,
            "strict_verified_approx_95pct_interval": [same_ci_low, same_ci_high],
            "adjudicated_precision": adjudicated_same,
            "possible_upper_bound": possible_same,
            "by_season": season_detail,
        },
        "combined_production_auto_resolutions": {
            "n": production_auto_resolutions,
            "strict_verified_rate": combined_strict,
            "strict_verified_approx_95pct_interval": [combined_ci_low, combined_ci_high],
            "possible_upper_bound": combined_possible,
            "verified_incorrect_matches_in_audit": overall["incorrect"],
        },
    }
