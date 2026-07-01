

class InvalidApiKeyError(Exception):
    """When api key is invalid"""
    pass

class InactiveApiKeyError(Exception):
    """When Api key is revoked/inactive"""
    pass


class InactiveDeveloperError(Exception):
    """When developer is revoked/inactive"""
    pass

