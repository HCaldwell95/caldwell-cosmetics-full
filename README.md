cd caldwell-cosmetics
.\venv\Scripts\Activate.ps1

or

.\start-dev.ps1

How to run dev settings:

$env:DJANGO_SETTINGS_MODULE="config.settings.dev"
python manage.py runserver

DJANGO_SETTINGS_MODULE=config.settings.prod

Template Structure:

templates/
├─ base/
│ ├─ base.html <-- main template
│ ├─ \_navbar.html <-- navbar only
│ ├─ \_footer.html <-- footer only
│ ├─ \_modals.html <-- all modal popups
├─ core/
│ └─ home.html
│ └─ cookies.html
│ └─ dashboard.html
│ └─ privacy.html
│ └─ terms.html
├─ treatments/
├─ bookings/
├─ accounts/

Static Structure:

static/
├─ css/
│ ├─ style.css
│ ├─ navbar.css
│ ├─ footer.css
│ └─ bootstrap.min.css
├─ js/
│ ├─ script.js
│ ├─ calendar.js
│ └─ bootstrap.bundle.min.js
├─ images/
├─ favicon/
