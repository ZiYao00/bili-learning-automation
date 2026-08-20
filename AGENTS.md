# 视频学习笔记

生成或修改 `notes\bilibili` 中的笔记前，必须先阅读：

- `docs\standards\CODEX-VIDEO-NOTE-GUIDE.md`
- `docs\standards\STANDARD-VIDEO-NOTE-EXAMPLE.md`
- `config\bilibili-note-taxonomy.json`

以示例为默认最终成品格式。视频简介是硬性必填项：必须从视频元数据取得 UP 主原始简介，放在标题之后、播放器之前；不得用 AI 摘要替代或因抓取失败而静默省略。机器资料只可临时保留在 `.runtime`，不写入主阅读页面或长期归档。

本机 Hermes 运维说明可另见 `G:\ai_data\hermes\docs\bilibili-learning\`；它不是项目运行或其他智能体执行的前置条件。
