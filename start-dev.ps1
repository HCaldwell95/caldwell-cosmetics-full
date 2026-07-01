Write-Host ""
Write-Host "Starting Caldwell Cosmetics Dev Environment..." -ForegroundColor Green
Write-Host ""

.\venv\Scripts\Activate.ps1

$env:DJANGO_SETTINGS_MODULE = "config.settings.dev"

python manage.py runserver