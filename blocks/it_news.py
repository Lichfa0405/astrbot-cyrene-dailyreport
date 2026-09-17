# blocks/it_news.py
import xml.etree.ElementTree as ET

from astrbot.api import logger

from .base import BaseBlock, BlockMeta
from . import register
from ..http_client import AsyncHttpx, DEFAULT_HEADERS


class ITNewsBlock(BaseBlock):
    meta = BlockMeta(
        id="it_news",
        title="IT资讯",
        icon="./res/icon/it.png",
        order=30,
        layout="full",
        default_enabled=True,
    )

    URL = "https://www.ithome.com/rss/"

    async def fetch(self, ctx: dict, cookie: str) -> list[str]:
        headers = dict(DEFAULT_HEADERS)
        if cookie:
            headers["Cookie"] = cookie

        try:
            res = await AsyncHttpx.get(self.URL, headers=headers)
            root = ET.fromstring(res.text)
            titles = []
            for item in root.findall("./channel/item"):
                title_element = item.find("title")
                if title_element is not None and title_element.text:
                    titles.append(title_element.text)
            return titles[:11] if len(titles) > 11 else titles
        except Exception as e:
            logger.warning(f"[xilian] IT资讯获取失败: {e}")
            return []

    def to_template(self, raw):
        return {"items": raw}


register(ITNewsBlock())