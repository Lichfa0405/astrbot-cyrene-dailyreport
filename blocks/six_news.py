# blocks/six_news.py
from typing import Any

from astrbot.api import logger

from .base import BaseBlock, BlockMeta
from . import register
from ..http_client import AsyncHttpx, DEFAULT_HEADERS
from ..models import SixData


class SixNewsBlock(BaseBlock):
    meta = BlockMeta(
        id="six_news",
        title="60S读世界",
        icon="./res/icon/60.png",
        order=40,
        layout="full",
        default_enabled=False,   # 默认关闭，想开在配置里打开
    )

    ALAPI_URL = "https://v2.alapi.cn/api/zaobao"
    SIX_URL = "https://60s.viki.moe/?v2=1"
    SIX_BACKUP_URL = "https://60s.viki.moe/v2/60s"

    async def fetch(self, ctx: dict, cookie: str) -> list[str]:
        config = ctx.get("config", {})
        alapi_token = config.get("alapi_token", "")

        if alapi_token:
            try:
                return await self._get_alapi_data(alapi_token)
            except Exception as e:
                logger.warning(f"[xilian] alapi 失败，将尝试公共接口: {e}")

        headers = dict(DEFAULT_HEADERS)
        if cookie:
            headers["Cookie"] = cookie

        for url in (self.SIX_URL, self.SIX_BACKUP_URL):
            try:
                res = await AsyncHttpx.get(url, headers=headers)
                payload: Any = res.json()

                if isinstance(payload, dict):
                    data = payload.get("data")
                    if isinstance(data, dict) and isinstance(data.get("news"), list):
                        return [str(i) for i in data["news"] if i][:11]
                    if isinstance(payload.get("news"), list):
                        return [str(i) for i in payload["news"] if i][:11]

                model = SixData(**payload)
                news = model.data.news
                return news[:11] if len(news) > 11 else news
            except Exception as e:
                logger.warning(f"[xilian] 60s 解析失败({url}): {e}")

        return []

    async def _get_alapi_data(self, token: str) -> list[str]:
        payload = {"token": token, "format": "json"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = await AsyncHttpx.post(self.ALAPI_URL, data=payload, headers=headers)
        if res.status_code != 200:
            return []
        data = res.json()
        news_items = data.get("data", {}).get("news", [])
        return news_items[:11] if len(news_items) > 11 else news_items

    def to_template(self, raw):
        return {"items": raw}


register(SixNewsBlock())