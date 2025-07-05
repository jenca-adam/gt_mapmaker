### Triangulate polygon, overlay grid
import shapely
import mapbox_earcut
import numpy as np
import itertools
import math
import random
import bisect
import tqdm
import pickle
import geopandas as gpd
import matplotlib.pyplot as plt

#### A FUCK TON OF SCARY GEOMETRY
## HELP ME

EPSILON = 1e-6


def nonconvex_triangulate(poly):
    vertices = np.array(poly.exterior.coords)
    tris = mapbox_earcut.triangulate_float32(vertices, np.array([len(vertices)]))
    tri_coords = [
        (vertices[a], vertices[b], vertices[c])
        for a, b, c in itertools.batched(tris, 3)
    ]
    return tri_coords


def box_corners(box):
    return (
        (box[0][0], box[0][1]),
        (box[1][0], box[0][1]),
        (box[1][0], box[1][1]),
        (box[0][0], box[1][1]),
    )


def boxes_intersect(A, B):
    return not (
        A[1][0] < B[0][0] or A[0][0] > B[1][0] or A[1][1] < B[0][1] or A[0][1] > B[1][1]
    )


def point_box_intersect(box, pt):
    return box[0][0] <= pt[0] <= box[1][0] and box[1][0] <= pt[1] <= box[1][1]


def ccw(A, B, C):
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segments_intersect(s1, e1, s2, e2):
    return ccw(s1, s2, e2) != ccw(e1, s2, e2) and ccw(s1, e1, s2) != ccw(s1, e1, e2)


def barycentric_precompute(a, b, c):
    x1, y1 = a
    x2, y2 = b
    x3, y3 = c
    detT = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)  # precompute
    return x1, y1, x2, y2, x3, y3, detT


def barycentric(x1, y1, x2, y2, x3, y3, detT, x, y):
    u = ((y2 - y3) * (x - x3) + (x3 - x2) * (y - y3)) / detT
    v = ((y3 - y1) * (x - x3) + (x1 - x3) * (y - y3)) / detT
    w = 1 - u - v
    return (u, v, w)


def segment_box_intersect(box, s, e):
    corners = box_corners(box)
    return any(
        segments_intersect(s, e, corners[i], corners[(i + 1) % 4]) for i in range(4)
    )


def tri_bbox(tri):
    return (
        (min(tri[0][0], tri[1][0], tri[2][0]), min(tri[0][1], tri[1][1], tri[2][1])),
        (max(tri[0][0], tri[1][0], tri[2][0]), max(tri[0][1], tri[1][1], tri[2][1])),
    )


def tri_box_intersect(box, tri, precomputed, poly_tri):
    # CHECK 1: Triangle vertices in box
    # fastest
    if any(point_box_intersect(box, pt) for pt in tri):
        return True
    # CHECK 1.5 : bboxes intersect; maybe swap with 1?
    if not boxes_intersect(box, tri_bbox(tri)):
        return False
    # CHECK 2: box vertices in triangle
    # bary precomputed
    if any(all(c > -EPSILON for c in barycentric(*precomputed, *pt)) for pt in box):
        return True
    # CHECK 3: shapely

    return shapely.Polygon(box_corners(box)).intersects(poly_tri)


def point_tri_intersect(tri, p):
    return all(x > -EPSILON for x in barycentric(*barycentric_precompute(*tri), *p))


def plot_grid(poly, grid_size=0.1):

    tris = [shapely.Polygon(tri) for tri in nonconvex_triangulate(poly)]
    series = gpd.GeoDataFrame({"geometry": tris})
    series.plot()
    left, top, right, bottom = poly.bounds
    x = left
    y = top
    while x < right:
        plt.plot([x, x], [top, bottom], linewidth=0.1)
        x += grid_size
    while y < bottom:
        plt.plot([left, right], [y, y], linewidth=0.1)
        y += grid_size
    plt.show()


def rand_in_tri(coords):
    A, B, C = coords
    r1 = random.random()
    r2 = random.random()
    if r1 + r2 > 1:
        r1 = 1 - r1
        r2 = 1 - r2
    x = A[0] + r1 * (B[0] - A[0]) + r2 * (C[0] - A[0])
    y = A[1] + r1 * (B[1] - A[1]) + r2 * (C[1] - A[1])
    return (x, y)


class TriGrid:
    def __init__(self, area, tri_areas, tri_coords, store, grid_size, tris=None):
        self.area = area
        self.tri_areas = tri_areas
        self.tri_coords = tri_coords
        self.store = store
        self.grid_size = grid_size
        self.tris = tris or [shapely.Polygon(tc) for tc in self.tri_coords]
        self.cdf = np.cumsum(tri_areas).tolist()

    @classmethod
    def build(cls, poly, grid_size=0.1):
        area = poly.area
        tri_coords = nonconvex_triangulate(poly)
        tris = [shapely.Polygon(tc) for tc in tri_coords]
        tri_areas = [tri.area for tri in tris]
        store = {}
        for index, tri in enumerate(tqdm.tqdm(tris)):
            # get grid cells occupied by bounding box
            bounds = tri.bounds
            left, top, right, bottom = map(
                int,
                (
                    bounds[0] // grid_size,
                    bounds[1] // grid_size,
                    math.ceil(bounds[2] / grid_size),
                    math.ceil(bounds[3] / grid_size),
                ),
            )
            A, B, C = tri_coords[index]
            precomputed = barycentric_precompute(A, B, C)
            if precomputed[-1] == 0:
                continue  # skip degenerates
            for x in range(left, right):
                seen_full = False
                for y in range(top, bottom):
                    # https://github.com/jenca-adam/crender/blob/main/src/texture.c#L239 (well, almost)

                    box = (
                        (x * grid_size, y * grid_size),
                        (x * grid_size + grid_size, y * grid_size + grid_size),
                    )

                    if tri_box_intersect(box, (A, B, C), precomputed, tris[index]):
                        store.setdefault((x, y), [])
                        store[(x, y)].append(index)
                        seen_full = True

                    # bail here (tris are always convex)
                    elif seen_full:
                        break
        return cls(area, tri_areas, tri_coords, store, grid_size, tris)

    def contains(self, x, y):
        cx, cy = x // self.grid_size, y // self.grid_size
        if (cx, cy) not in self.store:
            return False
        pt = shapely.Point(x, y)
        return any(
            point_tri_intersect(self.tri_coords[tri], (x, y))
            for tri in self.store[(cx, cy)]
        )

    def rand_point(self):
        m = random.uniform(0, self.area)
        index = bisect.bisect(self.cdf, m)
        coords = self.tri_coords[index]
        return rand_in_tri(coords)

    def rand_point_plot_test(self, n=10000):

        gpd.GeoDataFrame({"geometry": self.tris}).plot()
        for i in tqdm.tqdm(range(n)):
            x, y = self.rand_point()
            if self.contains(x, y):
                color = "b"
            else:
                color = "r"
            plt.plot(x, y, "ro", color=color)
        plt.show()


class MultiTriGrid:
    def __init__(self, tri_grids):
        self.tri_grids = tri_grids
        self.tg_areas = [tg.area for tg in self.tri_grids]
        self.area = sum(self.tg_areas)
        self.cdf = np.cumsum(self.tg_areas).tolist()

    @classmethod
    def build(cls, poly, grid_size=0.1):
        if hasattr(poly, "geoms"):  # idk how to properly check for multi polygons
            return cls([TriGrid.build(geom, grid_size) for geom in poly.geoms])
        return cls([TriGrid.build(poly, grid_size)])

    @classmethod
    def load(cls, file):
        with open(file, "rb") as f:
            tgs = [TriGrid(*args) for args in pickle.load(f)]
        return cls(tgs)

    def dump(self, file):
        with open(file, "wb") as f:
            pickle.dump(
                [
                    (tg.area, tg.tri_areas, tg.tri_coords, tg.store, tg.grid_size)
                    for tg in self.tri_grids
                ],
                f,
            )

    def contains(self, x, y):
        return any(tg.contains(x, y) for tg in self.tri_grids)

    def rand_point(self):
        m = random.uniform(0, self.area)
        index = bisect.bisect(self.cdf, m)
        return self.tri_grids[index].rand_point()
