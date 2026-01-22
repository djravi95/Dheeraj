import geopandas as gpd
import folium
import numpy as np
from shapely.geometry import box

# ==================================================
# 1. Load Hyderabad building footprints
# ==================================================
buildings = gpd.read_file("Urban Density Mapping/data/hyderabad_buildings.geojson")

if buildings.crs is None:
    buildings = buildings.set_crs(epsg=4326)

buildings = buildings.to_crs(epsg=3857)

# ==================================================
# 2. Convert buildings to centroids
# ==================================================
buildings["centroid"] = buildings.geometry.centroid
points = buildings.set_geometry("centroid")

# ==================================================
# 3. Create grid (500m x 500m)
# ==================================================
grid_size = 500

minx, miny, maxx, maxy = points.total_bounds

x_coords = np.arange(minx, maxx, grid_size)
y_coords = np.arange(miny, maxy, grid_size)

grid_cells = [
    box(x, y, x + grid_size, y + grid_size)
    for x in x_coords
    for y in y_coords
]

grid = gpd.GeoDataFrame(geometry=grid_cells, crs=points.crs)

# ==================================================
# 4. Density calculation
# ==================================================
joined = gpd.sjoin(points, grid, how="left", predicate="within")
density = joined.groupby("index_right").size()

grid["density"] = density
grid["density"] = grid["density"].fillna(0)

# ==================================================
# 5. Remove empty cells
# ==================================================
grid = grid[grid["density"] > 0]

# ==================================================
# 6. Quantile-based classification
# ==================================================
q70 = grid["density"].quantile(0.70)
q90 = grid["density"].quantile(0.90)

def classify_density(d):
    if d >= q90:
        return "high"
    elif d >= q70:
        return "medium"
    else:
        return "low"

grid["class"] = grid["density"].apply(classify_density)

# ==================================================
# 7. Suppress low-density cells
# ==================================================
grid = grid[grid["class"] != "low"]

# ==================================================
# 8. Load Hyderabad boundary
# ==================================================
boundary = gpd.read_file("Urban Density Mapping/data/hyderabad_boundary_admin8.geojson")

if boundary.crs is None:
    boundary = boundary.set_crs(epsg=4326)

# Convert everything to WGS84 for Folium
grid_wgs84 = grid.to_crs(epsg=4326)

# ==================================================
# 9. Create map
# ==================================================
m = folium.Map(
    location=[17.45, 78.45],
    zoom_start=11,
    tiles="CartoDB positron"
)

# ==================================================
# 10. Draw density grid
# ==================================================
color_map = {
    "high": "red",
    "medium": "orange"
}

sample_size = min(2000, len(grid_wgs84))
sample = grid_wgs84.sample(sample_size)

for _, row in sample.iterrows():
    folium.GeoJson(
        row.geometry,
        style_function=lambda x, c=color_map[row["class"]]: {
            "fillColor": c,
            "color": None,
            "fillOpacity": 0.65,
        },
        tooltip=f"Density: {int(row['density'])}"
    ).add_to(m)

# ==================================================
# 11. Draw THICK Hyderabad boundary (visual anchor)
# ==================================================
folium.GeoJson(
    boundary,
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "black",
        "weight": 6,   # 👈 thick border
    },
    name="Hyderabad Boundary"
).add_to(m)

# ==================================================
# 12. Save map
# ==================================================
m.save("hyderabad_urban_density_intelligence.html")
print("Saved: hyderabad_urban_density_intelligence.html")