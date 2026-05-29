from rest_framework import serializers
from .models import DeliveryPoint, RouteTask, AlgorithmBenchmark


class DeliveryPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryPoint
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'created_at']
        read_only_fields = ['id', 'created_at']


class AlgorithmBenchmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlgorithmBenchmark
        fields = ['id', 'algorithm_name', 'execution_time', 'total_distance', 'path']


class RouteTaskSerializer(serializers.ModelSerializer):
    algorithm_display = serializers.CharField(source='get_algorithm_display', read_only=True)
    point_count = serializers.SerializerMethodField()
    benchmarks = AlgorithmBenchmarkSerializer(many=True, read_only=True)

    class Meta:
        model = RouteTask
        fields = [
            'id', 'name', 'algorithm', 'algorithm_display',
            'result_path', 'total_distance', 'execution_time',
            'created_at', 'point_count', 'benchmarks',
        ]
        read_only_fields = ['id', 'created_at']

    def get_point_count(self, obj):
        return obj.points.count()
