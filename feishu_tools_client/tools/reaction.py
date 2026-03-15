from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


EMOJI_TYPES = [
    "THUMBSUP", "THUMBSDOWN", "HEART", "SMILE", "GRINNING",
    "FIRE", "CLAP", "OK", "CHECK", "CROSS",
    "PARTY", "PRAY", "CRY", "ANGRY", "THINKING",
    "SURPRISED", "LAUGHING", "FIST", "QUESTION", "EXCLAMATION",
]


def create_reaction_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        message_id: str | None = None,
        emoji_type: str | None = None,
        reaction_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "add": lambda: _add_reaction(client, message_id, emoji_type),
            "remove": lambda: _remove_reaction(client, message_id, reaction_id),
            "list": lambda: _list_reactions(client, message_id, emoji_type),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_reaction",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "list"],
                    "description": "Action to perform",
                },
                "message_id": {"type": "string", "description": "Feishu message ID (e.g., om_xxx)"},
                "emoji_type": {
                    "type": "string",
                    "description": f"Emoji type. Common values: {', '.join(EMOJI_TYPES[:10])}",
                },
                "reaction_id": {"type": "string", "description": "Reaction ID from add or list results (for remove)"},
            },
            "required": ["action", "message_id"],
        },
        description="Feishu message emoji reactions. Use when user mentions emoji, reaction, thumbsup, like, or responding to messages with emoji.",
        handler=handler,
    )


async def _add_reaction(client: FeishuClient, message_id: str | None, emoji_type: str | None) -> dict[str, Any]:
    if not message_id or not emoji_type:
        return {"error": "message_id and emoji_type are required"}

    try:
        result = await client.post(
            f"im/v1/messages/{message_id}/reactions",
            data={"reaction_type": {"emoji_type": emoji_type}},
        )
        reaction = result.get("data", {}).get("reaction", {})
        return {
            "ok": True,
            "action": "add",
            "message_id": message_id,
            "emoji_type": emoji_type,
            "reaction_id": reaction.get("reaction_id", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _remove_reaction(client: FeishuClient, message_id: str | None, reaction_id: str | None) -> dict[str, Any]:
    if not message_id or not reaction_id:
        return {"error": "message_id and reaction_id are required"}

    try:
        await client.delete(f"im/v1/messages/{message_id}/reactions/{reaction_id}")
        return {"ok": True, "action": "remove", "message_id": message_id, "reaction_id": reaction_id}
    except Exception as e:
        return {"error": str(e)}


async def _list_reactions(client: FeishuClient, message_id: str | None, emoji_type: str | None) -> dict[str, Any]:
    if not message_id:
        return {"error": "message_id is required"}

    try:
        params: dict[str, Any] = {}
        if emoji_type:
            params["reaction_type"] = emoji_type

        result = await client.get(f"im/v1/messages/{message_id}/reactions", params=params)
        reactions = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "action": "list",
            "message_id": message_id,
            "emoji_type_filter": emoji_type,
            "total": len(reactions),
            "reactions": [
                {
                    "reaction_id": r.get("reaction_id", ""),
                    "emoji_type": r.get("reaction_type", {}).get("emoji_type", ""),
                    "operator_type": r.get("operator", {}).get("operator_type", ""),
                    "operator_id": r.get("operator", {}).get("id", ""),
                }
                for r in reactions
            ],
        }
    except Exception as e:
        return {"error": str(e)}
