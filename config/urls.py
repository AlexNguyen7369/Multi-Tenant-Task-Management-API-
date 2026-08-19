from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/workspaces/", include("apps.workspaces.urls")),
    path("api/", include("apps.tasks.urls")),
    # Same-origin manual test console for exercising the API by hand — see
    # templates/testui.html. Same-origin (served by Django itself) so no CORS
    # setup is needed to call the API from it.
    path("testui/", TemplateView.as_view(template_name="testui.html"), name="testui"),
]
