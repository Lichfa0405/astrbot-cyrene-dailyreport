# blocks/bili_hot.py
from astrbot.api import logger

from .base import BaseBlock, BlockMeta
from . import register
from ..http_client import AsyncHttpx, DEFAULT_HEADERS


class BiliHotBlock(BaseBlock):
    meta = BlockMeta(
        id="bili_hot",
        title="B站热点",
        icon="./res/icon/bilibili.png",
        order=20,
        layout="half",
        default_enabled=True,
    )

    MAIN_URL = "https://s.search.bilibili.com/main/hotword"
    BACKUP_URL = "https://api.bilibili.com/x/web-interface/search/square?limit=20"

    async def fetch(self, ctx: dict, cookie: str) -> list[str]:
        headers = dict(DEFAULT_HEADERS)
        if cookie:
            headers["Cookie"] = cookie

        try:
            res = await AsyncHttpx.get(self.MAIN_URL, headers=headers)
            data = res.json()
            if isinstance(data, dict) and isinstance(data.get("list"), list):
                return [
                    item.get("keyword", "")
                    for item in data["list"]
                    if item.get("keyword")
                ]
        except Exception as e:
            logger.warning(f"[xilian] B站热搜主接口失败，尝试备用: {e}")

        try:
            res = await AsyncHttpx.get(self.BACKUP_URL, headers=headers)
            data = res.json()
            items = ((data.get("data") or {}).get("trending") or {}).get("list") or []
            if isinstance(items, list):
                return [
                    item.get("show_name", "")
                    for item in items
                    if item.get("show_name")
                ][:20]
        except Exception as e:
            logger.warning(f"[xilian] B站热搜备用接口失败: {e}")

        return []

    def to_template(self, raw):
        return {"items": raw}


register(BiliHotBlock())