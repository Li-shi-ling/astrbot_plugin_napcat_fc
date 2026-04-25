# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot / go-cqhttp 用户 API 注册为可供 LLM 调用的函数工具。每个接口都按 `@filter.llm_tool` 装饰器格式显式注册，便于后续做动态工具发现和按需注入。

## 功能

- 基于 `docs/napcat-apifox`、`docs/onebot-11` 和 `docs/go-cqhttp` 生成工具定义。
- 每个发现到的用户 API 都有一个显式 `@filter.llm_tool` 方法，工具名格式为 `napcat_<接口名>`。
- 具体接口工具使用字段级参数，例如 `group_id`、`user_id`、`message`，不要求 LLM 传入统一 `payload`。
- 复用 AstrBot 默认接入 NapCat 的 `AiocqhttpMessageEvent` 和当前事件的 `event.bot.api.call_action`，不自建 HTTP 客户端。
- 初始化时创建工具管理数据库 `napcat_fc_tools.db`，记录工具名、API、能力、参数、平台限制和启用状态，供动态工具发现使用。
- NapCat 工具默认不作为全局 active 工具常驻暴露，而是在 `on_llm_request(priority=-100)` 阶段按搜索发现结果和数据库状态注入到当前请求。
- `napcat_search_tools` 搜索工具会一直注入到 aiocqhttp/NapCat 请求中。它支持空格分词并发搜索，先合并综合相关度最高的一批候选，再排除已发现工具，将剩余最相关的前 3 个工具加入持久化发现队列，并立即注入当前请求后续工具调用。
- 仅系统专属工具名记录在插件类属性 `WINDOWS_TOOL_NAMES`、`LINUX_TOOL_NAMES`、`MAC_TOOL_NAMES` 中；当前只有 OCR 工具属于 Windows 专属。
- 信息获取类接口会通过函数 `return` 把 NapCat API 响应返回给 LLM，不直接向当前聊天发送消息。
- 当前 NapCat 版本中 `/translate_en2zh` 存在问题，老版本 NapCat 中 `/get_mini_app_ark` 不兼容；`napcat_translate_en2zh` 和 `napcat_get_mini_app_ark` 已临时禁用，不会进入工具搜索、动态发现或请求注入。
- Ark 分享类接口（`napcat_send_group_ark_share`、`napcat_send_ark_share`、`napcat_arksharegroup`、`napcat_arksharepeer`）会自动获取卡片 JSON 并发送，不需要二次调用消息发送工具。可通过 `send_group_id` 指定发送群号，或通过 `send_user_id` 指定发送用户；两者都不填时默认发送到当前会话。

## 会话默认参数

部分可以从 `AiocqhttpMessageEvent` 获取的参数已经改为可选，默认值为 `None`。当工具调用传入 `None` 或省略这些参数时，插件会按当前会话自动补齐：

- `group_id`：默认使用当前群聊的群号，即 `event.get_group_id()`。
- `user_id`：默认使用当前消息发送者 ID，即 `event.get_sender_id()`。
- `self_id`：默认使用当前机器人账号 ID，即 `event.get_self_id()`。
- `message_id`：默认优先使用当前消息中的回复目标消息 ID；如果当前消息不是回复，或回复目标解析失败，则回退为当前消息 ID，即 `event.message_obj.message_id`。
- `napcat_upload_image_to_qun_album` 的 `file`：默认优先使用被回复消息中的第一张图片；如果没有回复图片，则使用当前消息中的第一张图片。上传群相册前通常需要先调用 `napcat_get_qun_album_list` 获取准确的 `album_id` 和 `album_name`。

如果在私聊中调用需要群号的群聊工具，且没有显式提供 `group_id`，工具不会请求 NapCat API，而是返回 LLM 可读的 JSON 提示，说明当前消息不是群聊事件并要求提供群号或改用私聊工具。

对于所有同时具有群号和用户号输入语义的工具，插件会在调用 NapCat 前统一归一化参数：未提供 `user_id` 时使用当前消息发送者；群聊中未提供 `group_id` 时使用当前群号；私聊中不会为可选群号强行补值。`target_id` 这类目标 QQ 别名会在存在 `user_id` 语义的工具中自动映射为 `user_id`，不会把 `target_id` 原样传给 NapCat。

## 配置

当前版本使用显式 `@filter.llm_tool` 注册，不再通过配置开关动态增删全量工具。调用执行仍依赖当前消息事件是 aiocqhttp/NapCat 事件。

插件加载时会自动把当前插件目录加入 Python 模块搜索路径，确保 AstrBot 从项目根目录或插件管理器加载 `main.py` 时也能找到内部包 `napcat_fc`。

工具管理数据库位于 AstrBot 插件数据目录，表名为 `napcat_tool`。插件启动时会按当前 `main.py` 中的工具定义同步记录，保留已有 `enabled` 状态并移除已不存在的工具。外部工具发现逻辑可以读取 `enabled`、`parameters_json`、`required_parameters_json` 和 `platforms_json` 字段进行筛选。

搜索发现队列持久化在 `napcat_discovered_tool` 表中，最多保存 20 个工具。重复搜索到同一工具时会去重并刷新到队尾；超过 20 个时按 FIFO 队列出队。搜索工具每次会先取 `search_candidate_limit` 个候选并跳过已发现工具，默认值为 10，避免高相关旧工具长期占住前三名。已发现工具会在后续请求直接注入，不需要再次做数据库搜索。

如需临时关闭动态注入，可在插件配置中设置 `dynamic_injection_enabled: false`。此时请求阶段仍会先卸载本轮请求里已有的 NapCat 工具，但不会再注入新的 NapCat 工具。

如需调整搜索候选池大小，可在插件配置中设置 `search_candidate_limit`，默认 `10`，最小有效值为 `1`。

如需排查动态注入、搜索或数据库同步流程，可在插件配置中设置 `debug: true`。开启后插件会使用 AstrBot 提供的 `logger.debug` 输出关键运行节点日志。调试日志包含 `elapsed_ms` 和 `delta_ms`，用于定位搜索、数据库读取、工具注入等性能瓶颈。

所有 NapCat 相关请求级工具只会在 `AiocqhttpMessageEvent` 事件中处理。非 aiocqhttp/NapCat 消息事件会卸载本轮请求里已有的 NapCat 工具，并跳过搜索工具和具体 NapCat 工具注入。

系统专属工具会在搜索和注入阶段按当前运行系统过滤。例如 Windows 专属 OCR 工具只会在 Windows 环境中进入搜索发现队列并被注入。

搜索综合评分兼容旧版工具数据库仓库对象；如果运行环境暂时只更新了 `main.py`，仍会回退到旧评分逻辑，避免搜索工具因为评分方法缺失而中断。

## 使用方式

LLM 调用具体接口时使用对应工具，例如 `napcat_send_group_msg`：

```json
{
  "message": "hello",
  "auto_escape": false
}
```

在群聊事件中，上面的调用会默认使用当前群号作为 `group_id`。如果需要指定其他群，可以显式传入：

```json
{
  "group_id": "123456",
  "message": "hello",
  "auto_escape": false
}
```

这些工具必须在 aiocqhttp/NapCat 消息事件上下文中使用；非 aiocqhttp 平台事件不会注入 NapCat 工具。

获取信息类工具，例如 `napcat_get_login_info`、`napcat_get_group_info`、`napcat_fetch_custom_face`、`napcat_can_send_image`，返回值会作为工具结果交给 LLM 继续理解和组织回复，而不是由插件直接发送到聊天窗口。

发送 Ark 分享卡片时直接调用 `napcat_send_group_ark_share`、`napcat_send_ark_share`、`napcat_arksharegroup` 或 `napcat_arksharepeer`。这些工具会自动包装 OneBot `json` 消息段并发送到 `send_group_id`、`send_user_id` 或当前会话。

`napcat_send_poke`、`napcat_friend_poke` 和 `napcat_group_poke` 的 `target_id` 仅作为兼容别名使用，实际请求 NapCat 时会映射为 `user_id`，不会把 `target_id` 字段传给 NapCat。在群聊中省略 `group_id` 会默认使用当前群号；在私聊中省略 `group_id` 会按私聊戳一戳处理，群聊专用工具缺群号时会返回可读提示。

## 开发约束

本项目开发约束见 [CONSTRAINTS.md](CONSTRAINTS.md)。每次功能更新必须同步测试、更新日志、版本号和 README 对应说明。
