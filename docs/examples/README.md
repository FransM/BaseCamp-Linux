# Example plugins

The plugin guide, [PLUGINS.md](../PLUGINS.md), prints these in full. They live
here as well so you can copy a working folder instead of retyping a code block.

| Folder    | What it is                                                       |
|-----------|------------------------------------------------------------------|
| `led_api` | Service plugin: keyboard LED control over a Unix socket, plus `ledctl.py`, the companion script that talks to it |

To try one:

```bash
cp -r docs/examples/led_api ~/.config/mountain-time-sync/plugins/
```

Then restart BaseCamp. The plugin screen lists it, and you can enable, disable
or remove it there like any other plugin.

These are teaching material, not shipped features: they are not installed with
the app and they are not in the plugin index. For plugins meant to be installed
and updated, see
[basecamp-plugins](https://github.com/ramisotti13-eng/basecamp-plugins).
