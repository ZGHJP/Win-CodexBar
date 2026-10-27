# 验证记录

## 当前安装版的历史验证

对应构建：`pr779-trayfix-20261026-r5`；辅助层：20261026-r2，投影 schema 4。

- 辅助层九项合成回归测试通过，涵盖主进程接替、短暂重启空档、真实退出、压缩源文件、继承计数、轮次元数据及旧投影升级。
- 前端 96 文件、631 测试通过；类型检查、语言键检查与正式资源构建通过。
- R4 Rust core：3,689 通过、1 项忽略；desktop：612 通过。R5 未更改 Rust 计费实现及 CLI。
- Rust 1.99.1 的 clippy 需要对既有 `clippy::double_must_use` 警告作兼容豁免，不能把该结果写成无豁免通过。
- Windows 实测：同一个托盘窗口保持打开，未手动刷新或重开，顶部汇总、明细和今日金额随新增用量变化并保持一致。
- 主程序换 PID 后，辅助进程保持运行，投影心跳继续更新。

这组历史证据证明 R5 当时的短期自动更新行为；不代表所有锁屏场景、跨午夜、长期运行或 Fast 计价已被完整验证。

## 本次源码归档

`personal/stable` 的五组原生修复文件与已部署 R5 源码逐字节一致。辅助层仅归档 `compat.py`、`test_compat.py`、`Launcher.cs`，不归档运行数据。

本次新增构建及检查结果另按实际运行追加，不能把上面的历史验证自动套用到 integration 或新发行包。

2026-10-27 源码归档后的复验：

- `personal/build.ps1 -FrontendOnly` 完成冻结依赖安装、译文检查、类型检查和生产前端构建。
- `vitest run --config ../../personal/vitest.config.ts`：96 文件、631 测试通过。
- `python -m unittest discover -s personal/usage-compat -p test_compat.py -v`：9 测试通过（复用已安装的 zstandard 0.25.0）。
- 发布通过 GitHub Git Trees API 完成；每次写入均核对 API 返回的 tree SHA 与本地提交的 tree SHA 完全相同。发布的是可重建源码，没有在此次整理中替换本机 R5 可执行文件或发布新的安装包。
