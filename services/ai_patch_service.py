import json
import os
from typing import Any, Optional

from openai import AsyncOpenAI

from services.schema_registry import SchemaRegistry
from typing import get_origin


def _supports_json_schema(model: str) -> bool:
    return model.startswith("gpt-4o-2024-08-06") or model.startswith("gpt-4o-mini")


class AIPatchService:
    """
    Generates minimal, schema-valid patches for portfolio sections/fields.
    """

    def __init__(self, ai_client: Optional[AsyncOpenAI] = None, model: Optional[str] = None):
        self.client = ai_client or AsyncOpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")

    async def generate_patch(self, target_path: str, context_text: str) -> dict:
        resolution = SchemaRegistry.resolve(target_path)
        schema_json = resolution.json_schema

        system_prompt = (
            "You are a strict data extractor. "
            "Return ONLY valid JSON (no code fences) that fits the given JSON Schema. "
            "Do not invent data. Omit fields that are not present in the text. "
            "If the schema expects a list, return the single most relevant item from the text."
        )

        user_prompt = (
            f"Target path: {target_path}\n"
            f"JSON Schema: {json.dumps(schema_json)}\n\n"
            f"USER TEXT:\n{context_text}"
        )

        response_format: dict[str, Any] = {"type": "json_object"}
        if _supports_json_schema(self.model):
            response_format = {"type": "json_schema", "json_schema": {"schema": schema_json}}

        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-arg]
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,  # type: ignore[arg-type]
            )
        except Exception as exc:  # pragma: no cover - passthrough
            raise ValueError(f"AI provider error: {exc}")

        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"AI returned invalid JSON: {exc}") from exc

        # If the schema expects a list but AI returned a single item, wrap it.
        if get_origin(resolution.annotation) in {list, tuple} or resolution.annotation is list:
            if not isinstance(parsed, list):
                parsed = [parsed]

        try:
            validated_value = SchemaRegistry.validate_value(resolution, parsed)
        except Exception as exc:
            raise ValueError(f"AI output failed schema validation: {exc}") from exc

        patch = SchemaRegistry.build_patch(resolution, validated_value, parsed)
        return patch
