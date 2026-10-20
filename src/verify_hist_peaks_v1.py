"""Offline checks of comparison-point display; not a Pine interpreter."""
import hashlib
import json
import math
import numpy as np
from research import ROOT, load, atr, START, END, save, jsonlines
from reference_use import readlines
from verify_hist_lifecycle import find_span


class Display:
    def __init__(self, first=True, keep=6):
        self.first, self.keep = first, keep
        self.seen = {1: set(), -1: set()}
        self.shown, self.retained = [], []

    def step(self, t, bull, bear, confirmed=True, allowed=True):
        if not confirmed or not allowed:
            return None
        for refs in self.seen.values():
            refs.intersection_update(p for p in tuple(refs) if p >= t - 100)
        if bool(bull) == bool(bear):
            return None
        side, span = (1, bull) if bull else (-1, bear)
        ref = t - span
        fresh = ref not in self.seen[side]
        self.seen[side].add(ref)
        if self.first and not fresh:
            return None
        pair = dict(id=len(self.shown)+1, direction=side, a=ref, b=t-1, t=t)
        self.shown.append(pair)
        self.retained.append(pair.copy())
        self.retained = self.retained[-self.keep:]
        return pair


def synthetic():
    d = Display()
    assert d.step(20, 10, 0, confirmed=False) is None and not d.shown
    assert d.step(20, 10, 0, allowed=False) is None and not d.shown
    assert d.step(20, 10, 10) is None and not d.shown
    first = d.step(20, 10, 0).copy()
    assert d.step(21, 11, 0) is None
    assert d.step(25, 15, 0) is None  # same reference after a gap
    assert d.shown[0] == first       # never relocate the original endpoint
    assert d.step(26, 0, 16)["direction"] == -1
    for t in range(27, 45):
        d.step(t, 6, 0)
    assert len(d.retained) == 6
    d.step(150, 0, 0)
    assert not any(d.seen.values())
    all_pairs = Display(first=False)
    assert all_pairs.step(20, 10, 0) and all_pairs.step(21, 11, 0)
    return 9


def main():
    old = (ROOT/"pine/Hist_Divergence_Line_v4_6_1.pine").read_text(encoding="utf-8")
    new = (ROOT/"pine/Hist_Divergence_Peaks_v1.pine").read_text(encoding="utf-8")
    core = old[old.index("[macdValue, signalValue, hist] ="):old.index("int previewBullLength =")]
    assert core in new, "Original MACD, pivot and formal search block changed"
    out = ROOT/"results/hist_peaks_v1"
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    for tf in ("4h", "1d"):
        df = load(tf)
        saved = readlines(ROOT/f"data/derived/indicators_signals_{tf}.jsonl.gz")
        c = df.close.to_numpy()
        hist = np.array([r["Hist_value"] for r in saved])
        aa = atr(df)
        expected = np.array([[r["Hist_bull_length"], r["Hist_bear_length"]] for r in saved])
        spans = np.zeros_like(expected)
        pivots = [[], []]
        for t in range(10, len(c)):
            p = t - 5
            for side in (0, 1):
                bull = side == 0
                ok = (c[p] <= min(c[p-5:p]) and c[p] < min(c[p+1:t+1])) if bull else (c[p] >= max(c[p-5:p]) and c[p] > max(c[p+1:t+1]))
                if ok:
                    pivots[side].insert(0, p)
                    pivots[side] = pivots[side][:20]
                spans[t, side] = find_span(c, hist, t, pivots[side], bull, 1, True)
        assert np.array_equal(spans, expected)
        models = [Display(), Display(first=False)]
        raw_count = 0
        for t in range(len(c)):
            allowed = int(df.time.iloc[t]) >= START and int(df.close_time.iloc[t]) < END and math.isfinite(aa[t]) and aa[t] > 0
            raw_count += int(allowed and bool(spans[t, 0]) != bool(spans[t, 1]))
            for model in models:
                pair = model.step(t, *map(int, spans[t]), allowed=allowed)
                if pair:
                    a, b, side = pair["a"], pair["b"], pair["direction"]
                    assert a < b < t and t-a <= 100 and b == t-1
                    assert side*(hist[b]-hist[a]) > 0 and side*(c[b]-c[a]) < 0
                    pair.update(a_time=int(df.time.iloc[a]), b_time=int(df.time.iloc[b]),
                                confirmation_close_time=int(df.close_time.iloc[t])+1,
                                a_hist=float(hist[a]), b_hist=float(hist[b]),
                                a_close=float(c[a]), b_close=float(c[b]))
        assert len(models[1].shown) == raw_count
        # Prefix replay: appending future bars must not move or rewrite old pairs.
        for cutoff in (len(c)//2, len(c)*3//4, len(c)-1):
            prefix = Display()
            for t in range(cutoff):
                allowed = int(df.time.iloc[t]) >= START and int(df.close_time.iloc[t]) < END and math.isfinite(aa[t]) and aa[t] > 0
                prefix.step(t, *map(int, spans[t]), allowed=allowed)
            keys = ("id", "direction", "a", "b", "t")
            assert [{k:p[k] for k in keys} for p in models[0].shown if p["t"] < cutoff] == prefix.shown
        jsonlines(out/f"pairs_first_reference_{tf}.jsonl.gz", models[0].shown)
        jsonlines(out/f"pairs_all_raw_{tf}.jsonl.gz", models[1].shown)
        checks.append(dict(tf=tf, bars=len(c), raw_pairs=raw_count, first_reference_pairs=len(models[0].shown),
                           exact_saved_spans=True, endpoints_verified=True, prefix_checks=3))
    result = dict(status="PASS", exact_original_core=True, core_sha256=hashlib.sha256(core.encode()).hexdigest(),
                  synthetic_checks=synthetic(), datasets=checks,
                  scope="Python replay and source equivalence; TradingView compilation/UI checked separately. No return/accuracy study.",
                  full_TradingView_export_reconciliation="NOT_PERFORMED")
    save(out/"checks.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
