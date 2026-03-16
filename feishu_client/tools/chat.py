from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_chat_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "get":
            chat_id = kwargs.get("chat_id")

            if not chat_id:
                return {"error": "chat_id is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/im/v1/chats/{chat_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取群聊信息失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            chat = result.get("data", {})
            return {
                "chat": {
                    "chat_id": chat.get("chat_id"),
                    "name": chat.get("name"),
                    "owner_id": chat.get("owner_id"),
                    "owner_id_type": chat.get("owner_id_type"),
                    "member_count": chat.get("member_count"),
                }
            }

        elif action == "list":
            page_size = kwargs.get("page_size", 50)

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri("/open-apis/im/v1/chats") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("page_size", str(page_size))]) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取群聊列表失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            chats = []
            for c in data.get("items", []):
                chats.append({
                    "chat_id": c.get("chat_id"),
                    "name": c.get("name"),
                })

            return {
                "chats": chats,
                "has_more": data.get("has_more", False),
            }

        elif action == "create":
            name = kwargs.get("name")
            user_id_list = kwargs.get("user_id_list", [])
            owner_id = kwargs.get("owner_id")

            if not name:
                return {"error": "name is required"}

            body = {"name": name, "user_id_list": user_id_list}
            if owner_id:
                body["owner_id"] = owner_id

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/im/v1/chats") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body(body) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"创建群聊失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            chat = result.get("data", {}).get("chat", {})
            return {
                "success": True,
                "chat": {
                    "chat_id": chat.get("chat_id"),
                    "name": chat.get("name"),
                }
            }

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_chat",
        "description": """飞书群聊管理工具。用于获取群聊信息、创建群聊、获取群聊列表。

Actions:
- get: 获取群聊信息（必填: chat_id）
- list: 获取群聊列表
- create: 创建群聊（必填: name）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "list", "create"],
                    "description": "操作类型",
                },
                "chat_id": {
                    "type": "string",
                    "description": "群聊ID（get时必填）",
                },
                "name": {
                    "type": "string",
                    "description": "群聊名称（create时必填）",
                },
                "user_id_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "用户ID列表（create时可选）",
                },
                "owner_id": {
                    "type": "string",
                    "description": "群主ID（create时可选）",
                },
                "page_size": {
                    "type": "number",
                    "description": "每页数量（默认50）",
                },
            },
            "required": ["action"],
        },
        "handler": handler,
    }
