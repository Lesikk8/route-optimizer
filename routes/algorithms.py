"""
TSP (Travelling Salesman Problem) algorithms for delivery route optimization.

All algorithms receive a list of point dicts:
    [{'id': int, 'name': str, 'lat': float, 'lon': float}, ...]

All algorithms return:
    {'path': [index, ...], 'distance': float, 'execution_time': float}

'path' contains indices into the input list, starting and ending at index 0
(closed tour).  The caller maps indices back to point IDs.
"""

import math
import time
import random
import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Haversine formula — great-circle distance between two lat/lon points.
    Returns kilometres.
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(min(a, 1.0)))


def build_distance_matrix(points: list) -> np.ndarray:
    """Build an n×n symmetric matrix of Haversine distances (km)."""
    n = len(points)
    dist = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(points[i]['lat'], points[i]['lon'],
                          points[j]['lat'], points[j]['lon'])
            dist[i][j] = dist[j][i] = d
    return dist


def tour_distance(path: list, dist: np.ndarray) -> float:
    """Sum of edge weights for a closed tour."""
    return float(sum(dist[path[k]][path[k + 1]] for k in range(len(path) - 1)))


def _trivial_result(points: list, start: float) -> dict:
    """Return value for degenerate inputs (0 or 1 point)."""
    if not points:
        return {'path': [], 'distance': 0.0, 'execution_time': time.time() - start}
    return {'path': [0, 0], 'distance': 0.0, 'execution_time': round(time.time() - start, 4)}


# ---------------------------------------------------------------------------
# Algorithm 1 — Nearest Neighbour
# ---------------------------------------------------------------------------

class NearestNeighborTSP:
    """
    Greedy nearest-neighbour heuristic.

    Strategy: start at node 0, then always move to the closest unvisited node.
    Complexity: O(n²).  Fast but may produce routes 20-25 % longer than optimal.
    """

    def solve(self, points: list) -> dict:
        start = time.time()
        n = len(points)
        if n <= 1:
            return _trivial_result(points, start)

        dist = build_distance_matrix(points)
        visited = [False] * n
        path = [0]
        visited[0] = True

        for _ in range(n - 1):
            current = path[-1]
            # Find the nearest unvisited node
            nearest, nearest_dist = -1, math.inf
            for j in range(n):
                if not visited[j] and dist[current][j] < nearest_dist:
                    nearest, nearest_dist = j, dist[current][j]
            path.append(nearest)
            visited[nearest] = True

        path.append(0)  # close the tour
        return {
            'path': path,
            'distance': round(tour_distance(path, dist), 2),
            'execution_time': round(time.time() - start, 4),
        }


# ---------------------------------------------------------------------------
# Algorithm 2 — 2-Opt
# ---------------------------------------------------------------------------

class TwoOptTSP:
    """
    2-opt local search.

    Starts with the nearest-neighbour solution, then repeatedly reverses
    sub-paths (i…j) whenever doing so reduces total distance.  Runs until
    no improving swap exists (local optimum).
    Complexity: O(n²) per pass; typically converges in a few passes.
    """

    def solve(self, points: list) -> dict:
        start = time.time()
        n = len(points)
        if n <= 2:
            return NearestNeighborTSP().solve(points)

        dist = build_distance_matrix(points)

        # Seed with nearest-neighbour tour (open path, no duplicate start)
        nn = NearestNeighborTSP().solve(points)
        path = nn['path'][:-1]  # remove closing duplicate

        improved = True
        while improved:
            improved = False
            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    # Edges being replaced: (i-1 → i) and (j → j+1 mod n)
                    a, b = path[i - 1], path[i]
                    c, d = path[j], path[(j + 1) % n]
                    delta = (dist[a][b] + dist[c][d]) - (dist[a][c] + dist[b][d])
                    if delta > 1e-10:          # reversing segment [i..j] improves tour
                        path[i:j + 1] = path[i:j + 1][::-1]
                        improved = True

        path.append(path[0])  # close the tour
        return {
            'path': path,
            'distance': round(tour_distance(path, dist), 2),
            'execution_time': round(time.time() - start, 4),
        }


# ---------------------------------------------------------------------------
# Algorithm 3 — Ant Colony Optimization (ACO)
# ---------------------------------------------------------------------------

class AntColonyTSP:
    """
    Ant Colony Optimization (ACO) for the TSP.

    Inspired by how real ants find shortest paths via pheromone trails.
    Each ant builds a probabilistic tour guided by two forces:
      - tau  (pheromone): reinforced by historically good edges
      - eta  (heuristic): 1/distance — prefers short edges

    The selection probability for edge (i → j) is:
        P(i,j) = tau[i,j]^alpha * eta[i,j]^beta  /  Σ (same for unvisited)

    After all ants finish, pheromones evaporate and then each ant deposits
    1/tour_length on its edges — shorter tours strengthen more.

    Parameters
    ----------
    n_ants       : ants per iteration (more = better exploration)
    n_iterations : number of rounds
    alpha        : pheromone influence weight (higher → exploit known paths)
    beta         : heuristic influence weight (higher → prefer short edges)
    evaporation  : pheromone decay rate per iteration ∈ (0, 1)
    """

    def __init__(
        self,
        n_ants: int = 20,
        n_iterations: int = 100,
        alpha: float = 1.0,
        beta: float = 2.0,
        evaporation: float = 0.5,
    ):
        self.n_ants = n_ants
        self.n_iterations = n_iterations
        self.alpha = alpha
        self.beta = beta
        self.evaporation = evaporation

    def solve(self, points: list) -> dict:
        start = time.time()
        n = len(points)
        if n <= 2:
            return NearestNeighborTSP().solve(points)

        dist = build_distance_matrix(points)

        # eta[i][j] = 1 / distance — heuristic desirability
        with np.errstate(divide='ignore', invalid='ignore'):
            eta = np.where(dist > 0, 1.0 / dist, 0.0)

        # Pheromone matrix — initialise uniformly
        tau = np.ones((n, n), dtype=np.float64)

        best_path, best_dist = None, math.inf

        for _ in range(self.n_iterations):
            iteration_paths = []

            for _ in range(self.n_ants):
                path = self._build_ant_tour(tau, eta, n)
                d = tour_distance(path, dist)
                iteration_paths.append((path, d))
                if d < best_dist:
                    best_dist, best_path = d, path[:]

            # Evaporate pheromones
            tau *= (1.0 - self.evaporation)

            # Deposit pheromones proportional to solution quality
            for path, d in iteration_paths:
                deposit = 1.0 / d
                for k in range(len(path) - 1):
                    i, j = path[k], path[k + 1]
                    tau[i][j] += deposit
                    tau[j][i] += deposit

        return {
            'path': best_path,
            'distance': round(best_dist, 2),
            'execution_time': round(time.time() - start, 4),
        }

    def _build_ant_tour(self, tau: np.ndarray, eta: np.ndarray, n: int) -> list:
        """Construct one ant's complete tour using roulette-wheel selection."""
        start_node = random.randint(0, n - 1)
        visited = np.zeros(n, dtype=bool)
        path = [start_node]
        visited[start_node] = True

        for _ in range(n - 1):
            current = path[-1]

            # Attractiveness of each unvisited node
            attractiveness = np.where(
                ~visited,
                (tau[current] ** self.alpha) * (eta[current] ** self.beta),
                0.0,
            )
            total = attractiveness.sum()

            if total == 0.0:
                # Fallback: pick first unvisited node deterministically
                next_node = int(np.argmax(~visited))
            else:
                probabilities = attractiveness / total
                next_node = int(np.random.choice(n, p=probabilities))

            path.append(next_node)
            visited[next_node] = True

        path.append(start_node)  # close tour
        return path
