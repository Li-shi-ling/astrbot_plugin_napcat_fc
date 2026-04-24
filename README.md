# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot API 注册为可供 LLM 调用的函数工具。每个接口都按 `@filter.llm_tool` 装饰器格式显式注册，便于后续做工具发现相关改造。

## 功能

- 基于 `docs/napcat-apifox`、`docs/onebot-11/api` 和 `docs/go-cqhttp/api` 生成工具定义。
- 每个发现到的接口都有一个显式 `@filter.llm_tool` 方法，工具名格式为 `napcat_<接口名>`。
- 额外提供通用工具 `napcat_call_api`，用于调用未单独命名或临时新增的接口。
- 复用 AstrBot 默认接入 NapCat 的 aiocqhttp 事件和 bot 实例。

## 配置

在 AstrBot 插件配置中设置：

当前版本使用显式 `@filter.llm_tool` 注册，不再通过配置开关动态增删工具。调用执行仍依赖当前消息事件是 aiocqhttp/NapCat 事件。

## 使用方式

LLM 调用具体接口时使用对应工具，例如 `napcat_send_group_msg`：

```json
{
  "payload": {
    "group_id": "123456",
    "message": "hello"
  }
}
```

调用通用工具时传入接口名和请求体：

```json
{
  "endpoint": "send_private_msg",
  "payload": {
    "user_id": "123456789",
    "message": "hello"
  }
}
```

这些工具必须在 aiocqhttp/NapCat 消息事件上下文中使用；非 aiocqhttp 平台事件会返回错误。

## 开发约束

本项目开发约束见 [CONSTRAINTS.md](CONSTRAINTS.md)。每次功能更新必须同步测试、更新日志、版本号和 README 对应说明。
