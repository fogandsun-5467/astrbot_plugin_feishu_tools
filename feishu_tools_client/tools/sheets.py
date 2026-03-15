from __future__ import annotations

from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient


def create_sheets_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        spreadsheet_token: str | None = None,
        sheet_id: str | None = None,
        range_: str | None = None,
        value_render_option: str = "ToString",
        date_time_render_option: str = "FormattedString",
        values: list | None = None,
        title: str | None = None,
        index: int | None = None,
        name: str | None = None,
        hidden: int | None = None,
        row_count: int | None = None,
        column_count: int | None = None,
        start_row: int | None = None,
        start_column: int | None = None,
        end_row: int | None = None,
        end_column: int | None = None,
        insert_data_option: str = "Overwrite",
        major_dimension: str = "ROWS",
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "get": lambda: _get_spreadsheet(client, spreadsheet_token),
            "create": lambda: _create_spreadsheet(client, title),
            "list_sheets": lambda: _list_sheets(client, spreadsheet_token),
            "create_sheet": lambda: _create_sheet(client, spreadsheet_token, title, index),
            "update_sheet": lambda: _update_sheet(client, spreadsheet_token, sheet_id, title, hidden, index),
            "delete_sheet": lambda: _delete_sheet(client, spreadsheet_token, sheet_id),
            "read": lambda: _read_cells(
                client, spreadsheet_token, range_, value_render_option, date_time_render_option
            ),
            "write": lambda: _write_cells(
                client, spreadsheet_token, range_, values, major_dimension
            ),
            "batch_read": lambda: _batch_read_cells(
                client, spreadsheet_token, range_, value_render_option, date_time_render_option
            ),
            "batch_write": lambda: _batch_write_cells(
                client, spreadsheet_token, values
            ),
            "insert_rows": lambda: _insert_rows(client, spreadsheet_token, sheet_id, start_row, row_count),
            "insert_columns": lambda: _insert_columns(client, spreadsheet_token, sheet_id, start_column, column_count),
            "delete_rows": lambda: _delete_rows(client, spreadsheet_token, sheet_id, start_row, end_row),
            "delete_columns": lambda: _delete_columns(client, spreadsheet_token, sheet_id, start_column, end_column),
            "merge_cells": lambda: _merge_cells(client, spreadsheet_token, range_),
            "unmerge_cells": lambda: _unmerge_cells(client, spreadsheet_token, range_),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_sheets",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "get",
                        "create",
                        "list_sheets",
                        "create_sheet",
                        "update_sheet",
                        "delete_sheet",
                        "read",
                        "write",
                        "batch_read",
                        "batch_write",
                        "insert_rows",
                        "insert_columns",
                        "delete_rows",
                        "delete_columns",
                        "merge_cells",
                        "unmerge_cells",
                    ],
                    "description": "操作类型",
                },
                "spreadsheet_token": {
                    "type": "string",
                    "description": "电子表格 token，除 create 外的操作必填",
                },
                "sheet_id": {
                    "type": "string",
                    "description": "工作表 ID，工作表相关操作必填",
                },
                "range_": {
                    "type": "string",
                    "description": "单元格范围，格式：'Sheet1!A1:B10' 或 'A1:B10'（默认第一个工作表）",
                },
                "value_render_option": {
                    "type": "string",
                    "enum": ["ToString", "Formula", "FormattedValue"],
                    "default": "ToString",
                    "description": "值渲染方式：ToString（文本）、Formula（公式）、FormattedValue（格式化值）",
                },
                "date_time_render_option": {
                    "type": "string",
                    "enum": ["FormattedString", "SerialDateTime"],
                    "default": "FormattedString",
                    "description": "日期时间渲染方式",
                },
                "values": {
                    "type": "array",
                    "items": {"type": "array"},
                    "description": "单元格数据，二维数组格式。write 操作必填；batch_write 时格式为 [{range: '...', values: [[...]]}]",
                },
                "title": {
                    "type": "string",
                    "description": "电子表格/工作表标题，create/create_sheet 操作必填",
                },
                "index": {
                    "type": "integer",
                    "description": "工作表位置索引，create_sheet/update_sheet 操作可选",
                },
                "hidden": {
                    "type": "integer",
                    "enum": [0, 1],
                    "description": "是否隐藏工作表，0: 显示，1: 隐藏",
                },
                "row_count": {
                    "type": "integer",
                    "description": "插入/删除的行数",
                },
                "column_count": {
                    "type": "integer",
                    "description": "插入/删除的列数",
                },
                "start_row": {
                    "type": "integer",
                    "description": "起始行索引（从 0 开始）",
                },
                "start_column": {
                    "type": "integer",
                    "description": "起始列索引（从 0 开始）",
                },
                "end_row": {
                    "type": "integer",
                    "description": "结束行索引（delete_rows 操作必填）",
                },
                "end_column": {
                    "type": "integer",
                    "description": "结束列索引（delete_columns 操作必填）",
                },
                "insert_data_option": {
                    "type": "string",
                    "enum": ["Overwrite", "Insert"],
                    "default": "Overwrite",
                    "description": "写入方式：Overwrite（覆盖）、Insert（插入）",
                },
                "major_dimension": {
                    "type": "string",
                    "enum": ["ROWS", "COLUMNS"],
                    "default": "ROWS",
                    "description": "数据维度：ROWS（按行）、COLUMNS（按列）",
                },
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark电子表格工具】当用户提到飞书电子表格、Spreadsheet、Sheet、单元格、读写数据时使用此工具。支持创建/管理电子表格和工作表、读写单元格数据。\n\n"
        "Actions:\n"
        "- get：获取电子表格信息，需要 spreadsheet_token\n"
        "- create：创建电子表格，需要 title\n"
        "- list_sheets：列出工作表，需要 spreadsheet_token\n"
        "- create_sheet：创建工作表，需要 spreadsheet_token、title\n"
        "- update_sheet：更新工作表，需要 spreadsheet_token、sheet_id\n"
        "- delete_sheet：删除工作表，需要 spreadsheet_token、sheet_id\n"
        "- read：读取单元格，需要 spreadsheet_token、range_\n"
        "- write：写入单元格，需要 spreadsheet_token、range_、values\n"
        "- batch_read：批量读取，range_ 支持多个范围（逗号分隔）\n"
        "- batch_write：批量写入，values 格式：[{range: '...', values: [[...]]}]\n"
        "- insert_rows：插入行，需要 spreadsheet_token、sheet_id、start_row、row_count\n"
        "- insert_columns：插入列，需要 spreadsheet_token、sheet_id、start_column、column_count\n"
        "- delete_rows：删除行，需要 spreadsheet_token、sheet_id、start_row、end_row\n"
        "- delete_columns：删除列，需要 spreadsheet_token、sheet_id、start_column、end_column\n"
        "- merge_cells：合并单元格，需要 spreadsheet_token、range_\n"
        "- unmerge_cells：取消合并，需要 spreadsheet_token、range_\n\n"
        "【范围格式】range_ 使用 A1 表示法，如 'Sheet1!A1:B10' 或 'A1:B10'。",
        handler=handler,
    )


async def _get_spreadsheet(client: FeishuClient, spreadsheet_token: str | None) -> dict[str, Any]:
    if not spreadsheet_token:
        return {"error": "spreadsheet_token is required"}

    try:
        result = await client.get(f"sheets/v3/spreadsheets/{spreadsheet_token}")
        spreadsheet = result.get("data", {}).get("spreadsheet", {})
        return {
            "ok": True,
            "spreadsheet": {
                "token": spreadsheet.get("token", ""),
                "title": spreadsheet.get("title", ""),
                "url": f"https://feishu.cn/sheets/{spreadsheet.get('token', '')}",
                "owner": spreadsheet.get("owner", {}),
                "created_time": spreadsheet.get("created_time", ""),
                "modified_time": spreadsheet.get("modified_time", ""),
            },
        }
    except Exception as e:
        return {"error": str(e)}


async def _create_spreadsheet(client: FeishuClient, title: str | None) -> dict[str, Any]:
    if not title:
        return {"error": "title is required"}

    try:
        result = await client.post(
            "sheets/v3/spreadsheets",
            data={"title": title},
        )
        spreadsheet = result.get("data", {}).get("spreadsheet", {})
        return {
            "ok": True,
            "spreadsheet_token": spreadsheet.get("token", ""),
            "title": spreadsheet.get("title", title),
            "url": f"https://feishu.cn/sheets/{spreadsheet.get('token', '')}",
        }
    except Exception as e:
        return {"error": str(e)}


async def _list_sheets(client: FeishuClient, spreadsheet_token: str | None) -> dict[str, Any]:
    if not spreadsheet_token:
        return {"error": "spreadsheet_token is required"}

    try:
        result = await client.get(f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets/query")
        sheets = result.get("data", {}).get("sheets", [])

        formatted_sheets = [
            {
                "sheet_id": s.get("sheet_id", ""),
                "title": s.get("title", ""),
                "index": s.get("index", 0),
                "row_count": s.get("grid_properties", {}).get("row_count", 0),
                "column_count": s.get("grid_properties", {}).get("column_count", 0),
                "hidden": s.get("hidden", False),
            }
            for s in sheets
        ]

        return {"ok": True, "sheets": formatted_sheets}
    except Exception as e:
        return {"error": str(e)}


async def _create_sheet(
    client: FeishuClient,
    spreadsheet_token: str | None,
    title: str | None,
    index: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not title:
        return {"error": "spreadsheet_token and title are required"}

    try:
        data: dict[str, Any] = {"title": title}
        if index is not None:
            data["index"] = index

        result = await client.post(
            f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets",
            data=data,
        )
        sheet = result.get("data", {}).get("sheet", {})
        return {
            "ok": True,
            "sheet_id": sheet.get("sheet_id", ""),
            "title": sheet.get("title", title),
        }
    except Exception as e:
        return {"error": str(e)}


async def _update_sheet(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
    title: str | None,
    hidden: int | None,
    index: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id:
        return {"error": "spreadsheet_token and sheet_id are required"}

    try:
        data: dict[str, Any] = {}
        if title:
            data["title"] = title
        if hidden is not None:
            data["hidden"] = hidden
        if index is not None:
            data["index"] = index

        result = await client.put(
            f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}",
            data=data,
        )
        sheet = result.get("data", {}).get("sheet", {})
        return {"ok": True, "sheet": sheet}
    except Exception as e:
        return {"error": str(e)}


async def _delete_sheet(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id:
        return {"error": "spreadsheet_token and sheet_id are required"}

    try:
        await client.delete(f"sheets/v3/spreadsheets/{spreadsheet_token}/sheets/{sheet_id}")
        return {"ok": True, "sheet_id": sheet_id}
    except Exception as e:
        return {"error": str(e)}


async def _read_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    range_: str | None,
    value_render_option: str,
    date_time_render_option: str,
) -> dict[str, Any]:
    if not spreadsheet_token or not range_:
        return {"error": "spreadsheet_token and range_ are required"}

    try:
        params = {
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": date_time_render_option,
        }

        result = await client.get(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/values/{range_}",
            params=params,
        )
        value_range = result.get("data", {}).get("valueRange", {})
        return {
            "ok": True,
            "range": value_range.get("range", ""),
            "values": value_range.get("values", []),
            "major_dimension": value_range.get("majorDimension", "ROWS"),
        }
    except Exception as e:
        return {"error": str(e)}


async def _write_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    range_: str | None,
    values: list | None,
    major_dimension: str,
) -> dict[str, Any]:
    if not spreadsheet_token or not range_ or not values:
        return {"error": "spreadsheet_token, range_, and values are required"}

    try:
        result = await client.put(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/values",
            data={
                "range": range_,
                "values": values,
                "majorDimension": major_dimension,
            },
        )
        return {
            "ok": True,
            "spreadsheet_token": spreadsheet_token,
            "range": range_,
            "updated_cells": result.get("data", {}).get("updatedCells", 0),
            "updated_rows": result.get("data", {}).get("updatedRows", 0),
            "updated_columns": result.get("data", {}).get("updatedColumns", 0),
        }
    except Exception as e:
        return {"error": str(e)}


async def _batch_read_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    range_: str | None,
    value_render_option: str,
    date_time_render_option: str,
) -> dict[str, Any]:
    if not spreadsheet_token or not range_:
        return {"error": "spreadsheet_token and range_ are required"}

    try:
        ranges = [r.strip() for r in range_.split(",")]

        result = await client.get(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_get",
            params={
                "ranges": ranges,
                "valueRenderOption": value_render_option,
                "dateTimeRenderOption": date_time_render_option,
            },
        )
        value_ranges = result.get("data", {}).get("valueRanges", [])

        return {
            "ok": True,
            "ranges": [
                {
                    "range": vr.get("range", ""),
                    "values": vr.get("values", []),
                }
                for vr in value_ranges
            ],
        }
    except Exception as e:
        return {"error": str(e)}


async def _batch_write_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    values: list | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not values:
        return {"error": "spreadsheet_token and values are required"}

    try:
        data_values = []
        for item in values:
            if isinstance(item, dict) and "range" in item and "values" in item:
                data_values.append({
                    "range": item["range"],
                    "values": item["values"],
                })

        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/values_batch_update",
            data={"valueRanges": data_values},
        )
        return {
            "ok": True,
            "total_updated_cells": result.get("data", {}).get("totalUpdatedCells", 0),
            "total_updated_rows": result.get("data", {}).get("totalUpdatedRows", 0),
            "total_updated_columns": result.get("data", {}).get("totalUpdatedColumns", 0),
        }
    except Exception as e:
        return {"error": str(e)}


async def _insert_rows(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
    start_row: int | None,
    row_count: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id or start_row is None or not row_count:
        return {"error": "spreadsheet_token, sheet_id, start_row, and row_count are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/insert_rows",
            data={
                "sheet_id": sheet_id,
                "start_row": start_row,
                "row_count": row_count,
            },
        )
        return {"ok": True, "inserted_rows": row_count}
    except Exception as e:
        return {"error": str(e)}


async def _insert_columns(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
    start_column: int | None,
    column_count: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id or start_column is None or not column_count:
        return {"error": "spreadsheet_token, sheet_id, start_column, and column_count are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/insert_columns",
            data={
                "sheet_id": sheet_id,
                "start_column": start_column,
                "column_count": column_count,
            },
        )
        return {"ok": True, "inserted_columns": column_count}
    except Exception as e:
        return {"error": str(e)}


async def _delete_rows(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
    start_row: int | None,
    end_row: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id or start_row is None or end_row is None:
        return {"error": "spreadsheet_token, sheet_id, start_row, and end_row are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/delete_rows",
            data={
                "sheet_id": sheet_id,
                "start_row": start_row,
                "end_row": end_row,
            },
        )
        return {"ok": True, "deleted_rows": end_row - start_row + 1}
    except Exception as e:
        return {"error": str(e)}


async def _delete_columns(
    client: FeishuClient,
    spreadsheet_token: str | None,
    sheet_id: str | None,
    start_column: int | None,
    end_column: int | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not sheet_id or start_column is None or end_column is None:
        return {"error": "spreadsheet_token, sheet_id, start_column, and end_column are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/delete_columns",
            data={
                "sheet_id": sheet_id,
                "start_column": start_column,
                "end_column": end_column,
            },
        )
        return {"ok": True, "deleted_columns": end_column - start_column + 1}
    except Exception as e:
        return {"error": str(e)}


async def _merge_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    range_: str | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not range_:
        return {"error": "spreadsheet_token and range_ are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/merge_cells",
            data={"range": range_},
        )
        return {"ok": True, "range": range_}
    except Exception as e:
        return {"error": str(e)}


async def _unmerge_cells(
    client: FeishuClient,
    spreadsheet_token: str | None,
    range_: str | None,
) -> dict[str, Any]:
    if not spreadsheet_token or not range_:
        return {"error": "spreadsheet_token and range_ are required"}

    try:
        result = await client.post(
            f"sheets/v2/spreadsheets/{spreadsheet_token}/unmerge_cells",
            data={"range": range_},
        )
        return {"ok": True, "range": range_}
    except Exception as e:
        return {"error": str(e)}
