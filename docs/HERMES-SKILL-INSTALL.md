# Hermes skill 安装

`bili-learning-automation` 的唯一源码目录为：

```text
<project-root>\hermes-skills\bili-learning-automation
```

Hermes 的安装目录应直接指向这个源码目录：

```text
%LOCALAPPDATA%\hermes\skills\bili-learning-automation
```

不要经由旧项目目录、兼容目录链接或源码副本间接引用 skill。

安装或更新后验证：

1. 已安装 Junction 的目标为项目中的 `hermes-skills\bili-learning-automation`。
2. `hermes skills list` 显示 `bili-learning-automation` 为 `enabled`。
3. 已安装目录中的 `SKILL.md` 与项目源文件一致。
4. 若 Hermes 网关或微信会话已在运行，在该会话发送一次 `/reload-skills`，使其立即重扫本地 skill；无需重启网关。

skill 的项目路径、taxonomy 与笔记标准均以当前项目根目录为准。Cookie、私人笔记、`.runtime` 和本机虚拟环境不属于 skill 安装内容。
