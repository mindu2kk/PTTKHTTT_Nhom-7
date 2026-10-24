import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_layer_import_boundaries():
    root = Path(__file__).resolve().parents[1] / "app"
    forbidden = {
        "domain": ("fastapi", "sqlalchemy", "app.infrastructure", "app.api", "app.core"),
        "application": ("fastapi", "sqlalchemy", "app.infrastructure", "app.api", "app.core"),
        "api": ("sqlalchemy", "app.infrastructure"),
    }
    for layer, prefixes in forbidden.items():
        for file in (root / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
                names = (
                    [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else [n.name for n in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                assert not any(name.startswith(prefixes) for name in names), file


def test_local_only_cannot_enable_remote_inference():
    with pytest.raises(ValidationError):
        Settings(local_only=False)
