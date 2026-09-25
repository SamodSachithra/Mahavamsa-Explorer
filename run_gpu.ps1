$ErrorActionPreference = 'Stop'

$env:OLLAMA_LLM_LIBRARY = 'cuda'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_KEEP_ALIVE = '30m'
$env:OLLAMA_FLASH_ATTENTION = '1'
$env:OLLAMA_LOAD_TIMEOUT = '10m'

$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "Python virtual environment was not found at $python"
}

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    throw 'ollama executable was not found on PATH'
}

Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process ollama -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host 'Starting Ollama server with CUDA backend...'
Start-Process -FilePath $ollama.Source -ArgumentList 'serve' -NoNewWindow
Start-Sleep -Seconds 5

Write-Host 'Starting Mahavamsa GraphRAG with GPU-backed Ollama settings...'
Write-Host "OLLAMA_LLM_LIBRARY=$env:OLLAMA_LLM_LIBRARY"
Write-Host "OLLAMA_NUM_PARALLEL=$env:OLLAMA_NUM_PARALLEL"
Write-Host "OLLAMA_MAX_LOADED_MODELS=$env:OLLAMA_MAX_LOADED_MODELS"
Write-Host "OLLAMA_KEEP_ALIVE=$env:OLLAMA_KEEP_ALIVE"
Write-Host "OLLAMA_FLASH_ATTENTION=$env:OLLAMA_FLASH_ATTENTION"

& $python -m uvicorn src.api.main:app --reload --port 8000
