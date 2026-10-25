import json
import logging
from typing import Any

import openai
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import ResponseFormat
from pydantic import BaseModel, ValidationError

from app.core.errors import SourceUnavailableError
from app.services.llm.base import LLMResult

logger = logging.getLogger(__name__)


# Ajusta o schema do Pydantic ao modo estrito: todos os campos obrigatórios.
def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:

    def visit(node: Any, is_name_map: bool = False) -> Any:
        if isinstance(node, dict):
            if is_name_map:
                return {name: visit(value) for name, value in node.items()}
            node = {
                key: visit(value, is_name_map=key in ("properties", "$defs"))
                for key, value in node.items()
                if key not in ("default", "title")
            }
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
        elif isinstance(node, list):
            node = [visit(item) for item in node]
        return node

    result: dict[str, Any] = visit(model.model_json_schema())
    return result


class OpenAICompatClient:
    def __init__(self, api_key: str, base_url: str, models: list[str], timeout: float = 60) -> None:
        self.models = models
        self._client = openai.AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0
        )

    async def generate[T: BaseModel](self, system: str, user: str, output: type[T]) -> LLMResult[T]:
        errors = []
        # Tenta cada modelo em ordem até um responder.
        for model in self.models:
            try:
                return LLMResult(
                    value=await self._generate_with(model, system, user, output), model=model
                )
            except (openai.OpenAIError, ValidationError, ValueError) as exc:
                logger.warning("LLM %s failed: %s", model, exc)
                errors.append(f"{model}: {type(exc).__name__}")
        raise SourceUnavailableError("llm", "; ".join(errors) or "no model configured")

    async def _generate_with[T: BaseModel](
        self, model: str, system: str, user: str, output: type[T]
    ) -> T:
        schema = strict_json_schema(output)
        structured: ResponseFormat = {
            "type": "json_schema",
            "json_schema": {"name": output.__name__, "strict": True, "schema": schema},
        }
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            content = await self._complete(model, messages, structured)
        # Modelo sem saída estruturada: usa modo JSON com o schema no prompt.
        except openai.BadRequestError:
            schema_hint = f"\n\nResponda APENAS com JSON válido neste schema:\n{json.dumps(schema)}"
            messages = [
                {"role": "system", "content": system + schema_hint},
                {"role": "user", "content": user},
            ]
            content = await self._complete(model, messages, {"type": "json_object"})
        try:
            return output.model_validate_json(content)
        except ValidationError as exc:
            # Resposta fora do schema: pede uma correção uma vez.
            messages += [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": f"O JSON não segue o schema: {exc}. Corrija e responda só o JSON.",
                },
            ]
            return output.model_validate_json(
                await self._complete(model, messages, {"type": "json_object"})
            )

    async def _complete(
        self,
        model: str,
        messages: list[ChatCompletionMessageParam],
        response_format: ResponseFormat,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=model, messages=messages, response_format=response_format, temperature=0.7
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("empty answer")
        return content
