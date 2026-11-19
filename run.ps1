param(
    [Parameter(Position=0)][ValidateSet('extract','evaluate','test')][string]$Action = 'extract',
    [Parameter(Position=1)][string]$InputFile = 'samples/python_blurb.html',
    [string]$Expected = 'samples/python_blurb.expected.json',
    [string]$OutputFile,
    [string]$XPath,
    [switch]$ShowCandidates,
    [string]$PythonPath
)
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    $localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    $bundlePython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Test-Path -LiteralPath $localPython) { $PythonPath = $localPython }
    elseif (Test-Path -LiteralPath $bundlePython) { $PythonPath = $bundlePython }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $PythonPath = 'python' }
    else { throw 'Python unavailable. Pass -PythonPath with a working Python executable.' }
}
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $PSScriptRoot
try {
    switch ($Action) {
        'extract' {
            $cliArgs = @('-m','src.webextractor.cli',$InputFile)
            if ($OutputFile) { $cliArgs += @('--output',$OutputFile) }
            if ($XPath) { $cliArgs += @('--xpath',$XPath) }
            if ($ShowCandidates) { $cliArgs += '--show-candidates' }
            & $PythonPath @cliArgs
        }
        'evaluate' {
            $cliArgs = @('-m','src.webextractor.evaluate',$InputFile,$Expected)
            if ($OutputFile) { $cliArgs += @('--output',$OutputFile) }
            & $PythonPath @cliArgs
        }
        'test' { & $PythonPath -m unittest discover -s tests -v }
    }
    $resultCode = $LASTEXITCODE
} finally { Pop-Location }
exit $resultCode
