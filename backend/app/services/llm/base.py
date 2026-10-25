from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    value: T
    model: str


class LLMClient(Protocol):
    async def generate[T: BaseModel](
        self, system: str, user: str, output: type[T]
    ) -> LLMResult[T]: ...
