# Démarrage automatique de l'agent de la Télécommande ESP32 (avec droits administrateur).
# Phase 15 : chien de garde. La tâche se relance chaque minute ; si l'agent tourne déjà, Windows ignore
# le lancement (IgnoreNew) ; s'il est mort, il repart en moins d'une minute.
# Pour arrêter l'agent pour de bon : Disable-ScheduledTask, puis Stop-ScheduledTask.
# À lancer UNE SEULE FOIS dans un PowerShell ouvert « en tant qu'administrateur » :
#   powershell -ExecutionPolicy Bypass -File tools\agent\installer_demarrage.ps1
# Pour supprimer : Unregister-ScheduledTask -TaskName "ESP32 Telecommande Agent" -Confirm:$false

$python = & py -c "import sys; print(sys.executable)"
$pythonw = Join-Path (Split-Path $python) "pythonw.exe"
$agent = Join-Path $PSScriptRoot "agent_pc.py"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$agent`" --service" -WorkingDirectory $PSScriptRoot
$declencheur = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$gardien = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)
$compte = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest -LogonType Interactive
$reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "ESP32 Telecommande Agent" -Action $action -Trigger @($declencheur, $gardien) `
    -Principal $compte -Settings $reglages -Force | Out-Null

Write-Host "Tâche « ESP32 Telecommande Agent » créée (pythonw : $pythonw)."
Write-Host "Elle démarrera à chaque ouverture de session. Pour la lancer tout de suite :"
Write-Host "  Start-ScheduledTask -TaskName 'ESP32 Telecommande Agent'"
