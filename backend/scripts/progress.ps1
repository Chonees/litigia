# Live progress of a scraper run, read from its log.
# Usage (cmd, PowerShell or Git Bash):
#   powershell -ExecutionPolicy Bypass -File C:\Users\lucas\OneDrive\Escritorio\LITIGIA\backend\scripts\progress.ps1
#   ... -Log D:\litigia-data\logs\otro.log -Target 5000
param(
    [string]$Log = 'D:\litigia-data\logs\run_cnat_1000.log',
    [int]$Target = 1000
)

# The log can mix UTF-8 (python redirect) and UTF-16 (PowerShell Tee-Object) lines:
# read raw text and drop NUL bytes so both match.
# The writer keeps the file open, so open it shared instead of with ReadAllText.
function Read-Log {
    if (-not (Test-Path $Log)) { return '' }
    try {
        $fs = [IO.File]::Open($Log, 'Open', 'Read', 'ReadWrite')
        $reader = New-Object IO.StreamReader($fs)
        $text = $reader.ReadToEnd()
        $reader.Close()
        return $text -replace "`0", ''
    } catch {
        return ''
    }
}

while ($true) {
    $text = Read-Log
    $n = 0
    $m = [regex]::Matches($text, 'new ([\d,]+)')
    if ($m.Count -gt 0) { $n = [int]($m[$m.Count - 1].Groups[1].Value -replace ',', '') }
    $p = [math]::Min(100, [int][math]::Floor($n * 100 / $Target))
    $bar = '#' * [int][math]::Floor($p / 2)
    Write-Host -NoNewline ("`r{0,5}/{1}  {2,3}%  [{3,-50}]" -f $n, $Target, $p, $bar)
    if ($text -match 'DONE new') {
        Write-Host ' listo'
        break
    }
    Start-Sleep 5
}
