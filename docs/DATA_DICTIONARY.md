# 文件与字段

时间全部为 UTC Unix 毫秒，不是北京时间。正式区间的结束时刻为 2026-10-16 00:00:00 UTC，不含该时刻。比例 0.01 表示 1%，现金单位 USDT，数量单位 BTC。

## 原始数据

K线 JSON 每行依次为：开盘时间、open、high、low、close、基础资产成交量、收盘时间、报价资产成交量、成交笔数、主动买入基础量、主动买入报价量、ignore。原始数值字符串保持交易所响应格式。标记价格 K 线非成交量数据，不用于成交量指标。

资金费原始字段保留 Binance 响应。`data/derived/funding_resolved.jsonl.gz` 每行包含 `time, rate, mark_price, mark_source`，区分 API 标记价格和标记K线开盘代理。

## 逐根指标/信号

`indicators_signals_4h.jsonl.gz` 与 `indicators_signals_1d.jsonl.gz` 包含所有预热及测试 K 线。

- `time`：信号所在 K 线开盘时间；`confirm_time`：该 K 线收盘时间。
- `atr14`：收盘时已知的 ATR。
- `*_value`：每个指标的值；尚未预热完成时为 null。
- `*_bull, *_bear`：该指标普通底/顶背离是否成立，0 或 1。
- `*_bull_length, *_bear_length`：原脚本找到的背离跨度；0 表示无信号。

## 逐笔交易

文件名 `周期_指标_场景_区间.jsonl.gz`，组内 `seq` 从 1 递增。

| 字段 | 含义 |
|---|---|
| direction | 1 多头、−1 空头 |
| signal_open_time / signal_confirm_time | 信号 K 线开盘/确认时间 |
| entry_time | 下一根开盘时间 |
| exit_time_lower / exit_time_upper | 退出所在小时的时间界限；时间退出或跳空退出时相同 |
| exit_reason | stop、target、stop_gap、target_gap、time |
| ambiguous_hour | 同一小时止盈止损均触及，按止损先到 |
| entry_raw / exit_raw | 未加入滑点的成交参考价 |
| entry_exec / exit_exec | 含不利滑点的成交价 |
| atr_signal / stop / target | 确认时 ATR、初始止损和止盈价 |
| quantity / notional | BTC 数量、入场 USDT 名义金额 |
| initial_risk | 数量 × ATR止损距离，不含费用 |
| planned_risk_fraction | initial_risk / equity_before；固定持有基准为 null |
| gross_price_pnl | 含滑点、未扣手续费资金费的价差现金盈亏 |
| fees | 入场与退出手续费合计，正数成本 |
| funding | 资金费净成本；负数表示收到资金费 |
| pnl / equity_before / equity_after | 净现金盈亏、前后权益 |
| net_R | pnl / initial_risk |
| account_return | pnl / equity_before |
| direction_hit | 原始退出价是否相对原始入场价顺向 |
| regime | 信号确认时 close 在本周期 EMA200 上/下方 |
| mfe_pct / mae_pct | 固定持有窗口最大有利/不利波动，小数比例 |
| mfe_hours / mae_hours | 极值首次发生的小时序号 |
| hours_held_upper | 持仓覆盖的小时 K 线数，非毫秒精确持续时间 |

## 信号处理账本

`status` 为 entered、ignored_position_open、both_directions_skip、purged_boundary、purged_price_inconsistency 或 invalid_atr。保留全部正式区间内的原始单指标信号，能区分没有信号与有信号但不能交易。

## 汇总与曲线

`summary.json` 每行对应一组实验，`period=full/dev_YYYYMM/eval_YYYYMM`。详细统计定义见方法文档。`equity/` 只记录持仓内小时权益和每次入场前权益；空仓时权益保持不变。画连续日历曲线时应向前填充，不能线性插值当成实际收益。

`breakdowns.json` 是主账户交易的多空、入场年份和市场状态分组，组间不独立；`uncertainty.json` 为平均净 R 描述性区间；`screening.json` 为预设门槛结果。不同场景与滚动窗口不可合并计算一个总胜率或总收益。

## 实用参考扩展（results/reference_use）

13 种显示/提醒设置 × 全期、前段、近期，共 39 个观察账本。12 种预设，Hist_or_MOM 为看过首轮结果后明确追加的探索性简化检查。它不是新的止盈止损策略回测。

- `events/`：完整观察事件。`entry` 为收盘确认后下一根开盘参考价，不含滑点；`window_end` 为固定观察窗口末尾。日线10天，4H18根即3天。
- `first_barrier`：favorable_first、adverse_first、ambiguous_adverse_first 或 neither，分别为先顺向1ATR、先逆向1ATR、同小时双触及按逆向先到、均未触及。
- `first_touch_hours`：从观察窗口起点算起的首次边界触及小时序号，不能视为精确成交时间。
- `end_direction_positive`：观察期末方向是否正确；与先顺向1ATR比例不同。
- `mfe_atr/mae_atr`：整个固定窗口内最大顺向/逆向波动除以信号时ATR。即使边界先被触及，也继续观察到窗口结束。
- `daily_context_*`：当时已收盘的日线三项候选池背景。`daily_context_event_time` 可能记录已过期事件，方向为0表示背景无效；不能只凭事件时间判断有效性。
- `same_side_pool_count/pool_multiplicity`：原候选池（日线三项、4H两项）的同向信号数量，用于诊断，而非每个单项配置的启用数。
- `daily_regime_source_close`：行情状态所依据的最近已收盘日线收盘时间，必须不晚于当前信号确认。
- `daily_adx14/daily_regime`：日线Wilder ADX14；<20为range，>=25为trend，其他为transition。首个TR和方向变动不纳入种子，连续14个有效数作为RMA种子。
- `trend_relation`：强趋势下的提示方向与日线+DI/−DI方向同向或反向，其他为not_strong_trend。
- `ledgers/`：所有候选信号的采用/重叠/日线背景不符/边界/价格异常原因。
- `cohorts.json`：同一事件池按方向、行情状态、单项/多项、日线背景拆分。不是重新模拟的过滤策略。
- `filter_decisions.json`：预先定义的实用性门槛检查，不是显著性检验。

不同设置之间可能覆盖相同行情；不同时间段重复历史。不能合并样本数量、不能把参考指标的波动统计作为扣费交易收益。

## 无固定期限的结构反转（results/structure_reversal）

20 个单指标/周期设置，各自全期、前段、近期，共 60 个账本。精确口径见 `STRUCTURE_REVERSAL_METHOD.md`。

- `events/`：每个被接受事件一行；`status` 为 success、failure、pending 或 data_interrupted。
- `signal_time / confirm_time`：信号根开盘/收盘时间；`direction` 为 1 底背离、−1 顶背离。
- `pivot_time / pivot_confirm_time / divergence_length`：原始背离起点枢轴、它被右侧 5 根确认的时刻、原脚本保存的跨度。
- `structure_start / structure_end / structure_high / structure_low`：提示确认时已知的冻结区间及高低价，含两端 K 线。
- `confirmation_level / invalidation_level`：成功和失效收盘边界，之后不再改变；等于边界不触发。
- `reference_price / atr_at_signal`：提示收盘价和当时 ATR，前者不是交易入场价格。
- `reference_index / resolution_index`：在含预热数据的原生数组中的下标。待定时 resolution_index 为本段最后一根，不代表已完成。
- `status_time`：首次完成、首次数据中断、或待定截至的收盘时间；`path_last_time` 为计算波动的最后有效收盘时间，中断时早于 status_time。
- `resolution_close`：成功/失败时收盘价；待定或数据中断为 null。
- `wait_days / wait_bars`：从确认到有效路径末尾的等待天数/根数。
- `confirmation_distance_atr / failure_distance_atr`：冻结边界相对提示收盘价的顺向/逆向距离，除以当时 ATR。
- `mae_pct / mfe_pct`：下一根起至有效路径末尾最大逆向/顺向波动，除以 reference_price；小数比例。相应 `*_atr` 除以当时 ATR。
- `after_old_horizon`：路径是否超过日线 10 根、4H 18 根；仅用于描述等待，不是旧规则重放结果。
- `ledgers/`：每次候选提示的状态：observed、active_structure、conflicting_signal、invalid_atr、invalid_saved_pivot、tainted_structure_window。
- `summary.json`：每组事件数及完成成功率。`success_all_eligible` = 成功/(成功+失败+待定)；`upper_if_pending_succeed` 把待定全部视作成功所得上界；两者均排除数据中断。
- `by_direction.json`：同一账本按底/顶拆分，不是新实验；`median_success_* / p90_success_*` 只统计成功事件。
- `checks.json / independent_checks.json / report_checks.json`：协议与运行检查、独立逐事件重放、报告展示检查。

本目录所有成功率都是特定结构的确认比例，不是扣费交易胜率。全期/前段/近期会重复历史，不能合计 4,040 条记录当成独立样本。
