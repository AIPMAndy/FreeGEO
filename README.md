# FreeGEO · 开源 AI 搜索增长工作台

**真实用户问题 → 证据诊断 → 可执行修复 → 固定面板复测 → 商业结果。**

MIT · 浏览器本地优先 · 核心免费 · 无需注册或模型密钥 · 可选付费官方 API

[在线使用](https://aipmandy.github.io/FreeGEO/) · [快速上手](docs/QUICKSTART.md) · [深度研究](docs/RESEARCH.md) · [研究网页版](docs/research.html) · [v0.3 对抗式验收](docs/RELEASE_V03.md) · [真实业务试点](examples/pilots/README.md) · [GEO Handbook](https://github.com/AIPMAndy/geo-handbook) · [AI 酋长 Andy](https://metaver.vip/) · 微信 `AIPMAndy`

## 5 分钟获得下一步行动

双击 `index.html`，或启动 `python3 -m http.server 8000`，打开 `http://localhost:8000`。建议使用独立本地来源，确保浏览器允许本地存储。无需构建依赖。

1. **开始**：填品牌、真实服务、目标客户及精确 URL 范围，保存后获得按证据排列的任务。多个项目可独立保存。
2. **机会与缺口**：生成待验证问题，使用真实咨询/搜索记录核验，关联真正能帮助用户的页面。添加竞品范围，仅比较实际回答引用；不是排名或市场份额。
3. **页面体检**：粘贴目标页面 HTML，保存诊断并自动生成修复任务。实际 HTTP / robots.txt 可使用 Site Doctor（下方）。
4. **事实库、固定采样实验**：录入可核查事实；选择已验证问题，锁定面板，下载基线 CSV，在实际搜索入口采集。导回真实结果后登记干预，按相同条件复测。未执行、失败、未知分开。
5. **修复与验收**：下载任务包给工程师或 AI 编程助手；有执行凭证、复核凭证、复核人和日期才允许标为已验收。可以为已验证问题生成事实驱动的页面 Brief。执行与上线需人工确认。
6. **商业事件和报告**：记录真实业务事件，导出整个项目或全部项目库、Markdown 报告。以实际成本、线索和收入判断是否继续，不保证排名或收入。

`examples/pilots/` 内有两个基于公开真实网页的工作区，未采集的 AI 指标保持为空。`打开示例` 则是完全虚构的教学数据，不能当业绩。

## V0.3 实战功能

| 功能 | 实际能力与边界 |
|---|---|
| 多项目库 | 旧工作区迁移、独立保存、切换、全部备份与恢复；冲突时提示，当前最多 30 个项目/4MB 本地库。恢复全部是替换操作，先备份。 |
| 需求研究 | 根据业务组合可编辑假设；逐问题分析承接页、样本覆盖、外部信源；不是关键词搜索量。 |
| 固定面板 | 锁定问题文本、条件和重复序号；导出前后同条件 CSV；拒绝篡改和额外槽位。 |
| 技术诊断 | 离线 HTML 检查自动生成任务；Site Doctor JSON 可导入实际 HTTP/robots 检查，保留证据。 |
| 竞品 | 仅按声明 URL 范围统计记录中出现的链接，不自动推断推荐。 |
| 修复验收 | P0/P1/P2/待核验、实际动作、验收条件、人工复核凭证；AI 工程任务包、内容 Brief。 |
| 官方 API 采样 | 可选 OpenAI Responses API web_search；只读采样、请求数量上限、默认 dry-run、原始响应留档；API ≠ ChatGPT 网页端，需人工审查语义标签。 |
| 爬虫日志 | 离线汇总常见 combined log 中声明的 User-Agent 与 HTTP 状态；不证明真实爬虫身份，不导出 IP/路径/查询。 |
| 研究与测量 | 29 个补充研究单元、引用分母与覆盖、匹配实验、收入按币种与归因类别分开。 |

## 命令行（Node 18+ / Python 3.10+，标准库）

```sh
node cli.js validate examples/pilots/personal.json
node cli.js opportunities examples/pilots/personal.json
node cli.js plan examples/pilots/company.json
node cli.js report examples/pilots/company.json > report.md
node cli.js agent examples/pilots/company.json > tasks.md
node cli.js panels my-project.json
node cli.js panel-csv my-project.json PANEL_ID baseline > baseline.csv
# 先读取真实 HTML；--url 仅指定上下文，不联网
python3 site_doctor.py --file index.html --url https://example.com/tool/ --json > audit.json
# 用户明确开启时才访问给定公网页面及最终域名根 robots.txt
python3 site_doctor.py --live --url https://example.com/ --json > audit.json
# 离线汇总自己的授权访问日志
python3 crawler_logs.py access.log > crawler-report.json
```

### 可选：官方 API 自动采集（可能收费）

在固定面板填写 `OpenAI:YOUR_MODEL:web_search` 作为入口（使用账户实际支持的模型），终端 `API`，地区用 ISO 两字母代码，语言如 `zh-CN`。下载 CSV。**先 dry-run，再决定是否调用。**

```sh
python3 api_sampler.py baseline.csv --model YOUR_MODEL --max-requests 3
# 在本机安全设置 OPENAI_API_KEY；不粘贴到网页、聊天或 GitHub
# 用户确认费用后才执行，不会自动重试或覆盖已有文件
python3 api_sampler.py baseline.csv --model YOUR_MODEL --max-requests 3 --execute --accept-cost --output results.csv
```

仅发送问题文本和采样条件，不发送整个项目或事实库。请移除私人数据。API 费用由服务商计收，调用次数与输出 token 限制不是金额上限；核对账户预算。官方资料：[Web search](https://developers.openai.com/api/docs/guides/tools-web-search)、[Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)。本版已通过模拟响应测试，尚未使用真实密钥联调。原始 JSONL 可能包含公开搜索和用户问题中的内容，应保存在本地，不提交 Git。人工复核三项语义标签后导回结果 CSV。其他平台可通过合规手工观察或已获授权的数据导入，不自动登录或绕过验证码。

## 安全、测试与发布

```sh
node --test tests/*.test.js
python3 -m unittest discover -s tests -p 'test_*.py' -v
pip install playwright
python -m playwright install chromium
python tests/browser_dom.py
python tests/browser_smoke.py
```

`CHROMIUM=/path/to/chromium` 可指定系统浏览器。隔离 DOM 测试覆盖多项目、固定面板、引用伪装、验收和移动端，不代替 HTTP 端到端。CI 配置包含实际 HTTP 冒烟测试；必须在目标环境通过才能宣布正式发布。GitHub Pages：新建公共仓库，上传项目根目录，启用 Pages（main / root），以实际发布地址为准。GitHub Pages 项目子路径的 robots.txt 不是域名根规则。

不执行用户输入的 HTML/外部资料中的命令，不虚构搜索结果、不写虚假评价或排行榜；数据本地保存，不自动发布。CSV 导入全批校验；API 仅显式执行；不保存 API Key。源码诊断无法证明索引，引用无法证明推荐，相关性不能证明因果。官方依据：[Google AI 搜索优化](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)、[OpenAI crawlers](https://developers.openai.com/api/docs/bots)、[Bing AI Performance](https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c)。

原始 X 帖仍无法完整取得；研究报告使用公开大会的 29 个结构化单元作为补充，不等于原帖逐一核验。保留来源和局限，不复制未授权课件。

**AI 酋长 Andy · 星觉科技** — [官网](https://metaver.vip/) · 微信 `AIPMAndy` · [GitHub](https://github.com/AIPMAndy)
