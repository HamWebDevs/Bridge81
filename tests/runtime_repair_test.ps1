# Run using Windows PowerShell, not pwsh, to exercise the Windows 8.1-era API surface.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\RuntimeRepair.ps1')
$catalogPath = Join-Path $PSScriptRoot '..\scripts\ucrt-manifest.json'
$catalog = Get-BridgeCatalog $catalogPath
$sandbox = Join-Path ([IO.Path]::GetTempPath()) ('Bridge81 repair test ' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($sandbox) | Out-Null
$script:checks = 0
function Assert-True([bool]$Value, [string]$Message) {
    if (-not $Value) { throw ('FAILED: ' + $Message) }
    $script:checks++
}
function Assert-Throws([scriptblock]$Action, [string]$Pattern) {
    $caught = $null
    try { & $Action | Out-Null } catch { $caught = $_.Exception.Message }
    Assert-True ($null -ne $caught -and $caught -match $Pattern) ('Expected ' + $Pattern + '; got ' + $caught)
}
function Write-TestPe([string]$Path, [string]$Architecture) {
    $bytes = New-Object byte[] 512
    $bytes[0] = 0x4d; $bytes[1] = 0x5a
    [BitConverter]::GetBytes([uint32]128).CopyTo($bytes, 60)
    [BitConverter]::GetBytes([uint32]0x4550).CopyTo($bytes, 128)
    if ($Architecture -eq 'x64') { $machine = 0x8664; $magic = 0x20b } else { $machine = 0x14c; $magic = 0x10b }
    [BitConverter]::GetBytes([uint16]$machine).CopyTo($bytes, 132)
    [BitConverter]::GetBytes([uint16]$magic).CopyTo($bytes, 152)
    [BitConverter]::GetBytes([uint16]6).CopyTo($bytes, 200)
    [IO.File]::WriteAllBytes($Path, $bytes)
}
function New-TestGame([string]$Name = 'Game with spaces and '' quotes') {
    $root = Join-Path $sandbox $Name
    foreach ($directory in @($root, (Join-Path $root 'renpy'), (Join-Path $root 'game'),
                             (Join-Path $root 'lib\windows-x86_64'), (Join-Path $root 'lib\windows-i686'))) {
        [IO.Directory]::CreateDirectory($directory) | Out-Null
    }
    [IO.File]::WriteAllText((Join-Path $root 'renpy\__init__.py'), "version_tuple = (8, 3, 7)`nraise Exception('must not run')")
    Write-TestPe (Join-Path $root 'Story.exe') 'x64'
    Write-TestPe (Join-Path $root 'lib\windows-x86_64\Story.exe') 'x64'
    Write-TestPe (Join-Path $root 'lib\windows-i686\Story.exe') 'x86'
    [IO.File]::WriteAllText((Join-Path $root 'game\keep-save.txt'), 'save-data-must-not-change')
    return $root
}
try {
    Assert-True ($catalog.payloads.x86.files.Count -eq 41 -and $catalog.payloads.x64.files.Count -eq 41) 'complete catalog'
    $root = New-TestGame
    $exe = Join-Path $root 'Story.exe'
    $exeHash = Get-BridgeHash $exe
    Assert-True ((Get-BridgePe $exe).Architecture -eq 'x64') 'read x64 PE without running it'
    $targets = Get-BridgeGameTargets $exe
    Assert-True ($targets.Targets.Count -eq 3) 'root and both RenPy engine architectures found'
    Assert-True ($targets.Targets[2].Architecture -in @('x86', 'x64')) 'engine architecture read from PE'
    Assert-Throws { Get-BridgePe (Join-Path $root 'renpy\__init__.py') } 'Not a Windows executable'
    [IO.File]::WriteAllText((Join-Path $root 'renpy\vc_version.py'), 'version_tuple = (8, 4, 1)')
    Assert-Throws { Get-BridgeGameTargets $exe } 'requires Windows 10'
    [IO.File]::Delete((Join-Path $root 'renpy\vc_version.py'))
    Assert-Throws { Resolve-BridgeReceiptPath $root '..\ucrtbase.dll' $catalog } 'Invalid repair receipt'
    Assert-Throws { Resolve-BridgeReceiptPath $root 'game\save.dat' $catalog } 'non-runtime'
    $invalid = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json
    $invalid.payloads.x64.url = 'https://example.com/runtime.cab'
    $badCatalog = Join-Path $sandbox 'bad.json'
    $invalid | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $badCatalog
    Assert-Throws { Get-BridgeCatalog $badCatalog } 'pinned official'

    # Live integration: official HTTPS cabinet, pinned SHA-256, Windows expand.exe,
    # every extracted DLL's checksum and actual machine architecture. No game runs.
    $cache = Join-Path $sandbox 'runtime cache'
    $original = Join-Path $root 'ucrtbase.dll'
    [IO.File]::WriteAllText($original, 'original-game-runtime')
    $originalHash = Get-BridgeHash $original
    $saveHash = Get-BridgeHash (Join-Path $root 'game\keep-save.txt')
    $message = Install-BridgeRuntime $exe $catalog $cache { param($m) Write-Host $m }
    Assert-True ($message -like 'Runtime added*') 'repair completes'
    foreach ($target in $targets.Targets) {
        foreach ($file in $catalog.payloads.($target.Architecture).files) {
            Assert-True ((Get-BridgeHash (Join-Path $target.Directory $file.name)) -eq $file.sha256) ('DLL verified: ' + $file.name)
        }
    }
    Assert-True ((Get-BridgeHash $exe) -eq $exeHash) 'launcher bytes unchanged'
    Assert-True ((Get-BridgeHash (Join-Path $root 'game\keep-save.txt')) -eq $saveHash) 'game data unchanged'
    Assert-Throws { Install-BridgeRuntime $exe $catalog $cache } 'previous repair'
    $receipt = Join-Path $root '.bridge81-runtime\receipt.json'
    $receiptData = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
    Assert-True (@($receiptData.files).Count -eq 123) 'receipt tracks three complete sets'
    Assert-True ((Get-Content -LiteralPath $receipt -Raw) -notlike ('*' + $sandbox + '*')) 'receipt uses relative paths'
    $modified = Join-Path $root 'api-ms-win-crt-heap-l1-1-0.dll'
    [IO.File]::WriteAllText($modified, 'later-user-changes')
    Assert-Throws { Undo-BridgeRuntime $root $catalog } 'changed after repair'
    Assert-True ((Get-BridgeHash $original) -ne $originalHash) 'refused Undo did not partially restore other files'
    $runtimeFolder = Join-Path $cache ($catalog.version + '\x64')
    [IO.File]::Copy((Join-Path $runtimeFolder 'api-ms-win-crt-heap-l1-1-0.dll'), $modified, $true)
    Undo-BridgeRuntime $root $catalog | Out-Null
    Assert-True ((Get-BridgeHash $original) -eq $originalHash) 'Undo restores original'
    Assert-True (-not [IO.File]::Exists($modified)) 'Undo removes added DLL'
    Assert-True (-not [IO.Directory]::Exists((Join-Path $root '.bridge81-runtime'))) 'Undo removes completed receipt'
    Assert-True ((Get-BridgeHash (Join-Path $root 'game\keep-save.txt')) -eq $saveHash) 'Undo preserves game data'

    # Browser/offline downloads must work without making a network request.
    $offline = Join-Path $sandbox 'browser downloads'
    [IO.Directory]::CreateDirectory($offline) | Out-Null
    $payload = $catalog.payloads.x86
    $offlineCab = Join-Path $offline ([IO.Path]::GetFileName(([Uri]$payload.url).AbsolutePath))
    [IO.File]::Copy((Join-Path $cache ($catalog.version + '\x86\runtime.cab')), $offlineCab)
    $script:downloadRequested = $false
    $offlineResult = Get-BridgeRuntimeFiles $catalog 'x86' (Join-Path $sandbox 'offline cache') { param($m) $script:downloadRequested = $true } @($offline)
    Assert-True (-not $script:downloadRequested) 'verified browser download used without network'
    Assert-True ((Get-BridgeHash (Join-Path $offlineResult 'ucrtbase.dll')) -eq ($payload.files | Where-Object { $_.name -eq 'ucrtbase.dll' }).sha256) 'offline runtime verified'

    # Corrupted cached DLLs are rebuilt from the verified cabinet, not trusted.
    [IO.File]::WriteAllText((Join-Path $runtimeFolder 'ucrtbase.dll'), 'corrupt-cache')
    Install-BridgeRuntime $exe $catalog $cache | Out-Null
    Assert-True ((Get-BridgeHash $original) -eq ($catalog.payloads.x64.files | Where-Object { $_.name -eq 'ucrtbase.dll' }).sha256) 'corrupt cache repaired'
    # Receipt traversal must stop before any restoration or deletion.
    $goodReceipt = [IO.File]::ReadAllText($receipt)
    $tampered = $goodReceipt | ConvertFrom-Json
    $tampered.files[0].path = '..\ucrtbase.dll'
    $tampered | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receipt -Encoding UTF8
    Assert-Throws { Undo-BridgeRuntime $root $catalog } 'Invalid repair receipt'
    [IO.File]::WriteAllText($receipt, $goodReceipt)
    Undo-BridgeRuntime $root $catalog | Out-Null

    # Failure partway through copy must restore earlier replacements and additions.
    $script:realAtomicCopy = ${function:Copy-BridgeAtomic}
    $script:copyAttempts = 0
    function Copy-BridgeAtomic([string]$Source, [string]$Destination) {
        if ($Destination.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) {
            $script:copyAttempts++
            if ($script:copyAttempts -eq 5) { throw 'simulated write failure' }
        }
        & $script:realAtomicCopy $Source $Destination
    }
    Assert-Throws { Install-BridgeRuntime $exe $catalog $cache } 'simulated write failure'
    Assert-True ((Get-BridgeHash $original) -eq $originalHash) 'failure rolls back original runtime'
    Assert-True (-not [IO.File]::Exists($modified)) 'failure removes earlier additions'
    Assert-True (-not [IO.File]::Exists($receipt)) 'completed rollback removes receipt'
    Set-Item -Path function:Copy-BridgeAtomic -Value $script:realAtomicCopy

    # Junction rejection on an otherwise plausible Windows engine directory.
    if ([Environment]::OSVersion.Platform -eq 'Win32NT') {
        $junctionGame = New-TestGame 'junction-game'
        $link = Join-Path $junctionGame 'lib\windows-x86_64'
        Remove-Item -LiteralPath $link -Recurse -Force
        New-Item -ItemType Junction -Path $link -Target (Join-Path $root 'lib\windows-x86_64') | Out-Null
        Assert-Throws { Get-BridgeGameTargets (Join-Path $junctionGame 'Story.exe') } 'junction or symbolic link'
        [IO.Directory]::Delete($link)
    }
    Write-Host ('Runtime repair checks passed: ' + $script:checks + '. Real Microsoft cabinets downloaded and verified; no Windows 8.1 claim.')
} finally {
    Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
}
