
def api_key_meta_key(api_key: str) -> str:
    return f"apikey:meta:{api_key}"

def api_key_usage_key(api_key: str, window: str) -> str:
    return f"apikey:usage:{api_key}:{window}"

def storage_usage_key(developer_id: str) -> str:
    return f"developer:storage:{developer_id}"

def web_hook_config_key(developer_id:str) -> str:
    return f"webhook_cofig:{developer_id}"