"""Static guard: MAOS Kernel V1 source must remain importable without side effects."""

import ast
from pathlib import Path

KERNEL_ROOT = Path(__file__).parents[2] / "app" / "maos" / "kernel_v1"
FORBIDDEN_IMPORT_ROOTS = {
    "requests",
    "httpx",
    "socket",
    "asyncpg",
    "psycopg",
    "sqlalchemy",
    "redis",
    "subprocess",
    "docker",
    "google",
    "openai",
    "anthropic",
    "boto3",
}
FORBIDDEN_CALLS = {"open", "system", "popen", "connect", "create_engine", "create_async_engine", "getenv", "read_text", "write_text", "unlink", "mkdir"}


def test_kernel_source_has_no_io_provider_database_or_credential_access() -> None:
    violations: list[str] = []
    for path in sorted(KERNEL_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = [alias.name.split(".", maxsplit=1)[0] for alias in node.names]
                violations.extend(f"{path.name}: import {root}" for root in roots if root in FORBIDDEN_IMPORT_ROOTS)
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".", maxsplit=1)[0]
                if root in FORBIDDEN_IMPORT_ROOTS:
                    violations.append(f"{path.name}: from {root} import ...")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    violations.append(f"{path.name}: call {node.func.id}()")
                if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
                    violations.append(f"{path.name}: attribute call {node.func.attr}()")
            elif isinstance(node, ast.Attribute) and node.attr in {"environ", "environb"}:
                violations.append(f"{path.name}: credential/config environment access")
    assert violations == []
