"""Notice-only regression: frozen source comparison and saved 4H/1D replay."""
from pathlib import Path
import hashlib, json, re
from reference_use import readlines
from research import jsonlines, save

R = Path(__file__).resolve().parents[1]


class Notices:
    def __init__(self):
        self.refs = {1: set(), -1: set()}
        self.same = self.opposite = None
        self.counts = [0, 0]

    def step(self, i, active, start, bull=0, bear=0, confirmed=True):
        same = opposite = False
        if confirmed:
            if start or not active:
                self.refs = {1: set(), -1: set()}
                self.same = self.opposite = None
                self.counts = [0, 0]
                if start:
                    self.refs[start].add(i - (bull if start == 1 else bear))
            else:
                self.refs = {s: {p for p in refs if p >= i - 100}
                             for s, refs in self.refs.items()}
                if bool(bull) != bool(bear):
                    side = 1 if bull else -1
                    ref = i - (bull or bear)
                    if ref not in self.refs[side]:
                        self.refs[side].add(ref)
                        if side == active:
                            self.same = i
                            self.counts[0] += 1
                            same = True
                        else:
                            self.opposite = i
                            self.counts[1] += 1
                            opposite = True
        kind = 'opposite' if active and self.opposite is not None else 'same' if active and self.same is not None else 'none'
        last = self.opposite if kind == 'opposite' else self.same if kind == 'same' else None
        return dict(new_same=same, new_opposite=opposite, notice_kind=kind,
                    age=None if last is None else i-last,
                    same_groups=self.counts[0], opposite_groups=self.counts[1])


def main():
    old = (R/'pine/Hist_Divergence_Line_v4_5_2.pine').read_text(encoding='utf-8')
    baseline = json.loads((R/'config/hist_v452_frozen_baseline.json').read_text(encoding='utf-8'))
    pinned = next(a for a in baseline['assets'] if a['file'] == 'Hist_Divergence_Line_v4_5_2.pine')
    assert hashlib.sha256((R/'pine/Hist_Divergence_Line_v4_5_2.pine').read_bytes()).hexdigest() == pinned['sha256']
    p = R/'pine/Hist_Divergence_Line_v4_6.pine'
    new = p.read_text(encoding='utf-8')
    restored = re.sub(r'// BEGIN v4.6 notice aggregation.*?// END v4.6 notice aggregation\n\n', '', new, flags=re.S)
    restored = re.sub(r'// BEGIN v4.6 notice audits.*?// END v4.6 notice audits\n\n', '', restored, flags=re.S)
    restored = re.sub(r'\n    // One historical notice only\..*?f_row\(5,.*?\n', '\n', restored, flags=re.S)
    restored = restored.replace('v4.6', 'v4.5.2').replace('table.new(positionChoice, 2, 6,', 'table.new(positionChoice, 2, 5,')
    assert restored == old, 'Unexpected change outside notice/panel code'
    assert new.count('alertcondition(') == old.count('alertcondition(')
    m = Notices()
    assert m.step(100, 1, 1, 20)['notice_kind'] == 'none'
    assert not m.step(101, 1, 0, 21)['new_same']  # Same reference, later endpoint.
    assert m.step(102, 1, 0, 10)['new_same']
    m.step(103, 1, 0)
    assert not m.step(104, 1, 0, 12)['new_same']  # Gap cannot re-arm the group.
    assert m.step(105, 1, 0, bear=15)['new_opposite']
    assert not m.step(106, 1, 0, bear=16)['new_opposite']
    assert m.step(107, 1, 0, bull=7)['notice_kind'] == 'opposite'  # Priority persists.
    before = (dict((s, set(v)) for s, v in m.refs.items()), m.same, m.opposite)
    assert not m.step(108, 1, 0, bear=7, confirmed=False)['new_opposite']
    assert before == (m.refs, m.same, m.opposite)
    assert not m.step(108, 1, 0, bull=8, bear=7)['new_opposite']
    assert m.step(109, 0, 0)['notice_kind'] == 'none'
    assert m.step(110, -1, -1, bear=7)['notice_kind'] == 'none'
    assert not m.step(111, -1, 0, bear=8)['new_same']
    assert m.step(112, -1, 0, bull=7)['new_opposite']
    assert m.step(113, 1, 1, bull=8)['notice_kind'] == 'none'  # Same-close restart reset.
    out = R/'results/hist_line_v4_6'
    out.mkdir(exist_ok=True)
    datasets = []
    for tf in ['4h', '1d']:
        rows = readlines(R/f'results/hist_v432_backtest/timeline/{tf}_full.jsonl.gz')
        m = Notices()
        trace = []
        # Independent unpruned oracle: uniqueness by event, direction and reference.
        seen = set()
        raw = groups = repeats = ambiguous = 0
        max_refs = 0
        for r in rows:
            i, active, start = r['index'], r['active_direction'], r['start']
            bull, bear = r['bull_length'], r['bear_length']
            res = m.step(i, active, start, bull, bear)
            assert not (res['new_same'] and res['new_opposite'])
            if start:
                seen.add((r['event_id'], start, i-(bull if start == 1 else bear)))
            elif active:
                if bull and bear:
                    ambiguous += 1
                elif bull or bear:
                    raw += 1
                    side = 1 if bull else -1
                    key = (r['event_id'], side, i-(bull or bear))
                    fresh = key not in seen
                    assert (res['new_same'] or res['new_opposite']) == fresh
                    groups += int(fresh)
                    repeats += int(not fresh)
                    seen.add(key)
            if not active or start:
                assert res['notice_kind'] == 'none'
            max_refs = max(max_refs, sum(map(len, m.refs.values())))
            trace.append(dict(r, **res))
        assert raw == groups + repeats
        jsonlines(out/f'notices_{tf}.jsonl.gz', trace)
        datasets.append(dict(timeframe=tf, bars=len(rows), active_raw_signal_bars=raw,
                             new_reference_groups=groups, merged_repeats=repeats,
                             conflicting_bars_skipped=ambiguous, max_reference_storage=max_refs,
                             opposite_groups=sum(x['new_opposite'] for x in trace),
                             same_groups=sum(x['new_same'] for x in trace)))
    result = dict(status='PASS', formal_curve_and_existing_alerts_exact_v452=True,
                  source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), datasets=datasets,
                  scope='Display-only aggregation over saved closed-bar records; not a new return backtest or full TradingView export reconciliation.')
    save(out/'checks.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
