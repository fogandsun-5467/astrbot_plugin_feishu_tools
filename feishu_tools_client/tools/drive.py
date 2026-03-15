from __future__ import annotations

from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, extract_folder_token


def create_drive_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        folder_token: str | None = None,
        file_token: str | None = None,
        name: str | None = None,
        type: str | None = None,
        page_size: int = 200,
        page_token: str | None = None,
        order_by: str | None = None,
        direction: str | None = None,
        request_docs: list | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "list": lambda: _list_folder(client, folder_token, page_size, page_token, order_by, direction),
            "get_meta": lambda: _get_meta(client, request_docs),
            "create_folder": lambda: _create_folder(client, name, folder_token),
            "copy": lambda: _copy_file(client, file_token, name, type, folder_token),
            "move": lambda: _move_file(client, file_token, type, folder_token),
            "delete": lambda: _delete_file(client, file_token, type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_drive",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "get_meta", "create_folder", "copy", "move", "delete"],
                    "description": "操作类型",
                },
                "folder_token": {
                    "type": "string",
                    "description": "文件夹 token。list 操作可选（不填则列出根目录）；create_folder/copy/move 操作为目标文件夹",
                },
                "file_token": {
                    "type": "string",
                    "description": "文件 token，copy/move/delete 操作必填",
                },
                "name": {
                    "type": "string",
                    "description": "名称，create_folder/copy 操作必填",
                },
                "type": {
                    "type": "string",
                    "enum": ["doc", "docx", "sheet", "bitable", "folder", "file", "mindnote", "shortcut", "slides"],
                    "description": "文件类型，copy/move/delete 操作必填",
                },
                "page_size": {
                    "type": "integer",
                    "default": 200,
                    "description": "每页数量（默认 200，最大 200）",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记",
                },
                "order_by": {
                    "type": "string",
                    "enum": ["EditedTime", "CreatedTime"],
                    "description": "排序方式：EditedTime（编辑时间）、CreatedTime（创建时间）",
                },
                "direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "description": "排序方向：ASC（升序）、DESC（降序）",
                },
                "request_docs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "doc_token": {"type": "string"},
                            "doc_type": {"type": "string"},
                        },
                    },
                    "description": "批量查询文档列表，格式：[{doc_token: 'xxx', doc_type: 'sheet'}]。get_meta 操作必填",
                },
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark云盘工具】当用户提到飞书云盘、云空间、文件夹、文件管理、上传文件、移动文件时使用此工具。支持列出文件、获取元数据、创建文件夹、复制/移动/删除文件。\n\n"
        "Actions:\n"
        "- list：列出文件夹下的文件。不提供 folder_token 时获取根目录清单\n"
        "- get_meta：批量获取文档元信息。使用 request_docs 数组参数，格式：[{doc_token: '...', doc_type: 'sheet'}]\n"
        "- create_folder：创建文件夹\n"
        "- copy：复制文件到指定位置\n"
        "- move：移动文件到指定文件夹\n"
        "- delete：删除文件\n\n"
        "【重要】copy/move/delete 操作需要 file_token 和 type 参数。\n"
        "【重要】get_meta 使用 request_docs 数组参数，doc_type 可选值：doc、sheet、file、bitable、docx、folder、mindnote、slides",
        handler=handler,
    )


async def _list_folder(
    client: FeishuClient,
    folder_token: str | None,
    page_size: int,
    page_token: str | None,
    order_by: str | None,
    direction: str | None,
) -> dict[str, Any]:
    try:
        params: dict[str, Any] = {"page_size": min(max(page_size, 1), 200)}
        if folder_token:
            params["folder_token"] = extract_folder_token(folder_token)
        if page_token:
            params["page_token"] = page_token
        if order_by:
            params["order_by"] = order_by
        if direction:
            params["direction"] = direction

        result = await client.get("drive/v1/files", params=params)
        files = result.get("data", {}).get("files", [])

        formatted_files = [
            {
                "token": f.get("token", ""),
                "name": f.get("name", ""),
                "type": f.get("type", ""),
                "url": f.get("url", ""),
                "created_time": f.get("created_time", ""),
                "modified_time": f.get("modified_time", ""),
                "owner_id": f.get("owner_id", ""),
                "size": f.get("size", 0),
            }
            for f in files
        ]

        return {
            "ok": True,
            "files": formatted_files,
            "total": len(formatted_files),
            "next_page_token": result.get("data", {}).get("next_page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_meta(client: FeishuClient, request_docs: list | None) -> dict[str, Any]:
    if not request_docs or not isinstance(request_docs, list) or len(request_docs) == 0:
        return {
            "error": "request_docs must be a non-empty array. Correct format: [{doc_token: '...', doc_type: 'sheet'}]"
        }

    if len(request_docs) > 50:
        return {"error": "request_docs cannot exceed 50 items"}

    try:
        result = await client.post(
            "drive/v1/metas/batch_query",
            data={"request_docs": request_docs},
        )
        return {
            "ok": True,
            "metas": result.get("data", {}).get("metas", []),
        }
    except Exception as e:
        return {"error": str(e)}


async def _create_folder(client: FeishuClient, name: str | None, folder_token: str | None) -> dict[str, Any]:
    if not name:
        return {"error": "name is required"}

    try:
        data: dict[str, Any] = {"name": name}

        if folder_token:
            data["folder_token"] = extract_folder_token(folder_token)
        else:
            try:
                root_result = await client.get("drive/explorer/v2/root_folder/meta")
                data["folder_token"] = root_result.get("data", {}).get("token", "0")
            except Exception:
                data["folder_token"] = "0"

        result = await client.post("drive/v1/files/create_folder", data=data)
        folder_data = result.get("data", {})
        return {
            "ok": True,
            "token": folder_data.get("token", ""),
            "url": folder_data.get("url", ""),
            "name": name,
        }
    except Exception as e:
        return {"error": str(e)}


async def _copy_file(
    client: FeishuClient,
    file_token: str | None,
    name: str | None,
    file_type: str | None,
    folder_token: str | None,
) -> dict[str, Any]:
    if not file_token or not name or not file_type:
        return {"error": "file_token, name, and type are required"}

    try:
        data: dict[str, Any] = {
            "name": name,
            "type": file_type,
        }
        if folder_token:
            data["folder_token"] = extract_folder_token(folder_token)

        result = await client.post(f"drive/v1/files/{file_token}/copy", data=data)
        file_data = result.get("data", {}).get("file", {})
        return {
            "ok": True,
            "token": file_data.get("token", ""),
            "url": file_data.get("url", ""),
            "name": file_data.get("name", name),
        }
    except Exception as e:
        return {"error": str(e)}


async def _move_file(
    client: FeishuClient,
    file_token: str | None,
    file_type: str | None,
    folder_token: str | None,
) -> dict[str, Any]:
    if not file_token or not file_type or not folder_token:
        return {"error": "file_token, type, and folder_token are required"}

    try:
        result = await client.post(
            f"drive/v1/files/{file_token}/move",
            data={"type": file_type, "folder_token": extract_folder_token(folder_token)},
        )
        return {
            "ok": True,
            "task_id": result.get("data", {}).get("task_id", ""),
            "file_token": file_token,
            "target_folder_token": folder_token,
        }
    except Exception as e:
        return {"error": str(e)}


async def _delete_file(client: FeishuClient, file_token: str | None, file_type: str | None) -> dict[str, Any]:
    if not file_token:
        return {"error": "file_token is required"}

    try:
        params = {}
        if file_type:
            params["type"] = file_type

        result = await client.delete(f"drive/v1/files/{file_token}", params=params)
        return {
            "ok": True,
            "task_id": result.get("data", {}).get("task_id", ""),
            "file_token": file_token,
        }
    except Exception as e:
        return {"error": str(e)}
