@echo off
title Cho Restaurant - Developer 1 Foundation Server
cd /d "%~dp0"

echo ============================================================================
echo   Cho Restaurant - Ordering ^& Delivery Management System
echo   Role: Developer 1 (Backend Infrastructure, Auth, Roles, Database ^& Menu)
echo ============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
    echo Installing requirements...
    ".venv\Scripts\pip.exe" install -r requirements.txt
) else (
    echo [1/4] Virtual environment detected ^(.venv^).
)

echo.
echo [2/4] Applying database migrations...
".venv\Scripts\python.exe" manage.py migrate

echo.
echo [3/4] Seeding Developer 1 foundation data ^(Roles, Profiles, Addresses, Menu^)...
".venv\Scripts\python.exe" manage.py seed_dev1_data

echo.
echo ============================================================================
echo   Demo Accounts ^(Seeded^):
echo     ADMIN    : admin_cho     / AdminPass123!
echo     STAFF    : staff_ama     / StaffPass123!
echo     RIDER    : rider_kofi    / RiderPass123!
echo     CUSTOMER : customer_akua / CustomerPass123!
echo.
echo   Key URLs:
echo     Foundation Portal : http://127.0.0.1:8000/
echo     Django Admin      : http://127.0.0.1:8000/admin/
echo     REST API Root     : http://127.0.0.1:8000/api/
echo     Menu Catalog      : http://127.0.0.1:8000/menu/
echo ============================================================================
echo.
echo [4/4] Launching browser and starting Django server at http://127.0.0.1:8000/ ...
start "" "http://127.0.0.1:8000/"
".venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000

pause
