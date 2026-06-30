from fastapi import Request
import uuid
from gateway.core.config import INTERNAL_GATEWAY_SECRET
from dataclasses import dataclass, field


@dataclass
class HeaderBuilder:
    content_type: str = ""
    accept: str = ""
    developer_id: str = ""
    developer_plan: str = ""
    internal_secret : str = INTERNAL_GATEWAY_SECRET
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cookie: str = " "
    # api_key: str = "" TO BE COMPLETED

    @classmethod
    def from_request(
        cls, request: Request, developer_id: str = "", plan: str = ""
    ) -> "HeaderBuilder":
        return cls(
            content_type=request.headers.get("content-type", ""),
            accept=request.headers.get("accept", ""),
            developer_id=developer_id,
            developer_plan=plan,
            request_id=request.headers.get("x-request-id", str(uuid.uuid4())),
            cookie=request.headers.get("cookie")
        )

    def to_dict(self) -> dict:
        headers = {
            "x-internal-secret": self.internal_secret,
            "x-request-id": self.request_id,
        }
        if self.content_type:
            headers["content-type"] = self.content_type

        if self.accept:
            headers["accept"] = self.accept

        if self.developer_id:
            headers["x-developer-id"] = self.developer_id
        if self.developer_plan:
            headers["x-developer-plan"] = self.developer_plan

        if self.cookie:
            headers["cookie"] = self.cookie

        # if self.api_key: To be done
        return headers
    
    def set_developer_credentials(self,decoded_token:dict) ->None:
        self.developer_id = decoded_token.get("sub")
        self.developer_plan = decoded_token.get("plan")

