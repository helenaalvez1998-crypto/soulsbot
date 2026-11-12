import ast
import unittest
from pathlib import Path


class DatabaseConcurrencySafetyTests(unittest.TestCase):
    def test_memory_transactions_are_serialized(self):
        source = Path(__file__).resolve().parents[1].joinpath("database.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        database_class = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Database"
        )
        init = next(node for node in database_class.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        transaction = next(
            node for node in database_class.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "transaction"
        )
        init_source = ast.get_source_segment(source, init) or ""
        transaction_source = ast.get_source_segment(source, transaction) or ""
        self.assertIn("self._memory_lock = asyncio.Lock()", init_source)
        self.assertIn("await self._memory_lock.acquire()", transaction_source)
        self.assertIn("self._memory_lock.release()", transaction_source)
        self.assertIn("finally:", transaction_source)
        self.assertIn("BEGIN IMMEDIATE", transaction_source)

    def test_transaction_requires_connected_database(self):
        source = Path(__file__).resolve().parents[1].joinpath("database.py").read_text(encoding="utf-8")
        self.assertIn("Database.connect() precisa ser chamado antes de transaction()", source)


if __name__ == "__main__":
    unittest.main()
