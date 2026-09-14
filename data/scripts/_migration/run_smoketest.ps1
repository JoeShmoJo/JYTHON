# Runs smoketest_imports.py under ResSim's own Jython, with ResSim's jars on the
# classpath. Does NOT open a watershed and does NOT compute anything.
#
#   .\run_smoketest.ps1 -Install "C:\Program Files\HEC\HEC-ResSim\4.1"
#
# Compare versions by running it once against each install.

param(
    [Parameter(Mandatory=$true)][string]$Install
)

if (-not (Test-Path $Install)) {
    Write-Error "No such directory: $Install"
    exit 1
}

# Wildcard classpath entries are expanded by Java itself, so this survives a
# change in how the jars are laid out between versions.
$jarDirs = Get-ChildItem -Path $Install -Recurse -Filter *.jar |
    ForEach-Object { $_.DirectoryName } | Sort-Object -Unique
if ($jarDirs.Count -eq 0) {
    Write-Error "No .jar files found under $Install"
    exit 1
}
$classPath = ($jarDirs | ForEach-Object { Join-Path $_ '*' }) -join ';'
Write-Host "Found jars in $($jarDirs.Count) directory(ies) under $Install"

# Prefer the JRE shipped with ResSim, so the test uses the Java it really runs on
$java = Get-ChildItem -Path $Install -Recurse -Filter java.exe -ErrorAction SilentlyContinue |
    Select-Object -First 1
if ($java) {
    $javaExe = $java.FullName
    Write-Host "Using bundled Java: $javaExe"
} else {
    $javaExe = 'java'
    Write-Host "No bundled java.exe found, using java from PATH"
}

$nativeDir = Get-ChildItem -Path $Install -Recurse -Include *.dll -ErrorAction SilentlyContinue |
    Select-Object -First 1
$libPath = if ($nativeDir) { $nativeDir.DirectoryName } else { $Install }

$script = Join-Path $PSScriptRoot 'smoketest_imports.py'

& $javaExe "-Djava.library.path=$libPath" -cp $classPath org.python.util.jython $script
