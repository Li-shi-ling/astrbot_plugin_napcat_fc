# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot / go-cqhttp 用户 API 注册为可供 LLM 调用的函数工具。每个接口都按 `@filter.llm_tool` 装饰器格式显式注册，便于后续做工具发现相关改造。

## 功能

- 基于 `docs/napcat-apifox`、`docs/onebot-11/api` 和 `docs/go-cqhttp/api` 生成工具定义。
- 每个发现到的用户 API 都有一个显式 `@filter.llm_tool` 方法，工具名格式为 `napcat_<接口名>`。
- 具体接口工具使用字段级参数，例如 `group_id`、`user_id`、`message`，不再要求 LLM 传入统一 `payload`。
- 仅系统专属工具名记录在插件类属性 `WINDOWS_TOOL_NAMES`、`LINUX_TOOL_NAMES`、`MAC_TOOL_NAMES` 中；当前只有 OCR 工具属于 Windows 专属。
- 复用 AstrBot 默认接入 NapCat 的 aiocqhttp 事件和 bot 实例。

## 配置

在 AstrBot 插件配置中设置：

当前版本使用显式 `@filter.llm_tool` 注册，不再通过配置开关动态增删工具。调用执行仍依赖当前消息事件是 aiocqhttp/NapCat 事件。

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
