from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_bitable_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "list_records":
            app_token = kwargs.get("app_token")
            table_id = kwargs.get("table_id")
            page_size = kwargs.get("page_size", 50)

            if not app_token or not table_id:
                return {"error": "app_token and table_id are required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([("page_size", str(page_size))]) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"查询记录失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            records = []
            for rec in data.get("items", []):
                records.append({
                    "record_id": rec.get("record_id"),
                    "fields": rec.get("fields"),
                })

            return {
                "records": records,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        elif action == "create_record":
            app_token = kwargs.get("app_token")
            table_id = kwargs.get("table_id")
            fields = kwargs.get("fields")

            if not app_token or not table_id:
                return {"error": "app_token and table_id are required"}
            if not fields:
                return {"error": "fields is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body({"fields": fields}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"创建记录失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            record = result.get("data", {}).get("record", {})
            return {"success": True, "record_id": record.get("record_id")}

        elif action == "update_record":
            app_token = kwargs.get("app_token")
            table_id = kwargs.get("table_id")
            record_id = kwargs.get("record_id")
            fields = kwargs.get("fields")

            if not app_token or not table_id or not record_id:
                return {"error": "app_token, table_id and record_id are required"}
            if not fields:
                return {"error": "fields is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.PUT) \
                .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body({"fields": fields}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"更新记录失败: {response.msg}"}

            return {"success": True, "record_id": record_id}

        elif action == "delete_record":
            app_token = kwargs.get("app_token")
            table_id = kwargs.get("table_id")
            record_id = kwargs.get("record_id")

            if not app_token or not table_id or not record_id:
                return {"error": "app_token, table_id and record_id are required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.DELETE) \
                .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"删除记录失败: {response.msg}"}

            return {"success": True}

        elif action == "list_tables":
            app_token = kwargs.get("app_token")

            if not app_token:
                return {"error": "app_token is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"查询数据表失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            tables = []
            for tbl in data.get("items", []):
                tables.append({
                    "table_id": tbl.get("table_id"),
                    "name": tbl.get("name"),
                })

            return {"tables": tables}

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_bitable",
        "description": """飞书多维表格管理工具。用于管理多维表格记录。

Actions:
- list_records: 列出记录（必填: app_token, table_id）
- create_record: 创建记录（必填: app_token, table_id, fields）
- update_record: 更新记录（必填: app_token, table_id, record_id, fields）
- delete_record: 删除记录（必填: app_token, table_id, record_id）
- list_tables: 列出数据表（必填: app_token）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_records", "create_record", "update_record", "delete_record", "list_tables"],
                    "description": "操作类型",
                },
                "app_token": {
                    "type": "string",
                    "description": "多维表格token",
                },
                "table_id": {
                    "type": "string",
                    "description": "数据表ID",
                },
                "record_id": {
                    "type": "string",
                    "description": "记录ID（update/delete时必填）",
                },
                "fields": {
                    "type": "object",
                    "description": "字段数据 {\"字段名\": \"值\"}",
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
