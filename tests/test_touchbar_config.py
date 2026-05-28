import sys
import tomllib
import unittest

sys.path.insert(0, "src")

from touchbar_enhancer import helpers as touchbar_config_helpers


class TouchbarConfigSerializationTests(unittest.TestCase):
    def test_standard_media_matches_upstream_default(self):
        models = touchbar_config_helpers.standard_media_layout()

        self.assertEqual(
            models,
            [
                {"type": "Icon", "val": "brightness_low", "action": "BrightnessDown", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "brightness_high", "action": "BrightnessUp", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "mic_off", "action": "MicMute", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "search", "action": "Search", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "backlight_low", "action": "IllumDown", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "backlight_high", "action": "IllumUp", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "fast_rewind", "action": "PreviousSong", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "play_pause", "action": "PlayPause", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "fast_forward", "action": "NextSong", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "volume_off", "action": "Mute", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "volume_down", "action": "VolumeDown", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
                {"type": "Icon", "val": "volume_up", "action": "VolumeUp", "stretch": 1, "custom_icon_path": None, "spacer_type": "flexible"},
            ],
        )

    def test_generated_toml_roundtrips_for_standard_media(self):
        toml_text = touchbar_config_helpers.build_config_toml(
            touchbar_config_helpers.standard_media_layout(),
            [],
            media_layer_default=True,
            show_button_outlines=True,
            enable_pixel_shift=False,
            adaptive_brightness=True,
            font_template=":bold",
        )

        config = tomllib.loads(toml_text)

        self.assertTrue(config["MediaLayerDefault"])
        self.assertEqual(config["MediaLayerKeys"][0]["Icon"], "brightness_low")
        self.assertEqual(config["MediaLayerKeys"][-1]["Action"], "VolumeUp")

    def test_cupertino_icon_is_prefixed_while_builtin_is_not(self):
        # delete_solid is Cupertino only; brightness_low is built-in
        layout = [
            {"type": "Icon", "val": "delete_solid", "action": "Delete", "stretch": 1},
            {"type": "Icon", "val": "brightness_low", "action": "BrightnessDown", "stretch": 1},
        ]
        toml_text = touchbar_config_helpers.build_config_toml(
            layout,
        [],
            media_layer_default=True,
            show_button_outlines=True,
            enable_pixel_shift=False,
            adaptive_brightness=True,
            font_template=":bold",
        )
        config = tomllib.loads(toml_text)
        self.assertEqual(config["MediaLayerKeys"][0]["Icon"], "cupertino_delete_solid")
        self.assertEqual(config["MediaLayerKeys"][1]["Icon"], "brightness_low")

    def test_multi_key_combo_formatting(self):
        layout = [
            {"type": "Icon", "val": "terminal", "action": "LeftCtrl, LeftAlt, T", "stretch": 1},
            {"type": "Icon", "val": "lock_fill", "action": ["LeftMeta", "L"], "stretch": 1},
        ]
        toml_text = touchbar_config_helpers.build_config_toml(
            layout,
        [],
            media_layer_default=True,
            show_button_outlines=True,
            enable_pixel_shift=False,
            adaptive_brightness=True,
            font_template=":bold",
        )
        config = tomllib.loads(toml_text)
        self.assertEqual(config["MediaLayerKeys"][0]["Action"], ["LeftCtrl", "LeftAlt", "T"])
        self.assertEqual(config["MediaLayerKeys"][1]["Action"], ["LeftMeta", "L"])

    def test_spacer_formatting(self):
        layout = [
            {"type": "Spacer", "spacer_type": "small", "stretch": 1},
            {"type": "Spacer", "spacer_type": "large", "stretch": 1},
            {"type": "Spacer", "spacer_type": "flexible", "stretch": 1},
        ]
        toml_text = touchbar_config_helpers.build_config_toml(
            layout,
        [],
            media_layer_default=True,
            show_button_outlines=True,
            enable_pixel_shift=False,
            adaptive_brightness=True,
            font_template=":bold",
        )
        config = tomllib.loads(toml_text)
        keys = config["MediaLayerKeys"]
        self.assertNotIn("Text", keys[0])
        self.assertEqual(keys[0]["Stretch"], 1)
        self.assertNotIn("Text", keys[1])
        self.assertEqual(keys[1]["Stretch"], 2)
        self.assertNotIn("Text", keys[2])
        self.assertEqual(keys[2]["Stretch"], 5)



if __name__ == "__main__":
    unittest.main()
