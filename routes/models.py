from django.db import models


class DeliveryPoint(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=500, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.latitude:.4f}, {self.longitude:.4f})"


class RouteTask(models.Model):
    ALGORITHM_CHOICES = [
        ('nn', 'Nearest Neighbor'),
        ('2opt', '2-Opt'),
        ('aco', 'Ant Colony Optimization'),
        ('all', 'All Algorithms'),
    ]

    name = models.CharField(max_length=200)
    points = models.ManyToManyField(DeliveryPoint, related_name='tasks')
    algorithm = models.CharField(max_length=10, choices=ALGORITHM_CHOICES)
    result_path = models.JSONField(default=list)   # ordered list of DeliveryPoint IDs
    total_distance = models.FloatField(default=0.0)
    execution_time = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.get_algorithm_display()}] — {self.total_distance:.1f} km"


class AlgorithmBenchmark(models.Model):
    task = models.ForeignKey(RouteTask, on_delete=models.CASCADE, related_name='benchmarks')
    algorithm_name = models.CharField(max_length=50)
    execution_time = models.FloatField()
    total_distance = models.FloatField()
    path = models.JSONField(default=list)   # ordered list of DeliveryPoint IDs

    def __str__(self):
        return f"{self.task.name} — {self.algorithm_name}"
