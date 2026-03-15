from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, TypeVar, Callable

import aiohttp

from astrbot import logger

T = TypeVar("T")

BEIJING_TZ = timezone(timedelta(hours=8))
SHANGHAI_UTC_OFFSET_HOURS = 8
SHANGHAI_OFFSET_SUFFIX = "+08:00"


class FeishuAPIError(Exception):
    def __init__(
        self,
        code: int,
        msg: str,
        log_id: str = "",
        http_status: int = 0,
    ):
        self.code = code
        self.msg = msg
        self.log_id = log_id
        self.http_status = http_status
        super().__init__(
            f"Feishu API Error [{code}]: {msg}" + (f", log_id={log_id}" if log_id else "")
        )


class FeishuAuthError(FeishuAPIError):
    pass


class FeishuPermissionError(FeishuAPIError):
    pass


class FeishuNotFoundError(FeishuAPIError):
    pass


class FeishuRateLimitError(FeishuAPIError):
    pass


def parse_time_to_timestamp(input_time: str) -> Optional[int]:
    try:
        trimmed = input_time.strip()
        has_timezone = bool(trimmed.endswith("Z") or "+" in trimmed[-6:] or "-" in trimmed[-6:])

        if has_timezone:
            date = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
            return int(date.timestamp())

        normalized = trimmed.replace("T", " ")
        match = normalized.match(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?$") if hasattr(normalized, "match") else None

        if not match:
            import re
            match = re.match(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?$", normalized)

        if match:
            year, month, day, hour, minute, second = match.groups()
            beijing_tz = timezone(timedelta(hours=8))
            dt = datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second or 0),
                tzinfo=beijing_tz,
            )
            return int(dt.timestamp())

        date = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
        return int(date.timestamp())
    except Exception:
        return None


def parse_time_to_timestamp_ms(input_time: str) -> Optional[int]:
    ts = parse_time_to_timestamp(input_time)
    return ts * 1000 if ts else None


def parse_time_to_rfc3339(input_time: str) -> Optional[str]:
    try:
        trimmed = input_time.strip()
        has_timezone = bool(trimmed.endswith("Z") or "+" in trimmed[-6:] or "-" in trimmed[-6:])

        if has_timezone:
            date = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
            return date.isoformat()

        normalized = trimmed.replace("T", " ")
        import re
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?$", normalized)

        if match:
            year, month, day, hour, minute, second = match.groups()
            return f"{year}-{month}-{day}T{hour}:{minute}:{second or '00'}+08:00"

        date = datetime.fromisoformat(trimmed.replace("Z", "+00:00"))
        return date.isoformat()
    except Exception:
        return None


def unix_timestamp_to_iso8601(raw: str | int | None) -> Optional[str]:
    if raw is None:
        return None

    text = str(raw).strip()
    if not text.lstrip("-").isdigit():
        return None

    num = int(text)
    if not abs(num) >= 1e12:
        num *= 1000

    utc_dt = datetime.fromtimestamp(num / 1000, tz=timezone.utc)
    beijing_dt = utc_dt.astimezone(BEIJING_TZ)
    return beijing_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def pad2(value: int) -> str:
    return str(value).zfill(2)


class FeishuClient:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        domain: str = "https://open.feishu.cn",
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain.rstrip("/")
        self._tenant_access_token: str | None = None
        self._token_expire_time: float = 0
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

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

            code = data.get("code", 0)
            if code != 0:
                if code in (99991663, 99991664):
                    raise FeishuAuthError(code, data.get("msg", "Auth failed"), data.get("log_id", ""))
                raise FeishuAPIError(code, data.get("msg", "Unknown error"), data.get("log_id", ""))

            self._tenant_access_token = data.get("tenant_access_token", "")
            self._token_expire_time = time.time() + data.get("expire", 7200)
            logger.debug(f"[FeishuClient] Token refreshed, expires in {data.get('expire', 7200)}s")
            return self._tenant_access_token

    def _classify_error(self, code: int, msg: str, log_id: str) -> FeishuAPIError:
        if code in (99991663, 99991664, 99991661):
            return FeishuAuthError(code, msg, log_id)
        elif code in (99991662, 99991665, 99991666):
            return FeishuPermissionError(code, msg, log_id)
        elif code == 99991667:
            return FeishuNotFoundError(code, msg, log_id)
        elif code == 99991400:
            return FeishuRateLimitError(code, msg, log_id)
        return FeishuAPIError(code, msg, log_id)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        retry_count: int = 3,
        raw_response: bool = False,
    ) -> Dict:
        token = await self.get_tenant_access_token()
        url = f"{self.domain}/open-apis/{path}" if not path.startswith("http") else path
        session = await self._get_session()

        request_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        last_error: Exception | None = None
        for attempt in range(retry_count):
            try:
                async with session.request(
                    method,
                    url,
                    headers=request_headers,
                    params=params,
                    data=json.dumps(data) if data else None,
                    json=json_data,
                ) as resp:
                    if raw_response:
                        return {"raw": resp, "status": resp.status}

                    result = await resp.json()

                code = result.get("code", 0)
                if code == 0:
                    return result

                if code in (99991663, 99991664):
                    self._tenant_access_token = None
                    try:
                        token = await self.get_tenant_access_token()
                        request_headers["Authorization"] = f"Bearer {token}"
                        continue
                    except FeishuAuthError:
                        raise

                raise self._classify_error(
                    code,
                    result.get("msg", "Unknown error"),
                    result.get("log_id", ""),
                )

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"[FeishuClient] Request failed (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1 * (attempt + 1))

        raise last_error or FeishuAPIError(-1, "Request failed after retries")

    async def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        return await self.request("GET", path, params=params, **kwargs)

    async def post(
        self,
        path: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        **kwargs,
    ) -> Dict:
        return await self.request("POST", path, data=data, json_data=json_data, **kwargs)

    async def put(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict:
        return await self.request("PUT", path, data=data, **kwargs)

    async def delete(self, path: str, params: Optional[Dict] = None, data: Optional[Dict] = None, **kwargs) -> Dict:
        return await self.request("DELETE", path, params=params, data=data, **kwargs)

    async def patch(self, path: str, data: Optional[Dict] = None, **kwargs) -> Dict:
        return await self.request("PATCH", path, data=data, **kwargs)

    async def upload_file(
        self,
        path: str,
        file_content: bytes,
        file_name: str,
        parent_type: str = "explorer",
        parent_node: str = "",
        **kwargs,
    ) -> Dict:
        token = await self.get_tenant_access_token()
        url = f"{self.domain}/open-apis/{path}"
        session = await self._get_session()

        form_data = aiohttp.FormData()
        form_data.add_field("file_name", file_name)
        form_data.add_field("parent_type", parent_type)
        form_data.add_field("parent_node", parent_node)
        form_data.add_field("size", str(len(file_content)))
        form_data.add_field(
            "file",
            file_content,
            filename=file_name,
            content_type="application/octet-stream",
        )

        headers = {"Authorization": f"Bearer {token}"}

        async with session.post(url, data=form_data, headers=headers) as resp:
            result = await resp.json()

        code = result.get("code", 0)
        if code != 0:
            raise self._classify_error(
                code,
                result.get("msg", "Unknown error"),
                result.get("log_id", ""),
            )

        return result

    async def download_file(self, path: str, params: Optional[Dict] = None) -> bytes:
        token = await self.get_tenant_access_token()
        url = f"{self.domain}/open-apis/{path}"
        session = await self._get_session()

        headers = {"Authorization": f"Bearer {token}"}

        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise FeishuAPIError(resp.status, f"Download failed: {text}")
            return await resp.read()


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
                    lines.append(
                        "".join(
                            el.get("text", "") for el in paragraph if isinstance(el, dict)
                        )
                    )
            return f"{title}\n{chr(10).join(lines)}" if title else chr(10).join(lines)
        if msg_type == "image":
            return "[图片]"
        if msg_type == "file":
            return f"[文件: {parsed.get('file_name', '')}]"
        if msg_type == "audio":
            return "[语音]"
        if msg_type == "sticker":
            return "[表情]"
        if msg_type == "share_chat":
            return "[群名片]"
        if msg_type == "share_user":
            return "[用户名片]"
        if msg_type == "interactive":
            return "[消息卡片]"
        return f"[{msg_type or '未知类型'}]"
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


def extract_sheet_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        if "/sheets/" in url_or_token:
            return url_or_token.split("/sheets/")[-1].split("?")[0].split("/")[0]
        if "/spreadsheet/" in url_or_token:
            return url_or_token.split("/spreadsheet/")[-1].split("?")[0].split("/")[0]
    return url_or_token


def extract_bitable_token(url_or_token: str) -> str:
    if url_or_token.startswith("http"):
        if "/base/" in url_or_token:
            return url_or_token.split("/base/")[-1].split("?")[0].split("/")[0]
    return url_or_token


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
