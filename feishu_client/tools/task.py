import json
from typing import Any

import lark_oapi as lark

from ..client import FeishuClient
from ...utils.time_utils import parse_time_to_timestamp, timestamp_to_datetime_str


def create_task_tool(client: FeishuClient):
    async def task_handler(action: str, **kwargs) -> str:
        lark_client = client.get_client()
        
        if action == "create":
            return await _create_task(lark_client, kwargs)
        elif action == "get":
            return await _get_task(lark_client, kwargs)
        elif action == "list":
            return await _list_tasks(lark_client, kwargs)
        elif action == "patch":
            return await _patch_task(lark_client, kwargs)
        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)
    
    return {
        "name": "feishu_task",
        "description": """飞书任务管理工具。用于创建、查询、更新任务。

Actions:
- create: 创建任务（必填: summary）
- list: 查询任务列表
- get: 获取任务详情（必填: task_guid）
- patch: 更新任务（必填: task_guid）

时间格式: ISO 8601 / RFC 3339（带时区），例如 '2024-01-01T00:00:00+08:00'
完成时间: completed_at 设为 "0" 可反完成任务""",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "get", "list", "patch"],
                    "description": "操作类型",
                },
                "summary": {
                    "type": "string",
                    "description": "任务标题（create时必填）",
                },
                "task_guid": {
                    "type": "string",
                    "description": "任务ID（get/patch时必填）",
                },
                "description": {
                    "type": "string",
                    "description": "任务描述",
                },
                "due": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string", "description": "截止时间"},
                        "is_all_day": {"type": "boolean", "description": "是否全天任务"},
                    },
                    "description": "截止时间配置",
                },
                "completed_at": {
                    "type": "string",
                    "description": "完成时间。设为 '0' 可反完成任务",
                },
                "current_user_id": {
                    "type": "string",
                    "description": "当前用户的 open_id（强烈建议传入，确保创建者可编辑任务）",
                },
                "members": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "成员 open_id"},
                            "role": {"type": "string", "enum": ["assignee", "follower"], "description": "角色"},
                        },
                    },
                    "description": "任务成员列表",
                },
                "page_size": {
                    "type": "number",
                    "description": "每页数量（默认50，最大100）",
                },
                "completed": {
                    "type": "boolean",
                    "description": "是否筛选已完成任务",
                },
            },
            "required": ["action"],
        },
        "handler": task_handler,
    }


async def _create_task(client: lark.Client, params: dict) -> str:
    summary = params.get("summary")
    if not summary:
        return json.dumps({"error": "summary is required"}, ensure_ascii=False)
    
    task_data: dict[str, Any] = {"summary": summary}
    
    if params.get("description"):
        task_data["description"] = params["description"]
    
    if params.get("due"):
        due_ts = parse_time_to_timestamp(params["due"].get("timestamp", ""))
        if due_ts:
            task_data["due"] = {
                "timestamp": str(due_ts),
                "is_all_day": params["due"].get("is_all_day", False),
            }
    
    members = params.get("members", [])
    current_user_id = params.get("current_user_id")
    
    if current_user_id:
        member_ids = [m.get("id") for m in members if m.get("id")]
        if current_user_id not in member_ids:
            members.append({"id": current_user_id, "role": "follower"})
    
    if members:
        task_data["members"] = members
    
    try:
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.POST) \
            .uri("/open-apis/task/v2/tasks") \
            .token_types({lark.AccessTokenType.TENANT}) \
            .queries([("user_id_type", "open_id")]) \
            .body(task_data) \
            .build()
        
        response = await client.arequest(request)
        
        if not response.success():
            return json.dumps({"error": f"创建任务失败: {response.msg}", "code": response.code}, ensure_ascii=False)
        
        result = json.loads(str(response.raw.content, lark.UTF_8))
        task = result.get("data", {}).get("task", {})
        return json.dumps({
            "success": True,
            "task": {
                "guid": task.get("guid"),
                "summary": task.get("summary"),
            }
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"创建任务异常: {str(e)}"}, ensure_ascii=False)


async def _get_task(client: lark.Client, params: dict) -> str:
    task_guid = params.get("task_guid")
    if not task_guid:
        return json.dumps({"error": "task_guid is required"}, ensure_ascii=False)
    
    try:
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.GET) \
            .uri(f"/open-apis/task/v2/tasks/{task_guid}") \
            .token_types({lark.AccessTokenType.TENANT}) \
            .queries([("user_id_type", "open_id")]) \
            .build()
        
        response = await client.arequest(request)
        
        if not response.success():
            return json.dumps({"error": f"获取任务失败: {response.msg}", "code": response.code}, ensure_ascii=False)
        
        result = json.loads(str(response.raw.content, lark.UTF_8))
        task = result.get("data", {}).get("task", {})
        if not task:
            return json.dumps({"error": "任务不存在"}, ensure_ascii=False)
        
        due = task.get("due", {})
        return json.dumps({
            "task": {
                "guid": task.get("guid"),
                "summary": task.get("summary"),
                "description": task.get("description"),
                "status": task.get("status"),
                "completed_at": timestamp_to_datetime_str(int(task["completed_at"])) if task.get("completed_at") else None,
                "due": {
                    "timestamp": timestamp_to_datetime_str(int(due["timestamp"])) if due.get("timestamp") else None,
                    "is_all_day": due.get("is_all_day"),
                } if due else None,
            }
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"获取任务异常: {str(e)}"}, ensure_ascii=False)


async def _list_tasks(client: lark.Client, params: dict) -> str:
    page_size = params.get("page_size", 50)
    completed = params.get("completed")
    
    try:
        queries = [("page_size", str(page_size)), ("user_id_type", "open_id")]
        if completed is not None:
            queries.append(("completed", str(completed).lower()))
        
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.GET) \
            .uri("/open-apis/task/v2/tasks") \
            .token_types({lark.AccessTokenType.TENANT}) \
            .queries(queries) \
            .build()
        
        response = await client.arequest(request)
        
        if not response.success():
            return json.dumps({"error": f"查询任务失败: {response.msg}", "code": response.code}, ensure_ascii=False)
        
        result = json.loads(str(response.raw.content, lark.UTF_8))
        data = result.get("data", {})
        tasks = []
        for task in data.get("items", []):
            tasks.append({
                "guid": task.get("guid"),
                "summary": task.get("summary"),
                "status": task.get("status"),
                "completed_at": timestamp_to_datetime_str(int(task["completed_at"])) if task.get("completed_at") else None,
            })
        
        return json.dumps({
            "tasks": tasks,
            "has_more": data.get("has_more", False),
            "page_token": data.get("page_token"),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"查询任务异常: {str(e)}"}, ensure_ascii=False)


async def _patch_task(client: lark.Client, params: dict) -> str:
    task_guid = params.get("task_guid")
    if not task_guid:
        return json.dumps({"error": "task_guid is required"}, ensure_ascii=False)
    
    update_data: dict[str, Any] = {}
    update_fields = []
    
    if params.get("summary"):
        update_data["summary"] = params["summary"]
        update_fields.append("summary")
    
    if params.get("description") is not None:
        update_data["description"] = params["description"]
        update_fields.append("description")
    
    if params.get("due"):
        due_ts = parse_time_to_timestamp(params["due"].get("timestamp", ""))
        if due_ts:
            update_data["due"] = {
                "timestamp": str(due_ts),
                "is_all_day": params["due"].get("is_all_day", False),
            }
            update_fields.append("due")
    
    if params.get("completed_at") is not None:
        completed_at = params["completed_at"]
        if completed_at == "0":
            update_data["completed_at"] = "0"
        else:
            ts = parse_time_to_timestamp(completed_at)
            if ts:
                update_data["completed_at"] = str(ts)
        update_fields.append("completed_at")
    
    if params.get("members"):
        update_data["members"] = params["members"]
        update_fields.append("members")
    
    update_data["update_fields"] = update_fields
    
    try:
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.PATCH) \
            .uri(f"/open-apis/task/v2/tasks/{task_guid}") \
            .token_types({lark.AccessTokenType.TENANT}) \
            .queries([("user_id_type", "open_id")]) \
            .body(update_data) \
            .build()
        
        response = await client.arequest(request)
        
        if not response.success():
            return json.dumps({"error": f"更新任务失败: {response.msg}", "code": response.code}, ensure_ascii=False)
        
        result = json.loads(str(response.raw.content, lark.UTF_8))
        task = result.get("data", {}).get("task", {})
        return json.dumps({
            "success": True,
            "task": {
                "guid": task.get("guid", task_guid),
                "summary": task.get("summary"),
            }
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"更新任务异常: {str(e)}"}, ensure_ascii=False)
