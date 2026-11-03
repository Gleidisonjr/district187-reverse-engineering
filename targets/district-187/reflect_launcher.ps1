$exePath = Resolve-Path "targets\district-187\client-rebirth\S2Launcher.exe"
$bytes = [System.IO.File]::ReadAllBytes($exePath)
$asm = [System.Reflection.Assembly]::Load($bytes)
Write-Host "Assembly Name:" $asm.FullName
$types = $asm.GetTypes()
foreach ($t in $types) {
    Write-Host "Type:" $t.FullName
    foreach ($m in $t.GetMethods([System.Reflection.BindingFlags]"Public,NonPublic,Instance,Static,DeclaredOnly")) {
        Write-Host "  Method:" $m.ToString()
    }
}
