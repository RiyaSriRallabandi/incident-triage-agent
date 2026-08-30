"""Paired significance tests for variant-vs-baseline comparisons.

- McNemar's exact test on the binary "correct / not correct" label, paired by
  scenario run-slot.
- Wilcoxon signed-rank on a paired continuous metric (e.g. confidence).

With ~30 paired observations, power is modest: report the effect (the delta) with
the p-value and treat p as supporting evidence, not a verdict.
"""

from __future__ import annotations

from pydantic import BaseModel
from scipy.stats import binomtest, wilcoxon


class PairedTest(BaseModel):
    metric: str
    test: str
    n: int
    baseline: float
    variant: float
    delta: float
    statistic: float | None
    p_value: float | None
    note: str = ""


def _paired_keys(a: dict[str, object], b: dict[str, object]) -> list[str]:
    return sorted(set(a) & set(b))


def mcnemar_correct(
    baseline_labels: dict[str, str], variant_labels: dict[str, str], *, metric: str = "correct_rate"
) -> PairedTest:
    """Exact McNemar's test on 'label == "correct"', paired by key."""
    keys = _paired_keys(baseline_labels, variant_labels)
    b = [baseline_labels[k] == "correct" for k in keys]
    v = [variant_labels[k] == "correct" for k in keys]

    only_baseline = sum(1 for x, y in zip(b, v, strict=True) if x and not y)
    only_variant = sum(1 for x, y in zip(b, v, strict=True) if y and not x)
    discordant = only_baseline + only_variant

    if discordant == 0:
        stat, p = 0.0, 1.0
        note = "no discordant pairs"
    else:
        res = binomtest(only_variant, discordant, 0.5, alternative="two-sided")
        stat, p = float(only_variant), float(res.pvalue)
        note = (
            f"{only_variant} improved, {only_baseline} regressed, of {discordant} discordant pairs"
        )

    return PairedTest(
        metric=metric,
        test="mcnemar_exact",
        n=len(keys),
        baseline=round(sum(b) / len(keys), 3) if keys else 0.0,
        variant=round(sum(v) / len(keys), 3) if keys else 0.0,
        delta=round((sum(v) - sum(b)) / len(keys), 3) if keys else 0.0,
        statistic=stat,
        p_value=round(p, 4),
        note=note,
    )


def wilcoxon_paired(
    baseline_values: dict[str, float],
    variant_values: dict[str, float],
    *,
    metric: str,
) -> PairedTest:
    keys = _paired_keys(baseline_values, variant_values)
    diffs = [variant_values[k] - baseline_values[k] for k in keys]

    nonzero = [d for d in diffs if d != 0]
    if not nonzero:
        stat, p, note = 0.0, 1.0, "all paired differences are zero"
    else:
        res = wilcoxon(diffs, zero_method="wilcox", alternative="two-sided")
        stat, p, note = float(res.statistic), float(res.pvalue), f"{len(nonzero)} non-zero pairs"

    mean_b = sum(baseline_values[k] for k in keys) / len(keys) if keys else 0.0
    mean_v = sum(variant_values[k] for k in keys) / len(keys) if keys else 0.0
    return PairedTest(
        metric=metric,
        test="wilcoxon_signed_rank",
        n=len(keys),
        baseline=round(mean_b, 3),
        variant=round(mean_v, 3),
        delta=round(mean_v - mean_b, 3),
        statistic=stat,
        p_value=round(p, 4),
        note=note,
    )
