# blocks/hitokoto.py
from astrbot.api import logger

from .base import BaseBlock, BlockMeta
from . import register
from ..http_client import AsyncHttpx, DEFAULT_HEADERS
from ..models import Hitokoto


class HitokotoBlock(BaseBlock):
    meta = BlockMeta(
        id="hitokoto",
        title="今日一言",
        icon="./res/icon/hitokoto.png",
        order=100,
        layout="full",
        default_enabled=True,
    )

    URL = "https://v1.hitokoto.cn/?c=a"
    FALLBACK = "今天也要开心喵~"

    async def fetch(self, ctx: dict, cookie: str) -> str:
        try:
            res = await AsyncHttpx.get(self.URL, headers=DEFAULT_HEADERS)
            data = Hitokoto(**res.json())
            return data.hitokoto
        except Exception as e:
            logger.warning(f"[xilian] 一言获取失败，使用默认: {e}")
            return self.FALLBACK

    def to_template(self, raw):
        return {"text": raw}


register(HitokotoBlock())