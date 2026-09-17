# db.py
import json
import time
from pathlib import Path

import aiosqlite
from astrbot.api import logger

# ↓↓↓ 唯一改动：不用 nonebot_plugin_localstore，用插件本地目录 ↓↓↓
DATA_PATH = Path(__file__).parent / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)
# ↑↑↑

DB_PATH = DATA_PATH / "wwreport.db"
LEGACY_CLOSE_FILE = DATA_PATH / "data.json"


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS group_push_config (
                group_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                preferred_bot_id INTEGER,
                last_sender_bot_id INTEGER,
                updated_at INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.commit()
        await _migrate_legacy_close_file(db)


async def _migrate_legacy_close_file(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT COUNT(1) FROM group_push_config")
    row = await cursor.fetchone()
    has_rows = bool(row and row[0] > 0)
    if has_rows or not LEGACY_CLOSE_FILE.exists():
        return

    try:
        data = json.loads(LEGACY_CLOSE_FILE.read_text(encoding="utf8"))
        close_list = data.get("close") if isinstance(data, dict) else None
        if not isinstance(close_list, list):
            return

        now = int(time.time())
        for gid in close_list:
            gid_int = int(gid)
            await db.execute(
                """
                INSERT INTO group_push_config (group_id, enabled, updated_at)
                VALUES (?, 0, ?)
                ON CONFLICT(group_id)
                DO UPDATE SET enabled = 0, updated_at = excluded.updated_at
                """,
                (gid_int, now),
            )
        await db.commit()
        logger.info(f"[xilian] 已迁移旧版关闭群配置，共 {len(close_list)} 个群")
    except Exception as e:
        logger.warning(f"[xilian] 迁移旧版配置失败，已跳过: {e}")


async def upsert_group_config(
    group_id: int,
    enabled: bool = True,
    preferred_bot_id: int | None = None,
) -> None:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO group_push_config (group_id, enabled, preferred_bot_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(group_id)
            DO UPDATE SET enabled = excluded.enabled,
                          preferred_bot_id = COALESCE(excluded.preferred_bot_id, group_push_config.preferred_bot_id),
                          updated_at = excluded.updated_at
            """,
            (group_id, 1 if enabled else 0, preferred_bot_id, now),
        )
        await db.commit()


async def set_group_enabled(group_id: int, enabled: bool) -> None:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO group_push_config (group_id, enabled, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(group_id)
            DO UPDATE SET enabled = excluded.enabled,
                          updated_at = excluded.updated_at
            """,
            (group_id, 1 if enabled else 0, now),
        )
        await db.commit()


async def set_preferred_bot(group_id: int, bot_id: int | None) -> None:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO group_push_config (group_id, enabled, preferred_bot_id, updated_at)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(group_id)
            DO UPDATE SET preferred_bot_id = excluded.preferred_bot_id,
                          updated_at = excluded.updated_at
            """,
            (group_id, bot_id, now),
        )
        await db.commit()


async def set_last_sender(group_id: int, bot_id: int) -> None:
    now = int(time.time())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO group_push_config (group_id, enabled, preferred_bot_id, last_sender_bot_id, updated_at)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(group_id)
            DO UPDATE SET last_sender_bot_id = excluded.last_sender_bot_id,
                          updated_at = excluded.updated_at
            """,
            (group_id, bot_id, bot_id, now),
        )
        await db.commit()


async def get_group_config(group_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT enabled, preferred_bot_id, last_sender_bot_id
            FROM group_push_config
            WHERE group_id = ?
            """,
            (group_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "enabled": bool(row[0]),
                "preferred_bot_id": int(row[1]) if row[1] is not None else None,
                "last_sender_bot_id": int(row[2]) if row[2] is not None else None,
            }


async def get_all_group_configs(enabled_only: bool = False) -> list[dict]:
    query = """
        SELECT group_id, enabled, preferred_bot_id, last_sender_bot_id
        FROM group_push_config
    """
    params: tuple = ()
    if enabled_only:
        query += " WHERE enabled = 1"

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    return [
        {
            "group_id": int(row[0]),
            "enabled": bool(row[1]),
            "preferred_bot_id": int(row[2]) if row[2] is not None else None,
            "last_sender_bot_id": int(row[3]) if row[3] is not None else None,
        }
        for row in rows
    ]


async def get_enabled_group_ids() -> list[int]:
    rows = await get_all_group_configs(enabled_only=True)
    return [item["group_id"] for item in rows]


async def remove_group_configs(group_ids: list[int]) -> int:
    if not group_ids:
        return 0

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.executemany(
            "DELETE FROM group_push_config WHERE group_id = ?",
            ((gid,) for gid in group_ids),
        )
        await db.commit()
        return cursor.rowcount if cursor.rowcount is not None else 0