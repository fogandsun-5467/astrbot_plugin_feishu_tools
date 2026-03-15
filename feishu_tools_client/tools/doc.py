from __future__ import annotations

import json
from typing import Any

from astrbot.core.provider.func_tool_manager import FuncTool

from ..client import FeishuClient, extract_doc_token, BLOCK_TYPE_NAMES, STRUCTURED_BLOCK_TYPES


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
            return {"error": f"Unknown action: {action}. Available: {', '.join(actions.keys())}"}

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
                    "description": "操作类型",
                },
                "doc_token": {
                    "type": "string",
                    "description": "文档 token（可从 URL 中提取，或使用 create 操作返回的 token）",
                },
                "title": {
                    "type": "string",
                    "description": "文档标题，create 操作必填",
                },
                "content": {
                    "type": "string",
                    "description": "内容。write/append 操作填 Markdown 格式内容；create_comment 操作填评论文本",
                },
                "folder_token": {
                    "type": "string",
                    "description": "父文件夹 token，create 操作可选",
                },
                "block_id": {
                    "type": "string",
                    "description": "Block ID，用于 get_block/update_block/delete_block 操作",
                },
                "comment_id": {
                    "type": "string",
                    "description": "评论 ID，用于 get_comment/list_comment_replies 操作",
                },
                "page_token": {
                    "type": "string",
                    "description": "分页标记",
                },
                "page_size": {
                    "type": "integer",
                    "default": 50,
                    "description": "每页数量（默认 50，最大 50）",
                },
            },
            "required": ["action"],
        },
        description="【飞书/Feishu/Lark文档工具】当用户提到飞书文档、创建文档、编辑文档、写入文档、文档内容时使用此工具。支持读取、写入、创建文档，以及 Block 和评论管理。\n\n"
        "Actions:\n"
        "- read：读取文档内容，返回纯文本和元信息\n"
        "- write：覆盖写入文档内容（Markdown 格式）\n"
        "- append：在文档末尾追加内容（Markdown 格式）\n"
        "- create：创建新文档，返回 doc_token\n"
        "- create_and_write：创建文档并写入内容（便捷操作）\n"
        "- list_blocks：列出文档所有 Block\n"
        "- get_block：获取单个 Block 详情\n"
        "- update_block：更新 Block 内容\n"
        "- delete_block：删除 Block\n"
        "- list_comments：列出文档评论\n"
        "- get_comment：获取单条评论\n"
        "- create_comment：创建评论\n"
        "- list_comment_replies：列出评论回复\n\n"
        "【重要】doc_token 可以是：\n"
        "1. 文档 token（如 DoxcnXxx）\n"
        "2. 完整 URL（会自动提取 token）\n\n"
        "【内容格式】write/append 操作支持 Markdown 格式：\n"
        "- # 标题1  → 一级标题\n"
        "- ## 标题2 → 二级标题\n"
        "- - 列表项 → 无序列表\n"
        "- 普通文本 → 段落",
        handler=handler,
    )


async def _read_doc(client: FeishuClient, doc_token: str | None) -> dict[str, Any]:
    if not doc_token:
        return {"error": "doc_token is required"}

    token = extract_doc_token(doc_token)

    try:
        if token.startswith("doccn"):
            result = await client.get(f"doc/v2/{token}/raw_content")
            return {
                "ok": True,
                "content": result.get("data", {}).get("content", ""),
                "format": "doc",
                "hint": "旧版文档格式，仅返回纯文本内容",
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

        response: dict[str, Any] = {
            "ok": True,
            "title": info_result.get("data", {}).get("document", {}).get("title", ""),
            "content": content_result.get("data", {}).get("content", ""),
            "revision_id": info_result.get("data", {}).get("document", {}).get("revision_id", ""),
            "block_count": len(blocks),
            "block_types": block_counts,
        }

        if structured_types:
            response["hint"] = f"文档包含 {', '.join(structured_types)} 等结构化内容，纯文本不包含这些内容。使用 list_blocks 获取完整内容。"

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
        return {"ok": True, "revision_id": result.get("data", {}).get("revision_id", "")}
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
        return {"ok": True, "revision_id": result.get("data", {}).get("revision_id", "")}
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
        doc = result.get("data", {}).get("document", {})
        return {
            "ok": True,
            "doc_token": doc.get("document_id", ""),
            "title": doc.get("title", ""),
            "revision_id": doc.get("revision_id", ""),
        }
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
            return {"ok": True, "doc_token": doc_token, "write_error": write_result.get("error"), **create_result}

        return {"ok": True, "doc_token": doc_token, **create_result}
    except Exception as e:
        return {"error": str(e)}


async def _list_blocks(client: FeishuClient, doc_token: str | None) -> dict[str, Any]:
    if not doc_token:
        return {"error": "doc_token is required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.get(f"docx/v1/documents/{token}/blocks")
        blocks = result.get("data", {}).get("items", [])

        formatted_blocks = []
        for b in blocks:
            block_type = b.get("block_type", 0)
            formatted_blocks.append({
                "block_id": b.get("block_id", ""),
                "block_type": block_type,
                "block_type_name": BLOCK_TYPE_NAMES.get(block_type, f"type_{block_type}"),
                "parent_id": b.get("parent_id", ""),
                "children": b.get("children", []),
                "text": _extract_block_text(b),
            })

        return {"ok": True, "blocks": formatted_blocks, "total": len(formatted_blocks)}
    except Exception as e:
        return {"error": str(e)}


async def _get_block(client: FeishuClient, doc_token: str | None, block_id: str | None) -> dict[str, Any]:
    if not doc_token or not block_id:
        return {"error": "doc_token and block_id are required"}

    token = extract_doc_token(doc_token)

    try:
        result = await client.get(f"docx/v1/documents/{token}/blocks/{block_id}")
        block = result.get("data", {}).get("block")
        if not block:
            return {"error": "Block not found"}

        block_type = block.get("block_type", 0)
        return {
            "ok": True,
            "block": {
                "block_id": block.get("block_id", ""),
                "block_type": block_type,
                "block_type_name": BLOCK_TYPE_NAMES.get(block_type, f"type_{block_type}"),
                "parent_id": block.get("parent_id", ""),
                "children": block.get("children", []),
                "text": _extract_block_text(block),
            },
        }
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
        return {"ok": True, "block_id": block_id, "revision_id": result.get("data", {}).get("revision_id", "")}
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
        return {"ok": True, "deleted_block_id": block_id}
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
            "ok": True,
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
        return {"ok": True, "comment": result.get("data", {})}
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
        return {
            "ok": True,
            "comment_id": result.get("data", {}).get("comment_id", ""),
            "comment": result.get("data", {}),
        }
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
            "ok": True,
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
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({"block_type": 12, "bullet": {"elements": [{"text_run": {"content": line[2:]}}]}})
        elif line.startswith("```"):
            continue
        else:
            blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}]}})

    return blocks


def _extract_block_text(block: dict) -> str:
    block_type = block.get("block_type", 0)

    text_extractors = {
        2: lambda b: b.get("text", {}).get("elements", []),
        3: lambda b: b.get("heading1", {}).get("elements", []),
        4: lambda b: b.get("heading2", {}).get("elements", []),
        5: lambda b: b.get("heading3", {}).get("elements", []),
        12: lambda b: b.get("bullet", {}).get("elements", []),
        13: lambda b: b.get("ordered", {}).get("elements", []),
        14: lambda b: b.get("code", {}).get("elements", []),
        15: lambda b: b.get("quote", {}).get("elements", []),
        17: lambda b: b.get("todo", {}).get("elements", []),
    }

    elements = text_extractors.get(block_type, lambda b: [])(block)
    texts = []
    for el in elements:
        if "text_run" in el:
            texts.append(el["text_run"].get("content", ""))

    return "".join(texts)
