# Generate a Tauri updater signing key pair.
# Requires the project dependencies (`npm ci`) and the Tauri CLI.

$password = Read-Host -Prompt "Enter a password for the private key (min 8 chars)" -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$plainPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

if ($plainPassword.Length -lt 8) {
    Write-Error "Password must be at least 8 characters."
    exit 1
}

$projectDir = Split-Path -Parent $PSScriptRoot
Push-Location $projectDir

try {
    & npx tauri signer generate --password $plainPassword --ci
    if ($LASTEXITCODE -ne 0) {
        throw "Tauri signer failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Add the generated private key and password to these GitHub Actions secrets:" -ForegroundColor Green
    Write-Host "  TAURI_SIGNING_PRIVATE_KEY"
    Write-Host "  TAURI_SIGNING_PRIVATE_KEY_PASSWORD"
    Write-Host "Paste the public key into src-tauri/tauri.conf.json (plugins.updater.pubkey)."
    Write-Host "CI will publish signed bundles and latest.json on the next release."
} finally {
    $plainPassword = $null
    Pop-Location
}
