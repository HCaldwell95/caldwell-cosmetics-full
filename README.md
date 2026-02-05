cd caldwell-cosmetics
.\venv\Scripts\Activate.ps1

or

.\caldwell-cosmetics\venv\Scripts\Activate.ps1

How to run dev settings:

$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
python manage.py runserver

DJANGO_SETTINGS_MODULE=config.settings.prod
