param([int]$Port = 9527)

$ErrorActionPreference = "Continue"
Write-Host "清理端口 $Port 残留进程..."

$pids = @()
try {
  $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
  $pids = $conns | ForEach-Object { $_.OwningProcess } | Sort-Object -Unique
} catch {
  $lines = netstat -ano | Select-String ":$Port"
  $pids = $lines | ForEach-Object {
    $parts = ($_.ToString().Trim() -replace "\s+", " ").Split(" ")
    [int]$parts[-1]
  } | Sort-Object -Unique
}

$pids = $pids | Where-Object { $_ -gt 4 -and $_ -ne $PID }
if (-not $pids -or $pids.Count -eq 0) {
  Write-Host "未发现监听 $Port 的可终止进程"
  exit 0
}

foreach ($procId in $pids) {
  try {
    Stop-Process -Id $procId -Force -ErrorAction Stop
    Write-Host "已结束 PID: $procId"
  } catch {
    Write-Host "结束 PID 失败: $procId ($($_.Exception.Message))"
  }
}

Write-Host "清理完成"
