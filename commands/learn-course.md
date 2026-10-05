---
description: 把 B 站网课（BV号或链接）蒸馏成知识库/讲师人格，并可落库 Obsidian wiki
argument-hint: "[BV号 或 视频链接] [分P，如 1-3 或 全部] [auto]"
skills: bilibili-persona
---

用 `bilibili-persona` skill 处理这个请求：

$ARGUMENTS

默认（交互模式）：先把分P列表列出来给我确认（全部还是指定哪几个），再往下走。
参数里带 `auto`，或用户说了「自动学习 / 直接学 / 写进 Obsidian」：走自动学习模式——
不停下来确认，按 90 分钟规则定范围，**完成后执行阶段 8 把知识落进 Obsidian wiki**，
最后跑 lint 并汇报。
