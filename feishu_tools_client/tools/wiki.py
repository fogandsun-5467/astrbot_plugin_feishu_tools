from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, extract_wiki_token


def create_wiki_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        token: str | None = None,
        space_id: str | None = None,
        parent_node_token: str | None = None,
        title: str | None = None,
        obj_type: str = "docx",
        target_space_id: str | None = None,
        target_parent_token: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "spaces": lambda: _list_spaces(client),
            "nodes": lambda: _list_nodes(client, space_id, parent_node_token),
            "get": lambda: _get_node(client, token),
            "create": lambda: _create_node(client, space_id, title, obj_type, parent_node_token),
            "move": lambda: _move_node(client, space_id, token, target_space_id, target_parent_token),
            "rename": lambda: _rename_node(client, space_id, token, title),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_wiki",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["spaces", "nodes", "get", "create", "move", "rename"],
                    "description": "Action to perform",
                },
                "token": {"type": "string", "description": "Wiki node token (from URL or previous operations)"},
                "space_id": {"type": "string", "description": "Wiki space ID"},
                "parent_node_token": {"type": "string", "description": "Parent node token for nodes/create operations"},
                "title": {"type": "string", "description": "Title for create/rename operations"},
                "obj_type": {
                    "type": "string",
                    "enum": ["docx", "sheet", "bitable", "mindnote", "file", "doc", "slides"],
                    "default": "docx",
                    "description": "Object type for create operation",
                },
                "target_space_id": {"type": "string", "description": "Target space ID for move operation"},
                "target_parent_token": {"type": "string", "description": "Target parent token for move operation"},
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark知识库工具】当用户提到飞书知识库、Wiki、知识空间时使用此工具。支持浏览知识库空间、管理知识库节点。注意：知识库内容读写使用 feishu_doc 工具。",
        handler=handler,
    )


async def _list_spaces(client: FeishuClient) -> dict[str, Any]:
    try:
        result = await client.get("wiki/v2/spaces")
        spaces = result.get("data", {}).get("items", [])

        return {
            "spaces": [
                {
                    "space_id": s.get("space_id", ""),
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                }
                for s in spaces
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_nodes(client: FeishuClient, space_id: str | None, parent_node_token: str | None) -> dict[str, Any]:
    if not space_id:
        return {"error": "space_id is required"}

    try:
        params: dict[str, Any] = {}
        if parent_node_token:
            params["parent_node_token"] = parent_node_token

        result = await client.get(f"wiki/v2/spaces/{space_id}/nodes", params=params)
        nodes = result.get("data", {}).get("items", [])

        return {
            "nodes": [
                {
                    "node_token": n.get("node_token", ""),
                    "obj_token": n.get("obj_token", ""),
                    "obj_type": n.get("obj_type", ""),
                    "title": n.get("title", ""),
                    "parent_node_token": n.get("parent_node_token", ""),
                }
                for n in nodes
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_node(client: FeishuClient, token: str | None) -> dict[str, Any]:
    if not token:
        return {"error": "token is required"}

    node_token = extract_wiki_token(token)

    try:
        result = await client.get(f"wiki/v2/spaces/get_node", params={"token": node_token})
        node = result.get("data", {}).get("node", {})

        return {
            "node_token": node.get("node_token", ""),
            "obj_token": node.get("obj_token", ""),
            "obj_type": node.get("obj_type", ""),
            "title": node.get("title", ""),
            "space_id": node.get("space_id", ""),
            "parent_node_token": node.get("parent_node_token", ""),
            "hint": "Use obj_token with feishu_doc tool to read/write the document content",
        }
    except Exception as e:
        return {"error": str(e)}


async def _create_node(
    client: FeishuClient,
    space_id: str | None,
    title: str | None,
    obj_type: str,
    parent_node_token: str | None,
) -> dict[str, Any]:
    if not space_id or not title:
        return {"error": "space_id and title are required"}

    try:
        data: dict[str, Any] = {"title": title, "obj_type": obj_type}
        if parent_node_token:
            data["parent_node_token"] = parent_node_token

        result = await client.post(f"wiki/v2/spaces/{space_id}/nodes", data=data)
        node = result.get("data", {})

        return {
            "success": True,
            "node_token": node.get("node_token", ""),
            "obj_token": node.get("obj_token", ""),
            "obj_type": node.get("obj_type", obj_type),
        }
    except Exception as e:
        return {"error": str(e)}


async def _move_node(
    client: FeishuClient,
    space_id: str | None,
    token: str | None,
    target_space_id: str | None,
    target_parent_token: str | None,
) -> dict[str, Any]:
    if not space_id or not token:
        return {"error": "space_id and token are required"}

    node_token = extract_wiki_token(token)

    try:
        data: dict[str, Any] = {}
        if target_space_id:
            data["target_space_id"] = target_space_id
        if target_parent_token:
            data["target_parent_token"] = target_parent_token

        result = await client.post(f"wiki/v2/spaces/{space_id}/nodes/{node_token}/move", data=data)
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _rename_node(client: FeishuClient, space_id: str | None, token: str | None, title: str | None) -> dict[str, Any]:
    if not space_id or not token or not title:
        return {"error": "space_id, token, and title are required"}

    node_token = extract_wiki_token(token)

    try:
        result = await client.patch(f"wiki/v2/spaces/{space_id}/nodes/{node_token}", data={"title": title})
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}
