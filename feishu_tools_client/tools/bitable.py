from __future__ import annotations

from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


def create_bitable_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        app_token: str | None = None,
        table_id: str | None = None,
        record_id: str | None = None,
        field_id: str | None = None,
        view_id: str | None = None,
        name: str | None = None,
        fields: dict | None = None,
        field_name: str | None = None,
        field_type: int | None = None,
        property: dict | None = None,
        page_size: int = 50,
        page_token: str | None = None,
        view: str | None = None,
        field_names: list | None = None,
        sort: list | None = None,
        filter: str | None = None,
        automatic_fields: bool = False,
        text_field_as_array: bool = True,
        user_id_type: str = "open_id",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "create": lambda: _create_app(client, name),
            "get": lambda: _get_app(client, app_token),
            "list_tables": lambda: _list_tables(client, app_token, page_size, page_token),
            "create_table": lambda: _create_table(client, app_token, name),
            "list_records": lambda: _list_records(
                client, app_token, table_id, view_id, page_size, page_token, view, field_names, sort, filter,
                automatic_fields, text_field_as_array, user_id_type
            ),
            "get_record": lambda: _get_record(client, app_token, table_id, record_id, automatic_fields, text_field_as_array, user_id_type),
            "create_record": lambda: _create_record(client, app_token, table_id, fields, user_id_type),
            "update_record": lambda: _update_record(client, app_token, table_id, record_id, fields, user_id_type),
            "delete_record": lambda: _delete_record(client, app_token, table_id, record_id),
            "batch_create_records": lambda: _batch_create_records(client, app_token, table_id, fields, user_id_type),
            "batch_update_records": lambda: _batch_update_records(client, app_token, table_id, fields, user_id_type),
            "batch_delete_records": lambda: _batch_delete_records(client, app_token, table_id, fields),
            "list_fields": lambda: _list_fields(client, app_token, table_id, view_id),
            "create_field": lambda: _create_field(client, app_token, table_id, field_name, field_type, property),
            "update_field": lambda: _update_field(client, app_token, table_id, field_id, field_name, property),
            "delete_field": lambda: _delete_field(client, app_token, table_id, field_id),
            "list_views": lambda: _list_views(client, app_token, table_id, page_size, page_token),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_bitable",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "create",
                        "get",
                        "list_tables",
                        "create_table",
                        "list_records",
                        "get_record",
                        "create_record",
                        "update_record",
                        "delete_record",
                        "batch_create_records",
                        "batch_update_records",
                        "batch_delete_records",
                        "list_fields",
                        "create_field",
                        "update_field",
                        "delete_field",
                        "list_views",
                    ],
                    "description": "操作类型",
                },
                "app_token": {
                    "type": "string",
                    "description": "多维表格 app_token，除 create 外的操作必填",
                },
                "table_id": {
                    "type": "string",
                    "description": "数据表 ID，表/记录/字段相关操作必填",
                },
                "record_id": {
                    "type": "string",
                    "description": "记录 ID，get_record/update_record/delete_record 操作必填",
                },
                "field_id": {
                    "type": "string",
                    "description": "字段 ID，update_field/delete_field 操作必填",
                },
                "view_id": {
                    "type": "string",
                    "description": "视图 ID，list_records/list_fields 操作可选",
                },
                "name": {
                    "type": "string",
                    "description": "名称，create/create_table 操作必填",
                },
                "fields": {
                    "type": "object",
                    "description": "记录字段值，create_record/update_record 操作必填。格式：{字段名: 值}。batch 操作时为 records 数组",
                },
                "field_name": {
                    "type": "string",
                    "description": "字段名称，create_field 操作必填",
                },
                "field_type": {
                    "type": "integer",
                    "description": "字段类型。1:文本 2:数字 3:单选 4:多选 5:日期 7:复选框 11:人员 13:电话 15:网址 17:附件 18:关联 19:公式 20:双向关联 21:位置 22:群组 23:条码 24:进度条 25:货币 26:评分",
                },
                "property": {
                    "type": "object",
                    "description": "字段属性配置",
                },
                "page_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "每页数量",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记",
                },
                "view": {
                    "type": "string",
                    "description": "视图名称，list_records 操作可选",
                },
                "field_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "返回字段名列表，list_records 操作可选",
                },
                "sort": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_name": {"type": "string"},
                            "desc": {"type": "boolean"},
                        },
                    },
                    "description": "排序条件，list_records 操作可选",
                },
                "filter": {
                    "type": "string",
                    "description": "筛选条件，list_records 操作可选。示例：'CurrentValue.[字段名]=\"值\"'",
                },
                "automatic_fields": {
                    "type": "boolean",
                    "default": false,
                    "description": "是否自动识别字段类型",
                },
                "text_field_as_array": {
                    "type": "boolean",
                    "default": true,
                    "description": "文本字段是否返回数组格式",
                },
                "user_id_type": {
                    "type": "string",
                    "enum": ["open_id", "user_id", "union_id"],
                    "default": "open_id",
                    "description": "用户 ID 类型",
                },
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark多维表格工具】当用户提到飞书多维表格、Bitable、Base、数据表、记录、字段时使用此工具。支持创建/查询多维表格、管理数据表、记录、字段和视图。\n\n"
        "Actions:\n"
        "- create：创建多维表格，需要 name\n"
        "- get：获取多维表格信息，需要 app_token\n"
        "- list_tables：列出数据表，需要 app_token\n"
        "- create_table：创建数据表，需要 app_token 和 name\n"
        "- list_records：列出记录，需要 app_token 和 table_id\n"
        "- get_record：获取记录详情，需要 app_token、table_id、record_id\n"
        "- create_record：创建记录，需要 app_token、table_id、fields\n"
        "- update_record：更新记录，需要 app_token、table_id、record_id、fields\n"
        "- delete_record：删除记录，需要 app_token、table_id、record_id\n"
        "- batch_create_records：批量创建记录，fields 为 records 数组\n"
        "- batch_update_records：批量更新记录，fields 为 records 数组\n"
        "- batch_delete_records：批量删除记录，fields 为 record_ids 数组\n"
        "- list_fields：列出字段，需要 app_token、table_id\n"
        "- create_field：创建字段，需要 app_token、table_id、field_name、field_type\n"
        "- update_field：更新字段，需要 app_token、table_id、field_id\n"
        "- delete_field：删除字段，需要 app_token、table_id、field_id\n"
        "- list_views：列出视图，需要 app_token、table_id\n\n"
        "【重要】fields 参数格式：{字段名: 值}。批量操作时 fields 格式：{records: [{fields: {...}}, ...]}",
        handler=handler,
    )


async def _create_app(client: FeishuClient, name: str | None) -> dict[str, Any]:
    if not name:
        return {"error": "name is required"}

    try:
        result = await client.post("bitable/v1/apps", data={"name": name})
        app = result.get("data", {}).get("app", {})
        return {
            "ok": True,
            "app_token": app.get("app_token", ""),
            "name": app.get("name", ""),
            "url": f"https://feishu.cn/base/{app.get('app_token', '')}",
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_app(client: FeishuClient, app_token: str | None) -> dict[str, Any]:
    if not app_token:
        return {"error": "app_token is required"}

    try:
        result = await client.get(f"bitable/v1/apps/{app_token}")
        app = result.get("data", {}).get("app", {})
        return {"ok": True, "app": app}
    except Exception as e:
        return {"error": str(e)}


async def _list_tables(
    client: FeishuClient,
    app_token: str | None,
    page_size: int,
    page_token: str | None,
) -> dict[str, Any]:
    if not app_token:
        return {"error": "app_token is required"}

    try:
        params: dict[str, Any] = {"page_size": min(max(page_size, 1), 100)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get(f"bitable/v1/apps/{app_token}/tables", params=params)
        items = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "tables": items,
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _create_table(client: FeishuClient, app_token: str | None, name: str | None) -> dict[str, Any]:
    if not app_token or not name:
        return {"error": "app_token and name are required"}

    try:
        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables",
            data={"table": {"name": name}},
        )
        table = result.get("data", {}).get("table", {})
        return {
            "ok": True,
            "table_id": table.get("table_id", ""),
            "name": table.get("name", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_records(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    view_id: str | None,
    page_size: int,
    page_token: str | None,
    view: str | None,
    field_names: list | None,
    sort: list | None,
    filter: str | None,
    automatic_fields: bool,
    text_field_as_array: bool,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id:
        return {"error": "app_token and table_id are required"}

    try:
        params: dict[str, Any] = {
            "page_size": min(max(page_size, 1), 500),
            "user_id_type": user_id_type,
            "automatic_fields": str(automatic_fields).lower(),
            "text_field_as_array": str(text_field_as_array).lower(),
        }
        if view_id:
            params["view_id"] = view_id
        if page_token:
            params["page_token"] = page_token
        if view:
            params["view"] = view
        if field_names:
            params["field_names"] = ",".join(field_names)
        if sort:
            params["sort"] = sort
        if filter:
            params["filter"] = filter

        result = await client.get(f"bitable/v1/apps/{app_token}/tables/{table_id}/records", params=params)
        items = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "records": items,
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
            "total": result.get("data", {}).get("total", 0),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_record(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    record_id: str | None,
    automatic_fields: bool,
    text_field_as_array: bool,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id or not record_id:
        return {"error": "app_token, table_id, and record_id are required"}

    try:
        params = {
            "user_id_type": user_id_type,
            "automatic_fields": str(automatic_fields).lower(),
            "text_field_as_array": str(text_field_as_array).lower(),
        }
        result = await client.get(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params=params,
        )
        record = result.get("data", {}).get("record", {})
        return {"ok": True, "record": record}
    except Exception as e:
        return {"error": str(e)}


async def _create_record(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    fields: dict | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id or not fields:
        return {"error": "app_token, table_id, and fields are required"}

    try:
        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records",
            data={"fields": fields},
            json_data={"user_id_type": user_id_type},
        )
        record = result.get("data", {}).get("record", {})
        return {"ok": True, "record_id": record.get("record_id", ""), "record": record}
    except Exception as e:
        return {"error": str(e)}


async def _update_record(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    record_id: str | None,
    fields: dict | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id or not record_id or not fields:
        return {"error": "app_token, table_id, record_id, and fields are required"}

    try:
        result = await client.put(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            data={"fields": fields},
            json_data={"user_id_type": user_id_type},
        )
        record = result.get("data", {}).get("record", {})
        return {"ok": True, "record": record}
    except Exception as e:
        return {"error": str(e)}


async def _delete_record(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    record_id: str | None,
) -> dict[str, Any]:
    if not app_token or not table_id or not record_id:
        return {"error": "app_token, table_id, and record_id are required"}

    try:
        result = await client.delete(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        )
        return {"ok": True, "record_id": record_id, "deleted": result.get("data", {}).get("deleted", False)}
    except Exception as e:
        return {"error": str(e)}


async def _batch_create_records(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    fields: dict | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id or not fields:
        return {"error": "app_token, table_id, and fields are required"}

    records = fields.get("records", [])
    if not records:
        return {"error": "fields must contain 'records' array"}

    try:
        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            data={"records": records},
            json_data={"user_id_type": user_id_type},
        )
        return {
            "ok": True,
            "records": result.get("data", {}).get("records", []),
        }
    except Exception as e:
        return {"error": str(e)}


async def _batch_update_records(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    fields: dict | None,
    user_id_type: str,
) -> dict[str, Any]:
    if not app_token or not table_id or not fields:
        return {"error": "app_token, table_id, and fields are required"}

    records = fields.get("records", [])
    if not records:
        return {"error": "fields must contain 'records' array"}

    try:
        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            data={"records": records},
            json_data={"user_id_type": user_id_type},
        )
        return {
            "ok": True,
            "records": result.get("data", {}).get("records", []),
        }
    except Exception as e:
        return {"error": str(e)}


async def _batch_delete_records(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    fields: dict | None,
) -> dict[str, Any]:
    if not app_token or not table_id or not fields:
        return {"error": "app_token, table_id, and fields are required"}

    record_ids = fields.get("record_ids", [])
    if not record_ids:
        return {"error": "fields must contain 'record_ids' array"}

    try:
        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete",
            data={"records": record_ids},
        )
        return {
            "ok": True,
            "deleted_count": len(result.get("data", {}).get("records", [])),
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_fields(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    view_id: str | None,
) -> dict[str, Any]:
    if not app_token or not table_id:
        return {"error": "app_token and table_id are required"}

    try:
        params = {}
        if view_id:
            params["view_id"] = view_id

        result = await client.get(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            params=params,
        )
        items = result.get("data", {}).get("items", [])

        return {"ok": True, "fields": items}
    except Exception as e:
        return {"error": str(e)}


async def _create_field(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    field_name: str | None,
    field_type: int | None,
    property: dict | None,
) -> dict[str, Any]:
    if not app_token or not table_id or not field_name or field_type is None:
        return {"error": "app_token, table_id, field_name, and field_type are required"}

    try:
        field_data: dict[str, Any] = {
            "field_name": field_name,
            "type": field_type,
        }
        if property:
            field_data["property"] = property

        result = await client.post(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            data={"field": field_data},
        )
        field = result.get("data", {}).get("field", {})
        return {
            "ok": True,
            "field_id": field.get("field_id", ""),
            "field_name": field.get("field_name", ""),
        }
    except Exception as e:
        return {"error": str(e)}


async def _update_field(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    field_id: str | None,
    field_name: str | None,
    property: dict | None,
) -> dict[str, Any]:
    if not app_token or not table_id or not field_id:
        return {"error": "app_token, table_id, and field_id are required"}

    try:
        field_data: dict[str, Any] = {}
        if field_name:
            field_data["field_name"] = field_name
        if property:
            field_data["property"] = property

        result = await client.put(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
            data={"field": field_data},
        )
        field = result.get("data", {}).get("field", {})
        return {"ok": True, "field": field}
    except Exception as e:
        return {"error": str(e)}


async def _delete_field(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    field_id: str | None,
) -> dict[str, Any]:
    if not app_token or not table_id or not field_id:
        return {"error": "app_token, table_id, and field_id are required"}

    try:
        result = await client.delete(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
        )
        return {"ok": True, "field_id": field_id, "deleted": result.get("data", {}).get("deleted", False)}
    except Exception as e:
        return {"error": str(e)}


async def _list_views(
    client: FeishuClient,
    app_token: str | None,
    table_id: str | None,
    page_size: int,
    page_token: str | None,
) -> dict[str, Any]:
    if not app_token or not table_id:
        return {"error": "app_token and table_id are required"}

    try:
        params: dict[str, Any] = {"page_size": min(max(page_size, 1), 100)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get(
            f"bitable/v1/apps/{app_token}/tables/{table_id}/views",
            params=params,
        )
        items = result.get("data", {}).get("items", [])

        return {
            "ok": True,
            "views": items,
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}
