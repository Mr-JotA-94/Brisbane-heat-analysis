import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd

# ── 1. LOAD SUBURB BOUNDARIES ──────────────────────────────────────────────
suburbs = gpd.read_file("data/Suburbs/SAL_2021_AUST_GDA2020.shp")
print("=== SUBURBS ===")
print(f"Total suburbs in Australia: {len(suburbs)}")
print(f"Columns: {suburbs.columns.tolist()}")
print(f"CRS: {suburbs.crs}")
print()

# ── 2. LOAD VEGETATION LAYER ───────────────────────────────────────────────
vegetation = gpd.read_file("data/protected-vegetation-natural-assets-local-law-2003-council-vegetation.geojson")
print("=== VEGETATION ===")
print(f"Total vegetation polygons: {len(vegetation)}")
print(f"Columns: {vegetation.columns.tolist()}")
print(f"CRS: {vegetation.crs}")
print()

# ── 3. LOAD LANDSAT LST RASTER ─────────────────────────────────────────────
with rasterio.open("data/brisbane_lst.tif") as src:
    print("=== LANDSAT LST ===")
    print(f"CRS: {src.crs}")
    print(f"Resolution: {src.res} metres")
    print(f"Bounds: {src.bounds}")
    print(f"Band count: {src.count}")
    lst_data = src.read(1)  # read first band as numpy array
    print(f"Temperature range: {lst_data[lst_data > 0].min():.1f}°C — {lst_data.max():.1f}°C")
    print()

print("=== ALL FILES LOADED SUCCESSFULLY ===")