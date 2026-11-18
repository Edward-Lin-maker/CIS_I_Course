"""Closest-point queries against the triangle mesh."""

from typing import Tuple

import numpy as np
from scipy.spatial import cKDTree

from data_types.nominal_types import vct3
from ..mesh import Mesh

DEGENERATE_DETERMINANT = 1e-18    # Gram determinant below which a triangle is treated as degenerate
SEARCH_INDEX_CACHE_KEY = "closest_point_search_index"


def _closest_points_on_segments(p: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    """
    Projection of p onto the segment [start, end], clamped to the end points.
    input: p, start, end (M,3)
    output: (M,3) closest points on the segments
    """
    direction = end - start
    length_sq = np.einsum("ij,ij->i", direction, direction)
    t = np.einsum("ij,ij->i", p - start, direction) / np.where(length_sq > 0.0, length_sq, 1.0)
    t = np.clip(np.where(length_sq > 0.0, t, 0.0), 0.0, 1.0)
    return start + t[:, None] * direction


def closest_points_on_triangles(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """
    Vectorised exact point-to-triangle closest point for M (point, triangle) pairs.
    Step 1: least-squares (lambda, mu) with p ~= a + lambda (b - a) + mu (c - a) (Taylor, ICP slides).
    Step 2: if lambda, mu >= 0 and lambda + mu <= 1 the plane projection is the answer;
            otherwise the closest point is on the boundary: the nearest of the three
            clamped edge projections (exact also for obtuse and degenerate triangles).
    input: p, a, b, c (M,3)
    output: (M,3) closest points
    """
    ab, ac, ap = b - a, c - a, p - a
    d00 = np.einsum("ij,ij->i", ab, ab)
    d01 = np.einsum("ij,ij->i", ab, ac)
    d11 = np.einsum("ij,ij->i", ac, ac)
    d20 = np.einsum("ij,ij->i", ap, ab)
    d21 = np.einsum("ij,ij->i", ap, ac)
    det = d00 * d11 - d01 * d01
    valid = det > DEGENERATE_DETERMINANT * np.maximum(d00 * d11, 1.0)
    safe_det = np.where(valid, det, 1.0)
    lam = (d11 * d20 - d01 * d21) / safe_det
    mu = (d00 * d21 - d01 * d20) / safe_det
    inside = valid & (lam >= 0.0) & (mu >= 0.0) & (lam + mu <= 1.0)

    edge_candidates = np.stack([_closest_points_on_segments(p, a, b),
                                _closest_points_on_segments(p, b, c),
                                _closest_points_on_segments(p, c, a)], axis=0)       # (3,M,3)
    edge_dist_sq = np.sum((edge_candidates - p[None]) ** 2, axis=2)                   # (3,M)
    on_edge = edge_candidates[np.argmin(edge_dist_sq, axis=0), np.arange(p.shape[0])]
    in_face = a + lam[:, None] * ab + mu[:, None] * ac
    return np.where(inside[:, None], in_face, on_edge)


def closest_point_on_triangle(p: vct3, a: vct3, b: vct3, c: vct3) -> vct3:
    """
    input: query point p, triangle corners a, b, c (vct3)
    output: the point of the triangle (face, edge or vertex) closest to p (vct3)
    """
    rows = [np.asarray(v.vec, dtype=float).reshape(1, 3) for v in (p, a, b, c)]
    return vct3(closest_points_on_triangles(*rows)[0])


def _search_index(mesh: Mesh) -> Tuple[cKDTree, float]:
    """
    KD-tree over triangle centroids plus the largest bounding-sphere radius, cached on the mesh.
    input: mesh
    output: (tree, r_max)
    """
    if SEARCH_INDEX_CACHE_KEY not in mesh._cache:
        mesh._cache[SEARCH_INDEX_CACHE_KEY] = (cKDTree(mesh.centroids), float(mesh.bounding_sphere_radius.max()))
    return mesh._cache[SEARCH_INDEX_CACHE_KEY]


def closest_points_on_mesh(points: np.ndarray, mesh: Mesh) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Exact closest points on the mesh with bounding-sphere pruning (vectorised):
      1. upper bound u_k = distance to the triangle whose centroid is nearest (KD-tree);
      2. a triangle t can only beat u_k if ||q_k - centroid_t|| - r_t <= u_k
         (r_t = bounding-sphere radius), so only those candidates are evaluated exactly.
    input: points (K,3) in CT coordinates, mesh
    output: closest (K,3), triangle index (K,), distance (K,)
    """
    q = np.asarray(points, dtype=float).reshape(-1, 3)
    n_points = q.shape[0]
    if n_points == 0:
        return np.zeros((0, 3)), np.zeros(0, dtype=int), np.zeros(0)
    tree, r_max = _search_index(mesh)
    tri_vertices = mesh.tri_vertices

    _, first_guess = tree.query(q)
    guess_points = closest_points_on_triangles(q, *(tri_vertices[first_guess, i] for i in range(3)))
    upper_bound = np.linalg.norm(guess_points - q, axis=1)

    neighbour_lists = tree.query_ball_point(q, upper_bound + r_max + 1e-9)
    counts = np.array([len(lst) for lst in neighbour_lists])
    point_idx = np.repeat(np.arange(n_points), counts)
    tri_idx = np.concatenate([np.asarray(lst, dtype=int) for lst in neighbour_lists])
    centre_dist = np.linalg.norm(q[point_idx] - mesh.centroids[tri_idx], axis=1)
    keep = centre_dist - mesh.bounding_sphere_radius[tri_idx] <= upper_bound[point_idx] + 1e-9
    point_idx, tri_idx = point_idx[keep], tri_idx[keep]

    candidates = closest_points_on_triangles(q[point_idx], *(tri_vertices[tri_idx, i] for i in range(3)))
    cand_dist = np.linalg.norm(candidates - q[point_idx], axis=1)

    order = np.lexsort((cand_dist, point_idx))          # by point, then by distance
    first = order[np.r_[True, point_idx[order][1:] != point_idx[order][:-1]]]
    closest = guess_points.copy()
    triangle = first_guess.astype(int).copy()
    distance = upper_bound.copy()
    better = cand_dist[first] < distance[point_idx[first]]
    winners = first[better]
    closest[point_idx[winners]] = candidates[winners]
    triangle[point_idx[winners]] = tri_idx[winners]
    distance[point_idx[winners]] = cand_dist[winners]
    return closest, triangle, distance
