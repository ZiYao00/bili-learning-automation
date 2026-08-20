# Bili Learning Automation

将 Bilibili 的复制链接或 BV 号交给 Hermes，生成字幕优先的 Obsidian 学习笔记。默认只采集元数据、UP 主原始简介和可用字幕；不下载音视频，临时资料在任务完成后自动清理。

## 组成

- `hermes-skills/bilibili-learning/`：项目拥有的 Hermes skill、采集、校验与导航脚本。
- `config/bilibili-note-taxonomy.json`：笔记分类、短标题、模型标准名和导航规则的项目默认配置。
- `docs/`：笔记标准、架构和依赖说明。
- `notes/`：本机私人 Obsidian 知识库；默认不纳入 Git。

## 不在仓库中的内容

Cookie、个人笔记、运行时字幕/元数据/日志、历史归档、yt-dlp 测试输出、`bili-note` 与 `web-access` 的本地副本均不提交。

## 外部依赖

- Hermes 运行环境；
- `yt-dlp` 可执行文件；
- 本机提供的 Bilibili Netscape Cookie；
- 可选历史依赖：`bili-note`、`web-access`。当前默认 yt-dlp 流程不调用它们。

详见 [架构说明](docs/ARCHITECTURE.md) 和 [依赖说明](docs/DEPENDENCIES.md)。

## 验证入口

向 Hermes 私聊发送 B站“复制链接”或 BV 号。成功后应生成标准 Markdown、刷新 `99-导航`，且不留下音视频或临时字幕文件。

## 许可证

本项目尚未选择发布许可证。仓库公开不等于授权他人使用或再分发；第三方依赖遵循其各自许可证。
