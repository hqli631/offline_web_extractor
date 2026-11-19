param(
    [Parameter(Mandatory=$true)][uri]$Url,
    [Parameter(Mandatory=$true)][string]$OutFile
)
$ErrorActionPreference = 'Stop'
if ($Url.Scheme -notin @('http','https')) { throw 'Only http/https URLs are supported.' }
$destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutFile)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
Invoke-WebRequest -Uri $Url.AbsoluteUri -OutFile $destination -TimeoutSec 30
$manifest = [ordered]@{
    requested_url = $Url.AbsoluteUri
    fetched_at = [DateTimeOffset]::Now.ToString('o')
    sha256 = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    note = 'Raw HTTP HTML snapshot. JavaScript was not executed. Check that the response contains the target article.'
}
$manifest | ConvertTo-Json | Set-Content -LiteralPath ($destination + '.source.json') -Encoding utf8
Write-Output "Saved HTML: $destination"
