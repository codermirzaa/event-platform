# EventHub — Local Event & Ticket Platform

## Phase 1: Auth & RBAC — Setup Guide

---

## 1. Tələblər

- Python 3.10+
- MySQL 8.0+
- pip

---

## 2. Quraşdırma

### 2.1 Virtual environment yarat

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2.2 Paketləri yüklə

```bash
pip install -r requirements.txt
```

### 2.3 MySQL verilənlər bazasını yarat

MySQL-ə qoşul və aşağıdakı əmri icra et:

```sql
CREATE DATABASE event_platform_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2.4 settings.py-də database məlumatlarını yenilə

`event_platform/settings.py` faylında:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'event_platform_db',
        'USER': 'root',           # <-- öz MySQL istifadəçin
        'PASSWORD': 'yourpassword',  # <-- öz şifrən
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 2.5 Migrasiyaları icra et

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### 2.6 Superuser (Admin) yarat

```bash
python manage.py createsuperuser
```
> Qeyd: Superuser-in rolu avtomatik olaraq admin kimi işləyir.

### 2.7 Serveri başlat

```bash
python manage.py runserver
```

Brauzerda aç: **http://127.0.0.1:8000**

---

## 3. Layihə strukturu

```
event_platform/
├── manage.py
├── requirements.txt
├── event_platform/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/              ← Phase 1 (Auth & RBAC)
│   ├── models.py          ← CustomUser (role field)
│   ├── views.py           ← register, login, logout, dashboard, profile
│   ├── forms.py           ← RegisterForm, LoginForm, ProfileUpdateForm
│   ├── urls.py            ← /accounts/...
│   ├── decorators.py      ← @organizer_required, @admin_required, mixins
│   └── admin.py           ← Django admin config
├── templates/
│   ├── base.html          ← Navbar, Bootstrap 5
│   ├── 403.html
│   └── accounts/
│       ├── register.html
│       ├── login.html
│       ├── profile.html
│       ├── dashboard_attendee.html
│       ├── dashboard_organizer.html
│       └── dashboard_admin.html
└── static/
```

---

## 4. URL-lər

| URL | Təsvir |
|-----|--------|
| `/accounts/register/` | Qeydiyyat |
| `/accounts/login/` | Daxil ol |
| `/accounts/logout/` | Çıx |
| `/accounts/dashboard/` | Role-based dashboard |
| `/accounts/profile/` | Profil redaktəsi |
| `/admin/` | Django admin paneli |

---

## 5. Rollar

| Rol | Qeydiyyatda seçilir? | İcazələr |
|-----|---------------------|----------|
| Attendee | ✅ (default) | Tədbirə bax, bilet al |
| Organizer | ✅ | Tədbir yarat, idarə et |
| Admin | ❌ (createsuperuser ilə) | Hər şey |

---

## 6. RBAC istifadəsi (developer üçün)

```python
# Function-based view
from accounts.decorators import organizer_required, admin_required

@organizer_required
def create_event(request):
    ...

@admin_required
def admin_panel(request):
    ...

# Class-based view
from accounts.decorators import OrganizerRequiredMixin

class CreateEventView(OrganizerRequiredMixin, CreateView):
    ...
```

---

## 7. Növbəti mərhələ — Phase 2 (deadline: 4 May)

- [ ] F-03: Event Creation & Management
- [ ] F-04: Event Discovery & Search
- [ ] F-05: Ticket Booking System
- [ ] F-06: Attendee & Organizer Dashboards (tam)
- [ ] F-07: Admin Moderation Panel
