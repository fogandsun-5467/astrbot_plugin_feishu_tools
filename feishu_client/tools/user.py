from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_user_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()
        
        if action == "get":
            user_id = kwargs.get("user_id")
            user_id_type = kwargs.get("user_id_type", "open_id")
            
            if not user_id:
                return {"error": "user_id is required for get action"}
            
            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/contact/v3/users/{user_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("user_id_type", user_id_type)]) \
                .build()
            
            response = await lark_client.arequest(request)
            
            if not response.success():
                return {"error": f"获取用户信息失败: {response.msg}"}
            
            result = json.loads(str(response.raw.content, lark.UTF_8))
            user = result.get("data", {}).get("user", {})
            return {
                "open_id": user.get("open_id"),
                "union_id": user.get("union_id"),
                "name": user.get("name"),
                "en_name": user.get("en_name"),
                "department_ids": user.get("department_ids"),
            }
        
        elif action == "search":
            query = kwargs.get("query")
            page_size = kwargs.get("page_size", 20)
            
            if not query:
                return {"error": "query is required for search action"}
            
            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/contact/v3/users/find_by_department") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("user_id_type", "open_id"), ("page_size", str(page_size))]) \
                .body({"query": query}) \
                .build()
            
            response = await lark_client.arequest(request)
            
            if not response.success():
                return {"error": f"搜索用户失败: {response.msg}"}
            
            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            users = []
            for u in data.get("items", []):
                users.append({
                    "open_id": u.get("open_id"),
                    "name": u.get("name"),
                })
            
            return {"users": users, "has_more": data.get("has_more", False)}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    return {
        "name": "feishu_user",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "search"],
                    "description": "操作类型",
                },
                "user_id": {
                    "type": "string",
                    "description": "用户ID（get时必填）",
                },
                "user_id_type": {
                    "type": "string",
                    "description": "用户ID类型（默认open_id）",
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词（search时必填）",
                },
                "page_size": {
                    "type": "number",
                    "description": "每页数量（默认20）",
                },
            },
            "required": ["action"],
        },
        "description": "飞书用户查询工具.用于获取用户信息和搜索用户.",
        "handler": handler,
    }
