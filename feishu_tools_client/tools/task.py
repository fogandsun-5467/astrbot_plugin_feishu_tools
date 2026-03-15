from __future__ import annotations

from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, parse_time_to_timestamp_ms, unix_timestamp_to_iso8601


def create_task_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        task_guid: str | None = None,
        tasklist_guid: str | None = None,
        section_guid: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        due: dict | None = None,
        start: dict | None = None,
        completed_at: str | None = None,
        members: list | None = None,
        content: str | None = None,
        name: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        completed: bool | None = None,
        user_id_type: str = "open_id",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "create": lambda: _create_task(client, summary, description, due, start, members, user_id_type),
            "get": lambda: _get_task(client, task_guid, user_id_type),
            "list": lambda: _list_tasks(client, page_size, page_token, completed, user_id_type),
            "patch": lambda: _patch_task(client, task_guid, summary, description, due, start, completed_at, members, user_id_type),
            "delete": lambda: _delete_task(client, task_guid),
            "create_tasklist": lambda: _create_tasklist(client, name, members, user_id_type),
            "get_tasklist": lambda: _get_tasklist(client, tasklist_guid, user_id_type),
            "list_tasklists": lambda: _list_tasklists(client, page_size, page_token, user_id_type),
            "delete_tasklist": lambda: _delete_tasklist(client, tasklist_guid),
            "add_to_tasklist": lambda: _add_task_to_tasklist(client, task_guid, tasklist_guid, section_guid, user_id_type),
            "remove_from_tasklist": lambda: _remove_task_from_tasklist(client, task_guid, tasklist_guid, user_id_type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_task",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create",
                        "get",
                        "list",
                        "patch",
                        "delete",
                        "create_tasklist",
                        "get_tasklist",
                        "list_tasklists",
                        "delete_tasklist",
                        "add_to_tasklist",
                        "remove_from_tasklist",
                    ],
                    "description": "操作类型",
                },
                "task_guid": {
                    "type": "string",
                    "description": "任务 GUID，get/patch/delete/add_to_tasklist/remove_from_tasklist 操作必填",
                },
                "tasklist_guid": {
                    "type": "string",
                    "description": "任务清单 GUID，get_tasklist/delete_tasklist/add_to_tasklist/remove_from_tasklist 操作必填",
                },
                "section_guid": {
                    "type": "string",
                    "description": "分组 GUID，add_to_tasklist 操作可选",
                },
                "summary": {
                    "type": "string",
                    "description": "任务标题，create 操作必填，patch 操作可选",
                },
                "description": {
                    "type": "string",
                    "description": "任务描述",
                },
                "due": {
                    "type": "object",
                    "description": "截止时间，格式：{timestamp: '2024-01-01T00:00:00+08:00', is_all_day: false}",
                },
                "start": {
                    "type": "object",
                    "description": "开始时间，格式：{timestamp: '2024-01-01T00:00:00+08:00', is_all_day: false}",
                },
                "completed_at": {
                    "type": "string",
                    "description": "完成时间。填 ISO 8601 格式时间（如 '2024-01-01T00:00:00+08:00'）标记完成；填 '0' 标记未完成",
                },
                "members": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "role": {"type": "string", "enum": ["assignee", "follower"]},
                        },
                    },
                    "description": "任务成员列表，格式：[{id: 'ou_xxx', role: 'assignee'}]。role 可选值：assignee（负责人）、follower（关注人）",
                },
                "name": {
                    "type": "string",
                    "description": "任务清单名称，create_tasklist 操作必填",
                },
                "page_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "每页数量（默认 50，最大 100）",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记",
                },
                "completed": {
                    "type": "boolean",
                    "description": "是否筛选已完成任务，list 操作可选",
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
        description="【飞书/Feishu/Lark任务工具】当用户提到飞书任务、待办事项、创建任务、任务清单、完成任务时使用此工具。支持创建、查询、更新、删除任务和任务清单。\n\n"
        "Actions:\n"
        "- create：创建任务，需要 summary\n"
        "- get：获取任务详情，需要 task_guid\n"
        "- list：列出我的任务（仅返回我负责的任务）\n"
        "- patch：更新任务，需要 task_guid\n"
        "- delete：删除任务，需要 task_guid\n"
        "- create_tasklist：创建任务清单，需要 name\n"
        "- get_tasklist：获取任务清单详情，需要 tasklist_guid\n"
        "- list_tasklists：列出我的任务清单\n"
        "- delete_tasklist：删除任务清单，需要 tasklist_guid\n"
        "- add_to_tasklist：将任务添加到清单，需要 task_guid 和 tasklist_guid\n"
        "- remove_from_tasklist：将任务从清单移除，需要 task_guid 和 tasklist_guid\n\n"
        "【时间格式】due/start/completed_at 使用 ISO 8601 / RFC 3339 格式（包含时区），例如 '2024-01-01T00:00:00+08:00'。\n"
        "【重要】completed_at 设为 '0' 可将任务标记为未完成。",
        handler=handler,
    )


def _convert_time(time_obj: dict | None) -> dict | None:
    if not time_obj or not time_obj.get("timestamp"):
        return None

    ts = parse_time_to_timestamp_ms(time_obj["timestamp"])
    if not ts:
        return None

    return {
        "timestamp": ts,
        "is_all_day": time_obj.get("is_all_day", False),
    }


def _format_task(task: dict) -> dict:
    if not task:
        return {}

    due = task.get("due", {})
    start = task.get("start", {})

    return {
        "guid": task.get("guid", ""),
        "summary": task.get("summary", ""),
        "description": task.get("description", ""),
        "due": {
            "timestamp": unix_timestamp_to_iso8601(due.get("timestamp")),
            "is_all_day": due.get("is_all_day", False),
        } if due.get("timestamp") else None,
        "start": {
            "timestamp": unix_timestamp_to_iso8601(start.get("timestamp")),
            "is_all_day": start.get("is_all_day", False),
        } if start.get("timestamp") else None,
        "completed_at": unix_timestamp_to_iso8601(task.get("completed_at")),
        "status": task.get("status", ""),
        "members": task.get("members", []),
        "created_at": unix_timestamp_to_iso8601(task.get("created_at")),
        "updated_at": unix_timestamp_to_iso8601(task.get("updated_at")),
    }


async def _create_task(
    client: FeishuClient,
    summary: str | None,
    description: str | None,
    due: dict | None,
    start: dict | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not summary:
        return {"error": "summary is required"}

    try:
        data: dict[str, Any] = {"summary": summary}
        if description:
            data["description"] = description

        due_converted = _convert_time(due)
        if due_converted:
            data["due"] = due_converted

        start_converted = _convert_time(start)
        if start_converted:
            data["start"] = start_converted

        if members:
            data["members"] = members

        result = await client.post(
            "task/v2/tasks",
            data=data,
            json_data={"user_id_type": user_id_type},
        )
        task = result.get("data", {}).get("task", {})
        return {"ok": True, "task": _format_task(task)}
    except Exception as e:
        return {"error": str(e)}


async def _get_task(client: FeishuClient, task_guid: str | None, user_id_type: str) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        result = await client.get(f"task/v2/tasks/{task_guid}", params={"user_id_type": user_id_type})
        task = result.get("data", {}).get("task", {})
        return {"ok": True, "task": _format_task(task)}
    except Exception as e:
        return {"error": str(e)}


async def _list_tasks(
    client: FeishuClient,
    page_size: int,
    page_token: str | None,
    completed: bool | None,
    user_id_type: str,
) -> dict[str, Any]:
    try:
        params: dict[str, Any] = {
            "user_id_type": user_id_type,
            "page_size": min(max(page_size, 1), 100),
        }
        if page_token:
            params["page_token"] = page_token
        if completed is not None:
            params["completed"] = str(completed).lower()

        result = await client.get("task/v2/tasks", params=params)
        items = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "tasks": [_format_task(t) for t in items],
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _patch_task(
    client: FeishuClient,
    task_guid: str | None,
    summary: str | None,
    description: str | None,
    due: dict | None,
    start: dict | None,
    completed_at: str | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        task_data: dict[str, Any] = {}
        update_fields: list[str] = []

        if summary:
            task_data["summary"] = summary
            update_fields.append("summary")
        if description is not None:
            task_data["description"] = description
            update_fields.append("description")

        due_converted = _convert_time(due)
        if due_converted:
            task_data["due"] = due_converted
            update_fields.append("due")

        start_converted = _convert_time(start)
        if start_converted:
            task_data["start"] = start_converted
            update_fields.append("start")

        if completed_at is not None:
            if completed_at == "0":
                task_data["completed_at"] = "0"
            else:
                ts = parse_time_to_timestamp_ms(completed_at)
                if ts:
                    task_data["completed_at"] = ts
                else:
                    return {"error": f"Invalid completed_at format: {completed_at}"}
            update_fields.append("completed_at")

        if members:
            task_data["members"] = members
            update_fields.append("members")

        if not update_fields:
            return {"error": "No fields to update"}

        result = await client.patch(
            f"task/v2/tasks/{task_guid}",
            data={"task": task_data, "update_fields": update_fields},
            json_data={"user_id_type": user_id_type},
        )
        task = result.get("data", {}).get("task", {})
        return {"ok": True, "task": _format_task(task)}
    except Exception as e:
        return {"error": str(e)}


async def _delete_task(client: FeishuClient, task_guid: str | None) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        await client.delete(f"task/v2/tasks/{task_guid}")
        return {"ok": True, "task_guid": task_guid}
    except Exception as e:
        return {"error": str(e)}


async def _create_tasklist(
    client: FeishuClient,
    name: str | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not name:
        return {"error": "name is required"}

    try:
        data: dict[str, Any] = {"name": name}
        if members:
            data["members"] = members

        result = await client.post(
            "task/v1/tasklists",
            data=data,
            json_data={"user_id_type": user_id_type},
        )
        tasklist = result.get("data", {}).get("tasklist", {})
        return {
            "ok": True,
            "tasklist_guid": tasklist.get("guid", ""),
            "name": tasklist.get("name", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_tasklist(client: FeishuClient, tasklist_guid: str | None, user_id_type: str) -> dict[str, Any]:
    if not tasklist_guid:
        return {"error": "tasklist_guid is required"}

    try:
        result = await client.get(f"task/v1/tasklists/{tasklist_guid}", params={"user_id_type": user_id_type})
        tasklist = result.get("data", {}).get("tasklist", {})
        return {"ok": True, "tasklist": tasklist}
    except Exception as e:
        return {"error": str(e)}


async def _list_tasklists(
    client: FeishuClient,
    page_size: int,
    page_token: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    try:
        params: dict[str, Any] = {
            "user_id_type": user_id_type,
            "page_size": min(max(page_size, 1), 100),
        }
        if page_token:
            params["page_token"] = page_token

        result = await client.get("task/v1/tasklists", params=params)
        items = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "tasklists": items,
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _delete_tasklist(client: FeishuClient, tasklist_guid: str | None) -> dict[str, Any]:
    if not tasklist_guid:
        return {"error": "tasklist_guid is required"}

    try:
        await client.delete(f"task/v1/tasklists/{tasklist_guid}")
        return {"ok": True, "tasklist_guid": tasklist_guid}
    except Exception as e:
        return {"error": str(e)}


async def _add_task_to_tasklist(
    client: FeishuClient,
    task_guid: str | None,
    tasklist_guid: str | None,
    section_guid: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid or not tasklist_guid:
        return {"error": "task_guid and tasklist_guid are required"}

    try:
        data: dict[str, Any] = {}
        if section_guid:
            data["section_guid"] = section_guid

        result = await client.post(
            f"task/v1/tasklists/{tasklist_guid}/tasks/{task_guid}",
            data=data,
            json_data={"user_id_type": user_id_type},
        )
        return {"ok": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _remove_task_from_tasklist(
    client: FeishuClient,
    task_guid: str | None,
    tasklist_guid: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid or not tasklist_guid:
        return {"error": "task_guid and tasklist_guid are required"}

    try:
        await client.delete(
            f"task/v1/tasklists/{tasklist_guid}/tasks/{task_guid}",
            params={"user_id_type": user_id_type},
        )
        return {"ok": True}
    except Exception as e:
        return {"error": str(e)}
