# Security

## 敏感数据边界

本项目可能在本机使用 Bilibili Cookie。Cookie 属于凭据：

- 不要提交到 Git；
- 不要复制到 Issue、PR、日志或示例文档；
- 不要在调试输出中打印内容；
- 正常字幕/简介采集只把 Cookie 文件路径交给 yt-dlp；仅命中用户主动配置的、被 Git 忽略的 `config/pinned-comment-whitelist.local.json` 时，核心才可在本机读取 Netscape Cookie 以构造一次只读评论请求；本地名单和 Cookie 值都不得打印、写入 Job/笔记、上传或提交；
- 不要把单个 `SESSDATA`、完整 Cookie 请求头或真实 `cookies.txt` 当作排错文本发送给 Agent。

第一次获取、导出和更新 Cookie 的安全教程见 [Bilibili Cookie 获取与安全配置](docs/BILIBILI-COOKIE.md)。

私人 Obsidian 笔记、`.runtime`、本机 Cookie / 配置和其它机器私有数据都不属于公开 Git 内容。私人笔记可以物理保存在仓库工作区的 `notes/**` 以便本地 Agent 访问，但该目录必须保持 Git ignored；Vault 通过 Junction 映射时也不得因此把私人笔记加入提交。

## Git 身份与公开提交

Git 提交元数据会公开作者名和作者邮箱。准备公开仓库、发布 Release 或接受外部贡献前，应确认当前仓库使用的是你愿意公开的 Git 身份；如果不希望暴露私人邮箱，可以使用 GitHub 提供的 `noreply` 邮箱。

修改 Git 配置只会影响**未来提交**。已经推送到公开仓库的历史 commit 仍会保留原作者邮箱；如果必须移除历史邮箱，需要单独评估历史重写与 force-push 的影响，不应把它当成普通文档修改处理。

公开前也应检查受跟踪文档、验收报告和示例中是否残留维护者的绝对路径、Vault 位置、备份路径或其它机器特征。示例统一使用 `<repo-root>`、`<vault-root>`、`D:\\Notes\\MyVault` 等通用占位形式。

## 第三方工具与安装安全

本仓库附带经官方 SHA-256 校验的 Windows x64 单文件 `tools/yt-dlp.exe`。来源和版本见 `tools/yt-dlp.release.json`，许可文本见 `tools/YT-DLP-LICENSE.txt`、`tools/THIRD_PARTY_LICENSES.txt`。Agent 不得从系统 PATH 静默回退到其它版本，也不得未经授权替换可执行文件。

安装脚本只读计划为默认状态，`-Apply` 必须针对经过用户授权的用户级 Skill 或 Vault 路径。旧目录、已有笔记、不同目标的 Junction 均必须保留；遇到冲突停止，不自动删除、搬迁或覆盖。

## 报告安全问题

不要在公开 Issue 中附带 Cookie、账号信息、私人笔记或其他凭据。

如果问题不包含敏感数据，可以提交普通 Issue 并提供最小复现。涉及敏感信息时，请使用 GitHub 提供的私密安全报告机制（如果仓库已启用）；如果未启用，只描述问题类型并等待维护者提供安全的沟通方式。

## 运行时保护

- 短链解析只允许明确的 Bilibili 官方域名，并限制超时和重定向次数。
- 临时目录清理只允许作用于 `.runtime/bilibili-learning` 的子目录。
- 默认采集流程不下载视频或音频，不启动 Chrome/CDP，不自动运行 ASR。
