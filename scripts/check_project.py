import ast
from pathlib import Path
from jinja2 import Environment
import yaml

root = Path(__file__).resolve().parents[1]
errors = []
for base in (root / "services", root / "tests", root / "scripts"):
    for path in base.rglob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python: {path}: {exc}")
for path in (root / "services/web_gateway/templates").glob("*.html"):
    try:
        Environment().parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Jinja: {path}: {exc}")
for filename in ("docker-compose.yml", "docker-compose.test.yml"):
    try:
        yaml.safe_load((root / filename).read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Compose YAML ({filename}): {exc}")
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print("Validación estática correcta: aplicación, pruebas, Jinja y Docker Compose.")
