# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot HTTP API 批量注册为可供 LLM 调用的函数工具。

## 功能

- 自动扫描 `docs/napcat-apifox` 中的 OpenAPI Markdown 文档。
- 为每个发现到的接口注册一个函数工具，工具名格式为 `napcat_<接口名>`。
- 额外提供通用工具 `napcat_call_api`，用于调用未单独命名或临时新增的接口。
- 使用 OneBot HTTP POST 调用 NapCat，并支持 `access_token`。

## 配置

在 AstrBot 插件配置中设置：

- `base_url`：NapCat OneBot HTTP 地址，默认 `http://127.0.0.1:3000`。
- `access_token`：OneBot 访问令牌，留空则不发送 `Authorization`。
- `timeout`：接口请求超时时间，单位秒。
- `tool_prefix`：函数工具名前缀，默认 `napcat`。
- `register_tools`：是否注册函数工具。
- `enable_generic_tool`：是否注册通用调用工具。

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

## 开发约束

本项目开发约束见 [CONSTRAINTS.md](CONSTRAINTS.md)。每次功能更新必须同步测试、更新日志、版本号和 README 对应说明。
