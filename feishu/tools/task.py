import json
from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


def create_task_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        task_guid: str | None = None,
        tasklist_guid: str | None = None,
        section_guid: str | None = None,
        summary: str | None = None,
        description: str | None = None,
        due: dict | None = None,
        members: list | None = None,
        content: str | None = None,
        name: str | None = None,
        owner: dict | None = None,
        update_fields: list | None = None,
        origin_owner_to_role: str | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        file_path: str | None = None,
        file_url: str | None = None,
        filename: str | None = None,
        user_id_type: str = "open_id",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "create_task": lambda: _create_task(client, summary, description, due, members, user_id_type),
            "create_subtask": lambda: _create_subtask(client, task_guid, summary, description, due, members, user_id_type),
            "get_task": lambda: _get_task(client, task_guid, user_id_type),
            "update_task": lambda: _update_task(client, task_guid, summary, description, due, members, user_id_type),
            "delete_task": lambda: _delete_task(client, task_guid),
            "create_comment": lambda: _create_task_comment(client, task_guid, content, user_id_type),
            "list_comments": lambda: _list_task_comments(client, task_guid, page_size, page_token, user_id_type),
            "get_comment": lambda: _get_task_comment(client, task_guid, None, user_id_type),
            "upload_attachment": lambda: _upload_attachment(client, task_guid, file_path, file_url, filename, user_id_type),
            "list_attachments": lambda: _list_attachments(client, task_guid, user_id_type),
            "add_to_tasklist": lambda: _add_task_to_tasklist(client, task_guid, tasklist_guid, section_guid, user_id_type),
            "remove_from_tasklist": lambda: _remove_task_from_tasklist(client, task_guid, tasklist_guid, user_id_type),
            "create_tasklist": lambda: _create_tasklist(client, name, members, user_id_type),
            "get_tasklist": lambda: _get_tasklist(client, tasklist_guid, user_id_type),
            "list_tasklists": lambda: _list_tasklists(client, page_size, page_token, user_id_type),
            "update_tasklist": lambda: _update_tasklist(client, tasklist_guid, name, owner, update_fields, origin_owner_to_role, user_id_type),
            "delete_tasklist": lambda: _delete_tasklist(client, tasklist_guid),
            "add_tasklist_members": lambda: _add_tasklist_members(client, tasklist_guid, members, user_id_type),
            "remove_tasklist_members": lambda: _remove_tasklist_members(client, tasklist_guid, members, user_id_type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_task",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create_task",
                        "create_subtask",
                        "get_task",
                        "update_task",
                        "delete_task",
                        "create_comment",
                        "list_comments",
                        "get_comment",
                        "upload_attachment",
                        "list_attachments",
                        "add_to_tasklist",
                        "remove_from_tasklist",
                        "create_tasklist",
                        "get_tasklist",
                        "list_tasklists",
                        "update_tasklist",
                        "delete_tasklist",
                        "add_tasklist_members",
                        "remove_tasklist_members",
                    ],
                    "description": "Action to perform",
                },
                "task_guid": {"type": "string", "description": "Task GUID"},
                "tasklist_guid": {"type": "string", "description": "Tasklist GUID"},
                "section_guid": {"type": "string", "description": "Section GUID for add_to_tasklist"},
                "summary": {"type": "string", "description": "Task summary/title"},
                "description": {"type": "string", "description": "Task description"},
                "due": {
                    "type": "object",
                    "description": "Due date configuration: {timestamp: string, is_all_day: boolean}",
                },
                "members": {
                    "type": "array",
                    "description": "Task members: [{id: string, role: string, type: string}]",
                },
                "content": {"type": "string", "description": "Comment content"},
                "name": {"type": "string", "description": "Tasklist name"},
                "owner": {"type": "object", "description": "Tasklist owner: {id: string, type: string}"},
                "update_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to update for tasklist",
                },
                "origin_owner_to_role": {"type": "string", "description": "Role for original owner after ownership transfer"},
                "page_size": {"type": "integer", "default": 50, "description": "Page size for list operations"},
                "page_token": {"type": "string", "description": "Pagination token"},
                "file_path": {"type": "string", "description": "Local file path for attachment upload"},
                "file_url": {"type": "string", "description": "Remote file URL for attachment upload"},
                "filename": {"type": "string", "description": "Filename for remote URL attachment"},
                "user_id_type": {
                    "type": "string",
                    "enum": ["open_id", "user_id", "union_id"],
                    "default": "open_id",
                },
            },
            "required": ["action"],
        },
        description="Feishu Task, tasklist, subtask, comment, and attachment management. Use when user mentions tasks, tasklists, subtasks, or task comments.",
        handler=handler,
    )


async def _create_task(
    client: FeishuClient,
    summary: str | None,
    description: str | None,
    due: dict | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not summary:
        return {"error": "summary is required"}

    try:
        data: dict[str, Any] = {"summary": summary}
        if description:
            data["description"] = description
        if due:
            data["due"] = due
        if members:
            data["members"] = members

        result = await client.post("task/v1/tasks", data=data, json_data={"user_id_type": user_id_type})
        task = result.get("data", {}).get("task", {})
        return {"success": True, "task_guid": task.get("guid", ""), "task": task}
    except Exception as e:
        return {"error": str(e)}


async def _create_subtask(
    client: FeishuClient,
    task_guid: str | None,
    summary: str | None,
    description: str | None,
    due: dict | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid or not summary:
        return {"error": "task_guid and summary are required"}

    try:
        data: dict[str, Any] = {"summary": summary}
        if description:
            data["description"] = description
        if due:
            data["due"] = due
        if members:
            data["members"] = members

        result = await client.post(f"task/v1/tasks/{task_guid}/subtasks", data=data, json_data={"user_id_type": user_id_type})
        task = result.get("data", {}).get("task", {})
        return {"success": True, "task_guid": task.get("guid", ""), "task": task}
    except Exception as e:
        return {"error": str(e)}


async def _get_task(client: FeishuClient, task_guid: str | None, user_id_type: str) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        result = await client.get(f"task/v1/tasks/{task_guid}", params={"user_id_type": user_id_type})
        return {"task": result.get("data", {}).get("task", {})}
    except Exception as e:
        return {"error": str(e)}


async def _update_task(
    client: FeishuClient,
    task_guid: str | None,
    summary: str | None,
    description: str | None,
    due: dict | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        data: dict[str, Any] = {}
        if summary:
            data["summary"] = summary
        if description:
            data["description"] = description
        if due:
            data["due"] = due
        if members:
            data["members"] = members

        result = await client.patch(f"task/v1/tasks/{task_guid}", data=data, json_data={"user_id_type": user_id_type})
        return {"success": True, "task": result.get("data", {}).get("task", {})}
    except Exception as e:
        return {"error": str(e)}


async def _delete_task(client: FeishuClient, task_guid: str | None) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        await client.delete(f"task/v1/tasks/{task_guid}")
        return {"success": True, "task_guid": task_guid}
    except Exception as e:
        return {"error": str(e)}


async def _create_task_comment(
    client: FeishuClient,
    task_guid: str | None,
    content: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid or not content:
        return {"error": "task_guid and content are required"}

    try:
        result = await client.post(
            f"task/v1/tasks/{task_guid}/comments",
            data={"content": content},
            json_data={"user_id_type": user_id_type},
        )
        return {"success": True, "comment": result.get("data", {}).get("comment", {})}
    except Exception as e:
        return {"error": str(e)}


async def _list_task_comments(
    client: FeishuClient,
    task_guid: str | None,
    page_size: int,
    page_token: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        params: dict[str, Any] = {"user_id_type": user_id_type, "page_size": min(max(page_size, 1), 50)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get(f"task/v1/tasks/{task_guid}/comments", params=params)
        return {
            "comments": result.get("data", {}).get("items", []),
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_task_comment(client: FeishuClient, task_guid: str | None, comment_id: str | None, user_id_type: str) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        result = await client.get(f"task/v1/tasks/{task_guid}/comments", params={"user_id_type": user_id_type})
        return {"comment": result.get("data", {}).get("comment", {})}
    except Exception as e:
        return {"error": str(e)}


async def _upload_attachment(
    client: FeishuClient,
    task_guid: str | None,
    file_path: str | None,
    file_url: str | None,
    filename: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    if not file_path and not file_url:
        return {"error": "file_path or file_url is required"}

    try:
        data: dict[str, Any] = {}
        if file_path:
            data["file_path"] = file_path
        elif file_url:
            data["file_url"] = file_url
            if filename:
                data["filename"] = filename

        result = await client.post(
            f"task/v1/tasks/{task_guid}/attachments",
            data=data,
            json_data={"user_id_type": user_id_type},
        )
        return {"success": True, "attachment": result.get("data", {}).get("attachment", {})}
    except Exception as e:
        return {"error": str(e)}


async def _list_attachments(client: FeishuClient, task_guid: str | None, user_id_type: str) -> dict[str, Any]:
    if not task_guid:
        return {"error": "task_guid is required"}

    try:
        result = await client.get(f"task/v1/tasks/{task_guid}/attachments", params={"user_id_type": user_id_type})
        return {"attachments": result.get("data", {}).get("items", [])}
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
        return {"success": True, **result.get("data", {})}
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
        return {"success": True}
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

        result = await client.post("task/v1/tasklists", data=data, json_data={"user_id_type": user_id_type})
        tasklist = result.get("data", {}).get("tasklist", {})
        return {"success": True, "tasklist_guid": tasklist.get("guid", ""), "tasklist": tasklist}
    except Exception as e:
        return {"error": str(e)}


async def _get_tasklist(client: FeishuClient, tasklist_guid: str | None, user_id_type: str) -> dict[str, Any]:
    if not tasklist_guid:
        return {"error": "tasklist_guid is required"}

    try:
        result = await client.get(f"task/v1/tasklists/{tasklist_guid}", params={"user_id_type": user_id_type})
        return {"tasklist": result.get("data", {}).get("tasklist", {})}
    except Exception as e:
        return {"error": str(e)}


async def _list_tasklists(
    client: FeishuClient,
    page_size: int,
    page_token: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    try:
        params: dict[str, Any] = {"user_id_type": user_id_type, "page_size": min(max(page_size, 1), 50)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get("task/v1/tasklists", params=params)
        return {
            "tasklists": result.get("data", {}).get("items", []),
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _update_tasklist(
    client: FeishuClient,
    tasklist_guid: str | None,
    name: str | None,
    owner: dict | None,
    update_fields: list | None,
    origin_owner_to_role: str | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not tasklist_guid:
        return {"error": "tasklist_guid is required"}

    try:
        tasklist_data: dict[str, Any] = {}
        if name:
            tasklist_data["name"] = name
        if owner:
            tasklist_data["owner"] = owner

        data: dict[str, Any] = {"tasklist": tasklist_data}
        if update_fields:
            data["update_fields"] = update_fields
        if origin_owner_to_role:
            data["origin_owner_to_role"] = origin_owner_to_role

        result = await client.patch(f"task/v1/tasklists/{tasklist_guid}", data=data, json_data={"user_id_type": user_id_type})
        return {"success": True, "tasklist": result.get("data", {}).get("tasklist", {})}
    except Exception as e:
        return {"error": str(e)}


async def _delete_tasklist(client: FeishuClient, tasklist_guid: str | None) -> dict[str, Any]:
    if not tasklist_guid:
        return {"error": "tasklist_guid is required"}

    try:
        await client.delete(f"task/v1/tasklists/{tasklist_guid}")
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


async def _add_tasklist_members(
    client: FeishuClient,
    tasklist_guid: str | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not tasklist_guid or not members:
        return {"error": "tasklist_guid and members are required"}

    try:
        result = await client.post(
            f"task/v1/tasklists/{tasklist_guid}/members",
            data={"members": members},
            json_data={"user_id_type": user_id_type},
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _remove_tasklist_members(
    client: FeishuClient,
    tasklist_guid: str | None,
    members: list | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not tasklist_guid or not members:
        return {"error": "tasklist_guid and members are required"}

    try:
        result = await client.delete(
            f"task/v1/tasklists/{tasklist_guid}/members",
            params={"user_id_type": user_id_type},
            data={"members": members},
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}
