# 配置说明

如果你已经按照 [新手快速上手](QUICKSTART.md) 配好并成功生成过笔记，这份文档平时不需要经常看。

它主要解决三个问题：

1. yt-dlp 在哪里；
2. Cookie 文件在哪里；
3. 笔记要写到哪里。

普通用户优先使用 `config/local.json`，比临时环境变量更直观，也更适合长期使用。

---

## 1. 最推荐的配置方式：`config/local.json`

项目提供模板：

```text
config/local.json.example
```

复制一份：

```powershell
Copy-Item .\config\local.json.example .\config\local.json
```

然后修改成本机路径：

```json
{
  "ytdlp": "G:\\Program\\yt-dlp\\yt-dlp.exe",
  "notes_root": "D:\\Notes\\MyVault\\bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt"
}
```

### `ytdlp`

`yt-dlp.exe` 的完整路径。

例如：

```json
"ytdlp": "G:\\Program\\yt-dlp\\yt-dlp.exe"
```

### `notes_root`

生成 Markdown 笔记的根目录。

例如：

```json
"notes_root": "D:\\Notes\\MyVault\\bilibili"
```

新笔记会先进入：

```text
D:\Notes\MyVault\bilibili\00-待整理\
```

### `cookie_file`

Netscape 格式 Bilibili Cookie 文件的路径。

例如：

```json
"cookie_file": "D:\\Private\\bilibili_cookies.txt"
```

这里只填写**文件路径**，不要把 Cookie 内容直接写进 JSON。

`config/local.json` 已被 Git 忽略，不会作为正常源码提交。

---

## 2. 也可以使用环境变量

如果你更习惯脚本或临时环境，可以设置：

| 环境变量 | 用途 |
| --- | --- |
| `BILI_LEARNING_YTDLP` | yt-dlp 可执行文件 |
| `BILI_LEARNING_NOTES_ROOT` | 笔记根目录 |
| `BILI_LEARNING_COOKIE_FILE` | Cookie 文件 |
| `BILI_LEARNING_TAXONOMY` | 自定义 taxonomy 文件 |

PowerShell 示例：

```powershell
$env:BILI_LEARNING_YTDLP = 'G:\Program\yt-dlp\yt-dlp.exe'
$env:BILI_LEARNING_NOTES_ROOT = 'D:\Notes\MyVault\bilibili'
$env:BILI_LEARNING_COOKIE_FILE = 'D:\Private\bilibili_cookies.txt'
```

这种方式默认只对当前 PowerShell 会话生效。

---

## 3. 配置优先级

如果同一个项目同时存在环境变量、`local.json` 和默认值，优先级是：

```text
环境变量
→ config/local.json
→ 项目默认值
```

yt-dlp 还会继续尝试：

```text
系统 PATH 中的 yt-dlp
```

所以 yt-dlp 的完整查找顺序是：

1. `BILI_LEARNING_YTDLP`；
2. `config/local.json` 的 `ytdlp`；
3. PATH 中的 `yt-dlp`。

不确定当前到底用了哪一个时，直接运行 doctor，它会显示最终来源。

---

## 4. 默认配置在哪里

默认 taxonomy：

```text
config/bilibili-note-taxonomy.json
```

它负责：

- 默认 `notes_root`；
- `00-待整理` fallback；
- tags；
- 学习后整理时的建议分类；
- 导航目录。

### 一个容易误解的地方

Taxonomy route 的 `path` **不是新笔记直接发布的位置**。

新笔记统一先进入 fallback：

```text
00-待整理
```

只有你明确执行“学习后整理”时，系统才根据 tags / taxonomy 把笔记归档到建议目录。

这能避免还没学习的视频直接混进正式知识库。

---

## 5. 默认笔记目录

如果没有覆盖 `notes_root`，项目默认使用：

```text
notes/bilibili
```

你可以直接把它作为测试目录，也可以指向自己的 Obsidian Vault 子目录。

例如：

```text
D:\Notes\MyVault\bilibili
```

### 注意 CSS 放置位置

如果 `notes_root` 是：

```text
D:\Notes\MyVault\bilibili
```

真正的 Vault 是：

```text
D:\Notes\MyVault
```

CSS 应该放在：

```text
D:\Notes\MyVault\.obsidian\snippets\
```

而不是：

```text
D:\Notes\MyVault\bilibili\.obsidian\snippets\
```

详见 [Obsidian 样式教程](OBSIDIAN-STYLING.md)。

---

## 6. Cookie 怎么配置

项目默认会尝试：

```text
key/bilibili_cookies.txt
```

但更推荐显式写入 `config/local.json` 或环境变量，这样换机器时更容易理解。

Cookie 文件必须存在；项目不会主动读取、显示或记录 Cookie 内容，只把路径交给 yt-dlp。

不要：

- 把 Cookie 提交到 Git；
- 把 Cookie 内容放进 Issue；
- 把 Cookie 内容贴给智能体做诊断；
- 把 Cookie 内容写进 `local.json`。

---

## 7. 如何确认配置正确

运行：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py
```

正常情况下重点关注：

- yt-dlp 找到并可执行；
- Cookie 文件存在；
- taxonomy 有效；
- notes root 可写；
- runtime 可写；
- 共享协议文档存在。

如果智能体需要 JSON：

```powershell
python .\hermes-skills\bili-learning-automation\scripts\doctor_bilibili_learning.py --json
```

doctor 不访问 Bilibili，也不读取 Cookie 内容。

---

## 8. 配置错误时会怎样

项目不会为了“尽量跑下去”而静默猜配置。

以下情况会直接停止：

- `config/local.json` 不是有效 JSON；
- 出现未知字段；
- 路径值为空；
- taxonomy 格式无效；
- yt-dlp 路径不存在或不可执行；
- Cookie 文件不存在；
- notes / runtime 无法写入。

这样做是为了避免把笔记写错目录、误用旧配置或产生无法追踪的半成品。

---

## 9. 支持的 `local.json` 字段

当前只支持：

```text
ytdlp
notes_root
cookie_file
taxonomy
```

示例：

```json
{
  "ytdlp": "G:\\Program\\yt-dlp\\yt-dlp.exe",
  "notes_root": "D:\\Notes\\MyVault\\bilibili",
  "cookie_file": "D:\\Private\\bilibili_cookies.txt",
  "taxonomy": "D:\\Config\\my-taxonomy.json"
}
```

普通用户通常只需要前三项。

---

## 10. 笔记命名规则

默认文件名：

```text
{原视频标题}.md
```

例如：

```text
H3智能一体化节点重磅升级.md
```

如果同目录已经存在同名文件，会自动生成：

```text
H3智能一体化节点重磅升级（2）.md
H3智能一体化节点重磅升级（3）.md
```

不会覆盖旧笔记。

BVID 会写在 H1 下方，但不会强行加入文件名。

学习后如果希望使用更短的标题，应该通过 `organize` 统一整理，而不是手工改名和移动。

---

## 11. 换电脑时最少需要迁移什么

换机器后通常只需要重新准备：

1. 项目代码；
2. Python；
3. yt-dlp；
4. Cookie 文件；
5. `config/local.json`；
6. Obsidian Vault；
7. 对应智能体适配层。

其中 `local.json` 和 Cookie 都是本机私有配置，不建议提交到公开仓库。
