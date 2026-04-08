"""PluginContext — stable API surface for BaseCamp Linux plugins."""
import os
import json

from shared.config import CONFIG_DIR


class PluginContext:
    """Passed to every plugin on instantiation. Wraps app internals."""

    def __init__(self, app, plugin_manager):
        self._app = app
        self._pm = plugin_manager

    # ── i18n ──────────────────────────────────────────────────────────────────

    def T(self, key, **kwargs):
        """Translate a key using the app's current language."""
        return self._app.T(key, **kwargs)

    def register_translations(self, lang_dict):
        """Merge plugin translations into the app's language dict.
        lang_dict: {"en": {"my_key": "Label"}, "de": {"my_key": "Bezeichnung"}}
        """
        code = self._app._lang_code
        if code in lang_dict:
            self._app._lang.update(lang_dict[code])

    # ── Config ────────────────────────────────────────────────────────────────

    @property
    def config_dir(self):
        """Base config directory (~/.config/mountain-time-sync/)."""
        return CONFIG_DIR

    def load_plugin_config(self, plugin_id):
        """Load JSON config from plugins/<id>/config.json. Returns dict or {}."""
        path = os.path.join(CONFIG_DIR, "plugins", plugin_id, "config.json")
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def save_plugin_config(self, plugin_id, data):
        """Save JSON config to plugins/<id>/config.json."""
        pdir = os.path.join(CONFIG_DIR, "plugins", plugin_id)
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "config.json"), "w") as f:
            json.dump(data, f, indent=2)

    # ── GUI ───────────────────────────────────────────────────────────────────

    @property
    def panel_area(self):
        """The CTkFrame that holds all panels."""
        return self._app._panel_area

    def register_panel(self, plugin_id, label, panel_instance):
        """Register a plugin panel in the app's panel dict."""
        self._app._panels[plugin_id] = panel_instance

    def schedule(self, ms, callback):
        """Schedule a callback on the GUI main thread (wraps app.after())."""
        return self._app.after(ms, callback)

    def schedule_repeat(self, ms, callback):
        """Repeating timer on the GUI thread. Returns cancel function."""
        cancel_id = [None]

        def _loop():
            callback()
            cancel_id[0] = self._app.after(ms, _loop)

        cancel_id[0] = self._app.after(ms, _loop)
        return lambda: self._app.after_cancel(cancel_id[0])

    # ── Device access ─────────────────────────────────────────────────────────

    def get_displaypad(self):
        """Return the DisplayPadPanel instance, or None."""
        return getattr(self._app, "_displaypad_panel", None)

    def get_keyboard_panel(self):
        """Return the active keyboard panel instance."""
        return self._app._panels.get(self._app._kb_panel_id)

    def push_displaypad_image(self, key_index, pil_image):
        """Upload a PIL Image to a DisplayPad button (0-11). Thread-safe.
        The image will be resized to 102x102 and converted to BGR automatically.
        """
        dp = self.get_displaypad()
        if dp and hasattr(dp, "push_plugin_image"):
            dp.push_plugin_image(key_index, pil_image)

    # ── Action registration ───────────────────────────────────────────────────

    def register_action_type(self, type_id, label, handler):
        """Register a new button action type.
        type_id: internal name (e.g. "led_notify")
        label:   display name (e.g. "LED Notification")
        handler: callable(action_value) — called in a daemon thread on button press
        """
        self._pm._action_types[type_id] = {
            "label": label,
            "handler": handler,
        }
