import ast
from pathlib import Path


SRC = Path(__file__).parents[1] / "src"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_and_rules_do_not_depend_on_http_or_api_layers():
    domain_modules = set()
    for path in (SRC / "domain").rglob("*.py"):
        domain_modules.update(imported_modules(path))

    assert not any(module == "fastapi" or module.startswith("fastapi.") for module in domain_modules)
    assert "httpx" not in domain_modules

    rules_modules = imported_modules(SRC / "domain" / "insurance" / "rules_engine.py")
    assert not any(
        module in {"httpx", "requests", "urllib", "urllib.request", "socket", "json", "pathlib"}
        for module in rules_modules
    )


def test_domain_contracts_do_not_cross_into_external_or_other_business_domains():
    weather_models = imported_modules(SRC / "domain" / "weather" / "models.py")
    insurance_models = imported_modules(SRC / "domain" / "insurance" / "models.py")

    assert not any("insurance" in module or "Insured" in module for module in weather_models)
    assert not any("inmet" in module.lower() for module in insurance_models)
