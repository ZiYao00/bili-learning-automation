# Bilibili Cookie 获取与安全配置

> 文档类型：**新手教程 / 凭据配置说明**。如果你第一次使用 `bili-learning-automation`，而 Agent 提示 `cookie_file_required`，从这里开始。

本项目默认通过 `yt-dlp` 获取 Bilibili 的字幕、UP 主简介和元数据。部分内容需要登录态，因此通常需要一份由你自己的浏览器登录会话导出的 **Bilibili Cookie 文件**。此外，只有用户在被 Git 忽略的 `config/pinned-comment-whitelist.local.json` 中主动配置并命中 UP 主时，核心才会在本机使用同一 Netscape Cookie 做一次只读的 UP 主置顶一级评论查询；Cookie 值不会写入 Job、笔记或日志。

Cookie 可以理解为“浏览器已经登录 Bilibili 的凭据”。它不是普通配置文本，泄露后可能导致账号风险，因此必须像密码一样保护。

---

## 1. 项目到底需要什么 Cookie

项目需要的是一个 **Mozilla / Netscape 格式的 `cookies.txt` 文件**，例如：

```text
# Netscape HTTP Cookie File
...
```

第一行必须是下面两种之一：

```text
# Netscape HTTP Cookie File
# HTTP Cookie File
```

项目配置保存的是这个文件的**路径**：

```json
{
  "cookie_file": "D:\\Private\\bilibili_cookies.txt"
}
```

不是把 Cookie 内容直接写进 `local.json`。

### 不要只复制 `SESSDATA`

很多教程会让用户按 `F12` 找到 `SESSDATA`，但本项目不是只接收一个 Cookie 字段。

下面这些做法都不推荐：

```text
SESSDATA=xxxx
```

```json
{"SESSDATA":"xxxx"}
```

或者从开发者工具里复制一长串 `Cookie:` 请求头。

原因很简单：`yt-dlp --cookies` 期望读取的是完整的 Netscape Cookie 文件，而不是单个 `SESSDATA`、JSON 或请求头字符串。

---

## 2. 导出前先确认 Bilibili 已登录

在你平时使用的浏览器中：

1. 打开 <https://www.bilibili.com/>；
2. 正常登录自己的账号；
3. 刷新页面；
4. 确认右上角能够看到自己的头像，并能正常访问需要登录态的内容。

然后再导出 Cookie。

如果浏览器本身已经退出登录，导出的 Cookie 也无法提供有效登录态。

---

## 3. 推荐方法：从浏览器导出当前 Bilibili 站点的 `cookies.txt`

对于普通 Windows 用户，最容易理解的方式是使用**可信、支持 Netscape `cookies.txt` 格式的浏览器导出工具**，只导出当前 Bilibili 域名的 Cookie。

`yt-dlp` 官方 FAQ 提到的示例包括：

- Chromium / Chrome：`Get cookies.txt LOCALLY`；
- Firefox：`cookies.txt`。

Chrome Web Store：<https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc>

官方 yt-dlp Cookie 说明：<https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp>

> 浏览器扩展本身也属于第三方软件。安装前确认扩展名称、来源和权限，不要安装名称相似但来源不明的 Cookie 扩展。yt-dlp 官方 FAQ 特别提醒，旧的 `Get cookies.txt` 与 `Get cookies.txt LOCALLY` 不是同一个扩展。

### Chrome / Chromium 新手操作示例

以浏览器已经登录 Bilibili 为前提：

1. 从可信的浏览器扩展商店找到名称准确的 `Get cookies.txt LOCALLY`，先检查来源和权限再安装；
2. 打开 `https://www.bilibili.com/`，确认页面显示自己的登录头像；
3. 保持当前页面停留在 Bilibili，点击 Cookie 导出扩展；
4. 选择导出**当前站点 / 当前域名**的 Cookie。不同版本按钮文字可能略有不同，目标是只导出 `bilibili.com`，而不是整个浏览器；
5. 选择 Netscape / Mozilla `cookies.txt` 兼容格式并导出；
6. 将文件改成容易识别的名称，例如：

```text
bilibili_cookies.txt
```

7. 保存到只有你自己使用的本地目录；
8. 用文本编辑器只检查第一行是否为 `# Netscape HTTP Cookie File` 或 `# HTTP Cookie File`，不要复制真实 Cookie 内容。

Firefox 的思路相同，可以使用 yt-dlp 官方 FAQ 提到的 `cookies.txt` 类导出工具，导出当前 Bilibili 站点的 Netscape Cookie 文件。

导出完成后，不要把文件内容粘贴到聊天里。Agent 只需要知道它位于哪里。

---

## 4. Cookie 文件放在哪里

有两种常见方式。

### 方式 A：放在项目的 `key` 目录

本项目默认会查找：

```text
<repo-root>\key\bilibili_cookies.txt
```

`key/` 已被 Git 忽略，因此个人本机使用时最省事。

例如：

```text
bili-learning-automation\
├── key\
│   └── bilibili_cookies.txt
├── config\
└── ...
```

但要注意：**Git 忽略不等于 Cookie 不敏感**。如果你会复制整个项目目录、做云盘同步或把电脑给别人使用，仍然要保护这个文件。

### 方式 B：放在项目外的私密目录

如果你希望凭据与代码仓库完全分离，可以保存到：

```text
D:\Private\bilibili_cookies.txt
```

然后在 `config/local.json` 中填写路径：

```json
{
  "cookie_file": "D:\\Private\\bilibili_cookies.txt"
}
```

也可以让 Agent 在 onboarding 时帮你写入：

```powershell
python .\scripts\run_bili_learning.py configure-cookie --file 'D:\Private\bilibili_cookies.txt'
```

这个命令只保存**文件路径**，不会读取或打印 Cookie 内容。

---

## 5. 如何确认导出的文件格式正确

用普通文本编辑器打开文件时，只检查格式，不要把内容复制到聊天或 Issue。

第一行应该是：

```text
# Netscape HTTP Cookie File
```

或：

```text
# HTTP Cookie File
```

后面的每条 Cookie 通常由制表符分隔，整体类似：

```text
.bilibili.com    TRUE    /    FALSE    ...    cookie_name    cookie_value
```

这里只是结构示意，不要把自己的真实值公开。

### 常见错误格式

下面这些都不是本项目需要的文件：

```json
{"cookies":[...]}
```

```text
SESSDATA=xxxx; bili_jct=xxxx; ...
```

```text
Cookie: SESSDATA=xxxx; ...
```

如果导出工具可以选择格式，请选择 `Netscape`、`Mozilla cookies.txt` 或兼容 `yt-dlp` 的 `cookies.txt`。

`yt-dlp` 官方 FAQ 还提醒，Cookie 文件的换行格式也必须正确：Windows 通常使用 `CRLF`。如果文件看起来是 Netscape 格式但 yt-dlp 返回异常的 `HTTP Error 400: Bad Request`，可以把换行格式也列入排查范围。

---

## 6. 配置完成后怎样验证

先运行 onboarding：

```powershell
python .\scripts\run_bili_learning.py onboarding
```

Cookie 正常时，不应再出现：

```text
cookie_file_required
```

也可以运行完整诊断：

```powershell
python .\scripts\run_bili_learning.py doctor
```

看到类似下面的结果，表示**文件路径存在**：

```text
[OK] cookie file exists - D:\Private\bilibili_cookies.txt
```

需要注意：doctor 为了保护凭据，**不会读取 Cookie 内容，也不会登录 Bilibili 测试账号是否仍有效**。Cookie 是否真的有效，会在实际采集 B站视频时由 yt-dlp 验证。

---

## 7. 不想安装浏览器扩展：可以让 yt-dlp 导出

`yt-dlp` 官方还支持直接从浏览器读取 Cookie，并写成 Netscape 文件，例如：

```powershell
yt-dlp --cookies-from-browser chrome --cookies bilibili_cookies.txt
```

Firefox 可以把 `chrome` 换成：

```text
firefox
```

但这个方法有一个非常重要的安全特性：**yt-dlp 官方说明，它会把该浏览器中的所有网站 Cookie 导出到这个文件，而不是只导出 Bilibili。**

因此普通用户更适合优先使用“仅导出当前 Bilibili 站点”的方式。如果使用这条命令：

- 把生成的文件当作高敏感凭据；
- 不要放进 Git、聊天、Issue、日志或公开网盘；
- 不要把它当成可公开分享的 Bilibili 专用文件，因为里面可能包含其它网站的登录 Cookie。

官方说明：<https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp>

---

## 8. Windows Chrome 出现 `Failed to decrypt with DPAPI` 怎么办

某些 Windows / Chromium 环境下，yt-dlp 直接读取 Chrome Cookie 数据库时可能因为浏览器加密机制失败，例如看到：

```text
Failed to decrypt with DPAPI
```

这不代表你的 Bilibili 账号登录失败，也不建议继续尝试绕过浏览器的本地加密保护。

更稳妥的处理方式是：

1. 保持浏览器正常登录 Bilibili；
2. 改用浏览器内的可信 Cookie 导出工具生成 Netscape `cookies.txt`；
3. 或使用 Firefox 登录 Bilibili 后重新导出；
4. 再把新的 Cookie 文件路径配置给本项目。

---

## 9. Cookie 文件存在，但采集仍然失败

如果 doctor 已经显示 Cookie 文件存在，但实际采集仍提示登录态或访问失败，优先检查：

1. 浏览器里的 Bilibili 账号是否仍然登录；
2. Cookie 是否是最近重新导出的；
3. 文件是否仍然是 Netscape 格式；
4. `config/local.json` 是否指向了你刚导出的那个文件；
5. 是否把旧的 Cookie 文件和新的文件弄混；
6. 是否只复制了 `SESSDATA`，而没有导出完整 `cookies.txt`。

如果登录状态发生变化、主动退出账号、修改密码或 Bilibili 使原会话失效，都可能需要重新导出 Cookie。

---

## 10. 安全规则

请把下面几条当成硬规则：

- Cookie 是账号凭据，不是普通配置；
- 不要把真实 Cookie 内容发给 ChatGPT、Hermes、WorkBuddy、Codex 或其他 Agent；
- Agent 只需要知道 Cookie **文件路径**；
- 不要提交到 Git；
- 不要放进 README、Issue、PR、日志或截图；
- 不要上传到公开网盘；
- 不要把自己的 Cookie 文件发给其他用户作为“示例”；
- 需要截图排错时，隐藏 Cookie 内容和账号信息。

项目中的 `config/local.json`、`key/` 和真实凭据默认不属于公开仓库内容。完整安全边界见 [SECURITY.md](../SECURITY.md)。

---

## 11. 最短流程

第一次配置 Cookie，可以只记住下面这条链路：

```text
浏览器登录 Bilibili
→ 导出 bilibili.com 的 Netscape cookies.txt
→ 保存为 bilibili_cookies.txt
→ 告诉 Agent“文件路径”，不要发送文件内容
→ onboarding / doctor 检查文件存在
→ 发送一个 B站链接做真实采集测试
```

完成以后，日常使用不需要每次重新导出 Cookie。只有 Cookie 失效或登录状态变化时才需要更新。
