import os

# --------------------------------------------------------
# Base Directories
# --------------------------------------------------------
# Go three levels up from configuration/ to reach project root (ShopSync)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))

# Now build all subpaths relative to project root
DATABASE_DIR = os.path.join(BASE_DIR, "app", "modules", "database")
LOADSHEETS_DIR = os.path.join(DATABASE_DIR, "loadsheets")
LOADER_DIR = os.path.join(LOADSHEETS_DIR, "loader")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

# --------------------------------------------------------
# Database file
# --------------------------------------------------------
DB_PATH = os.path.join(DATABASE_DIR, "shopsync.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# --------------------------------------------------------
# Default files
# --------------------------------------------------------
EQUIPMENT_RELATIONSHIPS_XLSX = os.path.join(
    LOADSHEETS_DIR, "load_equipment_relationships_table_data.xlsx"
)

# Ensure directories exist
for d in [DATABASE_DIR, LOADSHEETS_DIR, LOADER_DIR, LOGS_DIR, IMAGES_DIR]:
    os.makedirs(d, exist_ok=True)
