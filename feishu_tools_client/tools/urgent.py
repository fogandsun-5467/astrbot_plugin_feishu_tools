from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


URGENT_TYPES = ["app", "sms", "phone"]


def create_urgent_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        message_id: str | None = None,
        user_ids: list[str] | None = None,
        urgent_type: str = "app",
        **kwargs,
    ) -> dict[str, Any]:
        return await _send_urgent(client, message_id, user_ids, urgent_type)

    return FuncTool(
        name="feishu_urgent",
        parameters={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Message ID to send urgent notification for. The message must already be sent.",
                },
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of open_id values to buzz. Recipients must be members of the chat.",
                },
                "urgent_type": {
                    "type": "string",
                    "enum": URGENT_TYPES,
                    "default": "app",
                    "description": "Urgency type: app (free), sms (may cost), phone (may cost)",
                },
            },
            "required": ["message_id", "user_ids"],
        },
        description="【飞书/Feishu/Lark紧急通知工具】当用户提到飞书紧急通知、加急、提醒、电话通知、短信通知时使用此工具。支持发送应用内/短信/电话紧急通知。注意：消息必须已发送才能加急。",
        handler=handler,
    )


async def _send_urgent(
    client: FeishuClient,
    message_id: str | None,
    user_ids: list[str] | None,
    urgent_type: str,
) -> dict[str, Any]:
    if not message_id:
        return {"error": "message_id is required"}

    if not user_ids or len(user_ids) == 0:
        return {"error": "user_ids is required and must not be empty"}

    try:
        result = await client.post(
            f"im/v1/messages/{message_id}/urgent",
            data={"user_ids": user_ids, "urgent_type": urgent_type},
        )

        invalid_users = result.get("data", {}).get("invalid_user_list", [])

        return {
            "ok": True,
            "message_id": message_id,
            "urgent_type": urgent_type,
            "invalid_user_list": invalid_users,
        }
    except Exception as e:
        error_msg = str(e)
        if "230024" in error_msg:
            return {"error": "Quota exhausted. Contact your tenant admin or check Feishu admin console > Cost Center > Quota."}
        return {"error": error_msg}
