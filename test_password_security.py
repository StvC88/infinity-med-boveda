import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import terabox_local as t
import recuperar_independiente as reader

STRONG = 'Frase larga de laboratorio con cinco palabras'


class PasswordSecurity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo, self.stage, self.out, self.new = [self.root / p for p in ('repo','stage','out','new')]
        for p in (self.repo,self.stage,self.out,self.new):p.mkdir()

    def tearDown(self):self.tmp.cleanup()

    def test_creation_rejects_simple_passwords_before_writing(self):
        for password in ['4','1234','password','a'*30,'a'*15+'!','abcabcabcabcabc!','12345678901234567890','qwertyuiopasdfgh','InfinityMed2026!','P@ssw0rd123456789!','   '*8]:
            with self.subTest(password=password):
                with patch.object(t.utils,'random',side_effect=AssertionError('No generar claves para entrada rechazada')):
                    with self.assertRaises(t.VaultError):t.Vault.create(self.repo,password,'',self.stage)
                self.assertEqual(list(self.repo.iterdir()),[])

    def test_rotation_rejects_weak_new_password_without_destination_changes(self):
        v=t.Vault.create(self.repo,STRONG,'',self.stage)
        before={p.name:p.read_bytes() for p in self.repo.iterdir()}
        with self.assertRaises(t.VaultError):v.migrate(STRONG,self.new,'4','',self.stage)
        self.assertEqual(list(self.new.iterdir()),[])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.repo.iterdir()})

    def test_legacy_weak_password_still_recovers_and_migrates(self):
        v=t.Vault.create(self.repo,STRONG,'',self.stage)
        source=self.root/'sintetico.txt';source.write_bytes(b'datos sinteticos')
        entry=v.add(source,self.stage)
        # Simular una bóveda antigua de contraseña débil con clave propia conocida.
        h=dict(v.header);t.wrap(h,v.key,'4');(self.repo/t.HEADER).write_bytes(t.canonical(h))
        old=t.Vault.unlock(self.repo,'4')
        self.assertEqual(old.restore(entry,self.out).read_bytes(),source.read_bytes())
        reader.recover(self.repo,'4')
        new=old.migrate('4',self.new,'Otra frase larga e independiente para pruebas','',self.stage)
        self.assertNotEqual(old.key,new.key)

    def test_wrong_defaults_cannot_unlock(self):
        t.Vault.create(self.repo,STRONG,'',self.stage)
        for candidate in ['4','actual','nueva','admin','password','test']:
            with self.subTest(candidate=candidate),self.assertRaises(t.VaultError):t.Vault.unlock(self.repo,candidate)

    def test_independent_random_keys_and_salts(self):
        a=t.Vault.create(self.repo,STRONG,'',self.stage)
        b=t.Vault.create(self.new,STRONG,'',self.stage)
        self.assertNotEqual(a.key,b.key)
        self.assertNotEqual(a.header['salt'],b.header['salt'])
        self.assertNotEqual(a.header['nonce'],b.header['nonce'])

    def test_unicode_phrase_unchanged(self):
        password='Árboles verdes junto al río durante otoño'
        t.validate_new_password(password)
        v=t.Vault.create(self.repo,password,'',self.stage)
        self.assertEqual(t.Vault.unlock(self.repo,password).key,v.key)
        with self.assertRaises(t.VaultError):t.Vault.unlock(self.repo,password+' ')

    def test_live_verification_checks_header_on_disk(self):
        v=t.Vault.create(self.repo,STRONG,'',self.stage)
        h=dict(v.header);h['nonce']=t.b64(b'x'*24)
        (self.repo/t.HEADER).write_bytes(t.canonical(h))
        with self.assertRaises(t.VaultError):v.verify()


if __name__=='__main__':unittest.main(verbosity=2)
