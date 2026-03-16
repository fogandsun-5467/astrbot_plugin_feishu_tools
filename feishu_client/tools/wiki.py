from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_wiki_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> str:
        lark_client = client.get_client()

        if action == "list_spaces":
            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/wiki/v2/spaces") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"查询空间失败: {response.msg}", "code": response.code}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                spaces = []
                for space in data.get("items", []):
                    spaces.append({
                        "space_id": space.get("space_id"),
                        "name": space.get("name"),
                        "description": space.get("description"),
                    })

                return json.dumps({
                    "spaces": spaces,
                    "has_more": data.get("has_more", False),
                    "page_token": data.get("page_token"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"查询空间异常: {str(e)}"}, ensure_ascii=False)

        elif action == "list_nodes":
            space_id = kwargs.get("space_id")
            if not space_id:
                return json.dumps({"error": "space_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/wiki/v2/spaces/nodes") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("space_id", space_id)]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"查询节点失败: {response.msg}", "code": response.code}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                nodes = []
                for node in data.get("items", []):
                    nodes.append({
                        "node_token": node.get("node_token"),
                        "title": node.get("title"),
                        "obj_type": node.get("obj_type"),
                    })

                return json.dumps({
                    "nodes": nodes,
                    "has_more": data.get("has_more", False),
                    "page_token": data.get("page_token"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"查询节点异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    return {
        "name": "feishu_wiki",
        "description": """飞书知识库管理工具。用于查询知识库空间和节点。

Actions:
- list_spaces: 查询知识库空间列表
- list_nodes: 查询指定空间的节点列表（必填: space_id）
""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_spaces", "list_nodes"],
                    "description": "操作类型",
                },
                "space_id": {
                    "type": "string",
                    "description": "空间ID（list_nodes时必填）",
                },
            },
            "required": ["action"],
        },
        "handler": handler,
    }
