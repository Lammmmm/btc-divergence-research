# TradingView 对账：待完成

没有 TradingView 导出文件，因此当前检查状态为 PENDING。Python 内部的标量翻译与截断未来数据检查，不能替代平台对账。

1. 在 TradingView 使用 BINANCE 的 BTCUSDT USDT 永续合约、普通蜡烛图；核实具体合约标识与数据源。分别选择 4H 和 1D。
2. 导入 `pine/signal_audit_export.pine`。该脚本保留原算法，新增 20 个单指标多空信号绘图和 ATR。尚未在 TradingView 编译，应先检查编译结果。
3. 参数保持 Close、普通背离、拐点 5、检查 10 个拐点/100 根、等待确认、所有 10 个指标开启、外部指标关闭。该导出在每个已确认收盘上记录 0/1，不依据历史标签位置。
4. 提供足够早的数据预热，尽可能从 2020 年或更早开始。有限历史长度可能影响 EMA/OBV 初始化和拐点集合。导出图表数据时包含该脚本的所有绘图列，使用 UTC 时间戳。
5. 将导出文件保存在新的 `data/tradingview/` 目录，避免混同 Binance 原始数据。运行：

```sh
python src/compare_tradingview.py --timeframe 4h --csv data/tradingview/4h.csv
python src/compare_tradingview.py --timeframe 1d --csv data/tradingview/1d.csv
```

比较程序匹配开盘时间与 20 个信号列，输出所有差异；它只检查所提供行，不能自动保证完整覆盖或数据源正确。还需人工核对 OHLC、ATR 和预热范围，并抽查信号出现后的下根开盘成交。平台的策略成交模拟与本项目的 1H 保守执行可能不同，需要另行核对，不应只看净利润是否接近。

在两周期均完成充分覆盖对账前，报告中的“待对账”标记保留。不要用本项目自己的导出冒充独立 TradingView 导出。
