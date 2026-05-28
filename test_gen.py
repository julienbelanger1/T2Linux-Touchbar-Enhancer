import sys
sys.path.insert(0, "src")
import tomllib
from touchbar_enhancer.helpers import build_config_toml
from touchbar_enhancer.main import PRESETS

media_specs = []
for p in PRESETS:
    media_specs.append({
        "type": p.get("type", "Icon"),
        "val": p.get("icon", p.get("name", "")),
        "action": p.get("action", ""),
        "stretch": p.get("stretch", 1)
    })

toml_str = build_config_toml(
    media_specs,
    [],
    media_layer_default=True,
    show_button_outlines=True,
    enable_pixel_shift=False,
    adaptive_brightness=True,
    font_template=":bold"
)

try:
    print(toml_str)
    parsed = tomllib.loads(toml_str)
    print("Parsed successfully!")
except Exception as e:
    print(f"Error parsing: {e}")
