# main.py
import asyncio
import random
from datetime import datetime
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.message_components import Image, Plain
from astrbot.api.star import Context, Star, register

from .collector import collect_report_data
from .db import (
    get_all_group_configs,
    get_group_config,
    init_db,
    remove_group_configs,
    set_group_enabled,
    set_last_sender,
    set_preferred_bot,
    upsert_group_config,
)
from .render import render_report


CACHE_DIR = Path(__file__).parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@register(
    "astrbot_plugin_xilian_report",
    "你的名字",
    "昔涟日报 - 聚合B站热点 / IT资讯 / 节日倒计时 / 一言",
    "1.0.0",
    "参考 Ubot/ubot-plugin-wwreport 重写的模块化日报插件",
)
class XilianReportPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self._bg_task: asyncio.Task | None = None

    async def initialize(self):
        await init_db()
        self._bg_task = asyncio.create_task(self._scheduler_loop())
        logger.info("[xilian] 昔涟日报插件已启动")

    async def terminate(self):
        if self._bg_task:
            self._bg_task.cancel()

    # ---------------- 定时调度（轮询，30 秒一次） ----------------
    async def _scheduler_loop(self):
        last_pregen_date = None
        last_push_date = None
        last_self_check_minute = None

        while True:
            try:
                now = datetime.now()
                today = now.date()

                # 00:01 预生成
                if now.hour == 0 and now.minute >= 1 and last_pregen_date != today:
                    last_pregen_date = today
                    try:
                        await self._get_report_image(force_refresh=True)
                        logger.info("[xilian] 预生成日报成功")
                    except Exception as e:
                        logger.warning(f"[xilian] 预生成失败: {e}")

                # 08:01 自动推送
                if (
                    self.config.get("auto_send", True)
                    and now.hour == 8
                    and now.minute >= 1
                    and last_push_date != today
                ):
                    last_push_date = today
                    await self._broadcast("每日定时推送")

                # 自检
                sc_h = int(self.config.get("self_check_hour", 7))
                sc_m = int(self.config.get("self_check_minute", 45))
                key = (today, now.hour, now.minute)
                if now.hour == sc_h and now.minute == sc_m and key != last_self_check_minute:
                    last_self_check_minute = key
                    await self._run_self_check("每日定时自检", notify=True)

                await asyncio.sleep(30)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[xilian] 调度循环异常: {e}")
                await asyncio.sleep(60)

    # ---------------- 核心 ----------------
    async def _get_report_image(self, force_refresh: bool = False) -> bytes:
        today = datetime.now().date()
        cache_file = CACHE_DIR / f"{today}.png"

        if not force_refresh and cache_file.exists():
            return cache_file.read_bytes()

        data = await collect_report_data(self.config)
        image_bytes = await render_report(data)
        cache_file.write_bytes(image_bytes)
        return image_bytes

    async def _broadcast(self, reason: str, notify: bool = True):
        configs = await get_all_group_configs(enabled_only=True)
        if not configs:
            return {"success": [], "fail": []}

        try:
            image = await self._get_report_image()
        except Exception as e:
            logger.error(f"[xilian] 生成图片失败: {e}")
            return {"success": [], "fail": [(c["group_id"], str(e)) for c in configs]}

        success, fail = [], []
        for cfg in configs:
            gid = int(cfg["group_id"])
            try:
                umo = f"aiocqhttp:GroupMessage:{gid}"
                chain = MessageChain([Image.fromBytes(image)])
                await self.context.send_message(umo, chain)
                success.append(gid)
                await set_last_sender(gid, 0)
                await asyncio.sleep(random.randint(1, 3))
            except Exception as e:
                fail.append((gid, str(e)[:80]))

        if notify:
            await self._notify_summary(
                f"[昔涟日报] {reason}\n"
                f"目标群: {len(configs)} 成功: {len(success)} 失败: {len(fail)}\n"
                + ("失败: " + "; ".join(f"{g}({e})" for g, e in fail[:12]) if fail else "")
            )
        return {"success": success, "fail": fail}

    async def _notify_summary(self, text: str):
        if self.config.get("notify_superuser", True):
            try:
                admins = self.context.get_config().get("admins_id", []) or []
                for admin_id in admins:
                    umo = f"aiocqhttp:FriendMessage:{admin_id}"
                    await self.context.send_message(umo, MessageChain([Plain(text)]))
            except Exception as e:
                logger.warning(f"[xilian] 私聊通知管理员失败: {e}")

        gid = self.config.get("notify_group_id")
        if gid:
            try:
                umo = f"aiocqhttp:GroupMessage:{gid}"
                await self.context.send_message(umo, MessageChain([Plain(text)]))
            except Exception as e:
                logger.warning(f"[xilian] 通知群 {gid} 失败: {e}")

    async def _run_self_check(self, reason: str, notify: bool = True) -> str:
        all_cfgs = await get_all_group_configs(enabled_only=False)
        enabled = sum(1 for c in all_cfgs if c["enabled"])
        text = (
            f"[昔涟日报自检] {reason}\n"
            f"入库群记录: {len(all_cfgs)}\n"
            f"启用推送群: {enabled}"
        )
        if notify:
            await self._notify_summary(text)
        return text

    # ---------------- 命令 ----------------
    @filter.command("昔涟日报", alias={"小爱日报", "ww日报", "日报"})
    async def cmd_report(self, event: AstrMessageEvent):
        """查看今日昔涟日报"""
        try:
            image = await self._get_report_image()
            yield event.image_result(image)
        except Exception as e:
            logger.exception("[xilian] 生成日报失败")
            yield event.plain_result(f"日报生成失败: {e}")

    @filter.command("日报帮助")
    async def cmd_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "昔涟日报指令表\n"
            "1. 昔涟日报 / 日报 —— 查看今日日报\n"
            "2. 日报帮助 —— 查看本指令表\n"
            "3. 日报状态 <群号...> —— 开启推送（管理员）\n"
            "4. 日报状态 --close <群号...> —— 关闭推送（管理员）\n"
            "5. 测试推送日报 —— 对所有已开启群测试推送（管理员）\n"
            "6. 日报自检 —— 自检（管理员）\n"
            "7. 重置日报 —— 清缓存（管理员）"
        )

    @filter.command("日报状态")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_status(self, event: AstrMessageEvent):
        """用法: 日报状态 [--close] 123456 789012"""
        args = event.message_str.split()[1:]
        close = "--close" in args
        gids = [a for a in args if a != "--close"]
        updated = []
        for g in gids:
            try:
                gid = int(g)
            except ValueError:
                continue
            await set_group_enabled(gid, not close)
            updated.append(gid)
        yield event.plain_result(
            f"已{'关闭' if close else '开启'}群组日报: {updated}"
        )

    @filter.command("测试推送日报")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_test_push(self, event: AstrMessageEvent):
        yield event.plain_result("测试推送已启动...")
        result = await self._broadcast("手动测试推送")
        yield event.plain_result(
            f"测试推送完成: 成功 {len(result['success'])}，失败 {len(result['fail'])}"
        )

    @filter.command("日报自检")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_self_check(self, event: AstrMessageEvent):
        text = await self._run_self_check("手动自检", notify=True)
        yield event.plain_result(text)

    @filter.command("重置日报")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def cmd_reset(self, event: AstrMessageEvent):
        today = datetime.now().date()
        file = CACHE_DIR / f"{today}.png"
        if file.exists():
            file.unlink()
        yield event.plain_result("昔涟日报缓存已重置！")