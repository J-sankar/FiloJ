import os
from dotenv import load_dotenv


load_dotenv()
SERVICES = {
    "file": os.getenv("FILE_SERVICE_URL", "http://localhost:8002"),
    "auth": os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
}

TIMEOUTS = {
    "file": 60.0,
    "auth": 10,
    "default": 30
}

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET", None)

JWT_SECRET          = os.getenv("JWT_SECRET")
JWT_ALGORITHM       = os.getenv("JWT_ALGORITHM", "HS256")