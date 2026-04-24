# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot / go-cqhttp 用户 API 注册为可供 LLM 调用的函数工具。每个接口都按 `@filter.llm_tool` 装饰器格式显式注册，便于后续做工具发现相关改造。

## 功能

- 基于 `docs/napcat-apifox`、`docs/onebot-11/api` 和 `docs/go-cqhttp/api` 生成工具定义。
- 每个发现到的用户 API 都有一个显式 `@filter.llm_tool` 方法，工具名格式为 `napcat_<接口名>`。
- 具体接口工具使用字段级参数，例如 `group_id`、`user_id`、`message`，不再要求 LLM 传入统一 `payload`。
- 仅系统专属工具名记录在插件类属性 `WINDOWS_TOOL_NAMES`、`LINUX_TOOL_NAMES`、`MAC_TOOL_NAMES` 中；当前只有 OCR 工具属于 Windows 专属。
- 复用 AstrBot 默认接入 NapCat 的 aiocqhttp 事件和 bot 实例。
- 初始化时创建工具管理数据库 `napcat_fc_tools.db`，记录工具名、API、能力、字段参数、平台限制和启用状态，便于后续动态工具发现。
- NapCat 工具默认不作为全局 active 工具常驻暴露，而是在 `on_llm_request(priority=-100)` 阶段按数据库 `enabled` 状态注入到本轮请求，注入前会先卸载本轮请求里已有的 NapCat 工具。
- `napcat_search_tools` 搜索工具会一直注入到请求中。它按关键词模糊搜索 NapCat 工具，将最相关的前 3 个工具加入持久化发现队列，并立即注入当前请求的后续工具调用。

## 配置

当前版本使用显式 `@filter.llm_tool` 注册，不再通过配置开关动态增删工具。调用执行仍依赖当前消息事件是 aiocqhttp/NapCat 事件。

工具管理数据库位于 AstrBot 插件数据目录，表名为 `napcat_tool`。插件启动时会按当前 `main.py` 中的工具定义同步记录，保留已有 `enabled` 状态并移除已不存在的工具。外部工具发现逻辑可以读取 `enabled`、`parameters_json`、`required_parameters_json` 和 `platforms_json` 字段进行筛选。

搜索发现队列持久化在 `napcat_discovered_tool` 表中，最多保存 20 个工具。重复搜索到同一工具时会去重并刷新到队尾；超过 20 个时按 FIFO 队列出队。已发现工具会在后续请求直接注入，不需要再次做数据库搜索。

如需临时关闭动态注入，可在插件配置中设置 `dynamic_injection_enabled: false`。此时请求阶段仍会先卸载本轮请求里已有的 NapCat 工具，但不会再注入新的 NapCat 工具。

## 使用方式

LLM 调用具体接口时使用对应工具，例如 `napcat_send_group_msg`：

```json
{
  "group_id": "123456",
  "message": "hello",
  "auto_escape": false
}
```

这些工具必须在 aiocqhttp/NapCat 消息事件上下文中使用；非 aiocqhttp 平台事件会返回错误。

## 开发约束

本项目开发约束见 [CONSTRAINTS.md](CONSTRAINTS.md)。每次功能更新必须同步测试、更新日志、版本号和 README 对应说明。
