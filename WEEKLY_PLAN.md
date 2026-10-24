# 7-Day Dual-Engine Project Schedule (存量项目自进化 + 思维外推造新物)

Window: `2026-10-25` -> `2026-10-31`
Strategy: **绝不把已有项目简单复制重包；只做两件事：(1) 在现有本地项目上直接发现痛点并升级；(2) 从思考日记与日常卡点外推孵化还没做过的全新项目。**

---

## Day 1 (`2026-10-25`) — `loop-engineer` [底座引擎]
- **Mode**: `extrapolate_new` (`/Users/huanghaodong/Desktop/project`)
- **交付**: 多源对话/日记采集器、零泄漏隐私安全门闩、双引擎调度器（`self_optimize` + `extrapolate_new`）与后台守护进程。

## Day 2 (`2026-10-26`) — `netmap` [引擎 A：现有项目直接自优化]
- **Mode**: `self_optimize` (直接优化 [`/Users/huanghaodong/Desktop/cs/netmap`](file:///Users/huanghaodong/Desktop/cs/netmap) 并推送至 GitHub)
- **痛点推导**: 10月24日晚你排查家里 Wi-Fi 手机刷不出视频、发现本机 `Misty` 回国节点晚高峰限速且劫持海外流量；但现有的 `netmap` 只会静态画代理路径和查出口 IP（`ip-api.com`），没法检测「分流错配」和「各链路真实流媒体/AI 吞吐掉速」。
- **自动升级动作**:
  - `nm-m1` `feat(probe)`: 在 `netmap/server.py` 直接增加「物理直连 vs Misty 系统代理 vs VPS 隧道」三路并发 TTFB 探针（实测 YouTube / B站 / Claude 真实首包延迟）。
  - `nm-m2` `feat(doctor)`: 在 `netmap` 前端面板新增 `Split-Tunnel Doctor（分流错配告警）`，一旦海外站点误走回国代理或延迟异常直接标红定位。

## Day 3 & Day 4 (`2026-10-27` ~ `10-28`) — `single-thread-lock` [引擎 B：从思考日记外推的全新项目]
- **Mode**: `extrapolate_new` (`/Users/huanghaodong/Desktop/project/workspaces/single-thread-lock`)
- **思维推导**: 你在 [`10-09 虚构过载与启动阻力`](file:///Users/huanghaodong/Documents/diary/2026-10-09-future-overload-and-activation-friction.md) 和 [`09-15 概率直觉与具身状态锚定`](file:///Users/huanghaodong/Documents/diary/2026-09-15-bayes-intuition-and-state-anchoring.md) 中剖析过自己为什么弃用传统待办系统（`Life OS`）：网状思维看到长列表会瞬间把 50 件事加载进大脑运行内存（Phantom Overload）导致瘫痪，只有「全量倾倒存盘 + 屏幕上只留唯一下一个 10 分钟物理微切片」才能消除启动摩擦力。
- **全新造物动作**:
  - `stl-m1` `feat(vault)`: 实现「零列表暗盒倾倒池（RAM-to-Disk）」与 10 分钟微切片拆解器（严禁展示全景待办列表）。
  - `stl-m2` `feat(aperture)`: 实现「单孔终端焦点锁（Single-Aperture TUI）」，内置 60 秒冥想无状态重置（Ground-State Reset）引导，每次全屏只暴露 1 个 10 分钟微动作，做完才解锁下一个。

## Day 4 & Day 5 (`2026-10-28` ~ `10-29`) — `submission-truth-auditor` [引擎 B：从日常交作业痛点外推的全新项目]
- **Mode**: `extrapolate_new` (`/Users/huanghaodong/Desktop/project/workspaces/submission-truth-auditor`)
- **痛点推导**: 10月24日你交 `FIT1043 A2` 前不得不逐条重跑 Shell 命令去核对报告/PDF 里的数字（抓出 `127 -> 118` 不一致、补时区说明、查 18 页是否溢出），10月22日又专门准备 `FIT1008 D1` Tutor Rediscuss 口试追问（为什么 `count_lt()` 是 `O(h)`）。
- **全新造物动作**:
  - `sta-m1` `feat(auditor)`: 自动提取 Markdown/PDF 报告中的所有统计数值声明，并与脚本/代码的真实标准输出做交叉比对，抓出前文写 127 后文写 118 的手滑不一致。
  - `sta-m2` `feat(viva)`: 扫描 C++/Python 源码的 AST 与复杂度注释，自动模拟刻薄 Tutor 生成 5 道最可能被问倒的 Live Coding / Viva 口试追问与标准防御回答。

## Day 5 (`2026-10-29`) — `moodle-mcp` 时区与延期守卫补丁 [引擎 A：现有项目直接自优化]
- **Mode**: `self_optimize` (直接优化 [`/Users/huanghaodong/Desktop/cs/moodle-mcp`](file:///Users/huanghaodong/Desktop/cs/moodle-mcp))
- **痛点推导**: 10月23日查 `FIT1043` 截止时间时发现 Moodle 默认按墨尔本 `AEDT (UTC+11)` 展示 `11:55 PM`（实为大马时间当晚 `20:55 MYT`，差点误判 3 小时）。
- **自动升级动作**:
  - `map-m1` `feat(deadline-myt)`: 直接给 `moodle-mcp` 增加 `AEDT -> MYT` 自动时区折算、剩余小时倒计时与 `Short Extension` 顺延窗口自动标注。

## Day 6 & Day 7 (`2026-10-30` ~ `10-31`) — `dex-cex-friction-radar` [引擎 B：从商业顿悟与区块链兴趣外推的全新项目]
- **Mode**: `extrapolate_new` (`/Users/huanghaodong/Desktop/project/workspaces/dex-cex-friction-radar`)
- **思维推导**: 结合你在 [`09-17 区块链与量化日记`](file:///Users/huanghaodong/Documents/diary/2026-09-17-blockchain-quant-and-fomo-impostor-loop.md) 中对合规数字资产/链上量化的向往、停掉单向 `okx-grid-bot` 后的思考，以及 [`10-16 喝水顿悟交易成本经济学`](file:///Users/huanghaodong/Documents/diary/2026-10-16-real-world-closed-loop-and-ai-native-product-leverage.md)（套利空间的本质是高交付/交易摩擦）。
- **全新造物动作**:
  - `dcf-m1` `feat(friction-engine)`: 构建链上 DEX（Uniswap v3 / Base 集中流动性池）与 CEX 永续合约的「全摩擦成本（Gas + 池子冲击成本 + 资金费率）净基差套利雷达」。
  - `dcf-m2` `feat(contracts)`: 编写配套的 Solidity `AtomicFrictionVault.sol` 智能合约（含最小净利硬门闩与闪电再平衡 Hook 测试）。
