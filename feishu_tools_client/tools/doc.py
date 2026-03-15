import json
from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, extract_doc_token


def create_doc_tool(client: FeishuClient) -> FuncTool:
    async def handler(
        action: str,
        doc_token: str | None = None,
        title: str | None = None,
        content: str | None = None,
        folder_token: str | None = None,
        block_id: str | None = None,
        comment_id: str | None = None,
        page_token: str | None = None,
        page_size: int = 50,
        **kwargs,
    ) -> dict[str, Any]:
        actions = {
            "read": lambda: _read_doc(client, doc_token),
            "write": lambda: _write_doc(client, doc_token, content),
            "append": lambda: _append_doc(client, doc_token, content),
            "create": lambda: _create_doc(client, title, folder_token),
            "create_and_write": lambda: _create_and_write_doc(client, title, content, folder_token),
            "list_blocks": lambda: _list_blocks(client, doc_token),
            "get_block": lambda: _get_block(client, doc_token, block_id),
            "update_block": lambda: _update_block(client, doc_token, block_id, content),
            "delete_block": lambda: _delete_block(client, doc_token, block_id),
            "list_comments": lambda: _list_comments(client, doc_token, page_token, page_size),
            "get_comment": lambda: _get_comment(client, doc_token, comment_id),
            "create_comment": lambda: _create_comment(client, doc_token, content),
            "list_comment_replies": lambda: _list_comment_replies(client, doc_token, comment_id, page_token, page_size),
        }

        if action not in actions:
            return {"error": f"Unknown action: {action}"}

        return await actions[action]()

    return FuncTool(
        name="feishu_doc",
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "read",
                        "write",
                        "append",
                        "create",
                        "create_and_write",
                        "list_blocks",
                        "get_block",
                        "update_block",
                        "delete_block",
                        "list_comments",
                        "get_comment",
                        "create_comment",
                        "list_comment_replies",
                    ],
                    "description": "Action to perform",
                },
                "doc_token": {"type": "string", "description": "Document token (from URL or previous operations)"},
                "title": {"type": "string", "description": "Document title for create operations"},
                "content": {"type": "string", "description": "Content to write/append or comment text"},
                "folder_token": {"type": "string", "description": "Parent folder token for create operations"},
                "block_id": {"type": "string", "description": "Block ID for block operations"},
                "comment_id": {"type": "string", "description": "Comment ID for comment operations"},
                "page_token": {"type": "string", "description": "Pagination token"},
                "page_size": {"type": "integer", "description": "Page size for list operations (default: 50)"},
            },
            "required": ["action"],
        },
        description="Feishu document read/write operations and comment management. Use when user mentions Feishu docs, cloud docs, docx links, or document comments.",
        handler=handler,
    )


BLOCK_TYPE_NAMES: dict[int, str] = {
    1: "Page",
    2: "Text",
    3: "Heading1",
    4: "Heading2",
    5: "Heading3",
    12: "Bullet",
    13: "Ordered",
    14: "Code",
    15: "Quote",
    17: "Todo",
    18: "Bitable",
    21: "Diagram",
    22: "Divider",
    23: "File",
    27: "Image",
    30: "Sheet",
    31: "Table",
    32: "TableCell",
}

STRUCTURED_BLOCK_TYPES = {14, 18, 21, 23, 27, 30, 31, 32}


async def _read_doc(client: FeishuClient, doc_token: str | None) -> dict[str, Any]:
    if not doc_token:
        return {"error": "doc_token is required"}

    token = extract_doc_token(doc_token)

    try:
        if token.startswith("doccn"):
            result = await client.get(f"doc/v2/{token}/raw_content")
            return {
                "content": result.get("data", {}).get("content", ""),
                "format": "doc",
                "hint": "Legacy document format. Only plain text content available.",
            }

        content_result = await client.get(f"docx/v1/documents/{token}/raw_content")
        info_result = await client.get(f"docx/v1/documents/{token}")
        blocks_result = await client.get(f"docx/v1/documents/{token}/blocks")

        blocks = blocks_result.get("data", {}).get("items", [])
        block_counts: dict[str, int] = {}
        structured_types: list[str] = []

        for b in blocks:
            block_type = b.get("block_type", 0)
            name = BLOCK_TYPE_NAMES.get(block_type, f"type_{block_type}")
            block_counts[name] = block_counts.get(name, 0) + 1
            if block_type in STRUCTURED_BLOCK_TYPES and name not in structured_types:
                structured_types.append(name)

        response = {
            "title": info_result.get("data", {}).get("document", {}).get("title", ""),
            "content": content_result.get("data", {}).get("content", ""),
            "revision_id": info_result.get("data", {}).get("document", {}).get("revision_id", ""),
            "block_count": len(blocks),
            "block_types": block_counts,
        }

        if structured_types:
            response["hint"] = f"This document contains {', '.join(structured_types)} which are NOT included in plain text. Use action: 'list_blocks' to get full content."

        return response
    except Exception as e:
        return {"error": str(e)}


async def _write_doc(client: FeishuClient, doc_token: str | None, content: str | None) -> dict[str, Any]:
    if not doc_token or not content:
        return {"error": "doc_token and content are required"}

    token = extract_doc_token(doc_token)

    try:
        blocks = _markdown_to_blocks(content)
        result = await client.patch(
            f"docx/v1/documents/{token}/blocks",
            data={"requests": [{"request_type": "ReplaceAllRequest", "replace_all": {"blocks": blocks}}]},
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _append_doc(client: FeishuClient, doc_token: str | None, content: str | None) -> dict[str, Any]:
    if not doc_token or not content:
        return {"error": "doc_token and content are required"}

    token = extract_doc_token(doc_token)

    try:
        blocks_result = await client.get(f"docx/v1/documents/{token}/blocks")
        blocks = blocks_result.get("data", {}).get("items", [])
        page_block = next((b for b in blocks if b.get("block_type") == 1), None)

        if not page_block:
            return {"error": "Could not find page root block"}

        new_blocks = _markdown_to_blocks(content)
        result = await client.post(
            f"docx/v1/documents/{token}/blocks/{page_block['block_id']}/children",
            data={"children": new_blocks, "index": len(page_block.get("children", []))},
        )
        return {"success": True, **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _create_doc(client: FeishuClient, title: str | None, folder_token: str | None) -> dict[str, Any]:
    if not title:
        return {"error": "title is required"}

    try:
        data: dict[str, Any] = {"title": title}
        if folder_token:
            data["folder_token"] = folder_token

        result = await client.post("docx/v1/documents", data=data)
        return {"success": True, "doc_token": result.get("data", {}).get("document", {}).get("document_id"), **result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _create_and_write_doc(client: FeishuClient, title: str | None, content: str | None, folder_token: str | None) -> dict[str, Any]:
    if not title or not content:
        return {"error": "title and content are required"}

    try:
        create_result = await _create_doc(client, title, folder_token)
        if "error" in create_result:
            return create_result

        doc_token = create_result.get("doc_token")
        if not doc_token:
            return {"error": "Failed to create document"}

        write_result = await _write_doc(client, doc_token, content)
        if "error" in write_result:
            return {"success": True, "doc_token": doc_token, "write_error": write_result.get("error"), **create_result}

        return {"success": True, "doc_token": doc_token, **create_result}
    except Exception as e:
        return {"error": str(e)}


async def _list_blocks(client: FeishuClient, doc_token: str | None) -> dict[str, Any]:
    if not doc_token:
        return {"error": "doc_token is required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.get(f"docx/v1/documents/{token}/blocks")
        return {"blocks": result.get("data", {}).get("items", [])}
    except Exception as e:
        return {"error": str(e)}


async def _get_block(client: FeishuClient, doc_token: str | None, block_id: str | None) -> dict[str, Any]:
    if not doc_token or not block_id:
        return {"error": "doc_token and block_id are required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.get(f"docx/v1/documents/{token}/blocks/{block_id}")
        return {"block": result.get("data", {}).get("block")}
    except Exception as e:
        return {"error": str(e)}


async def _update_block(client: FeishuClient, doc_token: str | None, block_id: str | None, content: str | None) -> dict[str, Any]:
    if not doc_token or not block_id or not content:
        return {"error": "doc_token, block_id, and content are required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.patch(
            f"docx/v1/documents/{token}/blocks/{block_id}",
            data={"update_text_elements": {"elements": [{"text_run": {"content": content}}]}},
        )
        return {"success": True, "block_id": block_id}
    except Exception as e:
        return {"error": str(e)}


async def _delete_block(client: FeishuClient, doc_token: str | None, block_id: str | None) -> dict[str, Any]:
    if not doc_token or not block_id:
        return {"error": "doc_token and block_id are required"}

    token = extract_doc_token(doc_token)

    try:
        block_info = await client.get(f"docx/v1/documents/{token}/blocks/{block_id}")
        parent_id = block_info.get("data", {}).get("block", {}).get("parent_id", token)

        children_result = await client.get(f"docx/v1/documents/{token}/blocks/{parent_id}/children")
        items = children_result.get("data", {}).get("items", [])
        index = next((i for i, item in enumerate(items) if item.get("block_id") == block_id), -1)

        if index == -1:
            return {"error": "Block not found"}

        await client.delete(f"docx/v1/documents/{token}/blocks/{parent_id}/children", params={"start_index": index, "end_index": index + 1})
        return {"success": True, "deleted_block_id": block_id}
    except Exception as e:
        return {"error": str(e)}


async def _list_comments(client: FeishuClient, doc_token: str | None, page_token: str | None, page_size: int) -> dict[str, Any]:
    if not doc_token:
        return {"error": "doc_token is required"}

    token = extract_doc_token(doc_token)

    try:
        params: dict[str, Any] = {"file_type": "docx", "page_size": min(max(page_size, 1), 50)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get(f"drive/v1/files/{token}/comments", params=params)
        return {
            "comments": result.get("data", {}).get("items", []),
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


async def _get_comment(client: FeishuClient, doc_token: str | None, comment_id: str | None) -> dict[str, Any]:
    if not doc_token or not comment_id:
        return {"error": "doc_token and comment_id are required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.get(f"drive/v1/files/{token}/comments/{comment_id}", params={"file_type": "docx"})
        return {"comment": result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _create_comment(client: FeishuClient, doc_token: str | None, content: str | None) -> dict[str, Any]:
    if not doc_token or not content:
        return {"error": "doc_token and content are required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.post(
            f"drive/v1/files/{token}/comments",
            data={
                "reply_list": {
                    "replies": [{"content": {"elements": [{"text_run": {"text": content}}]}}]
                }
            },
            json_data={"file_type": "docx"},
        )
        return {"comment_id": result.get("data", {}).get("comment_id"), "comment": result.get("data", {})}
    except Exception as e:
        return {"error": str(e)}


async def _list_comment_replies(client: FeishuClient, doc_token: str | None, comment_id: str | None, page_token: str | None, page_size: int) -> dict[str, Any]:
    if not doc_token or not comment_id:
        return {"error": "doc_token and comment_id are required"}

    token = extract_doc_token(doc_token)

    try:
        params: dict[str, Any] = {"file_type": "docx", "page_size": min(max(page_size, 1), 50)}
        if page_token:
            params["page_token"] = page_token

        result = await client.get(f"drive/v1/files/{token}/comments/{comment_id}/replies", params=params)
        return {
            "replies": result.get("data", {}).get("items", []),
            "page_token": result.get("data", {}).get("page_token"),
            "has_more": result.get("data", {}).get("has_more", False),
        }
    except Exception as e:
        return {"error": str(e)}


def _markdown_to_blocks(content: str) -> list[dict]:
    lines = content.split("\n")
    blocks: list[dict] = []

    for line in lines:
        if not line.strip():
            continue

        if line.startswith("# "):
            blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": line[2:]}}]}})
        elif line.startswith("## "):
            blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": line[3:]}}]}})
        elif line.startswith("### "):
            blocks.append({"block_type": 5, "heading3": {"elements": [{"text_run": {"content": line[4:]}}]}})
        elif line.startswith("- "):
            blocks.append({"block_type": 12, "bullet": {"elements": [{"text_run": {"content": line[2:]}}]}})
        elif line.startswith("```"):
            continue
        else:
            blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}]}})

    return blocks
