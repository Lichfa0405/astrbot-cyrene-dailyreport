# blocks/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class BlockMeta:
    id: str                       # 唯一标识，配置前缀为 block_<id>_enabled / block_<id>_cookie
    title: str                    # 渲染标题
    icon: str                     # 图标相对路径，如 "./res/icon/bilibili.png"
    order: int                    # 排序，越小越靠前
    layout: str = "full"          # full / half
    default_enabled: bool = True
    default_cookie: str = ""


class BaseBlock(ABC):
    meta: BlockMeta

    @abstractmethod
    async def fetch(self, ctx: dict, cookie: str) -> Any:
        """获取原始数据。抛异常由 collector 兜底，返回 None 或空结构表示无数据"""

    @abstractmethod
    def to_template(self, raw: Any) -> dict[str, Any]:
        """把原始数据转换成模板可直接消费的 dict"""