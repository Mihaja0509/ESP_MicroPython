# Autorise l'app du téléphone à joindre l'agent (port 8765), uniquement depuis :
#   - le réseau local (Wi-Fi de la maison)
#   - Tailscale (adresses 100.64.0.0/10)
# À lancer UNE SEULE FOIS dans un PowerShell ouvert « en tant qu'administrateur » :
#   powershell -ExecutionPolicy Bypass -File tools\agent\autoriser_app.ps1
# Pour supprimer : Remove-NetFirewallRule -DisplayName "ESP32 Telecommande App"

Remove-NetFirewallRule -DisplayName "ESP32 Telecommande App" -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName "ESP32 Telecommande App" -Direction Inbound -Protocol TCP `
    -LocalPort 8765 -Action Allow -Profile Any -RemoteAddress LocalSubnet, 100.64.0.0/10 | Out-Null
Write-Host "Pare-feu : port 8765 ouvert pour le réseau local et Tailscale."
