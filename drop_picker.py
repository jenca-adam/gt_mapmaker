import gt_mapmaker
import streetlevel.streetview
import shapely
import random

MAX_RETRIES = 10
RADIUS = 1000
country = gt_mapmaker.countries[gt_mapmaker.countries.iso_a2 == "MC"].iloc[0]

tg = gt_mapmaker.load_country_trigrids("MC")
def pick_point_in_poly():
    lon, lat = tg.rand_point()
    return lat, lon


def pick_drop(o, spawner):
    for i in range(MAX_RETRIES):
        if spawner.kill_flag:
            break
        lat, lon = pick_point_in_poly()
        try:
            pano = streetlevel.streetview.find_panorama(lat, lon, radius=RADIUS)
        except:
            continue
        if not pano:
            continue
        return gt_mapmaker.Drop(pano.lat, pano.lon, "mc", pano_id=pano.id)
