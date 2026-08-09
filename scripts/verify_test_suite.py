from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
required = [
    "docker-compose.test.yml", ".env.test.example", "tests/Dockerfile",
    "scripts/test_all.ps1", "scripts/test_all.sh", "scripts/run_full_test_suite.sh",
]
missing = [name for name in required if not (ROOT / name).exists()]
if missing:
    raise SystemExit(f"Faltan archivos de prueba: {missing}")
counts = {"unit": 0, "integration": 0, "e2e": 0, "destructive": 0}
for group in counts:
    for path in (ROOT / "tests" / group).glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        counts[group] += sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") for node in tree.body)
if any(value == 0 for value in counts.values()):
    raise SystemExit(f"Hay grupos sin pruebas: {counts}")
print(f"Suite completa verificada: {sum(counts.values())} pruebas declaradas: {counts}")
