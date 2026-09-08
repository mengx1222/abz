# 快速部署指南（新机器 / 朋友电脑）

> 目标：Clone 仓库后用 Docker 一键启动「安诊保 AI 副驾」全栈（真实 AI 对话 + 知识库关键词检索）。
> 适用系统：Windows / macOS / Linux 上已安装 Docker + Docker Compose 插件。

---

## 1. 准备

```bash
git clone https://github.com/mengx1222/abz.git
cd abz
```

## 2. 配置环境变量（唯一需要手工填写的是 AI Key）

```bash
cp .env.example .env
```

打开 `.env`,确认/修改这几项：

| 变量 | 值 | 说明 |
|------|----|------|
| `AZB_AI_API_KEY` | **向部署负责人索取** | 密钥不入 Git 仓库；示例 key 形如 `sk-...`（opencode.ai） |
| `AZB_JWT_SECRET_KEY` | 建议改成自己的随机串 | 登录令牌签名密钥 |
| `AZB_DEMO_PASSWORD` | 建议改成强密码 | 演示账号统一密码（默认 888888，演示用足够） |

其余已填默认值即可：AI 网关 `https://opencode.ai/zen/go/v1`、模型 `deepseek-v4-flash`、
路由标识 `anzhenbao-demo`、PostgreSQL/Redis 均在 Docker 内网。

## 3. 启动

```bash
docker compose up -d --build
```

首次构建约 5~10 分钟（前端 npm + 后端 pip 都在镜像内完成）。启动时后端自动执行
`alembic 迁移 → 播种演示数据`，无需手工建库。

## 4. 验证

- 打开 http://localhost:3000 → 登录页底部「演示账号快捷登录」或手机号 `13800138000` / 密码 `888888`（或你在 `.env` 里改的 `AZB_DEMO_PASSWORD`）
- 工作台「今日工作 / AI 今日建议」可点击跳转
- 进入 **AI 产品专家** 提问（如“百万医疗险的等待期是多久？”）→ 应显示「正在思考」后给出**带来源引用的回答**
- 管理后台（用系统管理员演示账号 13800138003 登录）→ 用户管理可真实创建/编辑/重置密码/禁用

## 5. 日常维护

```bash
# 更新到最新代码并重建
git pull
docker compose up -d --build

# 看日志
docker compose logs -f backend

# 健康检查
curl http://localhost:8000/api/v1/ready
```

## 6. 注意事项

- **密钥安全**：`AZB_AI_API_KEY` 只在本地 `.env`（已被 .gitignore 排除），永远不要放进仓库。
- **知识库检索模式**：当前 opencode.ai 网关无 `/embeddings`,知识库问答走**中文 2-gram 关键词检索**
  降级路径（已内置于代码，无需配置）；若日后需要语义向量检索，配置一个支持 embedding 的
  Provider 即可（见 docs/ops-runbook.md §1）。
- **外网演示**：需要固定公网地址时参见 docs/ops-runbook.md；临时把服务暴露给老板/朋友看
  可用 `cloudflared tunnel --url http://localhost:3000`（免费，重启后地址变化）。
- 详细运维（监控/备份/压测/限流）见 [docs/ops-runbook.md](ops-runbook.md)。