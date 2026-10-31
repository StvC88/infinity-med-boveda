"""Lector independiente v1/v2. Sólo requiere PyNaCl y Python, sin Qt ni motor de la app.

Uso: python recuperar_independiente.py BOVEDA --output DESTINO [--cloud-root AREA]
Omitir --output para verificar todo sin escribir texto claro. Nunca recibe la contraseña por argumentos.
"""
import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
from nacl import bindings as s, pwhash

LIMIT = 1048576
PATTERN = re.compile(r"[0-9a-f]{32}[.]tbe")


def checked(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            st = part.lstat()
            if stat.S_ISLNK(st.st_mode) or getattr(st, "st_file_attributes", 0) & 1024:
                raise ValueError("No se admiten enlaces ni junctions.")
    return path.resolve()


def bounded(path, limit):
    with checked(path).open("rb") as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Datos fuera de límites.")
    return data


def decode(value, length):
    if not isinstance(value, str) or len(value) > 256:
        raise ValueError("Campo binario inválido.")
    data = base64.b64decode(value, validate=True)
    if len(data) != length:
        raise ValueError("Longitud inválida.")
    return data


def unlock_repository(folder, password):
    folder = checked(folder)
    h = json.loads(bounded(folder / "boveda.json", 8192))
    fields = {"version", "vault", "salt", "ops", "mem", "hint", "state", "nonce", "wrapped"}
    if not isinstance(h, dict) or type(h.get("version")) is not int or h["version"] not in (1, 2):
        raise ValueError("Versión no admitida.")
    if h["version"] == 2:
        fields.add("inventory")
        if h.get("inventory") != "v1":
            raise ValueError("Inventario desconocido.")
    if set(h) != fields or type(h["ops"]) is not int or h["ops"] != 3 or type(h["mem"]) is not int or h["mem"] != 67108864:
        raise ValueError("Parámetros no admitidos.")
    if not isinstance(h["vault"], str) or not re.fullmatch(r"[0-9a-f]{32}", h["vault"]):
        raise ValueError("Identidad inválida.")
    if not isinstance(h["hint"], str) or len(h["hint"]) > 300 or h["state"] not in ("ready", "migration-incomplete", "migration-complete"):
        raise ValueError("Encabezado inválido.")
    if not 1 <= len(password.encode("utf-8")) <= 1024:
        raise ValueError("Contraseña fuera de límites.")
    nonce, wrapped, salt = decode(h["nonce"], 24), decode(h["wrapped"], 48), decode(h["salt"], 16)
    ad = json.dumps({k: v for k, v in h.items() if k not in ("nonce", "wrapped")}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    kek = pwhash.argon2id.kdf(32, password.encode("utf-8"), salt, opslimit=3, memlimit=67108864)
    key = s.crypto_aead_xchacha20poly1305_ietf_decrypt(wrapped, ad, nonce, kek)
    return h, key


def filename(name):
    if not isinstance(name, str) or not name or len(name.encode("utf-8")) > 800 or name in (".", ".."):
        raise ValueError("Nombre inválido.")
    if any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name) or name.endswith((".", " ")):
        raise ValueError("Nombre peligroso.")
    base = name.split(".")[0].rstrip(" ").upper()
    if base in ("CON", "AUX", "PRN", "NUL", "CONIN$", "CONOUT$") or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", base):
        raise ValueError("Nombre reservado.")
    return name


def exported_filename(name):
    filename(name)
    controls=frozenset('\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069')
    if not any(c in controls for c in name):return name
    safe='nombre-seguro-'+''.join(f'_U{ord(c):04X}_' if c in controls else c for c in name)
    if len(safe.encode('utf-16-le'))>480:
        safe='archivo-recuperado-'+hashlib.sha256(name.encode('utf-8')).hexdigest()+'.bin'
    return filename(safe)


def consume_object(folder, entry, h, key, destination=None):
    """Devuelve metadatos; publica el destino sólo después de FINAL y EOF."""
    if not PATTERN.fullmatch(entry):
        raise ValueError("Objeto inválido.")
    def exact(f, size):
        data = f.read(size)
        if len(data) != size:
            raise ValueError("Objeto truncado.")
        return data
    temp = None
    out = None
    try:
        with checked(Path(folder) / entry).open("rb") as f:
            prefix = exact(f, 40)
            if prefix != b"TBLOCAL1" + bytes.fromhex(h["vault"]) + bytes.fromhex(entry[:-4]):
                raise ValueError("Identidad de objeto no válida.")
            state = s.crypto_secretstream_xchacha20poly1305_state()
            s.crypto_secretstream_xchacha20poly1305_init_pull(state, exact(f, 24), key)
            def frame(maximum):
                size = struct.unpack(">I", exact(f, 4))[0]
                if not 17 <= size <= maximum + 17:
                    raise ValueError("Bloque fuera de límites.")
                return s.crypto_secretstream_xchacha20poly1305_pull(state, exact(f, size), prefix)
            raw, tag = frame(4096)
            meta = json.loads(raw)
            if tag != 0 or not isinstance(meta, dict) or set(meta) != {"name", "size"} or type(meta["size"]) is not int or not 0 <= meta["size"] < 2**63:
                raise ValueError("Metadatos inválidos.")
            name = exported_filename(meta["name"])
            if destination is not None:
                target = checked(destination) / name
                if target.exists() or target.is_symlink():
                    raise ValueError("El destino ya existe.")
                fd, tmp = tempfile.mkstemp(prefix=".recuperar-", suffix=".partial", dir=checked(destination))
                temp = Path(tmp)
                out = os.fdopen(fd, "wb")
            total = 0
            while True:
                data, tag = frame(LIMIT)
                if tag == s.crypto_secretstream_xchacha20poly1305_TAG_FINAL:
                    if data or total != meta["size"] or f.read(1):
                        raise ValueError("Fin o tamaño no válido.")
                    break
                if tag != 0 or not data or total + len(data) > meta["size"]:
                    raise ValueError("Bloque inesperado.")
                total += len(data)
                if out:
                    out.write(data)
            if out:
                out.flush()
                os.fsync(out.fileno())
                out.close()
                out = None
                checked(target.parent)
                if os.name == "nt":
                    os.rename(temp, target)
                else:
                    os.link(temp, target)
                    temp.unlink()
            return meta
    finally:
        if out:
            out.close()
        if temp:
            temp.unlink(missing_ok=True)


def recover(folder, password, destination=None, cloud_root=None):
    folder = checked(folder)
    root = checked(cloud_root or folder)
    if folder != root and root not in folder.parents:
        raise ValueError("Área de nube inválida.")
    if destination is not None:
        destination = checked(destination)
        if not destination.is_dir() or destination == root or root in destination.parents:
            raise ValueError("El destino final debe existir y estar fuera del área de nube.")
    h, key = unlock_repository(folder, password)
    entries = []
    for p in folder.iterdir():
        if PATTERN.fullmatch(p.name):
            entries.append(p.name)
            if len(entries) > 10000:
                raise ValueError("Demasiados objetos.")
    inventory = None
    if h["version"] == 2 or (folder / "inventario.tbi").exists():
        raw = bounded(folder / "inventario.tbi", 2 * 1024 * 1024)
        if len(raw) < 40:
            raise ValueError("Inventario truncado.")
        inventory = json.loads(s.crypto_aead_xchacha20poly1305_ietf_decrypt(raw[24:], b"inventory-v1" + bytes.fromhex(h["vault"]), raw[:24], key))
        if not isinstance(inventory, dict) or sorted(inventory) != sorted(entries):
            raise ValueError("Faltan archivos o el inventario no coincide.")
        # Comprobar hashes ANTES de publicar cualquier recuperado.
        for entry in entries:
            digest = hashlib.sha256()
            with checked(folder / entry).open("rb") as f:
                while data := f.read(LIMIT):
                    digest.update(data)
            if inventory[entry] != digest.hexdigest():
                raise ValueError("Un archivo no coincide con el inventario.")
    results = []
    for entry in sorted(entries):
        results.append(consume_object(folder, entry, h, key, destination))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cloud-root", type=Path)
    args = parser.parse_args()
    try:
        password = getpass.getpass("Contraseña del repositorio: ")
        result = recover(args.repository, password, args.output, args.cloud_root)
        print(f"{len(result)} archivos verificados" + (" y recuperados." if args.output else ". No se escribió texto claro."))
        return 0
    except Exception:
        print("No se pudo completar: revise contraseña, integridad, permisos y destino. Los archivos ya completados se conservan.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
