import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import tracemalloc
import unittest
from unittest.mock import patch

import terabox_local as t


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tblocal-test-")
        self.root = Path(self.temp.name)
        self.old = self.root / "old"
        self.stage = self.root / "stage"
        self.out = self.root / "out"
        self.new_dir = self.root / "new"
        for p in (self.old, self.stage, self.out, self.new_dir):
            p.mkdir()
        self.v = t.Vault.create(self.old, "actual contraseña larga", "pista pública", self.stage)

    def tearDown(self):
        self.temp.cleanup()

    def add(self, name="archivo.txt", data=b"contenido"):
        p = self.root / name
        p.write_bytes(data)
        return self.v.add(p, self.stage)

    def migrate(self):
        return self.v.migrate("actual contraseña larga", self.new_dir, "nueva contraseña larga", "otra pista", self.stage)

    def test_roundtrip_boundaries_and_empty(self):
        for n in (0, 1, t.BLOCK - 1, t.BLOCK, t.BLOCK + 1, 2 * t.BLOCK):
            with self.subTest(n=n):
                data = os.urandom(n)
                entry = self.add(f"datos-{n}.bin", data)
                self.assertEqual(self.v.metadata(entry)["name"], f"datos-{n}.bin")
                path = self.v.restore(entry, self.out)
                self.assertEqual(path.read_bytes(), data)
                self.assertEqual((self.root / path.name).read_bytes(), data)
                self.assertNotIn(path.name.encode(), (self.old / entry).read_bytes())
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_password_hint_and_bounded_parameters(self):
        with self.assertRaises(t.VaultError):
            t.Vault.unlock(self.old, "incorrecta")
        h = t.read_header(self.old)
        self.assertEqual(h["hint"], "pista pública")
        h["mem"] = 2**60
        (self.old / t.HEADER).write_text(json.dumps(h), encoding="utf-8")
        with patch.object(t.pwhash.argon2id, "kdf", side_effect=AssertionError("No debe ejecutar KDF")):
            with self.assertRaises(t.VaultError):
                t.Vault.unlock(self.old, "actual contraseña larga")

    def test_corruption_truncation_reorder_trailing_and_length(self):
        entry = self.add(data=os.urandom(2 * t.BLOCK + 1))
        path = self.old / entry
        original = path.read_bytes()
        offset = len(t.MAGIC) + 32 + 24
        frames = []
        while offset < len(original):
            size = struct.unpack(">I", original[offset:offset + 4])[0]
            frames.append(original[offset:offset + 4 + size])
            offset += 4 + size
        prefix = original[:len(t.MAGIC) + 32 + 24]
        mutations = [original[:-1], original + b"x", original[:100] + bytes([original[100] ^ 1]) + original[101:], prefix + frames[0] + frames[2] + frames[1] + b"".join(frames[3:]), prefix + struct.pack(">I", 0xFFFFFFFF)]
        for data in mutations:
            with self.subTest(length=len(data)):
                path.write_bytes(data)
                with self.assertRaises(t.VaultError):
                    self.v.restore(entry, self.out)
                self.assertEqual(list(self.out.iterdir()), [])

    def test_dangerous_names(self):
        for name in ("../x", "..\\x", "C:\\x", "x:y", "/root", ".", "..", "NUL.txt", "con .txt", "COM1", "LPT¹.txt", "x.", "x ", "x\x00y"):
            with self.subTest(name=name), self.assertRaises(t.VaultError):
                t.safe_name(name)
        # Metadatos maliciosos auténticos: también rechazados al leer.
        entry = self.add()
        path = self.old / entry
        prefix = path.read_bytes()[:len(t.MAGIC) + 32]
        state = t.sodium.crypto_secretstream_xchacha20poly1305_state()
        sh = t.sodium.crypto_secretstream_xchacha20poly1305_init_push(state, self.v.key)
        with path.open("wb") as f:
            f.write(prefix + sh)
            t.write_frame(f, state, t.canonical({"name": "../escape", "size": 0}), prefix)
            t.write_frame(f, state, b"", prefix, t.FINAL)
        with self.assertRaises(t.VaultError):
            self.v.restore(entry, self.out)
        self.assertFalse((self.root / "escape").exists())

    def test_no_plaintext_inside_vault_no_overwrite(self):
        entry = self.add()
        with self.assertRaises(t.VaultError):
            self.v.restore(entry, self.old)
        with self.assertRaises(t.VaultError):
            self.v.add(self.old / t.HEADER, self.stage)
        with self.assertRaises(t.VaultError):
            self.v.add(self.root / "archivo.txt", self.old)
        self.v.restore(entry, self.out)
        with self.assertRaises(t.VaultError):
            self.v.restore(entry, self.out)

    def test_declared_cloud_root_protects_other_sync_subfolders(self):
        cloud = self.root / "cloud"
        cloud.mkdir()
        vault_dir = cloud / "vault"
        vault_dir.mkdir()
        other = cloud / "other"
        other.mkdir()
        v = t.Vault.create(vault_dir, "frase de prueba extensa", "", self.stage).set_cloud_root(cloud)
        source = self.root / "plain.txt"
        source.write_bytes(b"datos")
        entry = v.add(source, self.stage)
        with self.assertRaises(t.VaultError):
            v.restore(entry, other)
        with self.assertRaises(t.VaultError):
            v.add(source, other)
        (other / "input.txt").write_bytes(b"x")
        with self.assertRaises(t.VaultError):
            v.add(other / "input.txt", self.stage)

    def test_cancel_restore_removes_partial(self):
        entry = self.add(data=os.urandom(t.BLOCK + 1))
        cancel = threading.Event()
        with self.assertRaises(t.Cancelled):
            self.v.restore(entry, self.out, lambda *_: cancel.set(), cancel)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_ciphertext_identity_binding(self):
        entry = self.add()
        renamed = "0" * 32 + ".tbe"
        (self.old / entry).rename(self.old / renamed)
        with self.assertRaises(t.VaultError):
            self.v.restore(renamed, self.out)
        with self.assertRaises(t.VaultError):
            self.v.metadata("../boveda.json")

    def test_cancel_and_publication_failure_clean_temps(self):
        p = self.root / "archivo.txt"
        p.write_bytes(os.urandom(t.BLOCK + 3))
        cancel = threading.Event()
        def progress(done, total):
            cancel.set()
        with self.assertRaises(t.Cancelled):
            self.v.add(p, self.stage, progress, cancel)
        self.assertEqual(self.v.entries(), [])
        self.assertEqual(list(self.stage.iterdir()), [])
        with patch.object(t.os, "rename" if os.name == "nt" else "link", side_effect=OSError("disco no compatible/lleno")):
            with self.assertRaises(OSError):
                self.v.add(p, self.stage)
        self.assertEqual(self.v.entries(), [])
        self.assertEqual(list(self.stage.iterdir()), [])

    def test_independent_rotation_and_both_passwords(self):
        old_entry = self.add(data=os.urandom(t.BLOCK + 1))
        before = {p.name: p.read_bytes() for p in self.old.iterdir()}
        new = self.migrate()
        self.assertNotEqual(new.key, self.v.key)
        self.assertNotEqual(new.header["vault"], self.v.header["vault"])
        self.assertEqual(new.header["state"], "migration-complete")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.old.iterdir()})
        old = t.Vault.unlock(self.old, "actual contraseña larga")
        new = t.Vault.unlock(self.new_dir, "nueva contraseña larga")
        self.assertEqual(old.metadata(old_entry), new.metadata(new.entries()[0]))
        dest1 = self.root / "out1"
        dest1.mkdir()
        a = old.restore(old_entry, self.out)
        b = new.restore(new.entries()[0], dest1)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        with self.assertRaises(t.VaultError):
            t.Vault.unlock(self.new_dir, "actual contraseña larga")

    def test_rotation_requires_current_password(self):
        with self.assertRaises(t.VaultError):
            self.v.migrate("incorrecta", self.new_dir, "nueva", "", self.stage)
        self.assertEqual(list(self.new_dir.iterdir()), [])

    def test_failed_migration_preserves_old_and_marks_incomplete(self):
        entry = self.add(data=b"texto seguro")
        with patch.object(t.Vault, "verify_records", side_effect=t.VaultError("verificación fallida")):
            with self.assertRaises(t.VaultError):
                self.migrate()
        self.assertEqual(t.read_header(self.new_dir)["state"], "migration-incomplete")
        self.assertEqual(self.v.restore(entry, self.out).read_bytes(), b"texto seguro")
        new = t.Vault.unlock(self.new_dir, "nueva contraseña larga")
        with self.assertRaises(t.VaultError):
            new.cleanup_previous("nueva contraseña larga", True)

    def test_cancel_migration_preserves_source(self):
        self.add(data=os.urandom(t.BLOCK + 1))
        cancel = threading.Event()
        def progress(*args):
            cancel.set()
        with self.assertRaises(t.Cancelled):
            self.v.migrate("actual contraseña larga", self.new_dir, "nueva frase larga de prueba", "", self.stage, progress, cancel)
        self.assertEqual(len(self.v.entries()), 1)
        self.assertEqual(t.read_header(self.new_dir)["state"], "migration-incomplete")
        self.assertEqual(list(self.stage.iterdir()), [])




    def test_cleanup_disabled_preserves_both_repositories(self):
        self.add()
        new = self.migrate()
        before_old = {p.name:p.read_bytes() for p in self.old.iterdir()}
        before_new = {p.name:p.read_bytes() for p in self.new_dir.iterdir()}
        for password, confirmed in [("nueva contraseña larga",True),("incorrecta",True),("nueva contraseña larga",False)]:
            with self.assertRaises(t.VaultError):
                new.cleanup_previous(password,confirmed)
        self.assertEqual(before_old,{p.name:p.read_bytes() for p in self.old.iterdir()})
        self.assertEqual(before_new,{p.name:p.read_bytes() for p in self.new_dir.iterdir()})

    def test_streaming_bounded_python_allocations(self):
        count = 80
        block = os.urandom(t.BLOCK)
        tracemalloc.start()
        try:
            entry = self.v.encrypt_chunks({"name": "grande.bin", "size": count * t.BLOCK}, (block for _ in range(count)), self.stage)
            result = self.v.restore(entry, self.out)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(result.stat().st_size, count * t.BLOCK)
        self.assertLess(peak, 12 * t.BLOCK)
        print(f"\nStreaming 80 MiB: pico de asignaciones Python {peak / t.BLOCK:.2f} MiB (no incluye memoria nativa/Argon2/Qt).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
