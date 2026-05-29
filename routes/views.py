from django.shortcuts import render, get_object_or_404
from .models import RouteTask, DeliveryPoint


def index_view(request):
    return render(request, 'routes/index.html')


def results_view(request, task_id):
    task = get_object_or_404(RouteTask, id=task_id)

    # Build ordered path with full coordinates
    points_by_id = {p.id: p for p in task.points.all()}
    path_points = []
    for pid in task.result_path:
        p = points_by_id.get(pid)
        if p:
            path_points.append({'id': p.id, 'name': p.name, 'lat': p.latitude, 'lon': p.longitude})
    # Close the polyline
    if path_points:
        path_points.append(path_points[0])

    # Benchmark data for the "all" comparison view
    benchmarks = {}
    if task.algorithm == 'all':
        algo_labels = {'nn': 'Nearest Neighbor', '2opt': '2-Opt', 'aco': 'Ant Colony'}
        for b in task.benchmarks.all():
            bench_path = []
            for pid in b.path:
                p = points_by_id.get(pid)
                if p:
                    bench_path.append({'id': p.id, 'name': p.name, 'lat': p.latitude, 'lon': p.longitude})
            if bench_path:
                bench_path.append(bench_path[0])
            benchmarks[b.algorithm_name] = {
                'label': algo_labels.get(b.algorithm_name, b.algorithm_name),
                'distance': b.total_distance,
                'execution_time': b.execution_time,
                'path': bench_path,
            }

    task_data = {
        'id': task.id,
        'name': task.name,
        'algorithm': task.algorithm,
        'algorithm_display': task.get_algorithm_display(),
        'path': path_points,
        'distance': task.total_distance,
        'execution_time': task.execution_time,
        'benchmarks': benchmarks,
        'point_count': task.points.count(),
    }

    return render(request, 'routes/results.html', {
        'task': task,
        'task_data': task_data,
    })


def history_view(request):
    tasks = RouteTask.objects.prefetch_related('points').order_by('-created_at')
    return render(request, 'routes/history.html', {'tasks': tasks})
