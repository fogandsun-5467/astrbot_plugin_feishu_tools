from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient


def create_sheets_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "get":
            spreadsheet_token = kwargs.get("spreadsheet_token")

            if not spreadsheet_token:
                return {"error": "spreadsheet_token is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取电子表格失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            spreadsheet = result.get("data", {}).get("spreadsheet", {})
            return {
                "spreadsheet": {
                    "spreadsheet_token": spreadsheet.get("spreadsheet_token"),
                    "title": spreadsheet.get("title"),
                    "sheet_count": spreadsheet.get("sheet_count"),
                }
            }

        elif action == "read_cells":
            spreadsheet_token = kwargs.get("spreadsheet_token")
            range_ = kwargs.get("range")

            if not spreadsheet_token:
                return {"error": "spreadsheet_token is required"}
            if not range_:
                return {"error": "range is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"读取单元格失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            value_range = result.get("data", {}).get("valueRange", {})
            return {
                "values": value_range.get("values", [])
            }

        elif action == "write_cells":
            spreadsheet_token = kwargs.get("spreadsheet_token")
            range_ = kwargs.get("range")
            values = kwargs.get("values")

            if not spreadsheet_token:
                return {"error": "spreadsheet_token is required"}
            if not range_:
                return {"error": "range is required"}
            if not values:
                return {"error": "values is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.PUT) \
                .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body({"valueRange": {"range": range_, "values": values}}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"写入单元格失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            return {"success": True, "updated_cells": data.get("updatedCells", len(values))}

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_sheets",
        "description": """飞书电子表格工具。用于读取和写入电子表格数据。

Actions:
- get: 获取电子表格信息（必填: spreadsheet_token）
- read_cells: 读取单元格数据（必填: spreadsheet_token, range）
- write_cells: 写入单元格数据（必填: spreadsheet_token, range, values）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get", "read_cells", "write_cells"],
                    "description": "操作类型",
                },
                "spreadsheet_token": {
                    "type": "string",
                    "description": "电子表格token",
                },
                "range": {
                    "type": "string",
                    "description": "单元格范围（如 Sheet1!A1:B2）",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "array"},
                    "description": "单元格值数组（write_cells时必填）",
                },
            },
            "required": ["action", "spreadsheet_token"],
        },
        "handler": handler,
    }
