import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime_paths import get_data_dir, get_state_path


class RuntimePathTests(unittest.TestCase):
    def test_data_dir_respects_environment(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"DATA_DIR": tmp}):
            self.assertEqual(get_data_dir(), Path(tmp))

    def test_state_files_default_inside_persistent_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"DATA_DIR": tmp}, clear=False):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("TAVILY_CIRCUIT_STATE_FILE", None)
                self.assertEqual(get_state_path("TAVILY_CIRCUIT_STATE_FILE", "tavily_circuit.json"), Path(tmp) / "tavily_circuit.json")

    def test_state_file_environment_override_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            override = Path(tmp) / "custom-state.json"
            with patch.dict(os.environ, {"TAVILY_CIRCUIT_STATE_FILE": str(override)}):
                self.assertEqual(get_state_path("TAVILY_CIRCUIT_STATE_FILE", "tavily_circuit.json"), override)


if __name__ == "__main__":
    unittest.main()
