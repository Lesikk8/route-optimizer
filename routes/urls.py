from django.urls import path
from . import views, api_views

urlpatterns = [
    # Django template views
    path('', views.index_view, name='index'),
    path('results/<int:task_id>/', views.results_view, name='results'),
    path('history/', views.history_view, name='history'),

    # REST API
    path('api/points/', api_views.DeliveryPointListCreate.as_view(), name='api-points'),
    path('api/points/<int:pk>/', api_views.DeliveryPointDelete.as_view(), name='api-point-delete'),
    path('api/optimize/', api_views.OptimizeView.as_view(), name='api-optimize'),
    path('api/tasks/', api_views.RouteTaskList.as_view(), name='api-tasks'),
    path('api/benchmark/<int:task_id>/', api_views.BenchmarkView.as_view(), name='api-benchmark'),
]
