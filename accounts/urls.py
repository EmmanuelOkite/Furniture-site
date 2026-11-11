from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Registration
    path("register/", views.register, name="register"),
    # Sign in / out
    path("login/", views.login_view, name="login"),
    path("login/two-factor/", views.login_two_factor, name="login_two_factor"),
    path("logout/", views.logout_view, name="logout"),
    # Passwords
    path("password/change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("password/reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password/reset/sent/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
    # Profile and security settings
    path("profile/", views.profile, name="profile"),
    path("security/", views.security, name="security"),
    path("security/sessions/<int:pk>/revoke/", views.revoke_session, name="revoke_session"),
    path("security/sessions/revoke-others/", views.revoke_other_sessions, name="revoke_other_sessions"),
    path("security/two-factor/setup/", views.two_factor_setup, name="two_factor_setup"),
    path("security/two-factor/disable/", views.two_factor_disable, name="two_factor_disable"),
    path("security/two-factor/backup-codes/", views.two_factor_backup_codes, name="two_factor_backup_codes"),
    # Deactivation, reactivation, deletion
    path("deactivate/", views.deactivate, name="deactivate"),
    path("reactivate/", views.reactivate_request, name="reactivate_request"),
    path("reactivate/<str:token>/", views.reactivate_confirm, name="reactivate_confirm"),
    path("delete/", views.delete_account, name="delete_account"),
]
