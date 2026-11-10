# 验证记录

## Personal 0.70.0-jp.5（2026-11-10）

发布源码：`da129a9214961540aa41a0a40fb1dea35fdba935`；
[完整 Windows 构建 #15](https://github.com/ZGHJP/Win-CodexBar/actions/runs/42790905487)；
[安装包与校验文件](https://github.com/ZGHJP/Win-CodexBar/releases/tag/personal-v0.70.0-jp.5)。

- 云端最终源码：前端 97 文件、662 测试；辅助层 12 测试；公开价格工具 4 测试；core 3699 通过、1 项既有忽略；CLI 1 测试；desktop 616 测试，均通过。
- 985 个译文键、TypeScript、生产前端、两份 Rust manifest 的格式/测试及 clippy 通过。clippy 沿用 `-D warnings -A clippy::double_must_use`，不是无豁免检查。
- 正式 Tauri CLI 编译生产资源；Windows x64 包含独立 Python 3.12.10、zstandard 0.25.0、公开价格种子及相关许可证。
- GitHub 下载的 ZIP 校验值与发布文件一致；包内 64 个文件逐个验证；来源 manifest 与本次源码一致。已用真实 Windows PowerShell 5.1 安装该下载包，安装后二进制与下载包一致，恢复普通托盘启动及辅助层心跳。
- 原症状有失败/通过对照：旧图表定时重读测试失败；旧生产快照顺序返回上一轮结果；混合扫描来源导致归属重复；旧首次导入遗漏 20 天前压缩日志；过期费率令常用 Codex 模型未定价。对应回归与新构建探针通过。
- 本机最终源码 desktop 原生 616 测试、公开费率原生 16 测试通过。此前本机完整 core 有一项 DeepInfra 连接分类测试因用户应用代理得到 502 而失败，未改用户代理来规避；干净 Windows CI 完整通过。
- 用户确认自编译价格修复版的今日费用和每日柱图恢复。此前同一原生窗口的周期聚合观察到自动增长；后台观察到扫描时间/用量推进且 pending 为零。最终下载包另做安装、进程、文件和后台扫描验证；Esc 停止界面工具后没有绕过它继续点击，未声称最终下载包已重新完成自动化窗口像素验证。
- API 403 回退到官方公开仓库有合成测试及实际获取成功记录；本机也观察过下载超时。新鲜目录不触发下载或写盘、失败续取保留旧目录的路径另经合成检查验证。导入保留明确上下文门槛，不代表完成 Fast、订阅/credits 或请求级计费审计。
- 核对上游至 `fd06294db4366bd1008ce2d32d6b6e7c0bb5b0d7`；基线仍 v0.70.0，未冒充完整最新版。多次锁屏、跨午夜和长期运行尚未完成稳定性验证。

ZIP SHA256：`de7a26d89a001194a4b14d9702df615ec132eb49e2142b35fa7933ce497f7623`。
桌面 SHA256：`c287fff125585703f8571101e7ce80c75028bee92ae752e50d8c583a9eb064e5`。
CLI SHA256：`50837825175d5383eb677cdfb1aea3778a0fd437210667a15c24010a8330d879`。
构建号：`personal-0.70.0-jp.5-gh-15`；原生文件版本保留上游 `0.70.0`。
真实账户、截图、会话、数据库及本机部署清单不提交 Git。

## Personal 0.70.0-jp.4（2026-11-06）

构建源码：`ee94dec04dc2ad4e70cebe18a5ca0cddb1068cc7`；
[Windows 云端构建 #8](https://github.com/ZGHJP/Win-CodexBar/actions/runs/42075088934)。
R6/R7 原提交未推送到此 fork，本次按维护记录重新实现，见
[变更说明](R6-R7-REIMPLEMENTATION.md)。

- 最终前端：97 文件、661 测试通过；TypeScript、984 个译文键及生产资源构建通过。
- Windows core：3,696 通过、1 项既有忽略；CLI 启动日志测试 1 项通过。
- Windows desktop：612 通过。Rust formatter 运行后源码无差异。
- 两份 manifest 的 release/all-target clippy 通过，使用既有
  `-D warnings -A clippy::double_must_use`；不是无豁免检查。
- 首轮完整 core 有 4 项失败。新增稀疏历史测试的预期错误地要求制造两天短尾；
  修正为保留九天不规则旧区间，并继续断言从最近边界倒推及不产生短尾。
  另外三项既有 Windows fixture 使用短临时路径，和规范化后的长路径比较失败；
  云端改用一致的 runner 临时目录后，完整测试重跑通过，没有跳过失败用例。
- 正式 Tauri 桌面及 CLI 构建成功；通过 Tauri CLI 嵌入生产资源。
- 构建包与 GitHub artifact SHA256 一致；包内每个文件校验通过；
  按用户安装后的二进制与包内哈希一致。
- 新构建的真实 Windows 窗口已展开并显示四段周期、更新时间、tokens 和估算费用。
  退出后以不同 PID 重启，四段起止不变，聚合用量继续更新。
  查询仍 pending 时恢复旧行、乱序请求、账户/周期隔离及坏存储的精确行为由组件测试覆盖；
  没有测量原生窗口第一帧耗时。验证后恢复普通启动。

Artifact ZIP SHA256：`e19fa4083958f227a17e7b3521933e5c9c5fad65869182ad8ab79061ff2336ae`。
桌面 EXE SHA256：`b53c583ee66b7d085bc087cbfd2e5127101078675947d5bff5193dd4df8657d1`。
个人构建号为 `personal-0.70.0-jp.4-gh-8`；原生文件版本保留上游 `0.70.0`。
价格、Fast、订阅/credits 换算及长期锁屏/跨午夜验证不在本次修复范围内。
真实账户、截图、用量和本机部署清单不提交到源码仓库。

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
