# 更新日志

## v1.15.8 - 2026-04-25

- 新增 `discovered_tool_limit` 配置项，用于调整已发现工具持久化队列的最大保存数量，默认值为 `20`，最小有效值为 `1`。
- 搜索工具返回的 `max_discovered_tools` 改为展示当前配置生效后的队列上限。

## v1.15.7 - 2026-04-25

- 修复 Ark 分享自动发送兼容性：支持 NapCat 直接返回 Ark JSON 字符串或 Ark JSON 对象的情况，不再只要求返回值包含顶层 `data` 字段。
- 新增回归测试覆盖 `send_group_ark_share` 直接返回 Ark JSON 字符串时的自动发送路径。

## v1.15.6 - 2026-04-25

- `napcat_send_group_ark_share`、`napcat_send_ark_share`、`napcat_arksharegroup` 和 `napcat_arksharepeer` 改为自动发送 Ark 卡片，不再要求 LLM 二次调用消息发送工具。
- 这 4 个 Ark 分享工具新增 `send_group_id` 和 `send_user_id` 参数；两个目标都不填时默认发送到当前会话。
- 移除上一版新增的 JSON 卡片辅助工具注册和普通消息工具中的二次发送提示，工具管理数据库同步数量恢复为 180 个。

## v1.15.5 - 2026-04-25

- 新增 `napcat_send_group_json_msg` 和 `napcat_send_private_json_msg`，用于发送 Ark、小程序和结构化 JSON 卡片。
- 普通消息发送工具的 `message` 参数提示补充：不要拼接 `[app]...[/app][data]...[/data]` 文本发送卡片，应改用 JSON 卡片辅助工具。
- 工具管理数据库同步数量调整为 182 个，并新增回归测试确认 JSON 卡片辅助工具会包装 OneBot `json` 消息段。

## v1.15.4 - 2026-04-25

- 调整 Ark 分享类工具提示，说明发送卡片需要按目标会话选择群聊或私聊消息发送工具。
- 补充私聊卡片发送示例：`napcat_send_private_msg(user_id=QQ号, message=[{"type":"json","data":{"data": data字段}}])`。

## v1.15.3 - 2026-04-25

- 优化 `napcat_send_group_ark_share`、`napcat_send_ark_share`、`napcat_arksharegroup` 和 `napcat_arksharepeer` 的工具提示。
- 明确 Ark 分享接口只返回卡片 JSON，发送卡片需要先取返回 JSON 的 `data` 字段，再通过消息发送工具发送 `json` 消息段。

## v1.15.2 - 2026-04-25

- 临时禁用 `napcat_get_mini_app_ark` 工具注册，避免老版本 NapCat 不兼容 `/get_mini_app_ark` 接口。
- 工具管理数据库同步数量调整为 180 个，并新增回归测试确认该工具不会进入动态发现和注入。

## v1.15.1 - 2026-04-25

- 临时禁用 `napcat_translate_en2zh` 工具注册，避免当前 NapCat 版本中 `/translate_en2zh` 接口异常影响工具调用。
- 移除该接口专用超时配置项 `translate_action_timeout_seconds`，保留通用 NapCat API 调用超时能力。
- 工具管理数据库同步数量调整为 181 个，并新增回归测试确认该工具不会进入动态发现和注入。

## v1.15.0 - 2026-04-25

- `napcat_upload_image_to_qun_album` 的 `file` 参数改为可选，省略时会优先使用被回复消息中的第一张图片。
- 如果被回复消息没有图片，会自动回退为当前消息中的第一张图片，并取图片 URL、文件值或 base64 作为上传来源。
- 上传群相册工具说明补充：通常需要先调用 `napcat_get_qun_album_list` 获取相册 ID 和名称。
- 新增回归测试，覆盖回复图片优先、当前图片回退和缺少图片时返回 LLM 可读提示。

## v1.14.9 - 2026-04-25

- 所有声明 `message_id` 参数的工具在省略消息 ID 时，默认优先使用当前消息中的回复目标消息 ID。
- 如果当前消息不是回复，或回复目标解析失败，则自动回退为当前消息 ID。
- 修复 `napcat_set_group_todo` 等工具省略 `message_id` 时未进入统一默认值填充的问题。

## v1.14.8 - 2026-04-24

- 新增 `search_candidate_limit` 配置项，用于调整搜索工具每次参与综合排序的候选数量，默认值为 `10`。
- 搜索工具返回的 `candidate_limit` 会反映当前配置值，配置缺失或非法时回退默认值，最小有效值为 `1`。

## v1.14.7 - 2026-04-24

- 修复搜索工具在部分环境中加载到旧版 `ToolRegistryRepo` 时抛出 `search_score` 缺失异常的问题。
- 搜索综合评分现在会优先使用公开评分方法，缺失时兼容回退到旧版 `_search_score`，再缺失时使用本地评分逻辑。

## v1.14.6 - 2026-04-24

- 优化 `napcat_search_tools` 的多关键词搜索逻辑：空格分隔的关键词会拆分后并发查询，并按多个词的综合相关度排序。
- 每次搜索先取综合相关度最高的 10 个候选，再排除已发现工具，只将剩余前三名加入发现队列并注入当前请求。
- 搜索返回结果新增 `search_terms`、`candidate_limit` 和 `skipped_discovered_tools`，便于在 debug 日志和工具结果中定位搜索行为。

## v1.14.5 - 2026-04-24

- 将 `group_id`、`user_id` 和 `target_id` 的会话默认值逻辑提升到统一调用层。
- 所有元数据中包含 `user_id` 的工具在未传用户号时会默认使用当前消息发送者。
- 所有元数据中包含 `group_id` 的工具在群聊上下文中未传群号时会默认使用当前群号；私聊中不会为可选群号强行补值。
- 所有同时存在 `target_id` 和 `user_id` 语义的工具会把 `target_id` 作为 `user_id` 兼容别名，不再把 `target_id` 字段传给 NapCat。
- 新增回归测试，覆盖非 poke 工具的可选群号/用户号默认填充，以及通用 `target_id` 归一化。

## v1.14.4 - 2026-04-24

- 将 `napcat_friend_poke` 和 `napcat_group_poke` 按 `napcat_send_poke` 的规则统一处理。
- 三个戳一戳工具都会把 `target_id` 作为 `user_id` 的兼容别名，不再把 `target_id` 字段传给 NapCat。
- 群聊上下文会自动补当前 `group_id`；私聊中可选群号工具不带群号，群聊专用工具缺群号时仍返回可读提示。
- 新增回归测试，覆盖 `friend_poke` 和 `group_poke` 仅传 `target_id` 的场景。

## v1.14.3 - 2026-04-24

- 修复 `napcat_send_poke` 将 `target_id` 原样传给 NapCat 导致戳一戳失败的问题。
- `target_id` 现在作为 `user_id` 的兼容别名处理；当 `user_id` 未提供时会映射为要戳的 QQ 号。
- 群聊中调用 `napcat_send_poke` 且未显式提供 `group_id` 时，会自动使用当前群号；私聊中则不带群号，按私聊戳一戳处理。
- 新增回归测试，覆盖仅传 `target_id` 和私聊默认戳当前发送者两种场景。

## v1.14.2 - 2026-04-24

- 明确信息获取类 NapCat 接口通过函数 `return` 把结果返回给 LLM，不直接发送聊天消息。
- 新增信息接口分类前缀，包括 `get_`、`_get_`、`fetch_`、`can_`、`check_`、`nc_get_` 和 `qidian_get_`。
- 新增回归测试，覆盖信息接口识别和 `get_login_info` 返回 JSON 字符串给 LLM 的行为。

## v1.14.1 - 2026-04-24

- 修复 AstrBot 从项目根目录加载插件时找不到内部包 `napcat_fc` 的问题。
- 插件会在导入内部模块前把当前插件目录加入 `sys.path`，确保 `main.py` 能稳定加载 `napcat_fc` 子包。
- 新增按文件路径加载 `main.py` 的回归测试，覆盖插件根目录不在 `sys.path` 时的导入场景。

## v1.14.0 - 2026-04-24

- 将可从 `AiocqhttpMessageEvent` 获取的 `group_id`、`user_id`、`self_id`、`message_id` 统一改为可选参数，默认值为 `None`。
- 当上述参数传入 `None` 时，调用前会自动从当前会话补齐：当前群号、当前发送者、当前机器人账号或当前消息 ID。
- 在私聊中调用需要群号的群聊工具且未提供 `group_id` 时，返回 LLM 可读的 `missing_context` JSON 提示，而不是直接请求 NapCat API。
- 工具参数说明补充默认行为，便于 LLM 知道省略参数时会使用当前会话信息。

## v1.13.0 - 2026-04-24

- 搜索结果进入发现队列前会按当前运行系统过滤平台专属工具。
- 已发现工具注入请求前会再次校验平台，避免不匹配系统的专属工具被注入。
- 当前 Windows 专属 OCR 工具只会在 Windows 环境中被搜索加入和注入。

## v1.12.0 - 2026-04-24

- 调试日志新增 `elapsed_ms` 和 `delta_ms` 字段，用于分析插件运行阶段和性能瓶颈。
- 所有 NapCat 请求级工具注入改为仅在 `AiocqhttpMessageEvent` 事件中处理。
- 搜索工具提示词扩展为能力概览，列出消息、群管理、好友、文件、媒体、账号、频道和 NapCat 扩展等主要工具类别。

## v1.11.0 - 2026-04-24

- 新增 `debug` 配置项，开启后通过 AstrBot `logger.debug` 输出关键运行节点。
- 调试日志覆盖初始化、数据库同步、请求级卸载、搜索工具注入、已发现工具注入、搜索匹配、发现队列更新和终止关闭等路径。

## v1.10.0 - 2026-04-24

- 新增常驻请求级搜索工具 `napcat_search_tools`，支持按关键词模糊搜索 NapCat 工具能力、工具名、API 名和参数名。
- 搜索结果取最相关前 3 个工具，写入持久化发现队列并立即注入当前 `req.func_tool`。
- 新增 `napcat_discovered_tool` 表，最多保存 20 个已发现工具，重复工具去重并刷新到队尾，超过上限时按 FIFO 出队。
- 请求阶段默认只注入搜索工具和已发现队列中的工具，不再注入全部 `enabled` NapCat 工具。

## v1.9.0 - 2026-04-24

- 改为在 `on_llm_request(priority=-100)` 阶段按工具管理数据库动态注入 NapCat 工具。
- 插件初始化后会将全局注册的 NapCat 工具设为 inactive，避免 182 个工具常驻进入默认工具集。
- 请求阶段会先卸载本轮已有的 NapCat 工具，再按数据库状态注入请求级 active 副本。

## v1.8.0 - 2026-04-24

- 新增工具管理数据库 `napcat_fc_tools.db`，启动时同步当前 182 个 NapCat/OneBot/go-cqhttp 工具。
- 新增 `napcat_tool` 表，记录工具名、API、方法名、能力描述、字段参数、必填字段、平台限制和启用状态。
- 启动同步会保留已有 `enabled` 状态，避免覆盖后续工具发现或管理逻辑写入的启用/禁用配置。

## v1.7.2 - 2026-04-24

- 将平台工具名类属性改为只记录对应系统专属工具，不再记录全量通用工具。
- 当前仅 `napcat_dot_ocr_image` 和 `napcat_ocr_image` 标记为 Windows 专属工具。

## v1.7.0 - 2026-04-24

- 将具体 API 工具从统一 `payload` 参数改为字段级参数签名。
- 扩展工具 docstring，使工具发现时能读取接口用途和字段说明。
- API 生成范围限定为 `docs/onebot-11`、`docs/go-cqhttp`、`docs/napcat-apifox` 三份 NapCat 支持的用户 API 文档。
- 移除通用 `napcat_call_api` 工具，避免工具发现时继续暴露泛化 `payload` 参数。

## v1.6.0 - 2026-04-24

- 将发现到的 NapCat/OneBot API 改为 `@filter.llm_tool` 显式方法注册格式。
- 移除 `__init__` 中动态 `add_llm_tools` 注册路径，便于后续工具发现改造直接读取工具定义。
- 保留通过 `AiocqhttpMessageEvent` 调用当前 NapCat/aiocqhttp `call_action` 的执行方式。

## v1.5.0 - 2026-04-24

- 改为复用 AstrBot `AiocqhttpMessageEvent` 和当前 NapCat/aiocqhttp bot 的 `call_action`。
- 移除插件自建 HTTP 客户端和 HTTP 地址/token 配置。

## v1.4.0 - 2026-04-24

- 将 NapCat / OneBot HTTP API 批量注册为 AstrBot LLM 函数工具。
- 新增插件配置 schema、开发约束文件和 pytest 测试。
- 将 README 和元数据改为中文展示内容。
