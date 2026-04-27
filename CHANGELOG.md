# 更新日志

## v1.15.34 - 2026-04-27

- 新增配置项 `fallback_invalid_context_ids`，默认开启；当 `group_id`、`user_id`、`self_id`、Ark 自动发送目标 `send_group_id`、`send_user_id` 等上下文 ID 参数小于 6 位或不是纯数字时，会回退为当前会话默认值。
- 对非法或过短上下文 ID 回退时，通过 AstrBot logger 输出警告，便于后台定位 LLM 误传参数。
- 新增回归测试，覆盖非法短 ID 自动回退、警告日志，以及关闭该配置后的保留原始参数行为。

## v1.15.33 - 2026-04-27

- 修复 Ark 群分享卡片自动发送时，LLM 传入 `group_id=0` 会被原样发送给 NapCat，导致 Ark 接口返回空数据的问题。
- `group_id`、`user_id`、`self_id`、`message_id` 这类可从当前事件补齐的上下文字段，现在会把 `0` 和空字符串也视为未填写并走默认补齐逻辑。
- 新增回归测试，覆盖上下文字段的 `0/空字符串` 默认补齐，以及 `napcat_send_group_ark_share` 在 `group_id=0` 时仍使用当前群生成并自动发送卡片。

## v1.15.32 - 2026-04-27

- 修复旧版本热更新残留清理不彻底的问题：AstrBot 的 `remove_func` 每次只删除一个同名工具，插件现在会循环删除所有重复残留的 `napcat_*` 全局工具。
- 测试桩 `FakeToolManager.remove_func` 调整为贴近 AstrBot 行为，并新增重复残留清理回归测试。
- 新增 `napcat_search_tools_tool` 在没有当前请求上下文时的回归测试，固定早退错误返回结构。

## v1.15.31 - 2026-04-27

- 动态注入 NapCat 工具时补全 JSON Schema 的 `required` 字段，避免 AstrBot `spec_to_func` 默认不声明必填参数导致 LLM 把所有参数都视为可选。
- `napcat_search_tools` 现在只将 `keyword` 标为必填，`result_limit` 保持可选；具体 NapCat 工具按函数签名生成必填参数列表。
- 修复 `napcat_get_group_honor_info` 的 `type` 参数文档标注为可选但函数签名没有默认值的问题。
- NapCat API 返回业务失败或 aiocqhttp 抛出异常时改为返回 `api_error` JSON 给 LLM，避免 `ERR_GROUP_IS_DELETED` 等接口失败升级为 AstrBot 工具执行警告。
- 新增回归测试，覆盖动态工具 schema 必填参数、搜索工具 schema 必填参数，以及所有文档标注可选的参数都必须有 Python 默认值。

## v1.15.30 - 2026-04-27

- 修复本地安装 zip 为平铺结构时，AstrBot v4.22.x 将 `.gitignore` 等第一个文件误当作解压目录导致安装失败的问题。
- 打包脚本现在会在 zip 第一项显式写入 `astrbot_plugin_napcat_fc/` 顶层目录，并把已跟踪文件放入该目录下，匹配 AstrBot 上传安装器的解压逻辑。
- 测试同步校验 zip 第一项必须是插件目录、私有文件和 `report/` 不进入安装包。

## v1.15.29 - 2026-04-27

- 新增 `scripts/package_plugin.py`，可将 `git ls-files` 中已跟踪的插件文件打包为 AstrBot 本地上传安装使用的 zip。
- 打包产物默认输出到 `dist/astrbot_plugin_napcat_fc-<version>.zip`，zip 根目录直接包含 `metadata.yaml`，符合 AstrBot 本地插件上传安装的元数据读取方式。
- 更新开发约束：每次更改后必须运行打包脚本生成对应版本 zip，README 和测试同步覆盖打包流程。

## v1.15.28 - 2026-04-27

- 修复 `napcat_send_like` 提示词写有默认值但函数签名仍要求 `times` 必填的问题。
- `napcat_send_like` 现在未传 `times` 时默认使用 `1`，避免 LLM 省略参数时触发 AstrBot handler 参数不匹配警告。
- 测试覆盖空参数调用点赞工具和工具元数据中 `times` 不再标记为必填。

## v1.15.27 - 2026-04-27

- `napcat_search_tools` 作为唯一 `@filter.llm_tool` 常驻注册工具保留，确保 LLM 始终有稳定工具发现入口。
- 搜索工具执行逻辑同时支持常驻注册入口和请求级注入副本，并通过当前事件绑定本轮 `ProviderRequest`，保证搜索后仍能立刻注入发现到的具体工具。
- 具体 162 个 NapCat API 工具继续只使用 `# napcat_tool:` 元数据标记，不进入 AstrBot 全局工具注册。

## v1.15.26 - 2026-04-27

- 移除 `tool_registration_mode` 配置项，不再提供旧式全量注册回退开关。
- 具体 NapCat 工具固定为按需构造和请求级注入；插件初始化仅清理旧版本热更新可能遗留在全局工具管理器里的同名工具。
- README、配置 schema、工具发现报告和测试同步删除注册模式切换说明。

## v1.15.25 - 2026-04-27

- 移除具体 NapCat 工具上的 `@filter.llm_tool` 装饰器，改用 `# napcat_tool:` 元数据标记，确保模块 import 阶段不会触发 160+ 个工具的 AstrBot 全局注册。
- 工具注册数据生成逻辑改为优先读取元数据标记，并保留旧装饰器解析作为兼容回退。
- `tool_registration_mode` 的旧模式改名为 `static`，表示初始化阶段手动全量注册；`decorator` 和 `legacy` 仅作为旧配置别名。

## v1.15.24 - 2026-04-27

- 新增 `tool_registration_mode` 配置项，默认 `lazy`，避免一次性将 160+ 个 NapCat 工具常驻注册到 AstrBot 全局工具管理器。
- 具体 NapCat 工具不再使用 `@filter.llm_tool` 装饰器，改用 `# napcat_tool:` 元数据标记生成工具数据库记录，从源头避免 import 阶段触发 AstrBot 全局工具注册。
- `lazy` 模式下，搜索工具发现具体工具后，按工具数据库记录和插件绑定方法动态构造当前请求级工具。
- 保留 `static` 兼容模式，可在初始化阶段手动恢复旧式全量注册、隐藏和请求级复制流程；`decorator` 和 `legacy` 仅作为旧配置别名兼容。
- README、配置 schema、工具发现报告、元数据版本和测试同步覆盖新旧注册模式切换。

## v1.15.23 - 2026-04-26

- 工具发现数据库初始化时会检测旧版 `napcat_tool` 表结构；如果缺少当前模型字段，会输出 warning 并列出缺失字段，然后自动执行兼容迁移。
- 已完成迁移或新建数据库不会重复告警，避免正常启动日志噪音。
- README、工具发现报告和测试同步覆盖旧数据告警行为。

## v1.15.22 - 2026-04-26

- 修复 AstrBot 热更新场景下只刷新 `main.py`、未刷新 `napcat_fc` 内部模块时，工具发现数据库迁移仍使用旧模型的问题。
- `main.py` 导入内部包前会重新加载插件目录内已存在的 `napcat_fc.db.tables`、`napcat_fc.db.database`、`napcat_fc.db.repo`、`napcat_fc.db` 和 `napcat_fc.tool_registry`，确保迁移模型、搜索 repo 和元数据生成逻辑版本一致。
- README、工具发现报告和测试同步记录热更新模块缓存边界。

## v1.15.21 - 2026-04-26

- 修复 `napcat_search_tools` 在运行环境仍返回旧版工具记录对象时直接访问 `namespace` 等新字段导致搜索工具报错的问题。
- 搜索结果序列化改为兼容缺少元数据字段的记录对象，缺省使用空命名空间、低风险和无需确认，避免工具发现流程被旧模型对象中断。
- 工具发现报告和测试同步补充该兼容边界。

## v1.15.20 - 2026-04-26

- 新增 `report/tool_discovery_report.md`，集中记录工具发现、搜索、动态注入、持久化发现队列和数据库迁移逻辑。
- 更新 `CONSTRAINTS.md`，新增约束：一旦改动工具发现相关模块或行为，必须同步更新工具发现报告。
- README 和测试同步覆盖工具发现报告维护要求，避免后续修改工具发现逻辑时遗漏设计记录。

## v1.15.19 - 2026-04-26

- 参考 `docs/资料/工具发现方案调研.md` 优化工具发现元数据，工具管理数据库新增命名空间、搜索别名、风险等级、确认需求和默认可发现字段。
- 搜索评分纳入工具命名空间和别名，提升群成员、群文件、媒体、系统、Ark 等能力的召回质量；风险等级仅作为元数据记录，暂不参与搜索降权。
- 数据库初始化会为旧版 `napcat_tool` 表自动补齐新增字段，避免已有插件数据目录升级后因表结构缺失导致启动失败。
- README、元数据版本和测试同步更新，新增搜索元数据持久化、别名检索和命名空间检索回归覆盖。

## v1.15.18 - 2026-04-25

- 新增配置项 `unlimited_request_tool_injection`，开启后同一轮 LLM 请求中通过 `napcat_search_tools` 注入的工具不受持久化发现队列上限限制。
- 搜索工具会在开启该配置时跳过本轮请求已注入的 NapCat 工具，允许多次搜索继续补充新工具；数据库持久化仍按 `discovered_tool_limit` FIFO 裁剪。
- README、配置 schema 和测试同步覆盖该行为，验证本轮请求可注入超过持久化上限的工具，而下一轮仍只按原上限保留。

## v1.15.17 - 2026-04-25

- 按 `待删除.md` 处理“建议优先删除”工具，移除内部调试、未知接口、底层 Packet、测试下载、底层 rkey、UIN 范围和事件过滤器重载等 7 个工具注册。
- 合并“可与其他工具合并”中的重复工具，保留通用发送、戳一戳、合并转发、已读、Ark 分享入口，并新增 `napcat_forward_single_msg` 承接单条消息转发。
- `TODO.md` 更新为当前保留注册的 162 个工具清单，`待删除.md` 标记已处理项，测试同步覆盖工具数量和合并后的入口。

## v1.15.16 - 2026-04-25

- 新增 `待删除.md`，按内部调试、高风险、重复包装、低频弱价值和需限制发现等类别记录候选删除/隐藏工具。
- README 补充候选删除清单说明，便于后续根据清单决定删除、禁用或从动态工具发现中隐藏。
- 新增回归测试，确认 `待删除.md` 存在并覆盖关键候选工具与处理类别。

## v1.15.15 - 2026-04-25

- 按 `TODO.md` 完成 131-180 号工具提示词优化，覆盖点赞、通用/私聊发送、在线文件、好友/群申请、群管理、频道角色、在线状态、头像资料、重启和上传类工具。
- `TODO.md` 现已将 180 个工具全部标记为完成，作为工具提示词优化清单和后续复核入口。
- 扩展提示词回归测试，验证最后一批工具包含资料卡点赞、群私聊发送、在线文件、群精华、好友申请、群管理、禁言踢人、在线状态、头像资料和文件上传等搜索关键词。

## v1.15.14 - 2026-04-25

- 按 `TODO.md` 继续优化 081-130 号工具提示词，覆盖频道资料、图片/语音信息、消息查询、在线文件、已读标记、群文件操作和发送类工具。
- `TODO.md` 已将前 130 个工具标记为完成，并保留 131-180 作为最后一批优化队列。
- 扩展提示词回归测试，验证第三批工具包含频道成员、图片路径、在线客户端、最近联系人、运行状态、OCR、在线文件、群公告和频道消息等搜索关键词。

## v1.15.13 - 2026-04-25

- 按 `TODO.md` 继续优化 031-080 号工具提示词，覆盖文件流下载、表情、消息转发、凭证、好友/群/频道信息查询等工具。
- `TODO.md` 已将前 80 个工具标记为完成，并保留 081-180 作为后续优化队列。
- 移除 `.gitignore` 中的 `TODO.md` 忽略规则，确保工具提示词优化清单可被版本管理。
- 扩展提示词回归测试，验证第二批工具包含图片流、表情、转发、AI 声线、鉴权、群相册、群文件和频道等搜索关键词。

## v1.15.12 - 2026-04-25

- 新增 `TODO.md`，记录 180 个 NapCat 工具的提示词优化进度。
- 按 TODO 清单优化前 30 个工具能力提示，补充动作、对象、适用场景和常见搜索词，提升 `napcat_search_tools` 命中效果。
- 新增 pipeline artifact，记录本轮提示词优化的 spec、plan 和 architecture。

## v1.15.11 - 2026-04-25

- 清理所有 NapCat 工具能力提示，移除 `能力:` 前缀、`(API: ...)` 后缀和冗余表格格式，使能力描述更适合作为 LLM 工具发现提示。
- 修正工具注册元数据的能力读取逻辑，继续兼容旧格式但输出保持短能力句。
- 新增回归测试，防止能力描述再次包含 `能力:`、`API:` 或 Markdown 表格。

## v1.15.10 - 2026-04-25

- `napcat_search_tools` 新增可选参数 `result_limit`，用于控制本次最多加入发现队列并注入当前请求的工具数量，默认值仍为 `3`。
- 搜索工具提示词补充：可以多次用同一个关键词搜索，已发现工具会被跳过，从而获取更广泛的候选工具。

## v1.15.9 - 2026-04-25

- 优化 `napcat_search_tools` 提示词：当当前可用工具列表中没有明确可以完成用户目标的 NapCat 工具时，要求先调用搜索工具进行工具发现。

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
