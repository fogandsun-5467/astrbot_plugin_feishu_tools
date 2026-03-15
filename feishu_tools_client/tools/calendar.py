from __future__ import annotations

from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, parse_time_to_timestamp_ms, unix_timestamp_to_iso8601


def create_calendar_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        calendar_id: str | None = None,
        event_id: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        start_time: dict | None = None,
        end_time: dict | None = None,
        location: str | None = None,
        reminders: list | None = None,
        attendees: list | None = None,
        visibility: str | None = None,
        color: int | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        sync_token: str | None = None,
        start_time_filter: str | None = None,
        end_time_filter: str | None = None,
        user_id_type: str = "open_id",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "create": lambda: _create_calendar(client, summary, description, color),
            "get": lambda: _get_calendar(client, calendar_id),
            "list": lambda: _list_calendars(client, page_size, page_token, sync_token),
            "update": lambda: _update_calendar(client, calendar_id, summary, description, color),
            "delete": lambda: _delete_calendar(client, calendar_id),
            "subscribe": lambda: _subscribe_calendar(client, calendar_id),
            "unsubscribe": lambda: _unsubscribe_calendar(client, calendar_id),
            "create_event": lambda: _create_event(
                client, calendar_id, summary, description, start_time, end_time, location, reminders, attendees, visibility, user_id_type
            ),
            "get_event": lambda: _get_event(client, calendar_id, event_id, user_id_type),
            "list_events": lambda: _list_events(
                client, calendar_id, page_size, page_token, sync_token, start_time_filter, end_time_filter, user_id_type
            ),
            "update_event": lambda: _update_event(
                client, calendar_id, event_id, summary, description, start_time, end_time, location, reminders, attendees, visibility, user_id_type
            ),
            "delete_event": lambda: _delete_event(client, calendar_id, event_id),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_calendar",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create",
                        "get",
                        "list",
                        "update",
                        "delete",
                        "subscribe",
                        "unsubscribe",
                        "create_event",
                        "get_event",
                        "list_events",
                        "update_event",
                        "delete_event",
                    ],
                    "description": "操作类型",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "日历 ID，除 create/list 外的日历操作和所有事件操作必填",
                },
                "event_id": {
                    "type": "string",
                    "description": "事件 ID，get_event/update_event/delete_event 操作必填",
                },
                "summary": {
                    "type": "string",
                    "description": "日历/事件标题，create 操作必填",
                },
                "description": {
                    "type": "string",
                    "description": "日历/事件描述",
                },
                "start_time": {
                    "type": "object",
                    "description": "事件开始时间，格式：{date: '2024-01-01'} 或 {timestamp: 1704067200000, timezone: 'Asia/Shanghai'}",
                },
                "end_time": {
                    "type": "object",
                    "description": "事件结束时间，格式同 start_time",
                },
                "location": {
                    "type": "string",
                    "description": "事件地点",
                },
                "reminders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "minutes": {"type": "integer"},
                            "method": {"type": "string", "enum": ["popup", "email"]},
                        },
                    },
                    "description": "提醒设置，格式：[{minutes: 30, method: 'popup'}]",
                },
                "attendees": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "is_optional": {"type": "boolean"},
                        },
                    },
                    "description": "参会人列表，格式：[{user_id: 'ou_xxx', is_optional: false}]",
                },
                "visibility": {
                    "type": "string",
                    "enum": ["default", "public", "private"],
                    "description": "事件可见性：default（默认）、public（公开）、private（私密）",
                },
                "color": {
                    "type": "integer",
                    "description": "日历颜色，范围 0-23",
                },
                "page_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "每页数量",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记",
                },
                "sync_token": {
                    "type": "string",
                    "description": "同步标记，用于增量同步",
                },
                "start_time_filter": {
                    "type": "string",
                    "description": "事件开始时间筛选（ISO 8601 格式），list_events 操作可选",
                },
                "end_time_filter": {
                    "type": "string",
                    "description": "事件结束时间筛选（ISO 8601 格式），list_events 操作可选",
                },
                "user_id_type": {
                    "type": "string",
                    "enum": ["open_id", "user_id", "union_id"],
                    "default": "open_id",
                    "description": "用户 ID 类型",
                },
            },
            "required": ["action"],
        },
        description="飞书日历工具。支持创建/管理日历和日程事件。\n\n"
        "Actions:\n"
        "- create：创建日历，需要 summary\n"
        "- get：获取日历信息，需要 calendar_id\n"
        "- list：列出我的日历\n"
        "- update：更新日历，需要 calendar_id\n"
        "- delete：删除日历，需要 calendar_id\n"
        "- subscribe：订阅日历，需要 calendar_id\n"
        "- unsubscribe：取消订阅日历，需要 calendar_id\n"
        "- create_event：创建日程，需要 calendar_id、summary、start_time、end_time\n"
        "- get_event：获取日程详情，需要 calendar_id、event_id\n"
        "- list_events：列出日程，需要 calendar_id\n"
        "- update_event：更新日程，需要 calendar_id、event_id\n"
        "- delete_event：删除日程，需要 calendar_id、event_id\n\n"
        "【时间格式】start_time/end_time 使用 {date: 'YYYY-MM-DD'} 表示全天事件，或 {timestamp: 毫秒时间戳, timezone: '时区'} 表示具体时间。",
        handler=handler,
    )


def _convert_event_time(time_obj: dict | None) -> dict | None:
    if not time_obj:
        return None

    if time_obj.get("date"):
        return {"date": time_obj["date"]}

    if time_obj.get("timestamp"):
        ts = time_obj["timestamp"]
        if isinstance(ts, str):
            ts = parse_time_to_timestamp_ms(ts)
        if ts:
            return {
                "timestamp": ts,
                "timezone": time_obj.get("timezone", "Asia/Shanghai"),
            }

    return None


def _format_event_time(time_obj: dict | None) -> dict | None:
    if not time_obj:
        return None

    if time_obj.get("date"):
        return {"date": time_obj["date"]}

    if time_obj.get("timestamp"):
        return {
            "timestamp": unix_timestamp_to_iso8601(time_obj["timestamp"]),
            "timezone": time_obj.get("timezone", "Asia/Shanghai"),
        }

    return None


def _format_event(event: dict) -> dict:
    if not event:
        return {}

    return {
        "event_id": event.get("event_id", ""),
        "summary": event.get("summary", ""),
        "description": event.get("description", ""),
        "start_time": _format_event_time(event.get("start_time")),
        "end_time": _format_event_time(event.get("end_time")),
        "location": event.get("location", ""),
        "visibility": event.get("visibility", ""),
        "status": event.get("status", ""),
        "color": event.get("color"),
        "reminders": event.get("reminders", []),
        "attendees": event.get("attendees", []),
        "organizer": event.get("organizer", {}),
        "created_time": unix_timestamp_to_iso8601(event.get("created_time")),
        "updated_time": unix_timestamp_to_iso8601(event.get("updated_time")),
    }


async def _create_calendar(
    client: FeishuClient,
    summary: str | None,
    description: str | None,
    color: int | None,
) -> dict[str, Any]:
    if not summary:
        return {"error": "summary is required"}

    try:
        data: dict[str, Any] = {"summary": summary}
        if description:
            data["description"] = description
        if color is not None:
            data["color"] = color

        result = await client.post("calendar/v4/calendars", data={"calendar": data})
        calendar = result.get("data", {}).get("calendar", {})
        return {
            "ok": True,
            "calendar_id": calendar.get("calendar_id", ""),
            "summary": calendar.get("summary", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_calendar(client: FeishuClient, calendar_id: str | None) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        result = await client.get(f"calendar/v4/calendars/{calendar_id}")
        calendar = result.get("data", {}).get("calendar", {})
        return {"ok": True, "calendar": calendar}
    except Exception as e:
        return {"error": str(e)}


async def _list_calendars(
    client: FeishuClient,
    page_size: int,
    page_token: str | None,
    sync_token: str | None,
) -> dict[str, Any]:
    try:
        params: dict[str, Any] = {"page_size": min(max(page_size, 1), 500)}
        if page_token:
            params["page_token"] = page_token
        if sync_token:
            params["sync_token"] = sync_token

        result = await client.get("calendar/v4/calendars", params=params)
        items = result.get("data", {}).get("calendar_list", [])

        return {
            "ok": True,
            "calendars": items,
            "page_token": result.get("data", {}).get("page_token"),
            "sync_token": result.get("data", {}).get("sync_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _update_calendar(
    client: FeishuClient,
    calendar_id: str | None,
    summary: str | None,
    description: str | None,
    color: int | None,
) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        data: dict[str, Any] = {}
        if summary:
            data["summary"] = summary
        if description is not None:
            data["description"] = description
        if color is not None:
            data["color"] = color

        result = await client.patch(f"calendar/v4/calendars/{calendar_id}", data={"calendar": data})
        calendar = result.get("data", {}).get("calendar", {})
        return {"ok": True, "calendar": calendar}
    except Exception as e:
        return {"error": str(e)}


async def _delete_calendar(client: FeishuClient, calendar_id: str | None) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        await client.delete(f"calendar/v4/calendars/{calendar_id}")
        return {"ok": True, "calendar_id": calendar_id}
    except Exception as e:
        return {"error": str(e)}


async def _subscribe_calendar(client: FeishuClient, calendar_id: str | None) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        result = await client.post(f"calendar/v4/calendars/{calendar_id}/subscribe")
        return {"ok": True, "calendar_id": calendar_id}
    except Exception as e:
        return {"error": str(e)}


async def _unsubscribe_calendar(client: FeishuClient, calendar_id: str | None) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        result = await client.post(f"calendar/v4/calendars/{calendar_id}/unsubscribe")
        return {"ok": True, "calendar_id": calendar_id}
    except Exception as e:
        return {"error": str(e)}


async def _create_event(
    client: FeishuClient,
    calendar_id: str | None,
    summary: str | None,
    description: str | None,
    start_time: dict | None,
    end_time: dict | None,
    location: str | None,
    reminders: list | None,
    attendees: list | None,
    visibility: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not calendar_id or not summary or not start_time or not end_time:
        return {"error": "calendar_id, summary, start_time, and end_time are required"}

    try:
        start_converted = _convert_event_time(start_time)
        end_converted = _convert_event_time(end_time)

        if not start_converted or not end_converted:
            return {"error": "Invalid start_time or end_time format"}

        event_data: dict[str, Any] = {
            "summary": summary,
            "start_time": start_converted,
            "end_time": end_converted,
        }
        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if reminders:
            event_data["reminders"] = reminders
        if attendees:
            event_data["attendees"] = attendees
        if visibility:
            event_data["visibility"] = visibility

        result = await client.post(
            f"calendar/v4/calendars/{calendar_id}/events",
            data={"event": event_data},
            json_data={"user_id_type": user_id_type},
        )
        event = result.get("data", {}).get("event", {})
        return {"ok": True, "event": _format_event(event)}
    except Exception as e:
        return {"error": str(e)}


async def _get_event(
    client: FeishuClient,
    calendar_id: str | None,
    event_id: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not calendar_id or not event_id:
        return {"error": "calendar_id and event_id are required"}

    try:
        result = await client.get(
            f"calendar/v4/calendars/{calendar_id}/events/{event_id}",
            params={"user_id_type": user_id_type},
        )
        event = result.get("data", {}).get("event", {})
        return {"ok": True, "event": _format_event(event)}
    except Exception as e:
        return {"error": str(e)}


async def _list_events(
    client: FeishuClient,
    calendar_id: str | None,
    page_size: int,
    page_token: str | None,
    sync_token: str | None,
    start_time_filter: str | None,
    end_time_filter: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not calendar_id:
        return {"error": "calendar_id is required"}

    try:
        params: dict[str, Any] = {
            "page_size": min(max(page_size, 1), 500),
            "user_id_type": user_id_type,
        }
        if page_token:
            params["page_token"] = page_token
        if sync_token:
            params["sync_token"] = sync_token
        if start_time_filter:
            ts = parse_time_to_timestamp_ms(start_time_filter)
            if ts:
                params["start_time_filter"] = ts
        if end_time_filter:
            ts = parse_time_to_timestamp_ms(end_time_filter)
            if ts:
                params["end_time_filter"] = ts

        result = await client.get(
            f"calendar/v4/calendars/{calendar_id}/events",
            params=params,
        )
        items = result.get("data", {}).get("events", [])

        return {
            "ok": True,
            "events": [_format_event(e) for e in items],
            "page_token": result.get("data", {}).get("page_token"),
            "sync_token": result.get("data", {}).get("sync_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _update_event(
    client: FeishuClient,
    calendar_id: str | None,
    event_id: str | None,
    summary: str | None,
    description: str | None,
    start_time: dict | None,
    end_time: dict | None,
    location: str | None,
    reminders: list | None,
    attendees: list | None,
    visibility: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not calendar_id or not event_id:
        return {"error": "calendar_id and event_id are required"}

    try:
        event_data: dict[str, Any] = {}
        if summary:
            event_data["summary"] = summary
        if description is not None:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if visibility:
            event_data["visibility"] = visibility

        start_converted = _convert_event_time(start_time)
        if start_converted:
            event_data["start_time"] = start_converted

        end_converted = _convert_event_time(end_time)
        if end_converted:
            event_data["end_time"] = end_converted

        if reminders:
            event_data["reminders"] = reminders
        if attendees:
            event_data["attendees"] = attendees

        result = await client.patch(
            f"calendar/v4/calendars/{calendar_id}/events/{event_id}",
            data={"event": event_data},
            json_data={"user_id_type": user_id_type},
        )
        event = result.get("data", {}).get("event", {})
        return {"ok": True, "event": _format_event(event)}
    except Exception as e:
        return {"error": str(e)}


async def _delete_event(
    client: FeishuClient,
    calendar_id: str | None,
    event_id: str | None,
) -> dict[str, Any]:
    if not calendar_id or not event_id:
        return {"error": "calendar_id and event_id are required"}

    try:
        await client.delete(f"calendar/v4/calendars/{calendar_id}/events/{event_id}")
        return {"ok": True, "event_id": event_id}
    except Exception as e:
        return {"error": str(e)}
