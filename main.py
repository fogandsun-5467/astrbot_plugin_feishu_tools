from __future__ import annotations

import json
from typing import Any

from astrbot.api import AstrBotConfig, llm_tool, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

import lark_oapi as lark

from .feishu_client import FeishuClient


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
        self._init_done = False

    async def _init_feishu_client(self):
        if self._init_done:
            return

        self._init_done = True

        lark_adapter = None
        for platform in self.context.platform_manager.platform_insts:
            platform_meta = platform.meta()
            logger.debug(f"[FeishuTools] 检查平台: {platform_meta.name}")
            if platform_meta.name == "lark":
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

    @filter.on_platform_loaded()
    async def on_platform_loaded(self):
        logger.info("[FeishuTools] 平台加载完成，开始初始化飞书客户端")
        await self._init_feishu_client()

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        logger.info("[FeishuTools] AstrBot 加载完成，尝试初始化飞书客户端")
        await self._init_feishu_client()

    async def _register_tools(self):
        if not self.feishu_client:
            logger.error("[FeishuTools] 飞书客户端未初始化，无法注册工具")
            return

        tool_names = [
            "feishu_task",
            "feishu_calendar",
            "feishu_bitable",
            "feishu_doc",
            "feishu_drive",
            "feishu_sheets",
            "feishu_wiki",
            "feishu_chat",
            "feishu_message",
            "feishu_user",
        ]

        for tool_name in tool_names:
            self.context.activate_llm_tool(tool_name)

        logger.info(f"[FeishuTools] 共激活 {len(tool_names)} 个工具")

    async def terminate(self):
        if self.feishu_client:
            await self.feishu_client.close()
        logger.info("[FeishuTools] 插件已卸载")

    @llm_tool("feishu_task")
    async def feishu_task(
        self,
        event: AstrMessageEvent,
        action: str,
        summary: str = None,
        task_guid: str = None,
        description: str = None,
        due: dict = None,
        completed_at: str = None,
        current_user_id: str = None,
        members: list = None,
        page_size: int = 50,
        completed: bool = None,
    ) -> str:
        """飞书任务管理工具。用于创建、查询、更新任务。

        Args:
            action(string): 操作类型 ["create", "get", "list", "patch"]
            summary(string): 任务标题（create时必填）
            task_guid(string): 任务ID（get/patch时必填）
            description(string): 任务描述
            due(object): 截止时间配置 {"timestamp": "时间戳", "is_all_day": false}
            completed_at(string): 完成时间，设为 "0" 可反完成任务
            current_user_id(string): 当前用户的 open_id
            members(array): 任务成员列表 [{"id": "open_id", "role": "assignee|follower"}]
            page_size(number): 每页数量（默认50，最大100）
            completed(boolean): 是否筛选已完成任务

        Returns:
            str: 任务操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "create":
            if not summary:
                return json.dumps({"error": "summary is required"}, ensure_ascii=False)

            task_data: dict[str, Any] = {"summary": summary}

            if description:
                task_data["description"] = description

            if due:
                from .utils.time_utils import parse_time_to_timestamp

                due_ts = parse_time_to_timestamp(due.get("timestamp", ""))
                if due_ts:
                    task_data["due"] = {
                        "timestamp": str(due_ts),
                        "is_all_day": due.get("is_all_day", False),
                    }

            if members is None:
                members = []
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

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"创建任务失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                task = result.get("data", {}).get("task", {})
                return json.dumps({
                    "success": True,
                    "task_guid": task.get("guid"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"创建任务异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get":
            if not task_guid:
                return json.dumps({"error": "task_guid is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/task/v2/tasks/{task_guid}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("user_id_type", "open_id")]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取任务失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                task = result.get("data", {}).get("task", {})
                return json.dumps({"task": task}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取任务异常: {str(e)}"}, ensure_ascii=False)

        elif action == "list":
            try:
                queries = [("page_size", str(page_size))]
                if completed is not None:
                    queries.append(("completed", str(completed).lower()))

                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/task/v2/tasks") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries(queries) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"查询任务失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                return json.dumps({
                    "tasks": data.get("items", []),
                    "has_more": data.get("has_more", False),
                    "page_token": data.get("page_token"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"查询任务异常: {str(e)}"}, ensure_ascii=False)

        elif action == "patch":
            if not task_guid:
                return json.dumps({"error": "task_guid is required"}, ensure_ascii=False)

            update_data: dict[str, Any] = {}
            if summary:
                update_data["summary"] = summary
            if description:
                update_data["description"] = description
            if due:
                from .utils.time_utils import parse_time_to_timestamp

                due_ts = parse_time_to_timestamp(due.get("timestamp", ""))
                if due_ts:
                    update_data["due"] = {
                        "timestamp": str(due_ts),
                        "is_all_day": due.get("is_all_day", False),
                    }
            if completed_at is not None:
                update_data["completed_at"] = completed_at

            if not update_data:
                return json.dumps({"error": "no data to update"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.PATCH) \
                    .uri(f"/open-apis/task/v2/tasks/{task_guid}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("user_id_type", "open_id")]) \
                    .body(update_data) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"更新任务失败: {response.msg}"}, ensure_ascii=False)

                return json.dumps({"success": True, "task_guid": task_guid}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"更新任务异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_calendar")
    async def feishu_calendar(
        self,
        event: AstrMessageEvent,
        action: str,
        summary: str = None,
        start_time: str = None,
        end_time: str = None,
        description: str = None,
        event_id: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书日历日程管理工具。用于创建、查询日程。

        Args:
            action(string): 操作类型 ["create", "list", "get"]
            summary(string): 日程标题（create时必填）
            start_time(string): 开始时间（create/list时必填）
            end_time(string): 结束时间（create/list时必填）
            description(string): 日程描述
            event_id(string): 日程ID（get时必填）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 日程操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "create":
            if not summary or not start_time or not end_time:
                return json.dumps({"error": "summary, start_time and end_time are required"}, ensure_ascii=False)

            from .utils.time_utils import parse_time_to_timestamp

            start_ts = parse_time_to_timestamp(start_time)
            end_ts = parse_time_to_timestamp(end_time)
            if not start_ts or not end_ts:
                return json.dumps({"error": "Invalid time format"}, ensure_ascii=False)

            event_data = {
                "summary": summary,
                "start_time": {"timestamp": str(start_ts), "timezone": "Asia/Shanghai"},
                "end_time": {"timestamp": str(end_ts), "timezone": "Asia/Shanghai"},
            }
            if description:
                event_data["description"] = description

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.POST) \
                    .uri("/open-apis/calendar/v4/calendars/primary/events") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body(event_data) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"创建日程失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                evt = result.get("data", {}).get("event", {})
                return json.dumps({"success": True, "event_id": evt.get("event_id")}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"创建日程异常: {str(e)}"}, ensure_ascii=False)

        elif action == "list":
            if not start_time or not end_time:
                return json.dumps({"error": "start_time and end_time are required"}, ensure_ascii=False)

            from .utils.time_utils import parse_time_to_timestamp

            start_ts = parse_time_to_timestamp(start_time)
            end_ts = parse_time_to_timestamp(end_time)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/calendar/v4/calendars/primary/events") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([
                        ("start_time", str(start_ts)),
                        ("end_time", str(end_ts)),
                        ("page_size", str(page_size)),
                    ]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"查询日程失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                events = []
                for evt in data.get("events", []):
                    events.append({
                        "event_id": evt.get("event_id"),
                        "summary": evt.get("summary"),
                    })

                return json.dumps({"events": events, "has_more": data.get("has_more", False)}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"查询日程异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get":
            if not event_id:
                return json.dumps({"error": "event_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/calendar/v4/calendars/primary/events/{event_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取日程失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                evt = result.get("data", {}).get("event", {})
                return json.dumps({
                    "event": {
                        "event_id": evt.get("event_id"),
                        "summary": evt.get("summary"),
                        "description": evt.get("description"),
                    }
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取日程异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_bitable")
    async def feishu_bitable(
        self,
        event: AstrMessageEvent,
        action: str,
        app_token: str = None,
        table_id: str = None,
        record_id: str = None,
        fields: dict = None,
        page_size: int = 50,
    ) -> str:
        """飞书多维表格工具。用于操作多维表格数据。

        Args:
            action(string): 操作类型 ["list_records", "create_record", "update_record", "delete_record"]
            app_token(string): 多维表格的 app_token
            table_id(string): 表格 ID
            record_id(string): 记录 ID（update/delete 时必填）
            fields(object): 字段数据（create/update 时使用）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 多维表格操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "list_records":
            if not app_token or not table_id:
                return json.dumps({"error": "app_token and table_id are required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("page_size", str(page_size))]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"查询记录失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                records = []
                for rec in data.get("items", []):
                    records.append({
                        "record_id": rec.get("record_id"),
                        "fields": rec.get("fields"),
                    })

                return json.dumps({
                    "records": records,
                    "has_more": data.get("has_more", False),
                    "page_token": data.get("page_token"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"查询记录异常: {str(e)}"}, ensure_ascii=False)

        elif action == "create_record":
            if not app_token or not table_id or not fields:
                return json.dumps({"error": "app_token, table_id and fields are required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.POST) \
                    .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body({"fields": fields}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"创建记录失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                record = result.get("data", {}).get("record", {})
                return json.dumps({"success": True, "record_id": record.get("record_id")}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"创建记录异常: {str(e)}"}, ensure_ascii=False)

        elif action == "update_record":
            if not app_token or not table_id or not record_id or not fields:
                return json.dumps({"error": "app_token, table_id, record_id and fields are required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.PUT) \
                    .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body({"fields": fields}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"更新记录失败: {response.msg}"}, ensure_ascii=False)

                return json.dumps({"success": True}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"更新记录异常: {str(e)}"}, ensure_ascii=False)

        elif action == "delete_record":
            if not app_token or not table_id or not record_id:
                return json.dumps({"error": "app_token, table_id and record_id are required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.DELETE) \
                    .uri(f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"删除记录失败: {response.msg}"}, ensure_ascii=False)

                return json.dumps({"success": True}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"删除记录异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_doc")
    async def feishu_doc(
        self,
        event: AstrMessageEvent,
        action: str,
        title: str = None,
        folder_token: str = None,
        document_id: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书文档工具。用于创建和获取飞书文档。

        Args:
            action(string): 操作类型 ["create", "get", "get_blocks"]
            title(string): 文档标题（create 时必填）
            folder_token(string): 文件夹 token（可选）
            document_id(string): 文档 ID（get/get_blocks 时必填）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 文档操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "create":
            if not title:
                return json.dumps({"error": "title is required"}, ensure_ascii=False)

            body = {"title": title}
            if folder_token:
                body["folder_token"] = folder_token

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.POST) \
                    .uri("/open-apis/docx/v1/documents") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body(body) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"创建文档失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                doc = result.get("data", {}).get("document", {})
                return json.dumps({
                    "success": True,
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"创建文档异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get":
            if not document_id:
                return json.dumps({"error": "document_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/docx/v1/documents/{document_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取文档失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                doc = result.get("data", {}).get("document", {})
                return json.dumps({
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                    "revision_id": doc.get("revision_id"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取文档异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get_blocks":
            if not document_id:
                return json.dumps({"error": "document_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/docx/v1/documents/{document_id}/blocks") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("page_size", str(page_size))]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取文档块失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                return json.dumps({
                    "blocks": data.get("items", []),
                    "has_more": data.get("has_more", False),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取文档块异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_drive")
    async def feishu_drive(
        self,
        event: AstrMessageEvent,
        action: str,
        token: str = None,
        file_name: str = None,
        file_type: str = None,
        parent_node: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书云盘工具。用于操作云盘文件。

        Args:
            action(string): 操作类型 ["list", "upload", "get"]
            token(string): 文件或文件夹 token（get 时必填）
            file_name(string): 文件名（upload 时必填）
            file_type(string): 文件类型（upload 时必填，如 "xlsx", "docx", "pdf"）
            parent_node(string): 父文件夹 token（upload 时可选）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 云盘操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "list":
            if not token:
                return json.dumps({"error": "token is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/drive/v1/files/{token}/children") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("page_size", str(page_size))]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"列出文件失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                files = []
                for f in data.get("items", []):
                    files.append({
                        "token": f.get("token"),
                        "name": f.get("name"),
                        "type": f.get("type"),
                    })

                return json.dumps({
                    "files": files,
                    "has_more": data.get("has_more", False),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"列出文件异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get":
            if not token:
                return json.dumps({"error": "token is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/drive/v1/files/{token}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取文件信息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                file = result.get("data", {})
                return json.dumps({
                    "token": file.get("token"),
                    "name": file.get("name"),
                    "type": file.get("type"),
                    "size": file.get("size"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取文件信息异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_sheets")
    async def feishu_sheets(
        self,
        event: AstrMessageEvent,
        action: str,
        spreadsheet_token: str = None,
        sheet_id: str = None,
        range_str: str = None,
        values: list = None,
    ) -> str:
        """飞书电子表格工具。用于操作电子表格数据。

        Args:
            action(string): 操作类型 ["get", "read", "write"]
            spreadsheet_token(string): 电子表格的 token（必填）
            sheet_id(string): 工作表 ID（read/write 时必填）
            range_str(string): 范围，如 "A1:B10"（read/write 时必填）
            values(array): 要写入的数据（二维数组，write 时必填）

        Returns:
            str: 电子表格操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "get":
            if not spreadsheet_token:
                return json.dumps({"error": "spreadsheet_token is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/sheets/v3/spreadsheets/{spreadsheet_token}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取表格信息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                sheet = result.get("data", {})
                return json.dumps({
                    "spreadsheet_token": sheet.get("spreadsheet_token"),
                    "title": sheet.get("title"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取表格信息异常: {str(e)}"}, ensure_ascii=False)

        elif action == "read":
            if not spreadsheet_token or not sheet_id or not range_str:
                return json.dumps({"error": "spreadsheet_token, sheet_id and range_str are required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!{range_str}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"读取数据失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                return json.dumps({
                    "values": data.get("valueRange", {}).get("values", []),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"读取数据异常: {str(e)}"}, ensure_ascii=False)

        elif action == "write":
            if not spreadsheet_token or not sheet_id or not range_str or not values:
                return json.dumps({"error": "spreadsheet_token, sheet_id, range_str and values are required"}, ensure_ascii=False)

            try:
                body = {
                    "values": values,
                }
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.PUT) \
                    .uri(f"/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}!{range_str}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body(body) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"写入数据失败: {response.msg}"}, ensure_ascii=False)

                return json.dumps({"success": True}, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"写入数据异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_wiki")
    async def feishu_wiki(
        self,
        event: AstrMessageEvent,
        action: str,
        space_id: str = None,
        parent_node_token: str = None,
        node_token: str = None,
        title: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书知识库工具。用于操作知识库文档。

        Args:
            action(string): 操作类型 ["list_nodes", "get_node", "create_node"]
            space_id(string): 知识库空间 ID（必填）
            parent_node_token(string): 父节点 token（list_nodes/create_node 时使用）
            node_token(string): 知识库节点 token（get_node 时必填）
            title(string): 文档标题（create_node 时必填）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 知识库操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "list_nodes":
            if not space_id:
                return json.dumps({"error": "space_id is required"}, ensure_ascii=False)

            try:
                queries = [("space_id", space_id), ("page_size", str(page_size))]
                if parent_node_token:
                    queries.append(("parent_node_token", parent_node_token))

                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/wiki/v2/spaces/{}/nodes".format(space_id)) \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries(queries) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"列出节点失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                nodes = []
                for node in data.get("nodes", []):
                    nodes.append({
                        "node_token": node.get("node_token"),
                        "title": node.get("obj_type"),
                        "parent_node_token": node.get("parent_node_token"),
                    })

                return json.dumps({
                    "nodes": nodes,
                    "has_more": data.get("has_more", False),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"列出节点异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get_node":
            if not node_token:
                return json.dumps({"error": "node_token is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/wiki/v2/nodes/{node_token}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取节点失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                node = result.get("data", {})
                return json.dumps({
                    "node_token": node.get("node_token"),
                    "parent_node_token": node.get("parent_node_token"),
                    "obj_type": node.get("obj_type"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取节点异常: {str(e)}"}, ensure_ascii=False)

        elif action == "create_node":
            if not space_id or not title:
                return json.dumps({"error": "space_id and title are required"}, ensure_ascii=False)

            body = {
                "obj_type": "docx",
                "parent_node_token": parent_node_token or "",
                "origin": False,
            }

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.POST) \
                    .uri(f"/open-apis/wiki/v2/spaces/{space_id}/nodes") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .body(body) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"创建节点失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                node = result.get("data", {})
                return json.dumps({
                    "success": True,
                    "node_token": node.get("node_token"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"创建节点异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_chat")
    async def feishu_chat(
        self,
        event: AstrMessageEvent,
        action: str,
        chat_id: str = None,
        user_id: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书群聊工具。用于获取群聊信息。

        Args:
            action(string): 操作类型 ["get", "list_members"]
            chat_id(string): 群聊 ID（get/list_members 时必填）
            user_id(string): 用户 ID（可选）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 群聊操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "get":
            if not chat_id:
                return json.dumps({"error": "chat_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/im/v1/chats/{chat_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取群聊信息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                chat = result.get("data", {})
                return json.dumps({
                    "chat_id": chat.get("chat_id"),
                    "name": chat.get("name"),
                    "avatar": chat.get("avatar"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取群聊信息异常: {str(e)}"}, ensure_ascii=False)

        elif action == "list_members":
            if not chat_id:
                return json.dumps({"error": "chat_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/im/v1/chats/{chat_id}/members") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("page_size", str(page_size))]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"列出群成员失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                members = []
                for m in data.get("items", []):
                    members.append({
                        "id": m.get("id"),
                        "name": m.get("name"),
                    })

                return json.dumps({
                    "members": members,
                    "has_more": data.get("has_more", False),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"列出群成员异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_message")
    async def feishu_message(
        self,
        event: AstrMessageEvent,
        action: str,
        receive_id: str = None,
        receive_id_type: str = "open_id",
        msg_type: str = "text",
        content: str = None,
        message_id: str = None,
    ) -> str:
        """飞书消息工具。用于发送和获取消息。

        Args:
            action(string): 操作类型 ["send", "get"]
            receive_id(string): 接收者 ID（send 时必填）
            receive_id_type(string): 接收者 ID 类型 ["open_id", "user_id", "union_id", "chat_id"]
            msg_type(string): 消息类型 ["text", "post", "image", "file", "audio"]
            content(string): 消息内容（send 时必填，文本类型为字符串，其他类型为 JSON）
            message_id(string): 消息 ID（get 时必填）

        Returns:
            str: 消息操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "send":
            if not receive_id or not content:
                return json.dumps({"error": "receive_id and content are required"}, ensure_ascii=False)

            body = {
                "receive_id": receive_id,
                "receive_id_type": receive_id_type,
                "msg_type": msg_type,
                "content": content if msg_type == "text" else json.dumps(content),
            }

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.POST) \
                    .uri("/open-apis/im/v1/messages") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("receive_id_type", receive_id_type)]) \
                    .body(body) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"发送消息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                return json.dumps({
                    "success": True,
                    "message_id": result.get("data", {}).get("message_id"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"发送消息异常: {str(e)}"}, ensure_ascii=False)

        elif action == "get":
            if not message_id:
                return json.dumps({"error": "message_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/im/v1/messages/{message_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取消息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                msg = result.get("data", {})
                return json.dumps({
                    "message_id": msg.get("message_id"),
                    "msg_type": msg.get("msg_type"),
                    "content": msg.get("content"),
                    "create_time": msg.get("create_time"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取消息异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @llm_tool("feishu_user")
    async def feishu_user(
        self,
        event: AstrMessageEvent,
        action: str,
        user_id: str = None,
        page_size: int = 50,
    ) -> str:
        """飞书用户工具。用于获取用户信息。

        Args:
            action(string): 操作类型 ["get", "list"]
            user_id(string): 用户 ID（get 时必填）
            page_size(number): 每页数量（默认50）

        Returns:
            str: 用户操作结果
        """
        if not self.feishu_client:
            return json.dumps({"error": "飞书客户端未初始化"}, ensure_ascii=False)

        lark_client = self.feishu_client.get_client()

        if action == "get":
            if not user_id:
                return json.dumps({"error": "user_id is required"}, ensure_ascii=False)

            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri(f"/open-apis/im/v1/users/{user_id}") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"获取用户信息失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                user = result.get("data", {})
                return json.dumps({
                    "user_id": user.get("user_id"),
                    "open_id": user.get("open_id"),
                    "name": user.get("name"),
                    "avatar": user.get("avatar"),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"获取用户信息异常: {str(e)}"}, ensure_ascii=False)

        elif action == "list":
            try:
                request = lark.BaseRequest.builder() \
                    .http_method(lark.HttpMethod.GET) \
                    .uri("/open-apis/im/v1/users") \
                    .token_types({lark.AccessTokenType.TENANT}) \
                    .queries([("page_size", str(page_size))]) \
                    .build()

                response = await lark_client.arequest(request)

                if not response.success():
                    return json.dumps({"error": f"列出用户失败: {response.msg}"}, ensure_ascii=False)

                result = json.loads(str(response.raw.content, lark.UTF_8))
                data = result.get("data", {})
                users = []
                for u in data.get("items", []):
                    users.append({
                        "user_id": u.get("user_id"),
                        "open_id": u.get("open_id"),
                        "name": u.get("name"),
                    })

                return json.dumps({
                    "users": users,
                    "has_more": data.get("has_more", False),
                }, ensure_ascii=False)
            except Exception as e:
                return json.dumps({"error": f"列出用户异常: {str(e)}"}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unknown action: {action}"}, ensure_ascii=False)

    @filter.command("feishu_tools")
    async def show_tools(self, event: AstrMessageEvent):
        """查看飞书工具集状态"""
        if not self.feishu_client:
            yield event.plain_result("飞书客户端未初始化，请检查飞书平台配置。")
            return

        yield event.plain_result("飞书工具集已启用。")

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
