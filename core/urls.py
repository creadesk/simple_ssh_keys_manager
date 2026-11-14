from django.contrib import admin
from django.urls import path, include

from sshkeys import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", views.credential_list, name="list"),
    path("new/", views.credential_create, name="create"),
    path("<int:pk>/edit/", views.credential_edit, name="edit"),
    path("<int:pk>/delete/", views.credential_delete, name="delete"),
    path("<int:pk>/test/", views.connection_test, name="test"),
    path("rotate-key/", views.rotate_encryption_key, name="rotate"),
    path('logout/', views.logout_view,name='logout'),
]
