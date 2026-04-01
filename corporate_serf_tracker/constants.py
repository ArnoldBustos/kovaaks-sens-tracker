from pathlib import Path
import os

DEFAULT_STATS_PATH = (
    r"C:\Program Files (x86)\Steam\steamapps\common\FPSAimTrainer\FPSAimTrainer\stats"
)
CM_OPTIONS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
MAX_SELECTED = 5

BG = "#0b0f14"
BG2 = "#131a24"
BG3 = "#1a2330"
BORDER = "#344152"
ACCENT = "#3fbcde"
ACCENT2 = "#01986f"
WARN = "#ed2c6b"
GOLD = "#e8d84a"
TEXT = "#f5f7fa"
TEXT2 = "#aab4c0"
MUTED = "#627082"
WORST_BG = "#241019"
WORST_COL = "#ff5c93"


def get_app_data_directory():
    appdata_directory = os.getenv("APPDATA")

    if appdata_directory:
        app_directory = Path(appdata_directory) / "KovaaksSensTracker"
    else:
        app_directory = Path.home() / ".kovaaks_sens_tracker"

    app_directory.mkdir(parents=True, exist_ok=True)
    return app_directory


DATABASE_FILE = get_app_data_directory() / "corporate_serf_data.db"
