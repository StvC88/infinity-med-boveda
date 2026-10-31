"""Datos sintéticos: inventario, exclusión y lector que no importa el motor."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import terabox_local as engine
import recuperar_independiente as reader

PASSWORD = "frase publica de pruebas sinteticas"


class Improvements(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.repo, self.stage, self.out = [self.base / p for p in ("repo", "stage", "out")]
        for path in (self.repo, self.stage, self.out):
            path.mkdir()
        self.vault = engine.Vault.create(self.repo, PASSWORD, "SINTÉTICO", self.stage)
        self.plain = self.base / "ejemplo.txt"
        self.plain.write_bytes(b"demostracion sintetica\n" * 60000)
        self.entry = self.vault.add(self.plain, self.stage)

    def tearDown(self):
        self.tmp.cleanup()

    def test_independent_reader_v2(self):
        self.assertNotIn("terabox_local", reader.__dict__)
        result = reader.recover(self.repo, PASSWORD, self.out)
        self.assertEqual(result[0]["name"], self.plain.name)
        self.assertEqual((self.out / self.plain.name).read_bytes(), self.plain.read_bytes())

    def test_independent_reader_legacy_v1(self):
        h = dict(self.vault.header)
        h["version"] = 1
        del h["inventory"]
        engine.wrap(h, self.vault.key, PASSWORD)
        (self.repo / engine.HEADER).write_bytes(engine.canonical(h))
        (self.repo / engine.INVENTORY).unlink()
        opened = engine.Vault.unlock(self.repo, PASSWORD)
        self.assertFalse(opened.verify()["inventory"])
        reader.recover(self.repo, PASSWORD, self.out)
        self.assertEqual((self.out / self.plain.name).read_bytes(), self.plain.read_bytes())

    def test_missing_object_and_missing_inventory(self):
        obj = self.repo / self.entry
        saved = obj.read_bytes()
        obj.unlink()
        with self.assertRaises(engine.VaultError):
            self.vault.verify()
        with self.assertRaises(ValueError):
            reader.recover(self.repo, PASSWORD, self.out)
        obj.write_bytes(saved)
        (self.repo / engine.INVENTORY).unlink()
        with self.assertRaises(engine.VaultError):
            self.vault.verify()
        with self.assertRaises(FileNotFoundError):
            reader.recover(self.repo, PASSWORD, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_inventory_tamper(self):
        path = self.repo / engine.INVENTORY
        raw = path.read_bytes()
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
        with self.assertRaises(engine.VaultError):
            self.vault.verify()
        with self.assertRaises(Exception):
            reader.recover(self.repo, PASSWORD, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_interrupted_inventory_update_keeps_complete_object(self):
        with patch.object(self.vault, "_write_inventory", side_effect=OSError("corte simulado")):
            with self.assertRaises(OSError):
                self.vault.add(self.plain, self.stage)
        self.assertEqual(len(self.vault.entries()), 2)
        with self.assertRaises(engine.VaultError):
            self.vault.verify()
        # Ambas cargas están completas, recuperables individualmente; no se borra ninguna.
        for i, entry in enumerate(self.vault.entries()):
            dest = self.base / str(i)
            dest.mkdir()
            self.assertEqual(self.vault.restore(entry, dest).read_bytes(), self.plain.read_bytes())
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_two_processes_cannot_write_same_repository(self):
        code = "import sys; from pathlib import Path; from terabox_local import operation_lock, VaultError\ntry:\n with operation_lock(Path(sys.argv[1])): print('UNEXPECTED')\nexcept VaultError: print('LOCKED')"
        with engine.operation_lock(self.repo):
            result = subprocess.run([sys.executable, "-c", code, str(self.repo)], capture_output=True, text=True, timeout=15, cwd=Path(__file__).parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "LOCKED")
        self.assertEqual(self.vault.verify()["files"], 1)

    def test_reader_rejects_truncation_without_publishing(self):
        h, key = reader.unlock_repository(self.repo, PASSWORD)
        path = self.repo / self.entry
        path.write_bytes(path.read_bytes()[:-1])
        with self.assertRaises(Exception):
            reader.consume_object(self.repo, self.entry, h, key, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_reader_rejects_wrong_password_and_cloud_destination(self):
        with self.assertRaises(Exception):
            reader.recover(self.repo, "incorrecta", self.out)
        with self.assertRaises(ValueError):
            reader.recover(self.repo, PASSWORD, self.repo)

    def test_public_vectors(self):
        vectors = json.loads((Path(__file__).parent / "vectores-publicos.json").read_text(encoding="utf-8"))
        for vector in vectors:
            repo = self.base / ("vector-" + str(vector["version"]))
            repo.mkdir()
            for name, value in vector["files"].items():
                (repo / name).write_bytes(base64.b64decode(value))
            dest = self.base / ("vector-out-" + str(vector["version"]))
            dest.mkdir()
            reader.recover(repo, vector["password"], dest)
            self.assertEqual(hashlib.sha256((dest / vector["name"]).read_bytes()).hexdigest(), vector["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
