param(
    [string]$OutputRoot = (Join-Path (Join-Path $PSScriptRoot "..") "split-repos"),
    [string[]]$Services,
    [switch]$Force,
    [switch]$SkipCommit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendRoot = Join-Path $workspaceRoot "backend"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$testInternalServiceKeys = [ordered]@{
    "API_EXECUTE_INTERNAL_SERVICE_SECRET_KEY" = "test-api-execute-internal-service-key-0123456789ab"
    "AI_DIALER_INTERNAL_SERVICE_SECRET_KEY" = "test-ai-dialer-internal-service-key-0123456789abcd"
    "CALLBACK_MANUAL_INTERNAL_SERVICE_SECRET_KEY" = "test-callback-manual-internal-service-key-0123456789"
    "TASKS_INTERNAL_SERVICE_SECRET_KEY" = "test-tasks-internal-service-key-0123456789abcdef"
    "CANALES_SERVICE_INTERNAL_SERVICE_SECRET_KEY" = "test-canales-service-internal-service-key-012345678"
    "OPEN_AGENT_INTERNAL_SERVICE_SECRET_KEY" = "test-open-agent-internal-service-key-012345678901"
}

$serviceMatrix = @(
    [pscustomobject]@{
        Id = "api_execute"
        RepoName = "sudamerica-api-execute"
        ImageName = "api-execute"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $true
    },
    [pscustomobject]@{
        Id = "AI_dialer"
        RepoName = "sudamerica-ai-dialer"
        ImageName = "ai-dialer"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $false
    },
    [pscustomobject]@{
        Id = "callback_manual"
        RepoName = "sudamerica-callback-manual"
        ImageName = "callback-manual"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $false
    },
    [pscustomobject]@{
        Id = "tasks"
        RepoName = "sudamerica-tasks"
        ImageName = "tasks"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $false
    },
    [pscustomobject]@{
        Id = "canales_service"
        RepoName = "sudamerica-canales-service"
        ImageName = "canales-service"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $false
    },
    [pscustomobject]@{
        Id = "open_agent"
        RepoName = "sudamerica-open-agent"
        ImageName = "open-agent"
        HasApp = $true
        HasShared = $true
        IncludeDbAssets = $false
    },
    [pscustomobject]@{
        Id = "evolution_api"
        RepoName = "sudamerica-evolution-api"
        ImageName = "evolution-api"
        HasApp = $false
        HasShared = $false
        IncludeDbAssets = $false
    }
)

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Copy-IfExists {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (Test-Path $Source) {
        Copy-Item -Path $Source -Destination $Destination -Recurse -Force
    }
}

function New-RepoGitIgnore {
    @"
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
venv/
Lib/
Scripts/
Include/
.env
.env.local
*.py[cod]
*.egg
*.egg-info/
.coverage
coverage.xml
htmlcov/
dist/
build/
.idea/
.vscode/
"@
}

function New-RepoDockerIgnore {
    @"
__pycache__/
.pytest_cache/
.ruff_cache/
.venv/
venv/
.git/
.env
*.egg
*.egg-info/
htmlcov/
.coverage
"@
}

function New-TestBootstrap {
    $lines = @(
        '"""Standalone repo pytest bootstrap."""',
        "",
        "import os",
        "",
        "_TEST_INTERNAL_SERVICE_KEYS = {"
    )

    foreach ($entry in $testInternalServiceKeys.GetEnumerator()) {
        $lines += ('    "{0}": "{1}",' -f $entry.Key, $entry.Value)
    }

    $lines += "}"
    $lines += ""
    $lines += "for env_name, env_value in _TEST_INTERNAL_SERVICE_KEYS.items():"
    $lines += "    os.environ.setdefault(env_name, env_value)"
    $lines += ""

    return ($lines -join "`n")
}

function New-Pyproject {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectName,
        [Parameter(Mandatory = $true)][bool]$HasShared
    )

    $sourceLine = if ($HasShared) { 'source = ["app", "shared"]' } else { 'source = ["app"]' }

    @"
[project]
name = "$ProjectName"
version = "0.1.0"
description = "Standalone microservice repo generated from MVP monorepo"
requires-python = ">=3.11"

[tool.ruff]
target-version = "py311"
line-length = 120
select = ["E", "F", "W", "I", "C901", "B", "UP"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short --import-mode=importlib"

[tool.coverage.run]
$sourceLine
omit = ["*/tests/*"]

[tool.coverage.report]
fail_under = 70
show_missing = true
"@
}

function New-CloudBuild {
    param([Parameter(Mandatory = $true)][string]$ImageName)

    @"
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/`$PROJECT_ID/sudamerica/${ImageName}:`$SHORT_SHA', '.']

images:
  - 'us-central1-docker.pkg.dev/`$PROJECT_ID/sudamerica/${ImageName}:`$SHORT_SHA'

options:
  logging: CLOUD_LOGGING_ONLY
"@
}

function New-Dockerfile {
    param(
        [Parameter(Mandatory = $true)][string]$ServiceId,
        [Parameter(Mandatory = $true)][bool]$HasShared,
        [Parameter(Mandatory = $true)][bool]$HasMainPy
    )

    if ($ServiceId -eq "evolution_api") {
        return "FROM docker.io/evoapicloud/evolution-api:v2.3.7`n"
    }

    $lines = @(
        "FROM python:3.12-slim",
        "",
        "WORKDIR /app",
        "",
        "RUN apt-get update && \",
        "    apt-get install -y --no-install-recommends gcc libpq-dev && \",
        "    rm -rf /var/lib/apt/lists/*",
        ""
    )

    if ($HasShared) {
        $lines += "COPY shared/ /opt/shared/"
        $lines += 'ENV PYTHONPATH="/opt"'
        $lines += ""
    }

    $lines += "COPY requirements.txt ."
    $lines += "RUN pip install --no-cache-dir -r requirements.txt"
    $lines += ""

    if ($HasMainPy) {
        $lines += "COPY main.py ./main.py"
    }

    $lines += "COPY app ./app"
    $lines += ""
    $lines += 'CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]'
    $lines += ""

    return ($lines -join "`n")
}

function New-OriginNote {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$RepoName,
        [Parameter(Mandatory = $true)][bool]$IncludesShared,
        [Parameter(Mandatory = $true)][bool]$IncludesDbAssets
    )

    $sharedLine = if ($IncludesShared) {
        "- Vendored copy of backend/shared included."
    } else {
        "- No vendored shared package required."
    }

    $dbLine = if ($IncludesDbAssets) {
        "- DB migration assets copied: alembic/, infra/, alembic.ini, init_db.py, init_db.sql, run_alembic.py."
    } else {
        "- No monorepo-level DB migration assets copied."
    }

    @"
# Standalone Repo Origin

This repo was generated from the MVP monorepo working tree.

- Source workspace: $workspaceRoot
- Source service path: $SourcePath
- Generated repo name: $RepoName
- Snapshot date: 2026-03-14
- Git history was not preserved. This is a clean bootstrap snapshot.
$sharedLine
$dbLine

Next steps:
1. Create an empty remote repository in GitHub.
2. Add the remote with `git remote add origin <url>`.
3. Push with `git push -u origin main`.
"@
}

function Initialize-Repo {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][bool]$SkipInitialCommit
    )

    try {
        git -C $RepoPath init -b main | Out-Null
    } catch {
        git -C $RepoPath init | Out-Null
        git -C $RepoPath checkout -b main | Out-Null
    }

    git -C $RepoPath config user.name "Codex" | Out-Null
    git -C $RepoPath config user.email "codex@local" | Out-Null
    git -C $RepoPath add . | Out-Null

    if (-not $SkipInitialCommit) {
        git -C $RepoPath commit -m "chore: bootstrap standalone repo from MVP monorepo snapshot" | Out-Null
    }
}

function Select-Services {
    if (-not $Services -or $Services.Count -eq 0) {
        return $serviceMatrix
    }

    $requested = @{}
    foreach ($name in $Services) {
        $requested[$name] = $true
    }

    $selected = @()
    foreach ($service in $serviceMatrix) {
        if ($requested.ContainsKey($service.Id) -or $requested.ContainsKey($service.RepoName)) {
            $selected += $service
        }
    }

    if ($selected.Count -ne $requested.Count) {
        $valid = ($serviceMatrix | ForEach-Object { $_.Id }) -join ", "
        throw "Unknown service requested. Valid values: $valid"
    }

    return $selected
}

$selectedServices = Select-Services
New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null

foreach ($service in $selectedServices) {
    $sourceDir = Join-Path $backendRoot $service.Id
    $repoPath = Join-Path $OutputRoot $service.RepoName

    if (Test-Path $repoPath) {
        if (-not $Force) {
            throw "Output path already exists: $repoPath. Re-run with -Force to replace it."
        }

        Remove-Item -Path $repoPath -Recurse -Force
    }

    New-Item -ItemType Directory -Path $repoPath -Force | Out-Null

    if ($service.HasApp) {
        Copy-IfExists (Join-Path $sourceDir "app") (Join-Path $repoPath "app")
        Copy-IfExists (Join-Path $sourceDir "tests") (Join-Path $repoPath "tests")
        Copy-IfExists (Join-Path $sourceDir "main.py") (Join-Path $repoPath "main.py")
        Copy-IfExists (Join-Path $sourceDir "requirements.txt") (Join-Path $repoPath "requirements.txt")
        Copy-IfExists (Join-Path $sourceDir "README.md") (Join-Path $repoPath "README.md")
        Copy-IfExists (Join-Path $sourceDir ".env.example") (Join-Path $repoPath ".env.example")
    } else {
        Copy-IfExists (Join-Path $sourceDir "Dockerfile") (Join-Path $repoPath "Dockerfile")
    }

    if ($service.HasShared) {
        Copy-IfExists (Join-Path $backendRoot "shared") (Join-Path $repoPath "shared")
        Get-ChildItem -Path (Join-Path $repoPath "shared") -Directory -Filter "*.egg-info" -Recurse -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($service.IncludeDbAssets) {
        Copy-IfExists (Join-Path $backendRoot "alembic") (Join-Path $repoPath "alembic")
        Copy-IfExists (Join-Path $backendRoot "infra") (Join-Path $repoPath "infra")
        Copy-IfExists (Join-Path $backendRoot "alembic.ini") (Join-Path $repoPath "alembic.ini")
        Copy-IfExists (Join-Path $backendRoot "init_db.py") (Join-Path $repoPath "init_db.py")
        Copy-IfExists (Join-Path $backendRoot "init_db.sql") (Join-Path $repoPath "init_db.sql")
        Copy-IfExists (Join-Path $backendRoot "run_alembic.py") (Join-Path $repoPath "run_alembic.py")
    }

    if ($service.HasApp) {
        Write-Utf8File -Path (Join-Path $repoPath "Dockerfile") -Content (New-Dockerfile -ServiceId $service.Id -HasShared $service.HasShared -HasMainPy (Test-Path (Join-Path $sourceDir "main.py")))
        Write-Utf8File -Path (Join-Path $repoPath ".dockerignore") -Content (New-RepoDockerIgnore)
        Write-Utf8File -Path (Join-Path $repoPath ".gitignore") -Content (New-RepoGitIgnore)
        Write-Utf8File -Path (Join-Path $repoPath "pyproject.toml") -Content (New-Pyproject -ProjectName $service.RepoName -HasShared $service.HasShared)
        Write-Utf8File -Path (Join-Path $repoPath "cloudbuild.yaml") -Content (New-CloudBuild -ImageName $service.ImageName)
        Write-Utf8File -Path (Join-Path $repoPath "conftest.py") -Content (New-TestBootstrap)
    } else {
        Write-Utf8File -Path (Join-Path $repoPath ".dockerignore") -Content (New-RepoDockerIgnore)
        Write-Utf8File -Path (Join-Path $repoPath ".gitignore") -Content (New-RepoGitIgnore)
        Write-Utf8File -Path (Join-Path $repoPath "cloudbuild.yaml") -Content (New-CloudBuild -ImageName $service.ImageName)
        Write-Utf8File -Path (Join-Path $repoPath "README.md") -Content @"
# sudamerica-evolution-api

Standalone repo wrapper for the Evolution API Cloud Run deployment.

- Source image: `docker.io/evoapicloud/evolution-api:v2.3.7`
- This repo contains only deployment assets.
"@
    }

    Write-Utf8File -Path (Join-Path $repoPath "MONOREPO_ORIGIN.md") -Content (
        New-OriginNote -SourcePath ("backend/" + $service.Id) -RepoName $service.RepoName -IncludesShared $service.HasShared -IncludesDbAssets $service.IncludeDbAssets
    )

    Initialize-Repo -RepoPath $repoPath -SkipInitialCommit:$SkipCommit
    Write-Host ("Created {0}" -f $repoPath)
}

Write-Host ("Generated {0} standalone repos under {1}" -f $selectedServices.Count, (Resolve-Path $OutputRoot).Path)
