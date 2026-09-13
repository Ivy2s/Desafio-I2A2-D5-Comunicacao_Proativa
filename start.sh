#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== Desafio I2A2 D5 - Comunicacao Proativa com o Segurado ==="

PY=python3
if [ ! -x .venv/bin/python ]; then
    echo "[1/4] Criando ambiente virtual Python..."
    "$PY" -m venv .venv
else
    echo "[1/4] Ambiente virtual Python encontrado."
fi

echo "[2/4] Instalando dependencias Python..."
.venv/bin/python -m pip install -e '.[dev]' --quiet

if [ -f frontend/package.json ]; then
    if [ -d frontend/node_modules ]; then
        echo "[3/4] Dependencias do frontend encontradas."
    else
        echo "[3/4] Instalando dependencias do frontend..."
        (cd frontend && npm install --no-fund --no-audit)
    fi

    if [ -f frontend/dist/index.html ]; then
        echo "[4/4] Build do frontend encontrado."
    else
        echo "[4/4] Gerando build do frontend..."
        (cd frontend && npm run build)
    fi
else
    echo "[3/4] Frontend nao encontrado; seguindo apenas com a API."
fi

echo
echo "API e interface disponiveis em http://127.0.0.1:8000"
echo "Pressione Ctrl+C para encerrar."
echo
exec .venv/bin/python main.py
