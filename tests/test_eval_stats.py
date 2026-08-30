from triage.eval.stats import mcnemar_correct, wilcoxon_paired


def test_mcnemar_all_improvements_is_significant():
    base = {f"s{i}__run1": "incorrect" for i in range(12)}
    variant = {f"s{i}__run1": "correct" for i in range(12)}
    r = mcnemar_correct(base, variant)
    assert r.baseline == 0.0
    assert r.variant == 1.0
    assert r.delta == 1.0
    assert r.p_value < 0.01
    assert "12 improved" in r.note


def test_mcnemar_no_change_is_not_significant():
    labels = {f"s{i}__run1": "correct" if i % 2 else "incorrect" for i in range(10)}
    r = mcnemar_correct(labels, dict(labels))
    assert r.delta == 0.0
    assert r.p_value == 1.0
    assert "no discordant pairs" in r.note


def test_mcnemar_pairs_by_key():
    base = {"a": "correct", "b": "incorrect", "c": "correct"}
    variant = {"a": "correct", "b": "correct", "c": "incorrect"}  # b improves, c regresses
    r = mcnemar_correct(base, variant)
    assert r.n == 3
    assert r.delta == 0.0  # one up, one down
    assert "1 improved, 1 regressed" in r.note


def test_wilcoxon_detects_a_consistent_shift():
    base = {f"s{i}": 0.5 for i in range(15)}
    variant = {f"s{i}": 0.8 for i in range(15)}
    r = wilcoxon_paired(base, variant, metric="confidence")
    assert r.delta == 0.3
    assert r.p_value < 0.01


def test_wilcoxon_all_equal_is_not_significant():
    vals = {f"s{i}": 0.6 for i in range(8)}
    r = wilcoxon_paired(vals, dict(vals), metric="confidence")
    assert r.delta == 0.0
    assert r.p_value == 1.0
    assert "zero" in r.note
