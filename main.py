from pathlib import Path

from qcm_monitor.app import create_app


if __name__ == "__main__":
    settings_path = Path(__file__).resolve().parent / "settings.ini"
    app = create_app(settings_path=settings_path)
    app.run()
