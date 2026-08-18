from rest_framework.routers import DefaultRouter

from .views import BoardViewSet, TaskViewSet

router = DefaultRouter()
router.register("boards", BoardViewSet, basename="board")
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
