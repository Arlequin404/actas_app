#!/usr/bin/env bash
set -u
mkdir -p test-artifacts/screenshots test-artifacts/traces
status=0
run_phase() {
  local name="$1"; shift
  echo "===== ${name} ====="
  if ! pytest "$@" -v --html="test-artifacts/${name}.html" --self-contained-html --junitxml="test-artifacts/${name}.xml"; then
    status=1
  fi
}
python scripts/check_project.py || status=1
python scripts/verify_catalog_admin.py || status=1
run_phase unitarias tests/unit
run_phase integracion tests/integration
run_phase interfaz tests/e2e --browser chromium --tracing retain-on-failure --screenshot only-on-failure
if [ "$status" -eq 0 ]; then
  run_phase restauracion tests/destructive
else
  echo "Se omite restauración porque fallaron pruebas anteriores." | tee test-artifacts/restauracion_omitida.txt
fi
python - <<'PY2'
from pathlib import Path
art=Path('test-artifacts')
reports=sorted(p.name for p in art.glob('*.html'))
Path('test-artifacts/LEEME_RESULTADOS.txt').write_text(
    'Reportes generados:\n' + '\n'.join(f'- {x}' for x in reports) +
    '\n\nRevise también docker.log, compose-ps.txt, screenshots y traces.\n', encoding='utf-8')
PY2
exit "$status"
