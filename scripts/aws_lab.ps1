param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("prepare", "validate", "preflight", "plan", "deploy", "run-etl",
                 "query-checks", "endpoint-check", "inventory", "teardown")]
    [string]$Operation,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$LabArguments
)
$ErrorActionPreference = "Stop"
$LabRoot = Split-Path -Parent $PSScriptRoot
$LabPython = Join-Path $LabRoot ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $LabPython)) {
    throw "Create the documented application environment first."
}
& $LabPython (Join-Path $PSScriptRoot "aws_lab.py") $Operation @LabArguments
exit $LASTEXITCODE
