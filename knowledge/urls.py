from rest_framework.routers import DefaultRouter
from .views import     KnowledgeNodeViewSet, KnowledgeComponentViewSet,GlossaryViewSet,QuestionViewSet,DependencyViewSet, TextViewSet


router = DefaultRouter()

# Register all ViewSets
router.register(r'nodes', KnowledgeNodeViewSet, basename='node')
router.register(r'text', TextViewSet, basename='text')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'knowledge-components', KnowledgeComponentViewSet)
router.register(r'Dependency',DependencyViewSet)
router.register(r'glossary', GlossaryViewSet, basename=' glossary')

urlpatterns = router.urls
