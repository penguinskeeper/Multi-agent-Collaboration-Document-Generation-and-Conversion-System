# 安全说明（Security Policy）

## 支持范围

这是一个**技术演示项目**，用于展示多智能体编排与 Web 服务工程化实践。
不面向生产环境，不提供 SLA，也没有安全响应承诺。

## 上报漏洞

如果你发现了安全问题（越权访问、路径穿越绕过、凭据泄露等），请**不要开公开 Issue**。

首选：使用 GitHub 的
[私密漏洞上报](https://docs.github.com/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
（仓库 Security 标签页 → Report a vulnerability）。

请在报告里说明：

- 问题类型与影响范围
- 复现步骤（最小可复现示例最好）
- 你判断的严重程度

我会尽快确认。修复后会在这里致谢（除非你希望匿名）。

## 部署前必读

这个项目默认配置面向**本机开发**，直接暴露到公网前请至少完成以下几项：

| 项 | 现状 | 你需要做什么 |
|---|---|---|
| 接口鉴权 | `API_KEY` 留空 = 不校验 | 设置 `API_KEY`，客户端带 `X-API-Key` 请求头 |
| CORS | 默认仅允许 `http://localhost:8000` | 改 `API_ALLOWED_ORIGINS` 为你的实际来源 |
| 限流 | **未实现** | 公网部署前自行在反向代理层加限流——Agent 被刷会产生真实 LLM 费用 |
| 数据库账号 | 应用推荐用只读账号 `dsp_reader` | 不要用 root 跑应用；只授 `SELECT` |
| 数据库凭据 | 示例默认值仅供本地 | 覆盖 `docker-compose.yml` 里的演示默认密码 |
| 密钥管理 | `.env` 不入库 | 用环境变量或密钥管理服务注入，别提交进仓库 |

## 已实现的安全措施

- **文件层**：路径穿越防护覆盖 12 类边界场景；上传 / 下载接口做越权校验
- **数据库层**：应用层正则只读校验 + 数据库层只授 `SELECT` 的专用账号（双保险）
- **接口层**：CORS 白名单、`X-API-Key` 校验、上传扩展名白名单与 20MB 大小限制
- **配置层**：`yaml.safe_load` 加载提示词，避免 YAML 注入

详见 [`docs/DESIGN.md`](docs/DESIGN.md) 第 8 节。
