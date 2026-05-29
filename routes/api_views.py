from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, DestroyAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import DeliveryPoint, RouteTask, AlgorithmBenchmark
from .serializers import DeliveryPointSerializer, RouteTaskSerializer, AlgorithmBenchmarkSerializer
from .algorithms import NearestNeighborTSP, TwoOptTSP, AntColonyTSP

ALGORITHMS = {
    'nn': NearestNeighborTSP,
    '2opt': TwoOptTSP,
    'aco': AntColonyTSP,
}


def _points_to_dicts(qs):
    """Convert a DeliveryPoint queryset to the list-of-dicts format algorithms expect."""
    return [{'id': p.id, 'name': p.name, 'lat': p.latitude, 'lon': p.longitude} for p in qs]


def _path_ids(result_indices: list, points: list) -> list:
    """Map algorithm index path (with closing duplicate) to point IDs, no closing duplicate."""
    return [points[i]['id'] for i in result_indices[:-1]]


def _path_coords(result_indices: list, points: list) -> list:
    """Return full coord dicts in tour order (including closing duplicate for the map polyline)."""
    return [points[i] for i in result_indices]


class DeliveryPointListCreate(ListCreateAPIView):
    queryset = DeliveryPoint.objects.all().order_by('-created_at')
    serializer_class = DeliveryPointSerializer


class DeliveryPointDelete(DestroyAPIView):
    queryset = DeliveryPoint.objects.all()
    serializer_class = DeliveryPointSerializer


class OptimizeView(APIView):
    """
    POST /api/optimize/

    Body:
        {
            "point_ids": [1, 2, 3, ...],          // >= 2 required
            "algorithm": "nn" | "2opt" | "aco" | "all",
            "name": "optional task name"
        }
    """

    def post(self, request):
        point_ids = request.data.get('point_ids', [])
        algorithm = request.data.get('algorithm', 'nn')
        name = request.data.get('name', '') or f'Route #{RouteTask.objects.count() + 1}'

        if len(point_ids) < 2:
            return Response({'error': 'Select at least 2 delivery points.'}, status=status.HTTP_400_BAD_REQUEST)

        if algorithm not in list(ALGORITHMS.keys()) + ['all']:
            return Response({'error': f'Unknown algorithm "{algorithm}".'}, status=status.HTTP_400_BAD_REQUEST)

        points_qs = DeliveryPoint.objects.filter(id__in=point_ids)
        id_map = {p.id: p for p in points_qs}
        # Preserve the order the client sent
        ordered_points = [id_map[pid] for pid in point_ids if pid in id_map]

        if len(ordered_points) < 2:
            return Response({'error': 'Points not found in database.'}, status=status.HTTP_404_NOT_FOUND)

        points = _points_to_dicts(ordered_points)

        if algorithm == 'all':
            return self._run_all(request, name, points, points_qs)

        return self._run_single(request, name, algorithm, points, points_qs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_single(self, request, name, algorithm, points, points_qs):
        algo = ALGORITHMS[algorithm]()
        result = algo.solve(points)

        task = RouteTask.objects.create(
            name=name,
            algorithm=algorithm,
            result_path=_path_ids(result['path'], points),
            total_distance=result['distance'],
            execution_time=result['execution_time'],
        )
        task.points.set(points_qs)

        return Response({
            'task_id': task.id,
            'algorithm': algorithm,
            'path': _path_coords(result['path'], points),
            'distance': result['distance'],
            'execution_time': result['execution_time'],
        }, status=status.HTTP_201_CREATED)

    def _run_all(self, request, name, points, points_qs):
        results = {}
        best_algo, best_dist, best_path = None, float('inf'), None

        for algo_key, AlgoClass in ALGORITHMS.items():
            r = AlgoClass().solve(points)
            results[algo_key] = r
            if r['distance'] < best_dist:
                best_dist, best_algo, best_path = r['distance'], algo_key, r['path']

        task = RouteTask.objects.create(
            name=name,
            algorithm='all',
            result_path=_path_ids(best_path, points),
            total_distance=best_dist,
            execution_time=sum(r['execution_time'] for r in results.values()),
        )
        task.points.set(points_qs)

        benchmarks = []
        for algo_key, r in results.items():
            b = AlgorithmBenchmark.objects.create(
                task=task,
                algorithm_name=algo_key,
                execution_time=r['execution_time'],
                total_distance=r['distance'],
                path=_path_ids(r['path'], points),
            )
            benchmarks.append(b)

        algo_labels = {'nn': 'Nearest Neighbor', '2opt': '2-Opt', 'aco': 'Ant Colony'}
        comparison = {
            k: {
                'label': algo_labels[k],
                'distance': results[k]['distance'],
                'execution_time': results[k]['execution_time'],
                'path': _path_coords(results[k]['path'], points),
            }
            for k in ALGORITHMS
        }

        return Response({
            'task_id': task.id,
            'algorithm': 'all',
            'best': best_algo,
            'best_distance': best_dist,
            'best_path': _path_coords(best_path, points),
            'comparison': comparison,
        }, status=status.HTTP_201_CREATED)


class RouteTaskList(ListAPIView):
    queryset = RouteTask.objects.all().order_by('-created_at')
    serializer_class = RouteTaskSerializer


class BenchmarkView(APIView):
    """GET /api/benchmark/<task_id>/"""

    def get(self, request, task_id):
        task = get_object_or_404(RouteTask, id=task_id)
        benchmarks = AlgorithmBenchmarkSerializer(task.benchmarks.all(), many=True)
        return Response({
            'task_id': task.id,
            'task_name': task.name,
            'algorithm': task.algorithm,
            'benchmarks': benchmarks.data,
        })
