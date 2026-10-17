# BTCUSDT 聚合背离单指标研究

BINANCE BTCUSDT USDT 永续合约，10 个内置指标分别测试 4H 和 1D。原始数据、代码、协议、逐根信号、逐笔交易、每组资金曲线、检查结果及前一轮研究文件全部保留。

[公开 GitHub 仓库](https://github.com/Lammmmm/btc-divergence-research) · [完整 ZIP、历史版本及原始交付文件](https://github.com/Lammmmm/btc-divergence-research/releases/tag/research-2026-10-17)。仓库保存展开后的研究目录，Release 保存本次完整归档、两份前期快照以及早期表格、HTML 和 Pine 显示版本。

**当前状态：历史研究完成；TradingView 对账和未来向前验证待完成。**

**显示微调 v3.1：** [完整源码](pine/Hist_Divergence_State_v3_1.pine) / [变更说明](docs/HIST_STATE_V3_1_STYLE.md)。线宽 2、底背离深橙色、顶背离深蓝色，适配浅黄/浅绿背景；状态规则沿用 v3。

**最新显示版本：Hist 背离状态 0–100 v3。** [Pine 源码](pine/Hist_Divergence_State_v3.pine) / [说明与测试范围](docs/HIST_STATE_V3_GUIDE.md)。底背离生效固定在 0 并变黄，顶背离生效固定在 100 并变蓝；观察段灰色 10–90，潜在形态用灰色 5/95，结束后离开边界并回灰。坐标是状态编码，不是胜率。保留原信号、结构判定及进度面板。复现：`python run_hist_state_v3.py`。[v3 发布与完整研究包](https://github.com/Lammmmm/btc-divergence-research/releases/tag/hist-lifecycle-v3)。

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
