# Windows PowerShell 4.0 / .NET 4.5.1. Dot-source this file; no UI or work on import.
Set-StrictMode -Version 2.0

function Get-BridgeHash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
}

function Assert-BridgeRegularPath([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw 'A selected path uses a junction or symbolic link. Use an ordinary extracted game folder.'
        }
        if ($item -is [IO.FileInfo]) { $item = $item.Directory } else { $item = $item.Parent }
    }
}

function Get-BridgePe([string]$Path) {
    Assert-BridgeRegularPath $Path
    $stream = [IO.File]::Open($Path, 'Open', 'Read', 'Read')
    $reader = New-Object IO.BinaryReader($stream)
    try {
        if ($stream.Length -lt 256 -or $reader.ReadUInt16() -ne 0x5a4d) { throw 'Not a Windows executable.' }
        $stream.Position = 60
        $offset = $reader.ReadUInt32()
        if ($offset -lt 64 -or $offset -gt 1048576 -or $offset + 96 -gt $stream.Length) { throw 'Invalid PE header offset.' }
        $stream.Position = $offset
        if ($reader.ReadUInt32() -ne 0x4550) { throw 'Invalid PE signature.' }
        $machine = $reader.ReadUInt16()
        $stream.Position = $offset + 24
        $magic = $reader.ReadUInt16()
        if ($machine -eq 0x8664 -and $magic -eq 0x20b) { $arch = 'x64' }
        elseif ($machine -eq 0x14c -and $magic -eq 0x10b) { $arch = 'x86' }
        else { throw 'Only matching x86 and x64 Windows PE headers are supported.' }
        $stream.Position = $offset + 72
        $major = $reader.ReadUInt16(); $minor = $reader.ReadUInt16()
        return [pscustomobject]@{ Architecture = $arch; Subsystem = (New-Object Version($major, $minor)) }
    } finally { $reader.Dispose(); $stream.Dispose() }
}

function Get-BridgeCatalog([string]$Path) {
    $catalog = Get-Content -LiteralPath $Path -Raw -ErrorAction Stop | ConvertFrom-Json
    if ($catalog.schema -ne 1 -or $catalog.version -ne '10.0.14393.795') { throw 'Unsupported runtime catalog.' }
    foreach ($arch in @('x86', 'x64')) {
        $payload = $catalog.payloads.$arch
        $uri = New-Object Uri($payload.url)
        if ($uri.Scheme -ne 'https' -or $uri.Host -ne 'download.microsoft.com' -or
            $uri.AbsolutePath -notmatch '^/download/C/D/8/CD8533F8-5324-4D30-824C-B834C5AD51F9/standalonesdk/Installers/[0-9a-f]{32}\.cab$') {
            throw 'The catalog must use the pinned official Microsoft SDK location.'
        }
        if ($payload.sha256 -notmatch '^[0-9a-f]{64}$' -or $payload.size -gt 2000000 -or $payload.size -lt 100000) { throw 'Invalid cabinet metadata.' }
        $names = @{}
        foreach ($file in $payload.files) {
            if ($file.name -notmatch '^(ucrtbase|api-ms-win-(crt|core)-[a-z0-9-]+)\.dll$' -or
                $file.member -notmatch '^fil[0-9a-f]{32}$' -or $file.sha256 -notmatch '^[0-9a-f]{64}$' -or
                $file.size -lt 512 -or $file.size -gt 3000000 -or $file.version -ne $catalog.version -or $names.ContainsKey($file.name)) {
                throw 'Invalid or duplicate runtime DLL metadata.'
            }
            $names[$file.name] = $true
        }
        if ($names.Count -ne 41 -or -not $names.ContainsKey('ucrtbase.dll') -or
            -not $names.ContainsKey('api-ms-win-crt-heap-l1-1-0.dll')) { throw 'The complete 41-file runtime set is required.' }
    }
    return $catalog
}

function Copy-BridgeAtomic([string]$Source, [string]$Destination) {
    $temporary = Join-Path ([IO.Path]::GetDirectoryName($Destination)) ('.bridge81-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    $replaced = $temporary + '.old'
    try {
        [IO.File]::Copy($Source, $temporary, $false)
        # Windows PowerShell converts $null string arguments to empty strings.
        # An explicit temporary backup path works on the .NET 4.5 API too.
        if ([IO.File]::Exists($Destination)) { [IO.File]::Replace($temporary, $Destination, $replaced) }
        else { [IO.File]::Move($temporary, $Destination) }
    } finally {
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
        if ([IO.File]::Exists($replaced)) { [IO.File]::Delete($replaced) }
    }
}

function Test-BridgeHelperNeedsCrt([string]$Path) {
    # A bounded, conservative string check, not a complete dependency resolver.
    # Opposite-architecture helpers using the OS msvcrt.dll do not consume UCRT.
    Assert-BridgeRegularPath $Path
    $length = (Get-Item -LiteralPath $Path).Length
    if ($length -gt 16777216) { throw 'An opposite-architecture helper is too large to verify safely. No game files have been changed.' }
    $text = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($Path))
    return [regex]::IsMatch($text, '(?i)(ucrtbase|vcruntime14[0-9_]*|msvcp14[0-9_]*)\.dll|api-ms-win-(crt|core)-[a-z0-9-]+\.dll')
}

function Get-BridgeEngineArchitecture([IO.DirectoryInfo]$Directory, [string]$GameExecutableName) {
    Assert-BridgeRegularPath $Directory.FullName
    $files = @(Get-ChildItem -LiteralPath $Directory.FullName -File -Force)
    if ($files.Count -gt 1024) { throw 'Too many files in a Windows engine folder.' }
    $executables = @($files | Where-Object { $_.Extension -ieq '.exe' })
    if ($executables.Count -gt 32) { throw 'Too many engine executables.' }
    $engineNames = @($GameExecutableName, 'python.exe', 'pythonw.exe', 'renpy.exe')
    $engineExecutables = @($executables | Where-Object { $_.Name -in $engineNames })
    $pythonDlls = @($files | Where-Object { $_.Name -match '^((lib)?python\d{1,3}(\.\d+)?(_d)?|librenpython)\.dll$' })
    # Prefer actual engine entry points and Python DLLs over updater/helper EXEs.
    $runtimeFiles = @($engineExecutables) + @($pythonDlls)
    if ($runtimeFiles.Count -eq 0) { $runtimeFiles = $executables }
    $architectures = @{}
    foreach ($runtime in $runtimeFiles) {
        $pe = Get-BridgePe $runtime.FullName
        if ($pe.Subsystem -gt [Version]'6.3') { throw 'An engine runtime declares a Windows version newer than 8.1.' }
        $architectures[$pe.Architecture] = $true
    }
    if ($architectures.Count -gt 1) {
        throw ('Game/Python engine files disagree on architecture in lib/' + $Directory.Name + '. No files were changed; the engine files need to match.')
    }
    if ($architectures.Count -eq 0) { return $null }
    $architecture = @($architectures.Keys)[0]
    foreach ($helper in $executables) {
        if ($helper.Name -in $engineNames) { continue }
        $helperPe = Get-BridgePe $helper.FullName
        if ($helperPe.Architecture -ne $architecture -and (Test-BridgeHelperNeedsCrt $helper.FullName)) {
            throw ('Helper ' + $helper.Name + ' in lib/' + $Directory.Name + ' uses a different architecture and references UCRT/Visual C++ DLLs. One runtime set cannot serve both here; no files were changed.')
        }
    }
    return $architecture
}

function Get-BridgeGameTargets([string]$Executable) {
    $exe = [IO.Path]::GetFullPath($Executable)
    Assert-BridgeRegularPath $exe
    if ([IO.Path]::GetExtension($exe) -ine '.exe' -or -not [IO.File]::Exists($exe)) { throw 'Choose the game executable in its main extracted folder.' }
    $root = [IO.Path]::GetDirectoryName($exe)
    foreach ($name in @('game', 'renpy')) {
        $directory = Join-Path $root $name
        if (-not [IO.Directory]::Exists($directory)) { throw 'Choose the main game EXE beside the game and renpy folders, after extracting the whole game ZIP.' }
        Assert-BridgeRegularPath $directory
    }
    # Read bounded text only: never import or run game Python, or load a game DLL.
    foreach ($name in @('renpy\__init__.py', 'renpy\vc_version.py', 'log.txt', 'traceback.txt')) {
        $path = Join-Path $root $name
        if (-not [IO.File]::Exists($path)) { continue }
        Assert-BridgeRegularPath $path
        $stream = [IO.File]::OpenRead($path)
        try { $bytes = New-Object byte[] ([Math]::Min($stream.Length, 262144)); $count = $stream.Read($bytes, 0, $bytes.Length) }
        finally { $stream.Dispose() }
        $text = [Text.Encoding]::UTF8.GetString($bytes, 0, $count)
        $patterns = @('version_tuple\s*=\s*\(\s*(\d+)\s*,\s*(\d+)', 'Ren''Py\s+(\d+)\.(\d+)')
        foreach ($pattern in $patterns) {
            foreach ($match in [regex]::Matches($text, $pattern)) {
                if ([int]$match.Groups[1].Value -gt 8 -or ([int]$match.Groups[1].Value -eq 8 -and [int]$match.Groups[2].Value -ge 4)) {
                    throw 'This game identifies Ren''Py 8.4 or newer, which requires Windows 10. Adding the runtime cannot make that engine support Windows 8.1.'
                }
            }
        }
    }
    $pe = Get-BridgePe $exe
    if ($pe.Subsystem -gt [Version]'6.3') { throw 'The selected executable declares a Windows version newer than 8.1.' }
    if ($pe.Architecture -eq 'x64' -and -not [Environment]::Is64BitOperatingSystem) { throw 'A 64-bit game needs 64-bit Windows.' }
    $targets = @([pscustomobject]@{ Directory = $root; Architecture = $pe.Architecture })
    $lib = Join-Path $root 'lib'
    if ([IO.Directory]::Exists($lib)) {
        Assert-BridgeRegularPath $lib
        $directories = @(Get-ChildItem -LiteralPath $lib -Directory -Force)
        if ($directories.Count -gt 128) { throw 'Too many lib folders. Use a clean extracted game build.' }
        foreach ($directory in $directories) {
            if ($directory.Name -notmatch '^(py\d+(\.\d+)*-)?(windows[-_](x86_64|amd64|i686|x86)|win[-_](amd64|x86)|win32)$') { continue }
            Assert-BridgeRegularPath $directory.FullName
            $architecture = Get-BridgeEngineArchitecture $directory ([IO.Path]::GetFileName($exe))
            if ($null -ne $architecture) {
                if ($architecture -eq 'x86' -or [Environment]::Is64BitOperatingSystem) {
                    $targets += [pscustomobject]@{ Directory = $directory.FullName; Architecture = $architecture }
                }
            }
        }
    }
    return [pscustomobject]@{ Root = $root; Targets = $targets }
}

function Get-BridgeRuntimeFiles($Catalog, [string]$Architecture, [string]$Cache, [scriptblock]$Progress, [string[]]$OfflineFolders = @()) {
    $payload = $Catalog.payloads.$Architecture
    $folder = Join-Path $Cache ($Catalog.version + '\' + $Architecture)
    [IO.Directory]::CreateDirectory($folder) | Out-Null
    Assert-BridgeRegularPath $folder
    $cab = Join-Path $folder 'runtime.cab'
    if (Test-Path -LiteralPath $cab) { Assert-BridgeRegularPath $cab }
    if (-not [IO.File]::Exists($cab) -or (Get-BridgeHash $cab) -ne $payload.sha256) {
        foreach ($offlineFolder in $OfflineFolders) {
            $candidate = Join-Path $offlineFolder ([IO.Path]::GetFileName(([Uri]$payload.url).AbsolutePath))
            if (-not [IO.File]::Exists($candidate)) { continue }
            Assert-BridgeRegularPath $candidate
            if ((Get-Item -LiteralPath $candidate).Length -eq $payload.size -and (Get-BridgeHash $candidate) -eq $payload.sha256) {
                Copy-BridgeAtomic $candidate $cab
                break
            }
        }
    }
    if (-not [IO.File]::Exists($cab) -or (Get-BridgeHash $cab) -ne $payload.sha256) {
        & $Progress ('Downloading Microsoft runtime (' + $Architecture + ', less than 1 MB)...')
        $part = Join-Path $folder ([Guid]::NewGuid().ToString('N') + '.part')
        $oldProtocol = [Net.ServicePointManager]::SecurityProtocol
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $client = New-Object Net.WebClient
            try { $client.DownloadFile($payload.url, $part) }
            catch { throw 'Windows could not download the runtime. Use the browser download links in docs/runtime-repair.md, leave the CAB files in Downloads, then click Repair again. No certificate checks were disabled.' }
            finally { $client.Dispose() }
            if ((Get-Item -LiteralPath $part).Length -ne $payload.size -or (Get-BridgeHash $part) -ne $payload.sha256) { throw 'Microsoft download checksum mismatch. No game files have been changed.' }
            [IO.File]::Copy($part, $cab, $true)
        } finally {
            [Net.ServicePointManager]::SecurityProtocol = $oldProtocol
            if ([IO.File]::Exists($part)) { [IO.File]::Delete($part) }
        }
    }
    Assert-BridgeRegularPath $cab
    if ((Get-Item -LiteralPath $cab).Length -ne $payload.size -or (Get-BridgeHash $cab) -ne $payload.sha256) { throw 'Cached runtime checksum mismatch.' }
    $staging = Join-Path $folder ([Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($staging) | Out-Null
    try {
        $expand = Join-Path $env:SystemRoot 'System32\expand.exe'
        & $expand '-F:*' $cab $staging | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Windows could not extract the verified Microsoft cabinet.' }
        foreach ($file in $payload.files) {
            $source = Join-Path $staging $file.member
            Assert-BridgeRegularPath $source
            if ((Get-Item -LiteralPath $source).Length -ne $file.size -or (Get-BridgeHash $source) -ne $file.sha256 -or
                (Get-BridgePe $source).Architecture -ne $Architecture) { throw 'Extracted runtime verification failed.' }
            $destination = Join-Path $folder $file.name
            if (Test-Path -LiteralPath $destination) { Assert-BridgeRegularPath $destination }
            Copy-BridgeAtomic $source $destination
        }
    } finally { Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue }
    return $folder
}

function Resolve-BridgeReceiptPath([string]$Root, [string]$Relative, $Catalog) {
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)|:') { throw 'Invalid repair receipt path.' }
    $path = [IO.Path]::GetFullPath((Join-Path $Root $Relative))
    if (-not $path.StartsWith($Root.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Repair receipt escapes the game folder.' }
    $name = [IO.Path]::GetFileName($path)
    if ($name -notin @($Catalog.payloads.x86.files.name)) { throw 'Repair receipt contains a non-runtime file.' }
    Assert-BridgeRegularPath ([IO.Path]::GetDirectoryName($path))
    if (Test-Path -LiteralPath $path) { Assert-BridgeRegularPath $path }
    return $path
}

function Undo-BridgeRuntime([string]$Root, $Catalog) {
    $rootPath = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)
    Assert-BridgeRegularPath $rootPath
    $backup = Join-Path $rootPath '.bridge81-runtime'
    $receiptPath = Join-Path $backup 'receipt.json'
    if (-not [IO.File]::Exists($receiptPath)) { throw 'No Bridge81 runtime repair receipt exists in this game folder.' }
    Assert-BridgeRegularPath $receiptPath
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($receipt.schema -ne 1 -or $receipt.version -ne $Catalog.version -or @($receipt.files).Count -gt 5289) { throw 'Unsupported repair receipt.' }
    $actions = @(); $seen = @{}
    foreach ($record in $receipt.files) {
        $path = Resolve-BridgeReceiptPath $rootPath $record.path $Catalog
        if ($seen.ContainsKey($path)) { throw 'Duplicate repair receipt path.' }
        $seen[$path] = $true
        if ($record.installedSha256 -notin (@($Catalog.payloads.x86.files.sha256) + @($Catalog.payloads.x64.files.sha256))) { throw 'Unrecognized installed runtime checksum in receipt.' }
        $original = $null
        if ($null -ne $record.originalSha256) {
            if ($record.originalSha256 -notmatch '^[0-9a-f]{64}$' -or $record.backup -notmatch '^\d{5}\.bak$') { throw 'Invalid original-file backup metadata.' }
            $original = Join-Path $backup $record.backup
            Assert-BridgeRegularPath $original
            if ((Get-BridgeHash $original) -ne $record.originalSha256) { throw 'Original-file backup checksum mismatch. Undo stopped before changing files.' }
        }
        $current = $null
        if ([IO.File]::Exists($path)) { $current = Get-BridgeHash $path }
        if ($null -ne $current -and $current -ne $record.installedSha256 -and $current -ne $record.originalSha256) {
            throw ('A runtime file changed after repair: ' + $record.path + '. Close the game and keep this file and its backup; Undo will not overwrite later changes.')
        }
        $actions += [pscustomobject]@{ Path = $path; Original = $original; Current = $current; Record = $record }
    }
    foreach ($action in $actions) {
        if ($null -ne $action.Original) {
            if ($action.Current -ne $action.Record.originalSha256) { Copy-BridgeAtomic $action.Original $action.Path }
        }
        elseif ($null -ne $action.Current) { [IO.File]::Delete($action.Path) }
    }
    foreach ($action in $actions) { if ($null -ne $action.Original) { [IO.File]::Delete($action.Original) } }
    [IO.File]::Delete($receiptPath)
    if (@(Get-ChildItem -LiteralPath $backup -Force).Count -eq 0) { [IO.Directory]::Delete($backup) }
    return 'Repair undone. Original runtime files restored; files added by Bridge81 removed.'
}

function Install-BridgeRuntime([string]$Executable, $Catalog, [string]$Cache, [scriptblock]$Progress = { param($Message) }, [string[]]$OfflineFolders = @()) {
    $game = Get-BridgeGameTargets $Executable
    $backup = Join-Path $game.Root '.bridge81-runtime'
    if (Test-Path -LiteralPath $backup) { throw 'A previous repair or backup exists. Use Undo first, then repair again if needed.' }
    $folders = @{}
    foreach ($target in $game.Targets) {
        if (-not $folders.ContainsKey($target.Architecture)) {
            $folders[$target.Architecture] = Get-BridgeRuntimeFiles $Catalog $target.Architecture $Cache $Progress $OfflineFolders
        }
    }
    & $Progress 'Checking the complete runtime set and preparing original-file backups...'
    $records = @(); $sources = @{}
    foreach ($target in $game.Targets) {
        foreach ($file in $Catalog.payloads.($target.Architecture).files) {
            $source = Join-Path $folders[$target.Architecture] $file.name
            Assert-BridgeRegularPath $source
            if ((Get-BridgeHash $source) -ne $file.sha256 -or (Get-BridgePe $source).Architecture -ne $target.Architecture) { throw 'Runtime cache verification failed before repair.' }
            $destination = Join-Path $target.Directory $file.name
            $existing = $null
            if (Test-Path -LiteralPath $destination) {
                Assert-BridgeRegularPath $destination
                $existing = Get-BridgeHash $destination
                if ($existing -eq $file.sha256) { continue }
            }
            $relative = $destination.Substring($game.Root.Length + 1)
            $backupName = $null
            if ($null -ne $existing) { $backupName = ('{0:D5}.bak' -f $records.Count) }
            $records += [pscustomobject]@{ path = $relative; installedSha256 = $file.sha256; originalSha256 = $existing; backup = $backupName }
            $sources[$relative] = $source
        }
    }
    if ($records.Count -eq 0) { return 'The complete matching runtime is already present. Launch the game normally to check for another error.' }
    [IO.Directory]::CreateDirectory($backup) | Out-Null
    $receiptPath = Join-Path $backup 'receipt.json'
    try {
        foreach ($record in $records) {
            if ($null -ne $record.backup) { [IO.File]::Copy((Join-Path $game.Root $record.path), (Join-Path $backup $record.backup), $false) }
        }
        $receipt = [pscustomobject]@{ schema = 1; version = $Catalog.version; files = $records }
        $preparedReceipt = Join-Path $backup 'receipt.tmp'
        $receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $preparedReceipt -Encoding UTF8
        [IO.File]::Move($preparedReceipt, $receiptPath)
        foreach ($record in $records) {
            $destination = Resolve-BridgeReceiptPath $game.Root $record.path $Catalog
            $current = $null
            if ([IO.File]::Exists($destination)) { $current = Get-BridgeHash $destination }
            if ($current -ne $record.originalSha256) { throw 'A destination changed while preparing the repair. Close the game and try again.' }
            Copy-BridgeAtomic $sources[$record.path] $destination
            if ((Get-BridgeHash $destination) -ne $record.installedSha256) { throw 'Runtime copy verification failed.' }
        }
    } catch {
        $failure = $_.Exception.Message
        if ([IO.File]::Exists($receiptPath)) {
            try { Undo-BridgeRuntime $game.Root $Catalog | Out-Null }
            catch { throw ($failure + ' Automatic rollback could not finish: ' + $_.Exception.Message + ' Keep .bridge81-runtime for recovery.') }
        } else {
            Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction SilentlyContinue
        }
        throw $failure
    }
    return ('Runtime added beside the launcher and ' + ($game.Targets.Count - 1) + ' engine folder(s). Launch the game normally. Use Undo to reverse this repair.')
}
