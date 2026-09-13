#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
RUNTIME_BASE="${HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies"
PY_BIN="${CODEX_PYTHON_BIN:-${RUNTIME_BASE}/python/bin/python3}"
NODE_BIN="${CODEX_NODE_BIN:-${RUNTIME_BASE}/node/bin/node}"
export PYTHONPATH="$PROJECT_DIR/work/python_deps:$PROJECT_DIR${PYTHONPATH:+:$PYTHONPATH}"
FINAL="outputs/c_final_v1"
mkdir -p "$FINAL/logs" "$FINAL/qa" work/fontconfig
if [[ ! -e node_modules ]]; then ln -s "$RUNTIME_BASE/node/node_modules" node_modules; fi
if [[ "${1:-}" != "--skip-model" ]]; then
  "$PY_BIN" -m unittest discover -s tests -v 2>&1 | tee "$FINAL/logs/constraint_and_causality_tests.log"
  "$PY_BIN" -u scripts/run_model.py --scope all 2>&1 | tee "$FINAL/logs/repaired_model.log"
fi
"$PY_BIN" scripts/analyze_results.py 2>&1 | tee "$FINAL/logs/analysis.log"
"$PY_BIN" -u scripts/strengthen_evidence.py 2>&1 | tee "$FINAL/logs/strengthen_evidence.log"
"$PY_BIN" src/audit/audit_final.py 2>&1 | tee "$FINAL/logs/independent_model_audit.log"
"$NODE_BIN" scripts/build_workbooks.mjs 2>&1 | tee "$FINAL/logs/workbook_build.log"
"$PY_BIN" src/audit/audit_final.py --workbooks 2>&1 | tee "$FINAL/logs/independent_workbook_audit.log"
"$PY_BIN" scripts/make_charts.py 2>&1 | tee "$FINAL/logs/charts.log"
"$PY_BIN" scripts/build_documents.py 2>&1 | tee "$FINAL/logs/documents.log"
if [[ -d /Library/Fonts ]]; then
  cat > work/fontconfig/fonts.conf <<'XML'
<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/Library/Fonts</dir><dir>/System/Library/Fonts</dir><cachedir>/tmp/v3-font-cache</cachedir></fontconfig>
XML
  export FONTCONFIG_FILE="$PROJECT_DIR/work/fontconfig/fonts.conf"
fi
DOC_SKILL="${HOME}/.codex/plugins/cache/openai-primary-runtime/documents/26.905.11957/skills/documents"
"$PY_BIN" "$DOC_SKILL/render_docx.py" "$FINAL/paper/C题论文.docx" --output_dir "$FINAL/qa/paper_render" --emit_pdf 2>&1 | tee "$FINAL/logs/paper_render.log"
"$PY_BIN" "$DOC_SKILL/render_docx.py" "$FINAL/paper/AI工具使用详情.docx" --output_dir "$FINAL/qa/ai_render" --emit_pdf 2>&1 | tee "$FINAL/logs/ai_render.log"
cp "$FINAL/qa/paper_render/C题论文.pdf" "$FINAL/paper/C题论文.pdf"
cp "$FINAL/qa/ai_render/AI工具使用详情.pdf" "$FINAL/paper/AI工具使用详情.pdf"
"$PY_BIN" scripts/final_quality.py 2>&1 | tee "$FINAL/logs/final_quality.log"
"$PY_BIN" scripts/write_improvement_report.py
"$PY_BIN" scripts/package_final.py 2>&1 | tee work/package.log
echo "Current-run artifacts are in $FINAL; synchronize only after visual review."
