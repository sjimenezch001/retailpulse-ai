param(
    [Parameter(Mandatory = $true)][int]$Port,
    [string]$DesktopBin = 'C:\Program Files\Microsoft Power BI Desktop\bin',
    [string]$EvidenceFile = 'docs/evidence/rp08_desktop_validation.json'
)
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Add-Type -Path (Join-Path $DesktopBin 'Microsoft.PowerBI.AdomdClient.dll')
$connection = [Microsoft.AnalysisServices.AdomdClient.AdomdConnection]::new("Data Source=localhost:$Port")
$results = [System.Collections.Generic.List[object]]::new()
try {
    $connection.Open()
    $checks = Get-Content -LiteralPath (Join-Path $repoRoot 'artifacts/powerbi/dax-checks.json') -Raw | ConvertFrom-Json
    foreach ($check in $checks) {
        $command = $connection.CreateCommand()
        $command.CommandText = $check.dax
        $reader = $command.ExecuteReader()
        if (-not $reader.Read()) { throw "No result: $($check.name)" }
        $actual = [ordered]@{}
        for ($index = 0; $index -lt $reader.FieldCount; $index++) {
            $name = $reader.GetName($index).Trim('[', ']')
            $value = if ($reader.IsDBNull($index)) { $null } else { $reader.GetValue($index) }
            $expected = $check.expected.$name
            if ($null -eq $expected -or $null -eq $value) {
                if (($null -eq $expected) -ne ($null -eq $value)) { throw "NULL mismatch: $($check.name).$name" }
            } elseif ([Math]::Abs([double]$value - [double]$expected) -gt [Math]::Max(1e-8, 1e-10 * [Math]::Abs([double]$expected))) {
                throw "DAX/SQL mismatch: $($check.name).$name actual=$value expected=$expected"
            }
            $actual[$name] = $value
        }
        $reader.Close()
        $results.Add([ordered]@{check=$check.name;status='PASS';values=$actual})
    }
} finally { $connection.Close() }
$evidence = [ordered]@{status='PASS';interface='Local Desktop ADOMD DAX';checks=$results}
$evidence | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $repoRoot $EvidenceFile) -Encoding utf8
Write-Output "Live Desktop DAX: $($results.Count) checks passed."
