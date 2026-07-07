from pathlib import Path

from .app import create_app


def main() -> None:
    settings_path = Path(__file__).resolve().parent.parent / "settings.ini"
    app = create_app(settings_path=settings_path)
    app.run()


if __name__ == "__main__":
    main()
