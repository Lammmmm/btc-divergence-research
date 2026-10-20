"""Build the focused Chinese report from saved results; no parameter fitting."""
from pathlib import Path
import json
from reference_use import readlines
from research import save

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/hist_local_completion"
LABEL = {"original": "原版", "dedup_control": "仅去重", "local3": "局部完成＋去重"}


def main():
    rows = json.loads((RESULT / "summary.json").read_text(encoding="utf-8"))
    paired = json.loads((RESULT / "paired_summary.json").read_text(encoding="utf-8"))
    checks = json.loads((RESULT / "checks.json").read_text(encoding="utf-8"))
    for tf in ("4h", "1d"):
        for period in ("full", "earlier", "recent"):
            base = readlines(RESULT / f"{tf}_{period}_original_events.jsonl.gz")
            old_starts = {(e["start_index"], e["direction"]) for e in base}
            old_groups = {(e["direction"], e["pivot_index"]) for e in base}
            for arm in ("dedup_control", "local3"):
                events = readlines(RESULT / f"{tf}_{period}_{arm}_events.jsonl.gz")
                groups = {(e["direction"], e["pivot_index"]) for e in events}
                comparison = dict(
                    added_starts=[e for e in events if (e["start_index"],e["direction"]) not in old_starts],
                    added_reference_groups=[dict(direction=d,pivot_index=p) for d,p in sorted(groups-old_groups)],
                    omitted_reference_groups=[dict(direction=d,pivot_index=p) for d,p in sorted(old_groups-groups)])
                save(RESULT / f"{tf}_{period}_{arm}_coverage.json", comparison)
    full = [r for r in rows if r["period"] == "full"]
    text = [
        "# 局部反转完成：横线时长、反弹误导、新信号与切换",
        "",
        "研究日期：2026-10-20。测试完成；当前 TradingView v4.6.1 未修改，未发布新指标版本。",
        "",
        "## 结论",
        "",
        "局部完成可以明显减少前台横线，但不能代替原研究的反转确认。4H局部完成后的再创新低／新高较多；日线表现更干净，但只有13次局部完成，样本不足以认定稳定可靠。另一个值得保留的发现是：仅禁止同一方向、同一历史参照反复启动，已经能减少约两成横线占用。",
        "",
        "这是一轮显示生命周期研究，不是交易收益回测；未将“局部完成”加到原成功数中。MACD、原始正式背离、原冻结确认价和失效价均未改变。改变的是前台退出和信号接收规则，因此不能把新前台事件数称作原版正式事件数。",
        "",
        "## 固定口径",
        "",
        "- Binance BTCUSDT USDT永续；4H和1D分别测试。2020年预热，2021-01-01至2026-10-15 UTC；复用已有历史快照和异常数据处理，没有新增行情或清洗。",
        "- 只测试一种局部完成方案：影线高／低点左右各3根，严格独立极值；到右侧第3根收盘才可使用。与正式背离原来的Close枢轴完全分开。",
        "- 底背离选择最近已确认的小高点，顶背离选择小低点。必须位于原参照之后、触发价的预期方向、且比原确认价更近。触发时找不到，就等后续已确认的合格拐点；选中即冻结，不追踪挪动。选择时不超过100根旧。",
        "- 从触发后的下一根开始，收盘严格突破局部价才结束前台；等于或影线碰到不算。原规则确认／失效优先。局部结束后允许同根接受另一个新参照信号，无额外冷却期。",
        "- 去重键为方向＋原始历史参照枢轴；每个测试区间内只启动一次。同一参照的新末端不再重复启动，这也可能略过后来有意义的再次背离；不是无代价过滤。去重控制组不使用局部完成。",
        "- 每个前台事件另存原边界最终结果，允许后台事件重叠；后台结果不反馈给前台决策。原版官方事件流同时单独保留。",
        "",
        "方案在执行前提交于 `b7563c5`；未遍历其他枢轴根数、ATR或冷却参数。",
        "",
        "## 1. 横线是否缩短",
        "",
        "| 周期 | 方案 | 前台事件 | 横线占用（根） | 比原版减少 | 已结束等待中位/90分位 | 最长观察等待（根） |",
        "|---|---|---:|---:|---:|---|---:|",
    ]
    for r in full:
        text.append(f"| {r['timeframe']} | {LABEL[r['arm']]} | {r['events']} | {r['occupied_bars']} | {r['occupied_reduction']:.1%} | {r['median_completed_wait']:.1f} / {r['p90_completed_wait']:.1f} | {r['longest_observed_event']} |")
    text += [
        "",
        "占用＝每根收盘仍有前台事件的根数。中位/90分位只统计已结束事件；最长值包含待定事件目前已经等待的时间。最长同方向连续端点段也已计算，本轮与表中最长观察等待相同。原版每个周期各有1个未结束事件；局部方案4H有1个、1D有0个。",
        "",
        "不能把组合方案全部改善归功于局部完成：", "",
    ]
    for tf in ("4h", "1d"):
        control = next(r for r in full if r["timeframe"] == tf and r["arm"] == "dedup_control")
        local = next(r for r in full if r["timeframe"] == tf and r["arm"] == "local3")
        text.append(f"- {tf}：在已经去重的基础上，局部完成再把占用从{control['occupied_bars']}降到{local['occupied_bars']}根，进一步减少{1-local['occupied_bars']/control['occupied_bars']:.1%}。")
    text += [
        "",
        "同起点配对进一步排除接收新事件的影响：",
        "",
        "| 周期 | 原版起点数 | 提前局部完成 | 节省等待总根数 | 同起点最长等待：原→局部 |",
        "|---|---:|---:|---:|---|",
    ]
    for r in paired:
        if r["period"] == "full":
            text.append(f"| {r['timeframe']} | {r['baseline_events']} | {r['earlier_local_exits']} | {r['total_saved_bars']} | {r['max_observed_wait_original']} → {r['max_observed_wait_local']} |")
    text += [
        "",
        "**关键限制：4H同起点最长仍有490根，日线仍有78根。** 实际流中的4H最长降到132根，还包含去重和事件起点改变的作用；局部完成并不能保证每条长横线都会缩短。配对记录与实际流不能混用分母。",
        "",
        "## 2. 是否只是短暂反弹",
        "",
        "对每次局部完成，冻结从背离末端K线（触发前一根）到局部完成当根已出现的最低/最高影线价。之后到原规则事件结束为止，底背离再次严格跌破该低点、顶背离再次严格突破该高点，记为回撤破坏。影线和收盘分别统计，不设置最长等待；另列6根以内的快速破坏。",
        "",
        "| 周期 | 局部完成次数 | 后来影线破坏 | 后来收盘破坏 | 6根内影线破坏 | 原规则最终成功/失败/待定 |",
        "|---|---:|---|---|---|---|",
    ]
    for r in full:
        if r["arm"] == "local3":
            n = r["foreground_local"]
            text.append(f"| {r['timeframe']} | {n} | {r['local_wick_relapses']}/{n}（{r['local_wick_relapses']/n:.1%}） | {r['local_close_relapses']}/{n}（{r['local_close_relapses']/n:.1%}） | {r['local_wick_relapses_within_6']}/{n} | {r['local_original_success']}/{r['local_original_failure']}/{r['local_original_pending']} |")
    text += [
        "",
        "全区间局部完成样本均可观察到原规则结局，无删失；分段样本可能仍待定，已单列censored，未当作无破坏成功。统计包括原结局当根的影线，OHLC不能辨别该根内先后顺序；不据此模拟成交。局部破坏后仍可能最终达到原确认价，所以破坏次数不等于原失败次数。",
        "",
        "4H中23/61后来破坏局部反转，其中4次发生在6根内。日线1/13后来破坏，13次最后都按原规则成功，但这不是13笔交易全赢，也不是未来成功概率。",
        "",
        "## 3. 新信号与频繁切换",
        "",
        "| 周期 | 方案 | 相对原版新增不同参照组 | 原版参照组未被接收 | 被去重的信号根数 | 全部结束→3根内再启动 | 全部结束→6根内反向启动 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for r in full:
        text.append(f"| {r['timeframe']} | {LABEL[r['arm']]} | {r['added_distinct_reference_groups']} | {r['omitted_baseline_reference_groups']} | {r['duplicate_signal_bars_suppressed']} | {r['all_restarts_within_3']}/{r['all_transitions']} | {r['all_opposite_restarts_within_6']}/{r['all_transitions']} |")
    text += [
        "",
        "新增按方向＋历史参照去重，不保证统计独立；过滤重复会改变随后可接收的起点，因此减少事件总数也可能增加不同参照覆盖。原版4H有36次重复参照启动，日线5次；两个去重组均为0。数据保留新增起点和遗漏组，未只展示有利指标。",
        "",
        "只看局部完成之后：", "",
    ]
    for r in full:
        if r["arm"] == "local3":
            text.append(f"- {r['timeframe']}：{r['foreground_local']}次局部完成中，{r['local_with_next_event']}次后来出现下一前台事件；{r['local_restart_within_3']}次在3根内再次启动，{r['local_opposite_restart_within_6']}次在6根内反向启动。")
    text += [
        "",
        "3/6根只是描述指标，不参与退出或过滤。4H分别等于12/24小时，日线等于3/6天；不能当作相同日历时间比较。未重新绘制Pine平滑曲线，切换统计是事件级噪声代理，不是完整视觉主观评分。",
        "",
        "## 近期诊断：2025年起",
        "",
        "| 周期 | 方案 | 占用比原版减少 | 最长等待 | 局部完成/后来影线破坏 | 新增参照组 |",
        "|---|---|---:|---:|---|---:|",
    ]
    for r in rows:
        if r["period"] == "recent":
            text.append(f"| {r['timeframe']} | {LABEL[r['arm']]} | {r['occupied_reduction']:.1%} | {r['longest_observed_event']} | {r['foreground_local']} / {r['local_wick_relapses']} | {r['added_distinct_reference_groups']} |")
    text += [
        "",
        "近期4H仍有132根的最长等待未改善；近期日线仅5次局部完成，0次破坏不能说明风险为0。完整、2025年前、2025年起分别重置前台状态；区间重叠且均为已看过的历史，不能相加，也不能称为新样本外验证。",
        "",
        "## 实际选择",
        "",
        "建议先把“去重后保持原边界”的方案作为保守候选；局部完成保留为可选观察模式，不直接替换默认。理由是仅去重已有明显占用改善，并保留每个已接收事件的原结束规则。它仍改变信号接收范围，需要明确同参照后续事件会被省略，不能据此声称准确率提升。",
        "",
        "如果使用局部模式，必须把结束命名为“局部观察完成”，原结构继续后台跟踪，不能将灰色恢复理解为原背离已经失效。尤其4H，改善时长与反弹误导的取舍明显。日线可作为小样本候选进一步向前观察，不能依据这13次直接升级为默认。",
        "",
        "本次没有实施第二轮参数寻优，也没有修改线上指标或警报。",
        "",
        "## 验证与文件",
        "",
        f"- {checks['synthetic_cases']}组合成场景、{checks['independently_verified_events']}条事件独立搜索核对、{checks['truncated_prefix_checks']}次实际截断输入前缀检查全部通过。",
        "- 全部周期/时期的原版逐根结果与保存的v4.3.2基线一致；当前v4.6.1源码SHA256未变。原始行情、信号及程序哈希保存在checks.json。",
        "- 18组前台事件、逐根状态、信号接收账本和后台结果，以及6组同起点配对，全部保存在results/hist_local_completion/。这些实验共享行情，不是独立样本。",
        "- 失败反弹的全部案例见false_bounce_cases.json；明确保留当时阈值、局部结束时刻、首次再破坏时刻及原结局。",
        "- Python离线重放通过，不等于TradingView全历史逐根对账。本轮没有新的Pine版本，因此没有宣称在TradingView运行了局部模式。",
        "",
        "复现：",
        "",
        "```text",
        "python src/compare_hist_local_completion.py",
        "python src/report_hist_local_completion.py",
        "```",
        "",
        "[冻结方案](../config/hist_local_completion.json) · [检查记录](../results/hist_local_completion/checks.json) · [结果目录](../results/hist_local_completion/)",
    ]
    (ROOT / "reports/HIST_LOCAL_COMPLETION.md").write_text("\n".join(text)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
