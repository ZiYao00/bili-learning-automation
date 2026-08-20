# 架构说明

## 主链路

```text
Hermes 私聊中的复制链接 / BV 号
→ bilibili-learning skill
→ yt-dlp 采集元数据、原始简介、ai-zh/zh 字幕
→ Hermes 撰写 Markdown
→ finalizer 校验标题、分类、标签、iframe 与简介
→ 自动刷新导航并清理临时任务目录
```

项目脚本以自身位置计算项目根目录。默认 taxonomy 位于 `config/bilibili-note-taxonomy.json`；可通过 `BILI_LEARNING_TAXONOMY` 覆盖。yt-dlp 与 Cookie 路径也支持本机环境变量覆盖，见依赖说明。

## 外部系统

- Hermes：独立运行环境；项目仅管理 `bilibili-learning` skill 源码。实际安装位置由 Hermes Junction 指向本项目 skill。
- Obsidian：笔记位于 `notes/bilibili`，当前可由本机目录链接映射到个人 Vault。
- yt-dlp：外部可执行文件，默认沿用当前 Windows 安装位置。

## 数据边界

- 长期产物：私人 Markdown 笔记与导航页，默认不入 Git。
- 临时产物：`.runtime/bilibili-learning`；成功、失败或 20 分钟兜底后清理。
- 敏感数据：`key/` 下的登录态，不读取、不输出、不提交。
- 历史原始资料：`archive/`，仅保留本机，不纳入 Git。
