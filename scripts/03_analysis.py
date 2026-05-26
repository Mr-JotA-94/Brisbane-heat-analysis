import geopandas as gpd
import rasterio
import numpy as np
import pandas as pd
from rasterstats import zonal_stats

# ── 1. LOAD PREPROCESSED FILES ────────────────────────────────────────────
print("Loading preprocessed files...")
suburbs = gpd.read_file("data/brisbane_suburbs.gpkg")
vegetation = gpd.read_file("data/vegetation_brisbane.gpkg")
vegetation_projected = vegetation.to_crs("EPSG:32756")
vegetation['shape_area'] = vegetation_projected.geometry.area
print(f"Suburbs: {len(suburbs)}")
print(f"Vegetation polygons: {len(vegetation)}")
print()

# ── 2. ZONAL STATISTICS — MEAN LST PER SUBURB ─────────────────────────────
print("Calculating mean temperature per suburb...")
suburbs_4326 = suburbs.to_crs("EPSG:4326")

with rasterio.open("data/brisbane_lst.tif") as src:
    lst_data = src.read(1).astype(float)
    nodata = src.nodata
    if nodata is not None:
        lst_data[lst_data == nodata] = np.nan
    lst_data[lst_data <= 0] = np.nan
    lst_data[lst_data > 60] = np.nan
    lst_data[lst_data < 10] = np.nan
    affine = src.transform

stats = zonal_stats(
    suburbs_4326,
    lst_data,
    affine=affine,
    stats=["mean", "max"],
    nodata=np.nan
)

suburbs['lst_mean'] = [s['mean'] if s['mean'] else np.nan for s in stats]
suburbs['lst_max'] = [s['max'] if s['max'] else np.nan for s in stats]
print(f"Temperature stats calculated for {suburbs['lst_mean'].notna().sum()} suburbs")
print()

# ── 3. CANOPY COVERAGE % PER SUBURB ───────────────────────────────────────
print("Calculating canopy coverage per suburb...")

# Reproject to UTM Zone 56S for accurate area in metres
suburbs_projected = suburbs.to_crs("EPSG:32756")
vegetation_projected = vegetation.to_crs("EPSG:32756")

# Clip vegetation to each suburb boundary — prevents overlap inflation
vegetation_clipped = gpd.overlay(vegetation_projected, 
                                  suburbs_projected[['SAL_NAME21', 'geometry']], 
                                  how='intersection')

# Recalculate area after clipping
vegetation_clipped['clipped_area_m2'] = vegetation_clipped.geometry.area

# Sum clipped vegetation area per suburb
veg_area = vegetation_clipped.groupby('SAL_NAME21')['clipped_area_m2'].sum().reset_index()
veg_area.columns = ['SAL_NAME21', 'veg_area_m2']

# Suburb area in metres
suburbs['suburb_area_m2'] = suburbs_projected.geometry.area

# Merge and calculate %
suburbs = suburbs.merge(veg_area, on='SAL_NAME21', how='left')
suburbs['veg_area_m2'] = suburbs['veg_area_m2'].fillna(0)
suburbs['canopy_pct'] = (suburbs['veg_area_m2'] / suburbs['suburb_area_m2']) * 100

# Cap at 100% — anything over is a data artefact
suburbs['canopy_pct'] = suburbs['canopy_pct'].clip(upper=100)

print(f"Canopy coverage calculated")
print(f"Mean canopy coverage: {suburbs['canopy_pct'].mean():.1f}%")
print(f"Max canopy coverage: {suburbs['canopy_pct'].max():.1f}%")
print(f"Min canopy coverage: {suburbs['canopy_pct'].min():.1f}%")
print()

# ── 4. PRIORITY SCORING ───────────────────────────────────────────────────
print("Building priority scores...")

# Normalise both metrics 0-1
suburbs['heat_norm'] = (
    (suburbs['lst_mean'] - suburbs['lst_mean'].min()) /
    (suburbs['lst_mean'].max() - suburbs['lst_mean'].min())
)

# Invert canopy — low canopy = high score
suburbs['canopy_norm'] = 1 - (
    (suburbs['canopy_pct'] - suburbs['canopy_pct'].min()) /
    (suburbs['canopy_pct'].max() - suburbs['canopy_pct'].min())
)

# Equal weight — adjust later if needed
suburbs['priority_score'] = (suburbs['heat_norm'] + suburbs['canopy_norm']) / 2

# Drop rows with no temperature data
suburbs_scored = suburbs.dropna(subset=['lst_mean']).copy()
suburbs_scored = suburbs_scored.sort_values('priority_score', ascending=False)

# ── 5. OUTPUT RANKED TABLE ────────────────────────────────────────────────
print()
print("=== TOP 20 PRIORITY SUBURBS ===")
print()
top20 = suburbs_scored[[
    'SAL_NAME21', 'lst_mean', 'canopy_pct', 'priority_score'
]].head(20)
top20.columns = ['Suburb', 'Mean Temp (°C)', 'Canopy %', 'Priority Score']
top20['Mean Temp (°C)'] = top20['Mean Temp (°C)'].round(1)
top20['Canopy %'] = top20['Canopy %'].round(2)
top20['Priority Score'] = top20['Priority Score'].round(3)
print(top20.to_string(index=False))

# ── 6. SAVE RESULTS ───────────────────────────────────────────────────────
print()
print("Saving results...")
suburbs_scored.to_file("data/brisbane_scored.gpkg", driver="GPKG")
top20.to_csv("data/top20_priority_suburbs.csv", index=False)
print("Saved: data/brisbane_scored.gpkg")
print("Saved: data/top20_priority_suburbs.csv")
print()
print("=== ANALYSIS COMPLETE ===")