from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import StyledAuthForm

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=StyledAuthForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/api/login/"),
         name="logout"),
    path("post-login/", views.post_login_redirect, name="post_login_redirect"),
    path("school/", views.school_profile, name="school_profile"),
    path("users/", views.user_list, name="user_list"),
    path("users/add/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path("parent-links/", views.parent_links, name="parent_links"),
]
