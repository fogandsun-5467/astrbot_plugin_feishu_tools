from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_drive_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "list":
            folder_token = kwargs.get("folder_token", "")
            page_size = kwargs.get("page_size", 20)

            queries = [("page_size", str(page_size))]
            if folder_token:
                queries.append(("folder_token", folder_token))

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri("/open-apis/drive/v1/files") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries(queries) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取文件列表失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            files = []
            for f in data.get("files", []):
                files.append({
                    "token": f.get("token"),
                    "name": f.get("name"),
                    "type": f.get("type"),
                    "size": f.get("size"),
                })

            return {
                "files": files,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        elif action == "create_folder":
            folder_token = kwargs.get("folder_token", "")
            name = kwargs.get("name")

            if not name:
                return {"error": "name is required"}

            body = {"name": name, "type": "folder"}
            if folder_token:
                body["folder_token"] = folder_token

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/drive/v1/files") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body(body) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"创建文件夹失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            folder = result.get("data", {}).get("file", {})
            return {
                "success": True,
                "folder": {
                    "token": folder.get("token"),
                    "name": folder.get("name"),
                }
            }

        elif action == "get":
            token = kwargs.get("token")

            if not token:
                return {"error": "token is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/drive/v1/files/{token}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取文件信息失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            f = result.get("data", {}).get("file", {})
            return {
                "file": {
                    "token": f.get("token"),
                    "name": f.get("name"),
                    "type": f.get("type"),
                    "size": f.get("size"),
                }
            }

        elif action == "delete":
            token = kwargs.get("token")

            if not token:
                return {"error": "token is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.DELETE) \
                .uri(f"/open-apis/drive/v1/files/{token}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"删除文件失败: {response.msg}"}

            return {"success": True}

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_drive",
        "description": """飞书云盘管理工具。用于浏览文件夹、创建文件夹、获取文件信息、删除文件。

Actions:
- list: 列出文件（可选: folder_token）
- create_folder: 创建文件夹（必填: name）
- get: 获取文件信息（必填: token）
- delete: 删除文件（必填: token）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create_folder", "get", "delete"],
                    "description": "操作类型",
                },
                "folder_token": {
                    "type": "string",
                    "description": "文件夹token",
                },
                "name": {
                    "type": "string",
                    "description": "文件夹名称（create_folder时必填）",
                },
                "token": {
                    "type": "string",
                    "description": "文件token（get/delete时必填）",
                },
                "page_size": {
                    "type": "number",
                    "description": "每页数量（默认20）",
                },
            },
            "required": ["action"],
        },
        "handler": handler,
    }
