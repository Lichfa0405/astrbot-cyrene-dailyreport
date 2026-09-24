# 昔涟日报 · astrbot_plugin_xilian_report

AstrBot 的聚合日报插件。每天定时生成一张粉色调的日报图片，推送到指定群聊。

参考 [Ubot/ubot-plugin-wwreport](https://github.com/UsotsukiKaze/Ubot) 的设计重写，代码层重构成"板块化 + 配置驱动"架构，方便长期扩展。

---

## 特性

- **一张图聚合多个信息源**：节日倒计时 / B站热点 / IT资讯 / 60S读世界 / 今日一言
- **板块化架构**：每个板块独立实现，可单独开关、可配置 Cookie
- **配置驱动扩展**：在 WebUI 里填一段 JSON 就能接入新数据源，不用改代码
- **定时推送**：每天指定时间自动推送到配置的群
- **平台实例可配置**：支持 NapCat / QQ官方 / 微信等多平台（填写平台实例 ID）
- **渲染独立**：图片渲染失败不影响主流程，缓存命中直接返回

---

## 安装

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
```

> **注意**：AstrBot 已自带 `httpx`、`pydantic`、`jinja2`、`playwright`，所以 `requirements.txt` 里**不要**再声明它们，否则每次启动 AstrBot 都会重新下载（playwright 的 wheel 有 48MB）。

### 2. 放置插件

将整个 `astrbot_plugin_xilian_report/` 目录放到 AstrBot 的插件目录下：

```
<AstrBot>/data/plugins/astrbot_plugin_xilian_report/
```

重启 AstrBot 或在 WebUI 里重载插件。

---

## 目录结构

```
astrbot_plugin_xilian_report/
├── main.py                # 插件入口：命令、定时调度、推送
├── collector.py           # 数据聚合：并发调用各板块
├── render.py              # HTML → PNG 渲染
├── date_utils.py          # 节日倒计时计算
├── http_client.py         # 带重试的 HTTP 客户端
├── db.py                  # 群配置存储（SQLite）
├── models.py              # Pydantic 数据模型
├── blocks/                # 各板块实现
│   ├── base.py            # 板块基类 BlockMeta / BaseBlock
│   ├── __init__.py        # 注册表
│   ├── festival.py        # 节日倒计时
│   ├── bili_hot.py        # B站热点
│   ├── it_news.py         # IT资讯
│   ├── six_news.py        # 60S读世界
│   ├── hitokoto.py        # 今日一言
│   └── custom.py          # 通用板块（配置驱动）
├── templates/xilian_report/   # 渲染模板
│   ├── main.html
│   ├── main.css
│   └── res/                   # 字体、图标、立绘
├── data/                      # 运行时生成：数据库和缓存
├── _conf_schema.json      # 配置 schema
├── metadata.yaml          # 插件元数据
└── requirements.txt
```

---

## 命令

| 命令 | 权限 | 说明 |
|---|---|---|
| `/日报` 或 `/昔涟日报` | 所有人 | 生成并发送日报图片 |
| `/日报帮助` | 所有人 | 查看指令列表 |
| `/日报状态 <群号>` | 管理员 | 开启指定群推送 |
| `/日报状态 --close <群号>` | 管理员 | 关闭指定群推送 |
| `/测试推送日报` | 管理员 | 立即对配置的目标测试推送一次 |
| `/日报自检` | 管理员 | 查看数据库和推送状态 |
| `/重置日报` | 管理员 | 清除今日缓存 |

---

## 配置

全部通过 AstrBot WebUI 的「插件配置」页面调整。

### 基础

| 项 | 默认 | 说明 |
|---|---|---|
| `report_title` | `昔涟日报` | 顶部大标题 |
| `report_subtitle` | `把今天的好消息，轻轻装进信箱。` | 副标题 |
| `full_show` | `false` | 是否完整显示长文本（关闭则单行截断） |
| `alapi_token` | 空 | ALAPI Token（用于 60S 板块，可选） |

### 定时推送

| 项 | 默认 | 说明 |
|---|---|---|
| `auto_send` | `true` | 是否开启定时推送 |
| `push_groups` | 空 | 推送目标，详见下方「推送目标格式」 |
| `push_platform_id` | `093` | 平台实例 ID，填纯群号时使用 |
| `push_hour` | `8` | 推送小时（0-23） |
| `push_minute` | `1` | 推送分钟（0-59） |
| `notify_superuser` | `true` | 推送完成后私聊管理员 |
| `notify_group_id` | `0` | 推送结果通知群号（留空不通知） |

### 推送目标格式（`push_groups`）

支持两种格式，多个用英文逗号分隔：

**格式 1：纯群号**

```
1102322910
```

会自动用 `push_platform_id` 拼接成 `093:GroupMessage:1102322910`。

**格式 2：完整 UMO**

```
093:GroupMessage:1102322910
```

**UMO 怎么查**：在群里发一次 `/日报`，然后看 AstrBot 日志，会有一条 `[xilian][DEBUG] UMO = xxx` 记录（如果没开调试，见「常见问题 - 怎么知道我的平台实例 ID」）。

多个示例：

```
1102322910,1102322911
```

或混合：

```
1102322910,093:GroupMessage:1102322911
```

### 板块开关

每个板块都有 `block_<id>_enabled` 和 `block_<id>_cookie` 两个配置项。

| 板块 | 前缀 | 默认开启 | 是否需要 Cookie |
|---|---|---|---|
| 节日倒计时 | `block_festival_` | ✅ | ❌ |
| B站热点 | `block_bili_hot_` | ✅ | 可选 |
| IT资讯 | `block_it_news_` | ✅ | 可选 |
| 60S读世界 | `block_six_news_` | ❌ | 可选 |
| 今日一言 | `block_hitokoto_` | ✅ | ❌ |

> **关于 Cookie**：默认所有数据源都是公开接口，留空即可。只有在遇到限流、返回空数据、或想要个性化内容时，才需要填写。

---

## 加一个新板块

### 方式 1：配置驱动（推荐，无需改代码）

在 WebUI 的 `custom_blocks` 里填一段 JSON 数组，每一条就是一个新板块。

```json
[
  {
    "id": "zhihu",
    "title": "知乎热榜",
    "icon": "./res/icon/hitokoto.png",
    "url": "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
    "format": "json",
    "items_path": "data",
    "title_key": "target.title",
    "limit": 10,
    "layout": "full",
    "order": 35
  }
]
```

字段说明：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✅ | 唯一标识，配置开关会变成 `block_<id>_enabled` |
| `title` | ✅ | 显示的标题 |
| `icon` | ⬜ | 图标相对路径，可复用 `./res/icon/` 下的现有图标 |
| `url` | ✅ | 数据源 URL |
| `format` | ⬜ | `json` / `rss` / `text`，默认 `json` |
| `items_path` | ⬜ | JSON 里取列表的路径，如 `data.list`。留空则按整段处理 |
| `title_key` | ⬜ | 每条数据里取标题的键，如 `title` / `name` / `target.title`。留空会自动尝试常见键 |
| `limit` | ⬜ | 最多显示几条，默认 10 |
| `layout` | ⬜ | `full`（整行）/ `half`（半栏，与另一个 half 并排），默认 `full` |
| `order` | ⬜ | 排序，小的在前，默认 50 |
| `cookie` | ⬜ | 若接口需要登录，填 Cookie 字符串 |

### 方式 2：写代码（复杂逻辑）

1. 在 `blocks/` 下新建 `xxx.py`，继承 `BaseBlock`
2. 实现 `fetch(ctx, cookie)` 和 `to_template(raw)`
3. 在 `blocks/__init__.py` 末尾加 `from . import xxx`
4. 在 `_conf_schema.json` 加 `block_xxx_enabled` 和 `block_xxx_cookie`

**最小示例**：

```python
from .base import BaseBlock, BlockMeta
from . import register
from ..http_client import AsyncHttpx, DEFAULT_HEADERS


class MyBlock(BaseBlock):
    meta = BlockMeta(
        id="my_block",
        title="自定义板块",
        icon="./res/icon/hitokoto.png",
        order=60,
        layout="full",
    )

    async def fetch(self, ctx, cookie):
        headers = dict(DEFAULT_HEADERS)
        if cookie:
            headers["Cookie"] = cookie
        res = await AsyncHttpx.get("https://example.com/api", headers=headers)
        return res.json().get("items", [])[:10]

    def to_template(self, raw):
        return {"items": raw}


register(MyBlock())
```

---

## 常见问题

### 图片是纯文本，没样式

1. 删掉 `data/cache/*.png` 缓存重试
2. 确认 `render.py` 用的是 `page.goto("file://...")` 而不是 `set_content`
3. 检查 `templates/xilian_report/res/` 下的字体、图标是否齐全

### 报 `Executable doesn't exist at ...chromium-xxxx`

Playwright 的 Chromium 没装：

```bash
playwright install --with-deps chromium
```

用 AstrBot 环境里的 playwright：

```bash
sudo /root/.local/share/uv/tools/astrbot/bin/playwright install --with-deps chromium
```

国内慢的话换镜像：

```bash
sudo env PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright \
  /root/.local/share/uv/tools/astrbot/bin/playwright install chromium
```

### 报 `libnss3.so: cannot open shared object file`

系统库缺失，跑一次：

```bash
playwright install-deps chromium
```

### 修改子模块（如 `render.py`、`blocks/*.py`）后重载无效

AstrBot 的「重载插件」**不会**重新加载子模块，只重新加载主模块。改了子模块必须**重启 AstrBot 进程**：

```bash
sudo pkill -f "astrbot run"
```

如果 AstrBot 用 guardian 管理，会自动拉起新进程。

### 提示 `cannot find platform for session aiocqhttp:GroupMessage:xxx`

平台实例 ID 写错了。用 `/日报` 命令抓一下真实的 UMO：

1. 在目标群里发一次 `/日报`
2. 看日志里 `[xilian][DEBUG] UMO = xxx`
3. 冒号前的那段（如 `093`）就是 `push_platform_id` 该填的值

### 怎么知道我的平台实例 ID

两种方式：

**方式 1：看日志里的 UMO**

在 `main.py` 的 `cmd_report` 里临时加一行：

```python
logger.error(f"[xilian][DEBUG] UMO = {event.unified_msg_origin}")
```

在目标群发一次 `/日报`，看日志。

**方式 2：看 AstrBot 启动日志**

```bash
sudo grep -iE "platform|adapter" /var/log/astrbot/astrbot.log | grep -iE "instance|loaded"
```

### 推送 2 分钟后还没收到

看日志：

```bash
sudo tail -50 /var/log/astrbot/astrbot.log | grep -iE "xilian|push"
```

- `目标群: 1 成功: 1` → 已发送，QQ 那边可能延迟
- `目标群: 1 成功: 0 失败: 1` → 发送失败，看失败详情
- 完全没 `[xilian]` → 定时任务没触发，检查 `push_hour` / `push_minute`

---

## 更新 / 维护

### 版本号

每次发版改 `metadata.yaml` 的 `version` 字段：

| 改动类型 | 版本变化示例 |
|---|---|
| 修 bug、调样式 | `1.1.0` → `1.1.1` |
| 加功能（新板块、新推送） | `1.1.3` → `1.2.0` |
| 大重构、不兼容旧配置 | `1.9.5` → `2.0.0` |

### 打包上传

排除缓存和运行时数据：

```bash
zip -r astrbot_plugin_xilian_report.zip astrbot_plugin_xilian_report \
  -x "*/__pycache__/*" "*.pyc" ".git/*" \
     "astrbot_plugin_xilian_report/data/cache/*" \
     "astrbot_plugin_xilian_report/data/*.db"
```

### AstrBot 4.28.1+ 的原地更新

AstrBot 4.28.1 及更高版本支持通过 WebUI 直接上传 zip 覆盖已安装的插件。上传前确保 `metadata.yaml` 的 `version` 已递增。

**4.28.0 及更早版本不支持**，需要先卸载旧插件，或直接用服务器脚本覆盖。

### 服务器上快速更新脚本

放在插件目录外（比如 `data/plugins/deploy_xilian.sh`），每次本地打包后 scp 上去，执行：

```bash
sudo bash deploy_xilian.sh /tmp/astrbot_plugin_xilian_report.zip
```

脚本会自动备份、解压、保留 `data/`、清缓存、重启进程。

---

## 许可

参考原 Ubot 插件重写。原始插件遵循相应开源协议，本重写版本以 MIT 发布。