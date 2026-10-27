# ZGHJP 自用维护版

此分支用于维护 Windows 上已验证的本地修复，保留上游 MIT 许可及原作者归属。上游为 [nesszer/Win-CodexBar](https://github.com/nesszer/Win-CodexBar)，个人 fork 为 [ZGHJP/Win-CodexBar](https://github.com/ZGHJP/Win-CodexBar)。

## 分支与版本

- `main`：保留上游代码，不在这里叠加个人修复。
- `personal/stable`：以 v0.70.0（`f0b45ed`）为基础，保存当前本机 R5 修复的完整源码；维护版本 `0.70.0-jp.1`。
- `personal/integration`：把仍适用的通用修复移植到较新上游；通过检查后才用于升级。
- `fix/*`：每项通用修复一个分支，面向上游单独提交。

`personal/stable` 保留旧基线是为了重建目前已使用的修复，不代表它包含最新上游功能。不要把 integration 分支未完成的验证当作稳定版验证。

## 已纳入的修复

| 修复 | 范围 | 归属 |
| --- | --- | --- |
| 工作区快照最多复用五分钟、跨日失效 | Rust 工作区索引 | 上游 PR #779，作者 zhangkom；已在上游合并 |
| 同账户更新后重新读取每日图表、保留未定价 token 标记 | 托盘卡片 | 本地修复 |
| 切换 30 天／今天／7 天后不丢失已知模型定价 | Rust 费用扫描与缓存 | 本地修复 |
| 忽略未来重置预测造成的虚假历史边界，正确显示本地时间 | 配额历史及界面 | 本地修复 |
| 提供者更新后刷新顶部汇总，并阻止旧响应覆盖新结果 | 托盘 Overview | 本地修复 |
| 主程序 PID 更换后继续整理日志，退出后结束辅助进程 | `usage-compat` | 本机兼容层，单独维护 |

辅助层只随 stable 旧扫描器使用；升级上游前先测试原生分页、压缩和继承计数能力，确认需要后再迁移，避免重复整理。

## 计费口径与已知限制

用户使用 ChatGPT / Codex 官方订阅或 credits。应用当前显示的美元费用是按 API 单价计算的等价估算，不能代表订阅实际扣费、剩余额度或 credits 账单。

2026-10-27 核对的[官方 Codex 计费说明](https://learn.chatgpt.com/docs/pricing)：Standard 每百万输入／缓存输入／输出 tokens，Sol 6.1 为 50 / 2.5 / 250 credits，Astra 6 为 250 / 25 / 1250 credits。Codex credits 不单独收取 cache-write 费用。Fast 的套餐内额度消耗倍数为 2.5，购买 credits 的倍数为 2。套餐内额度并不能仅凭公开 token 单价精确还原。

API 模型页目前给出的长上下文加价门槛仍为单次输入超过 272K，不能据此推断订阅／credits 也使用同一门槛，更没有确认到 475K 的套餐计费规则。

待解决问题：

1. 旧版 Sol 6.1 的 models.dev 定价使用 200K 门槛，与当前 API 文档的 272K 不一致。这里只记录，未冒充已修复。
2. Fast 模型支持表与 `service_tier=fast` 识别不完整；保存 turn_id 只是补齐关联证据，不能保证所有 Fast 请求已计入。
3. 需要审计每日聚合是否误用请求级长上下文门槛；不能用一天累计输入判断单次请求是否加价。
4. 多次锁屏、跨午夜及长期运行的完整稳定性尚未证明。

## 上游贡献

2026-10-27 已分别提交以下 PR，目前等待上游审查；它们都基于上游 `main`，互不依赖：

- [#1036：切换历史范围后丢失已知模型定价](https://github.com/nesszer/Win-CodexBar/pull/1036)
- [#1037：重置预测抖动产生几分钟的虚假历史周期](https://github.com/nesszer/Win-CodexBar/pull/1037)
- [#1038：托盘顶部汇总不随提供者更新](https://github.com/nesszer/Win-CodexBar/pull/1038)
- [#1039：每日图表不更新及未定价 token 日不可见](https://github.com/nesszer/Win-CodexBar/pull/1039)

个人辅助层没有混入这些 PR。旧表格的时间与列标题改动仅保留在 stable，因为新版上游已经替换了该界面。

## 构建与检查

前提：Windows、Git、项目锁定的 pnpm、Rust 与 Windows C++ 构建环境；辅助层使用 Python 3.12 和 `zstandard==0.25.0`。已有 WSL cargo-xwin 环境也可沿用，见 `build-wsl.sh`。

从仓库根目录运行 `powershell -File personal/build.ps1`，构建只写入输出目录，不安装、不替换正在运行的应用。Python 依赖安装到独立目录，不要复制账户 home 目录来“打包依赖”。

辅助层测试：`python -m unittest discover -s personal/usage-compat -p test_compat.py -v`。

前端：在 `apps/desktop-tauri` 执行 `pnpm exec vitest run --config ../../personal/vitest.config.ts`。该配置只固定测试进程的英文区域格式，不更改用户系统语言。

Rust：两份 manifest 的 tests、fmt 和 clippy；界面变更另需新构建的 Windows 实测。已安装 R5 的历史证据在 `VALIDATION.md`，每次发布必须重新记录对应源码、构建号、哈希和检查结果。

## 升级、发布和回滚

1. 获取上游 main，逐项检查哪些补丁已被上游吸收；#779 不再重复提交。
2. 在 integration 上迁移仍需要的提交，运行回归检查。每个上游 PR 只包含一个修复，不带个人辅助层、账户资料或机器路径。
3. 形成明确的版本标记、构建记录和 SHA-256 后再部署。当前整理不会自动更换本机 R5 程序。
4. 当前原生更新器仍指向上游 release。安装自用构建前，应在应用设置中关闭自动下载安装，避免上游更新覆盖补丁；本次整理不修改用户设置。自用更新渠道独立发布前，先手动验证升级。
5. 部署前备份被替换的可执行文件及版本清单。回滚前校验当前文件与部署清单一致，再恢复备份；不要清空用量数据或原始会话。

代码仓库只保存源码、合成测试、脱敏维护说明。`usage-compat/home`、认证文件、数据库、真实会话、状态日志、个人运行清单及构建输出均不提交。现有本机回滚脚本继续保存在原维护目录，不把带本机状态的脚本直接公开。
