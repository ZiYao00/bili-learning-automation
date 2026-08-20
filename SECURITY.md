# Security

## 敏感数据边界

本项目可能在本机使用 Bilibili Cookie。Cookie 属于凭据：

- 不要提交到 Git；
- 不要复制到 Issue、PR、日志或示例文档；
- 不要在调试输出中打印内容；
- 程序只应把配置的 Cookie 文件路径交给 yt-dlp。

私人 Obsidian 笔记、`.runtime`、`archive`、`materials` 和本机第三方副本默认也不属于公开仓库内容。

## 报告安全问题

不要在公开 Issue 中附带 Cookie、账号信息、私人笔记或其他凭据。

如果问题不包含敏感数据，可以提交普通 Issue 并提供最小复现。涉及敏感信息时，请使用 GitHub 提供的私密安全报告机制（如果仓库已启用）；如果未启用，只描述问题类型并等待维护者提供安全的沟通方式。

## 运行时保护

- 短链解析只允许明确的 Bilibili 官方域名，并限制超时和重定向次数。
- 临时目录清理只允许作用于 `.runtime/bilibili-learning` 的子目录。
- 默认采集流程不下载视频或音频，不启动 Chrome/CDP，不自动运行 ASR。
