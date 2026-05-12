# Repo Health

GitHub 仓库代码健康度分析平台。用户输入 public GitHub repo URL 后，后端异步浅克隆最近 100 个 commit，生成 7 天有效、可分享的分析报告。

## 架构

- Frontend: React + Vite，轮询任务进度，展示总分、雷达图、commit 热力图、高风险文件和可展开详情。
- API: FastAPI，负责创建任务、限流、读取任务状态和报告。
- Queue: Redis list + 独立 worker，避免 HTTP 请求超时。
- Storage: Redis TTL key，报告 7 天过期，同 repo 24 小时内命中缓存。
- Analyzer: Git 浅克隆、语言识别、静态分析、Git 历史分析、依赖漏洞查询、README 评分、综合评分。

## 本地启动

```bash
docker compose up --build
```

打开：

- Web: http://localhost:5173
- API health: http://localhost:8000/api/health

## 环境变量

| 名称 | 默认值 | 用途 |
| --- | --- | --- |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接 |
| `FRONTEND_ORIGIN` | `*` | CORS origin |
| `WORK_DIR` | `/tmp/repo-health-work` | 仓库克隆临时目录 |
| `REPORT_TTL_SECONDS` | `604800` | 分享报告有效期 |
| `CACHE_TTL_SECONDS` | `86400` | 同 repo 缓存期 |
| `RATE_LIMIT_COUNT` | `5` | 单 IP 窗口内分析次数 |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | 限流窗口 |
| `OPENAI_API_KEY` | 空 | 配置后 README 评分使用 LLM，否则用确定性规则 |

## 测试

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. pytest
```

Windows PowerShell:

```powershell
cd backend
pip install -r requirements.txt
$env:PYTHONPATH='.'
pytest
```

## 部署

仓库包含 `render.yaml`，可在 Render 以 Blueprint 方式部署 API、worker、Redis 和前端。首次部署后，把 `render.yaml` 里 `VITE_API_BASE_URL` 改成实际 API 域名，重新部署前端即可。

生产建议使用至少 starter 级别实例分析大型仓库，例如 `facebook/react`。免费实例在浅克隆和扫描大型 repo 时可能超时或休眠。

## API

- `POST /api/analysis` 创建分析任务
- `GET /api/analysis/{job_id}` 查询进度
- `GET /api/reports/{report_id}` 查询报告
