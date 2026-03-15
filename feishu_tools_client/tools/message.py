from __future__ import annotations

import json
from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, parse_message_content


def create_message_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        message_id: str | None = None,
        chat_id: str | None = None,
        receive_id_type: str | None = None,
        receive_id: str | None = None,
        msg_type: str = "text",
        content: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        sort_type: str = "ByCreateTimeDesc",
        start_time: str | None = None,
        end_time: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "get": lambda: _get_message(client, message_id),
            "list": lambda: _list_messages(
                client, chat_id, page_size, page_token, sort_type, start_time, end_time
            ),
            "send": lambda: _send_message(client, receive_id_type, receive_id, msg_type, content),
            "reply": lambda: _reply_message(client, message_id, msg_type, content),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: get, list, send, reply"}

        return await actions[action]()

    return FuncTool(
        name="feishu_message",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "list", "send", "reply"],
                    "description": "操作类型：get（获取单条消息）、list（列出聊天消息）、send（发送消息）、reply（回复消息）",
                },
                "message_id": {
                    "type": "string",
                    "description": "消息 ID（om_xxx 格式）。get 和 reply 操作必填",
                },
                "chat_id": {
                    "type": "string",
                    "description": "聊天 ID（oc_xxx 格式）。list 操作必填",
                },
                "receive_id_type": {
                    "type": "string",
                    "enum": ["open_id", "chat_id", "user_id", "union_id"],
                    "description": "接收者 ID 类型：open_id（用户）、chat_id（群聊）、user_id、union_id。send 操作必填",
                },
                "receive_id": {
                    "type": "string",
                    "description": "接收者 ID。send 操作必填。私聊填 open_id（ou_xxx），群聊填 chat_id（oc_xxx）",
                },
                "msg_type": {
                    "type": "string",
                    "enum": ["text", "post", "image", "file", "audio", "media", "interactive", "share_chat", "share_user"],
                    "default": "text",
                    "description": "消息类型：text（纯文本）、post（富文本）、image（图片）、file（文件）、interactive（消息卡片）等",
                },
                "content": {
                    "type": "string",
                    "description": "消息内容。text 类型直接填文本内容，其他类型需填 JSON 字符串。例如文本消息填 '你好'，图片消息填 '{\"image_key\":\"img_xxx\"}'",
                },
                "page_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "每页消息数量（默认 50，最大 50）",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记，用于获取下一页",
                },
                "sort_type": {
                    "type": "string",
                    "enum": ["ByCreateTimeDesc", "ByCreateTimeAsc"],
                    "default": "ByCreateTimeDesc",
                    "description": "排序方式：ByCreateTimeDesc（时间降序）、ByCreateTimeAsc（时间升序）",
                },
                "start_time": {
                    "type": "string",
                    "description": "起始时间（Unix 时间戳秒，或 ISO 8601 格式如 '2024-01-01T00:00:00+08:00'）",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间（Unix 时间戳秒，或 ISO 8601 格式）",
                },
            },
            "required": ["action"],
        },
        description="飞书消息工具。支持获取消息、列出聊天消息、发送消息、回复消息。\n\n"
        "Actions:\n"
        "- get：获取单条消息详情，需要 message_id\n"
        "- list：列出聊天中的消息，需要 chat_id\n"
        "- send：发送消息到私聊或群聊，需要 receive_id_type、receive_id、content\n"
        "- reply：回复指定消息，需要 message_id、content\n\n"
        "【重要】发送消息时，content 参数格式取决于 msg_type：\n"
        "- text：直接填文本内容，如 '你好'\n"
        "- image：填 JSON 字符串 '{\"image_key\":\"img_xxx\"}'\n"
        "- post：填富文本 JSON\n\n"
        "【安全提示】send 和 reply 操作会以机器人身份发送消息，调用前请确认发送内容。",
        handler=handler,
    )


async def _get_message(client: FeishuClient, message_id: str | None) -> dict[str, Any]:
    if not message_id:
        return {"error": "message_id is required for action=get"}

    try:
        result = await client.get(f"im/v1/messages/{message_id}")
        items = result.get("data", {}).get("items", [])
        if not items:
            return {"ok": True, "action": "get", "message_id": message_id, "found": False}

        item = items[0]
        sender = item.get("sender", {})
        sender_id = sender.get("id", "")
        sender_type = sender.get("sender_type", "")

        return {
            "ok": True,
            "action": "get",
            "found": True,
            "message_id": item.get("message_id", message_id),
            "msg_type": item.get("msg_type", ""),
            "content": parse_message_content(
                item.get("msg_type"), item.get("body", {}).get("content")
            ),
            "sender_id": sender_id,
            "sender_type": sender_type,
            "chat_id": item.get("chat_id", ""),
            "create_time": item.get("create_time", ""),
            "update_time": item.get("update_time", ""),
            "mentions": [
                {"id": m.get("id", ""), "name": m.get("name", ""), "type": m.get("type", "")}
                for m in item.get("mentions", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_messages(
    client: FeishuClient,
    chat_id: str | None,
    page_size: int,
    page_token: str | None,
    sort_type: str,
    start_time: str | None,
    end_time: str | None,
) -> dict[str, Any]:
    if not chat_id:
        return {"error": "chat_id is required for action=list"}

    try:
        page_size = min(max(page_size, 1), 50)
        params: dict[str, Any] = {
            "container_id_type": "chat",
            "container_id": chat_id,
            "sort_type": sort_type,
            "page_size": page_size,
        }
        if page_token:
            params["page_token"] = page_token
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        result = await client.get("im/v1/messages", params=params)
        items = result.get("data", {}).get("items", [])

        messages = []
        for item in items:
            if item.get("deleted"):
                continue
            sender = item.get("sender", {})
            messages.append({
                "message_id": item.get("message_id", ""),
                "msg_type": item.get("msg_type", ""),
                "content_preview": parse_message_content(
                    item.get("msg_type"), item.get("body", {}).get("content")
                ),
                "sender_id": sender.get("id", ""),
                "sender_type": sender.get("sender_type", ""),
                "create_time": item.get("create_time", ""),
                "chat_id": item.get("chat_id", ""),
            })

        return {
            "ok": True,
            "action": "list",
            "chat_id": chat_id,
            "total": len(messages),
            "messages": messages,
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _send_message(
    client: FeishuClient,
    receive_id_type: str | None,
    receive_id: str | None,
    msg_type: str,
    content: str | None,
) -> dict[str, Any]:
    if not receive_id_type or not receive_id:
        return {"error": "receive_id_type and receive_id are required for action=send"}
    if not content:
        return {"error": "content is required for action=send"}

    try:
        if msg_type == "text":
            content_json = json.dumps({"text": content})
        else:
            try:
                json.loads(content)
                content_json = content
            except json.JSONDecodeError:
                content_json = json.dumps({"text": content})

        result = await client.post(
            f"im/v1/messages?receive_id_type={receive_id_type}",
            data={
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": content_json,
            },
        )

        data = result.get("data", {})
        return {
            "ok": True,
            "action": "send",
            "message_id": data.get("message_id", ""),
            "chat_id": data.get("chat_id", ""),
            "create_time": data.get("create_time", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _reply_message(
    client: FeishuClient,
    message_id: str | None,
    msg_type: str,
    content: str | None,
) -> dict[str, Any]:
    if not message_id:
        return {"error": "message_id is required for action=reply"}
    if not content:
        return {"error": "content is required for action=reply"}

    try:
        if msg_type == "text":
            content_json = json.dumps({"text": content})
        else:
            try:
                json.loads(content)
                content_json = content
            except json.JSONDecodeError:
                content_json = json.dumps({"text": content})

        result = await client.post(
            f"im/v1/messages/{message_id}/reply",
            data={
                "content": content_json,
                "msg_type": msg_type,
            },
        )

        data = result.get("data", {})
        return {
            "ok": True,
            "action": "reply",
            "message_id": data.get("message_id", ""),
            "chat_id": data.get("chat_id", ""),
            "create_time": data.get("create_time", ""),
        }
    except Exception as e:
        return {"error": str(e)}
