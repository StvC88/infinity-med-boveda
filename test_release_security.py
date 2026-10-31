"""Regresión funcional de la versión distribuida; sin PoCs del informe privado."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import terabox_local as t
import recuperar_independiente as reader
from recovery_history import RecoveryHistory

PASSWORD='Frase larga para pruebas locales independientes'


class ReleaseSecurity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name).resolve()
        self.repo,self.stage,self.out=[self.root/name for name in ('repo','stage','out')]
        for path in (self.repo,self.stage,self.out):path.mkdir()
        self.v=t.Vault.create(self.repo,PASSWORD,'',self.stage)

    def tearDown(self):self.tmp.cleanup()

    def test_bidi_new_import_rejected_all_controls(self):
        for control in t.BIDI_CONTROLS:
            source=self.root/('reporte_'+control+'txt.exe')
            source.write_bytes(b'sintetico')
            with self.assertRaises(t.VaultError):self.v.add(source,self.stage)
        self.assertEqual(self.v.entries(),[])

    def test_legacy_bidi_recovered_with_safe_name_in_both_readers(self):
        for i,control in enumerate(['\u061c','\u202e','\u2066','\u2069']):
            name=f'reporte{i}_'+control+'txt.exe'
            entry=self.v.encrypt_chunks({'name':name,'size':4},iter([b'data']),self.stage)
            self.assertEqual(self.v.metadata(entry)['name'],name)
            self.assertNotIn(control,t.display_name(name))
            a=self.v.restore(entry,self.out)
            self.assertEqual(a.name,t.export_name(name))
            self.assertNotIn(control,a.name)
            h,key=reader.unlock_repository(self.repo,PASSWORD)
            other=self.root/('out'+str(i));other.mkdir()
            reader.consume_object(self.repo,entry,h,key,other)
            self.assertEqual((other/a.name).read_bytes(),b'data')

    def test_legacy_bidi_rotation_preserves_authenticated_metadata(self):
        name='reporte_\u202etxt.exe'
        self.v.encrypt_chunks({'name':name,'size':4},iter([b'data']),self.stage)
        destination=self.root/'new';destination.mkdir()
        new=self.v.migrate(PASSWORD,destination,'Otra frase larga y diferente para pruebas','',self.stage)
        self.assertEqual(new.metadata(new.entries()[0])['name'],name)
        self.assertEqual(new.verify()['files'],1)
        self.assertEqual(new.restore(new.entries()[0],self.out).read_bytes(),b'data')

    def test_safe_export_does_not_overwrite_collision(self):
        name='reporte_\u202etxt.exe'
        entry=self.v.encrypt_chunks({'name':name,'size':4},iter([b'data']),self.stage)
        existing=self.out/t.export_name(name);existing.write_bytes(b'conservar')
        with self.assertRaises(t.VaultError):self.v.restore(entry,self.out)
        self.assertEqual(existing.read_bytes(),b'conservar')

    def test_unicode_normalization_not_silently_applied(self):
        for name in ['café.txt','cafe\u0301.txt','文档.txt']:
            entry=self.v.encrypt_chunks({'name':name,'size':1},iter([b'x']),self.stage)
            self.assertEqual(self.v.metadata(entry)['name'],name)
            self.assertEqual(self.v.restore(entry,self.out).name,name)

    @unittest.skipUnless(os.name=='nt','Compartición nativa Windows')
    def test_source_writer_denied_during_import(self):
        source=self.root/'origen.bin';source.write_bytes(b'a'*(t.BLOCK+1));denied=[]
        def writer(*args):
            try:
                with source.open('r+b') as f:f.write(b'X')
            except PermissionError:denied.append(True)
        entry=self.v.add(source,self.stage,writer)
        self.assertTrue(denied)
        self.assertEqual(self.v.restore(entry,self.out).read_bytes(),source.read_bytes())

    @unittest.skipUnless(os.name=='nt','Compartición nativa Windows')
    def test_existing_writer_blocks_import_without_publication(self):
        source=self.root/'origen.bin';source.write_bytes(b'data')
        with source.open('r+b'):
            with self.assertRaises(t.VaultError):self.v.add(source,self.stage)
        self.assertEqual(self.v.entries(),[])
        self.assertEqual(list(self.stage.iterdir()),[])

    def test_complete_recovery_clears_its_journal(self):
        journal=RecoveryHistory(self.root/'state')
        source=self.root/'origen.txt';source.write_bytes(b'data')
        entry=self.v.add(source,self.stage)
        self.v.restore(entry,self.out,journal=journal)
        self.assertEqual(journal.pending(),[])
        self.assertTrue((self.out/source.name).exists())

    @unittest.skipUnless(os.name=='nt','Cierre de proceso y borrado por identidad Windows')
    def test_abrupt_recovery_is_registered_and_reviewable(self):
        source=self.root/'sintetico.bin';source.write_bytes(b'X'*(t.BLOCK+1))
        entry=self.v.add(source,self.stage)
        state=self.root/'state'
        code="import os,sys; from pathlib import Path; from terabox_local import Vault; from recovery_history import RecoveryHistory\nv=Vault.unlock(Path(sys.argv[1]),sys.stdin.readline().rstrip('\\n'))\nv.restore(sys.argv[2],Path(sys.argv[3]),lambda *args:os._exit(17),journal=RecoveryHistory(Path(sys.argv[4])))"
        result=subprocess.run([sys.executable,'-c',code,str(self.repo),entry,str(self.out),str(state)],input=PASSWORD+'\n',text=True,capture_output=True,timeout=20,cwd=Path(__file__).parent)
        self.assertEqual(result.returncode,17,result.stderr)
        journal=RecoveryHistory(state)
        pending=journal.pending();self.assertEqual(len(pending),1)
        self.assertFalse((self.out/source.name).exists())
        unrelated=self.out/'completo.txt';unrelated.write_bytes(b'conservar')
        journal.purge(pending)
        self.assertFalse(pending[0].exists())
        self.assertEqual(unrelated.read_bytes(),b'conservar')

    @unittest.skipUnless(os.name=='nt','Borrado por handle Windows')
    def test_journal_purges_only_recorded_identity(self):
        journal=RecoveryHistory(self.root/'state')
        path=self.out/'.tblocal-abcdefgh.partial';path.write_bytes(b'incompleto')
        unrelated=self.out/'otra.partial';unrelated.write_bytes(b'conservar')
        final=self.out/'recuperado.txt';final.write_bytes(b'conservar')
        journal.record(path,self.repo)
        self.assertEqual(journal.pending(),[path])
        journal.purge([path])
        self.assertFalse(path.exists())
        self.assertEqual(unrelated.read_bytes(),b'conservar')
        self.assertEqual(final.read_bytes(),b'conservar')

    @unittest.skipUnless(os.name=='nt','Borrado por handle Windows')
    def test_journal_refuses_replaced_file(self):
        journal=RecoveryHistory(self.root/'state')
        path=self.out/'.tblocal-abcdefgh.partial';path.write_bytes(b'incompleto');journal.record(path,self.repo)
        path.rename(self.out/'conservado.partial');path.write_bytes(b'otro archivo')
        with self.assertRaises(OSError):journal.purge([path])
        self.assertEqual(path.read_bytes(),b'otro archivo')

    def test_journal_refuses_active_recovery(self):
        journal=RecoveryHistory(self.root/'state')
        path=self.out/'.tblocal-abcdefgh.partial';path.write_bytes(b'incompleto');journal.record(path,self.repo)
        with t.operation_lock(self.out):
            with self.assertRaises(t.VaultError):journal.purge([path])
        self.assertTrue(path.exists())

    def test_directory_export_blocked_even_with_partial_descendant(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from qt_ui import Window
        app=QApplication.instance() or QApplication([])
        folder=self.out/'carpeta';folder.mkdir();(folder/'.tblocal-abcdefgh.partial').write_bytes(b'incompleto')
        w=Window(journal=RecoveryHistory(self.root/'state'))
        w.vault=SimpleNamespace(cloud_root=self.repo);w.show_recovered(self.out)
        index=w.recovered_model.index(str(folder))
        self.assertTrue(index.isValid())
        self.assertFalse(w.recovered_model.flags(index)&Qt.ItemFlag.ItemIsDragEnabled)
        self.assertEqual(w.recovered_model.mimeData([index]).urls(),[])
        w.close()

    def test_cleanup_api_unconditionally_disabled(self):
        with patch.object(t,'file_digest',side_effect=AssertionError('No acceder ni borrar objetos')):
            with self.assertRaises(t.VaultError):self.v.cleanup_previous(PASSWORD,True)

    @unittest.skipUnless(os.name=='nt','Junction nativa Windows')
    def test_junction_cannot_redirect_registered_partial_cleanup(self):
        real=self.root/'real';real.mkdir()
        witness=real/'.tblocal-abcdefgh.partial';witness.write_bytes(b'conservar')
        link=self.root/'junction'
        result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(real)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        try:
            journal=RecoveryHistory(self.root/'state')
            with self.assertRaises((OSError,t.VaultError)):journal.record(link/witness.name,self.repo)
            self.assertEqual(witness.read_bytes(),b'conservar')
        finally:
            link.rmdir() # Retira sólo el enlace creado por esta prueba, nunca su destino.

    @unittest.skipUnless(os.name=='nt','Symlink nativo Windows')
    def test_symlink_source_is_rejected_when_privilege_available(self):
        source=self.root/'real.txt';source.write_bytes(b'conservar')
        link=self.root/'enlace.txt'
        try:link.symlink_to(source)
        except OSError as exc:
            if getattr(exc,'winerror',None)==1314:self.skipTest('El entorno no permite crear symlinks (1314)')
            raise
        with self.assertRaises((OSError,t.VaultError)):self.v.add(link,self.stage)
        self.assertEqual(source.read_bytes(),b'conservar')
        self.assertEqual(self.v.entries(),[])


if __name__=='__main__':unittest.main(verbosity=2)
