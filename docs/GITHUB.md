# GitHub 保存步骤

公开仓库：https://github.com/Lammmmm/btc-divergence-research

归档发布：https://github.com/Lammmmm/btc-divergence-research/releases/tag/research-2026-10-17

仓库主分支保存本目录的全部研究文件，包括 data、results、archive 和 manifest。Release 附件保存完整 ZIP、校验文件、两份前期 ZIP 快照，以及早期表格、HTML 和 Pine 显示版本。ZIP 放在 Release，避免在 Git 文件历史里重复保存整包。

下载和验证可以使用 Git 或 GitHub Desktop。网页逐个上传不适合本项目大量逐笔文件。

```sh
git clone https://github.com/Lammmmm/btc-divergence-research.git
cd btc-divergence-research
python src/check_manifest.py
```

后续实验建议先提交到新分支；修改完成后重新生成校验清单，再提交实际变更。例如：

```sh
git switch -c research-update
# 执行实验并检查报告后：
python src/package_release.py
python src/check_manifest.py
git add .
git commit -m "Update divergence research and verification"
git push -u origin research-update
```

以上新分支命令只是后续更新示例。无需提供 Binance 密钥。`.gitignore` 只忽略 Python 环境、缓存、密钥类文件和编辑器文件，**没有忽略原始行情和测试结果**。

发布前先执行 `python src/check_manifest.py`，确认收到的快照未变化。后续实验建议用版本标签或新分支保存协议变更；原始数据更新需建立新快照并重新生成校验清单。

许可证覆盖项目研究代码，不代表重新授权第三方数据；保留 LICENSE、NOTICE、原始 Pine 署名及接口来源。
