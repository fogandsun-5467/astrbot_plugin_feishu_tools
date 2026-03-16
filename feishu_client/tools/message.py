from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_message_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "send":
            receive_id = kwargs.get("receive_id")
            receive_id_type = kwargs.get("receive_id_type", "open_id")
            msg_type = kwargs.get("msg_type", "text")
            content = kwargs.get("content")

            if not receive_id or not content:
                return {"error": "receive_id and content are required"}

            if msg_type == "text":
                content_str = json.dumps({"text": content})
            else:
                content_str = json.dumps(content) if isinstance(content, dict) else content

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/im/v1/messages") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("receive_id_type", receive_id_type)]) \
                .body({"receive_id": receive_id, "msg_type": msg_type, "content": content_str}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"发送消息失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            return {"success": True, "message_id": result.get("data", {}).get("message_id")}

        elif action == "reply":
            message_id = kwargs.get("message_id")
            msg_type = kwargs.get("msg_type", "text")
            content = kwargs.get("content")

            if not message_id or not content:
                return {"error": "message_id and content are required"}

            if msg_type == "text":
                content_str = json.dumps({"text": content})
            else:
                content_str = json.dumps(content) if isinstance(content, dict) else content

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri(f"/open-apis/im/v1/messages/{message_id}/reply") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body({"msg_type": msg_type, "content": content_str}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"回复消息失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            return {"success": True, "message_id": result.get("data", {}).get("message_id")}

        elif action == "get":
            message_id = kwargs.get("message_id")

            if not message_id:
                return {"error": "message_id is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/im/v1/messages/{message_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取消息失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            items = data.get("items", [])
            if not items:
                return {"error": "消息不存在"}

            msg = items[0]
            return {
                "message": {
                    "message_id": msg.get("message_id"),
                    "msg_type": msg.get("msg_type"),
                    "content": msg.get("body", {}).get("content"),
                    "create_time": msg.get("create_time"),
                }
            }

        elif action == "list":
            container_id = kwargs.get("container_id")
            container_id_type = kwargs.get("container_id_type", "chat")
            page_size = kwargs.get("page_size", 50)
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")

            if not container_id:
                return {"error": "container_id is required"}

            queries = [
                ("container_id_type", container_id_type),
                ("container_id", container_id),
                ("page_size", str(page_size)),
            ]
            if start_time:
                queries.append(("start_time", str(start_time)))
            if end_time:
                queries.append(("end_time", str(end_time)))

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri("/open-apis/im/v1/messages") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries(queries) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取消息列表失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            messages = []
            for msg in data.get("items", []):
                messages.append({
                    "message_id": msg.get("message_id"),
                    "msg_type": msg.get("msg_type"),
                    "create_time": msg.get("create_time"),
                })

            return {
                "messages": messages,
                "has_more": data.get("has_more", False),
            }

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_message",
        "description": """飞书消息管理工具。用于发送、回复、读取消息。

Actions:
- send: 发送消息（必填: receive_id, content）
- reply: 回复消息（必填: message_id, content）
- get: 获取消息详情（必填: message_id）
- list: 获取消息列表（必填: container_id）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["send", "reply", "get", "list"],
                    "description": "操作类型",
                },
                "receive_id": {
                    "type": "string",
                    "description": "接收者ID（send时必填）",
                },
                "receive_id_type": {
                    "type": "string",
                    "description": "接收者类型（open_id/user_id/union_id/chat_id，默认open_id）",
                },
                "message_id": {
                    "type": "string",
                    "description": "消息ID（reply/get时必填）",
                },
                "msg_type": {
                    "type": "string",
                    "description": "消息类型（text/post/image/file等，默认text）",
                },
                "content": {
                    "type": "string",
                    "description": "消息内容（send/reply时必填）",
                },
                "container_id": {
                    "type": "string",
                    "description": "容器ID（list时必填，通常为chat_id）",
                },
                "container_id_type": {
                    "type": "string",
                    "description": "容器类型（默认chat）",
                },
                "page_size": {
                    "type": "number",
                    "description": "每页数量（默认50）",
                },
                "start_time": {
                    "type": "string",
                    "description": "开始时间戳（list时可选）",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间戳（list时可选）",
                },
            },
            "required": ["action"],
        },
        "handler": handler,
    }
