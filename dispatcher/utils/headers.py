import time

def prepare_headers(signature:str)->dict :
    return {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Timestamp": str(int(time.time()))
    }