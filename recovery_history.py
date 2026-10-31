"""Registro local de parciales propios; no almacena documentos, claves ni contraseñas."""
import json
import os
from pathlib import Path
import re
import tempfile
from terabox_local import operation_lock, safe_path, outside
from windows_io import delete_recorded_partial


class RecoveryHistory:
    def __init__(self, directory=None):
        self.directory = Path(directory or os.environ.get('INFINITYMED_STATE_DIR') or (Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir())) / 'InfinityMedBoveda'))
        self.path = self.directory / 'recuperaciones.json'

    def _load(self):
        if not self.path.exists():return {}
        with safe_path(self.path).open('rb') as f:raw=f.read(262145)
        if len(raw)>262144:raise ValueError('Registro local demasiado grande.')
        data=json.loads(raw)
        if not isinstance(data,dict) or len(data)>256:raise ValueError('Registro local inválido.')
        return data

    def _save(self, data):
        fd,name=tempfile.mkstemp(prefix='.registro-',dir=self.directory)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(data,f,ensure_ascii=False);f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
        finally:
            Path(name).unlink(missing_ok=True)

    def record(self,path,cloud_root,identity=None):
        path=outside(path,cloud_root)
        safe_path(self.directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        outside(self.directory,cloud_root)
        info=path.stat() if identity is None else None
        with operation_lock(self.directory):
            data=self._load()
            if len(data)>=256:raise ValueError('Revise recuperaciones pendientes antes de continuar.')
            data[str(path)]={'identity':list(identity) if identity is not None else [info.st_dev,info.st_ino],'destination':str(path.parent)}
            self._save(data)

    def forget(self,path):
        if not self.directory.exists():return
        with operation_lock(self.directory):
            data=self._load();data.pop(str(path),None);self._save(data)

    def pending(self):
        if not self.directory.exists():return []
        with operation_lock(self.directory):data=self._load()
        result=[]
        for name,record in data.items():
            path=Path(name)
            if not re.fullmatch(r'\.tblocal-[a-z0-9_]{8}\.partial',path.name):continue
            if not isinstance(record,dict) or record.get('destination')!=str(path.parent):continue
            if not isinstance(record.get('identity'),list) or len(record['identity'])!=2:continue
            try:
                checked=safe_path(path)
                if checked.is_file():result.append(checked)
            except OSError:continue
        return result

    def purge(self,paths):
        if os.name!='nt':raise OSError('Limpieza de parciales sólo disponible en Windows.')
        # Nunca escanea discos ni elimina por sufijo: sólo registros concretos de esta app.
        with operation_lock(self.directory):data=self._load()
        for value in paths:
            path=safe_path(value)
            record=data.get(str(path))
            if record is None or not re.fullmatch(r'\.tblocal-[a-z0-9_]{8}\.partial',path.name):
                raise ValueError('El archivo no pertenece al registro de la aplicación.')
            if record.get('destination')!=str(path.parent):raise ValueError('Destino inválido.')
            with operation_lock(path.parent):
                delete_recorded_partial(path,record['identity'])
            self.forget(path)
