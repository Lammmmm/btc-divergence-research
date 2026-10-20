"""Registered display-completion experiment. Does not modify Pine or raw signals."""
from pathlib import Path
import hashlib
import json
import numpy as np
from research import load, atr, START, END, jsonlines, save
from reference_use import readlines
from compare_hist_boundaries import levels, outcome, first, replay as baseline_replay

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/hist_local_completion"
ARMS = ("original", "dedup_control", "local3")
SPLIT = 1735689600000


def swings(values, n=3):
    """Commit strict unique wick pivots on the right-side confirmation bar."""
    values = np.asarray(values)
    hi, lo = [[] for _ in values], [[] for _ in values]
    for t in range(2*n, len(values)):
        p = t-n
        others = np.r_[values[p-n:p], values[p+1:t+1]]
        if np.all(values[p] > others):
            hi[t].append(p)
        if np.all(values[p] < others):
            lo[t].append(p)
    return hi, lo


def context(df, aa, lengths):
    return dict(df=df, aa=aa, lengths=lengths,
                h=df.high.to_numpy(), l=df.low.to_numpy(), c=df.close.to_numpy(),
                tm=df.time.to_numpy(), ct=df.close_time.to_numpy(),
                sh=swings(df.high.to_numpy())[0], sl=swings(df.low.to_numpy())[1])


def choose(ctx, e, t, known):
    d = e["direction"]
    values = ctx["h"] if d == 1 else ctx["l"]
    for p in reversed(known):
        if p < max(e["pivot_index"], t-100):
            break
        price = float(values[p])
        if d*(price-e["reference"]) > 0 and d*(e["target"]-price) > 0:
            return dict(local_target=price, local_pivot=p, local_known_at=t)
    return None


def replay(ctx, start, end, arm):
    """Only current/past OHLC and confirmed signal spans drive the foreground."""
    active = None
    seen = set()
    known_hi, known_lo = [], []
    events, trace, ledger = [], [], []
    seq = 0
    for t in range(len(ctx["c"])):
        if ctx["ct"][t] >= end:
            break
        known_hi.extend(ctx["sh"][t]); known_lo.extend(ctx["sl"][t])
        if ctx["tm"][t] < start:
            continue
        pulse = dict(start=0, success=0, failure=0, local=0)
        if active and t > active["start_index"]:
            status = outcome(ctx["c"][t], active["direction"], active["target"], active["invalid"])
            if not status and arm == "local3":
                if active["local_target"] is None:
                    found = choose(ctx, active, t, known_hi if active["direction"] == 1 else known_lo)
                    if found:
                        active.update(found)
                if active["local_target"] is not None and active["direction"]*(ctx["c"][t]-active["local_target"]) > 0:
                    status = "local"
            if status:
                active.update(status=status, end_index=t, end_time=int(ctx["ct"][t]),
                              wait_bars=t-active["start_index"])
                events.append(active)
                pulse[status] = active["direction"]
                active = None
        bull, bear = map(int, ctx["lengths"][t])
        if bull or bear:
            d = 1 if bull else -1
            span = bull or bear
            key = (d, t-span)
            reason = "accepted"
            if active:
                reason = "active_structure"
            elif bull and bear:
                reason = "conflict"
            elif not np.isfinite(ctx["aa"][t]) or ctx["aa"][t] <= 0:
                reason = "invalid_atr"
            elif arm != "original" and key in seen:
                reason = "duplicate_reference"
            ledger.append(dict(index=t, time=int(ctx["tm"][t]), bull_length=bull,
                               bear_length=bear, reason=reason))
            if reason == "accepted":
                target, invalid = levels(ctx["h"], ctx["l"], t, span, d, ctx["aa"][t], "original")
                seq += 1
                active = dict(seq=seq, direction=d, start_index=t, start_time=int(ctx["tm"][t]),
                              pivot_index=t-span, reference=float(ctx["c"][t]), target=target,
                              invalid=invalid, atr=float(ctx["aa"][t]), status="pending",
                              local_target=None, local_pivot=None, local_known_at=None)
                if arm == "local3":
                    found = choose(ctx, active, t, known_hi if d == 1 else known_lo)
                    if found:
                        active.update(found)
                seen.add(key)
                pulse["start"] = d
        trace.append(dict(index=t, time=int(ctx["tm"][t]), **pulse, event_id=seq,
                          active_direction=active["direction"] if active else 0,
                          confirmation=active["target"] if active else None,
                          invalidation=active["invalid"] if active else None,
                          local_target=active["local_target"] if active else None,
                          local_pivot=active["local_pivot"] if active else None))
    if active:
        t = trace[-1]["index"]
        events.append(dict(active, end_index=t, end_time=int(ctx["ct"][t]),
                           wait_bars=t-active["start_index"]))
    return events, trace, ledger


def independent_local_exit(ctx, event, last):
    """Separate direct window search: determine frozen target then first crossing."""
    t, d = event["start_index"], event["direction"]
    original_end, original_status = first(ctx["c"], t, last, d, event["target"], event["invalid"])
    vals = ctx["h"] if d == 1 else ctx["l"]
    candidates = []
    for p in range(max(3, event["pivot_index"]), last-2):
        # Check pivots directly, independently of the streaming commit arrays.
        v = vals[p]
        other = np.concatenate((vals[p-3:p], vals[p+1:p+4]))
        if not np.all(d*(v-other) > 0):
            continue
        known = max(t, p+3)
        if p < known-100:
            continue
        if d*(v-event["reference"]) > 0 and d*(event["target"]-v) > 0:
            candidates.append((known, -p, float(v)))
    local_target = local_pivot = local_known = None
    if candidates:
        local_known, negative_pivot, local_target = min(candidates)
        local_pivot = -negative_pivot
        start = max(t+1, local_known)
        hits = np.flatnonzero(d*(ctx["c"][start:last+1]-local_target) > 0)
        hit = start+int(hits[0]) if len(hits) else last+1
        # Original resolution takes precedence on ties.
        if hit < original_end or (hit == original_end and original_status == "pending"):
            return dict(end_index=hit, status="local", local_target=local_target,
                        local_pivot=local_pivot, local_known_at=local_known)
    return dict(end_index=original_end, status=original_status)


def audit_background(ctx, e, last):
    """Future evaluation only: never called by foreground replay."""
    t, d = e["start_index"], e["direction"]
    end, status = first(ctx["c"], t, last, d, e["target"], e["invalid"])
    result = dict(start_index=t, direction=d, pivot_index=e["pivot_index"],
                  original_end_index=end, original_status=status, original_wait=end-t)
    if e["status"] != "local":
        return result
    q = e["end_index"]
    extreme = float(np.min(ctx["l"][t-1:q+1]) if d == 1 else np.max(ctx["h"][t-1:q+1]))
    wick = ctx["l"] if d == 1 else ctx["h"]
    def breach(values):
        hits = np.flatnonzero(d*(values[q+1:end+1]-extreme) < 0)
        return q+1+int(hits[0]) if len(hits) else None
    w, c = breach(wick), breach(ctx["c"])
    result.update(local_end_index=q, local_end_time=int(ctx["ct"][q]),
                  adverse_extreme_at_local_exit=extreme, wick_relapse_index=w,
                  close_relapse_index=c, wick_relapse=w is not None, close_relapse=c is not None,
                  wick_relapse_within_6=w is not None and w-q <= 6,
                  six_bar_observation_complete=end-q >= 6 or status != "pending",
                  relapse_class="breached" if w is not None else
                                "censored" if status == "pending" else "no_breach_before_original_end",
                  bars_saved_original=end-q,
                  local_move_atr=d*(ctx["c"][q]-e["reference"])/e["atr"])
    return result


def longest_run(trace):
    maximum = count = 0
    previous = 0
    for r in trace:
        d = r["active_direction"]
        count = count+1 if d and d == previous else int(bool(d))
        maximum = max(maximum, count)
        previous = d
    return maximum


def stats(events, trace, ledger, backgrounds, base_events, base_trace):
    completed = [e for e in events if e["status"] != "pending"]
    local = [e for e in events if e["status"] == "local"]
    paired_by_start = {r["start_index"]: r for r in backgrounds}
    checks = [paired_by_start[e["start_index"]] for e in local]
    old_starts = {(e["start_index"], e["direction"]) for e in base_events}
    old_groups = {(e["direction"], e["pivot_index"]) for e in base_events}
    groups = {(e["direction"], e["pivot_index"]) for e in events}
    added = [e for e in events if (e["start_index"], e["direction"]) not in old_starts]
    local_next = [(a, b) for a, b in zip(events, events[1:]) if a["status"] == "local"]
    transitions = list(zip(events, events[1:]))
    occupied = sum(bool(r["active_direction"]) for r in trace)
    original_occupied = sum(bool(r["active_direction"]) for r in base_trace)
    waits = [e["wait_bars"] for e in completed]
    known = sum(r["relapse_class"] != "censored" for r in checks)
    return dict(events=len(events), completed=len(completed),
                foreground_success=sum(e["status"] == "success" for e in events),
                foreground_failure=sum(e["status"] == "failure" for e in events),
                foreground_local=len(local), foreground_pending=len(events)-len(completed),
                occupied_bars=occupied, occupied_reduction=1-occupied/original_occupied,
                median_completed_wait=float(np.median(waits)) if waits else None,
                p90_completed_wait=float(np.quantile(waits, .9)) if waits else None,
                longest_observed_event=max(e["wait_bars"] for e in events),
                longest_same_direction_endpoint_run=longest_run(trace),
                added_starts=len(added), added_distinct_reference_groups=len(groups-old_groups),
                omitted_baseline_reference_groups=len(old_groups-groups),
                accepted_reference_groups=len(groups), repeated_accepted_starts=len(events)-len(groups),
                ignored_signal_bars=sum(r["reason"] == "active_structure" for r in ledger),
                duplicate_signal_bars_suppressed=sum(r["reason"] == "duplicate_reference" for r in ledger),
                all_transitions=len(transitions),
                all_restarts_within_3=sum(b["start_index"]-a["end_index"] <= 3 for a,b in transitions),
                all_opposite_restarts_within_6=sum(b["direction"] != a["direction"] and
                    b["start_index"]-a["end_index"] <= 6 for a,b in transitions),
                local_wick_relapses=sum(r["wick_relapse"] for r in checks),
                local_close_relapses=sum(r["close_relapse"] for r in checks),
                local_wick_relapses_within_6=sum(r["wick_relapse_within_6"] for r in checks),
                local_censored=len(checks)-known, local_known_relapse_denominator=known,
                local_original_success=sum(r["original_status"] == "success" for r in checks),
                local_original_failure=sum(r["original_status"] == "failure" for r in checks),
                local_original_pending=sum(r["original_status"] == "pending" for r in checks),
                local_with_next_event=len(local_next),
                local_restart_within_3=sum(b["start_index"]-a["end_index"] <= 3 for a, b in local_next),
                local_opposite_restart_within_6=sum(b["direction"] != a["direction"] and
                    b["start_index"]-a["end_index"] <= 6 for a, b in local_next))


def synthetic_checks():
    hi, _ = swings([0, 1, 2, 5, 2, 1, 0, 0])
    assert all(not v for v in hi[:6]) and hi[6] == [3]
    tied, _ = swings([0, 1, 5, 5, 2, 1, 0])
    assert not any(tied)
    assert first(np.array([100., 110., 111.]), 0, 2, 1, 110., 80.) == (2, "success")
    import pandas as pd
    # Target 120 from original pivot, initial local target 110 confirmed at index 8.
    h = np.array([120,104,103,104,105,110,105,104,103,104,105,107,110,112,113.])
    l = np.full(len(h), 95.)
    c = np.full(len(h), 100.)
    c[12:15] = [110, 111, 112]
    df = pd.DataFrame(dict(time=np.arange(len(h)),close_time=np.arange(len(h)),
                           high=h, low=l, close=c))
    lengths = np.zeros((len(h), 2), dtype=int)
    lengths[10, 0] = 10; lengths[13, 0] = 13  # same historical reference
    ctx = context(df, np.ones(len(h)), lengths)
    ev, tr, ledger = replay(ctx, 0, len(h), "local3")
    assert len(ev) == 1 and ev[0]["status"] == "local" and ev[0]["end_index"] == 13
    assert tr[12]["active_direction"] == 1 and ledger[-1]["reason"] == "duplicate_reference"
    assert independent_local_exit(ctx, ev[0], len(h)-1)["end_index"] == 13
    # Exact sign-mirrored short case must have the same local exit and dedup outcome.
    mirrored = df.copy()
    mirrored["high"], mirrored["low"], mirrored["close"] = -df.low, -df.high, -df.close
    negative_lengths = lengths[:, ::-1]
    mirror_ctx = context(mirrored, np.ones(len(h)), negative_lengths)
    short_ev, _, short_ledger = replay(mirror_ctx, 0, len(h), "local3")
    assert short_ev[0]["end_index"] == 13 and short_ev[0]["direction"] == -1
    assert short_ledger[-1]["reason"] == "duplicate_reference"
    # Deferred target: signal before pivot becomes known; cannot use it early.
    lengths[:] = 0; lengths[6, 0] = 6
    ctx = context(df, np.ones(len(h)), lengths)
    ev, tr, _ = replay(ctx, 0, len(h), "local3")
    assert tr[6]["local_target"] is None and tr[7]["local_target"] is None
    assert tr[8]["local_target"] == 110 and ev[0]["local_known_at"] == 8
    # Wick touching original invalidation does not close; strict close does.
    df.loc[9, "low"] = 90
    df.loc[10, "close"] = 90
    df.loc[10, "low"] = 89
    ctx = context(df, np.ones(len(h)), lengths)
    ev, tr, _ = replay(ctx, 0, len(h), "local3")
    assert tr[9]["active_direction"] == 1
    assert ev[0]["status"] == "failure" and ev[0]["end_index"] == 10
    # Original target crossed on same bar as local target must stay original success.
    df.loc[10, "close"] = 121
    df.loc[10, "high"] = 122
    ctx = context(df, np.ones(len(h)), lengths)
    ev, _, _ = replay(ctx, 0, len(h), "local3")
    assert ev[0]["status"] == "success" and ev[0]["end_index"] == 10
    return 8


def main():
    OUT.mkdir(exist_ok=True)
    synthetic_count = synthetic_checks()
    summaries, pair_summaries, case_rows, hashes = [], [], [], {}
    verified, prefix_checks = 0, 0
    for tf in ("4h", "1d"):
        df = load(tf); aa = atr(df)
        path = ROOT / f"data/derived/indicators_signals_{tf}.jsonl.gz"
        saved = readlines(path)
        hashes[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert df.time.tolist() == [r["time"] for r in saved]
        lengths = np.array([[r["Hist_bull_length"], r["Hist_bear_length"]] for r in saved], dtype=int)
        ctx = context(df, aa, lengths)
        for period, start, end in (("full", START, END), ("earlier", START, SPLIT), ("recent", SPLIT, END)):
            base, bt, _ = baseline_replay(df, aa, lengths, start, end, "original")
            saved_base = readlines(ROOT / f"results/hist_v432_backtest/timeline/{tf}_{period}.jsonl.gz")
            assert len(bt) == len(saved_base)
            assert all(all(x[k] == y[k] for k in x) for x, y in zip(bt, saved_base))
            last = bt[-1]["index"]
            for arm in ARMS:
                ev, tr, le = replay(ctx, start, end, arm)
                if arm == "original":
                    assert len(tr) == len(bt)
                    assert all(all(x[k] == y[k] for k in y) for x, y in zip(tr, bt))
                if arm != "original":
                    assert len({(e["direction"], e["pivot_index"]) for e in ev}) == len(ev)
                for e in ev:
                    actual = (e["end_index"], e["status"])
                    if arm == "local3":
                        expected = independent_local_exit(ctx, e, last)
                        assert actual == (expected["end_index"], expected["status"]), (tf, period, e, expected)
                        if e["status"] == "local":
                            for k in ("local_target", "local_pivot", "local_known_at"):
                                assert e[k] == expected[k]
                            assert e["local_pivot"]+3 <= e["local_known_at"] <= e["end_index"]
                    else:
                        assert actual == first(ctx["c"], e["start_index"], last, e["direction"], e["target"], e["invalid"])
                    verified += 1
                # Actually truncate input, including OHLC, indicators and pivot availability.
                for fraction in (.33, .67):
                    k = bt[int((len(bt)-1)*fraction)]["index"]
                    small = context(df.iloc[:k+1], aa[:k+1], lengths[:k+1])
                    short = replay(small, start, int(ctx["ct"][k])+1, arm)[1]
                    assert short == tr[:len(short)]
                    prefix_checks += 1
                backgrounds = [audit_background(ctx, e, last) for e in ev]
                summary = stats(ev, tr, le, backgrounds, base, bt)
                summaries.append(dict(timeframe=tf, period=period, arm=arm, **summary))
                prefix = f"{tf}_{period}_{arm}"
                for suffix, rows in (("events", ev), ("timeline", tr), ("ledger", le), ("background", backgrounds)):
                    jsonlines(OUT / f"{prefix}_{suffix}.jsonl.gz", rows)
                if arm == "local3" and period == "full":
                    case_rows.extend(dict(timeframe=tf, **r) for r in backgrounds if r.get("wick_relapse"))
            pairs = []
            for e in base:
                alternative = independent_local_exit(ctx, e, last)
                q = dict(e, **alternative)
                q["wait_bars"] = q["end_index"]-q["start_index"]
                background = audit_background(ctx, q, last)
                pairs.append(dict(start_index=e["start_index"], start_time=e["start_time"], direction=e["direction"],
                                  original_status=e["status"], original_wait=e["wait_bars"],
                                  local_status=q["status"], local_wait=q["wait_bars"],
                                  saved_bars=e["end_index"]-q["end_index"], **{
                                      k:v for k,v in background.items() if k.startswith("wick_") or k == "relapse_class"}))
            jsonlines(OUT / f"{tf}_{period}_paired.jsonl.gz", pairs)
            local_pairs = [p for p in pairs if p["local_status"] == "local"]
            pair_summaries.append(dict(timeframe=tf, period=period, baseline_events=len(base),
                                      earlier_local_exits=len(local_pairs),
                                      total_saved_bars=sum(p["saved_bars"] for p in pairs),
                                      median_all_observed_wait_original=float(np.median([p["original_wait"] for p in pairs])),
                                      median_all_observed_wait_local=float(np.median([p["local_wait"] for p in pairs])),
                                      max_observed_wait_original=max(p["original_wait"] for p in pairs),
                                      max_observed_wait_local=max(p["local_wait"] for p in pairs),
                                      wick_relapses=sum(p["wick_relapse"] for p in local_pairs),
                                      censored=sum(p["relapse_class"] == "censored" for p in local_pairs)))
    for name, rows in (("summary", summaries), ("paired_summary", pair_summaries), ("false_bounce_cases", case_rows)):
        save(OUT / f"{name}.json", rows)
    for rel in ("config/hist_local_completion.json", "src/compare_hist_local_completion.py",
                "src/compare_hist_boundaries.py", "src/signal_port.py", "src/research.py",
                "pine/Hist_Divergence_Line_v4_6_1.pine"):
        hashes[rel] = hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    for p in sorted((ROOT/"data/raw").glob("*")):
        if p.is_file():
            hashes[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    assert hashes["pine/Hist_Divergence_Line_v4_6_1.pine"] == "102496e335a696e138f5748b4959325723bd46548a066d89a9ec108c315978aa"
    save(OUT / "checks.json", dict(status="PASS", synthetic_cases=synthetic_count,
                                  independently_verified_events=verified, truncated_prefix_checks=prefix_checks,
                                  baseline_matches_saved=True, no_duplicate_reference_local=True,
                                  original_pine_unchanged=True, source_hashes=hashes))
    print(json.dumps([r for r in summaries if r["period"] == "full"], indent=2))


if __name__ == "__main__":
    main()
