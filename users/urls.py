from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import TeacherViewSet, StudentViewSet

router = DefaultRouter()
router.register(r'teachers', TeacherViewSet, basename="teachers")
router.register(r'students', StudentViewSet, basename="students")

urlpatterns = [
    path('', include(router.urls)),  # API endpoints (e.g., /api/teachers/, /api/students/)
]
