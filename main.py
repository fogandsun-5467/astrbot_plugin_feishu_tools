from __future__ import annotations

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.provider.func_tool_manager import FuncTool

from .feishu_tools_client import FeishuClient
from .feishu_tools_client.tools import (
    create_bitable_tool,
    create_calendar_tool,
    create_chat_tool,
    create_doc_tool,
    create_drive_tool,
    create_message_tool,
    create_perm_tool,
    create_reaction_tool,
    create_sheets_tool,
    create_task_tool,
    create_urgent_tool,
    create_wiki_tool,
)


@register(
    "astrbot_plugin_feishu_tools",
    "AstrBot",
    "飞书工具集：为飞书机器人提供文档、云盘、任务、群聊管理等高级功能",
    "1.0.0",
    "https://github.com/AstrBotDevs/astrbot_plugin_feishu_tools",
)
class FeishuToolsPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.feishu_client: FeishuClient | None = None
        self._registered_tools: list[FuncTool] = []

    @filter.platform_adapter_type(filter.PlatformAdapterType.LARK)
    async def initialize(self):
        lark_adapter = None
        for platform in self.context.platform_manager.platform_insts:
            if platform.meta().name == "lark":
                lark_adapter = platform
                break

        if not lark_adapter:
            logger.warning(
                "[FeishuTools] 未找到飞书平台适配器。请确保已在 AstrBot 中配置并启用飞书机器人。"
            )
            return

        try:
            app_id = lark_adapter.appid
            app_secret = lark_adapter.appsecret
            domain = lark_adapter.domain

            self.feishu_client = FeishuClient(
                app_id=app_id,
                app_secret=app_secret,
                domain=domain,
            )

            logger.info(f"[FeishuTools] 飞书客户端初始化成功，domain: {domain}")

            await self._register_tools()

        except Exception as e:
            logger.error(f"[FeishuTools] 初始化飞书客户端失败: {e}")

    async def _register_tools(self):
        if not self.feishu_client:
            logger.error("[FeishuTools] 飞书客户端未初始化，无法注册工具")
            return

        enabled_tools = self.config.get(
            "enabled_tools",
            [
                "message",
                "chat",
                "doc",
                "drive",
                "task",
                "bitable",
                "calendar",
                "sheets",
                "wiki",
                "reaction",
                "perm",
                "urgent",
            ],
        )

        tool_factories = {
            "message": lambda: create_message_tool(self.feishu_client),
            "chat": lambda: create_chat_tool(self.feishu_client),
            "doc": lambda: create_doc_tool(self.feishu_client),
            "drive": lambda: create_drive_tool(self.feishu_client),
            "task": lambda: create_task_tool(self.feishu_client),
            "bitable": lambda: create_bitable_tool(self.feishu_client),
            "calendar": lambda: create_calendar_tool(self.feishu_client),
            "sheets": lambda: create_sheets_tool(self.feishu_client),
            "wiki": lambda: create_wiki_tool(self.feishu_client),
            "reaction": lambda: create_reaction_tool(self.feishu_client),
            "perm": lambda: create_perm_tool(self.feishu_client),
            "urgent": lambda: create_urgent_tool(self.feishu_client),
        }

        perm_tool_config = self.config.get("perm_tool", {})
        if not perm_tool_config.get("enabled", False) and "perm" in enabled_tools:
            enabled_tools = [t for t in enabled_tools if t != "perm"]
            logger.info("[FeishuTools] 权限工具已禁用（敏感操作）")

        for tool_name in enabled_tools:
            if tool_name not in tool_factories:
                logger.warning(f"[FeishuTools] 未知的工具名称: {tool_name}")
                continue

            try:
                tool = tool_factories[tool_name]()
                self.context.add_llm_tools(tool)
                self._registered_tools.append(tool)
                logger.info(f"[FeishuTools] 已注册工具: {tool.name}")
            except Exception as e:
                logger.error(f"[FeishuTools] 注册工具 {tool_name} 失败: {e}")

        logger.info(f"[FeishuTools] 共注册 {len(self._registered_tools)} 个工具")

    @filter.command("feishu_tools")
    async def show_tools(self, event: AstrMessageEvent):
        """查看飞书工具集状态"""
        if not self.feishu_client:
            yield event.plain_result("飞书客户端未初始化，请检查飞书平台配置。")
            return

        tool_names = [tool.name for tool in self._registered_tools]
        if tool_names:
            yield event.plain_result(
                f"飞书工具集已启用，当前注册的工具：\n" + "\n".join(f"- {name}" for name in tool_names)
            )
        else:
            yield event.plain_result("飞书工具集已启用，但未注册任何工具。")

    @filter.command("feishu_test")
    async def test_connection(self, event: AstrMessageEvent):
        """测试飞书 API 连接"""
        if not self.feishu_client:
            yield event.plain_result("飞书客户端未初始化。")
            return

        try:
            token = await self.feishu_client.get_tenant_access_token()
            if token:
                yield event.plain_result("✅ 飞书 API 连接成功！")
            else:
                yield event.plain_result("❌ 获取访问令牌失败。")
        except Exception as e:
            yield event.plain_result(f"❌ 连接测试失败: {e}")

    async def terminate(self):
        if self.feishu_client:
            await self.feishu_client.close()
        logger.info("[FeishuTools] 插件已卸载")
