import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verificar_producao", ROOT / "tools" / "verificar_producao.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class PreflightTests(unittest.TestCase):
    def test_schema_real_sqlite(self):
        self.assertGreaterEqual(module.validar_schema(), 6)

    def test_transaction_requires_connection_before_opening_file(self):
        source = (ROOT / "database.py").read_text(encoding="utf-8")
        method = source.split("async def transaction(self):", 1)[1].split("async def close(self):", 1)[0]
        self.assertLess(method.index("if self.conn is None:"), method.index("aiosqlite.connect(self.path"))


if __name__ == "__main__":
    unittest.main()
