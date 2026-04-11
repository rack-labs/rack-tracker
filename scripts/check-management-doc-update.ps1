param(
    [switch]$Staged
)

$ErrorActionPreference = "Stop"

$managementDocPattern = '^docs/mvp-v2/issues/(sub-issues/|[^/]+/).+\.md$'
$currentBranch = (git branch --show-current).Trim()

function Get-ChangedPaths {
    param([switch]$UseStaged)

    if ($UseStaged) {
        $output = git diff --cached --name-only --diff-filter=ACMR
        if (-not $output) {
            return @()
        }

        return @($output | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    $trackedChanges = git diff --name-only --diff-filter=ACMR HEAD
    $untrackedFiles = git ls-files --others --exclude-standard

    $paths = @()
    if ($trackedChanges) {
        $paths += @($trackedChanges | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    if ($untrackedFiles) {
        $paths += @($untrackedFiles | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    return @($paths | Select-Object -Unique)
}

$changedPaths = Get-ChangedPaths -UseStaged:$Staged

if ($changedPaths.Count -eq 0) {
    Write-Host "No changed files detected for management-document check."
    exit 0
}

$managementDocs = @($changedPaths | Where-Object { $_ -match $managementDocPattern })
$nonManagementDocs = @($changedPaths | Where-Object { $_ -notmatch $managementDocPattern })
$expectedManagementDocs = @()

if ($currentBranch) {
    $escapedBranch = [regex]::Escape($currentBranch)
    $expectedManagementDocs = @(
        $managementDocs | Where-Object {
            $_ -match "^docs/mvp-v2/issues/(sub-issues/|[^/]+/)$escapedBranch\.md$"
        }
    )
}

if ($nonManagementDocs.Count -eq 0) {
    Write-Host "Only management documents changed."
    exit 0
}

if ($expectedManagementDocs.Count -gt 0) {
    Write-Host "Management-document check passed."
    Write-Host "Changed matching management document(s):"
    $expectedManagementDocs | ForEach-Object { Write-Host " - $_" }
    exit 0
}

Write-Error @"
Management-document check failed.
Changed files were found without an updated management document for the current branch.

Current branch: $currentBranch
Expected management document name: $currentBranch.md under docs/mvp-v2/issues/ or docs/mvp-v2/issues/sub-issues/

Add or update the matching management document before commit.
If this is not issue-tracked work, re-check AGENTS.md and docs/agent-workflow/documentation-rules.md before proceeding.
"@
