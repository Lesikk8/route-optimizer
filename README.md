# RouteOptimizer

A delivery route optimization system built with Django and Django REST Framework.
Implements and visually compares three TSP algorithms on an interactive Leaflet.js map.

---

## Quick Start

### 1. Activate virtual environment
```bash
cd delivery_optimizer
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run database migrations
```bash
python manage.py migrate
```

### 4. Load sample Ukrainian cities
```bash
python manage.py loaddata routes/fixtures/initial_data.json
```

### 5. Create admin user (optional)
```bash
python manage.py createsuperuser
```

### 6. Start the development server
```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

---

## Features

| Page | URL | Description |
|------|-----|-------------|
| Map  | `/` | Add delivery points, select algorithm, optimize |
| Results | `/results/<id>/` | Visualize route, compare algorithms |
| History | `/history/` | All past optimization tasks |
| Admin | `/admin/` | Django admin panel |

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/points/` | List / create delivery points |
| DELETE | `/api/points/<id>/` | Delete a point |
| POST | `/api/optimize/` | Run optimization |
| GET | `/api/tasks/` | List all route tasks |
| GET | `/api/benchmark/<task_id>/` | Benchmark data for a task |

**Optimize request body:**
```json
{
  "point_ids": [1, 2, 3, 4, 5],
  "algorithm": "nn",
  "name": "My first route"
}
```
`algorithm` values: `nn`, `2opt`, `aco`, `all`

---

## Algorithms

### 1. Nearest Neighbor (`nn`)
Greedy heuristic. Starting from the first point, always moves to the closest unvisited
point until all points are visited. Returns to the start to close the tour.
- **Time complexity:** O(n²)
- **Quality:** Fast but sub-optimal — typically 20–25 % above optimal
- **Use when:** You need a quick, good-enough answer

### 2. 2-Opt (`2opt`)
Local search improvement. Starts with the Nearest Neighbor solution, then
iteratively reverses sub-paths whenever doing so reduces the total distance.
Repeats until no improving swap exists (local optimum).
- **Time complexity:** O(n²) per pass
- **Quality:** Significantly better than NN — eliminates crossing edges
- **Use when:** You want a better route and can afford a small wait

### 3. Ant Colony Optimization (`aco`)
Population-based metaheuristic. A colony of virtual ants each builds a
probabilistic tour guided by *pheromone trails* (reinforced by short tours)
and *heuristic information* (shorter edges are preferred). Pheromones
evaporate between iterations so the search explores broadly at first, then
converges on the best found solution.
- **Parameters:** 20 ants, 100 iterations, α=1, β=2, evaporation=0.5
- **Quality:** Best of the three — often near-optimal
- **Use when:** Route quality matters more than speed

### Distance metric
All algorithms use the **Haversine formula** to compute real great-circle
distances (km) between geographic coordinates.

---

## Project Structure

```
delivery_optimizer/
├── config/              # Django project settings
├── routes/
│   ├── algorithms.py    # NearestNeighborTSP, TwoOptTSP, AntColonyTSP
│   ├── api_views.py     # DRF API endpoints
│   ├── models.py        # DeliveryPoint, RouteTask, AlgorithmBenchmark
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # Django template views
│   ├── urls.py          # URL routing
│   ├── fixtures/        # Sample Ukrainian cities
│   ├── templates/       # HTML templates (base, index, results, history)
│   └── static/          # CSS + JavaScript
├── requirements.txt
└── manage.py
```
