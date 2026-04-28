# NapCat 函数工具

这是一个 AstrBot 插件，用于把本地文档中的 NapCat / OneBot / go-cqhttp 用户 API 提供为可供 LLM 调用的函数工具。只有 `napcat_search_tools` 搜索入口使用 `@filter.llm_tool` 常驻注册；具体 NapCat 接口工具不使用该装饰器，默认不会把 160+ 个工具常驻注册到 AstrBot 全局工具管理器，而是在工具发现后按需注入到当前请求。

## 功能

- 基于 `docs/napcat-apifox`、`docs/onebot-11` 和 `docs/go-cqhttp` 生成工具定义。
- 每个发现到的用户 API 都有一个 `# napcat_tool: napcat_<接口名>` 元数据标记和对应异步方法，供工具数据库生成、搜索和按需构造使用。
- 具体接口工具使用字段级参数，例如 `group_id`、`user_id`、`message`，不要求 LLM 传入统一 `payload`。
- 工具能力提示保持为面向 LLM 的中文说明，不在能力描述中重复 `能力:`、API 路径或 Markdown 表格；提示应覆盖动作、对象和常见搜索词，便于 `napcat_search_tools` 发现对应工具。
- 工具提示词优化进度记录在 `TODO.md`；当前保留注册的 160 个工具已全部完成提示词优化。
- 低价值、危险、重复或更适合隐藏的工具候选记录在 `待删除.md`，用于后续决定删除、禁用或从工具发现中隐藏。
- 复用 AstrBot 默认接入 NapCat 的 `AiocqhttpMessageEvent` 和当前事件的 `event.bot.api.call_action`，不自建 HTTP 客户端。
- 初始化时创建工具管理数据库 `napcat_fc_tools.db`，记录工具名、API、能力、参数、平台限制、命名空间、搜索别名、风险等级和启用状态，供动态工具发现使用。
- 具体 NapCat 工具不作为全局工具常驻注册或暴露，而是在 `on_llm_request(priority=-150)` 阶段按搜索发现结果和数据库状态构造请求级工具并注入到当前请求；该优先级会晚于旧上传残留实例执行，确保当前版本同名工具覆盖旧 handler。聊天记录查询统一暴露为 `napcat_get_msg_history`，合并转发和单条转发统一暴露为 `napcat_send_forward_msg`，底层群/私聊/单条接口只作为内部兼容方法保留。
- `napcat_search_tools` 搜索工具会一直注入到 aiocqhttp/NapCat 请求中。当当前可用工具列表里没有明确可以完成用户目标的 NapCat 工具时，应先调用它进行工具发现。它支持空格分词并发搜索，并会结合工具名、API、能力说明、命名空间、搜索别名和参数名综合排序；然后排除已发现工具，将剩余最相关的一批工具加入持久化发现队列，并立即注入当前请求后续工具调用。可通过 `result_limit` 控制本次加入工具列表的数量，默认 `3`；如果需要更广泛的工具集合，可以多次用同一个关键词搜索，已发现工具会被跳过，后续搜索会继续补充新候选。
- 在 aiocqhttp/NapCat 请求中，当前用户文本和 `napcat_search_tools` 搜索关键词里的 `qq`/`QQ` 会归一为 `napcat`，减少模型把 NapCat 平台能力误当作普通 QQ 文本操作的情况。
- 仅系统专属工具名记录在插件类属性 `WINDOWS_TOOL_NAMES`、`LINUX_TOOL_NAMES`、`MAC_TOOL_NAMES` 中；当前只有 OCR 工具属于 Windows 专属。
- 信息获取类接口会通过函数 `return` 把 NapCat API 响应返回给 LLM，不直接向当前聊天发送消息。
- 动态注入的工具会按函数签名补全 JSON Schema 的必填参数；文档标注为可选的参数必须在函数签名中提供默认值，避免 LLM 误以为必填参数可以省略。
- NapCat API 业务失败会返回 `api_error` JSON 给 LLM，包含接口名、错误类型、错误消息和实际 payload，便于模型调整参数后重试。
- NapCat 动作接口如果返回 `None/null`，工具会包装为 `status: ok` JSON，说明接口已调用但没有业务数据，避免 LLM 只看到 `null` 后无法判断调用结果。
- 当前 NapCat 版本中 `/translate_en2zh` 存在问题，老版本 NapCat 中 `/get_mini_app_ark` 不兼容；`napcat_translate_en2zh` 和 `napcat_get_mini_app_ark` 已临时禁用，不会进入工具搜索、动态发现或请求注入。
- Ark 分享类接口（`napcat_send_group_ark_share`、`napcat_send_ark_share`、`napcat_arksharegroup`、`napcat_arksharepeer`）会自动获取卡片 JSON 并发送，不需要二次调用消息发送工具。可通过 `send_group_id` 指定发送群号，或通过 `send_user_id` 指定发送用户；两者都不填时默认发送到当前会话。自动发送兼容 NapCat 返回顶层 `data` 字段、直接 Ark JSON 字符串或直接 Ark JSON 对象。
- 合并转发聊天记录时，优先调用 `napcat_get_msg_history` 获取群聊或私聊历史消息，再把返回的 `message_id` 或 `message_ids` 传给 `napcat_send_forward_msg`；该工具会自动组成 `messages=[{"type":"node","data":{"id": message_id}}]` 并按当前会话或显式目标发送。

## 会话默认参数

部分可以从 `AiocqhttpMessageEvent` 获取的参数已经改为可选，默认值为 `None`。当工具调用传入 `None`、`0`、空字符串或省略这些参数时，插件会按当前会话自动补齐：

- `group_id`：默认使用当前群聊的群号，即 `event.get_group_id()`。
- `user_id`：默认使用当前消息发送者 ID，即 `event.get_sender_id()`。
- `self_id`：默认使用当前机器人账号 ID，即 `event.get_self_id()`。
- `message_id`：默认优先使用当前消息中的回复目标消息 ID；如果当前消息不是回复，或回复目标解析失败，则回退为当前消息 ID，即 `event.message_obj.message_id`。
- `napcat_upload_image_to_qun_album` 的 `file`：默认优先使用被回复消息中的第一张图片；如果没有回复图片，则使用当前消息中的第一张图片。上传群相册前通常需要先调用 `napcat_get_qun_album_list` 获取准确的 `album_id` 和 `album_name`。
- `napcat_get_group_album_media_list` 的 `attach_info`：首次查询默认使用空字符串；翻页时传入上次返回的 `next_attach_info`。

如果在私聊中调用需要群号的群聊工具，且没有显式提供 `group_id`，工具不会请求 NapCat API，而是返回 LLM 可读的 JSON 提示，说明当前消息不是群聊事件并要求提供群号或改用私聊工具。

对于所有同时具有群号和用户号输入语义的工具，插件会在调用 NapCat 前统一归一化参数：未提供 `user_id` 或传入 `0` 时使用当前消息发送者；群聊中未提供 `group_id` 或传入 `0` 时使用当前群号；私聊中不会为可选群号强行补值。`target_id` 这类目标 QQ 别名会在存在 `user_id` 语义的工具中自动映射为 `user_id`，不会把 `target_id` 原样传给 NapCat。

开启 `fallback_invalid_context_ids` 时，如果群聊工具收到的 `group_id` 恰好等于当前消息发送者 `user_id`，插件会判定为 LLM 把用户号误填为群号，自动回退为当前群号并输出警告。`napcat_get_msg_history` 在未传 `message_seq` 时会自动使用 `0` 获取最近消息，避免旧版 NapCat 把缺省值处理为 `undefined`。

## 配置

具体 NapCat 工具不会经过 `@filter.llm_tool` 注册，也不会一次性注册到 AstrBot 全局工具管理器。插件只让 `napcat_search_tools` 常驻注册，具体工具会在搜索发现或持久化队列命中时，基于工具数据库记录和插件绑定方法临时构造为当前请求级工具，避免 160+ 个工具导致 AstrBot 内部 hook 或工具管理压力。

插件初始化时会清理全局工具管理器里残留的同名 NapCat 工具，用于兼容从旧版本热更新到当前版本的场景；如果旧版本留下多个同名工具，会循环删除到没有残留。之后所有具体接口工具都只走按需注入。

插件加载时会自动把当前插件目录加入 Python 模块搜索路径，确保 AstrBot 从项目根目录或插件管理器加载 `main.py` 时也能找到内部包 `napcat_fc`。

插件热更新时会主动重新加载插件目录内的 `napcat_fc` 内部模块，避免 AstrBot 只刷新 `main.py` 而保留旧版数据库模型或工具注册逻辑，导致工具发现数据库迁移没有使用最新字段。

如果启动时检测到工具发现数据库仍是旧版 `napcat_tool` 表结构，插件会输出警告并列出缺失字段，然后自动执行兼容迁移；已完成迁移的数据库不会重复告警。

工具管理数据库位于 AstrBot 插件数据目录，表名为 `napcat_tool`。插件启动时会按当前 `main.py` 中的工具定义同步记录，保留已有 `enabled` 状态并移除已不存在的工具。外部工具发现逻辑可以读取 `enabled`、`namespace`、`aliases_json`、`risk_level`、`requires_confirmation`、`default_discoverable`、`parameters_json`、`required_parameters_json` 和 `platforms_json` 字段进行筛选。

搜索发现队列持久化在 `napcat_discovered_tool` 表中，默认最多保存 20 个工具。重复搜索到同一工具时会去重并刷新到队尾；超过上限时按 FIFO 队列出队。搜索工具每次会先取 `search_candidate_limit` 个候选并跳过已发现工具，默认值为 10，避免高相关旧工具长期占住前三名。已发现工具会在后续请求直接注入，不需要再次做数据库搜索。

如需临时关闭动态注入，可在插件配置中设置 `dynamic_injection_enabled: false`。此时请求阶段仍会先卸载本轮请求里已有的 NapCat 工具，但不会再注入新的 NapCat 工具。

如需调整搜索候选池大小，可在插件配置中设置 `search_candidate_limit`，默认 `10`，最小有效值为 `1`。

如需调整已发现工具持久化队列上限，可在插件配置中设置 `discovered_tool_limit`，默认 `20`，最小有效值为 `1`。

如需让同一轮 LLM 请求中通过 `napcat_search_tools` 添加的工具不受持久化队列上限限制，可设置 `unlimited_request_tool_injection: true`。开启后，本轮请求内多次搜索会继续注入新工具；请求结束后的下一轮仍按 `discovered_tool_limit` 只保留持久化队列上限内的工具。

如需控制上下文 ID 容错，可设置 `fallback_invalid_context_ids`，默认 `true`。开启后，`group_id`、`user_id`、`self_id`、Ark 自动发送目标 `send_group_id`、`send_user_id` 等可从当前事件补齐或回退的 ID 参数如果小于 6 位或不是纯数字，插件会回退为当前会话默认值，并在后台通过 AstrBot logger 输出警告；关闭后只对 `None`、`0` 和空字符串走默认补齐。

如需排查动态注入、搜索或数据库同步流程，可在插件配置中设置 `debug: true`。开启后插件会使用 AstrBot 提供的 `logger.debug` 输出关键运行节点日志。调试日志包含 `elapsed_ms` 和 `delta_ms`，用于定位搜索、数据库读取、工具注入等性能瓶颈。

所有 NapCat 相关请求级工具只会在 `AiocqhttpMessageEvent` 事件中处理。非 aiocqhttp/NapCat 消息事件会卸载本轮请求里已有的 NapCat 工具，并跳过搜索工具和具体 NapCat 工具注入。

系统专属工具会在搜索和注入阶段按当前运行系统过滤。例如 Windows 专属 OCR 工具只会在 Windows 环境中进入搜索发现队列并被注入。

搜索综合评分兼容旧版工具数据库仓库对象；如果运行环境暂时只更新了 `main.py`，仍会回退到旧评分逻辑，避免搜索工具因为评分方法缺失而中断。

搜索结果序列化同样兼容旧版工具记录对象；如果运行环境中的记录暂时缺少 `namespace`、`risk_level` 或 `requires_confirmation` 字段，会使用安全默认值返回，避免工具发现流程中断。

## 本地打包

运行以下命令可生成 AstrBot 本地插件安装使用的 zip 压缩包：

```powershell
python scripts/package_plugin.py
```

脚本只打包 `git ls-files` 返回的已跟踪文件，输出到 `dist/astrbot_plugin_napcat_fc-<version>.zip`。压缩包第一项是 `astrbot_plugin_napcat_fc/` 顶层目录，目录内包含 `metadata.yaml`，符合 AstrBot v4.22.x 上传安装时先解压顶层目录、再移动目录内容的逻辑。

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

本项目开发约束见 [CONSTRAINTS.md](CONSTRAINTS.md)。每次功能更新必须同步测试、更新日志、版本号和 README 对应说明，并运行 `python scripts/package_plugin.py` 生成对应版本的本地安装 zip。工具发现逻辑的设计与维护记录见 [report/tool_discovery_report.md](report/tool_discovery_report.md)；凡是改动工具发现相关模块或行为，必须同步更新该报告。
