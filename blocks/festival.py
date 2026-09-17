# blocks/festival.py
from .base import BaseBlock, BlockMeta
from . import register


class FestivalBlock(BaseBlock):
    meta = BlockMeta(
        id="festival",
        title="节日倒计时",
        icon="./res/icon/calendar.png",
        order=10,
        layout="half",
        default_enabled=True,
    )

    async def fetch(self, ctx: dict, cookie: str):
        # 直接复用 ctx 中已算好的节日数据
        return ctx.get("festivals", [])

    def to_template(self, raw):
        return {"items": [{"days": d, "name": n} for d, n in raw]}


register(FestivalBlock())