# ByteMuse

> 自动化 PT 站点订阅与媒体库管理工具 / An automated subscription & media-library orchestration tool for PT sites.

ByteMuse 是一个自托管的私人助理服务，专为 PT 用户设计。它会按计划从排行榜 / 厂牌 / 演员等渠道抓取番剧番号，自动匹配种子，过滤后下载到 qBittorrent / Transmission / 迅雷，并将元数据同步到 Emby / Plex / Jellyfin 等媒体服务器。配套 Telegram / 微信推送与 Web 管理面板，做到“一处订阅、整链路自动化”。

---

## ✨ 主要功能

| 模块 | 能力 |
| --- | --- |
| 🔭 **自动发现** | 拉取榜单（Library / AvDB / Brands）、厂牌、演员订阅源，按番号生成订阅条目 |
| 🎯 **资源匹配** | 自动从 AvDB / AVBase / Bus / Library 等站点获取番号元数据（封面、演员、标签） |
| 🧹 **智能过滤** | 自定义过滤规则（中字、UHD、UC、免费、体积、关键词），可针对每个订阅独立配置 |
| ⬇️ **多客户端下载** | 原生支持 qBittorrent、Transmission、迅雷（远程下载）、Aria2 |
| 🎞️ **媒体库同步** | 检索 Emby / Plex / Jellyfin 中已存在的资源，自动标记完成，避免重复下载 |
| 🔔 **即时通知** | 微信企业号、Telegram Bot（含白名单与防剧透模式） |
| 🌐 **Web 管理面板** | FastAPI 后端，提供订阅、排行榜、演员、配置、消息、管理员等 REST 接口 |
| ⏰ **调度任务** | APScheduler 内置三个定时任务：榜单订阅、演员订阅、下载检查 |
| 🧩 **可扩展模块** | 模块化设计，新增站点 / 客户端只需实现统一接口 |

---

## 🧱 技术栈

- **语言**：Python 3.12
- **Web 框架**：[FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/)
- **数据**：SQLAlchemy 2 + SQLite（默认）/ MySQL（可替换）
- **调度**：[APScheduler](https://apscheduler.readthedocs.io/)
- **打包**：Cython（`modules/ladysite`、`modules/ptsite`、`modules/mongo`）
- **依赖管理**：`requirements.txt`

---

## 📁 项目结构

```
bytemuse/
├── main.py                # 入口：启动 FastAPI 服务
├── settings.py            # 配置加载（基于 .env）
├── setup.py               # Cython 打包配置
├── version.py             # 版本号
├── requirements.txt
│
├── api/                   # FastAPI 路由 & 服务层
│   ├── routes/            # subscribe / actors / config / admin ...
│   └── services/          # 业务实现
├── schduler/              # APScheduler 定时任务
├── services/              # 核心服务（过滤、排序、消息、订阅）
├── modules/               # 适配各外部系统的模块
│   ├── ladysite/          # AvDB / AVBase / Bus / Library / Jable / Brands
│   ├── ptsite/            # PTT / NicePT / MTeam
│   ├── mediaserver/       # Emby / Plex / Jellyfin
│   ├── downloadclient/    # qBittorrent / Transmission / Thunder / Aria2
│   ├── notify/            # WeChat / Telegram
│   ├── cloudnas/          # CloudDrive / CloudNAS 集成
│   ├── dockerhub/         # Docker Hub 镜像查询
│   ├── github/            # GitHub 集成
│   └── mongo/             # MongoDB 共享 & 色花堂
├── database/              # SQLAlchemy 模型 & 会话
├── common/                # 通用对象（Torrent / Response）
├── config/                # 配置模板
├── utils/                 # 工具函数
└── build/                 # Cython 编译产物
```

---

## 🚀 快速开始

### 1. 准备环境

```bash
git clone <your-repo-url> bytemuse
cd bytemuse

# 推荐 Python 3.12
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 编辑配置

复制并按需修改模板：

```bash
cp config/template.env data/app.env   # 程序首次启动会自动拷贝
```

主要字段：

| 区块 | 变量 |
| --- | --- |
| **调度** | `RANK_SCHEDULE_TIME` / `ACTOR_SCHEDULE_TIME` / `DOWNLOAD_SCHEDULE_TIME` |
| **下载客户端** | `QBITTORRENT_*` / `TRANSMISSION_*` / `THUNDER_*` |
| **媒体服务器** | `EMBY_*` / `PLEX_*` / `JELLYFIN_*` |
| **PT 站点** | `PTT_COOKIE` / `NICEPT_COOKIE` / `MTEAM_API_KEY` |
| **刮削源** | `AVDB_COOKIE` / `AVBASE_COOKIE` / `BUS_COOKIE` / `LIBRARY_COOKIE` |
| **通知** | `WECHAT_*` / `TELEGRAM_*` |
| **过滤 / 排序** | `DEFAULT_FILTER` / `DEFAULT_SORT` / `IMAGE_MODE` |

> 完整字段请参考 [`config/template.env`](config/template.env)。

### 3. 启动服务

```bash
python main.py
```

首次启动会自动：

- 初始化 SQLite 数据库（`data/lady.db`）
- 生成 `SECRET_KEY`（写入 `data/app.env`）
- 创建默认管理员账号（用户名 `admin`，随机密码会打印在日志中）
- 启动三个定时任务线程

Web API 默认监听 `http://0.0.0.0:8000`，OpenAPI 文档位于 `/docs`。

### 4. Docker（可选）

当前仓库未自带 Dockerfile，可参考如下最小化示例：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV DOCKER_ENV=1
EXPOSE 8000
CMD ["python", "main.py"]
```

挂载 `/app/data` 用于持久化配置与数据库。

---

## 🧠 核心流程

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  榜单 / 厂牌  │ → │  番号抓取     │ → │  元数据匹配   │
│  演员订阅     │   │ (ladysite)   │   │ (avbase/...) │
└──────────────┘   └──────────────┘   └──────┬───────┘
                                              ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  下载客户端   │ ← │  过滤 / 排序  │ ← │  媒体库去重   │
│ qBittorrent  │   │              │   │ Emby/Plex/JF │
└──────┬───────┘   └──────────────┘   └──────────────┘
       ↓
┌──────────────┐
│  通知推送     │
│ WeChat/TG    │
└──────────────┘
```

---

## 🔌 REST API 概览

所有接口挂载在 `/api/v1` 前缀下，需要登录态（`Authorization: Bearer <token>`）：

| 分组 | 路径 | 说明 |
| --- | --- | --- |
| subscribe | `/dashboard`、`/ranks`、`/codes/list`、`/codes/recommend`、`/codes/release_today` | 订阅与排行榜 |
| actors | `/actors/...` | 演员订阅管理 |
| config | `/config/...` | 运行时配置读写 |
| picproxy | `/picproxy/...` | 图片反代（防止外链被墙） |
| admin | `/admin/...` | 用户与系统管理 |
| message | `/message/...` | 消息与通知 |

> 完整接口定义见 `api/routes/`。

---

## 🛠️ 二次开发

新增一个外部系统（站点 / 客户端 / 媒体服务器）只需：

1. 在 `modules/<group>/` 下新建继承基类的实现；
2. 在 `modules/__init__.py` 的 `Module` 类中暴露属性；
3. 通过 `config/template.env` 与 `settings.py` 添加对应配置项；
4. 在 `services/` 中按需编排调用即可。

`get_module()` 单例保证所有适配器共享同一份配置。

---

## ⚠️ 免责声明

- 本项目仅供**个人学习与家庭自用**；
- 请勿用于任何侵犯版权或违反所在地法律的用途；
- 项目作者不对因使用本项目产生的任何纠纷承担责任；
- 仓库保持私有（Private），请勿公开传播或商用。

---

## 📜 License

Private / All rights reserved.