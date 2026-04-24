from __future__ import annotations

import json

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


@register(
    "astrbot_plugin_napcat_fc",
    "Soulter / AstrBot contributors",
    "将 NapCat / OneBot / go-cqhttp API 注册为 AstrBot 函数工具。",
    "1.7.0",
)
class NapCatFunctionToolsPlugin(Star):
    WINDOWS_TOOL_NAMES = (
        'napcat_arksharegroup',
        'napcat_arksharepeer',
        'napcat_bot_exit',
        'napcat_can_send_image',
        'napcat_can_send_record',
        'napcat_cancel_group_todo',
        'napcat_cancel_online_file',
        'napcat_check_url_safely',
        'napcat_clean_cache',
        'napcat_clean_stream_temp_file',
        'napcat_click_inline_keyboard_button',
        'napcat_complete_group_todo',
        'napcat_create_collection',
        'napcat_create_flash_task',
        'napcat_create_group_file_folder',
        'napcat_create_guild_role',
        'napcat_del_group_album_media',
        'napcat_del_group_notice',
        'napcat_delete_essence_msg',
        'napcat_delete_friend',
        'napcat_delete_group_file',
        'napcat_delete_group_folder',
        'napcat_delete_guild_role',
        'napcat_delete_msg',
        'napcat_delete_unidirectional_friend',
        'napcat_do_group_album_comment',
        'napcat_dot_get_word_slices',
        'napcat_dot_handle_quick_operation',
        'napcat_dot_ocr_image',
        'napcat_download_file',
        'napcat_download_file_image_stream',
        'napcat_download_file_record_stream',
        'napcat_download_file_stream',
        'napcat_download_fileset',
        'napcat_fetch_custom_face',
        'napcat_fetch_emoji_like',
        'napcat_forward_friend_single_msg',
        'napcat_forward_group_single_msg',
        'napcat_friend_poke',
        'napcat_get_ai_characters',
        'napcat_get_ai_record',
        'napcat_get_clientkey',
        'napcat_get_collection_list',
        'napcat_get_cookies',
        'napcat_get_credentials',
        'napcat_get_csrf_token',
        'napcat_get_doubt_friends_add_request',
        'napcat_get_emoji_likes',
        'napcat_get_essence_msg_list',
        'napcat_get_file',
        'napcat_get_fileset_id',
        'napcat_get_fileset_info',
        'napcat_get_flash_file_list',
        'napcat_get_flash_file_url',
        'napcat_get_forward_msg',
        'napcat_get_friend_list',
        'napcat_get_friend_msg_history',
        'napcat_get_friends_with_category',
        'napcat_get_group_album_media_list',
        'napcat_get_group_at_all_remain',
        'napcat_get_group_detail_info',
        'napcat_get_group_file_system_info',
        'napcat_get_group_file_url',
        'napcat_get_group_files_by_folder',
        'napcat_get_group_honor_info',
        'napcat_get_group_ignore_add_request',
        'napcat_get_group_ignored_notifies',
        'napcat_get_group_info',
        'napcat_get_group_info_ex',
        'napcat_get_group_list',
        'napcat_get_group_member_info',
        'napcat_get_group_member_list',
        'napcat_get_group_msg_history',
        'napcat_get_group_notice',
        'napcat_get_group_root_files',
        'napcat_get_group_shut_list',
        'napcat_get_group_system_msg',
        'napcat_get_guild_channel_list',
        'napcat_get_guild_list',
        'napcat_get_guild_member_list',
        'napcat_get_guild_member_profile',
        'napcat_get_guild_meta_by_guest',
        'napcat_get_guild_msg',
        'napcat_get_guild_roles',
        'napcat_get_guild_service_profile',
        'napcat_get_image',
        'napcat_get_login_info',
        'napcat_get_mini_app_ark',
        'napcat_get_model_show',
        'napcat_get_msg',
        'napcat_get_online_clients',
        'napcat_get_online_file_msg',
        'napcat_get_private_file_url',
        'napcat_get_profile_like',
        'napcat_get_qun_album_list',
        'napcat_get_recent_contact',
        'napcat_get_record',
        'napcat_get_rkey',
        'napcat_get_rkey_server',
        'napcat_get_robot_uin_range',
        'napcat_get_share_link',
        'napcat_get_status',
        'napcat_get_stranger_info',
        'napcat_get_topic_channel_feeds',
        'napcat_get_unidirectional_friend_list',
        'napcat_get_version_info',
        'napcat_group_poke',
        'napcat_mark_all_as_read',
        'napcat_mark_group_msg_as_read',
        'napcat_mark_msg_as_read',
        'napcat_mark_private_msg_as_read',
        'napcat_move_group_file',
        'napcat_nc_get_packet_status',
        'napcat_nc_get_rkey',
        'napcat_nc_get_user_status',
        'napcat_ocr_image',
        'napcat_qidian_get_account_info',
        'napcat_receive_online_file',
        'napcat_refuse_online_file',
        'napcat_reload_event_filter',
        'napcat_rename_group_file',
        'napcat_send_ark_share',
        'napcat_send_flash_msg',
        'napcat_send_forward_msg',
        'napcat_send_group_ai_record',
        'napcat_send_group_ark_share',
        'napcat_send_group_forward_msg',
        'napcat_send_group_msg',
        'napcat_send_group_notice',
        'napcat_send_group_sign',
        'napcat_send_guild_channel_msg',
        'napcat_send_like',
        'napcat_send_msg',
        'napcat_send_online_file',
        'napcat_send_online_folder',
        'napcat_send_packet',
        'napcat_send_poke',
        'napcat_send_private_forward_msg',
        'napcat_send_private_msg',
        'napcat_set_diy_online_status',
        'napcat_set_doubt_friends_add_request',
        'napcat_set_essence_msg',
        'napcat_set_friend_add_request',
        'napcat_set_friend_remark',
        'napcat_set_group_add_option',
        'napcat_set_group_add_request',
        'napcat_set_group_admin',
        'napcat_set_group_album_media_like',
        'napcat_set_group_anonymous',
        'napcat_set_group_anonymous_ban',
        'napcat_set_group_ban',
        'napcat_set_group_card',
        'napcat_set_group_kick',
        'napcat_set_group_kick_members',
        'napcat_set_group_leave',
        'napcat_set_group_name',
        'napcat_set_group_portrait',
        'napcat_set_group_remark',
        'napcat_set_group_robot_add_option',
        'napcat_set_group_search',
        'napcat_set_group_sign',
        'napcat_set_group_special_title',
        'napcat_set_group_todo',
        'napcat_set_group_whole_ban',
        'napcat_set_guild_member_role',
        'napcat_set_input_status',
        'napcat_set_model_show',
        'napcat_set_msg_emoji_like',
        'napcat_set_online_status',
        'napcat_set_qq_avatar',
        'napcat_set_qq_profile',
        'napcat_set_restart',
        'napcat_set_self_longnick',
        'napcat_test_download_stream',
        'napcat_trans_group_file',
        'napcat_translate_en2zh',
        'napcat_unknown',
        'napcat_update_guild_role',
        'napcat_upload_file_stream',
        'napcat_upload_group_file',
        'napcat_upload_image_to_qun_album',
        'napcat_upload_private_file',
    )
    LINUX_TOOL_NAMES = WINDOWS_TOOL_NAMES
    MAC_TOOL_NAMES = WINDOWS_TOOL_NAMES

    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = dict(config or {})
        self.tool_count = len(self.WINDOWS_TOOL_NAMES)

    async def initialize(self):
        logger.info(f"NapCat 函数工具已初始化：{self.tool_count} 个。")

    async def terminate(self):
        return None

    async def _call_napcat_api(
        self,
        event: AstrMessageEvent,
        endpoint: str,
        payload: dict = None,
    ) -> str:
        if not isinstance(event, AiocqhttpMessageEvent):
            raise ValueError("NapCat tools require an aiocqhttp/NapCat message event.")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object.")
        action = endpoint.strip().lstrip("/")
        if not action:
            raise ValueError("endpoint must not be empty.")
        bot = event.bot
        api = getattr(bot, "api", None)
        call_action = getattr(api, "call_action", None) or getattr(bot, "call_action", None)
        if not call_action:
            raise RuntimeError("Current aiocqhttp bot does not support call_action.")
        result = await call_action(action, **payload)
        return json.dumps(result, ensure_ascii=False, default=str)

    @filter.llm_tool(name='napcat_arksharegroup')
    async def napcat_arksharegroup_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群分享的 Ark 内容 (API: /ArkShareGroup).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'ArkShareGroup', payload)

    @filter.llm_tool(name='napcat_arksharepeer')
    async def napcat_arksharepeer_tool(
        self,
        event: AstrMessageEvent,
        phone_number: str,
        group_id: int = None,
        phoneNumber: str = None,
        user_id: int = None
    ):
        """能力: 获取用户推荐的 Ark 内容 (API: /ArkSharePeer).

Args:
    phone_number(str): 必填，手机号。
    group_id(int): 可选，和user_id二选一。
    phoneNumber(str): 可选，对方手机号。
    user_id(int): 可选，和user_id二选一。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if phone_number is not None:
            payload['phone_number'] = phone_number
        if group_id is not None:
            payload['group_id'] = group_id
        if phoneNumber is not None:
            payload['phoneNumber'] = phoneNumber
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'ArkSharePeer', payload)

    @filter.llm_tool(name='napcat_bot_exit')
    async def napcat_bot_exit_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 账号退出 (API: /bot_exit).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'bot_exit', payload)

    @filter.llm_tool(name='napcat_can_send_image')
    async def napcat_can_send_image_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 检查是否可以发送图片 (API: /can_send_image).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'can_send_image', payload)

    @filter.llm_tool(name='napcat_can_send_record')
    async def napcat_can_send_record_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 检查是否可以发送语音 (API: /can_send_record).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'can_send_record', payload)

    @filter.llm_tool(name='napcat_cancel_group_todo')
    async def napcat_cancel_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message_id: int = None,
        message_seq: int = None
    ):
        """能力: 将指定消息对应的群待办取消 (API: /cancel_group_todo).

Args:
    group_id(int): 必填，群号。
    message_id(int): 可选，消息ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'cancel_group_todo', payload)

    @filter.llm_tool(name='napcat_cancel_online_file')
    async def napcat_cancel_online_file_tool(
        self,
        event: AstrMessageEvent,
        msg_id: str,
        user_id: int
    ):
        """能力: 取消在线文件 (API: /cancel_online_file).

Args:
    msg_id(str): 必填，消息 ID。
    user_id(int): 必填，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if msg_id is not None:
            payload['msg_id'] = msg_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'cancel_online_file', payload)

    @filter.llm_tool(name='napcat_check_url_safely')
    async def napcat_check_url_safely_tool(
        self,
        event: AstrMessageEvent,
        url: str
    ):
        """能力: 检查指定URL的安全等级 (API: /check_url_safely).

Args:
    url(str): 必填，要检查的 URL。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if url is not None:
            payload['url'] = url
        return await self._call_napcat_api(event, 'check_url_safely', payload)

    @filter.llm_tool(name='napcat_clean_cache')
    async def napcat_clean_cache_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 清理缓存 (API: /clean_cache).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'clean_cache', payload)

    @filter.llm_tool(name='napcat_clean_stream_temp_file')
    async def napcat_clean_stream_temp_file_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 清理流临时文件 (API: /clean_stream_temp_file).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'clean_stream_temp_file', payload)

    @filter.llm_tool(name='napcat_click_inline_keyboard_button')
    async def napcat_click_inline_keyboard_button_tool(
        self,
        event: AstrMessageEvent,
        bot_appid: str,
        button_id: str,
        callback_data: str,
        group_id: int,
        msg_seq: int
    ):
        """能力: 点击内联键盘按钮 (API: /click_inline_keyboard_button).

Args:
    bot_appid(str): 必填，机器人AppID。
    button_id(str): 必填，按钮ID。
    callback_data(str): 必填，回调数据。
    group_id(int): 必填，群号。
    msg_seq(int): 必填，消息序列号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if bot_appid is not None:
            payload['bot_appid'] = bot_appid
        if button_id is not None:
            payload['button_id'] = button_id
        if callback_data is not None:
            payload['callback_data'] = callback_data
        if group_id is not None:
            payload['group_id'] = group_id
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq
        return await self._call_napcat_api(event, 'click_inline_keyboard_button', payload)

    @filter.llm_tool(name='napcat_complete_group_todo')
    async def napcat_complete_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message_id: int = None,
        message_seq: int = None
    ):
        """能力: 将指定消息对应的群待办标记为已完成 (API: /complete_group_todo).

Args:
    group_id(int): 必填，群号。
    message_id(int): 可选，消息ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'complete_group_todo', payload)

    @filter.llm_tool(name='napcat_create_collection')
    async def napcat_create_collection_tool(
        self,
        event: AstrMessageEvent,
        brief: str,
        rawData: str
    ):
        """能力: 创建收藏 (API: /create_collection).

Args:
    brief(str): 必填，简要描述。
    rawData(str): 必填，原始数据。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if brief is not None:
            payload['brief'] = brief
        if rawData is not None:
            payload['rawData'] = rawData
        return await self._call_napcat_api(event, 'create_collection', payload)

    @filter.llm_tool(name='napcat_create_flash_task')
    async def napcat_create_flash_task_tool(
        self,
        event: AstrMessageEvent,
        files: str,
        name: str = None,
        thumb_path: str = None
    ):
        """能力: 创建闪传任务 (API: /create_flash_task).

Args:
    files(str): 必填，文件列表或单个文件路径。
    name(str): 可选，任务名称。
    thumb_path(str): 可选，缩略图路径。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if files is not None:
            payload['files'] = files
        if name is not None:
            payload['name'] = name
        if thumb_path is not None:
            payload['thumb_path'] = thumb_path
        return await self._call_napcat_api(event, 'create_flash_task', payload)

    @filter.llm_tool(name='napcat_create_group_file_folder')
    async def napcat_create_group_file_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_name: str,
        group_id: int,
        name: str = None,
        parent_id: str = None
    ):
        """能力: 创建群文件文件夹 (API: /create_group_file_folder).

Args:
    folder_name(str): 必填，文件夹名称。
    group_id(int): 必填，群号。
    name(str): 可选，文件夹名称。
    parent_id(str): 可选，仅能为 `/`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_name is not None:
            payload['folder_name'] = folder_name
        if group_id is not None:
            payload['group_id'] = group_id
        if name is not None:
            payload['name'] = name
        if parent_id is not None:
            payload['parent_id'] = parent_id
        return await self._call_napcat_api(event, 'create_group_file_folder', payload)

    @filter.llm_tool(name='napcat_create_guild_role')
    async def napcat_create_guild_role_tool(
        self,
        event: AstrMessageEvent,
        color: str,
        guild_id: str,
        name: str,
        independent: bool = None,
        initial_users: list = None
    ):
        """能力: 创建频道角色 (API: /create_guild_role).

Args:
    color(str): 必填，颜色。
    guild_id(str): 必填，频道ID。
    name(str): 必填，角色名。
    independent(bool): 可选，未知 默认值: false。
    initial_users(list): 可选，- 默认值: string。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if color is not None:
            payload['color'] = color
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if name is not None:
            payload['name'] = name
        if independent is not None:
            payload['independent'] = independent
        if initial_users is not None:
            payload['initial_users'] = initial_users
        return await self._call_napcat_api(event, 'create_guild_role', payload)

    @filter.llm_tool(name='napcat_del_group_album_media')
    async def napcat_del_group_album_media_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        group_id: int,
        lloc: str
    ):
        """能力: 删除群相册媒体 (API: /del_group_album_media).

Args:
    album_id(str): 必填，相册ID。
    group_id(int): 必填，群号。
    lloc(str): 必填，媒体ID (lloc)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if group_id is not None:
            payload['group_id'] = group_id
        if lloc is not None:
            payload['lloc'] = lloc
        return await self._call_napcat_api(event, 'del_group_album_media', payload)

    @filter.llm_tool(name='napcat_del_group_notice')
    async def napcat_del_group_notice_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        notice_id: str
    ):
        """能力: _删除群公告 (API: /_del_group_notice).

Args:
    group_id(int): 必填，群号。
    notice_id(str): 必填，公告ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if notice_id is not None:
            payload['notice_id'] = notice_id
        return await self._call_napcat_api(event, '_del_group_notice', payload)

    @filter.llm_tool(name='napcat_delete_essence_msg')
    async def napcat_delete_essence_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int,
        group_id: int = None,
        msg_random: str = None,
        msg_seq: int = None
    ):
        """能力: 删除群精华消息 (API: /delete_essence_msg).

Args:
    message_id(int): 必填，消息ID。
    group_id(int): 可选，群号。
    msg_random(str): 可选，消息随机数。
    msg_seq(int): 可选，消息序号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        if group_id is not None:
            payload['group_id'] = group_id
        if msg_random is not None:
            payload['msg_random'] = msg_random
        if msg_seq is not None:
            payload['msg_seq'] = msg_seq
        return await self._call_napcat_api(event, 'delete_essence_msg', payload)

    @filter.llm_tool(name='napcat_delete_friend')
    async def napcat_delete_friend_tool(
        self,
        event: AstrMessageEvent,
        temp_block: bool,
        temp_both_del: bool,
        user_id: int,
        friend_id: str = None
    ):
        """能力: 从好友列表中删除指定用户 (API: /delete_friend).

Args:
    temp_block(bool): 必填，是否加入黑名单。
    temp_both_del(bool): 必填，是否双向删除。
    user_id(int): 必填，用户 QQ 号。
    friend_id(str): 可选，好友 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if temp_block is not None:
            payload['temp_block'] = temp_block
        if temp_both_del is not None:
            payload['temp_both_del'] = temp_both_del
        if user_id is not None:
            payload['user_id'] = user_id
        if friend_id is not None:
            payload['friend_id'] = friend_id
        return await self._call_napcat_api(event, 'delete_friend', payload)

    @filter.llm_tool(name='napcat_delete_group_file')
    async def napcat_delete_group_file_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int,
        busid: int = None
    ):
        """能力: 在群文件系统中删除指定的文件 (API: /delete_group_file).

Args:
    file_id(str): 必填，文件ID 参考 `File` 对象。
    group_id(int): 必填，群号。
    busid(int): 可选，文件类型 参考 `File` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        if group_id is not None:
            payload['group_id'] = group_id
        if busid is not None:
            payload['busid'] = busid
        return await self._call_napcat_api(event, 'delete_group_file', payload)

    @filter.llm_tool(name='napcat_delete_group_folder')
    async def napcat_delete_group_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_id: str,
        group_id: int,
        folder: str = None
    ):
        """能力: 删除群文件夹 (API: /delete_group_folder).

Args:
    folder_id(str): 必填，文件夹ID。
    group_id(int): 必填，群号。
    folder(str): 可选，文件夹ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_id is not None:
            payload['folder_id'] = folder_id
        if group_id is not None:
            payload['group_id'] = group_id
        if folder is not None:
            payload['folder'] = folder
        return await self._call_napcat_api(event, 'delete_group_folder', payload)

    @filter.llm_tool(name='napcat_delete_guild_role')
    async def napcat_delete_guild_role_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        role_id: str = None
    ):
        """能力: 删除频道角色 (API: /delete_guild_role).

Args:
    guild_id(str): 可选，频道ID。
    role_id(str): 可选，角色ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if role_id is not None:
            payload['role_id'] = role_id
        return await self._call_napcat_api(event, 'delete_guild_role', payload)

    @filter.llm_tool(name='napcat_delete_msg')
    async def napcat_delete_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int
    ):
        """能力: 撤回已发送的消息 (API: /delete_msg).

Args:
    message_id(int): 必填，消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'delete_msg', payload)

    @filter.llm_tool(name='napcat_delete_unidirectional_friend')
    async def napcat_delete_unidirectional_friend_tool(
        self,
        event: AstrMessageEvent,
        user_id: int = None
    ):
        """能力: 删除单向好友 (API: /delete_unidirectional_friend).

Args:
    user_id(int): 可选，单向好友QQ号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'delete_unidirectional_friend', payload)

    @filter.llm_tool(name='napcat_do_group_album_comment')
    async def napcat_do_group_album_comment_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        content: str,
        group_id: int,
        lloc: str
    ):
        """能力: 发表群相册评论 (API: /do_group_album_comment).

Args:
    album_id(str): 必填，相册 ID。
    content(str): 必填，评论内容。
    group_id(int): 必填，群号。
    lloc(str): 必填，图片 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if content is not None:
            payload['content'] = content
        if group_id is not None:
            payload['group_id'] = group_id
        if lloc is not None:
            payload['lloc'] = lloc
        return await self._call_napcat_api(event, 'do_group_album_comment', payload)

    @filter.llm_tool(name='napcat_dot_get_word_slices')
    async def napcat_dot_get_word_slices_tool(
        self,
        event: AstrMessageEvent,
        content: str = None
    ):
        """能力: 获取中文分词 ( 隐藏 API ).

Args:
    content(str): 可选，内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if content is not None:
            payload['content'] = content
        return await self._call_napcat_api(event, '.get_word_slices', payload)

    @filter.llm_tool(name='napcat_dot_handle_quick_operation')
    async def napcat_dot_handle_quick_operation_tool(
        self,
        event: AstrMessageEvent,
        context: dict,
        operation: dict
    ):
        """能力: 相当于http的快速操作.

Args:
    context(dict): 必填，事件数据对象, 可做精简, 如去掉 `message` 等无用字段。
    operation(dict): 必填，快速操作对象, 例如 `{"ban": true, "reply": "请不要说脏话"}`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if context is not None:
            payload['context'] = context
        if operation is not None:
            payload['operation'] = operation
        return await self._call_napcat_api(event, '.handle_quick_operation', payload)

    @filter.llm_tool(name='napcat_dot_ocr_image')
    async def napcat_dot_ocr_image_tool(
        self,
        event: AstrMessageEvent,
        image: str
    ):
        """能力: 仅 Windows 可用.

Args:
    image(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, '.ocr_image', payload)

    @filter.llm_tool(name='napcat_download_file')
    async def napcat_download_file_tool(
        self,
        event: AstrMessageEvent,
        base64: str = None,
        headers: list = None,
        name: str = None,
        thread_count: int = None,
        url: str = None
    ):
        """能力: 下载网络文件到本地临时目录 (API: /download_file).

Args:
    base64(str): 可选，base64数据。
    headers(list): 可选，自定义请求头。
    name(str): 可选，自定义文件名称。
    thread_count(int): 可选，下载线程数。
    url(str): 可选，下载链接。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if base64 is not None:
            payload['base64'] = base64
        if headers is not None:
            payload['headers'] = headers
        if name is not None:
            payload['name'] = name
        if thread_count is not None:
            payload['thread_count'] = thread_count
        if url is not None:
            payload['url'] = url
        return await self._call_napcat_api(event, 'download_file', payload)

    @filter.llm_tool(name='napcat_download_file_image_stream')
    async def napcat_download_file_image_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None
    ):
        """能力: 下载图片文件流 (API: /download_file_image_stream).

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'download_file_image_stream', payload)

    @filter.llm_tool(name='napcat_download_file_record_stream')
    async def napcat_download_file_record_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None,
        out_format: str = None
    ):
        """能力: 下载语音文件流 (API: /download_file_record_stream).

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。
    out_format(str): 可选，输出格式。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        if out_format is not None:
            payload['out_format'] = out_format
        return await self._call_napcat_api(event, 'download_file_record_stream', payload)

    @filter.llm_tool(name='napcat_download_file_stream')
    async def napcat_download_file_stream_tool(
        self,
        event: AstrMessageEvent,
        chunk_size: int = None,
        file: str = None,
        file_id: str = None
    ):
        """能力: 以流式方式从网络或本地下载文件 (API: /download_file_stream).

Args:
    chunk_size(int): 可选，分块大小 (字节)。
    file(str): 可选，文件路径或 URL。
    file_id(str): 可选，文件 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chunk_size is not None:
            payload['chunk_size'] = chunk_size
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'download_file_stream', payload)

    @filter.llm_tool(name='napcat_download_fileset')
    async def napcat_download_fileset_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str
    ):
        """能力: 下载文件集 (API: /download_fileset).

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'download_fileset', payload)

    @filter.llm_tool(name='napcat_fetch_custom_face')
    async def napcat_fetch_custom_face_tool(
        self,
        event: AstrMessageEvent,
        count: int
    ):
        """能力: 获取收藏表情 (API: /fetch_custom_face).

Args:
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'fetch_custom_face', payload)

    @filter.llm_tool(name='napcat_fetch_emoji_like')
    async def napcat_fetch_emoji_like_tool(
        self,
        event: AstrMessageEvent,
        cookie: str,
        count: int,
        emojiId: str,
        emojiType: str,
        message_id: int
    ):
        """能力: 获取表情点赞详情 (API: /fetch_emoji_like).

Args:
    cookie(str): 必填，分页Cookie。
    count(int): 必填，获取数量。
    emojiId(str): 必填，表情ID。
    emojiType(str): 必填，表情类型。
    message_id(int): 必填，消息ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if cookie is not None:
            payload['cookie'] = cookie
        if count is not None:
            payload['count'] = count
        if emojiId is not None:
            payload['emojiId'] = emojiId
        if emojiType is not None:
            payload['emojiType'] = emojiType
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'fetch_emoji_like', payload)

    @filter.llm_tool(name='napcat_forward_friend_single_msg')
    async def napcat_forward_friend_single_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int,
        user_id: int,
        group_id: int = None
    ):
        """能力: 消息转发到私聊 (API: /forward_friend_single_msg).

Args:
    message_id(int): 必填，消息ID。
    user_id(int): 必填，目标用户QQ。
    group_id(int): 可选，目标群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'forward_friend_single_msg', payload)

    @filter.llm_tool(name='napcat_forward_group_single_msg')
    async def napcat_forward_group_single_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message_id: int,
        user_id: int = None
    ):
        """能力: 消息转发到群 (API: /forward_group_single_msg).

Args:
    group_id(int): 必填，目标群号。
    message_id(int): 必填，消息ID。
    user_id(int): 可选，目标用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'forward_group_single_msg', payload)

    @filter.llm_tool(name='napcat_friend_poke')
    async def napcat_friend_poke_tool(
        self,
        event: AstrMessageEvent,
        user_id: int,
        group_id: int = None,
        target_id: int = None
    ):
        """能力: 在群聊或私聊中发送戳一戳动作 (API: /friend_poke).

Args:
    user_id(int): 必填，用户QQ。
    group_id(int): 可选，群号。
    target_id(int): 可选，目标QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        if target_id is not None:
            payload['target_id'] = target_id
        return await self._call_napcat_api(event, 'friend_poke', payload)

    @filter.llm_tool(name='napcat_get_ai_characters')
    async def napcat_get_ai_characters_tool(
        self,
        event: AstrMessageEvent,
        chat_type: str,
        group_id: int
    ):
        """能力: 获取群聊中的AI角色列表 (API: /get_ai_characters).

Args:
    chat_type(str): 必填，1 or 2?。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if chat_type is not None:
            payload['chat_type'] = chat_type
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_ai_characters', payload)

    @filter.llm_tool(name='napcat_get_ai_record')
    async def napcat_get_ai_record_tool(
        self,
        event: AstrMessageEvent,
        character: str,
        group_id: int,
        text: str
    ):
        """能力: 通过 AI 语音引擎获取指定文本的语音 URL (API: /get_ai_record).

Args:
    character(str): 必填，character_id。
    group_id(int): 必填，群号。
    text(str): 必填，语音文本内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if character is not None:
            payload['character'] = character
        if group_id is not None:
            payload['group_id'] = group_id
        if text is not None:
            payload['text'] = text
        return await self._call_napcat_api(event, 'get_ai_record', payload)

    @filter.llm_tool(name='napcat_get_clientkey')
    async def napcat_get_clientkey_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取当前登录帐号的ClientKey (API: /get_clientkey).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_clientkey', payload)

    @filter.llm_tool(name='napcat_get_collection_list')
    async def napcat_get_collection_list_tool(
        self,
        event: AstrMessageEvent,
        category: str,
        count: int
    ):
        """能力: 获取收藏列表 (API: /get_collection_list).

Args:
    category(str): 必填，分类ID。
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if category is not None:
            payload['category'] = category
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_collection_list', payload)

    @filter.llm_tool(name='napcat_get_cookies')
    async def napcat_get_cookies_tool(
        self,
        event: AstrMessageEvent,
        domain: str
    ):
        """能力: 获取指定域名的 Cookies (API: /get_cookies).

Args:
    domain(str): 必填，需要获取 cookies 的域名 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if domain is not None:
            payload['domain'] = domain
        return await self._call_napcat_api(event, 'get_cookies', payload)

    @filter.llm_tool(name='napcat_get_credentials')
    async def napcat_get_credentials_tool(
        self,
        event: AstrMessageEvent,
        domain: str
    ):
        """能力: 获取 QQ 相关接口凭证 (API: /get_credentials).

Args:
    domain(str): 必填，需要获取 cookies 的域名 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if domain is not None:
            payload['domain'] = domain
        return await self._call_napcat_api(event, 'get_credentials', payload)

    @filter.llm_tool(name='napcat_get_csrf_token')
    async def napcat_get_csrf_token_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取 CSRF Token (API: /get_csrf_token).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_csrf_token', payload)

    @filter.llm_tool(name='napcat_get_doubt_friends_add_request')
    async def napcat_get_doubt_friends_add_request_tool(
        self,
        event: AstrMessageEvent,
        count: int
    ):
        """能力: 获取系统的可疑好友申请列表 (API: /get_doubt_friends_add_request).

Args:
    count(int): 必填，获取数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_doubt_friends_add_request', payload)

    @filter.llm_tool(name='napcat_get_emoji_likes')
    async def napcat_get_emoji_likes_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        emoji_id: int,
        message_id: int,
        emoji_type: int = None,
        group_id: int = None
    ):
        """能力: 获取消息表情点赞列表 (API: /get_emoji_likes).

Args:
    count(int): 必填，数量，0代表全部。
    emoji_id(int): 必填，表情ID。
    message_id(int): 必填，消息ID，可以传递长ID或短ID。
    emoji_type(int): 可选，表情类型。
    group_id(int): 可选，群号，短ID可不传。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if emoji_id is not None:
            payload['emoji_id'] = emoji_id
        if message_id is not None:
            payload['message_id'] = message_id
        if emoji_type is not None:
            payload['emoji_type'] = emoji_type
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_emoji_likes', payload)

    @filter.llm_tool(name='napcat_get_essence_msg_list')
    async def napcat_get_essence_msg_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取指定群聊中的精华消息列表 (API: /get_essence_msg_list).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_essence_msg_list', payload)

    @filter.llm_tool(name='napcat_get_file')
    async def napcat_get_file_tool(
        self,
        event: AstrMessageEvent,
        file: str = None,
        file_id: str = None
    ):
        """能力: 获取指定文件的详细信息及下载路径 (API: /get_file).

Args:
    file(str): 可选，文件路径、URL或Base64。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_file', payload)

    @filter.llm_tool(name='napcat_get_fileset_id')
    async def napcat_get_fileset_id_tool(
        self,
        event: AstrMessageEvent,
        share_code: str
    ):
        """能力: 获取文件集 ID (API: /get_fileset_id).

Args:
    share_code(str): 必填，分享码或分享链接。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if share_code is not None:
            payload['share_code'] = share_code
        return await self._call_napcat_api(event, 'get_fileset_id', payload)

    @filter.llm_tool(name='napcat_get_fileset_info')
    async def napcat_get_fileset_info_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str
    ):
        """能力: 获取文件集信息 (API: /get_fileset_info).

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_fileset_info', payload)

    @filter.llm_tool(name='napcat_get_flash_file_list')
    async def napcat_get_flash_file_list_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str
    ):
        """能力: 获取闪传文件列表 (API: /get_flash_file_list).

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_flash_file_list', payload)

    @filter.llm_tool(name='napcat_get_flash_file_url')
    async def napcat_get_flash_file_url_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
        file_index: int = None,
        file_name: str = None
    ):
        """能力: 获取闪传文件链接 (API: /get_flash_file_url).

Args:
    fileset_id(str): 必填，文件集 ID。
    file_index(int): 可选，文件索引。
    file_name(str): 可选，文件名。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        if file_index is not None:
            payload['file_index'] = file_index
        if file_name is not None:
            payload['file_name'] = file_name
        return await self._call_napcat_api(event, 'get_flash_file_url', payload)

    @filter.llm_tool(name='napcat_get_forward_msg')
    async def napcat_get_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int,
        id: str = None
    ):
        """能力: 获取合并转发消息的具体内容 (API: /get_forward_msg).

Args:
    message_id(int): 必填，消息ID。
    id(str): 可选，合并转发 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        if id is not None:
            payload['id'] = id
        return await self._call_napcat_api(event, 'get_forward_msg', payload)

    @filter.llm_tool(name='napcat_get_friend_list')
    async def napcat_get_friend_list_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool
    ):
        """能力: 获取当前帐号的好友列表 (API: /get_friend_list).

Args:
    no_cache(bool): 必填，是否不使用缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_friend_list', payload)

    @filter.llm_tool(name='napcat_get_friend_msg_history')
    async def napcat_get_friend_msg_history_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        disable_get_url: bool,
        parse_mult_msg: bool,
        quick_reply: bool,
        reverse_order: bool,
        reverseOrder: bool,
        user_id: int,
        message_seq: int = None
    ):
        """能力: 获取指定好友的历史聊天记录 (API: /get_friend_msg_history).

Args:
    count(int): 必填，获取消息数量。
    disable_get_url(bool): 必填，是否禁用获取URL。
    parse_mult_msg(bool): 必填，是否解析合并消息。
    quick_reply(bool): 必填，是否快速回复。
    reverse_order(bool): 必填，是否反向排序。
    reverseOrder(bool): 必填，是否反向排序(旧版本兼容)。
    user_id(int): 必填，用户QQ。
    message_seq(int): 可选，起始消息序号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if disable_get_url is not None:
            payload['disable_get_url'] = disable_get_url
        if parse_mult_msg is not None:
            payload['parse_mult_msg'] = parse_mult_msg
        if quick_reply is not None:
            payload['quick_reply'] = quick_reply
        if reverse_order is not None:
            payload['reverse_order'] = reverse_order
        if reverseOrder is not None:
            payload['reverseOrder'] = reverseOrder
        if user_id is not None:
            payload['user_id'] = user_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'get_friend_msg_history', payload)

    @filter.llm_tool(name='napcat_get_friends_with_category')
    async def napcat_get_friends_with_category_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取好友分组列表 (API: /get_friends_with_category).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_friends_with_category', payload)

    @filter.llm_tool(name='napcat_get_group_album_media_list')
    async def napcat_get_group_album_media_list_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        attach_info: str,
        group_id: int
    ):
        """能力: 获取群相册列表 (API: /get_group_album_media_list).

Args:
    album_id(str): 必填，相册ID。
    attach_info(str): 必填，附加信息（用于分页）。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if attach_info is not None:
            payload['attach_info'] = attach_info
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_album_media_list', payload)

    @filter.llm_tool(name='napcat_get_group_at_all_remain')
    async def napcat_get_group_at_all_remain_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群 @全体成员 剩余次数 (API: /get_group_at_all_remain).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_at_all_remain', payload)

    @filter.llm_tool(name='napcat_get_group_detail_info')
    async def napcat_get_group_detail_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群聊的详细信息，包括成员数、最大成员数等 (API: /get_group_detail_info).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_detail_info', payload)

    @filter.llm_tool(name='napcat_get_group_file_system_info')
    async def napcat_get_group_file_system_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群聊文件系统的空间及状态信息 (API: /get_group_file_system_info).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_file_system_info', payload)

    @filter.llm_tool(name='napcat_get_group_file_url')
    async def napcat_get_group_file_url_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int,
        busid: int = None
    ):
        """能力: 获取指定群文件的下载链接 (API: /get_group_file_url).

Args:
    file_id(str): 必填，文件ID 参考 `File` 对象。
    group_id(int): 必填，群号。
    busid(int): 可选，文件类型 参考 `File` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        if group_id is not None:
            payload['group_id'] = group_id
        if busid is not None:
            payload['busid'] = busid
        return await self._call_napcat_api(event, 'get_group_file_url', payload)

    @filter.llm_tool(name='napcat_get_group_files_by_folder')
    async def napcat_get_group_files_by_folder_tool(
        self,
        event: AstrMessageEvent,
        file_count: int,
        group_id: int,
        folder: str = None,
        folder_id: str = None
    ):
        """能力: 获取群子目录文件列表 (API: /get_group_files_by_folder).

Args:
    file_count(int): 必填，一次性获取的文件数量。
    group_id(int): 必填，群号。
    folder(str): 可选，和 folder_id 二选一。
    folder_id(str): 可选，文件夹ID 参考 `Folder` 对象。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_count is not None:
            payload['file_count'] = file_count
        if group_id is not None:
            payload['group_id'] = group_id
        if folder is not None:
            payload['folder'] = folder
        if folder_id is not None:
            payload['folder_id'] = folder_id
        return await self._call_napcat_api(event, 'get_group_files_by_folder', payload)

    @filter.llm_tool(name='napcat_get_group_honor_info')
    async def napcat_get_group_honor_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        type: str
    ):
        """能力: | type | 类型 | | ----------------- | ------------------------ | | all | 所有（默认） | | talkative | 群聊之火 | | performer | 群聊炽焰 | | legend | 龙王 | | strong_newbie | 冒尖小春笋（R.I.P） | | emotion | 快乐源泉 | (API: /get_group_honor_info).

Args:
    group_id(int): 必填，群号。
    type(str): 必填，要获取的群荣誉类型, 可传入 `talkative` `performer` `legend` `strong_newbie` `emotion` 以分别获取单个类型的群荣誉数据, 或传入 `all` 获取所有数据。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if type is not None:
            payload['type'] = type
        return await self._call_napcat_api(event, 'get_group_honor_info', payload)

    @filter.llm_tool(name='napcat_get_group_ignore_add_request')
    async def napcat_get_group_ignore_add_request_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取群被忽略的加群请求 (API: /get_group_ignore_add_request).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_group_ignore_add_request', payload)

    @filter.llm_tool(name='napcat_get_group_ignored_notifies')
    async def napcat_get_group_ignored_notifies_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取被忽略的入群申请和邀请通知 (API: /get_group_ignored_notifies).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_group_ignored_notifies', payload)

    @filter.llm_tool(name='napcat_get_group_info')
    async def napcat_get_group_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        no_cache: bool = None
    ):
        """能力: 获取群聊的基本信息 (API: /get_group_info).

Args:
    group_id(int): 必填，群号。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_info', payload)

    @filter.llm_tool(name='napcat_get_group_info_ex')
    async def napcat_get_group_info_ex_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群信息ex (API: /get_group_info_ex).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_info_ex', payload)

    @filter.llm_tool(name='napcat_get_group_list')
    async def napcat_get_group_list_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool
    ):
        """能力: 获取当前帐号的群聊列表 (API: /get_group_list).

Args:
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_list', payload)

    @filter.llm_tool(name='napcat_get_group_member_info')
    async def napcat_get_group_member_info_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        no_cache: bool,
        user_id: int
    ):
        """能力: 获取群聊中指定成员的信息 (API: /get_group_member_info).

Args:
    group_id(int): 必填，群号。
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。
    user_id(int): 必填，QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_group_member_info', payload)

    @filter.llm_tool(name='napcat_get_group_member_list')
    async def napcat_get_group_member_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        no_cache: bool = None
    ):
        """能力: 获取群聊中的所有成员列表 (API: /get_group_member_list).

Args:
    group_id(int): 必填，群号。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_group_member_list', payload)

    @filter.llm_tool(name='napcat_get_group_msg_history')
    async def napcat_get_group_msg_history_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        disable_get_url: bool,
        group_id: int,
        parse_mult_msg: bool,
        quick_reply: bool,
        reverse_order: bool,
        reverseOrder: bool,
        message_seq: int = None
    ):
        """能力: 获取指定群聊的历史聊天记录 (API: /get_group_msg_history).

Args:
    count(int): 必填，获取消息数量。
    disable_get_url(bool): 必填，是否禁用获取URL。
    group_id(int): 必填，群号。
    parse_mult_msg(bool): 必填，是否解析合并消息。
    quick_reply(bool): 必填，是否快速回复。
    reverse_order(bool): 必填，是否反向排序。
    reverseOrder(bool): 必填，是否反向排序(旧版本兼容)。
    message_seq(int): 可选，起始消息序号, 可通过 `get_msg` 获得。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if disable_get_url is not None:
            payload['disable_get_url'] = disable_get_url
        if group_id is not None:
            payload['group_id'] = group_id
        if parse_mult_msg is not None:
            payload['parse_mult_msg'] = parse_mult_msg
        if quick_reply is not None:
            payload['quick_reply'] = quick_reply
        if reverse_order is not None:
            payload['reverse_order'] = reverse_order
        if reverseOrder is not None:
            payload['reverseOrder'] = reverseOrder
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'get_group_msg_history', payload)

    @filter.llm_tool(name='napcat_get_group_notice')
    async def napcat_get_group_notice_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: _获取群公告 (API: /_get_group_notice).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, '_get_group_notice', payload)

    @filter.llm_tool(name='napcat_get_group_root_files')
    async def napcat_get_group_root_files_tool(
        self,
        event: AstrMessageEvent,
        file_count: int,
        group_id: int
    ):
        """能力: 获取群文件根目录下的所有文件和文件夹 (API: /get_group_root_files).

Args:
    file_count(int): 必填，文件数量。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_count is not None:
            payload['file_count'] = file_count
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_root_files', payload)

    @filter.llm_tool(name='napcat_get_group_shut_list')
    async def napcat_get_group_shut_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群禁言列表 (API: /get_group_shut_list).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'get_group_shut_list', payload)

    @filter.llm_tool(name='napcat_get_group_system_msg')
    async def napcat_get_group_system_msg_tool(
        self,
        event: AstrMessageEvent,
        count: int
    ):
        """能力: 获取群系统消息 (API: /get_group_system_msg).

Args:
    count(int): 必填，获取的消息数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_group_system_msg', payload)

    @filter.llm_tool(name='napcat_get_guild_channel_list')
    async def napcat_get_guild_channel_list_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        no_cache: bool = None
    ):
        """能力: 获取子频道列表 (API: /get_guild_channel_list).

Args:
    guild_id(str): 可选，频道ID。
    no_cache(bool): 可选，是否无视缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_guild_channel_list', payload)

    @filter.llm_tool(name='napcat_get_guild_list')
    async def napcat_get_guild_list_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: get_guild_list (API: /get_guild_list).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_guild_list', payload)

    @filter.llm_tool(name='napcat_get_guild_member_list')
    async def napcat_get_guild_member_list_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        next_token: str = None
    ):
        """能力: 获取频道成员列表 (API: /get_guild_member_list).

Args:
    guild_id(str): 可选，频道ID。
    next_token(str): 可选，翻页Token。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if next_token is not None:
            payload['next_token'] = next_token
        return await self._call_napcat_api(event, 'get_guild_member_list', payload)

    @filter.llm_tool(name='napcat_get_guild_member_profile')
    async def napcat_get_guild_member_profile_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None,
        user_id: int = None
    ):
        """能力: 单独获取频道成员信息 (API: /get_guild_member_profile).

Args:
    guild_id(str): 可选，频道ID。
    user_id(int): 可选，用户ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_guild_member_profile', payload)

    @filter.llm_tool(name='napcat_get_guild_meta_by_guest')
    async def napcat_get_guild_meta_by_guest_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str = None
    ):
        """能力: 通过访客获取频道元数据 (API: /get_guild_meta_by_guest).

Args:
    guild_id(str): 可选，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_guild_meta_by_guest', payload)

    @filter.llm_tool(name='napcat_get_guild_msg')
    async def napcat_get_guild_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int,
        no_cache: bool = None
    ):
        """能力: 获取频道消息 (API: /get_guild_msg).

Args:
    message_id(int): 必填，频道消息ID。
    no_cache(bool): 可选，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: false。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_guild_msg', payload)

    @filter.llm_tool(name='napcat_get_guild_roles')
    async def napcat_get_guild_roles_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str
    ):
        """能力: 获取频道角色列表 (API: /get_guild_roles).

Args:
    guild_id(str): 必填，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_guild_roles', payload)

    @filter.llm_tool(name='napcat_get_guild_service_profile')
    async def napcat_get_guild_service_profile_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: get_guild_service_profile (API: /get_guild_service_profile).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_guild_service_profile', payload)

    @filter.llm_tool(name='napcat_get_image')
    async def napcat_get_image_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        file_id: str = None
    ):
        """能力: 获取指定图片的信息及路径 (API: /get_image).

Args:
    file(str): 必填，收到的图片文件名（消息段的 `file` 参数），如 `6B4DE3DFD1BD271E3297859D41C530F5.jpg`。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_image', payload)

    @filter.llm_tool(name='napcat_get_login_info')
    async def napcat_get_login_info_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取当前登录帐号的信息 (API: /get_login_info).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_login_info', payload)

    @filter.llm_tool(name='napcat_get_mini_app_ark')
    async def napcat_get_mini_app_ark_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取小程序 Ark (API: /get_mini_app_ark).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_mini_app_ark', payload)

    @filter.llm_tool(name='napcat_get_model_show')
    async def napcat_get_model_show_tool(
        self,
        event: AstrMessageEvent,
        model: str
    ):
        """能力: _获取在线机型 (API: /_get_model_show).

Args:
    model(str): 必填，模型名称。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if model is not None:
            payload['model'] = model
        return await self._call_napcat_api(event, '_get_model_show', payload)

    @filter.llm_tool(name='napcat_get_msg')
    async def napcat_get_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int
    ):
        """能力: 根据消息 ID 获取消息详细信息 (API: /get_msg).

Args:
    message_id(int): 必填，消息 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'get_msg', payload)

    @filter.llm_tool(name='napcat_get_online_clients')
    async def napcat_get_online_clients_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool = None
    ):
        """能力: 获取当前登录账号的在线客户端列表 (API: /get_online_clients).

Args:
    no_cache(bool): 可选，是否无视缓存。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        return await self._call_napcat_api(event, 'get_online_clients', payload)

    @filter.llm_tool(name='napcat_get_online_file_msg')
    async def napcat_get_online_file_msg_tool(
        self,
        event: AstrMessageEvent,
        user_id: int
    ):
        """能力: 获取在线文件消息 (API: /get_online_file_msg).

Args:
    user_id(int): 必填，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_online_file_msg', payload)

    @filter.llm_tool(name='napcat_get_private_file_url')
    async def napcat_get_private_file_url_tool(
        self,
        event: AstrMessageEvent,
        file_id: str
    ):
        """能力: 获取指定私聊文件的下载链接 (API: /get_private_file_url).

Args:
    file_id(str): 必填，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_private_file_url', payload)

    @filter.llm_tool(name='napcat_get_profile_like')
    async def napcat_get_profile_like_tool(
        self,
        event: AstrMessageEvent,
        count: int,
        start: int,
        user_id: int = None
    ):
        """能力: 获取点赞列表 (API: /get_profile_like).

Args:
    count(int): 必填，获取数量。
    start(int): 必填，起始位置。
    user_id(int): 可选，指定用户，不填为获取所有。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        if start is not None:
            payload['start'] = start
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_profile_like', payload)

    @filter.llm_tool(name='napcat_get_qun_album_list')
    async def napcat_get_qun_album_list_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        attach_info: str = None
    ):
        """能力: 获取群相册列表 (API: /get_qun_album_list).

Args:
    group_id(int): 必填，群号。
    attach_info(str): 可选，附加信息（用于分页，从上一次返回结果中获取）。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if attach_info is not None:
            payload['attach_info'] = attach_info
        return await self._call_napcat_api(event, 'get_qun_album_list', payload)

    @filter.llm_tool(name='napcat_get_recent_contact')
    async def napcat_get_recent_contact_tool(
        self,
        event: AstrMessageEvent,
        count: int
    ):
        """能力: 获取的最新消息是每个会话最新的消息 (API: /get_recent_contact).

Args:
    count(int): 必填，获取的数量。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if count is not None:
            payload['count'] = count
        return await self._call_napcat_api(event, 'get_recent_contact', payload)

    @filter.llm_tool(name='napcat_get_record')
    async def napcat_get_record_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        out_format: str,
        file_id: str = None
    ):
        """能力: 获取指定语音文件的信息，并支持格式转换 (API: /get_record).

Args:
    file(str): 必填，收到的语音文件名（消息段的 `file` 参数）, 如 `0B38145AA44505000B38145AA4450500.silk`。
    out_format(str): 必填，要转换到的格式, 目前支持 `mp3`、`amr`、`wma`、`m4a`、`spx`、`ogg`、`wav`、`flac`。
    file_id(str): 可选，文件ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if out_format is not None:
            payload['out_format'] = out_format
        if file_id is not None:
            payload['file_id'] = file_id
        return await self._call_napcat_api(event, 'get_record', payload)

    @filter.llm_tool(name='napcat_get_rkey')
    async def napcat_get_rkey_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取rkey (API: /get_rkey).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_rkey', payload)

    @filter.llm_tool(name='napcat_get_rkey_server')
    async def napcat_get_rkey_server_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取 RKey 服务器 (API: /get_rkey_server).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_rkey_server', payload)

    @filter.llm_tool(name='napcat_get_robot_uin_range')
    async def napcat_get_robot_uin_range_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取机器人 UIN 范围 (API: /get_robot_uin_range).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_robot_uin_range', payload)

    @filter.llm_tool(name='napcat_get_share_link')
    async def napcat_get_share_link_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str
    ):
        """能力: 获取文件分享链接 (API: /get_share_link).

Args:
    fileset_id(str): 必填，文件集 ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        return await self._call_napcat_api(event, 'get_share_link', payload)

    @filter.llm_tool(name='napcat_get_status')
    async def napcat_get_status_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取状态 (API: /get_status).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_status', payload)

    @filter.llm_tool(name='napcat_get_stranger_info')
    async def napcat_get_stranger_info_tool(
        self,
        event: AstrMessageEvent,
        no_cache: bool,
        user_id: int
    ):
        """能力: 获取账号信息 (API: /get_stranger_info).

Args:
    no_cache(bool): 必填，是否不使用缓存（使用缓存可能更新不及时, 但响应更快） 默认值: `false`。
    user_id(int): 必填，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if no_cache is not None:
            payload['no_cache'] = no_cache
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'get_stranger_info', payload)

    @filter.llm_tool(name='napcat_get_topic_channel_feeds')
    async def napcat_get_topic_channel_feeds_tool(
        self,
        event: AstrMessageEvent,
        channel_id: str = None,
        guild_id: str = None
    ):
        """能力: 获取话题频道帖子 (API: /get_topic_channel_feeds).

Args:
    channel_id(str): 可选，子频道ID。
    guild_id(str): 可选，频道ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if channel_id is not None:
            payload['channel_id'] = channel_id
        if guild_id is not None:
            payload['guild_id'] = guild_id
        return await self._call_napcat_api(event, 'get_topic_channel_feeds', payload)

    @filter.llm_tool(name='napcat_get_unidirectional_friend_list')
    async def napcat_get_unidirectional_friend_list_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取单向好友列表 (API: /get_unidirectional_friend_list).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_unidirectional_friend_list', payload)

    @filter.llm_tool(name='napcat_get_version_info')
    async def napcat_get_version_info_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取版本信息 (API: /get_version_info).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'get_version_info', payload)

    @filter.llm_tool(name='napcat_group_poke')
    async def napcat_group_poke_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        user_id: int,
        target_id: int = None
    ):
        """能力: 在群聊或私聊中发送戳一戳动作 (API: /group_poke).

Args:
    group_id(int): 必填，群号。
    user_id(int): 必填，用户QQ。
    target_id(int): 可选，目标QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        if target_id is not None:
            payload['target_id'] = target_id
        return await self._call_napcat_api(event, 'group_poke', payload)

    @filter.llm_tool(name='napcat_mark_all_as_read')
    async def napcat_mark_all_as_read_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: _设置所有消息已读 (API: /_mark_all_as_read).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, '_mark_all_as_read', payload)

    @filter.llm_tool(name='napcat_mark_group_msg_as_read')
    async def napcat_mark_group_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message_id: int = None,
        user_id: int = None
    ):
        """能力: 标记指定渠道的消息为已读 (API: /mark_group_msg_as_read).

Args:
    group_id(int): 必填，群号。
    message_id(int): 可选，消息ID。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'mark_group_msg_as_read', payload)

    @filter.llm_tool(name='napcat_mark_msg_as_read')
    async def napcat_mark_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        group_id: int = None,
        message_id: int = None,
        user_id: int = None
    ):
        """能力: 标记指定渠道的消息为已读 (API: /mark_msg_as_read).

Args:
    group_id(int): 可选，与user_id二选一。
    message_id(int): 可选，消息ID。
    user_id(int): 可选，与user_id二选一。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'mark_msg_as_read', payload)

    @filter.llm_tool(name='napcat_mark_private_msg_as_read')
    async def napcat_mark_private_msg_as_read_tool(
        self,
        event: AstrMessageEvent,
        user_id: int,
        group_id: int = None,
        message_id: int = None
    ):
        """能力: 标记指定渠道的消息为已读 (API: /mark_private_msg_as_read).

Args:
    user_id(int): 必填，用户QQ。
    group_id(int): 可选，群号。
    message_id(int): 可选，消息ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'mark_private_msg_as_read', payload)

    @filter.llm_tool(name='napcat_move_group_file')
    async def napcat_move_group_file_tool(
        self,
        event: AstrMessageEvent,
        current_parent_directory: str,
        file_id: str,
        group_id: int,
        target_parent_directory: str
    ):
        """能力: 移动群文件 (API: /move_group_file).

Args:
    current_parent_directory(str): 必填，根目录填 /。
    file_id(str): 必填，文件ID。
    group_id(int): 必填，群号。
    target_parent_directory(str): 必填，目标父目录。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if current_parent_directory is not None:
            payload['current_parent_directory'] = current_parent_directory
        if file_id is not None:
            payload['file_id'] = file_id
        if group_id is not None:
            payload['group_id'] = group_id
        if target_parent_directory is not None:
            payload['target_parent_directory'] = target_parent_directory
        return await self._call_napcat_api(event, 'move_group_file', payload)

    @filter.llm_tool(name='napcat_nc_get_packet_status')
    async def napcat_nc_get_packet_status_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取底层Packet服务的运行状态 (API: /nc_get_packet_status).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'nc_get_packet_status', payload)

    @filter.llm_tool(name='napcat_nc_get_rkey')
    async def napcat_nc_get_rkey_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: nc获取rkey (API: /nc_get_rkey).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'nc_get_rkey', payload)

    @filter.llm_tool(name='napcat_nc_get_user_status')
    async def napcat_nc_get_user_status_tool(
        self,
        event: AstrMessageEvent,
        user_id: int
    ):
        """能力: 获取用户在线状态 (API: /nc_get_user_status).

Args:
    user_id(int): 必填，QQ号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'nc_get_user_status', payload)

    @filter.llm_tool(name='napcat_ocr_image')
    async def napcat_ocr_image_tool(
        self,
        event: AstrMessageEvent,
        image: str
    ):
        """能力: 仅 Windows 可用 (API: /ocr_image).

Args:
    image(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, 'ocr_image', payload)

    @filter.llm_tool(name='napcat_qidian_get_account_info')
    async def napcat_qidian_get_account_info_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: 获取企点账号信息 (API: /qidian_get_account_info).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'qidian_get_account_info', payload)

    @filter.llm_tool(name='napcat_receive_online_file')
    async def napcat_receive_online_file_tool(
        self,
        event: AstrMessageEvent,
        element_id: str,
        msg_id: str,
        user_id: int
    ):
        """能力: 接收在线文件 (API: /receive_online_file).

Args:
    element_id(str): 必填，元素 ID。
    msg_id(str): 必填，消息 ID。
    user_id(int): 必填，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if element_id is not None:
            payload['element_id'] = element_id
        if msg_id is not None:
            payload['msg_id'] = msg_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'receive_online_file', payload)

    @filter.llm_tool(name='napcat_refuse_online_file')
    async def napcat_refuse_online_file_tool(
        self,
        event: AstrMessageEvent,
        element_id: str,
        msg_id: str,
        user_id: int
    ):
        """能力: 拒绝在线文件 (API: /refuse_online_file).

Args:
    element_id(str): 必填，元素 ID。
    msg_id(str): 必填，消息 ID。
    user_id(int): 必填，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if element_id is not None:
            payload['element_id'] = element_id
        if msg_id is not None:
            payload['msg_id'] = msg_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'refuse_online_file', payload)

    @filter.llm_tool(name='napcat_reload_event_filter')
    async def napcat_reload_event_filter_tool(
        self,
        event: AstrMessageEvent,
        file: str
    ):
        """能力: 重载事件过滤器 (API: /reload_event_filter).

Args:
    file(str): 必填，事件过滤器文件。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        return await self._call_napcat_api(event, 'reload_event_filter', payload)

    @filter.llm_tool(name='napcat_rename_group_file')
    async def napcat_rename_group_file_tool(
        self,
        event: AstrMessageEvent,
        current_parent_directory: str,
        file_id: str,
        group_id: int,
        new_name: str
    ):
        """能力: 重命名群文件 (API: /rename_group_file).

Args:
    current_parent_directory(str): 必填，当前父目录。
    file_id(str): 必填，文件ID。
    group_id(int): 必填，群号。
    new_name(str): 必填，新文件名。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if current_parent_directory is not None:
            payload['current_parent_directory'] = current_parent_directory
        if file_id is not None:
            payload['file_id'] = file_id
        if group_id is not None:
            payload['group_id'] = group_id
        if new_name is not None:
            payload['new_name'] = new_name
        return await self._call_napcat_api(event, 'rename_group_file', payload)

    @filter.llm_tool(name='napcat_send_ark_share')
    async def napcat_send_ark_share_tool(
        self,
        event: AstrMessageEvent,
        phone_number: str,
        group_id: int = None,
        user_id: int = None
    ):
        """能力: 获取用户推荐的 Ark 内容 (API: /send_ark_share).

Args:
    phone_number(str): 必填，手机号。
    group_id(int): 可选，群号。
    user_id(int): 可选，QQ号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if phone_number is not None:
            payload['phone_number'] = phone_number
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_ark_share', payload)

    @filter.llm_tool(name='napcat_send_flash_msg')
    async def napcat_send_flash_msg_tool(
        self,
        event: AstrMessageEvent,
        fileset_id: str,
        group_id: int = None,
        user_id: int = None
    ):
        """能力: 发送闪传消息 (API: /send_flash_msg).

Args:
    fileset_id(str): 必填，文件集 ID。
    group_id(int): 可选，群号。
    user_id(int): 可选，用户 QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if fileset_id is not None:
            payload['fileset_id'] = fileset_id
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_flash_msg', payload)

    @filter.llm_tool(name='napcat_send_forward_msg')
    async def napcat_send_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        messages: list,
        auto_escape: str = None,
        group_id: int = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
        user_id: int = None
    ):
        """能力: 发送合并转发消息 (API: /send_forward_msg).

Args:
    message(str): 必填，See source API docs。
    messages(list): 必填，See source API docs。
    auto_escape(str): 可选，是否作为纯文本发送。
    group_id(int): 可选，群号。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if group_id is not None:
            payload['group_id'] = group_id
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_group_ai_record')
    async def napcat_send_group_ai_record_tool(
        self,
        event: AstrMessageEvent,
        character: str,
        group_id: int,
        text: str
    ):
        """能力: 发送 AI 生成的语音到指定群聊 (API: /send_group_ai_record).

Args:
    character(str): 必填，character_id。
    group_id(int): 必填，群号。
    text(str): 必填，语音文本内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if character is not None:
            payload['character'] = character
        if group_id is not None:
            payload['group_id'] = group_id
        if text is not None:
            payload['text'] = text
        return await self._call_napcat_api(event, 'send_group_ai_record', payload)

    @filter.llm_tool(name='napcat_send_group_ark_share')
    async def napcat_send_group_ark_share_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 获取群分享的 Ark 内容 (API: /send_group_ark_share).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'send_group_ark_share', payload)

    @filter.llm_tool(name='napcat_send_group_forward_msg')
    async def napcat_send_group_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message: str,
        messages: list,
        auto_escape: str = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
        user_id: int = None
    ):
        """能力: 发送群合并转发消息 (API: /send_group_forward_msg).

Args:
    group_id(int): 必填，群号。
    message(str): 必填，See source API docs。
    messages(list): 必填，自定义转发消息, 具体看 [CQcodeopen in new window](https://docs.go-cqhttp.org/cqcode/#%E5%90%88%E5%B9%B6%E8%BD%AC%E5%8F%91%E6%B6%88%E6%81%AF%E8%8A%82%E7%82%B9)。
    auto_escape(str): 可选，是否作为纯文本发送。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_group_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_group_msg')
    async def napcat_send_group_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message: str,
        auto_escape: bool = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None,
        user_id: int = None
    ):
        """能力: 发送群消息 (API: /send_group_msg).

Args:
    group_id(int): 必填，群号。
    message(str): 必填，要发送的内容。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。
    user_id(int): 可选，用户QQ。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_group_msg', payload)

    @filter.llm_tool(name='napcat_send_group_notice')
    async def napcat_send_group_notice_tool(
        self,
        event: AstrMessageEvent,
        confirm_required: str,
        content: str,
        group_id: int,
        is_show_edit_card: str,
        pinned: str,
        tip_window_type: str,
        type: str,
        image: str = None
    ):
        """能力: _发送群公告 (API: /_send_group_notice).

Args:
    confirm_required(str): 必填，是否需要确认 (0/1)。
    content(str): 必填，公告内容。
    group_id(int): 必填，群号。
    is_show_edit_card(str): 必填，是否显示修改群名片引导 (0/1)。
    pinned(str): 必填，是否置顶 (0/1)。
    tip_window_type(str): 必填，弹窗类型 (默认为 0)。
    type(str): 必填，类型 (默认为 1)。
    image(str): 可选，公告图片路径或 URL。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if confirm_required is not None:
            payload['confirm_required'] = confirm_required
        if content is not None:
            payload['content'] = content
        if group_id is not None:
            payload['group_id'] = group_id
        if is_show_edit_card is not None:
            payload['is_show_edit_card'] = is_show_edit_card
        if pinned is not None:
            payload['pinned'] = pinned
        if tip_window_type is not None:
            payload['tip_window_type'] = tip_window_type
        if type is not None:
            payload['type'] = type
        if image is not None:
            payload['image'] = image
        return await self._call_napcat_api(event, '_send_group_notice', payload)

    @filter.llm_tool(name='napcat_send_group_sign')
    async def napcat_send_group_sign_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 群打卡 (API: /send_group_sign).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'send_group_sign', payload)

    @filter.llm_tool(name='napcat_send_guild_channel_msg')
    async def napcat_send_guild_channel_msg_tool(
        self,
        event: AstrMessageEvent,
        channel_id: str = None,
        guild_id: str = None,
        message: str = None
    ):
        """能力: 发送信息到子频道 (API: /send_guild_channel_msg).

Args:
    channel_id(str): 可选，子频道ID。
    guild_id(str): 可选，频道ID。
    message(str): 可选，消息, 与原有消息类型相同。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if channel_id is not None:
            payload['channel_id'] = channel_id
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if message is not None:
            payload['message'] = message
        return await self._call_napcat_api(event, 'send_guild_channel_msg', payload)

    @filter.llm_tool(name='napcat_send_like')
    async def napcat_send_like_tool(
        self,
        event: AstrMessageEvent,
        times: int,
        user_id: int
    ):
        """能力: 给指定用户点赞 (API: /send_like).

Args:
    times(int): 必填，赞的次数，每个好友每天最多 10 次 默认值: 1。
    user_id(int): 必填，对方 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if times is not None:
            payload['times'] = times
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'send_like', payload)

    @filter.llm_tool(name='napcat_send_msg')
    async def napcat_send_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message: str,
        message_type: str,
        user_id: int,
        auto_escape: bool = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None
    ):
        """能力: send_msg (API: /send_msg).

Args:
    group_id(int): 必填，群号 ( 消息类型为 `group` 时需要 )。
    message(str): 必填，要发送的内容。
    message_type(str): 必填，消息类型, 支持 `private`、`group` , 分别对应私聊、群组, 如不传入, 则根据传入的 `*_id` 参数判断。
    user_id(int): 必填，对方 QQ 号 ( 消息类型为 `private` 时需要 )。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if message_type is not None:
            payload['message_type'] = message_type
        if user_id is not None:
            payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_msg', payload)

    @filter.llm_tool(name='napcat_send_online_file')
    async def napcat_send_online_file_tool(
        self,
        event: AstrMessageEvent,
        file_path: str,
        user_id: int,
        file_name: str = None
    ):
        """能力: 发送在线文件 (API: /send_online_file).

Args:
    file_path(str): 必填，本地文件路径。
    user_id(int): 必填，用户 QQ。
    file_name(str): 可选，文件名 (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_path is not None:
            payload['file_path'] = file_path
        if user_id is not None:
            payload['user_id'] = user_id
        if file_name is not None:
            payload['file_name'] = file_name
        return await self._call_napcat_api(event, 'send_online_file', payload)

    @filter.llm_tool(name='napcat_send_online_folder')
    async def napcat_send_online_folder_tool(
        self,
        event: AstrMessageEvent,
        folder_path: str,
        user_id: int,
        folder_name: str = None
    ):
        """能力: 发送在线文件夹 (API: /send_online_folder).

Args:
    folder_path(str): 必填，本地文件夹路径。
    user_id(int): 必填，用户 QQ。
    folder_name(str): 可选，文件夹名称 (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if folder_path is not None:
            payload['folder_path'] = folder_path
        if user_id is not None:
            payload['user_id'] = user_id
        if folder_name is not None:
            payload['folder_name'] = folder_name
        return await self._call_napcat_api(event, 'send_online_folder', payload)

    @filter.llm_tool(name='napcat_send_packet')
    async def napcat_send_packet_tool(
        self,
        event: AstrMessageEvent,
        cmd: str,
        data: str,
        rsp: str
    ):
        """能力: 发送原始数据包 (API: /send_packet).

Args:
    cmd(str): 必填，命令字。
    data(str): 必填，十六进制数据。
    rsp(str): 必填，是否等待响应。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if cmd is not None:
            payload['cmd'] = cmd
        if data is not None:
            payload['data'] = data
        if rsp is not None:
            payload['rsp'] = rsp
        return await self._call_napcat_api(event, 'send_packet', payload)

    @filter.llm_tool(name='napcat_send_poke')
    async def napcat_send_poke_tool(
        self,
        event: AstrMessageEvent,
        user_id: int,
        group_id: int = None,
        target_id: int = None
    ):
        """能力: 在群聊或私聊中发送戳一戳动作 (API: /send_poke).

Args:
    user_id(int): 必填，不填则为私聊戳。
    group_id(int): 可选，不填则为私聊戳。
    target_id(int): 可选，不填则为私聊戳。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if user_id is not None:
            payload['user_id'] = user_id
        if group_id is not None:
            payload['group_id'] = group_id
        if target_id is not None:
            payload['target_id'] = target_id
        return await self._call_napcat_api(event, 'send_poke', payload)

    @filter.llm_tool(name='napcat_send_private_forward_msg')
    async def napcat_send_private_forward_msg_tool(
        self,
        event: AstrMessageEvent,
        message: str,
        messages: list,
        user_id: int,
        auto_escape: str = None,
        group_id: int = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None
    ):
        """能力: 发送私聊合并转发消息 (API: /send_private_forward_msg).

Args:
    message(str): 必填，See source API docs。
    messages(list): 必填，自定义转发消息, 具体看 [CQcodeopen in new window](https://docs.go-cqhttp.org/cqcode/#%E5%90%88%E5%B9%B6%E8%BD%AC%E5%8F%91%E6%B6%88%E6%81%AF%E8%8A%82%E7%82%B9)。
    user_id(int): 必填，好友QQ号。
    auto_escape(str): 可选，是否作为纯文本发送。
    group_id(int): 可选，群号。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message is not None:
            payload['message'] = message
        if messages is not None:
            payload['messages'] = messages
        if user_id is not None:
            payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if group_id is not None:
            payload['group_id'] = group_id
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_private_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_private_msg')
    async def napcat_send_private_msg_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message: str,
        user_id: int,
        auto_escape: bool = None,
        message_type: str = None,
        news: list = None,
        prompt: str = None,
        source: str = None,
        summary: str = None,
        timeout: int = None
    ):
        """能力: send_private_msg (API: /send_private_msg).

Args:
    group_id(int): 必填，主动发起临时会话时的来源群号(可选, 机器人本身必须是管理员/群主)。
    message(str): 必填，要发送的内容。
    user_id(int): 必填，对方 QQ 号。
    auto_escape(bool): 可选，消息内容是否作为纯文本发送 ( 即不解析 CQ 码 ) , 只在 `message` 字段是字符串时有效 默认值: `false`。
    message_type(str): 可选，消息类型 (private/group)。
    news(list): 可选，合并转发新闻。
    prompt(str): 可选，合并转发提示。
    source(str): 可选，合并转发来源。
    summary(str): 可选，合并转发摘要。
    timeout(int): 可选，自定义发送超时(毫秒)，覆盖自动计算值。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message is not None:
            payload['message'] = message
        if user_id is not None:
            payload['user_id'] = user_id
        if auto_escape is not None:
            payload['auto_escape'] = auto_escape
        if message_type is not None:
            payload['message_type'] = message_type
        if news is not None:
            payload['news'] = news
        if prompt is not None:
            payload['prompt'] = prompt
        if source is not None:
            payload['source'] = source
        if summary is not None:
            payload['summary'] = summary
        if timeout is not None:
            payload['timeout'] = timeout
        return await self._call_napcat_api(event, 'send_private_msg', payload)

    @filter.llm_tool(name='napcat_set_diy_online_status')
    async def napcat_set_diy_online_status_tool(
        self,
        event: AstrMessageEvent,
        face_id: str,
        face_type: str,
        wording: str
    ):
        """能力: 设置自定义在线状态 (API: /set_diy_online_status).

Args:
    face_id(str): 必填，图标ID。
    face_type(str): 必填，图标类型。
    wording(str): 必填，状态文字内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if face_id is not None:
            payload['face_id'] = face_id
        if face_type is not None:
            payload['face_type'] = face_type
        if wording is not None:
            payload['wording'] = wording
        return await self._call_napcat_api(event, 'set_diy_online_status', payload)

    @filter.llm_tool(name='napcat_set_doubt_friends_add_request')
    async def napcat_set_doubt_friends_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str
    ):
        """能力: 同意或拒绝系统的可疑好友申请 (API: /set_doubt_friends_add_request).

Args:
    approve(bool): 必填，是否同意 (强制为 true)。
    flag(str): 必填，请求 flag。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        return await self._call_napcat_api(event, 'set_doubt_friends_add_request', payload)

    @filter.llm_tool(name='napcat_set_essence_msg')
    async def napcat_set_essence_msg_tool(
        self,
        event: AstrMessageEvent,
        message_id: int
    ):
        """能力: 将一条消息设置为群精华消息 (API: /set_essence_msg).

Args:
    message_id(int): 必填，消息ID。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if message_id is not None:
            payload['message_id'] = message_id
        return await self._call_napcat_api(event, 'set_essence_msg', payload)

    @filter.llm_tool(name='napcat_set_friend_add_request')
    async def napcat_set_friend_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str,
        remark: str
    ):
        """能力: 同意或拒绝加好友请求 (API: /set_friend_add_request).

Args:
    approve(bool): 必填，是否同意请求 默认值: `true`。
    flag(str): 必填，加好友请求的 flag（需从上报的数据中获得）。
    remark(str): 必填，添加后的好友备注（仅在同意时有效） 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        if remark is not None:
            payload['remark'] = remark
        return await self._call_napcat_api(event, 'set_friend_add_request', payload)

    @filter.llm_tool(name='napcat_set_friend_remark')
    async def napcat_set_friend_remark_tool(
        self,
        event: AstrMessageEvent,
        remark: str,
        user_id: int
    ):
        """能力: 设置好友备注 (API: /set_friend_remark).

Args:
    remark(str): 必填，备注内容。
    user_id(int): 必填，对方 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if remark is not None:
            payload['remark'] = remark
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_friend_remark', payload)

    @filter.llm_tool(name='napcat_set_group_add_option')
    async def napcat_set_group_add_option_tool(
        self,
        event: AstrMessageEvent,
        add_type: int,
        group_id: int,
        group_answer: str = None,
        group_question: str = None
    ):
        """能力: 设置群加群选项 (API: /set_group_add_option).

Args:
    add_type(int): 必填，加群方式。
    group_id(int): 必填，群号。
    group_answer(str): 可选，加群答案。
    group_question(str): 可选，加群问题。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if add_type is not None:
            payload['add_type'] = add_type
        if group_id is not None:
            payload['group_id'] = group_id
        if group_answer is not None:
            payload['group_answer'] = group_answer
        if group_question is not None:
            payload['group_question'] = group_question
        return await self._call_napcat_api(event, 'set_group_add_option', payload)

    @filter.llm_tool(name='napcat_set_group_add_request')
    async def napcat_set_group_add_request_tool(
        self,
        event: AstrMessageEvent,
        approve: bool,
        flag: str,
        count: int = None,
        reason: str = None
    ):
        """能力: 同意或拒绝加群请求或邀请 (API: /set_group_add_request).

Args:
    approve(bool): 必填，是否同意请求／邀请 默认值: `true`。
    flag(str): 必填，加群请求的 flag（需从上报的数据中获得）。
    count(int): 可选，搜索通知数量。
    reason(str): 可选，拒绝理由（仅在拒绝时有效） 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if approve is not None:
            payload['approve'] = approve
        if flag is not None:
            payload['flag'] = flag
        if count is not None:
            payload['count'] = count
        if reason is not None:
            payload['reason'] = reason
        return await self._call_napcat_api(event, 'set_group_add_request', payload)

    @filter.llm_tool(name='napcat_set_group_admin')
    async def napcat_set_group_admin_tool(
        self,
        event: AstrMessageEvent,
        enable: bool,
        group_id: int,
        user_id: int
    ):
        """能力: 设置群管理 (API: /set_group_admin).

Args:
    enable(bool): 必填，true 为设置, false 为取消 默认值: `true`。
    group_id(int): 必填，群号。
    user_id(int): 必填，要设置管理员的 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if enable is not None:
            payload['enable'] = enable
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_group_admin', payload)

    @filter.llm_tool(name='napcat_set_group_album_media_like')
    async def napcat_set_group_album_media_like_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        group_id: int,
        id: str,
        lloc: str,
        set: bool
    ):
        """能力: 点赞群相册 (API: /set_group_album_media_like).

Args:
    album_id(str): 必填，相册ID。
    group_id(int): 必填，群号。
    id(str): 必填，点赞ID。
    lloc(str): 必填，媒体ID (lloc)。
    set(bool): 必填，是否点赞。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if group_id is not None:
            payload['group_id'] = group_id
        if id is not None:
            payload['id'] = id
        if lloc is not None:
            payload['lloc'] = lloc
        if set is not None:
            payload['set'] = set
        return await self._call_napcat_api(event, 'set_group_album_media_like', payload)

    @filter.llm_tool(name='napcat_set_group_anonymous')
    async def napcat_set_group_anonymous_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        enable: bool = None
    ):
        """能力: 群组匿名 (API: /set_group_anonymous).

Args:
    group_id(int): 必填，群号。
    enable(bool): 可选，是否允许匿名聊天 默认值: `true`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if enable is not None:
            payload['enable'] = enable
        return await self._call_napcat_api(event, 'set_group_anonymous', payload)

    @filter.llm_tool(name='napcat_set_group_anonymous_ban')
    async def napcat_set_group_anonymous_ban_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        anonymous: dict = None,
        anonymous_flag: str = None,
        duration: int = None,
        flag: str = None
    ):
        """能力: 群组匿名用户禁言 (API: /set_group_anonymous_ban).

Args:
    group_id(int): 必填，群号。
    anonymous(dict): 可选，可选, 要禁言的匿名用户对象（群消息上报的 `anonymous` 字段）。
    anonymous_flag(str): 可选，可选, 要禁言的匿名用户的 flag（需从群消息上报的数据中获得）。
    duration(int): 可选，禁言时长, 单位秒, 无法取消匿名用户禁言 默认值: `30 * 60`。
    flag(str): 可选，可选, 要禁言的匿名用户的 flag（需从群消息上报的数据中获得）。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if anonymous is not None:
            payload['anonymous'] = anonymous
        if anonymous_flag is not None:
            payload['anonymous_flag'] = anonymous_flag
        if duration is not None:
            payload['duration'] = duration
        if flag is not None:
            payload['flag'] = flag
        return await self._call_napcat_api(event, 'set_group_anonymous_ban', payload)

    @filter.llm_tool(name='napcat_set_group_ban')
    async def napcat_set_group_ban_tool(
        self,
        event: AstrMessageEvent,
        duration: int,
        group_id: int,
        user_id: int
    ):
        """能力: 群禁言 (API: /set_group_ban).

Args:
    duration(int): 必填，禁言时长, 单位秒, 0 表示取消禁言 默认值: `30 * 60`。
    group_id(int): 必填，群号。
    user_id(int): 必填，要禁言的 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if duration is not None:
            payload['duration'] = duration
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_group_ban', payload)

    @filter.llm_tool(name='napcat_set_group_card')
    async def napcat_set_group_card_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        user_id: int,
        card: str = None
    ):
        """能力: 设置群聊中指定成员的群名片 (API: /set_group_card).

Args:
    group_id(int): 必填，群号。
    user_id(int): 必填，要设置的 QQ 号。
    card(str): 可选，群名片内容, 不填或空字符串表示删除群名片 默认值: 空。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        if card is not None:
            payload['card'] = card
        return await self._call_napcat_api(event, 'set_group_card', payload)

    @filter.llm_tool(name='napcat_set_group_kick')
    async def napcat_set_group_kick_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        user_id: int,
        reject_add_request: bool = None
    ):
        """能力: 将指定成员踢出群聊 (API: /set_group_kick).

Args:
    group_id(int): 必填，群号。
    user_id(int): 必填，要踢的 QQ 号。
    reject_add_request(bool): 可选，拒绝此人的加群请求 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        if reject_add_request is not None:
            payload['reject_add_request'] = reject_add_request
        return await self._call_napcat_api(event, 'set_group_kick', payload)

    @filter.llm_tool(name='napcat_set_group_kick_members')
    async def napcat_set_group_kick_members_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        user_id: int,
        reject_add_request: bool = None
    ):
        """能力: 从指定群聊中批量踢出多个成员 (API: /set_group_kick_members).

Args:
    group_id(int): 必填，群号。
    user_id(int): 必填，QQ号列表。
    reject_add_request(bool): 可选，是否拒绝加群请求。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if user_id is not None:
            payload['user_id'] = user_id
        if reject_add_request is not None:
            payload['reject_add_request'] = reject_add_request
        return await self._call_napcat_api(event, 'set_group_kick_members', payload)

    @filter.llm_tool(name='napcat_set_group_leave')
    async def napcat_set_group_leave_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        is_dismiss: bool = None
    ):
        """能力: 退出或解散指定群聊 (API: /set_group_leave).

Args:
    group_id(int): 必填，群号。
    is_dismiss(bool): 可选，是否解散, 如果登录号是群主, 则仅在此项为 true 时能够解散 默认值: `false`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if is_dismiss is not None:
            payload['is_dismiss'] = is_dismiss
        return await self._call_napcat_api(event, 'set_group_leave', payload)

    @filter.llm_tool(name='napcat_set_group_name')
    async def napcat_set_group_name_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        group_name: str
    ):
        """能力: 设置群名 (API: /set_group_name).

Args:
    group_id(int): 必填，群号。
    group_name(str): 必填，群名称。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if group_name is not None:
            payload['group_name'] = group_name
        return await self._call_napcat_api(event, 'set_group_name', payload)

    @filter.llm_tool(name='napcat_set_group_portrait')
    async def napcat_set_group_portrait_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        group_id: int,
        cache: int = None
    ):
        """能力: 修改指定群聊的头像 (API: /set_group_portrait).

Args:
    file(str): 必填，头像文件路径或 URL。
    group_id(int): 必填，群号。
    cache(int): 可选，表示是否使用已缓存的文件。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if group_id is not None:
            payload['group_id'] = group_id
        if cache is not None:
            payload['cache'] = cache
        return await self._call_napcat_api(event, 'set_group_portrait', payload)

    @filter.llm_tool(name='napcat_set_group_remark')
    async def napcat_set_group_remark_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        remark: str
    ):
        """能力: 设置群备注 (API: /set_group_remark).

Args:
    group_id(int): 必填，群号。
    remark(str): 必填，备注。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if remark is not None:
            payload['remark'] = remark
        return await self._call_napcat_api(event, 'set_group_remark', payload)

    @filter.llm_tool(name='napcat_set_group_robot_add_option')
    async def napcat_set_group_robot_add_option_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        robot_member_examine: int = None,
        robot_member_switch: int = None
    ):
        """能力: 设置群机器人加群选项 (API: /set_group_robot_add_option).

Args:
    group_id(int): 必填，群号。
    robot_member_examine(int): 可选，机器人成员审核。
    robot_member_switch(int): 可选，机器人成员开关。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if robot_member_examine is not None:
            payload['robot_member_examine'] = robot_member_examine
        if robot_member_switch is not None:
            payload['robot_member_switch'] = robot_member_switch
        return await self._call_napcat_api(event, 'set_group_robot_add_option', payload)

    @filter.llm_tool(name='napcat_set_group_search')
    async def napcat_set_group_search_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        no_code_finger_open: int = None,
        no_finger_open: int = None
    ):
        """能力: 设置群搜索 (API: /set_group_search).

Args:
    group_id(int): 必填，群号。
    no_code_finger_open(int): 可选，未知。
    no_finger_open(int): 可选，未知。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if no_code_finger_open is not None:
            payload['no_code_finger_open'] = no_code_finger_open
        if no_finger_open is not None:
            payload['no_finger_open'] = no_finger_open
        return await self._call_napcat_api(event, 'set_group_search', payload)

    @filter.llm_tool(name='napcat_set_group_sign')
    async def napcat_set_group_sign_tool(
        self,
        event: AstrMessageEvent,
        group_id: int
    ):
        """能力: 群打卡 (API: /set_group_sign).

Args:
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'set_group_sign', payload)

    @filter.llm_tool(name='napcat_set_group_special_title')
    async def napcat_set_group_special_title_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        special_title: str,
        user_id: int,
        duration: int = None
    ):
        """能力: 设置群聊中指定成员的专属头衔 (API: /set_group_special_title).

Args:
    group_id(int): 必填，群号。
    special_title(str): 必填，专属头衔, 不填或空字符串表示删除专属头衔 默认值: 空。
    user_id(int): 必填，要设置的 QQ 号。
    duration(int): 可选，专属头衔有效期, 单位秒, -1 表示永久, 不过此项似乎没有效果, 可能是只有某些特殊的时间长度有效, 有待测试 默认值: `-1`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if special_title is not None:
            payload['special_title'] = special_title
        if user_id is not None:
            payload['user_id'] = user_id
        if duration is not None:
            payload['duration'] = duration
        return await self._call_napcat_api(event, 'set_group_special_title', payload)

    @filter.llm_tool(name='napcat_set_group_todo')
    async def napcat_set_group_todo_tool(
        self,
        event: AstrMessageEvent,
        group_id: int,
        message_id: int,
        message_seq: int = None
    ):
        """能力: 设置群代办 (API: /set_group_todo).

Args:
    group_id(int): 必填，群号。
    message_id(int): 必填，消息ID。
    message_seq(int): 可选，消息Seq (可选)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if group_id is not None:
            payload['group_id'] = group_id
        if message_id is not None:
            payload['message_id'] = message_id
        if message_seq is not None:
            payload['message_seq'] = message_seq
        return await self._call_napcat_api(event, 'set_group_todo', payload)

    @filter.llm_tool(name='napcat_set_group_whole_ban')
    async def napcat_set_group_whole_ban_tool(
        self,
        event: AstrMessageEvent,
        enable: bool,
        group_id: int
    ):
        """能力: 全体禁言 (API: /set_group_whole_ban).

Args:
    enable(bool): 必填，是否开启全员禁言 默认值: `true`。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if enable is not None:
            payload['enable'] = enable
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'set_group_whole_ban', payload)

    @filter.llm_tool(name='napcat_set_guild_member_role')
    async def napcat_set_guild_member_role_tool(
        self,
        event: AstrMessageEvent,
        guild_id: str,
        role_id: str,
        set: bool = None,
        users: str = None
    ):
        """能力: 设置用户在频道中的角色 (API: /set_guild_member_role).

Args:
    guild_id(str): 必填，频道ID。
    role_id(str): 必填，频道ID。
    set(bool): 可选，是否设置(默认假，取消) 默认值: false。
    users(str): 可选，- 默认值: array。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if role_id is not None:
            payload['role_id'] = role_id
        if set is not None:
            payload['set'] = set
        if users is not None:
            payload['users'] = users
        return await self._call_napcat_api(event, 'set_guild_member_role', payload)

    @filter.llm_tool(name='napcat_set_input_status')
    async def napcat_set_input_status_tool(
        self,
        event: AstrMessageEvent,
        event_type: int,
        user_id: int
    ):
        """能力: 设置输入状态 (API: /set_input_status).

Args:
    event_type(int): 必填，事件类型。
    user_id(int): 必填，QQ号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if event_type is not None:
            payload['event_type'] = event_type
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'set_input_status', payload)

    @filter.llm_tool(name='napcat_set_model_show')
    async def napcat_set_model_show_tool(
        self,
        event: AstrMessageEvent,
        model: str = None,
        model_show: str = None
    ):
        """能力: _设置在线机型 (API: /_set_model_show).

Args:
    model(str): 可选，机型名称。
    model_show(str): 可选，-。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if model is not None:
            payload['model'] = model
        if model_show is not None:
            payload['model_show'] = model_show
        return await self._call_napcat_api(event, '_set_model_show', payload)

    @filter.llm_tool(name='napcat_set_msg_emoji_like')
    async def napcat_set_msg_emoji_like_tool(
        self,
        event: AstrMessageEvent,
        emoji_id: int,
        message_id: int,
        set: bool
    ):
        """能力: 设置消息表情点赞 (API: /set_msg_emoji_like).

Args:
    emoji_id(int): 必填，表情ID。
    message_id(int): 必填，消息ID。
    set(bool): 必填，是否设置。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if emoji_id is not None:
            payload['emoji_id'] = emoji_id
        if message_id is not None:
            payload['message_id'] = message_id
        if set is not None:
            payload['set'] = set
        return await self._call_napcat_api(event, 'set_msg_emoji_like', payload)

    @filter.llm_tool(name='napcat_set_online_status')
    async def napcat_set_online_status_tool(
        self,
        event: AstrMessageEvent,
        battery_status: str,
        batteryStatus: int,
        ext_status: str,
        extStatus: int,
        status: int
    ):
        """能力: ## 状态列表 ### 在线 ```json5; { "status": 10, "ext_status": 0, "battery_status": 0; } ``` ### Q我吧 ```json5; { "status": 60, "ext_status": 0, "battery_status": 0; } ``` ### 离开 ```json5; { "status": 30, "ext_status": 0, "battery_status": 0; } ``` ### 忙碌 ```json5; { " (API: /set_online_status).

Args:
    battery_status(str): 必填，电量状态。
    batteryStatus(int): 必填，电量。
    ext_status(str): 必填，扩展状态。
    extStatus(int): 必填，详情看顶部。
    status(int): 必填，详情看顶部。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if battery_status is not None:
            payload['battery_status'] = battery_status
        if batteryStatus is not None:
            payload['batteryStatus'] = batteryStatus
        if ext_status is not None:
            payload['ext_status'] = ext_status
        if extStatus is not None:
            payload['extStatus'] = extStatus
        if status is not None:
            payload['status'] = status
        return await self._call_napcat_api(event, 'set_online_status', payload)

    @filter.llm_tool(name='napcat_set_qq_avatar')
    async def napcat_set_qq_avatar_tool(
        self,
        event: AstrMessageEvent,
        file: str
    ):
        """能力: 修改当前账号的QQ头像 (API: /set_qq_avatar).

Args:
    file(str): 必填，图片路径、URL或Base64。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        return await self._call_napcat_api(event, 'set_qq_avatar', payload)

    @filter.llm_tool(name='napcat_set_qq_profile')
    async def napcat_set_qq_profile_tool(
        self,
        event: AstrMessageEvent,
        nickname: str,
        personal_note: str = None,
        sex: str = None
    ):
        """能力: 修改当前账号的昵称、个性签名等资料 (API: /set_qq_profile).

Args:
    nickname(str): 必填，昵称。
    personal_note(str): 可选，个性签名。
    sex(str): 可选，性别 (0: 未知, 1: 男, 2: 女)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if nickname is not None:
            payload['nickname'] = nickname
        if personal_note is not None:
            payload['personal_note'] = personal_note
        if sex is not None:
            payload['sex'] = sex
        return await self._call_napcat_api(event, 'set_qq_profile', payload)

    @filter.llm_tool(name='napcat_set_restart')
    async def napcat_set_restart_tool(
        self,
        event: AstrMessageEvent,
        delay: int = None
    ):
        """能力: 重启服务 (API: /set_restart).

Args:
    delay(int): 可选，要延迟的毫秒数, 如果默认情况下无法重启, 可以尝试设置延迟为 2000 左右 默认值: `0`。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if delay is not None:
            payload['delay'] = delay
        return await self._call_napcat_api(event, 'set_restart', payload)

    @filter.llm_tool(name='napcat_set_self_longnick')
    async def napcat_set_self_longnick_tool(
        self,
        event: AstrMessageEvent,
        longNick: str
    ):
        """能力: 修改当前登录帐号的个性签名 (API: /set_self_longnick).

Args:
    longNick(str): 必填，签名内容。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if longNick is not None:
            payload['longNick'] = longNick
        return await self._call_napcat_api(event, 'set_self_longnick', payload)

    @filter.llm_tool(name='napcat_test_download_stream')
    async def napcat_test_download_stream_tool(
        self,
        event: AstrMessageEvent,
        error: bool = None
    ):
        """能力: 流式下载测试 (API: /test_download_stream).

Args:
    error(bool): 可选，是否触发测试错误。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if error is not None:
            payload['error'] = error
        return await self._call_napcat_api(event, 'test_download_stream', payload)

    @filter.llm_tool(name='napcat_trans_group_file')
    async def napcat_trans_group_file_tool(
        self,
        event: AstrMessageEvent,
        file_id: str,
        group_id: int
    ):
        """能力: 传输群文件 (API: /trans_group_file).

Args:
    file_id(str): 必填，文件ID。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_id is not None:
            payload['file_id'] = file_id
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'trans_group_file', payload)

    @filter.llm_tool(name='napcat_translate_en2zh')
    async def napcat_translate_en2zh_tool(
        self,
        event: AstrMessageEvent,
        words: list
    ):
        """能力: 将英文单词列表翻译为中文 (API: /translate_en2zh).

Args:
    words(list): 必填，待翻译单词列表。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if words is not None:
            payload['words'] = words
        return await self._call_napcat_api(event, 'translate_en2zh', payload)

    @filter.llm_tool(name='napcat_unknown')
    async def napcat_unknown_tool(
        self,
        event: AstrMessageEvent
    ):
        """能力: unknown (API: /unknown).

Args:
    无接口参数。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        return await self._call_napcat_api(event, 'unknown', payload)

    @filter.llm_tool(name='napcat_update_guild_role')
    async def napcat_update_guild_role_tool(
        self,
        event: AstrMessageEvent,
        color: str,
        guild_id: str,
        name: str,
        role_id: str,
        independent: bool = None
    ):
        """能力: 修改频道角色 (API: /update_guild_role).

Args:
    color(str): 必填，颜色(示例:4294927682)。
    guild_id(str): 必填，频道ID。
    name(str): 必填，角色名。
    role_id(str): 必填，角色ID。
    independent(bool): 可选，未知 默认值: false。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if color is not None:
            payload['color'] = color
        if guild_id is not None:
            payload['guild_id'] = guild_id
        if name is not None:
            payload['name'] = name
        if role_id is not None:
            payload['role_id'] = role_id
        if independent is not None:
            payload['independent'] = independent
        return await self._call_napcat_api(event, 'update_guild_role', payload)

    @filter.llm_tool(name='napcat_upload_file_stream')
    async def napcat_upload_file_stream_tool(
        self,
        event: AstrMessageEvent,
        file_retention: int,
        stream_id: str,
        chunk_data: str = None,
        chunk_index: int = None,
        expected_sha256: str = None,
        file_size: int = None,
        filename: str = None,
        is_complete: bool = None,
        reset: bool = None,
        total_chunks: int = None,
        verify_only: bool = None
    ):
        """能力: 以流式方式上传文件数据到机器人 (API: /upload_file_stream).

Args:
    file_retention(int): 必填，默认5分钟回收 不设置或0为不回收。
    stream_id(str): 必填，流 ID。
    chunk_data(str): 可选，分块数据 (Base64)。
    chunk_index(int): 可选，分块索引。
    expected_sha256(str): 可选，期望的 SHA256。
    file_size(int): 可选，文件总大小。
    filename(str): 可选，文件名。
    is_complete(bool): 可选，是否完成。
    reset(bool): 可选，是否重置。
    total_chunks(int): 可选，总分块数。
    verify_only(bool): 可选，是否仅验证。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file_retention is not None:
            payload['file_retention'] = file_retention
        if stream_id is not None:
            payload['stream_id'] = stream_id
        if chunk_data is not None:
            payload['chunk_data'] = chunk_data
        if chunk_index is not None:
            payload['chunk_index'] = chunk_index
        if expected_sha256 is not None:
            payload['expected_sha256'] = expected_sha256
        if file_size is not None:
            payload['file_size'] = file_size
        if filename is not None:
            payload['filename'] = filename
        if is_complete is not None:
            payload['is_complete'] = is_complete
        if reset is not None:
            payload['reset'] = reset
        if total_chunks is not None:
            payload['total_chunks'] = total_chunks
        if verify_only is not None:
            payload['verify_only'] = verify_only
        return await self._call_napcat_api(event, 'upload_file_stream', payload)

    @filter.llm_tool(name='napcat_upload_group_file')
    async def napcat_upload_group_file_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        group_id: int,
        name: str,
        upload_file: bool,
        folder: str = None,
        folder_id: str = None
    ):
        """能力: 上传资源路径或URL指定的文件到指定群聊的文件系统中 (API: /upload_group_file).

Args:
    file(str): 必填，资源路径或URL。
    group_id(int): 必填，群号。
    name(str): 必填，储存名称。
    upload_file(bool): 必填，是否执行上传。
    folder(str): 可选，文件夹ID（二选一）。
    folder_id(str): 可选，父目录 ID (兼容性字段)。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if group_id is not None:
            payload['group_id'] = group_id
        if name is not None:
            payload['name'] = name
        if upload_file is not None:
            payload['upload_file'] = upload_file
        if folder is not None:
            payload['folder'] = folder
        if folder_id is not None:
            payload['folder_id'] = folder_id
        return await self._call_napcat_api(event, 'upload_group_file', payload)

    @filter.llm_tool(name='napcat_upload_image_to_qun_album')
    async def napcat_upload_image_to_qun_album_tool(
        self,
        event: AstrMessageEvent,
        album_id: str,
        album_name: str,
        file: str,
        group_id: int
    ):
        """能力: 上传图片到群相册 (API: /upload_image_to_qun_album).

Args:
    album_id(str): 必填，相册ID。
    album_name(str): 必填，相册名称。
    file(str): 必填，图片路径、URL或Base64。
    group_id(int): 必填，群号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if album_id is not None:
            payload['album_id'] = album_id
        if album_name is not None:
            payload['album_name'] = album_name
        if file is not None:
            payload['file'] = file
        if group_id is not None:
            payload['group_id'] = group_id
        return await self._call_napcat_api(event, 'upload_image_to_qun_album', payload)

    @filter.llm_tool(name='napcat_upload_private_file')
    async def napcat_upload_private_file_tool(
        self,
        event: AstrMessageEvent,
        file: str,
        name: str,
        upload_file: bool,
        user_id: int
    ):
        """能力: 上传本地文件到指定私聊会话中 (API: /upload_private_file).

Args:
    file(str): 必填，资源路径或URL。
    name(str): 必填，文件名称。
    upload_file(bool): 必填，是否执行上传。
    user_id(int): 必填，对方 QQ 号。

Returns:
    str: 返回 API 响应的 JSON 字符串。"""
        payload: dict = {}
        if file is not None:
            payload['file'] = file
        if name is not None:
            payload['name'] = name
        if upload_file is not None:
            payload['upload_file'] = upload_file
        if user_id is not None:
            payload['user_id'] = user_id
        return await self._call_napcat_api(event, 'upload_private_file', payload)


