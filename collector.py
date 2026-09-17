# collector.py
import asyncio
from datetime import datetime

from astrbot.api import logger

from .blocks import get_enabled_blocks
from .date_utils import get_festivals_dates, get_lunar_date_str


async def collect_report_data(config: dict) -> dict:
    """聚合所有启用板块的数据，返回给模板的 dict"""
    now = datetime.now()
    blocks = get_enabled_blocks(config)

    ctx = {
        "config": config,
        "now": now,
        "festivals": get_festivals_dates(),
    }

    # 并发抓取，单板块异常不影响其他
    results = await asyncio.gather(
        *[b.fetch(ctx, config.get(f"block_{b.meta.id}_cookie", b.meta.default_cookie)) for b in blocks],
        return_exceptions=True,
    )

    rendered_blocks = []
    for block, raw in zip(blocks, results):
        if isinstance(raw, Exception):
            logger.warning(f"[xilian] 板块 {block.meta.id} 抓取失败: {raw}")
            continue
        if raw is None:
            continue
        try:
            payload = block.to_template(raw)
        except Exception as e:
            logger.warning(f"[xilian] 板块 {block.meta.id} 数据转换失败: {e}")
            continue

        rendered_blocks.append({
            "id": block.meta.id,
            "title": block.meta.title,
            "icon": block.meta.icon,
            "layout": block.meta.layout,
            **payload,
        })

    return {
        "title": config.get("report_title", "昔涟日报"),
        "subtitle": config.get("report_subtitle", "把今天的好消息，轻轻装进信箱。"),
        "week": "一二三四五六日"[now.weekday()],
        "date": now.strftime("%Y-%m-%d"),
        "zh_date": get_lunar_date_str(now.date()),
        "full_show": config.get("full_show", False),
        "blocks": rendered_blocks,
    }