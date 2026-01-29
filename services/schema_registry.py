from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel, TypeAdapter

from schemas.portfolio import PortfolioUpdate


@dataclass
class SchemaResolution:
    """Resolved metadata for a target portfolio path."""

    path: str
    root: str
    tokens: List[Any]
    annotation: Any
    json_schema: dict


class SchemaRegistry:
    """Utility for mapping dot/bracket paths to portfolio schema types."""

    _portfolio_model = PortfolioUpdate
    _allowed_roots = set(_portfolio_model.model_fields.keys())

    @classmethod
    def parse_path(cls, path: str) -> List[Any]:
        if not path or not isinstance(path, str):
            raise ValueError("target_path is required")
        tokens: List[Any] = []
        buffer = ""
        idx = 0
        while idx < len(path):
            char = path[idx]
            if char == ".":
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                idx += 1
                continue
            if char == "[":
                if buffer:
                    tokens.append(buffer)
                    buffer = ""
                end = path.find("]", idx)
                if end == -1:
                    raise ValueError("Invalid target_path: missing closing bracket")
                index_token = path[idx + 1 : end]
                if not index_token.isdigit():
                    raise ValueError("Invalid array index in target_path")
                tokens.append(int(index_token))
                idx = end + 1
                continue
            buffer += char
            idx += 1
        if buffer:
            tokens.append(buffer)
        if not tokens:
            raise ValueError("Invalid target_path")
        return tokens

    @classmethod
    def _strip_optional(cls, annotation: Any) -> Any:
        origin = get_origin(annotation)
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]  # noqa: E721
            if len(args) == 1:
                return args[0]
        return annotation

    @classmethod
    def _annotation_for_root(cls, root: str) -> Any:
        field = cls._portfolio_model.model_fields.get(root)
        if not field:
            raise ValueError(f"Invalid target section: {root}")
        return cls._strip_optional(field.annotation)

    @classmethod
    def _annotation_for_tokens(cls, annotation: Any, tokens: List[Any]) -> Any:
        current = cls._strip_optional(annotation)
        for token in tokens:
            origin = get_origin(current)
            args = get_args(current)
            if origin in (list, List):
                item_type = args[0] if args else Any
                current = cls._strip_optional(item_type)
                # numeric indexes simply move into the list item type
                continue
            if isinstance(current, type) and issubclass(current, BaseModel):
                if not isinstance(token, str):
                    raise ValueError("List index provided for non-list field")
                field = current.model_fields.get(token)
                if not field:
                    raise ValueError(f"Field '{token}' not found on {current.__name__}")
                current = cls._strip_optional(field.annotation)
                continue
            # Leaf types (str, int, etc.)
            return current
        return current

    @classmethod
    def resolve(cls, path: str) -> SchemaResolution:
        tokens = cls.parse_path(path)
        root = str(tokens[0])
        if root not in cls._allowed_roots:
            raise ValueError(f"Unsupported target section: {root}")
        annotation = cls._annotation_for_root(root)
        leaf_annotation = cls._annotation_for_tokens(annotation, tokens[1:])
        adapter = TypeAdapter(leaf_annotation)
        json_schema = adapter.json_schema()
        return SchemaResolution(
            path=path,
            root=root,
            tokens=tokens,
            annotation=leaf_annotation,
            json_schema=json_schema,
        )

    @classmethod
    def extract_value(cls, resolution: SchemaResolution, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        candidate = payload.get(resolution.root, payload)
        tokens = resolution.tokens[1:]
        current = candidate
        for token in tokens:
            if isinstance(token, int):
                if not isinstance(current, list) or token >= len(current):
                    return candidate
                current = current[token]
                continue
            if isinstance(current, dict) and token in current:
                current = current[token]
                continue
            return candidate
        return current

    @classmethod
    def validate_value(cls, resolution: SchemaResolution, value: Any) -> Any:
        adapter = TypeAdapter(resolution.annotation)
        return adapter.validate_python(value)

    @classmethod
    def _nest_value(cls, tokens: List[Any], value: Any) -> Any:
        if not tokens:
            return value
        token, *rest = tokens
        if isinstance(token, int):
            # Minimal list containing the indexed value
            items: List[Any] = []
            # Place value at index while keeping list compact
            while len(items) <= token:
                items.append(None)
            items[token] = cls._nest_value(rest, value)
            # Drop trailing None values
            while items and items[-1] is None:
                items.pop()
            return items
        return {token: cls._nest_value(rest, value)}

    @classmethod
    def build_patch(cls, resolution: SchemaResolution, value: Any, payload: Any) -> dict:
        if isinstance(payload, dict) and resolution.root in payload:
            return {resolution.root: payload[resolution.root]}
        tokens_after_root = resolution.tokens[1:]
        if tokens_after_root:
            # If the provided value already includes nested structure, keep it
            if isinstance(value, dict) and isinstance(tokens_after_root[0], str) and tokens_after_root[0] in value:
                return {resolution.root: value}
            nested = cls._nest_value(tokens_after_root, value)
            return {resolution.root: nested}
        return {resolution.root: value}

    @classmethod
    def pretty_schema(cls, resolution: SchemaResolution) -> str:
        return json.dumps(resolution.json_schema, ensure_ascii=True)
