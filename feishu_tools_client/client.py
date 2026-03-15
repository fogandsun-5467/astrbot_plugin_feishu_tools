import json
import asyncio
from typing import Any, Dict, Optional

import aiohttp

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
        self._tenant_access_token: str | None = None
        self._token_expire_time: float = 0
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_tenant_access_token(self) -> str:
        async with self._lock:
            if self._tenant_access_token and time.time() < self._token_expire_time - 60:
                return self._tenant_access_token

            url = f"{self.domain}/open-apis/auth/v3/tenant_access_token/internal"
            session = await self._get_session()

            async with session.post(
                url,
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            ) as resp:
                data = await resp.json()

            if data.get("code", 0) != 0:
                raise FeishuAPIError(
                    data.get("code", -1),
                    data.get("msg", "Unknown error"),
                    data.get("log_id", ""),
                )

            self._tenant_access_token = data.get("tenant_access_token", "")
            self._token_expire_time = time.time() + data.get("expire", 7200)
            return self._tenant_access_token

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
        import time
        token = await self.get_tenant_access_token()
        url = f"{self.domain}/open-apis/{path}"
        session = await self._get_session()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(retry_count):
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=json.dumps(data) if data else None,
                    json=json_data,
                ) as resp:
                    result = await resp.json()

                code = result.get("code", 0)
                if code == 0:
                    return result

                if code in (99991663, 99991664):
                    self._tenant_access_token = None
                    token = await self.get_tenant_access_token()
                    headers["Authorization"] = f"Bearer {token}"
                    continue

                raise FeishuAPIError(
                    code,
                    result.get("msg", "Unknown error"),
                    result.get("log_id", ""),
                )

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"Feishu API request failed (attempt {attempt + 1}): {e}")
                await asyncio.sleep(1)

        raise last_error or FeishuAPIError(-1, "Request failed after retries")

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
