# Windows PowerShell 4.0 / .NET 4.5.1 compatible. No PowerShell Gallery modules.
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $env:LOCALAPPDATA 'Bridge81\Python312'
$python = Join-Path $runtime 'python.exe'
$downloadUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
# SHA-256 from Python.org's release Sigstore bundle messageSignature.messageDigest.
$expectedHash = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb'
$temporary = $null
try {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'Automatic setup is for x64 Windows only. Use the official 32-bit traditional Python installer manually; current Cygwin needs x64 Windows.'
    }
    if (Test-Path -LiteralPath $python -PathType Leaf) {
        & $python -I -c 'import sys, tkinter; sys.exit(sys.version_info < (3,10))'
        if ($LASTEXITCODE -ne 0) { throw 'The existing Bridge81 runtime needs repair. It has not been overwritten.' }
        Write-Host 'A working Bridge81 runtime is already installed.'
        exit 0
    }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('Bridge81-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporary | Out-Null
    $installer = Join-Path $temporary 'python-3.12.10-amd64.exe'
    Write-Host 'Downloading the traditional Python.org x64 installer (about 26 MB)...'
    $client = New-Object Net.WebClient
    try { $client.DownloadFile($downloadUrl, $installer) } finally { $client.Dispose() }
    $actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $expectedHash) { throw 'SHA-256 mismatch. The download will not be executed.' }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate -or $signature.SignerCertificate.Subject -notlike '*Python Software Foundation*') {
        throw 'Windows could not verify the Python Software Foundation signature. Check Windows certificate updates, date and time, or use the official Python.org manual setup. Verification has not been disabled.'
    }
    Write-Host ('Verified. Installing for your user in ' + $runtime)
    $installerArgs = @('/passive', 'InstallAllUsers=0', ('TargetDir="{0}"' -f $runtime), 'Include_launcher=0', 'AssociateFiles=0', 'Shortcuts=0', 'PrependPath=0', 'AppendPath=0', 'Include_test=0', 'Include_doc=0', 'Include_tcltk=1', 'Include_pip=1')
    $result = Start-Process -FilePath $installer -ArgumentList $installerArgs -Wait -PassThru
    if ($result.ExitCode -ne 0 -and $result.ExitCode -ne 3010) { throw ('Python installer returned ' + $result.ExitCode + '. If Python 3.12 is already installed, use or modify that installation instead.') }
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'The installer did not create the private runtime. Use your existing traditional Python 3.12 installation with Start-Bridge81.cmd.' }
    & $python -I -c 'import sys, tkinter, venv; print("Python and Tcl/Tk are ready.")'
    if ($LASTEXITCODE -ne 0) { throw 'The installed runtime could not pass its startup check.' }
    if ($result.ExitCode -eq 3010) { Write-Host 'Windows reports that a restart is needed to finish Python setup.' }
} catch {
    Write-Host ('Setup stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if ($temporary -and (Test-Path -LiteralPath $temporary)) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}
