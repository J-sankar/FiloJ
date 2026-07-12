import hmac
import hashlib


def sign_request_body(key: str, body_str: str):
    body_bytes = body_str.encode()
    signature = hmac.new(
        str(key).encode(), msg=body_bytes, digestmod=hashlib.sha256
    ).hexdigest()
    return signature