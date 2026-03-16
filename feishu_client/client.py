import json
import lark_oapi as lark
from lark_oapi import Client


class FeishuClient:
    def __init__(self, app_id: str, app_secret: str, domain: str = lark.FEISHU_DOMAIN):
        self.app_id = app_id
        self.app_secret = app_secret
        self.domain = domain
        self._client: Client | None = None
        self._tenant_access_token: str | None = None

    def get_client(self) -> Client:
        if self._client is None:
            self._client = (
                Client.builder()
                .app_id(self.app_id)
                .app_secret(self.app_secret)
                .log_level(lark.LogLevel.ERROR)
                .domain(self.domain)
                .build()
            )
        return self._client

    async def get_tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token

        client = self.get_client()
        request = lark.BaseRequest.builder() \
            .http_method(lark.HttpMethod.POST) \
            .uri("/open-apis/auth/v3/tenant_access_token/internal") \
            .token_types(set()) \
            .body({
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            }) \
            .build()

        response = await client.arequest(request)
        if not response.success():
            raise Exception(f"获取tenant_access_token失败: {response.msg}")

        result = json.loads(str(response.raw.content, lark.UTF_8))
        self._tenant_access_token = result.get("tenant_access_token")
        return self._tenant_access_token

    async def close(self):
        pass
