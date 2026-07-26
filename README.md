# 这是byte-muse的legacy版本未加密代码

# ByteMuse

> 自动化 PT 站点订阅与媒体库管理工具 / Automated PT subscription and media-library orchestration.

ByteMuse 是自托管的 PT 订阅服务，支持从榜单 / 厂牌 / 演员来源抓取番号，按规则过滤后下发到下载客户端，并与媒体库/消息通知打通。

---

## 介绍

- 支持榜单、厂牌、演员订阅全链路处理
- 规则化过滤与排序（关键词、体积、分辨率、UC 等）
- 下载客户端：qBittorrent / Transmission / 迅雷 / Aria2
- 媒体库：Emby / Plex / Jellyfin
- 通知：微信企业号、Telegram
- REST API：FastAPI 提供管理与控制接口

## 技术栈

- Python 3.12
- FastAPI + Uvicorn
- SQLAlchemy 2 + SQLite（默认）
- APScheduler
- 依赖管理：`requirements.txt`

## 快速开始

<details>
<summary>环境与启动</summary>

```bash
git clone <your-repo-url> bytemuse
cd bytemuse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/template.env data/app.env
python main.py
```

</details>

## 运行地址

- 接口前缀：`/api/v1`
- 文档：`/docs`
- 默认监听：`http://0.0.0.0:8000`

## 配置项（示例）

<details>
<summary>核心配置目录</summary>

- 调度：`RANK_SCHEDULE_TIME`、`ACTOR_SCHEDULE_TIME`、`DOWNLOAD_SCHEDULE_TIME`
- 下载：`QBITTORRENT_*`、`TRANSMISSION_*`、`THUNDER_*`
- 媒体库：`EMBY_*`、`PLEX_*`、`JELLYFIN_*`
- PT 源：`PTT_COOKIE`、`NICEPT_COOKIE`、`MTEAM_API_KEY`
- 通知：`WECHAT_*`、`TELEGRAM_*`

完整变量请参考 [config/template.env](config/template.env)。

</details>

## 项目结构

<details>
<summary>核心目录</summary>

```text
bytemuse/
├── api/              # 路由与服务
├── modules/          # 外部系统适配
├── database/         # 数据库模型与会话
├── services/         # 业务服务
├── config/           # 配置模板
├── utils/            # 工具函数
└── main.py / settings.py / version.py
```

</details>

## 安全提示

- 首次启动会自动创建管理员账号，建议启动后立即修改。
- 建议删除或迁移日志中可能出现的敏感信息。
- 生产环境请避免在公网直接暴露管理接口。

## 免责声明

仅供个人学习与家庭自用，禁止用于非法用途。

## License

Private / All rights reserved.

