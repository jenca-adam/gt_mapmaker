import importlib_resources
import geopandas as gpd
import shapely
import threading
from .trigrid import MultiTriGrid

country_lock = threading.Lock()
with importlib_resources.path("gt_mapmaker", "data/countries.geojson") as p:
    countries = gpd.read_file(p)

for _, country in countries.iterrows():

    country.geometry = country.geometry.buffer(0)


def country_from_position(lat, lon):
    with country_lock:
        selected = countries[countries.contains(shapely.Point(lon, lat))]
        if selected.empty:
            return "un"
        return selected.iloc[0]["iso_a2"].lower()

def load_country_trigrids(code):
    with importlib_resources.path("gt_mapmaker", f"data/grids/{code}.pickle") as p:
        return MultiTriGrid.load(p)
