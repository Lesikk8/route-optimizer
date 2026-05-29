from django.contrib import admin
from .models import DeliveryPoint, RouteTask, AlgorithmBenchmark


@admin.register(DeliveryPoint)
class DeliveryPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'latitude', 'longitude', 'created_at']
    search_fields = ['name', 'address']


class BenchmarkInline(admin.TabularInline):
    model = AlgorithmBenchmark
    extra = 0
    readonly_fields = ['algorithm_name', 'total_distance', 'execution_time']


@admin.register(RouteTask)
class RouteTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'algorithm', 'total_distance', 'execution_time', 'created_at']
    list_filter = ['algorithm']
    inlines = [BenchmarkInline]


@admin.register(AlgorithmBenchmark)
class AlgorithmBenchmarkAdmin(admin.ModelAdmin):
    list_display = ['task', 'algorithm_name', 'total_distance', 'execution_time']
