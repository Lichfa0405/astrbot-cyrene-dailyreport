# render.py
from pathlib import Path
from typing import Any

from astrbot.api import logger

TEMPLATE_DIR = Path(__file__).parent / "templates" / "xilian_report"

# 优先使用 AstrBot 内置渲染，失败时 fallback 到 playwright
try:
    from astrbot.core.utils.t2i import html_to_pic as _astrbot_html_to_pic
    _HAS_ASTRBOT_T2I = True
except ImportError:
    _astrbot_html_to_pic = None
    _HAS_ASTRBOT_T2I = False


async def render_report(data: dict[str, Any]) -> bytes:
    """把 data 渲染成 PNG 字节"""
    logger.error("[xilian] ===== render_report v2 被执行 =====")
    viewport = {"width": 578, "height": 1885}

    if False:  # 强制走 playwright
        try:
            return await _astrbot_html_to_pic(
                template_path=str(TEMPLATE_DIR),
                template_name="main.html",
                templates={"data": data},
                pages={
                    "viewport": viewport,
                    "base_url": f"file://{TEMPLATE_DIR}",
                },
                wait=2,
            )
        except Exception as e:
            logger.warning(f"[xilian] AstrBot 内置渲染失败，回退到 playwright: {e}")

    return await _render_with_playwright(data, viewport)

async def _render_with_playwright(data: dict, viewport: dict) -> bytes:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from playwright.async_api import async_playwright

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template("main.html").render(data=data)

    # 把渲染后的 HTML 写到模板目录，用 file:// 加载，相对路径才能命中
    tmp_html = TEMPLATE_DIR / "_render_tmp.html"
    tmp_html.write_text(html, encoding="utf-8")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(channel="chromium", args=["--no-sandbox"])
            page = await browser.new_page(
                viewport={"width": viewport["width"], "height": viewport["height"]}
            )
            await page.goto(f"file://{tmp_html}", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            # 只截 .wrapper 元素，自动按内容高度
            element = await page.query_selector(".wrapper")
            img = await element.screenshot()
            await browser.close()
            return img
    finally:
        tmp_html.unlink(missing_ok=True)

