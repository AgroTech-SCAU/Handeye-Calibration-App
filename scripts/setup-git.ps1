$repoRoot = git rev-parse --show-toplevel 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
    Write-Error "[AgroTech] 当前目录不在 Git 仓库中"
    exit 1
}

Set-Location $repoRoot
git config --local core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) {
    Write-Error "[AgroTech] 设置 core.hooksPath 失败"
    exit 1
}

$hooksPath = git config --local --get core.hooksPath
Write-Host "[AgroTech] 已启用本仓库的本地 Git 防误操作提醒"
Write-Host "[AgroTech] core.hooksPath = $hooksPath"
Write-Host "[AgroTech] 注意：Hook 只是本地体验增强，main 的最终保护仍由 GitHub Ruleset 提供"
