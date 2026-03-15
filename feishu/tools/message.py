import json
from typing import Any

from astrbot.core.agent.tool import FunctionTool
from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, parse_message_content


def create_message_tool(client: FeishuClient) -> FunctionTool:
    async def handler(
        action: str,
        message_id: str | None = None,
        chat_id: str | None = None,
        page_size: int = 10,
        sort_type: str = "ByCreateTimeDesc",
        start_time: str | None = None,
        end_time: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        if action == "get":
            if not message_id:
                return {"error": "message_id is required for action=get"}
            return await _get_message(client, message_id)
        elif action == "list":
            if not chat_id:
                return {"error": "chat_id is required for action=list"}
            return await _list_messages(
                client, chat_id, page_size, sort_type, start_time, end_time
            )
        else:
            return {"error": f"Unknown action: {action}"}

    return FuncTool(
        name="feishu_message",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "list"],
                    "description": "Action to perform: 'get' to retrieve a single message, 'list' to list messages in a chat",
                },
                "message_id": {
                    "type": "string",
                    "description": "Feishu message ID (e.g., om_xxx). Required for action=get",
                },
                "chat_id": {
                    "type": "string",
                    "description": "Feishu chat ID (e.g., oc_xxx). Required for action=list",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Number of messages to return (default: 10, max: 50)",
                    "default": 10,
                },
                "sort_type": {
                    "type": "string",
                    "enum": ["ByCreateTimeDesc", "ByCreateTimeAsc"],
                    "description": "Sort order (default: ByCreateTimeDesc)",
                    "default": "ByCreateTimeDesc",
                },
                "start_time": {
                    "type": "string",
                    "description": "Unix timestamp in seconds for start time filter",
                },
                "end_time": {
                    "type": "string",
                    "description": "Unix timestamp in seconds for end time filter",
                },
            },
            "required": ["action"],
        },
        description="Feishu message reading tool. Get a single message by ID or list recent messages in a chat. Use when user mentions reading messages, chat history, or finding previous messages.",
        handler=handler,
    )


async def _get_message(client: FeishuClient, message_id: str) -> dict[str, Any]:
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
                {"id": m.get("id", ""), "name": m.get("name", "")}
                for m in item.get("mentions", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_messages(
    client: FeishuClient,
    chat_id: str,
    page_size: int,
    sort_type: str,
    start_time: str | None,
    end_time: str | None,
) -> dict[str, Any]:
    try:
        page_size = min(max(page_size, 1), 50)
        params = {
            "container_id_type": "chat",
            "container_id": chat_id,
            "sort_type": sort_type,
            "page_size": page_size,
        }
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
        }
    except Exception as e:
        return {"error": str(e)}
