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

## 较新上游的集成验证（2026-10-27）

上游基线：`31b10ce42993d3be2f041e169e82ef174d24c7ec`。
已测试的四项修复组合：fork `personal/integration`，提交 `b27e6ba81be915b4e4416ef9146058c39626f83a`。本地构建时的等价源码树由各独立修复组合而成，发布时核对 tree SHA 一致；GitHub API 提交元数据与本地提交元数据可以不同。

- Windows core：5,495 通过、2 项忽略。首次执行因未编译 `fake_grok_acp` 和 `fake_kiro_cli` 而有 21 项失败；补编译这两个仓库自带的模拟程序后，完整重跑通过。没有通过跳过失败用例来得到通过结果。
- Windows desktop：834 通过。
- 前端：168 文件、1,671 测试通过。旧“同一天不重新取数”的断言已在原有专用图表测试中更新；新未定价标记测试在修改前确实失败。
- 前端类型检查、语言键检查、生产构建通过。构建仍有既有大资源块提示。
- `cargo fmt --all --check` 通过。两份 manifest 的 all-target clippy 通过，使用 `-D warnings -A clippy::double_must_use`，以适配本机 Rust 1.99.1 与既有 async-trait 代码；没有把它描述成无豁免通过。
- 按要求进行了最终差异的结构自审：复用已有图表测试入口，保留 Rust 提供者模块边界，没有增加依赖；排除了新版不再使用的旧表格改动。
- [截图](tray-proof-310px.png)：Chrome / Chromium on Windows，310×1032，mocked IPC，仅含合成账户与用量。证明当前集成界面的布局；自动刷新、乱序响应和 null 价格标记的精确行为由组件回归测试覆盖。它不证明新的 WebView2 原生窗口行为或长期锁屏稳定性。

主要构建检查：

```text
cargo xwin test -p codexbar --lib --release --target x86_64-pc-windows-msvc --no-run
cargo xwin test --manifest-path apps/desktop-tauri/src-tauri/Cargo.toml --release --target x86_64-pc-windows-msvc --no-run
cargo xwin build -p codexbar --example fake_grok_acp --example fake_kiro_cli --release --target x86_64-pc-windows-msvc
cargo xwin clippy --manifest-path rust/Cargo.toml --target x86_64-pc-windows-msvc --all-targets -- -D warnings -A clippy::double_must_use
cargo xwin clippy --manifest-path apps/desktop-tauri/src-tauri/Cargo.toml --target x86_64-pc-windows-msvc --all-targets -- -D warnings -A clippy::double_must_use
cargo fmt --all --check
```

编译出的测试 EXE 在 Windows 上执行。前端通过项目锁定版本的 Vitest 运行，额外加载测试进程专用 en-US 格式配置，未改变系统区域设置。上述是四项独立修复组合后的本地检查，不是每个 PR 都完成了托管 CI；上游针对 fork PR 的 CI 与审查规则仍适用。
