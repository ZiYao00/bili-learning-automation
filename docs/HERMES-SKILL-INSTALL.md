# Hermes skill 安装

`bilibili-learning` 的唯一源码目录为：

```text
<project-root>\hermes-skills\bilibili-learning
```

Hermes 的安装目录应直接指向这个源码目录：

```text
%LOCALAPPDATA%\hermes\skills\bilibili-learning
```

不要经由旧项目目录、兼容目录链接或源码副本间接引用 skill。

安装或更新后验证：

1. 已安装 Junction 的目标为项目中的 `hermes-skills\bilibili-learning`。
2. `hermes skills list` 显示 `bilibili-learning` 为 `enabled`。
3. 已安装目录中的 `SKILL.md` 与项目源文件一致。

skill 的项目路径、taxonomy 与笔记标准均以当前项目根目录为准。Cookie、私人笔记、`.runtime` 和本机虚拟环境不属于 skill 安装内容。
