@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ================================================================
echo           VIETNAM MOTORBIKE SMART TRAFFIC ASSISTANT
echo          Khoi dong Ung dung Toan trinh [1-Click Run]
echo ================================================================
echo.

REM 1. Tu dong tao file .env tu .env.example kem sinh Secret an toan neu chua co
if not exist .env (
    if exist .env.example (
        echo [INFO] Chua tim thay .env, dang tao tu .env.example...
        copy .env.example .env >nul
        for /f "delims=" %%i in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((New-Guid).ToString() + (New-Guid).ToString()))"') do set RANDOM_KEY=%%i
        powershell -Command "(Get-Content .env) -replace 'SECRET_KEY=.*', ('SECRET_KEY=' + $env:RANDOM_KEY) | Set-Content .env"
        echo [OK] Da tao .env kem sinh ngau nhien SECRET_KEY bao mat.
    ) else (
        echo [CANH BAO] Khong tim thay .env.example.
    )
)

REM 2. Kiem tra Docker Engine
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set RUN_MODE=docker
    echo [OK] Docker Engine da san sang. Che do: Docker Container.
) else (
    set RUN_MODE=local
    echo [THONG BAO] Docker Desktop chua bat. He thong se chay truc tiep bang Python cuc bo.
)

REM 3. Xu ly cac tham so tuy chon [stop / logs / test]
if "%1"=="test" (
    echo [INFO] Dang chay bo kiem thu TDD Pytest...
    pytest --cov=backend/src tests/
    exit /b 0
)

if "%1"=="stop" (
    if "!RUN_MODE!"=="docker" (
        echo [INFO] Dang dung Docker containers...
        docker compose down
    ) else (
        echo [INFO] Dung tien trinh Python Uvicorn...
        taskkill /F /IM python.exe /T >nul 2>&1
    )
    echo [OK] Da dung he thong.
    exit /b 0
)

REM 4. Khoi dong theo che do phu hop
if "!RUN_MODE!"=="docker" (
    echo [INFO] Dang build va khoi dong he thong bang Docker Compose...
    docker compose up -d --build
    if %ERRORLEVEL% NEQ 0 (
        echo [LOI] Docker Compose gap su co. Chuyen sang che do Python cuc bo...
        set RUN_MODE=local
    )
)

if "!RUN_MODE!"=="local" (
    echo [INFO] Dang cai dat/kiem tra cac goi phu thuoc can thiet...
    pip install -q fastapi uvicorn httpx pydantic python-dotenv pytest pytest-cov
    echo [INFO] Dang khoi dong Uvicorn Web Server tai cong 8000...
    start "Traffic Assistant Web Server" python -m uvicorn backend.src.presentation.main:app --host 0.0.0.0 --port 8000
    timeout /t 3 /nobreak >nul
)

echo.
echo ================================================================
echo          HE THONG TRAFFIC ASSISTANT DA KHOI DONG THANH CONG!
echo ================================================================
echo.
echo  Giao dien nguoi dung [PWA va HUD Mode]:  http://localhost:8000
echo  Trang Quan Tri Huan Luyen AI:            http://localhost:8000/training.html
echo  Tai lieu Backend API [Swagger UI]:       http://localhost:8000/docs
echo  Cong kiem tra Health Check API:          http://localhost:8000/api/v1/health
echo.
echo  LENH TIEN ICH BO TRO:
echo     - Chay kiem thu TDD:      run.bat test
echo     - Dung toan bo he thong:  run.bat stop
echo ================================================================
echo.

set /p OPEN_BROWSER="Ban co muon mo ngay giao dien tren trinh duyet khong? [Y/N, Mac dinh: Y]: "
if "%OPEN_BROWSER%"=="" set OPEN_BROWSER=Y
if /i "%OPEN_BROWSER%"=="Y" (
    start http://localhost:8000
)

echo.
echo Nhan phim bat ky de dong cua so nay...
pause >nul
