import json
from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


BLOCK_TYPE_NAMES: dict[int, str] = {
    1: "Page",
    2: "Text",
    3: "Heading1",
    4: "Heading2",
    5: "Heading3",
    12: "Bullet",
    13: "Ordered",
    14: "Code",
    15: "Quote",
    17: "Todo",
    18: "Bitable",
    21: "Diagram",
    22: "Divider",
    23: "File",
    27: "Image",
    30: "Sheet",
    31: "Table",
    32: "TableCell",
}

STRUCTURED_BLOCK_TYPES = {14, 18, 21, 23, 27, 30, 31, 32}


def create_chat_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        chat_id: str | None = None,
        block_id: str | None = None,
        content: str | None = None,
        name: str | None = None,
        user_ids: list[str] | None = None,
        description: str | None = None,
        greeting: str | None = None,
        user_id_type: str = "open_id",
        member_id_type: str = "open_id",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "get_announcement_info": lambda: _get_announcement(client, chat_id, info_only=True),
            "get_announcement": lambda: _get_announcement(client, chat_id, info_only=False),
            "list_announcement_blocks": lambda: _list_announcement_blocks(client, chat_id),
            "get_announcement_block": lambda: _get_announcement_block(client, chat_id, block_id),
            "write_announcement": lambda: _write_announcement(client, chat_id, content),
            "append_announcement": lambda: _append_announcement(client, chat_id, content),
            "update_announcement_block": lambda: _update_announcement_block(client, chat_id, block_id, content),
            "create_chat": lambda: _create_chat(client, name, user_ids, description, user_id_type),
            "add_members": lambda: _add_members(client, chat_id, user_ids, member_id_type),
            "check_bot_in_chat": lambda: _check_bot_in_chat(client, chat_id),
            "delete_chat": lambda: _delete_chat(client, chat_id),
            "create_session_chat": lambda: _create_session_chat(client, name, user_ids, greeting, description, user_id_type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_chat",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get_announcement_info",
                        "get_announcement",
                        "list_announcement_blocks",
                        "get_announcement_block",
                        "write_announcement",
                        "append_announcement",
                        "update_announcement_block",
                        "create_chat",
                        "add_members",
                        "check_bot_in_chat",
                        "delete_chat",
                        "create_session_chat",
                    ],
                    "description": "Action to perform",
                },
                "chat_id": {"type": "string", "description": "Feishu chat ID (e.g., oc_xxx)"},
                "block_id": {"type": "string", "description": "Announcement block ID"},
                "content": {"type": "string", "description": "Content to write or append"},
                "name": {"type": "string", "description": "Chat name for create_chat/create_session_chat"},
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs (open_id)",
                },
                "description": {"type": "string", "description": "Chat description"},
                "greeting": {"type": "string", "description": "Greeting message for create_session_chat"},
                "user_id_type": {
                    "type": "string",
                    "enum": ["open_id", "user_id", "union_id"],
                    "default": "open_id",
                },
                "member_id_type": {
                    "type": "string",
                    "enum": ["open_id", "user_id", "union_id", "app_id"],
                    "default": "open_id",
                },
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark群聊工具】当用户提到飞书群聊、群公告、创建群、添加成员、群管理时使用此工具。支持群公告读写、创建群聊、管理群成员。\n\n"
        "Actions:\n"
        "- get_announcement_info：获取群公告基本信息，需要 chat_id\n"
        "- get_announcement：获取群公告完整内容，需要 chat_id\n"
        "- list_announcement_blocks：列出群公告所有 Block，需要 chat_id\n"
        "- get_announcement_block：获取群公告单个 Block，需要 chat_id、block_id\n"
        "- write_announcement：写入群公告，需要 chat_id、content\n"
        "- append_announcement：追加群公告内容，需要 chat_id、content\n"
        "- update_announcement_block：更新群公告 Block，需要 chat_id、block_id、content\n"
        "- create_chat：创建群聊，需要 name\n"
        "- add_members：添加群成员，需要 chat_id、user_ids\n"
        "- check_bot_in_chat：检查机器人是否在群中，需要 chat_id\n"
        "- delete_chat：解散群聊，需要 chat_id\n"
        "- create_session_chat：创建群聊并发送问候消息，需要 name、user_ids\n\n"
        "【重要】chat_id 格式为 oc_xxx，user_ids 使用 open_id 格式（ou_xxx）。",
        handler=handler,
    )


def _require(value: Any, field: str) -> str:
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field} is required")
    return value


async def _get_announcement(client: FeishuClient, chat_id: str | None, info_only: bool) -> dict[str, Any]:
    if not chat_id:
        return {"error": "chat_id is required"}

    try:
        result = await client.get(f"docx/v1/chats/{chat_id}/announcement")
        data = result.get("data", {})
        announcement_type = data.get("announcement_type", "docx")

        if announcement_type == "doc":
            doc_result = await client.get(f"im/v1/chats/{chat_id}/announcement")
            return {
                "announcement_type": "doc",
                **doc_result.get("data", {}),
            }

        blocks_result = await client.get(f"docx/v1/chats/{chat_id}/announcement/blocks")
        blocks = blocks_result.get("data", {}).get("items", [])

        block_counts: dict[str, int] = {}
        structured_types: list[str] = []

        for b in blocks:
            block_type = b.get("block_type", 0)
            name = BLOCK_TYPE_NAMES.get(block_type, f"type_{block_type}")
            block_counts[name] = block_counts.get(name, 0) + 1
            if block_type in STRUCTURED_BLOCK_TYPES and name not in structured_types:
                structured_types.append(name)

        response = {
            "announcement_type": "docx",
            "info": data,
            "blocks": blocks,
            "block_count": len(blocks),
            "block_types": block_counts,
        }

        if structured_types:
            response["hint"] = f"This announcement contains {', '.join(structured_types)} which are NOT included in basic info. Use action: 'list_announcement_blocks' to get full content."

        return response
    except Exception as e:
        return {"error": str(e)}


async def _list_announcement_blocks(client: FeishuClient, chat_id: str | None) -> dict[str, Any]:
    if not chat_id:
        return {"error": "chat_id is required"}

    try:
        result = await client.get(f"docx/v1/chats/{chat_id}/announcement/blocks")
        return {"blocks": result.get("data", {}).get("items", [])}
    except Exception as e:
        return {"error": str(e)}


async def _get_announcement_block(client: FeishuClient, chat_id: str | None, block_id: str | None) -> dict[str, Any]:
    if not chat_id or not block_id:
        return {"error": "chat_id and block_id are required"}

    try:
        result = await client.get(f"docx/v1/chats/{chat_id}/announcement/blocks/{block_id}")
        return {"block": result.get("data", {}).get("block")}
    except Exception as e:
        return {"error": str(e)}


async def _write_announcement(client: FeishuClient, chat_id: str | None, content: str | None) -> dict[str, Any]:
    if not chat_id or not content:
        return {"error": "chat_id and content are required"}

    try:
        current = await _get_announcement(client, chat_id, info_only=False)
        announcement_type = current.get("announcement_type", "docx")

        if announcement_type == "doc":
            doc_result = await client.get(f"im/v1/chats/{chat_id}/announcement")
            revision = doc_result.get("data", {}).get("revision")
            if not revision:
                return {"error": "Failed to get current announcement revision"}

            try:
                result = await client.patch(
                    f"im/v1/chats/{chat_id}/announcement",
                    data={"revision": revision, "requests": [content]},
                )
            except Exception:
                result = await client.patch(
                    f"im/v1/chats/{chat_id}/announcement",
                    data={"content": content, "revision": revision},
                )

            return {"success": True, "announcement_type": "doc", **result.get("data", {})}
        else:
            blocks = current.get("blocks", [])
            page_block = next((b for b in blocks if b.get("block_type") == 1), None)
            if not page_block or not page_block.get("block_id"):
                return {"error": "Could not find the Page root block for docx announcement"}

            result = await client.post(
                f"docx/v1/chats/{chat_id}/announcement/blocks/{page_block['block_id']}/children",
                data={
                    "children": [{
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": content}}]},
                    }]
                },
            )
            return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _append_announcement(client: FeishuClient, chat_id: str | None, content: str | None) -> dict[str, Any]:
    if not chat_id or not content:
        return {"error": "chat_id and content are required"}

    try:
        current = await _get_announcement(client, chat_id, info_only=False)
        announcement_type = current.get("announcement_type", "docx")

        if announcement_type == "doc":
            existing = current.get("content", "")
            new_content = f"{existing}\n{content}"
            return await _write_announcement(client, chat_id, new_content)
        else:
            return await _write_announcement(client, chat_id, content)
    except Exception as e:
        return {"error": str(e)}


async def _update_announcement_block(client: FeishuClient, chat_id: str | None, block_id: str | None, content: str | None) -> dict[str, Any]:
    if not chat_id or not block_id or not content:
        return {"error": "chat_id, block_id, and content are required"}

    try:
        info_result = await client.get(f"docx/v1/chats/{chat_id}/announcement")
        revision_id = info_result.get("data", {}).get("revision_id")

        result = await client.patch(
            f"docx/v1/chats/{chat_id}/announcement/blocks",
            params={"revision_id": revision_id},
            data={
                "requests": [{
                    "block_id": block_id,
                    "update_text_elements": {"elements": [{"text_run": {"content": content}}]},
                }]
            },
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _create_chat(
    client: FeishuClient,
    name: str | None,
    user_ids: list[str] | None,
    description: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not name:
        return {"error": "name is required"}

    try:
        data: dict[str, Any] = {"name": name}
        if user_ids:
            data["user_id_list"] = user_ids
        if description:
            data["description"] = description

        result = await client.post("im/v1/chats", data=data, json_data={"user_id_type": user_id_type})
        return {"success": True, "chat_id": result.get("data", {}).get("chat_id"), **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _add_members(
    client: FeishuClient,
    chat_id: str | None,
    user_ids: list[str] | None,
    member_id_type: str,
) -> dict[str, Any]:
    if not chat_id or not user_ids:
        return {"error": "chat_id and user_ids are required"}

    try:
        result = await client.post(
            f"im/v1/chats/{chat_id}/members",
            data={"id_list": user_ids},
            json_data={"member_id_type": member_id_type},
        )
        return {"success": True, "chat_id": chat_id, "added_user_ids": user_ids, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _check_bot_in_chat(client: FeishuClient, chat_id: str | None) -> dict[str, Any]:
    if not chat_id:
        return {"error": "chat_id is required"}

    try:
        result = await client.get(f"im/v1/chats/{chat_id}")
        return {"success": True, "chat_id": chat_id, "in_chat": True, "chat_info": result.get("data", {})}
    except Exception as e:
        if "90003" in str(e):
            return {"success": True, "chat_id": chat_id, "in_chat": False, "error": "Bot is not in this chat"}
        return {"error": str(e)}


async def _delete_chat(client: FeishuClient, chat_id: str | None) -> dict[str, Any]:
    if not chat_id:
        return {"error": "chat_id is required"}

    try:
        result = await client.delete(f"im/v1/chats/{chat_id}")
        return {"success": True, "chat_id": chat_id, "message": "Chat has been successfully disbanded/deleted", **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _create_session_chat(
    client: FeishuClient,
    name: str | None,
    user_ids: list[str] | None,
    greeting: str | None,
    description: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not name or not user_ids:
        return {"error": "name and user_ids are required"}

    try:
        create_result = await _create_chat(client, name, user_ids, description, user_id_type)
        chat_id = create_result.get("chat_id")

        if not chat_id:
            return {"success": False, "error": "Failed to create chat - no chat_id returned", "create_result": create_result}

        greeting_msg = greeting or "Hello! I've created this group chat for us to collaborate."
        try:
            await client.post(
                "im/v1/messages",
                data={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": json.dumps({"text": greeting_msg}),
                },
                json_data={"receive_id_type": "chat_id"},
            )
        except Exception as e:
            return {"success": True, "chat_id": chat_id, "create_result": create_result, "message_error": str(e)}

        return {"success": True, "chat_id": chat_id, "create_result": create_result}
    except Exception as e:
        return {"error": str(e)}
