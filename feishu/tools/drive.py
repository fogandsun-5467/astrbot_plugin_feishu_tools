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
        title: str | None = None,
        content: str | None = None,
        doc_type: str = "docx",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "list": lambda: _list_folder(client, folder_token),
            "info": lambda: _get_file_info(client, file_token, type),
            "create_folder": lambda: _create_folder(client, name, folder_token),
            "move": lambda: _move_file(client, file_token, type, folder_token),
            "delete": lambda: _delete_file(client, file_token, type),
            "import_document": lambda: _import_document(client, title, content, folder_token, doc_type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_drive",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "info", "create_folder", "move", "delete", "import_document"],
                    "description": "Action to perform",
                },
                "folder_token": {"type": "string", "description": "Folder token (from URL or previous operations)"},
                "file_token": {"type": "string", "description": "File token for info/move/delete operations"},
                "name": {"type": "string", "description": "Name for create_folder operation"},
                "type": {
                    "type": "string",
                    "enum": ["doc", "docx", "sheet", "bitable", "folder", "file", "mindnote", "shortcut", "slides"],
                    "description": "File type",
                },
                "title": {"type": "string", "description": "Document title for import_document"},
                "content": {"type": "string", "description": "Document content for import_document"},
                "doc_type": {
                    "type": "string",
                    "enum": ["docx", "doc"],
                    "default": "docx",
                    "description": "Document format for import_document",
                },
            },
            "required": ["action"],
        },
        description="Feishu cloud storage file management. Use when user mentions cloud space, folders, drive, or file management.",
        handler=handler,
    )


async def _list_folder(client: FeishuClient, folder_token: str | None) -> dict[str, Any]:
    try:
        params = {}
        if folder_token:
            params["folder_token"] = extract_folder_token(folder_token)

        result = await client.get("drive/v1/files", params=params)
        files = result.get("data", {}).get("files", [])

        return {
            "files": [
                {
                    "token": f.get("token", ""),
                    "name": f.get("name", ""),
                    "type": f.get("type", ""),
                    "url": f.get("url", ""),
                    "created_time": f.get("created_time", ""),
                    "modified_time": f.get("modified_time", ""),
                    "owner_id": f.get("owner_id", ""),
                }
                for f in files
            ],
            "next_page_token": result.get("data", {}).get("next_page_token"),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_file_info(client: FeishuClient, file_token: str | None, file_type: str | None) -> dict[str, Any]:
    if not file_token:
        return {"error": "file_token is required"}

    try:
        page_token = None
        while True:
            params = {}
            if page_token:
                params["page_token"] = page_token

            result = await client.get("drive/v1/files", params=params)
            files = result.get("data", {}).get("files", [])

            for f in files:
                if f.get("token") == file_token:
                    return {
                        "token": f.get("token", ""),
                        "name": f.get("name", ""),
                        "type": f.get("type", ""),
                        "url": f.get("url", ""),
                        "created_time": f.get("created_time", ""),
                        "modified_time": f.get("modified_time", ""),
                        "owner_id": f.get("owner_id", ""),
                    }

            page_token = result.get("data", {}).get("next_page_token")
            if not page_token:
                break

        return {"error": f"File not found: {file_token}"}
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
        return {"token": result.get("data", {}).get("token", ""), "url": result.get("data", {}).get("url", "")}
    except Exception as e:
        return {"error": str(e)}


async def _move_file(client: FeishuClient, file_token: str | None, file_type: str | None, folder_token: str | None) -> dict[str, Any]:
    if not file_token or not file_type or not folder_token:
        return {"error": "file_token, type, and folder_token are required"}

    try:
        result = await client.post(
            f"drive/v1/files/{file_token}/move",
            data={"type": file_type, "folder_token": extract_folder_token(folder_token)},
        )
        return {"success": True, "task_id": result.get("data", {}).get("task_id", "")}
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
        return {"success": True, "task_id": result.get("data", {}).get("task_id", ""), "type_used": file_type}
    except Exception as e:
        return {"error": str(e)}


async def _import_document(
    client: FeishuClient,
    title: str | None,
    content: str | None,
    folder_token: str | None,
    doc_type: str,
) -> dict[str, Any]:
    if not title or not content:
        return {"error": "title and content are required"}

    try:
        data: dict[str, Any] = {"title": title}
        if folder_token:
            data["folder_token"] = extract_folder_token(folder_token)

        result = await client.post("docx/v1/documents", data=data)
        doc_token = result.get("data", {}).get("document", {}).get("document_id")

        if not doc_token:
            return {"error": "Failed to create document"}

        lines = content.split("\n")
        blocks: list[dict] = []
        for line in lines:
            if not line.strip():
                continue
            blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}]}})

        await client.patch(
            f"docx/v1/documents/{doc_token}/blocks",
            data={"requests": [{"request_type": "ReplaceAllRequest", "replace_all": {"blocks": blocks}}]},
        )

        return {"success": True, "doc_token": doc_token}
    except Exception as e:
        return {"error": str(e)}
