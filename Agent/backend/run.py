import os
import sys

# Ensure local lib directory is on sys.path for bundled dependencies in AppSail
lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
if os.path.exists(lib_dir) and lib_dir not in sys.path:
    sys.path.insert(0, lib_dir)

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT", os.getenv("PORT", 5100)))
    # Try running with Gunicorn for concurrency if available, otherwise fallback to app.run
    try:
        from gunicorn.app.base import BaseApplication

        class StandaloneApplication(BaseApplication):
            def __init__(self, application, options=None):
                self.options = options or {}
                self.application = application
                super().__init__()

            def load_config(self):
                for key, value in self.options.items():
                    if key in self.cfg.settings and value is not None:
                        self.cfg.set(key.lower(), value)

            def load(self):
                return self.application

        options = {
            "bind": f"0.0.0.0:{port}",
            "workers": 2,
            "timeout": 120,
        }
        StandaloneApplication(app, options).run()
    except Exception as exc:
        print(f"Starting with Flask server on port {port} (Gunicorn fallback: {exc})", flush=True)
        app.run(host="0.0.0.0", port=port, debug=False)
