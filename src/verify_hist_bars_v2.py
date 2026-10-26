"""Verify the original-rule Hist column adapter without simulating Pine execution.

The saved-data comparison covers Close pivots, period 5, 10 pivots, 100 bars,
Regular divergence, MACD 12/26/9 and dontconfirm=False only.  It has no date,
ATR, event-lock, first-occurrence or trade-outcome filtering.  Source identity
protects the original optional paths; it is not runtime validation of them.
MPL-2.0; original divergence detection copyright LonesomeTheBlue.
"""
import hashlib
import json
import re

import numpy as np

from reference_use import readlines
from research import ROOT, jsonlines, load, save
from verify_hist_lifecycle import find_span


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_checks():
    original_path = ROOT / "pine/original_user_source.pine"
    product_path = ROOT / "pine/Hist_Divergence_Bars_v2.pine"
    original = original_path.read_text(encoding="utf-8-sig")
    product = product_path.read_text(encoding="utf-8-sig")
    start = "// keep values and positions of Pivot Highs/Lows in the arrays"
    end = "// calculate 4 types of divergence"
    core = original[original.index(start):original.index(end)]
    assert core in product, "Original pivot arrays, insertion and search functions changed"
    assert product.count(core) == 1, "Original search block must appear once"
    exact_lines = (
        'float ph = pivothigh((source == "Close" ? close : high), prd, prd)',
        'float pl = pivotlow((source == "Close" ? close : low), prd, prd)',
        '[macd, signal, deltamacd] = macd(close, 12, 26, 9)',
    )
    for line in exact_lines:
        assert line in original and line in product, f"Original declaration changed: {line}"
    # Strip comments and string values so explanatory text is not mistaken for code.
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', product)
    code = re.sub(r"//[^\n]*", "", code)
    for forbidden in ("active", "trackingStart", "bufferATR", "confirmationPrice", "invalidationPrice"):
        assert re.search(rf"\b{forbidden}\b", code) is None, f"Unexpected lifecycle state: {forbidden}"
    assert re.search(r"\batr\s*\(", code) is None, "ATR must not gate original divergence"
    # Top-level direct expressions rule out the previous event lock, close gate,
    # conflicting-direction exclusion and first-occurrence deduplication.
    expected_assignments = (
        ("bullLength", r"positive_regular_positive_hidden_divergence\(deltamacd,\s*1\)"),
        ("bearLength", r"negative_regular_negative_hidden_divergence\(deltamacd,\s*1\)"),
        ("rawBull", r"bullLength\s*>\s*0"),
        ("rawBear", r"bearLength\s*>\s*0"),
        ("columnColor", r"rawBear\s*\?\s*bearColor\s*:\s*rawBull\s*\?\s*bullColor\s*:\s*normalColor"),
    )
    for name, expression in expected_assignments:
        pattern = rf"^(?:(?:int|bool|color)\s+)?{name}\s*=\s*{expression}\s*$"
        assert re.search(pattern, code, re.MULTILINE), f"Direct original-rule assignment missing: {name}"
    assert re.search(r"alertcondition\(\s*rawBull\s*,", code), "Independent bottom alert missing"
    assert re.search(r"alertcondition\(\s*rawBear\s*,", code), "Independent top alert missing"
    assert "//@version=4" in product, "Adapter should retain Pine v4 semantics"
    assert "plot.style_columns" in product, "Raw Hist columns missing"
    assert not re.search(r"\b(?:label|line)\.new\s*\(|\bplotshape\s*\(", code), "Unexpected chart marks"
    return dict(
        exact_original_pivot_and_search_block=True,
        original_core_sha256=hashlib.sha256(core.encode("utf-8")).hexdigest(),
        exact_original_macd_and_pivot_declarations=True,
        direct_independent_raw_conditions=True,
        top_color_precedence_only=True,
        independent_alert_conditions=True,
        no_structure_lifecycle_or_atr_gate=True,
        original_source_sha256=sha256(original_path),
        product_source_sha256=sha256(product_path),
    )


def display_color(raw_bull, raw_bear):
    """Only display precedence; neither raw flag is modified or excluded."""
    return "top_red" if raw_bear else "bottom_blue" if raw_bull else "ordinary"


def display_sanity():
    cases = ((False, False, "ordinary"), (True, False, "bottom_blue"),
             (False, True, "top_red"), (True, True, "top_red"))
    for bull, bear, expected in cases:
        assert display_color(bull, bear) == expected
    both = dict(bottom_alert=True, top_alert=True, color=display_color(True, True))
    assert both["bottom_alert"] and both["top_alert"] and both["color"] == "top_red"
    # Repeated calculations of the same open bar consume current flags only;
    # no previous true value may latch an event or retain the bright color.
    ticks = ((True, False), (False, False), (False, True), (False, False))
    assert [display_color(*flags) for flags in ticks] == [
        "bottom_blue", "ordinary", "top_red", "ordinary"]
    consecutive = ((True, False), (True, False), (False, False), (True, False))
    assert [display_color(*flags) for flags in consecutive] == [
        "bottom_blue", "bottom_blue", "ordinary", "bottom_blue"]
    return dict(mapping_cases=4, dual_direction_alerts_preserved=True,
                same_bar_false_retracts_color=True, consecutive_signals_not_deduplicated=True,
                scope="Pure display specification; not a live tick or Pine execution test")


def replay(tf, out):
    df = load(tf)
    saved_path = ROOT / f"data/derived/indicators_signals_{tf}.jsonl.gz"
    saved = readlines(saved_path)
    assert len(saved) == len(df)
    assert np.array_equal(df.time.to_numpy(), np.array([row["time"] for row in saved]))
    close = df.close.to_numpy()
    hist = np.array([row["Hist_value"] for row in saved], dtype=float)
    expected = np.array([[row["Hist_bull_length"], row["Hist_bear_length"]]
                         for row in saved], dtype=np.int16)
    spans = np.zeros_like(expected)
    pivots = [[], []]
    for t in range(10, len(close)):
        p = t - 5
        for side in (0, 1):
            bullish = side == 0
            # Pine selects the rightmost tied extreme: equal values may be on
            # its left, but none of the five bars on its right may tie it.
            extreme = ((close[p] <= min(close[p-5:p]) and close[p] < min(close[p+1:t+1]))
                       if bullish else
                       (close[p] >= max(close[p-5:p]) and close[p] > max(close[p+1:t+1])))
            if extreme:
                pivots[side].insert(0, p)
                del pivots[side][20:]
            spans[t, side] = find_span(close, hist, t, pivots[side], bullish, 1, True)
    mismatch = np.argwhere(spans != expected)
    assert len(mismatch) == 0, f"{tf}: saved Hist lengths differ at {mismatch[:10].tolist()}"
    expected_flags = np.array([[row["Hist_bull"], row["Hist_bear"]] for row in saved], dtype=bool)
    assert np.array_equal(spans > 0, expected_flags), f"{tf}: saved signal flags differ"
    rows = []
    for t in range(len(close)):
        bull_length, bear_length = map(int, spans[t])
        raw_bull, raw_bear = bull_length > 0, bear_length > 0
        rows.append(dict(
            time=int(df.time.iloc[t]), close_time=int(df.close_time.iloc[t]),
            close=float(close[t]), hist=float(hist[t]),
            bull_length=bull_length, bear_length=bear_length,
            raw_bull=raw_bull, raw_bear=raw_bear,
            column_color=display_color(raw_bull, raw_bear),
            ordinary_sign="positive" if hist[t] >= 0 else "negative",
            bottom_alert_condition=raw_bull, top_alert_condition=raw_bear,
        ))
    output_path = out / f"columns_{tf}.jsonl.gz"
    jsonlines(output_path, rows)
    flags = spans > 0
    return dict(
        timeframe=tf, source_bars=len(close), compared_bars=len(close), mismatched_lengths=0,
        exact_saved_lengths=True, exact_saved_flags=True,
        bottom_condition_bars=int(flags[:, 0].sum()),
        top_condition_bars=int(flags[:, 1].sum()),
        both_condition_bars=int(np.all(flags, axis=1).sum()),
        no_condition_bars=int((~np.any(flags, axis=1)).sum()),
        all_rows_included_without_date_atr_or_event_filter=True,
        saved_reference_sha256=sha256(saved_path),
        raw_candles_sha256=sha256(ROOT / f"data/raw/binance_BTCUSDT_{tf}.json"),
        columns_sha256=sha256(output_path),
    )


def main():
    out = ROOT / "results/hist_bars_v2"
    out.mkdir(parents=True, exist_ok=True)
    checks = source_checks()
    sanity = display_sanity()
    datasets = [replay(tf, out) for tf in ("4h", "1d")]
    result = dict(
        status="PASS", source_checks=checks, display_sanity=sanity, datasets=datasets,
        tested_configuration=dict(pivot_source="Close", pivot_period=5, max_pivots=10,
                                  max_bars=100, macd=[12, 26, 9], divergence="Regular",
                                  dontconfirm=False, minimum_divergences=1),
        scope="Original-source identity plus Python reference replay over saved closed bars; "
              "not a Pine interpreter or TradingView execution. No profitability or reversal-outcome study.",
        optional_high_low_and_dontconfirm_true_runtime_validation="NOT_PERFORMED",
        full_TradingView_export_reconciliation="NOT_PERFORMED",
        live_intrabar_tick_validation="NOT_PERFORMED; display retraction sanity only",
    )
    save(out / "checks.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
