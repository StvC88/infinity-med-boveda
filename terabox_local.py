"""Prototipo local: Python 3.11+, PyNaCl, PySide6. Sin red ni API TeraBox."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
import uuid
from contextlib import contextmanager
from functools import wraps

from nacl import bindings as sodium
from nacl import pwhash, utils
from nacl.exceptions import CryptoError

BLOCK = 1024 * 1024
MAGIC = b"TBLOCAL1"
HEADER = "boveda.json"
MAX_HEADER = 8192
META_MAX = 4096
OPS = 3
MEM = 64 * 1024 * 1024
ABYTES = sodium.crypto_secretstream_xchacha20poly1305_ABYTES
FINAL = sodium.crypto_secretstream_xchacha20poly1305_TAG_FINAL
MESSAGE = sodium.crypto_secretstream_xchacha20poly1305_TAG_MESSAGE
ENTRY = re.compile(r"^[0-9a-f]{32}\.tbe$")
RECEIPT = "rotacion.tbr"
MAX_FILES = 10000
INVENTORY = "inventario.tbi"


@contextmanager
def operation_lock(folder):
    """Exclusión entre procesos del mismo equipo; no es un bloqueo distribuido."""
    identity = hashlib.sha256(os.path.normcase(str(safe_path(folder))).encode()).hexdigest()
    path = Path(tempfile.gettempdir()) / ("infinity-med-" + identity + ".lock")
    outside(path, safe_path(folder))
    f = path.open("a+b")
    locked = False
    try:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b"0")
            f.flush()
        f.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise VaultError("Otra operación está usando esta bóveda en este equipo.") from exc
        yield
    finally:
        if locked:
            f.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def serialized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with operation_lock(self.folder):
            return method(self, *args, **kwargs)
    return wrapped


class VaultError(Exception):
    pass


class Cancelled(VaultError):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled("Operación cancelada; los archivos ya completados se conservan.")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def b64(value):
    return base64.b64encode(value).decode("ascii")


def unb64(value, length):
    if not isinstance(value, str) or len(value) > 256:
        raise VaultError("Encabezado no válido.")
    try:
        result = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise VaultError("Base64 no válido.") from exc
    if len(result) != length:
        raise VaultError("Longitud de encabezado no válida.")
    return result


def safe_path(path, directory=False):
    """Rechaza enlaces y junctions existentes antes de resolver la ruta."""
    p = Path(os.path.abspath(path))
    for part in (p, *p.parents):
        if part.exists() or part.is_symlink():
            s = part.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s, "st_file_attributes", 0) & 0x400:
                raise VaultError("No se admiten enlaces simbólicos ni junctions: " + str(part))
    if directory and not p.is_dir():
        raise VaultError("La carpeta debe existir: " + str(p))
    return p.resolve()


def inside(path, parent):
    return path == parent or parent in path.parents


def outside(path, vault):
    p = safe_path(path)
    if inside(p, vault):
        raise VaultError("El texto claro y los temporales deben quedar fuera de la carpeta cifrada.")
    return p


def safe_name(name):
    if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 800:
        raise VaultError("Nombre no válido.")
    if name in (".", "..") or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name):
        raise VaultError("Nombre peligroso rechazado.")
    if name.endswith((".", " ")) or name.split(".")[0].rstrip(" ").upper() in {
        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
        *(f"COM{x}" for x in "123456789¹²³"), *(f"LPT{x}" for x in "123456789¹²³"),
    }:
        raise VaultError("Nombre reservado de Windows rechazado.")
    return name


def stage_dir(path, vault):
    p = outside(path, vault)
    safe_path(p, directory=True)
    if inside(vault, p):
        raise VaultError("Use una carpeta temporal separada, no una carpeta antecesora de la bóveda.")
    if p.stat().st_dev != vault.stat().st_dev:
        raise VaultError("Temporales y bóveda deben estar en el mismo volumen (NTFS recomendado).")
    return p


def temp_file(folder, suffix=".tmp"):
    fd, name = tempfile.mkstemp(prefix=".tblocal-", suffix=suffix, dir=folder)
    return Path(name), os.fdopen(fd, "wb")


def sync_file(f):
    f.flush()
    os.fsync(f.fileno())


def publish(temp, target):
    """Enlace atómico sin sobrescritura. Nunca copiar un parcial al destino."""
    safe_path(target.parent, directory=True)
    if target.exists() or target.is_symlink():
        raise VaultError("El destino ya existe; no se sobrescribe: " + target.name)
    if os.name == "nt":
        os.rename(temp, target)  # Windows: atómico en el mismo volumen, falla si existe.
    else:
        os.link(temp, target)
        temp.unlink()


def read_exact(f, n):
    data = f.read(n)
    if len(data) != n:
        raise VaultError("Archivo truncado.")
    return data


def file_digest(path, cancel=None):
    digest = hashlib.sha256()
    with safe_path(path).open("rb") as f:
        while True:
            check_cancel(cancel)
            data = f.read(BLOCK)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def write_frame(f, state, data, ad, tag=MESSAGE):
    encrypted = sodium.crypto_secretstream_xchacha20poly1305_push(state, data, ad, tag)
    f.write(struct.pack(">I", len(encrypted)))
    f.write(encrypted)


def read_frame(f, state, ad, limit):
    n = struct.unpack(">I", read_exact(f, 4))[0]
    if not ABYTES <= n <= limit + ABYTES:
        raise VaultError("Tamaño de bloque fuera de límites.")
    try:
        return sodium.crypto_secretstream_xchacha20poly1305_pull(state, read_exact(f, n), ad)
    except CryptoError as exc:
        raise VaultError("Autenticación fallida: archivo alterado o clave incorrecta.") from exc


def read_header(folder):
    p = safe_path(Path(folder) / HEADER)
    with p.open("rb") as f:
        data = f.read(MAX_HEADER + 1)
    if len(data) > MAX_HEADER:
        raise VaultError("Encabezado demasiado grande.")
    try:
        h = json.loads(data)
        base_fields = {"version", "vault", "salt", "ops", "mem", "hint", "state", "nonce", "wrapped"}
        if not isinstance(h, dict) or set(h) != (base_fields | ({"inventory"} if h.get("version") == 2 else set())):
            raise ValueError()
        if type(h["version"]) is not int or h["version"] not in (1, 2) or type(h["ops"]) is not int or h["ops"] != OPS or type(h["mem"]) is not int or h["mem"] != MEM:
            raise ValueError()
        if h["version"] == 2 and h["inventory"] != "v1":
            raise ValueError()
        if not isinstance(h["vault"], str) or not re.fullmatch(r"[0-9a-f]{32}", h["vault"]):
            raise ValueError()
        if not isinstance(h["hint"], str) or len(h["hint"]) > 300 or h["state"] not in ("ready", "migration-incomplete", "migration-complete"):
            raise ValueError()
        unb64(h["salt"], 16)
        unb64(h["nonce"], 24)
        unb64(h["wrapped"], 48)
        return h
    except (ValueError, TypeError, KeyError) as exc:
        raise VaultError("Formato o parámetros de encabezado no admitidos.") from exc


def header_ad(h):
    return canonical({k: v for k, v in h.items() if k not in ("nonce", "wrapped")})


def derive(password, h):
    if not isinstance(password, str) or not password or len(password.encode("utf-8")) > 1024:
        raise VaultError("Introduzca una contraseña de 1 a 1024 bytes.")
    return pwhash.argon2id.kdf(32, password.encode("utf-8"), unb64(h["salt"], 16), opslimit=OPS, memlimit=MEM)


def wrap(h, key, password):
    nonce = utils.random(24)
    h["nonce"] = b64(nonce)
    h["wrapped"] = b64(sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(key, header_ad(h), nonce, derive(password, h)))


class Vault:
    def __init__(self, folder, header, key):
        self.folder = safe_path(folder, directory=True)
        self.header = header
        self.key = key
        self.cloud_root = self.folder

    def set_cloud_root(self, root):
        root = safe_path(root, directory=True)
        if not inside(self.folder, root):
            raise VaultError("La bóveda debe estar dentro del área sincronizada declarada.")
        self.cloud_root = root
        return self

    @classmethod
    def create(cls, folder, password, hint, staging, state="ready"):
        with operation_lock(folder):
            return cls._create(folder, password, hint, staging, state)

    @classmethod
    def _create(cls, folder, password, hint, staging, state="ready"):
        folder = safe_path(folder, directory=True)
        if any(folder.iterdir()):
            raise VaultError("Para crear una bóveda use una carpeta vacía.")
        staging = stage_dir(staging, folder)
        if len(hint) > 300:
            raise VaultError("La pista admite hasta 300 caracteres.")
        h = {"version": 2, "inventory": "v1", "vault": uuid.uuid4().hex, "salt": b64(utils.random(16)), "ops": OPS, "mem": MEM, "hint": hint, "state": state}
        key = utils.random(32)
        wrap(h, key, password)
        temp, f = temp_file(staging)
        try:
            with f:
                f.write(canonical(h))
                sync_file(f)
            publish(temp, folder / HEADER)
        finally:
            temp.unlink(missing_ok=True)
        vault = cls(folder, h, key)
        vault._write_inventory({}, staging)
        return vault

    @classmethod
    def unlock(cls, folder, password):
        folder = safe_path(folder, directory=True)
        h = read_header(folder)  # Valida recursos ANTES de Argon2id.
        try:
            key = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(unb64(h["wrapped"], 48), header_ad(h), unb64(h["nonce"], 24), derive(password, h))
        except CryptoError as exc:
            raise VaultError("Contraseña incorrecta o encabezado alterado.") from exc
        return cls(folder, h, key)

    def entries(self):
        names = []
        for p in self.folder.iterdir():
            if ENTRY.fullmatch(p.name):
                names.append(p.name)
                if len(names) > MAX_FILES:
                    raise VaultError("El prototipo admite hasta 10 000 archivos por bóveda.")
        return sorted(names)

    def _read_inventory(self):
        path = safe_path(self.folder / INVENTORY)
        if not path.exists():
            if self.header["version"] >= 2:
                raise VaultError("Falta el inventario requerido. Restaure o sincronice el repositorio completo.")
            return None  # Compatibilidad v1 anterior: no detecta objetos desaparecidos.
        with path.open("rb") as f:
            raw = f.read(2 * 1024 * 1024 + 1)
        if not 40 <= len(raw) <= 2 * 1024 * 1024:
            raise VaultError("Inventario fuera de límites.")
        try:
            data = json.loads(sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(raw[24:], b"inventory-v1" + bytes.fromhex(self.header["vault"]), raw[:24], self.key))
            if not isinstance(data, dict) or len(data) > MAX_FILES:
                raise ValueError()
            for entry, digest in data.items():
                if not ENTRY.fullmatch(entry) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise ValueError()
            return data
        except (CryptoError, ValueError, TypeError) as exc:
            raise VaultError("Inventario alterado o inválido.") from exc

    def _write_inventory(self, records, staging):
        nonce = utils.random(24)
        raw = nonce + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(canonical(records), b"inventory-v1" + bytes.fromhex(self.header["vault"]), nonce, self.key)
        temp, out = temp_file(staging)
        try:
            with out:
                out.write(raw)
                sync_file(out)
            os.replace(temp, self.folder / INVENTORY)
        finally:
            temp.unlink(missing_ok=True)

    @serialized
    def verify(self, progress=None, cancel=None):
        records = self._read_inventory()
        entries = self.entries()
        if records is not None and sorted(records) != entries:
            raise VaultError("Faltan archivos o hay objetos no registrados. Conserve la bóveda y revise la sincronización; no se eliminará nada.")
        for i, entry in enumerate(entries):
            f, state, ad, meta = self.reader(entry)
            with f:
                for _ in self.chunks(f, state, ad, meta["size"], cancel):
                    pass
            if records is not None and file_digest(self.folder / entry, cancel) != records[entry]:
                raise VaultError("Un archivo no coincide con el inventario autenticado.")
            if progress:
                progress(i + 1, len(entries))
        return {"files": len(entries), "inventory": records is not None}

    def reader(self, entry):
        if not isinstance(entry, str) or not ENTRY.fullmatch(entry):
            raise VaultError("Identificador no válido.")
        path = safe_path(self.folder / entry)
        try:
            f = path.open("rb")
        except OSError as exc:
            raise VaultError("El archivo cifrado no está accesible localmente. Descárguelo o sincronícelo con su cliente de nube y reintente.") from exc
        try:
            prefix = read_exact(f, len(MAGIC) + 32)
            expected = MAGIC + bytes.fromhex(self.header["vault"]) + bytes.fromhex(entry[:-4])
            if prefix != expected:
                raise VaultError("Archivo de otra bóveda o formato no válido.")
            state = sodium.crypto_secretstream_xchacha20poly1305_state()
            sodium.crypto_secretstream_xchacha20poly1305_init_pull(state, read_exact(f, 24), self.key)
            metadata, tag = read_frame(f, state, prefix, META_MAX)
            if tag != MESSAGE:
                raise VaultError("Metadatos no válidos.")
            try:
                meta = json.loads(metadata)
                if not isinstance(meta, dict) or set(meta) != {"name", "size"}:
                    raise ValueError()
                safe_name(meta["name"])
                if type(meta["size"]) is not int or not 0 <= meta["size"] <= 2**63 - 1:
                    raise ValueError()
            except (ValueError, TypeError, KeyError) as exc:
                raise VaultError("Metadatos no válidos.") from exc
            return f, state, prefix, meta
        except BaseException:
            f.close()
            raise

    def metadata(self, entry):
        f, _, _, meta = self.reader(entry)
        f.close()
        return meta  # Sólo cabecera autenticada; la recuperación verifica el contenido entero.

    def chunks(self, f, state, ad, size, cancel=None):
        total = 0
        while True:
            check_cancel(cancel)
            data, tag = read_frame(f, state, ad, BLOCK)
            if tag == FINAL:
                if data or total != size or f.read(1):
                    raise VaultError("Fin, tamaño o datos posteriores no válidos.")
                return
            if tag != MESSAGE or not data or total + len(data) > size:
                raise VaultError("Bloque no válido.")
            total += len(data)
            yield data

    @serialized
    def encrypt_chunks(self, meta, chunks, staging, progress=None, cancel=None):
        safe_name(meta["name"])
        outside(staging, self.cloud_root)
        if len(self.entries()) >= MAX_FILES:
            raise VaultError("Límite de 10 000 archivos por bóveda alcanzado.")
        staging = stage_dir(staging, self.folder)
        inventory = self._read_inventory()
        if inventory is not None and sorted(inventory) != self.entries():
            raise VaultError("El inventario no coincide: revise archivos faltantes o una operación interrumpida antes de agregar.")
        entry = uuid.uuid4().hex + ".tbe"
        prefix = MAGIC + bytes.fromhex(self.header["vault"]) + bytes.fromhex(entry[:-4])
        state = sodium.crypto_secretstream_xchacha20poly1305_state()
        stream_header = sodium.crypto_secretstream_xchacha20poly1305_init_push(state, self.key)
        temp, out = temp_file(staging)
        total = 0
        try:
            with out:
                out.write(prefix + stream_header)
                write_frame(out, state, canonical(meta), prefix)
                for data in chunks:
                    check_cancel(cancel)
                    if not 0 < len(data) <= BLOCK:
                        raise VaultError("Bloque de entrada no válido.")
                    write_frame(out, state, data, prefix)
                    total += len(data)
                    if progress:
                        progress(total, meta["size"])
                if total != meta["size"]:
                    raise VaultError("El tamaño del archivo cambió durante la lectura.")
                check_cancel(cancel)
                write_frame(out, state, b"", prefix, FINAL)
                sync_file(out)
            publish(temp, self.folder / entry)
            if inventory is not None:
                inventory[entry] = file_digest(self.folder / entry, cancel)
                self._write_inventory(inventory, staging)
            return entry
        finally:
            temp.unlink(missing_ok=True)

    def add(self, source, staging, progress=None, cancel=None):
        source = outside(source, self.cloud_root)
        if not source.is_file():
            raise VaultError("Seleccione un archivo regular.")
        safe_name(source.name)
        with source.open("rb") as f:
            before = os.fstat(f.fileno())
            def blocks():
                while True:
                    check_cancel(cancel)
                    data = f.read(BLOCK)
                    if not data:
                        break
                    yield data
                after = os.fstat(f.fileno())
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise VaultError("El archivo cambió mientras se cifraba.")
            return self.encrypt_chunks({"name": source.name, "size": before.st_size}, blocks(), staging, progress, cancel)

    @serialized
    def restore(self, entry, destination, progress=None, cancel=None):
        destination = outside(destination, self.cloud_root)
        safe_path(destination, directory=True)
        f, state, ad, meta = self.reader(entry)
        temp = None
        try:
            target = destination / safe_name(meta["name"])
            if target.exists() or target.is_symlink():
                raise VaultError("Ya existe un archivo con ese nombre en el destino.")
            temp, out = temp_file(destination, ".partial")
            with f, out:
                total = 0
                for data in self.chunks(f, state, ad, meta["size"], cancel):
                    out.write(data)
                    total += len(data)
                    if progress:
                        progress(total, meta["size"])
                sync_file(out)
            check_cancel(cancel)
            publish(temp, target)  # Sólo después de autenticar TAG_FINAL y EOF.
            return target
        finally:
            f.close()
            if temp is not None:
                temp.unlink(missing_ok=True)

    @serialized
    def migrate(self, current_password, new_folder, new_password, hint, staging, progress=None, cancel=None):
        if new_password == current_password:
            raise VaultError("La nueva contraseña debe ser distinta.")
        fresh = Vault.unlock(self.folder, current_password)  # Exigir contraseña ACTUAL aun desbloqueada.
        if fresh.key != self.key or fresh.header != self.header:
            raise VaultError("La bóveda cambió; vuelva a desbloquearla.")
        new_folder = safe_path(new_folder, directory=True)
        if inside(new_folder, self.folder) or inside(self.folder, new_folder):
            raise VaultError("La nueva bóveda debe estar en una carpeta separada.")
        staging = stage_dir(staging, self.folder)
        outside(staging, self.cloud_root)
        stage_dir(staging, new_folder)
        entries = self.entries()
        source_inventory = self._read_inventory()
        if source_inventory is not None and sorted(source_inventory) != entries:
            raise VaultError("El inventario de origen no coincide. Migración bloqueada.")
        source_header_hash = file_digest(self.folder / HEADER)
        new = Vault.create(new_folder, new_password, hint, staging, "migration-incomplete")
        if inside(new_folder, self.cloud_root):
            new.set_cloud_root(self.cloud_root)
        records = []
        for index, entry in enumerate(entries):
            check_cancel(cancel)
            f, state, ad, meta = self.reader(entry)
            with f:
                callback = (lambda done, total: progress(index + 1, len(entries), done, total)) if progress else None
                digest = hashlib.sha256()
                source_hash = file_digest(self.folder / entry, cancel)
                if source_inventory is not None and source_inventory[entry] != source_hash:
                    raise VaultError("El origen cambió respecto al inventario.")
                def blocks():
                    for data in self.chunks(f, state, ad, meta["size"], cancel):
                        digest.update(data)
                        yield data
                new_entry = new.encrypt_chunks(meta, blocks(), staging, callback, cancel)
            if file_digest(self.folder / entry, cancel) != source_hash:
                raise VaultError("Cambió un archivo de origen durante la migración.")
            records.append({"old": entry, "new": new_entry, "cipher_hash": source_hash, "plain_hash": digest.hexdigest(), "meta": meta})
        check_cancel(cancel)
        if entries != self.entries() or file_digest(self.folder / HEADER) != source_header_hash:
            raise VaultError("Cambió el conjunto de archivos durante la migración.")
        # Segunda lectura REAL de la nueva bóveda, desbloqueada con la contraseña nueva.
        verified = Vault.unlock(new.folder, new_password)
        verified.verify_records(records, cancel)
        receipt = {"version": 1, "source": str(self.folder), "header_hash": source_header_hash, "records": records}
        if source_inventory is not None:
            receipt["inventory_hash"] = file_digest(self.folder / INVENTORY)
        receipt_data = canonical(receipt)
        if len(receipt_data) > 32 * 1024 * 1024:
            raise VaultError("Demasiados archivos para el registro de rotación del prototipo.")
        nonce = utils.random(24)
        receipt_data = nonce + sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(receipt_data, bytes.fromhex(new.header["vault"]), nonce, new.key)
        temp, out = temp_file(staging)
        try:
            with out:
                out.write(receipt_data)
                sync_file(out)
            publish(temp, new.folder / RECEIPT)
        finally:
            temp.unlink(missing_ok=True)
        # El estado completo también está autenticado por la contraseña nueva.
        new.header["state"] = "migration-complete"
        wrap(new.header, new.key, new_password)
        temp, out = temp_file(staging)
        try:
            with out:
                out.write(canonical(new.header))
                sync_file(out)
            os.replace(temp, new.folder / HEADER)
        finally:
            temp.unlink(missing_ok=True)
        return new

    def verify_records(self, records, cancel=None):
        if self.entries() != sorted(r["new"] for r in records):
            raise VaultError("El contenido de la nueva bóveda cambió; limpieza bloqueada.")
        for record in records:
            f, state, ad, meta = self.reader(record["new"])
            digest = hashlib.sha256()
            with f:
                if meta != record["meta"]:
                    raise VaultError("Metadatos distintos después de la rotación.")
                for data in self.chunks(f, state, ad, meta["size"], cancel):
                    digest.update(data)
            if digest.hexdigest() != record["plain_hash"]:
                raise VaultError("Contenido distinto después de la rotación.")

    @serialized
    def cleanup_previous(self, new_password, upload_confirmed=False, cancel=None, deleted_callback=None):
        if not upload_confirmed:
            raise VaultError("Primero compruebe personalmente la subida de la nueva bóveda en TeraBox.")
        fresh = Vault.unlock(self.folder, new_password)
        if fresh.key != self.key or fresh.header["state"] != "migration-complete":
            raise VaultError("La rotación no está completa.")
        with safe_path(self.folder / RECEIPT).open("rb") as f:
            raw = f.read(32 * 1024 * 1024 + 41)
        if not 40 <= len(raw) <= 32 * 1024 * 1024 + 40:
            raise VaultError("Registro de rotación no válido.")
        try:
            receipt = json.loads(sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(raw[24:], bytes.fromhex(self.header["vault"]), raw[:24], self.key))
        except (CryptoError, ValueError) as exc:
            raise VaultError("Registro de rotación no auténtico.") from exc
        source = safe_path(receipt["source"], directory=True)
        if inside(source, self.folder) or inside(self.folder, source):
            raise VaultError("Ruta de limpieza no válida.")
        with operation_lock(source):
            records = receipt["records"]
            for r in records:
                if not ENTRY.fullmatch(r["old"]) or not ENTRY.fullmatch(r["new"]):
                    raise VaultError("Identificador peligroso en registro.")
            # Revalidar TODO el nuevo contenido antes de cualquier borrado antiguo.
            fresh.verify_records(records, cancel)
            new_inventory = fresh._read_inventory()
            if new_inventory is not None and sorted(new_inventory) != fresh.entries():
                raise VaultError("Inventario nuevo no coincide; limpieza bloqueada.")
            old_header = source / HEADER
            if old_header.exists() and file_digest(old_header, cancel) != receipt["header_hash"]:
                raise VaultError("La identidad de la bóveda anterior cambió; limpieza bloqueada.")
            for r in records:
                path = source / r["old"]
                if path.exists() and file_digest(path, cancel) != r["cipher_hash"]:
                    raise VaultError("Un archivo antiguo cambió; limpieza bloqueada.")
            old_inventory = source / INVENTORY
            if "inventory_hash" in receipt and old_inventory.exists() and file_digest(old_inventory, cancel) != receipt["inventory_hash"]:
                raise VaultError("El inventario anterior cambió; limpieza bloqueada.")
            for r in records:
                check_cancel(cancel)
                path = source / r["old"]
                if path.exists():
                    if file_digest(path, cancel) != r["cipher_hash"]:
                        raise VaultError("Cambió el archivo antes de borrarlo.")
                    safe_path(path).unlink()  # Sólo archivo enumerado y validado; nunca recursivo.
                    if deleted_callback:
                        deleted_callback(path)
            check_cancel(cancel)
            # Si aparecen nuevas entradas, conservar el encabezado para poder recuperarlas.
            if old_header.exists() and not any(ENTRY.fullmatch(p.name) for p in source.iterdir()):
                if file_digest(old_header, cancel) != receipt["header_hash"]:
                    raise VaultError("Cambió el encabezado antiguo.")
                if "inventory_hash" in receipt and old_inventory.exists():
                    if file_digest(old_inventory, cancel) != receipt["inventory_hash"]:
                        raise VaultError("Cambió el inventario antiguo.")
                    safe_path(old_inventory).unlink()
                safe_path(old_header).unlink()
            return source



if __name__ == "__main__":
    from qt_ui import run_gui
    run_gui()
