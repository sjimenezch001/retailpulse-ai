param([string]$TomDirectory = 'artifacts/rp08-tools/tom')
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$tomRoot = (Resolve-Path (Join-Path $repoRoot $TomDirectory)).Path
Add-Type -Path (Join-Path $tomRoot 'Microsoft.AnalysisServices.Core.dll')
Add-Type -Path (Join-Path $tomRoot 'Microsoft.AnalysisServices.Tabular.dll')
$modelJson = Get-Content -LiteralPath (Join-Path $repoRoot 'artifacts/rp08-tools/model.json') -Raw
$database = [Microsoft.AnalysisServices.Tabular.JsonSerializer]::DeserializeDatabase($modelJson)
$definition = Join-Path $PSScriptRoot 'RetailPulse.SemanticModel/definition'
[Microsoft.AnalysisServices.Tabular.TmdlSerializer]::SerializeDatabaseToFolder($database, $definition)
Get-ChildItem -LiteralPath $definition -Recurse -Filter '*.tmdl' -File | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName).Replace("`r`n", "`n").TrimEnd([char[]]"`r`n") + "`n"
    [System.IO.File]::WriteAllText($_.FullName, $content, [System.Text.UTF8Encoding]::new($false))
}
$roundtrip = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder($definition)
Write-Output "TMDL roundtrip passed: $($roundtrip.Model.Tables.Count) tables, $($roundtrip.Model.Relationships.Count) relationships."
