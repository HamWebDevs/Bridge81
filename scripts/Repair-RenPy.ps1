# A Python-free repair UI for Windows PowerShell 4.0 and Windows 8.1.
param([switch]$SmokeTest)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'RuntimeRepair.ps1')
    $catalog = Get-BridgeCatalog (Join-Path $PSScriptRoot 'ucrt-manifest.json')
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    [Windows.Forms.Application]::EnableVisualStyles()
    $form = New-Object Windows.Forms.Form
    $form.Text = 'Bridge81 - Ren''Py runtime repair'
    $form.ClientSize = New-Object Drawing.Size(720, 470)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = 'FixedDialog'
    $form.MaximizeBox = $false
    $form.Font = New-Object Drawing.Font('Segoe UI', 12)
    $form.BackColor = [Drawing.Color]::FromArgb(16, 27, 43)
    $form.ForeColor = [Drawing.Color]::FromArgb(230, 237, 245)
    $heading = New-Object Windows.Forms.Label
    $heading.Text = 'Fix missing Microsoft runtime DLLs'
    $heading.Font = New-Object Drawing.Font('Segoe UI', 20, [Drawing.FontStyle]::Bold)
    $heading.SetBounds(24, 20, 675, 45)
    $form.Controls.Add($heading)
    $description = New-Object Windows.Forms.Label
    $description.Text = "For api-ms-win-crt-heap-l1-1-0.dll and related UCRT errors.`r`nClose the game, then choose its main EXE in the extracted game folder."
    $description.SetBounds(26, 76, 670, 65)
    $form.Controls.Add($description)
    $path = New-Object Windows.Forms.TextBox
    $path.ReadOnly = $true
    $path.SetBounds(26, 151, 526, 32)
    $form.Controls.Add($path)
    $browse = New-Object Windows.Forms.Button
    $browse.Text = 'Choose game'
    $browse.SetBounds(564, 147, 130, 38)
    $form.Controls.Add($browse)
    $explanation = New-Object Windows.Forms.Label
    $explanation.Text = "Repair downloads Microsoft's verified runtime (less than 1 MB per architecture) and places the complete matching set beside your game's executables. Existing runtime files are backed up for Undo. No Python or administrator access is needed."
    $explanation.SetBounds(26, 204, 668, 96)
    $form.Controls.Add($explanation)
    $repair = New-Object Windows.Forms.Button
    $repair.Text = 'Repair runtime'
    $repair.SetBounds(26, 310, 205, 46)
    $repair.Enabled = $false
    $form.Controls.Add($repair)
    $undo = New-Object Windows.Forms.Button
    $undo.Text = 'Undo repair'
    $undo.SetBounds(246, 310, 170, 46)
    $undo.Enabled = $false
    $form.Controls.Add($undo)
    $copy = New-Object Windows.Forms.Button
    $copy.Text = 'Copy result'
    $copy.SetBounds(432, 310, 150, 46)
    $form.Controls.Add($copy)
    $status = New-Object Windows.Forms.Label
    $status.Text = 'Ready. Choose the game that shows the missing runtime error.'
    $status.SetBounds(26, 375, 668, 76)
    $form.Controls.Add($status)
    $script:repairBusy = $false
    $copy.add_Click({ if ($status.Text) { [Windows.Forms.Clipboard]::SetText($status.Text) } })
    $form.add_FormClosing({ param($sender, $event) if ($script:repairBusy) { $event.Cancel = $true } })
    $browse.add_Click({
        $picker = New-Object Windows.Forms.OpenFileDialog
        $picker.Title = 'Choose the main game EXE beside the game and renpy folders'
        $picker.Filter = 'Windows game executable (*.exe)|*.exe'
        if ($picker.ShowDialog($form) -eq 'OK') {
            $path.Text = $picker.FileName
            $repair.Enabled = $true
            $undo.Enabled = $true
            $status.Text = 'Selected. Close this game before repairing or undoing.'
        }
        $picker.Dispose()
    })
    $progress = { param($message) $status.Text = $message; $status.Refresh(); [Windows.Forms.Application]::DoEvents() }
    $action = {
        param([bool]$UndoRequested)
        $script:repairBusy = $true
        $browse.Enabled = $false; $repair.Enabled = $false; $undo.Enabled = $false
        try {
            if ($UndoRequested) {
                $status.Text = Undo-BridgeRuntime ([IO.Path]::GetDirectoryName($path.Text)) $catalog
            } else {
                $cache = Join-Path $env:LOCALAPPDATA 'Bridge81\RuntimeCache'
                $offline = @((Join-Path (Split-Path $PSScriptRoot -Parent) 'runtime-downloads'), (Join-Path $env:USERPROFILE 'Downloads'))
                $status.Text = Install-BridgeRuntime $path.Text $catalog $cache $progress $offline
            }
            [Windows.Forms.MessageBox]::Show($form, ($status.Text + "`r`n`r`nThis fixes missing UCRT files. Other OS, graphics or game errors can still need a separate fix."), 'Bridge81', 'OK', 'Information') | Out-Null
        } catch {
            $status.Text = 'Stopped: ' + $_.Exception.Message
            [Windows.Forms.MessageBox]::Show($form, $status.Text, 'Bridge81 repair', 'OK', 'Warning') | Out-Null
        } finally {
            $script:repairBusy = $false
            $browse.Enabled = $true; $repair.Enabled = $true; $undo.Enabled = $true
        }
    }
    $repair.add_Click({ & $action $false })
    $undo.add_Click({ & $action $true })
    if ($SmokeTest) {
        $form.Show()
        [Windows.Forms.Application]::DoEvents()
        if ($form.Controls.Count -ne 9 -or $repair.Enabled) { throw 'Repair UI smoke check failed.' }
        $form.Close()
        Write-Host 'Python-free repair UI smoke passed.'
    } else { [Windows.Forms.Application]::Run($form) }
    $form.Dispose()
} catch {
    Write-Host ('Bridge81 repair stopped: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
