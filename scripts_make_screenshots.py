from pathlib import Path
import subprocess

from corporate_serf_tracker.app import App


PROJECT_ROOT = Path(__file__).resolve().parent
SCREENSHOT_DIR = PROJECT_ROOT / 'assets' / 'screenshots'
SAMPLE_DIR = PROJECT_ROOT / 'sample_data' / 'kovaaks_stats'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def capture_app_state(app: App, output_name: str):
  app.update_idletasks()
  app.update()
  subprocess.run([
    'scrot',
    str(SCREENSHOT_DIR / output_name),
  ], check=True)


app = App()
app.folder_path = str(SAMPLE_DIR)
app._load_folder()
app.selected = [
  '1wall6targets TE',
  'Close Long Strafes Invincible',
  'Smoothbot Voltaic Easy',
]
app.sel_label.config(text=f'{len(app.selected)} / 5 selected')
app._refresh_main()
app.update_idletasks()
app.after(400, lambda: capture_app_state(app, 'dashboard-overview.png'))


def second_shot():
  app.cm_range_min.set('30')
  app.cm_range_max.set('55')
  app._refresh_main(restore_tab='Close Long Strafes Invincible')
  capture_app_state(app, 'dashboard-range-filter.png')
  app.destroy()

app.after(900, second_shot)
app.mainloop()
