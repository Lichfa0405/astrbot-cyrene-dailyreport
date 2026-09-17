# blocks/__init__.py
from .base import BaseBlock, BlockMeta

_REGISTRY: dict[str, BaseBlock] = {}


def register(block: BaseBlock) -> None:
    _REGISTRY[block.meta.id] = block


def get_enabled_blocks(config: dict) -> list[BaseBlock]:
    blocks = [
        b
        for b in _REGISTRY.values()
        if config.get(f"block_{b.meta.id}_enabled", b.meta.default_enabled)
    ]
    return sorted(blocks, key=lambda b: b.meta.order)


def list_blocks() -> list[BaseBlock]:
    return list(_REGISTRY.values())


# 自动导入所有板块模块，触发 register()
from . import festival   # noqa: E402, F401
from . import bili_hot   # noqa: E402, F401
from . import it_news    # noqa: E402, F401
from . import six_news   # noqa: E402, F401
from . import hitokoto   # noqa: E402, F401