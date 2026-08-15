from abc import ABC, abstractmethod

from fastapi import Request


class ServiceHandler(ABC):
    def should_handle(self, path: str) -> bool:
        return True

    @abstractmethod
    async def get_context(self, request: Request) -> tuple[str, str]:
        raise NotImplementedError