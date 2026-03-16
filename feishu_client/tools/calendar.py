from __future__ import annotations
import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient
from ...utils.time_utils import parse_time_to_timestamp, timestamp_to_datetime_str


def create_calendar_tool(client: FeishuClient):
    async def handler(action: str, **kwargs) -> dict[str, Any]:
        lark_client = client.get_client()

        if action == "create":
            summary = kwargs.get("summary")
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            description = kwargs.get("description")

            if not summary:
                return {"error": "summary is required"}
            if not start_time or not end_time:
                return {"error": "start_time and end_time are required"}

            start_ts = parse_time_to_timestamp(start_time)
            end_ts = parse_time_to_timestamp(end_time)
            if not start_ts or not end_ts:
                return {"error": "Invalid time format"}

            event_data = {
                "summary": summary,
                "start_time": {"timestamp": str(start_ts), "timezone": "Asia/Shanghai"},
                "end_time": {"timestamp": str(end_ts), "timezone": "Asia/Shanghai"},
            }
            if description:
                event_data["description"] = description

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.POST) \
                .uri("/open-apis/calendar/v4/calendars/primary/events") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .body(event_data) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"创建日程失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            event = result.get("data", {}).get("event", {})
            return {"success": True, "event_id": event.get("event_id")}

        elif action == "list":
            start_time = kwargs.get("start_time")
            end_time = kwargs.get("end_time")
            page_size = kwargs.get("page_size", 50)

            if not start_time or not end_time:
                return {"error": "start_time and end_time are required"}

            start_ts = parse_time_to_timestamp(start_time)
            end_ts = parse_time_to_timestamp(end_time)

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri("/open-apis/calendar/v4/calendars/primary/events") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .queries([
                    ("start_time", str(start_ts)),
                    ("end_time", str(end_ts)),
                    ("page_size", str(page_size)),
                ]) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"查询日程失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            data = result.get("data", {})
            events = []
            for evt in data.get("events", []):
                events.append({
                    "event_id": evt.get("event_id"),
                    "summary": evt.get("summary"),
                })

            return {"events": events, "has_more": data.get("has_more", False)}

        elif action == "get":
            event_id = kwargs.get("event_id")

            if not event_id:
                return {"error": "event_id is required"}

            request = lark.BaseRequest.builder() \
                .http_method(lark.HttpMethod.GET) \
                .uri(f"/open-apis/calendar/v4/calendars/primary/events/{event_id}") \
                .token_types({lark.AccessTokenType.TENANT}) \
                .build()

            response = await lark_client.arequest(request)

            if not response.success():
                return {"error": f"获取日程失败: {response.msg}"}

            result = json.loads(str(response.raw.content, lark.UTF_8))
            evt = result.get("data", {}).get("event", {})
            return {
                "event": {
                    "event_id": evt.get("event_id"),
                    "summary": evt.get("summary"),
                    "description": evt.get("description"),
                }
            }

        else:
            return {"error": f"Unknown action: {action}"}

    return {
        "name": "feishu_calendar",
        "description": """飞书日历日程管理工具。用于创建、查询日程。

Actions:
- create: 创建日程（必填: summary, start_time, end_time）
- list: 查询日程列表（必填: start_time, end_time）
- get: 获取日程详情（必填: event_id）

时间格式: ISO 8601 / RFC 3339（带时区）""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "get"],
                    "description": "操作类型",
                },
                "summary": {
                    "type": "string",
                    "description": "日程标题（create时必填）",
                },
                "event_id": {
                    "type": "string",
                    "description": "日程ID（get时必填）",
                },
                "start_time": {
                    "type": "string",
                    "description": "开始时间（create/list时必填）",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间（create/list时必填）",
                },
                "description": {
                    "type": "string",
                    "description": "日程描述",
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
