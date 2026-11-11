"""
URL configuration for furniture_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from accounts.views import admin_login_redirect
from furnitureapp import views

urlpatterns = [
    # The admin signs in through the account sign-in (rate limits, lockout, 2FA).
    path('admin/login/', admin_login_redirect),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', views.home, name='home'),
    path('collection/', views.collection, name='collection'),
    path('living-room/', views.room_page, {'room': 'living-room'}, name='living_room'),
    path('bedroom/', views.room_page, {'room': 'bedroom'}, name='bedroom'),
    path('dining-room/', views.room_page, {'room': 'dining-room'}, name='dining_room'),
    path('office/', views.room_page, {'room': 'office'}, name='office'),
    path('outdoor/', views.room_page, {'room': 'outdoor'}, name='outdoor'),
    path('search/', views.search, name='search'),
]
