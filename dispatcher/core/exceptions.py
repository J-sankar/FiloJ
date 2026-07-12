class WebhookException(Exception):
    def __init__(self, details:str,code:int):
        self.details = details
        self.code = code
        