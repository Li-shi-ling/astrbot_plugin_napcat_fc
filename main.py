from __future__ import annotations

import json
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


@register(
    "astrbot_plugin_napcat_fc",
    "Soulter / AstrBot contributors",
    "将 NapCat / OneBot API 注册为 AstrBot 函数工具。",
    "1.6.0",
)
class NapCatFunctionToolsPlugin(Star):
    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        super().__init__(context)
        self.config = dict(config or {})
        self.tool_count = 166

    async def initialize(self):
        logger.info(f"NapCat 函数工具已初始化：{self.tool_count} 个。")

    async def terminate(self):
        return None

    async def _call_napcat_api(
        self,
        event: AstrMessageEvent,
        endpoint: str,
        payload: dict[str, Any] | None = None,
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

    @filter.llm_tool(name="napcat_call_api")
    async def napcat_call_api_tool(
        self,
        event: AstrMessageEvent,
        endpoint: str = "",
        payload: dict[str, Any] | None = None,
    ):
        """Call any NapCat/OneBot API through the current aiocqhttp event.

        Args:
            endpoint(string): API action name or path, for example send_group_msg.
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, endpoint, payload)

    @filter.llm_tool(name='napcat_dot_handle_quick_operation')
    async def napcat_dot_handle_quick_operation_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /.handle_quick_operation.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '.handle_quick_operation', payload)

    @filter.llm_tool(name='napcat_dot_ocr_image')
    async def napcat_dot_ocr_image_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /.ocr_image.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '.ocr_image', payload)

    @filter.llm_tool(name='napcat_del_group_notice')
    async def napcat_del_group_notice_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_del_group_notice.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_del_group_notice', payload)

    @filter.llm_tool(name='napcat_get_group_notice')
    async def napcat_get_group_notice_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_get_group_notice.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_get_group_notice', payload)

    @filter.llm_tool(name='napcat_get_model_show')
    async def napcat_get_model_show_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_get_model_show.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_get_model_show', payload)

    @filter.llm_tool(name='napcat_mark_all_as_read')
    async def napcat_mark_all_as_read_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_mark_all_as_read.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_mark_all_as_read', payload)

    @filter.llm_tool(name='napcat_send_group_notice')
    async def napcat_send_group_notice_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_send_group_notice.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_send_group_notice', payload)

    @filter.llm_tool(name='napcat_set_model_show')
    async def napcat_set_model_show_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /_set_model_show.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, '_set_model_show', payload)

    @filter.llm_tool(name='napcat_arksharegroup')
    async def napcat_arksharegroup_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /ArkShareGroup.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'ArkShareGroup', payload)

    @filter.llm_tool(name='napcat_arksharepeer')
    async def napcat_arksharepeer_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /ArkSharePeer.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'ArkSharePeer', payload)

    @filter.llm_tool(name='napcat_bot_exit')
    async def napcat_bot_exit_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /bot_exit.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'bot_exit', payload)

    @filter.llm_tool(name='napcat_can_send_image')
    async def napcat_can_send_image_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /can_send_image.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'can_send_image', payload)

    @filter.llm_tool(name='napcat_can_send_record')
    async def napcat_can_send_record_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /can_send_record.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'can_send_record', payload)

    @filter.llm_tool(name='napcat_cancel_group_todo')
    async def napcat_cancel_group_todo_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /cancel_group_todo.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'cancel_group_todo', payload)

    @filter.llm_tool(name='napcat_cancel_online_file')
    async def napcat_cancel_online_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /cancel_online_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'cancel_online_file', payload)

    @filter.llm_tool(name='napcat_check_url_safely')
    async def napcat_check_url_safely_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /check_url_safely.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'check_url_safely', payload)

    @filter.llm_tool(name='napcat_clean_cache')
    async def napcat_clean_cache_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /clean_cache.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'clean_cache', payload)

    @filter.llm_tool(name='napcat_clean_stream_temp_file')
    async def napcat_clean_stream_temp_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /clean_stream_temp_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'clean_stream_temp_file', payload)

    @filter.llm_tool(name='napcat_click_inline_keyboard_button')
    async def napcat_click_inline_keyboard_button_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /click_inline_keyboard_button.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'click_inline_keyboard_button', payload)

    @filter.llm_tool(name='napcat_complete_group_todo')
    async def napcat_complete_group_todo_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /complete_group_todo.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'complete_group_todo', payload)

    @filter.llm_tool(name='napcat_create_collection')
    async def napcat_create_collection_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /create_collection.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'create_collection', payload)

    @filter.llm_tool(name='napcat_create_flash_task')
    async def napcat_create_flash_task_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /create_flash_task.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'create_flash_task', payload)

    @filter.llm_tool(name='napcat_create_group_file_folder')
    async def napcat_create_group_file_folder_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /create_group_file_folder.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'create_group_file_folder', payload)

    @filter.llm_tool(name='napcat_del_group_album_media')
    async def napcat_del_group_album_media_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /del_group_album_media.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'del_group_album_media', payload)

    @filter.llm_tool(name='napcat_delete_essence_msg')
    async def napcat_delete_essence_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /delete_essence_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'delete_essence_msg', payload)

    @filter.llm_tool(name='napcat_delete_friend')
    async def napcat_delete_friend_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /delete_friend.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'delete_friend', payload)

    @filter.llm_tool(name='napcat_delete_group_file')
    async def napcat_delete_group_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /delete_group_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'delete_group_file', payload)

    @filter.llm_tool(name='napcat_delete_group_folder')
    async def napcat_delete_group_folder_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /delete_group_folder.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'delete_group_folder', payload)

    @filter.llm_tool(name='napcat_delete_msg')
    async def napcat_delete_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /delete_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'delete_msg', payload)

    @filter.llm_tool(name='napcat_do_group_album_comment')
    async def napcat_do_group_album_comment_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /do_group_album_comment.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'do_group_album_comment', payload)

    @filter.llm_tool(name='napcat_download_file')
    async def napcat_download_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /download_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'download_file', payload)

    @filter.llm_tool(name='napcat_download_file_image_stream')
    async def napcat_download_file_image_stream_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /download_file_image_stream.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'download_file_image_stream', payload)

    @filter.llm_tool(name='napcat_download_file_record_stream')
    async def napcat_download_file_record_stream_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /download_file_record_stream.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'download_file_record_stream', payload)

    @filter.llm_tool(name='napcat_download_file_stream')
    async def napcat_download_file_stream_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /download_file_stream.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'download_file_stream', payload)

    @filter.llm_tool(name='napcat_download_fileset')
    async def napcat_download_fileset_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /download_fileset.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'download_fileset', payload)

    @filter.llm_tool(name='napcat_fetch_custom_face')
    async def napcat_fetch_custom_face_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /fetch_custom_face.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'fetch_custom_face', payload)

    @filter.llm_tool(name='napcat_fetch_emoji_like')
    async def napcat_fetch_emoji_like_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /fetch_emoji_like.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'fetch_emoji_like', payload)

    @filter.llm_tool(name='napcat_forward_friend_single_msg')
    async def napcat_forward_friend_single_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /forward_friend_single_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'forward_friend_single_msg', payload)

    @filter.llm_tool(name='napcat_forward_group_single_msg')
    async def napcat_forward_group_single_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /forward_group_single_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'forward_group_single_msg', payload)

    @filter.llm_tool(name='napcat_friend_poke')
    async def napcat_friend_poke_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /friend_poke.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'friend_poke', payload)

    @filter.llm_tool(name='napcat_get_ai_characters')
    async def napcat_get_ai_characters_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_ai_characters.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_ai_characters', payload)

    @filter.llm_tool(name='napcat_get_ai_record')
    async def napcat_get_ai_record_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_ai_record.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_ai_record', payload)

    @filter.llm_tool(name='napcat_get_clientkey')
    async def napcat_get_clientkey_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_clientkey.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_clientkey', payload)

    @filter.llm_tool(name='napcat_get_collection_list')
    async def napcat_get_collection_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_collection_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_collection_list', payload)

    @filter.llm_tool(name='napcat_get_cookies')
    async def napcat_get_cookies_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_cookies.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_cookies', payload)

    @filter.llm_tool(name='napcat_get_credentials')
    async def napcat_get_credentials_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_credentials.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_credentials', payload)

    @filter.llm_tool(name='napcat_get_csrf_token')
    async def napcat_get_csrf_token_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_csrf_token.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_csrf_token', payload)

    @filter.llm_tool(name='napcat_get_doubt_friends_add_request')
    async def napcat_get_doubt_friends_add_request_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_doubt_friends_add_request.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_doubt_friends_add_request', payload)

    @filter.llm_tool(name='napcat_get_emoji_likes')
    async def napcat_get_emoji_likes_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_emoji_likes.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_emoji_likes', payload)

    @filter.llm_tool(name='napcat_get_essence_msg_list')
    async def napcat_get_essence_msg_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_essence_msg_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_essence_msg_list', payload)

    @filter.llm_tool(name='napcat_get_file')
    async def napcat_get_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_file', payload)

    @filter.llm_tool(name='napcat_get_fileset_id')
    async def napcat_get_fileset_id_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_fileset_id.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_fileset_id', payload)

    @filter.llm_tool(name='napcat_get_fileset_info')
    async def napcat_get_fileset_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_fileset_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_fileset_info', payload)

    @filter.llm_tool(name='napcat_get_flash_file_list')
    async def napcat_get_flash_file_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_flash_file_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_flash_file_list', payload)

    @filter.llm_tool(name='napcat_get_flash_file_url')
    async def napcat_get_flash_file_url_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_flash_file_url.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_flash_file_url', payload)

    @filter.llm_tool(name='napcat_get_forward_msg')
    async def napcat_get_forward_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_forward_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_forward_msg', payload)

    @filter.llm_tool(name='napcat_get_friend_list')
    async def napcat_get_friend_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_friend_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_friend_list', payload)

    @filter.llm_tool(name='napcat_get_friend_msg_history')
    async def napcat_get_friend_msg_history_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_friend_msg_history.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_friend_msg_history', payload)

    @filter.llm_tool(name='napcat_get_friends_with_category')
    async def napcat_get_friends_with_category_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_friends_with_category.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_friends_with_category', payload)

    @filter.llm_tool(name='napcat_get_group_album_media_list')
    async def napcat_get_group_album_media_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_album_media_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_album_media_list', payload)

    @filter.llm_tool(name='napcat_get_group_at_all_remain')
    async def napcat_get_group_at_all_remain_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_at_all_remain.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_at_all_remain', payload)

    @filter.llm_tool(name='napcat_get_group_detail_info')
    async def napcat_get_group_detail_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_detail_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_detail_info', payload)

    @filter.llm_tool(name='napcat_get_group_file_system_info')
    async def napcat_get_group_file_system_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_file_system_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_file_system_info', payload)

    @filter.llm_tool(name='napcat_get_group_file_url')
    async def napcat_get_group_file_url_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_file_url.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_file_url', payload)

    @filter.llm_tool(name='napcat_get_group_files_by_folder')
    async def napcat_get_group_files_by_folder_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_files_by_folder.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_files_by_folder', payload)

    @filter.llm_tool(name='napcat_get_group_honor_info')
    async def napcat_get_group_honor_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_honor_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_honor_info', payload)

    @filter.llm_tool(name='napcat_get_group_ignore_add_request')
    async def napcat_get_group_ignore_add_request_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_ignore_add_request.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_ignore_add_request', payload)

    @filter.llm_tool(name='napcat_get_group_ignored_notifies')
    async def napcat_get_group_ignored_notifies_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_ignored_notifies.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_ignored_notifies', payload)

    @filter.llm_tool(name='napcat_get_group_info')
    async def napcat_get_group_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_info', payload)

    @filter.llm_tool(name='napcat_get_group_info_ex')
    async def napcat_get_group_info_ex_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_info_ex.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_info_ex', payload)

    @filter.llm_tool(name='napcat_get_group_list')
    async def napcat_get_group_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_list', payload)

    @filter.llm_tool(name='napcat_get_group_member_info')
    async def napcat_get_group_member_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_member_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_member_info', payload)

    @filter.llm_tool(name='napcat_get_group_member_list')
    async def napcat_get_group_member_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_member_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_member_list', payload)

    @filter.llm_tool(name='napcat_get_group_msg_history')
    async def napcat_get_group_msg_history_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_msg_history.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_msg_history', payload)

    @filter.llm_tool(name='napcat_get_group_root_files')
    async def napcat_get_group_root_files_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_root_files.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_root_files', payload)

    @filter.llm_tool(name='napcat_get_group_shut_list')
    async def napcat_get_group_shut_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_shut_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_shut_list', payload)

    @filter.llm_tool(name='napcat_get_group_system_msg')
    async def napcat_get_group_system_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_group_system_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_group_system_msg', payload)

    @filter.llm_tool(name='napcat_get_guild_list')
    async def napcat_get_guild_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_guild_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_guild_list', payload)

    @filter.llm_tool(name='napcat_get_guild_service_profile')
    async def napcat_get_guild_service_profile_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_guild_service_profile.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_guild_service_profile', payload)

    @filter.llm_tool(name='napcat_get_image')
    async def napcat_get_image_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_image.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_image', payload)

    @filter.llm_tool(name='napcat_get_login_info')
    async def napcat_get_login_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_login_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_login_info', payload)

    @filter.llm_tool(name='napcat_get_mini_app_ark')
    async def napcat_get_mini_app_ark_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_mini_app_ark.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_mini_app_ark', payload)

    @filter.llm_tool(name='napcat_get_msg')
    async def napcat_get_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_msg', payload)

    @filter.llm_tool(name='napcat_get_online_clients')
    async def napcat_get_online_clients_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_online_clients.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_online_clients', payload)

    @filter.llm_tool(name='napcat_get_online_file_msg')
    async def napcat_get_online_file_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_online_file_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_online_file_msg', payload)

    @filter.llm_tool(name='napcat_get_private_file_url')
    async def napcat_get_private_file_url_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_private_file_url.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_private_file_url', payload)

    @filter.llm_tool(name='napcat_get_profile_like')
    async def napcat_get_profile_like_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_profile_like.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_profile_like', payload)

    @filter.llm_tool(name='napcat_get_qun_album_list')
    async def napcat_get_qun_album_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_qun_album_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_qun_album_list', payload)

    @filter.llm_tool(name='napcat_get_recent_contact')
    async def napcat_get_recent_contact_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_recent_contact.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_recent_contact', payload)

    @filter.llm_tool(name='napcat_get_record')
    async def napcat_get_record_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_record.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_record', payload)

    @filter.llm_tool(name='napcat_get_rkey')
    async def napcat_get_rkey_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_rkey.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_rkey', payload)

    @filter.llm_tool(name='napcat_get_rkey_server')
    async def napcat_get_rkey_server_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_rkey_server.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_rkey_server', payload)

    @filter.llm_tool(name='napcat_get_robot_uin_range')
    async def napcat_get_robot_uin_range_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_robot_uin_range.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_robot_uin_range', payload)

    @filter.llm_tool(name='napcat_get_share_link')
    async def napcat_get_share_link_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_share_link.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_share_link', payload)

    @filter.llm_tool(name='napcat_get_status')
    async def napcat_get_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_status', payload)

    @filter.llm_tool(name='napcat_get_stranger_info')
    async def napcat_get_stranger_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_stranger_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_stranger_info', payload)

    @filter.llm_tool(name='napcat_get_unidirectional_friend_list')
    async def napcat_get_unidirectional_friend_list_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_unidirectional_friend_list.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_unidirectional_friend_list', payload)

    @filter.llm_tool(name='napcat_get_version_info')
    async def napcat_get_version_info_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /get_version_info.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'get_version_info', payload)

    @filter.llm_tool(name='napcat_group_poke')
    async def napcat_group_poke_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /group_poke.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'group_poke', payload)

    @filter.llm_tool(name='napcat_mark_group_msg_as_read')
    async def napcat_mark_group_msg_as_read_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /mark_group_msg_as_read.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'mark_group_msg_as_read', payload)

    @filter.llm_tool(name='napcat_mark_msg_as_read')
    async def napcat_mark_msg_as_read_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /mark_msg_as_read.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'mark_msg_as_read', payload)

    @filter.llm_tool(name='napcat_mark_private_msg_as_read')
    async def napcat_mark_private_msg_as_read_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /mark_private_msg_as_read.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'mark_private_msg_as_read', payload)

    @filter.llm_tool(name='napcat_move_group_file')
    async def napcat_move_group_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /move_group_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'move_group_file', payload)

    @filter.llm_tool(name='napcat_nc_get_packet_status')
    async def napcat_nc_get_packet_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /nc_get_packet_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'nc_get_packet_status', payload)

    @filter.llm_tool(name='napcat_nc_get_rkey')
    async def napcat_nc_get_rkey_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /nc_get_rkey.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'nc_get_rkey', payload)

    @filter.llm_tool(name='napcat_nc_get_user_status')
    async def napcat_nc_get_user_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /nc_get_user_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'nc_get_user_status', payload)

    @filter.llm_tool(name='napcat_ocr_image')
    async def napcat_ocr_image_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /ocr_image.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'ocr_image', payload)

    @filter.llm_tool(name='napcat_receive_online_file')
    async def napcat_receive_online_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /receive_online_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'receive_online_file', payload)

    @filter.llm_tool(name='napcat_refuse_online_file')
    async def napcat_refuse_online_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /refuse_online_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'refuse_online_file', payload)

    @filter.llm_tool(name='napcat_rename_group_file')
    async def napcat_rename_group_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /rename_group_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'rename_group_file', payload)

    @filter.llm_tool(name='napcat_send_ark_share')
    async def napcat_send_ark_share_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_ark_share.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_ark_share', payload)

    @filter.llm_tool(name='napcat_send_flash_msg')
    async def napcat_send_flash_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_flash_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_flash_msg', payload)

    @filter.llm_tool(name='napcat_send_forward_msg')
    async def napcat_send_forward_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_forward_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_group_ai_record')
    async def napcat_send_group_ai_record_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_group_ai_record.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_group_ai_record', payload)

    @filter.llm_tool(name='napcat_send_group_ark_share')
    async def napcat_send_group_ark_share_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_group_ark_share.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_group_ark_share', payload)

    @filter.llm_tool(name='napcat_send_group_forward_msg')
    async def napcat_send_group_forward_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_group_forward_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_group_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_group_msg')
    async def napcat_send_group_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_group_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_group_msg', payload)

    @filter.llm_tool(name='napcat_send_group_sign')
    async def napcat_send_group_sign_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_group_sign.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_group_sign', payload)

    @filter.llm_tool(name='napcat_send_like')
    async def napcat_send_like_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_like.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_like', payload)

    @filter.llm_tool(name='napcat_send_msg')
    async def napcat_send_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_msg', payload)

    @filter.llm_tool(name='napcat_send_online_file')
    async def napcat_send_online_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_online_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_online_file', payload)

    @filter.llm_tool(name='napcat_send_online_folder')
    async def napcat_send_online_folder_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_online_folder.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_online_folder', payload)

    @filter.llm_tool(name='napcat_send_packet')
    async def napcat_send_packet_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_packet.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_packet', payload)

    @filter.llm_tool(name='napcat_send_poke')
    async def napcat_send_poke_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_poke.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_poke', payload)

    @filter.llm_tool(name='napcat_send_private_forward_msg')
    async def napcat_send_private_forward_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_private_forward_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_private_forward_msg', payload)

    @filter.llm_tool(name='napcat_send_private_msg')
    async def napcat_send_private_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /send_private_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'send_private_msg', payload)

    @filter.llm_tool(name='napcat_set_diy_online_status')
    async def napcat_set_diy_online_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_diy_online_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_diy_online_status', payload)

    @filter.llm_tool(name='napcat_set_doubt_friends_add_request')
    async def napcat_set_doubt_friends_add_request_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_doubt_friends_add_request.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_doubt_friends_add_request', payload)

    @filter.llm_tool(name='napcat_set_essence_msg')
    async def napcat_set_essence_msg_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_essence_msg.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_essence_msg', payload)

    @filter.llm_tool(name='napcat_set_friend_add_request')
    async def napcat_set_friend_add_request_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_friend_add_request.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_friend_add_request', payload)

    @filter.llm_tool(name='napcat_set_friend_remark')
    async def napcat_set_friend_remark_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_friend_remark.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_friend_remark', payload)

    @filter.llm_tool(name='napcat_set_group_add_option')
    async def napcat_set_group_add_option_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_add_option.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_add_option', payload)

    @filter.llm_tool(name='napcat_set_group_add_request')
    async def napcat_set_group_add_request_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_add_request.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_add_request', payload)

    @filter.llm_tool(name='napcat_set_group_admin')
    async def napcat_set_group_admin_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_admin.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_admin', payload)

    @filter.llm_tool(name='napcat_set_group_album_media_like')
    async def napcat_set_group_album_media_like_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_album_media_like.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_album_media_like', payload)

    @filter.llm_tool(name='napcat_set_group_anonymous')
    async def napcat_set_group_anonymous_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_anonymous.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_anonymous', payload)

    @filter.llm_tool(name='napcat_set_group_anonymous_ban')
    async def napcat_set_group_anonymous_ban_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_anonymous_ban.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_anonymous_ban', payload)

    @filter.llm_tool(name='napcat_set_group_ban')
    async def napcat_set_group_ban_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_ban.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_ban', payload)

    @filter.llm_tool(name='napcat_set_group_card')
    async def napcat_set_group_card_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_card.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_card', payload)

    @filter.llm_tool(name='napcat_set_group_kick')
    async def napcat_set_group_kick_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_kick.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_kick', payload)

    @filter.llm_tool(name='napcat_set_group_kick_members')
    async def napcat_set_group_kick_members_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_kick_members.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_kick_members', payload)

    @filter.llm_tool(name='napcat_set_group_leave')
    async def napcat_set_group_leave_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_leave.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_leave', payload)

    @filter.llm_tool(name='napcat_set_group_name')
    async def napcat_set_group_name_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_name.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_name', payload)

    @filter.llm_tool(name='napcat_set_group_portrait')
    async def napcat_set_group_portrait_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_portrait.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_portrait', payload)

    @filter.llm_tool(name='napcat_set_group_remark')
    async def napcat_set_group_remark_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_remark.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_remark', payload)

    @filter.llm_tool(name='napcat_set_group_robot_add_option')
    async def napcat_set_group_robot_add_option_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_robot_add_option.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_robot_add_option', payload)

    @filter.llm_tool(name='napcat_set_group_search')
    async def napcat_set_group_search_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_search.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_search', payload)

    @filter.llm_tool(name='napcat_set_group_sign')
    async def napcat_set_group_sign_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_sign.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_sign', payload)

    @filter.llm_tool(name='napcat_set_group_special_title')
    async def napcat_set_group_special_title_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_special_title.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_special_title', payload)

    @filter.llm_tool(name='napcat_set_group_todo')
    async def napcat_set_group_todo_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_todo.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_todo', payload)

    @filter.llm_tool(name='napcat_set_group_whole_ban')
    async def napcat_set_group_whole_ban_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_group_whole_ban.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_group_whole_ban', payload)

    @filter.llm_tool(name='napcat_set_input_status')
    async def napcat_set_input_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_input_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_input_status', payload)

    @filter.llm_tool(name='napcat_set_msg_emoji_like')
    async def napcat_set_msg_emoji_like_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_msg_emoji_like.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_msg_emoji_like', payload)

    @filter.llm_tool(name='napcat_set_online_status')
    async def napcat_set_online_status_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_online_status.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_online_status', payload)

    @filter.llm_tool(name='napcat_set_qq_avatar')
    async def napcat_set_qq_avatar_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_qq_avatar.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_qq_avatar', payload)

    @filter.llm_tool(name='napcat_set_qq_profile')
    async def napcat_set_qq_profile_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_qq_profile.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_qq_profile', payload)

    @filter.llm_tool(name='napcat_set_restart')
    async def napcat_set_restart_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_restart.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_restart', payload)

    @filter.llm_tool(name='napcat_set_self_longnick')
    async def napcat_set_self_longnick_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /set_self_longnick.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'set_self_longnick', payload)

    @filter.llm_tool(name='napcat_test_download_stream')
    async def napcat_test_download_stream_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /test_download_stream.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'test_download_stream', payload)

    @filter.llm_tool(name='napcat_trans_group_file')
    async def napcat_trans_group_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /trans_group_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'trans_group_file', payload)

    @filter.llm_tool(name='napcat_translate_en2zh')
    async def napcat_translate_en2zh_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /translate_en2zh.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'translate_en2zh', payload)

    @filter.llm_tool(name='napcat_unknown')
    async def napcat_unknown_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /unknown.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'unknown', payload)

    @filter.llm_tool(name='napcat_upload_file_stream')
    async def napcat_upload_file_stream_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /upload_file_stream.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'upload_file_stream', payload)

    @filter.llm_tool(name='napcat_upload_group_file')
    async def napcat_upload_group_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /upload_group_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'upload_group_file', payload)

    @filter.llm_tool(name='napcat_upload_image_to_qun_album')
    async def napcat_upload_image_to_qun_album_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /upload_image_to_qun_album.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'upload_image_to_qun_album', payload)

    @filter.llm_tool(name='napcat_upload_private_file')
    async def napcat_upload_private_file_tool(
        self, event: AstrMessageEvent, payload: dict[str, Any] | None = None
    ):
        """Call NapCat/OneBot API: /upload_private_file.

        Args:
            payload(object): API request body. Field names must match the docs.

        Returns:
            str: JSON encoded API result.
        """
        return await self._call_napcat_api(event, 'upload_private_file', payload)

