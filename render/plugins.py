"""Plugin system — custom post-processing and behavior extensions.

Allows external Python scripts to hook into the renderer pipeline
for custom post-processing effects, expression triggers, and avatar behaviors.
"""
import os
import sys
import importlib
import importlib.util
import logging
import threading

_log = logging.getLogger("karin.plugins")


class PluginBase:
    """Base class for all Karin plugins."""

    name: str = "unnamed_plugin"
    version: str = "1.0.0"
    description: str = ""

    def __init__(self):
        self._renderer = None
        self._enabled = True

    def on_load(self, renderer):
        """Called when plugin is loaded. Use to initialize resources."""
        self._renderer = renderer

    def on_unload(self):
        """Called when plugin is unloaded. Use to cleanup resources."""
        pass

    def on_frame_start(self, dt: float):
        """Called at the start of each frame."""
        pass

    def on_frame_end(self):
        """Called at the end of each frame."""
        pass

    def on_model_loaded(self, model_path: str):
        """Called when a model is loaded."""
        pass

    def on_expression(self, expression_name: str, weight: float):
        """Called when an expression is triggered."""
        pass

    def on_tracking_update(self, tracking_data: dict):
        """Called when tracking data is received."""
        pass

    def on_render(self, scene, camera):
        """Called during render. Can add custom objects to scene."""
        pass

    def on_post_process(self, texture, width: int, height: int):
        """Called after scene render. Can apply custom post-processing.

        Args:
            texture: GPU texture handle
            width: Texture width
            height: Texture height
        Returns:
            Modified texture or None to skip
        """
        return None

    def get_config_schema(self) -> dict:
        """Return config schema for UI generation."""
        return {}


class PluginManager:
    """Load, manage, and dispatch to plugins."""

    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}
        self._plugin_dirs: list[str] = []
        self._lock = threading.Lock()
        self._renderer = None

    def set_renderer(self, renderer):
        self._renderer = renderer
        with self._lock:
            for plugin in self._plugins.values():
                try:
                    plugin.on_load(renderer)
                except Exception as e:
                    _log.warning("Plugin '%s' on_load error: %s", plugin.name, e)

    def add_plugin_dir(self, path: str):
        if path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def load_plugin(self, path: str) -> bool:
        try:
            spec = importlib.util.spec_from_file_location("plugin_" + os.path.basename(path), path)
            if spec is None or spec.loader is None:
                _log.warning("Plugin: cannot load spec from %s", path)
                return False
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                        issubclass(attr, PluginBase) and
                        attr is not PluginBase):
                    plugin_class = attr
                    break

            if plugin_class is None:
                _log.warning("Plugin: no PluginBase subclass found in %s", path)
                return False

            instance = plugin_class()
            with self._lock:
                self._plugins[instance.name] = instance
            _log.info("Plugin: loaded '%s' v%s from %s", instance.name, instance.version, path)
            return True
        except Exception as e:
            _log.error("Plugin: failed to load %s: %s", path, e)
            return False

    def load_all(self):
        for d in self._plugin_dirs:
            if not os.path.isdir(d):
                continue
            for fname in os.listdir(d):
                if fname.endswith(".py") and not fname.startswith("_"):
                    self.load_plugin(os.path.join(d, fname))

    def unload_plugin(self, name: str):
        with self._lock:
            plugin = self._plugins.pop(name, None)
        if plugin:
            try:
                plugin.on_unload()
            except Exception as e:
                _log.warning("Plugin '%s' on_unload error: %s", name, e)
            _log.info("Plugin: unloaded '%s'", name)

    def dispatch(self, event: str, *args, **kwargs):
        with self._lock:
            plugins = list(self._plugins.values())
        for plugin in plugins:
            if not plugin._enabled:
                continue
            handler = getattr(plugin, event, None)
            if handler and callable(handler):
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    _log.warning("Plugin '%s' %s error: %s", plugin.name, event, e)

    @property
    def plugin_names(self) -> list[str]:
        with self._lock:
            return list(self._plugins.keys())

    def get_plugin(self, name: str) -> PluginBase | None:
        with self._lock:
            return self._plugins.get(name)
