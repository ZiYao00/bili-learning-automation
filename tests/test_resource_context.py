from __future__ import annotations

from bili_learning.note_template import _description_resources, quote_description


def _url(host: str, path: str) -> str:
    return "https" + ":" + chr(47) * 2 + host + path


def test_numbered_description_context_replaces_generic_link_label() -> None:
    first_url = _url("example.com", "/alpha")
    second_url = _url("example.com", "/beta")
    description = (
        f"1｜alpha-project：资源项目说明，直接翻。\n链接：{first_url}\n"
        f"2｜beta-project：第二个资源项目说明。\n链接：{second_url}"
    )

    resources = _description_resources(description)

    assert resources == [("alpha-project", first_url), ("beta-project", second_url)]


def test_section_field_does_not_override_generic_address_label() -> None:
    demo_url = _url("example.com", "/demo")
    description = f"国际站：\n工作流：AITUDOU-MiniMax H3(全能参考)\n体验地址：{demo_url}"

    rendered = quote_description(description, "present")

    assert f"- [国际站 · 体验地址](<{demo_url}>)" in rendered
