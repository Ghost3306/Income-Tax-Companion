from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify/<uuid:token>/", views.verify_account, name="verify_account"),
    path("login/", views.login_view, name="login"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<uuid:token>/", views.reset_password, name="reset_password"),
]
