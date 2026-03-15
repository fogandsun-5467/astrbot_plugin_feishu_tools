import json
from typing import Any, Dict, Optional

from lark_oapi import AsyncClient
from lark_oapi.api import Request, Response
from lark_oapi.core import AccessTokenType
from lark_oapi.core.exception import LarkException

from astrbot import logger


class FeishuAPIError(Exception):
    def __init__(self, code: int, msg: str, log_id: str = ""):
        self.code = code
        self.msg = msg
        self.log_id = log_id
        super().__init__(f"Feishu API Error [{code}]: {msg}" + (f", log_id={log_id}" if log_id else ""))


class FeishuClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain
        self.client = AsyncClient(
            app_id=app_id,
            app_secret=app_secret,
            access_token_type=AccessTokenType.TENANT,
            domain=domain,
        )

    async def close(self):
        # lark-oapi 客户端不需要显式关闭
        pass

    async def get_tenant_access_token(self) -> str:
        try:
            token = await self.client.get_tenant_access_token()
            return token
        except LarkException as e:
            raise FeishuAPIError(e.code, e.msg, e.log_id)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 3,
    ) -> Dict:
        for attempt in range(retry_count):
            try:
                req = Request(
                    method=method,
                    path=path,
                    params=params,
                    body=data or json_data,
                )
                resp = await self.client.request(req)
                if resp.code != 0:
                    raise FeishuAPIError(resp.code, resp.msg, resp.log_id)
                return resp.data
            except LarkException as e:
                logger.warning(f"Feishu API request failed (attempt {attempt + 1}): {e}")
                if attempt == retry_count - 1:
                    raise FeishuAPIError(e.code, e.msg, e.log_id)

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict:
        return await self.request("POST", path, data=data, json_data=json_data)

    async def put(self, path: str, data: Optional[Dict] = None) -> Dict:
        return await self.request("PUT", path, data=data)

    async def delete(self, path: str, params: Optional[Dict] = None) -> Dict:
        return await self.request("DELETE", path, params=params)

    async def patch(self, path: str, data: Optional[Dict] = None) -> Dict:
        return await self.request("PATCH", path, data=data)


def parse_message_content(msg_type: str | None, raw_content: str | None) -> str:
    if not raw_content:
        return ""
    try:
        parsed = json.loads(raw_content)
        if msg_type == "text":
            return parsed.get("text", raw_content)
        if msg_type == "post":
            title = parsed.get("title", "")
            lines: list[str] = []
            for paragraph in parsed.get("content", []):
                if isinstance(paragraph, list):
                    lines.append("".join(el.get("text", "") for el in paragraph if isinstance(el, dict)))
            return f"{title}\n{chr(10).join(lines)}" if title else chr(10).join(lines)
        if msg_type == "image":
            return "[image]"
        if msg_type == "file":
            return f"[file: {parsed.get('file_name', '')}]"
        if msg_type == "audio":
            return "[audio]"
        if msg_type == "sticker":
            return "[sticker]"
        if msg_type == "share_chat":
            return "[share_chat]"
        if msg_type == "share_user":
            return "[share_user]"
        return f"[{msg_type or 'unknown'}]"
    except json.JSONDecodeError:
        return raw_content


def extract_doc_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        if "/docx/" in url_or_token:
            return url_or_token.split("/docx/")[-1].split("?")[0].split("/")[0]
        if "/docs/" in url_or_token:
            return url_or_token.split("/docs/")[-1].split("?")[0].split("/")[0]
    return url_or_token


def extract_folder_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        if "/folder/" in url_or_token:
            return url_or_token.split("/folder/")[-1].split("?")[0].split("/")[0]
    return url_or_token


def extract_wiki_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        if "/wiki/" in url_or_token:
            return url_or_token.split("/wiki/")[-1].split("?")[0].split("/")[0]
    return url_or_token
