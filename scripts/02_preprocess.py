import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
from shapely.geometry import mapping

# ── 1. LOAD ALL THREE FILES ────────────────────────────────────────────────
print("Loading files...")
suburbs = gpd.read_file("data/Suburbs/SAL_2021_AUST_GDA2020.shp")
vegetation = gpd.read_file("data/protected-vegetation-natural-assets-local-law-2003-council-vegetation.geojson")

# ── 2. FILTER SUBURBS TO BRISBANE ONLY ────────────────────────────────────
# The shapefile has all Australian suburbs — filter to Queensland first
# then clip to Brisbane's rough bounding box
print("Filtering to Brisbane...")
brisbane_suburbs = suburbs[suburbs['STE_NAME21'] == 'Queensland'].copy()

# Clip to Brisbane metro bounding box (same coords as GEE script)
from shapely.geometry import box
brisbane_bbox = box(152.95, -27.65, 153.25, -27.35)
brisbane_bbox_gdf = gpd.GeoDataFrame(geometry=[brisbane_bbox], crs="EPSG:4326")

# Reproject suburbs to EPSG:4326 for clipping (they're in 7844)
brisbane_suburbs = brisbane_suburbs.to_crs("EPSG:4326")
brisbane_suburbs = gpd.clip(brisbane_suburbs, brisbane_bbox_gdf)

print(f"Brisbane suburbs found: {len(brisbane_suburbs)}")
print(f"Sample suburbs: {brisbane_suburbs['SAL_NAME21'].head(10).tolist()}")
print()

# ── 3. REPROJECT EVERYTHING TO GDA2020 (EPSG:7844) ────────────────────────
print("Reprojecting to GDA2020...")
brisbane_suburbs = brisbane_suburbs.to_crs("EPSG:7844")
vegetation = vegetation.to_crs("EPSG:7844")
print(f"Suburbs CRS: {brisbane_suburbs.crs}")
print(f"Vegetation CRS: {vegetation.crs}")
print()

# ── 4. CLIP VEGETATION TO BRISBANE BOUNDARY ───────────────────────────────
print("Clipping vegetation to Brisbane boundary...")
brisbane_boundary = brisbane_suburbs.union_all()
vegetation_brisbane = vegetation[vegetation.intersects(brisbane_boundary)].copy()
print(f"Vegetation polygons within Brisbane: {len(vegetation_brisbane)}")
print()

# ── 5. HANDLE NAN VALUES IN RASTER ────────────────────────────────────────
print("Inspecting raster...")
with rasterio.open("data/brisbane_lst.tif") as src:
    lst_data = src.read(1).astype(float)
    nodata = src.nodata
    print(f"Nodata value from file: {nodata}")
    
    # Replace nodata and zero values with nan
    if nodata is not None:
        lst_data[lst_data == nodata] = np.nan
    lst_data[lst_data <= 0] = np.nan
    lst_data[lst_data > 60] = np.nan
    lst_data[lst_data < 10] = np.nan
    
    valid_pixels = lst_data[~np.isnan(lst_data)]
    print(f"Valid pixels: {len(valid_pixels)}")
    print(f"Temperature range (cleaned): {valid_pixels.min():.1f}°C — {valid_pixels.max():.1f}°C")
    print(f"Mean temperature: {valid_pixels.mean():.1f}°C")

print()
print("=== PREPROCESSING COMPLETE ===")

# ── 6. SAVE PREPROCESSED FILES ────────────────────────────────────────────
print("Saving preprocessed files...")
brisbane_suburbs.to_file("data/brisbane_suburbs.gpkg", driver="GPKG")
vegetation_brisbane.to_file("data/vegetation_brisbane.gpkg", driver="GPKG")
print("Saved: data/brisbane_suburbs.gpkg")
print("Saved: data/vegetation_brisbane.gpkg")
print()
print("=== ALL DONE ===")