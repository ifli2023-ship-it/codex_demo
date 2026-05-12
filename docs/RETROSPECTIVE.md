# 开发过程复盘

## 遇到的坑

1. 大型仓库扫描容易超时。处理方式是浅克隆最近 100 个 commit，跳过 `.git`、`node_modules`、`target`、`vendor` 等目录，并限制单文件最大读取体积。
2. 不同语言的函数边界差异很大。这里对 Python 使用 AST，对 JavaScript/TypeScript、Go、Rust 使用轻量 brace parser，满足跨语言概览，但不是编译器级精度。
3. 漏洞库跨生态不统一。实现里统一查询 OSV batch API，它覆盖 PyPI、npm、Go、crates.io，并能链接到具体漏洞页。
4. README 质量评分要求 LLM，但部署环境未必有 OpenAI key。实现为有 `OPENAI_API_KEY` 时走 LLM，没有 key 时走确定性 rubric，保证平台可运行。
5. 分享报告需要过期和缓存共存。最终用 Redis TTL key 分别管理报告 7 天有效和 repo 24 小时缓存，逻辑比较清晰。

## 取舍

- 实时进度选择轮询而不是 WebSocket，部署和前端状态更简单，用户体验仍然接近实时。
- 重复代码率使用规范化行重复率，而不是 token/AST 克隆检测。优点是快、跨语言；缺点是对结构性重复的识别较粗。
- 复杂度统计是启发式圈复杂度，适合风险排序，不适合替代专业语言工具。
- 依赖解析覆盖 `requirements.txt`、`package.json`、`go.mod`、`Cargo.toml` 的主路径，暂未解析 lockfile 中完整依赖树。

## 还可以继续做

- 为每种语言接入成熟 analyzer，例如 radon、eslint complexity、gocyclo、rust-code-analysis。
- 增加 GitHub App OAuth，支持私有仓库。
- 把报告持久化到 Postgres/S3，而不是只放 Redis。
- 增加后台取消任务、任务并发上限和管理员面板。
- 增加 Playwright 端到端测试和部署后 smoke test 自动化。
