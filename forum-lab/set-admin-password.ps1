$ErrorActionPreference = 'Stop'

$compose = @('-f', 'compose.yaml', '-f', 'compose.forum.local.yaml')
$container = (& docker compose @compose ps -q forum_lab).Trim()
if ($LASTEXITCODE -ne 0 -or -not $container) {
    throw 'The local phpBB container is not running.'
}

$backupDirectory = Join-Path $env:LOCALAPPDATA ('dndtools\forum-backups\' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-before-password')
New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
& docker cp "${container}:/var/www/html/store/forum_lab.sqlite" (Join-Path $backupDirectory 'forum_lab.sqlite')
if ($LASTEXITCODE -ne 0) { throw 'Could not back up the forum database.' }

Write-Host 'Defina a nova senha de Ronassic para o fórum local (mínimo de 8 caracteres).'
while ($true) {
    $first = Read-Host 'Nova senha' -AsSecureString
    $second = Read-Host 'Repita a senha' -AsSecureString
    $firstPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($first)
    $secondPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($second)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($firstPtr)
        $repeated = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secondPtr)
        if ($plain -cne $repeated) {
            Write-Warning 'As senhas não coincidem. Tente novamente.'
            continue
        }
        if ([Text.Encoding]::UTF8.GetByteCount($plain) -lt 8 -or [Text.Encoding]::UTF8.GetByteCount($plain) -gt 128) {
            Write-Warning 'Use uma senha de pelo menos 8 caracteres. Tente novamente.'
            continue
        }

        & docker cp 'forum-lab/set-admin-password.php' "${container}:/tmp/dndtools-set-admin-password.php"
        if ($LASTEXITCODE -ne 0) { throw 'Could not copy the password helper into phpBB.' }
        try {
            $plain | & docker exec -i $container php /tmp/dndtools-set-admin-password.php
            if ($LASTEXITCODE -ne 0) { throw 'phpBB rejected the password update.' }
        }
        finally {
            & docker exec $container rm -f /tmp/dndtools-set-admin-password.php | Out-Null
        }
        break
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($firstPtr)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secondPtr)
        $plain = $null
        $repeated = $null
        $first.Dispose()
        $second.Dispose()
    }
}
Write-Host 'Senha atualizada no fórum local. O backup anterior está em pasta privada.'
