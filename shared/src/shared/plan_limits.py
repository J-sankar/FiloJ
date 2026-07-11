PLAN_LIMITS = {
    "free": {
        "requests_per_hour": 15,
        "max_file_size_bytes": 10 * 1024 * 1024,       # 10 MB
        "storage_quota_bytes": 1 * 1024 * 1024 * 1024,  # 1 GB
    },
    "pro": {
        "requests_per_hour": 5000,
        "max_file_size_bytes": 100 * 1024 * 1024,       # 100 MB
        "storage_quota_bytes": 50 * 1024 * 1024 * 1024, # 50 GB
    },
}