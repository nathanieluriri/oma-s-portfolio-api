import json
import os
from typing import Any, Optional

from openai import AsyncOpenAI

from services.schema_registry import SchemaRegistry
from typing import get_origin


def _supports_json_schema(model: str) -> bool:
    return model.startswith("gpt-4o-2024-08-06") or model.startswith("gpt-4o-mini")


def _ensure_object_schema(schema_json: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """OpenAI JSON schema response_format requires a top-level object schema.

    Returns a tuple of (schema_for_response, wrapped_output_flag). If the provided
    schema is already an object, it is returned unchanged with wrapped_output_flag=False.
    Otherwise, the schema is wrapped under a single required property "value" so the
    top-level type is an object, and wrapped_output_flag=True so we can unwrap the
    response before validation/building the patch.
    """

    if schema_json.get("type") == "object":
        return schema_json, False

    wrapped_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["value"],
        "properties": {"value": schema_json},
    }
    return wrapped_schema, True


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
        schema_for_response, wrapped_output = _ensure_object_schema(schema_json)

        system_prompt = (
            "You are a strict data extractor. "
            "Return ONLY valid JSON (no code fences) that fits the given JSON Schema. "
            "Do not invent data. Omit fields that are not present in the text. "
            "If the schema expects a list, return the single most relevant item from the text."
        )

        user_prompt = (
            f"Target path: {target_path}\n"
            f"JSON Schema: {json.dumps(schema_for_response)}\n\n"
            f"USER TEXT:\n{context_text}"
        )

        response_format: dict[str, Any] = {"type": "json_object"}
        if _supports_json_schema(self.model):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "portfolio_patch",
                    "schema": schema_for_response,
                    "strict": True,
                },
            }

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

        if wrapped_output:
            if not isinstance(parsed, dict) or "value" not in parsed:
                raise ValueError("AI returned JSON missing wrapped 'value' field")
            parsed = parsed["value"]

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
