# CodexBar jp.6 凭据修复安装入口

[下载 Windows x64 安装入口 ZIP](https://github.com/ZGHJP/Win-CodexBar/raw/refs/heads/downloads-jp6/CodexBar-0.70.0-jp.6-windows-x64-setup.zip)

解压整个目录，退出已有 CodexBar 并等待辅助进程结束，然后运行 `Install.cmd`。需要网络下载约 38 MB 的已编译程序及系统 WebView2；无需 Python、Rust 或 Visual Studio。目标电脑使用自己的 Codex 登录，不包含原电脑的账户或用量。

**不要单独安装旧 jp.5 来验证此修复**：它仍可能创建凭据硬链接。此入口先校验原编译包，再更新兼容层和安装逻辑为 jp.6，启动前迁移标准及商店版缓存目录的旧链接。原始凭据不被改写，不清空回收站。

桌面与 CLI 的 Rust / 前端源码没有改变，沿用已完整测试的 jp.5 二进制；此更新没有重新编译相同原生组件。“关于”页中的原生编译号仍可能显示 jp.5-gh-15。安装清单分别记录兼容层源码与原生编译来源，兼容层版本为 jp.6。

- [凭据修复源码](https://github.com/ZGHJP/Win-CodexBar/commit/dbfbd8d1a730769529dfb8e31f74cefb366a6043)
- [原生编译来源](https://github.com/ZGHJP/Win-CodexBar/commit/da129a9214961540aa41a0a40fb1dea35fdba935)
- [原生完整检查](https://github.com/ZGHJP/Win-CodexBar/actions/runs/42790905487)
- 本次兼容层 16 项、价格工具 4 项测试通过；覆盖独立文件、认证更新/退出、失败保留原件、WAL 一致性和商店版缓存迁移。
- 安装入口 SHA256：`f29aeddc8abc973cd299ebcdaba2f0a6a0230d8afb99fea97d6d56cc9fa6f5ac`。

美元仍是 API 等价估算；Fast、订阅/credits 和长期锁屏稳定性不是本次修复的保证范围。旧辅助脚本备份不应重新启用，否则可能重建链接。
