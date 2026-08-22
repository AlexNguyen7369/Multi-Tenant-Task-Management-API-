from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    # Root landing page — just a button pointing at /testui/. This project
    # has no real homepage (it's an API, not a website); see notes/hood.md.
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/workspaces/", include("apps.workspaces.urls")),
    path("api/", include("apps.tasks.urls")),
    # Same-origin manual test console for exercising the API by hand — see
    # templates/testui.html. Same-origin (served by Django itself) so no CORS
    # setup is needed to call the API from it.
    path("testui/", TemplateView.as_view(template_name="testui.html"), name="testui"),
]
