\# 更新日志



\## \[1.0.1] - 2026-09-24



\### 新增

\- 定时推送到指定群（`push\_groups` / `push\_hour` / `push\_minute`）

\- 平台实例 ID 配置（`push\_platform\_id`），支持 NapCat / QQ官方 / 微信

\- `push\_groups` 支持纯群号和完整 UMO 两种填法

\- README 完整文档



\### 优化

\- 渲染改用元素裁剪，消除底部白底

\- 副标题字号缩小，半栏区高度按内容撑开，全宽卡片间距收紧

\- 精简 `requirements.txt`，移除 AstrBot 已自带的依赖（httpx / pydantic / jinja2 / playwright）



\### 修复

\- 板块数据键 `items` 与 Jinja2 内置方法冲突

\- 缓存命中导致新代码不生效

\- 硬编码 `aiocqhttp` 前缀导致 NapCat 推送失败



\## \[1.0.2] - 2026-09-17



首个可用版本，参考 Ubot/ubot-plugin-wwreport 重写。

