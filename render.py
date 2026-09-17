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
    viewport = {"width": 578, "height": 1885}

    if _HAS_ASTRBOT_T2I:
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

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(
            viewport={"width": viewport["width"], "height": viewport["height"]}
        )
        # base url 让相对路径的字体、图标能加载
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        img = await page.screenshot(full_page=True)
        await browser.close()
        return img