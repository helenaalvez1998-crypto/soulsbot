"""Garante que todo canal criado pelo assistente automático seja configurável no /adm."""
import unittest

from admin_config import KEYS, LABELS, SECTIONS


class AdminConfigMappingTests(unittest.TestCase):
    def test_auto_setup_channels_have_mapping_and_label(self):
        expected = {
            "mod_channel", "platinas_channel", "zerados_channel", "soulslike_channel",
            "perfis_channel", "video_channel", "live_channel", "games_channel",
            "promos_channel", "colizeu_channel", "nara_channel",
        }
        self.assertTrue(expected.issubset(KEYS))
        self.assertTrue(expected.issubset(LABELS))
        self.assertTrue(expected.issubset(set(SECTIONS["channels"])))

    def test_channel_keys_map_to_existing_config_attributes(self):
        import config
        for key in SECTIONS["channels"]:
            attr, cast = KEYS[key]
            self.assertTrue(hasattr(config, attr), f"{key} -> config.{attr} ausente")
            self.assertIs(cast, int)


if __name__ == "__main__":
    unittest.main()
