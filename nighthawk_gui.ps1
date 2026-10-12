Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$logsDir = Join-Path $projectDir "logs"
if (!(Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$backendLog = Join-Path $logsDir "backend.log"
$frontendLog = Join-Path $logsDir "frontend.log"

# Main Form
$form = New-Object System.Windows.Forms.Form
$form.Text = "NightHawk AI — Operations Control Center"
$form.Size = New-Object System.Drawing.Size(650, 680)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42) # Slate 900
$form.ForeColor = [System.Drawing.Color]::White
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

# Title Label
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "🦅 NIGHTHAWK AI — CONTROL PANEL"
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(56, 189, 248) # Cyan 400
$titleLabel.Size = New-Object System.Drawing.Size(600, 35)
$titleLabel.Location = New-Object System.Drawing.Point(25, 20)
$form.Controls.Add($titleLabel)

# Subtitle
$subLabel = New-Object System.Windows.Forms.Label
$subLabel.Text = "Autonomous Cybersecurity, Linux C2 & Multi-Container Engine"
$subLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Regular)
$subLabel.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184) # Slate 400
$subLabel.Size = New-Object System.Drawing.Size(600, 20)
$subLabel.Location = New-Object System.Drawing.Point(25, 55)
$form.Controls.Add($subLabel)

# Status Group Box
$statusGroup = New-Object System.Windows.Forms.GroupBox
$statusGroup.Text = " System Status "
$statusGroup.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$statusGroup.ForeColor = [System.Drawing.Color]::FromArgb(203, 213, 225)
$statusGroup.Size = New-Object System.Drawing.Size(580, 80)
$statusGroup.Location = New-Object System.Drawing.Point(25, 85)

$backendStatus = New-Object System.Windows.Forms.Label
$backendStatus.Text = "Backend API (:8000): Checking..."
$backendStatus.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)
$backendStatus.ForeColor = [System.Drawing.Color]::FromArgb(251, 146, 60)
$backendStatus.Size = New-Object System.Drawing.Size(260, 30)
$backendStatus.Location = New-Object System.Drawing.Point(20, 30)
$statusGroup.Controls.Add($backendStatus)

$frontendStatus = New-Object System.Windows.Forms.Label
$frontendStatus.Text = "Frontend UI (:3000): Checking..."
$frontendStatus.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)
$frontendStatus.ForeColor = [System.Drawing.Color]::FromArgb(251, 146, 60)
$frontendStatus.Size = New-Object System.Drawing.Size(260, 30)
$frontendStatus.Location = New-Object System.Drawing.Point(300, 30)
$statusGroup.Controls.Add($frontendStatus)

$form.Controls.Add($statusGroup)

# Function to check status
function Update-ServiceStatus {
    $bOnline = $false
    $fOnline = $false
    try {
        $tcpB = New-Object System.Net.Sockets.TcpClient
        $tcpB.Connect("127.0.0.1", 8000)
        $bOnline = $true
        $tcpB.Close()
    } catch {}

    try {
        $tcpF = New-Object System.Net.Sockets.TcpClient
        $tcpF.Connect("127.0.0.1", 3000)
        $fOnline = $true
        $tcpF.Close()
    } catch {}

    if ($bOnline) {
        $backendStatus.Text = "Backend API (:8000): ONLINE"
        $backendStatus.ForeColor = [System.Drawing.Color]::FromArgb(74, 222, 128) # Green
    } else {
        $backendStatus.Text = "Backend API (:8000): OFFLINE"
        $backendStatus.ForeColor = [System.Drawing.Color]::FromArgb(248, 113, 113) # Red
    }

    if ($fOnline) {
        $frontendStatus.Text = "Frontend UI (:3000): ONLINE"
        $frontendStatus.ForeColor = [System.Drawing.Color]::FromArgb(74, 222, 128) # Green
    } else {
        $frontendStatus.Text = "Frontend UI (:3000): OFFLINE"
        $frontendStatus.ForeColor = [System.Drawing.Color]::FromArgb(248, 113, 113) # Red
    }
}

# Log Console Box
$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.BackColor = [System.Drawing.Color]::FromArgb(2, 6, 23)
$logBox.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$logBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$logBox.Size = New-Object System.Drawing.Size(580, 240)
$logBox.Location = New-Object System.Drawing.Point(25, 180)
$form.Controls.Add($logBox)

function Write-GuiLog($msg) {
    $time = (Get-Date).ToString("HH:mm:ss")
    $logBox.AppendText("[$time] $msg`r`n")
    $logBox.SelectionStart = $logBox.Text.Length
    $logBox.ScrollToCaret()
}

# Button Helper
function Create-Btn($text, $x, $y, $w, $h, $bg) {
    $btn = New-Object System.Windows.Forms.Button
    $btn.Text = $text
    $btn.Size = New-Object System.Drawing.Size($w, $h)
    $btn.Location = New-Object System.Drawing.Point($x, $y)
    $btn.BackColor = $bg
    $btn.ForeColor = [System.Drawing.Color]::White
    $btn.FlatStyle = "Flat"
    $btn.FlatAppearance.BorderSize = 0
    $btn.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
    $btn.Cursor = [System.Windows.Forms.Cursors]::Hand
    $form.Controls.Add($btn)
    return $btn
}

# Buttons Layout
$btnStart = Create-Btn "▶  Start All" 25 440 180 42 ([System.Drawing.Color]::FromArgb(22, 163, 74)) # Green
$btnStop = Create-Btn "⏹  Stop All" 225 440 180 42 ([System.Drawing.Color]::FromArgb(220, 38, 38)) # Red
$btnRestart = Create-Btn "🔄  Restart All" 425 440 180 42 ([System.Drawing.Color]::FromArgb(202, 138, 4)) # Yellow

$btnLogB = Create-Btn "📜  Backend Logs" 25 495 180 38 ([System.Drawing.Color]::FromArgb(30, 41, 59))
$btnLogF = Create-Btn "📜  Frontend Logs" 225 495 180 38 ([System.Drawing.Color]::FromArgb(30, 41, 59))
$btnAgent = Create-Btn "⚡  Linux Agent" 425 495 180 38 ([System.Drawing.Color]::FromArgb(147, 51, 234)) # Purple

$btnOpen = Create-Btn "🌐  Open Web Dashboard (http://localhost:3000)" 25 545 380 40 ([System.Drawing.Color]::FromArgb(2, 132, 199)) # Blue
$btnRefresh = Create-Btn "⟳ Refresh" 425 545 180 40 ([System.Drawing.Color]::FromArgb(71, 85, 105))

# Action: Start All
$btnStart.Add_Click({
    Write-GuiLog "Starting NightHawk AI Services..."
    
    # 1. Start Backend
    $venvPy = Join-Path $projectDir "backend\.venv\Scripts\python.exe"
    $backendDir = Join-Path $projectDir "backend"
    
    $procB = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    if (-not $procB) {
        Write-GuiLog "Launching FastAPI Backend on port 8000..."
        Start-Process -FilePath $venvPy -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" `
            -WorkingDirectory $backendDir `
            -RedirectStandardOutput $backendLog `
            -RedirectStandardError (Join-Path $logsDir "backend_err.log") `
            -WindowStyle Hidden
    } else {
        Write-GuiLog "Backend is already running on port 8000."
    }

    # 2. Start Frontend
    $frontendDir = Join-Path $projectDir "frontend"
    $procF = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess
    if (-not $procF) {
        Write-GuiLog "Launching React Frontend on port 3000..."
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --host 127.0.0.1 --port 3000" `
            -WorkingDirectory $frontendDir `
            -RedirectStandardOutput $frontendLog `
            -RedirectStandardError (Join-Path $logsDir "frontend_err.log") `
            -WindowStyle Hidden
    } else {
        Write-GuiLog "Frontend is already running on port 3000."
    }

    Start-Sleep -Seconds 2
    Update-ServiceStatus
    Write-GuiLog "Start sequence executed."
})

# Action: Stop All
$btnStop.Add_Click({
    Write-GuiLog "Stopping NightHawk AI Services..."
    
    $p8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($p8000) {
        foreach ($pidToKill in $p8000) {
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Write-GuiLog "Stopped Backend Process (PID $pidToKill)."
        }
    }

    $p3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($p3000) {
        foreach ($pidToKill in $p3000) {
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            Write-GuiLog "Stopped Frontend Process (PID $pidToKill)."
        }
    }

    Start-Sleep -Seconds 1
    Update-ServiceStatus
    Write-GuiLog "All services stopped."
})

# Action: Restart All
$btnRestart.Add_Click({
    Write-GuiLog "Restarting all services..."
    $btnStop.PerformClick()
    Start-Sleep -Seconds 2
    $btnStart.PerformClick()
})

# Action: Backend Logs
$btnLogB.Add_Click({
    if (Test-Path $backendLog) {
        $content = Get-Content $backendLog -Tail 25
        Write-GuiLog "=== RECENT BACKEND LOGS ==="
        foreach ($line in $content) { Write-GuiLog $line }
    } else {
        Write-GuiLog "Backend log file not found yet."
    }
})

# Action: Frontend Logs
$btnLogF.Add_Click({
    if (Test-Path $frontendLog) {
        $content = Get-Content $frontendLog -Tail 25
        Write-GuiLog "=== RECENT FRONTEND LOGS ==="
        foreach ($line in $content) { Write-GuiLog $line }
    } else {
        Write-GuiLog "Frontend log file not found yet."
    }
})

# Action: Linux Agent Test
$btnAgent.Add_Click({
    Write-GuiLog "Opening Autonomous Linux Agent in interactive window..."
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k python nighthawk_linux_agent.py" -WorkingDirectory $projectDir
})

# Action: Open Browser
$btnOpen.Add_Click({
    Start-Process "http://localhost:3000"
    Write-GuiLog "Opened dashboard in default browser."
})

# Action: Refresh Status
$btnRefresh.Add_Click({
    Update-ServiceStatus
    Write-GuiLog "Refreshed status."
})

# Timer for periodic status updates
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 3000
$timer.Add_Tick({ Update-ServiceStatus })
$timer.Start()

# Initial Load
Write-GuiLog "NightHawk AI Control Center Initialized."
Update-ServiceStatus

$form.Add_Shown({ $form.Activate() })
[void]$form.ShowDialog()
