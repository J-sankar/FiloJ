        


class DispatchError(Exception):
    """Base class for all Webhook Dispatch Errors"""
    retryable :bool = False

class WebhookException(DispatchError):
    def __init__(self, details:str,code:int):
        self.details = details
        self.code = code
        self.retryable = False

class RetryableDispatchError(DispatchError):
    """Retryable Dispatch Errors"""
    retryable = True 



class PermanentDispatchError(DispatchError):
    retryable = False