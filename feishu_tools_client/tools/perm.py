from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


MEMBER_TYPES = ["email", "openid", "userid", "unionid", "openchat", "opendepartmentid"]
PERMISSION_LEVELS = ["view", "edit", "full_access"]
FILE_TYPES = ["doc", "docx", "sheet", "bitable", "folder", "file", "wiki", "mindnote"]


def create_perm_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        token: str | None = None,
        type: str | None = None,
        member_type: str | None = None,
        member_id: str | None = None,
        perm: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "list": lambda: _list_collaborators(client, token, type),
            "add": lambda: _add_collaborator(client, token, type, member_type, member_id, perm),
            "remove": lambda: _remove_collaborator(client, token, type, member_type, member_id),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_perm",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "add", "remove"],
                    "description": "Action to perform",
                },
                "token": {"type": "string", "description": "File/document token"},
                "type": {
                    "type": "string",
                    "enum": FILE_TYPES,
                    "description": "File type",
                },
                "member_type": {
                    "type": "string",
                    "enum": MEMBER_TYPES,
                    "description": "Member type for add/remove operations",
                },
                "member_id": {"type": "string", "description": "Member ID (email, open_id, etc.)"},
                "perm": {
                    "type": "string",
                    "enum": PERMISSION_LEVELS,
                    "description": "Permission level for add operation",
                },
            },
            "required": ["action", "token", "type"],
        },
        description="【飞书/Feishu/Lark权限工具】当用户提到飞书权限、分享、协作者、共享时使用此工具。支持管理文档/文件协作者权限。注意：此工具涉及敏感操作，默认禁用。",
        handler=handler,
    )


async def _list_collaborators(client: FeishuClient, token: str | None, file_type: str | None) -> dict[str, Any]:
    if not token or not file_type:
        return {"error": "token and type are required"}

    try:
        result = await client.get(f"drive/v1/permissions/{token}/members", params={"type": file_type})
        members = result.get("data", {}).get("members", [])

        return {
            "members": [
                {
                    "member_type": m.get("member_type", ""),
                    "member_id": m.get("member_id", ""),
                    "perm": m.get("perm", ""),
                    "name": m.get("name", ""),
                }
                for m in members
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def _add_collaborator(
    client: FeishuClient,
    token: str | None,
    file_type: str | None,
    member_type: str | None,
    member_id: str | None,
    perm: str | None,
) -> dict[str, Any]:
    if not token or not file_type or not member_type or not member_id or not perm:
        return {"error": "token, type, member_type, member_id, and perm are required"}

    try:
        result = await client.post(
            f"drive/v1/permissions/{token}/members",
            data={
                "type": file_type,
                "member_type": member_type,
                "member_id": member_id,
                "perm": perm,
            },
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _remove_collaborator(
    client: FeishuClient,
    token: str | None,
    file_type: str | None,
    member_type: str | None,
    member_id: str | None,
) -> dict[str, Any]:
    if not token or not file_type or not member_type or not member_id:
        return {"error": "token, type, member_type, and member_id are required"}

    try:
        await client.delete(
            f"drive/v1/permissions/{token}/members",
            params={"type": file_type},
            data={"member_type": member_type, "member_id": member_id},
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
