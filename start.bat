@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo === Desafio I2A2 D5 - Comunicacao Proativa com o Segurado ===
echo.

REM 1/4 - Ambiente virtual Python
if exist .venv\Scripts\python.exe (
    echo [1/4] Ambiente virtual Python encontrado.
) else (
    echo [1/4] Criando ambiente virtual Python...
    set "PY="
    where py >nul 2>nul && set "PY=py"
    if defined PY (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist .venv\Scripts\python.exe (
        echo Erro: nao foi possivel criar o ambiente virtual. Verifique se o Python 3.12+ esta instalado.
        exit /b 1
    )
)

REM 2/4 - Dependencias Python
echo [2/4] Instalando dependencias Python...
.venv\Scripts\python.exe -m pip install -e ".[dev]" --quiet
if errorlevel 1 (
    echo Erro: falha ao instalar as dependencias Python.
    exit /b 1
)

REM 3/4 - Dependencias do frontend
if exist frontend\package.json (
    if exist frontend\node_modules (
        echo [3/4] Dependencias do frontend encontradas.
    ) else (
        echo [3/4] Instalando dependencias do frontend...
        pushd frontend
        call npm install --no-fund --no-audit
        if errorlevel 1 (
            popd
            echo Erro: falha ao instalar as dependencias do frontend. Verifique se o Node.js esta instalado.
            exit /b 1
        )
        popd
    )
) else (
    echo [3/4] Frontend nao encontrado; seguindo apenas com a API.
)

REM 4/4 - Build do frontend
if exist frontend\package.json (
    if exist frontend\dist\index.html (
        echo [4/4] Build do frontend encontrado.
    ) else (
        echo [4/4] Gerando build do frontend...
        pushd frontend
        call npm run build
        if errorlevel 1 (
            popd
            echo Erro: falha no build do frontend.
            exit /b 1
        )
        popd
    )
)

echo.
echo API e interface disponiveis em http://127.0.0.1:8000
echo Documentacao interativa em http://127.0.0.1:8000/docs
echo Pressione Ctrl+C para encerrar.
echo.
.venv\Scripts\python.exe main.py
