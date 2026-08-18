Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# for android

.\venv\Scripts\Activate.ps1


# Redirect Windows temp folders away from C: drive space limits
New-Item -ItemType Directory -Force -Path "D:\Temp" | Out-Null
$env:TEMP = "D:\Temp"
$env:TMP = "D:\Temp"

# Redirect Flutter & Gradle build caches to D:
$env:GRADLE_USER_HOME = "D:\flet_cache\.gradle"
$env:PUB_CACHE        = "D:\flet_cache\pub"
$env:FLET_CACHE_DIR   = "D:\flet_cache"

# Point Flutter directly to your Android SDK folder
$env:ANDROID_HOME     = "D:\Andriod\sdk"

# Set Flutter's Android SDK config
D:\flet_cache\flutter\3.44.8\bin\flutter.bat config --android-sdk "D:\Andriod\sdk"

# Accept all Android licenses (Press 'y' for each prompt)
D:\flet_cache\flutter\3.44.8\bin\flutter.bat doctor --android-licenses

# Kill any hidden Java daemons holding file locks
Stop-Process -Name "java" -Force -ErrorAction SilentlyContinue

# Nuke corrupted Gradle caches
Remove-Item -Recurse -Force "D:\flet_cache\.gradle" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\Users\Natha\.gradle" -ErrorAction SilentlyContinue

# Ensure virtual environment is active
.\venv\Scripts\Activate.ps1

# Run the build
flet build apk