from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_doc_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "create":
            title = kwargs.get("title")
            folder_token = kwargs.get("folder_token")

            if not title:
                return {"error": "title is required"}

            body = {"title": title}
            if folder_token:
                body["folder_token"] = folder_token

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/docx/v1/documents") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body(body) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"创建文档失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            doc = result.get("data", {}).get("document", {})
            return {
                "success": True,
                "document": {
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                }
            }

        elif action == "get":
            document_id = kwargs.get("document_id")

            if not document_id:
                return {"error": "document_id is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/docx/v1/documents/{document_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取文档失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            doc = result.get("data", {}).get("document", {})
            return {
                "document": {
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                    "revision_id": doc.get("revision_id"),
                }
            }

        elif action == "get_blocks":
            document_id = kwargs.get("document_id")
            page_size = kwargs.get("page_size", 50)

            if not document_id:
                return {"error": "document_id is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/docx/v1/documents/{document_id}/blocks") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("page_size", str(page_size))]) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取文档内容失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            blocks = []
            for block in data.get("items", []):
                blocks.append({
                    "block_id": block.get("block_id"),
                    "block_type": block.get("block_type"),
                    "text": block.get("text"),
                })

            return {"blocks": blocks, "has_more": data.get("has_more", False)}

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_doc",
        "description": """飞书文档工具。用于创建、获取飞书文档。

Actions:
- create: 创建文档（必填: title）
- get: 获取文档信息（必填: document_id）
- get_blocks: 获取文档内容块（必填: document_id）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "get", "get_blocks"],
                    "description": "操作类型",
                },
                "title": {
                    "type": "string",
                    "description": "文档标题（create时必填）",
                },
                "document_id": {
                    "type": "string",
                    "description": "文档ID（get/get_blocks时必填）",
                },
                "folder_token": {
                    "type": "string",
                    "description": "文件夹token（create时可选）",
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
