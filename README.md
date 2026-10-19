# BTCUSDT 聚合背离单指标研究

BINANCE BTCUSDT USDT 永续合约，10 个内置指标分别测试 4H 和 1D。原始数据、代码、协议、逐根信号、逐笔交易、每组资金曲线、检查结果及前一轮研究文件全部保留。

[公开 GitHub 仓库](https://github.com/Lammmmm/btc-divergence-research) · [完整 ZIP、历史版本及原始交付文件](https://github.com/Lammmmm/btc-divergence-research/releases/tag/research-2026-10-17)。仓库保存展开后的研究目录，Release 保存本次完整归档、两份前期快照以及早期表格、HTML 和 Pine 显示版本。

**当前状态：历史研究完成；TradingView 对账和未来向前验证待完成。**

## 当前指标与完整说明

**当前修正版：Hist Line v4.5.1。** [源码](pine/Hist_Divergence_Line_v4_5_1.pine) · [修正说明](docs/HIST_LINE_V4_5_1_FIX.md) · [完整下载](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-5-1)。默认恢复持续横线：正式顶背离100横线红色、底背离0横线蓝色，所有中间折线及进出横线的斜线灰色。形成阶段保留平滑，正式事件直接固定端点；MACD及全部正式规则未改。14,798根双模式显示检查通过，彩色斜线和中间线段均为0。TradingView 4H/1D已运行核对。

**保留显示版本：Hist Line v4.5（中间结构曲线配色已由v4.5.1修正）。** [源码](pine/Hist_Divergence_Line_v4_5.pine) · [平滑公式与使用说明](docs/HIST_LINE_V4_5_GUIDE.md) · [下载](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-5)。只对最终显示曲线增加因果平滑，默认周期3、单根变化上限15点；关闭即可恢复v4.4原值，横线模式不受影响。MACD、正式信号、确认/失效及配色规则未改。4H和1D的平均单根变化分别由7.74/9.60点降到4.28/5.44点；数值会滞后，面板保留“平滑 / 原值”，状态、风险和变色不等待平滑。14,798根显示回归通过，TradingView 4H/1D已编译运行。非概率，不代表收益或准确率提升。复现：`python src/verify_hist_line_v45.py`。

**保留显示版本：Hist Line v4.4。** [源码](pine/Hist_Divergence_Line_v4_4.pine) · [完整说明](docs/HIST_LINE_V4_4_GUIDE.md) · [下载归档](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-4)。默认改为结构位置：触发后0表示冻结失效边界、100表示冻结反转确认边界，红顶蓝底；可切回与v4.3.2完全一致的持续横线模式。面板明确“已触发／等待结构结果”。正式信号、形成评分、确认、失效和警报代码未改，不设置超时。14,798根显示回归与8项边界断言通过；TradingView已在4H、1D编译运行，并核对日线模式切换。百分比不是概率，收益仍参考下方同规则回测。复现：`python src/verify_hist_line_v44.py`。

**当前版本专项回测（2026-10-19）：** [完整结果与方法](reports/HIST_V432_BACKTEST.md) · [离线 HTML 报告](reports/hist_v432_backtest.html) · [逐事件、逐笔交易与检查](results/hist_v432_backtest/) · [冻结方案](config/hist_v432_backtest.json)。只测 v4.3.2 正式事件启动，沿用 2021-01-01 至 2026-10-15 的同一历史快照。日线结构成功 27/38（71.05%），4H 83/201（41.29%），各有 1 个待定。套用旧 ATR 交易规则后的累计净收益分别 +9.46%、+3.05%；手续费/滑点翻倍后为 +8.98%、−3.37%。结构成功率不是交易胜率。日线只有 38 笔交易，近期表现减弱；完整 TradingView 历史导出对账仍待完成。25 项既有测试和独立逐笔复核通过，原指标未修改。复现：`python run_hist_v432_backtest.py`。

**保留修复版：Hist Line v4.3.2。** [源码](pine/Hist_Divergence_Line_v4_3_2.pine) · [修复说明](docs/HIST_LINE_V4_3_2_SEGMENTS.md) · [完整下载](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-3-2)。修复进入横线的斜线提前变红/蓝：只有同一次正式事件内的 0/100 水平段着色，其余连接保持灰色且不断线。主线数值、触发、确认、失效和警报不变。已对 14,798 根保存记录检查，彩色斜线为 0，并在 TradingView 核对实际绘制。

**保留配色版本：Hist Line v4.3.1。** [源码](pine/Hist_Divergence_Line_v4_3_1.pine) · [配色说明](docs/HIST_LINE_V4_3_1_COLORS.md) · [完整下载](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-3-1)。正式顶背离生效显示红色，正式底背离生效显示蓝色，其他阶段全部灰色；横线和全部判定规则保持 v4.3 不变。风险信息保留在面板及数据窗口，不再覆盖主线颜色。已在 TradingView 4H、1D 运行检查，旧版保留。

**保留版本：Hist Line v4.3 背离持续横线。** [新版代码](pine/Hist_Divergence_Line_v4_3.pine) · [使用说明](docs/HIST_LINE_V4_3_GUIDE.md) · [完整下载包](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-3-tested)。底背离生效期间固定 0，顶背离固定 100，直到原规则确认或失效；取消断口，所有阶段连续连接。风险实时变红，真实结构位置保留在数据窗口。正式规则与 v4.2 完全相同。14,798 根离线显示检查通过；TradingView 已保存独立脚本并回读核对一致，已在 BTCUSDT 永续 4H、1D 编译运行：底背离固定 0、顶背离固定 100。[实测记录](results/hist_line_v4_3/tradingview_checks.json)。

**保留的上一版本：Hist Line v4.2 枢轴动态进度。** [完整源码](pine/Hist_Divergence_Line_v4_2.pine) · [新版完整说明及 v4.1 对比](docs/HIST_LINE_V4_2_GUIDE.md) · [完整归档下载](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-2)。

v4.2 重新设计展示评分：以原始历史 Close 枢轴及同根 Hist 为参照，关系临界为 50，价格和 Hist 共同约束，长短波动尺度防止分母过小，稳定保持候选及显示方向。同一参照内连续，跨参照/方向/阶段不强行连接。结构位置保持原值，风险颜色即时更新。正式背离、确认、失效核心与 v4.1 逐字一致；旧版和历史研究不覆盖。百分比不是成功概率。

13 项测试及 14,798 根离线显示回放通过，已在 TradingView 的 BINANCE:BTCUSDT.P 4H、1D 编译运行。完整历史 Pine 导出对账仍待完成。[离线检查](results/hist_line_v4_2/checks.json) · [实图验证记录](results/hist_line_v4_2/tradingview_checks.json)。复现：`python run_hist_line_v42.py`。

**旧版手册保留：** [v4.1 完整手册](docs/HIST_INDICATOR_MANUAL.md) · [v4.1 历史归档](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-line-v4-1-manual-2026-10-18)。其中旧评分、平滑和灰色连接规则仅适用于 v4.1，使用新版请以上方 v4.2 说明为准。

**保留的上一显示版本：连续单折线 v4.1。** [完整 Pine](pine/Hist_Divergence_Line_v4_1.pine) / [显示口径与限制](docs/HIST_LINE_V4_1_GUIDE.md)。只有一条连续细线，无密集图形标记；形成阶段轻微平滑、稳定选择主要方向，结构阶段保持真实位置，正式触发不再人为拉到 100 形成尖峰。参照或阶段切换以灰色连接段和数据窗口记录区分，风险红色优先。原始信号及候选算法与 v4 完全一致。复现显示检查：`python src/verify_hist_line_v41.py`。

**上一版：枢轴形成与结构进度 v4。** [完整 Pine](pine/Hist_Divergence_Progress_v4.pine) / [精确公式、阶段和复盘限制](docs/HIST_PROGRESS_V4_GUIDE.md)。形成阶段以原始已确认 Close 枢轴及同根 Hist 为基准，价格按 ATR、Hist 按近期标准差归一化，综合取两项较低值且最高 99；正式触发以 100 处三角标记。之后显示冻结失效价 0 到确认价 100 的结构位置。触线立即预警、正式结果等收盘。原始正式信号与研究规则保持一致。复现：`python run_hist_progress_v4.py`。[v4 完整发布](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-progress-v4)。

**显示微调 v3.1：** [完整源码](pine/Hist_Divergence_State_v3_1.pine) / [变更说明](docs/HIST_STATE_V3_1_STYLE.md)。线宽 2、底背离深橙色、顶背离深蓝色，适配浅黄/浅绿背景；状态规则沿用 v3。

**历史显示版本：Hist 背离状态 0–100 v3。** [Pine 源码](pine/Hist_Divergence_State_v3.pine) / [说明与测试范围](docs/HIST_STATE_V3_GUIDE.md)。底背离生效固定在 0 并变黄，顶背离生效固定在 100 并变蓝；观察段灰色 10–90，潜在形态用灰色 5/95，结束后离开边界并回灰。坐标是状态编码，不是胜率。保留原信号、结构判定及进度面板。复现：`python run_hist_state_v3.py`。[v3 发布与完整研究包](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-lifecycle-v3)。

**保留历史显示版本：Hist 背离折线 v2。** [Pine 源码](pine/Hist_Divergence_Line_v2.pine) / [使用说明](docs/HIST_LINE_V2_GUIDE.md)。连续 Hist 折线：普通灰色、底背离生效黄色、顶背离生效蓝色，事件结束恢复灰色；无柱状图、竖向色带或背离连线，保留进度面板。仅调整显示，背离与结构跟踪逻辑、警报规则均与 v1 一致。[v2 发布及完整研究包](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-lifecycle-v2)。

**新增可用副图：Hist 背离全过程 v1。** [Pine v6 源码](pine/Hist_Divergence_Lifecycle_v1.pine) / [安装与使用说明](docs/HIST_LIFECYCLE_GUIDE.md)。显示潜在形态、生效、等待、反转确认和结构失效；价格进度不是胜率。已在 TradingView 的 BINANCE:BTCUSDT.P 日线与 4H 编译运行，保存源码与本地文件比对一致；完整历史导出对账仍待完成。离线检查：`python run_hist_lifecycle.py`。这不会改变下方旧回测结果或其统计口径。

[副图 v1 发布与更新后的完整研究包](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-lifecycle-v1)。旧 `research-2026-10-17` 发布保留当时快照，不覆盖。

**最新：允许横盘等待的结构反转测试。** 10 个指标分别测试日线和 4H，不组合、不优化；取消固定等待期限，以信号确认时冻结的价格结构判定成功或失效。[本轮结论](reports/STRUCTURE_REVERSAL.md) / [完整报告](reports/structure_reversal.html) / [精确规则及限制](docs/STRUCTURE_REVERSAL_METHOD.md)。20 组主比较，以及各自前段、近期诊断，共 60 个账本；6 项合成测试和 4,040 条事件记录的独立复核通过。这些记录含重复的历史区间，不能合并为独立样本。单独复现：`python run_structure.py`。本轮统计结构确认率，不计算交易收益；旧研究全部保留。

**新增：围绕日常参考用途的集中检验。** 只比较 12 种预设设置，另加 1 种明确标记为探索性的日线精简设置；不扩大参数搜索。[实用设置结论](reports/REFERENCE_USE.md) / [完整实用报告](reports/reference_use.html)。该轮评价信号后的顺逆波动，不是账户收益回测。单独重跑命令：`python run_reference.py`。原来的 500 组交易研究及结果完整保留。

- [结果摘要](reports/SUMMARY.md)
- [完整 HTML 报告](reports/report.html)：下载后用浏览器打开；无需联网。
- [冻结测试方案](config/protocol.json)及[数据质量修订](config/data_quality_amendment.json)
- [方法、指标定义和限制](docs/METHODOLOGY.md)
- [字段说明](docs/DATA_DICTIONARY.md)
- [TradingView 对账步骤](docs/TRADINGVIEW.md)
- [未来模拟验证方案](docs/FORWARD_PLAN.md)
- [上传 GitHub 的步骤](docs/GITHUB.md)

## 这次测试做了什么

2020 年行情用于预热，正式区间为 2021-01-01 至 2026-10-15 UTC，排除截止时尚未完成的交易。基础策略为收盘确认、下一根开盘入场，ATR(14) × 1.5 止损、2R 止盈、最多持有 10 根，单笔计划风险 0.5%，名义仓位上限 1 倍净值。每组独立 10,000 USDT 账户，不同时持有多个头寸，持仓中忽略后续信号。

共 500 个实验账本：

| 类型 | 组数 |
|---|---:|
| 基础风险策略：10 指标 × 2 周期 | 20 |
| 7 个单因素敏感性场景 × 20 | 140 |
| 固定持有 10 根、近 1 倍仓位基准 | 20 |
| 8 个滚动窗口 × 开发/评估 × 20 | 320 |

这是 500 个实验账本，不是 500 套独立策略，也不是独立验证样本。策略之间、滚动开发区间之间会重复使用历史行情。2026 年最后评估窗口不足半年，单独标记。

## 复现

在 Python 3.11 或更新版本的独立环境中执行：

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python src/check_manifest.py
python run_all.py
```

已随包提供全部数据，重跑不需要联网、Binance 账户或 API 密钥。运行会重新生成 `results/`、`reports/` 和 `logs/`，原始数据不会被修改。先检查发布快照的 SHA256，再运行复现。运行后日志、平台信息或依赖版本可能不同。

`run_all.py` 依次执行合成测试、全部历史实验、独立账务复核及报告生成。每一步的标准输出和错误输出保存到 `logs/`，任何一步失败即停止。逐笔文件使用固定 gzip 时间头，方便同环境下比较重跑结果。

两轮参考用途扩展分别执行 `python run_reference.py` 和 `python run_structure.py`，不包含在 `run_all.py` 中。需要重新打包时执行 `python src/package_release.py`，它会更新清单和工作目录外同名 ZIP，并校验归档内容；请先保留需要的旧版本。

补充数据下载器 `src/fetch_supplemental.py` 只访问公共行情端点，并复用已存在文件；原始 4H/1D/资金费下载脚本保存在 `archive/previous_run/fetch_market.py`。若重新下载，请在新目录进行并保留新快照，不覆盖本研究数据。

## 目录

```text
config/                  冻结参数、原始协议哈希、数据质量修订
data/raw/                Binance 原始 JSON、获取记录、异常复查响应
data/derived/            资金费标记价格来源、逐根指标与信号
src/                     信号移植、模拟引擎、复核、报告和对账程序
tests/                   独立合成测试
pine/                    用户原始 Pine、显示版、待编译的信号导出版
results/summary.json      所有 500 组统计
results/trades/           每组全部逐笔交易 JSONL.GZ
results/equity/           每组持仓时小时权益及入场前平仓权益
results/signal_ledger/    每个信号的入场/忽略/剔除原因
results/breakdowns.json   多空、年度、市场状态分组
results/uncertainty.json  区块重采样区间
reports/                 HTML 完整报告和 Markdown 摘要
logs/                    复现日志、研究过程记录
archive/previous_run/     此前基准与探索研究的代码、结果和报告
manifest.sha256.json     发布快照文件清单与校验值
```

JSONL.GZ 是 gzip 压缩的逐行 JSON，不是加密文件。Python 标准库可直接读取：

```python
import gzip, json
with gzip.open('results/trades/1d_Hist_risk_base_full.jsonl.gz', 'rt', encoding='utf-8') as f:
    trades = [json.loads(line) for line in f]
print(trades[0])
```

## 尚未完成的验证

1. 尚未取得 TradingView 导出数据，不能声称与 TradingView 完全一致。`pine/signal_audit_export.pine` 已准备，尚未在 TradingView 编译；对账程序已准备。
2. 未来行情尚未发生，不能完成真实向前验证。预先固定的方案见 `docs/FORWARD_PLAN.md`。
3. 现有历史区间已被查看，滚动评估是历史稳健性诊断，不是未接触过的数据。

## 归属与许可

原始 Pine 背离逻辑由 **LonesomeTheBlue** 编写，保留 MPL-2.0 声明。Python 信号移植及本包新增研究代码按 MPL-2.0 提供，详见 `LICENSE` 和 `NOTICE`。第三方交易所行情与文档引用不因本项目许可而重新授权。没有账户信息、下单功能或 API 密钥。
