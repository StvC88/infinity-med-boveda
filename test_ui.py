"""Pruebas Qt offscreen: no equivalen a arrastre físico con Explorer."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
from pathlib import Path
import unittest
from PySide6.QtCore import QMimeData, QUrl, Qt, QPoint, QPointF
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QListWidgetItem
from qt_ui import Window, local_drop_paths


class UITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_native_file_urls_import_export_and_clipboard(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "prueba español.txt"
            p.write_bytes(b"datos")
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(p))])
            self.assertEqual(local_drop_paths(mime), [p.resolve()])
            window = Window()
            item = QListWidgetItem("prueba español.txt")
            item.setData(Qt.ItemDataRole.UserRole, "entry")
            window.files.addItem(item)
            item.setSelected(True)
            window.prepared["entry"] = p
            from types import SimpleNamespace
            window.vault = SimpleNamespace(cloud_root=Path(temp) / "encrypted")
            exported = window.files.export_mime()
            self.assertEqual(Path(exported.urls()[0].toLocalFile()), p)
            window.show_recovered(p.parent)
            index = window.recovered_model.index(str(p))
            window.recovered.selectionModel().select(index, __import__("PySide6.QtCore", fromlist=["QItemSelectionModel"]).QItemSelectionModel.SelectionFlag.Select | __import__("PySide6.QtCore", fromlist=["QItemSelectionModel"]).QItemSelectionModel.SelectionFlag.Rows)
            window.copy_files()
            self.assertTrue(self.app.clipboard().mimeData().hasUrls())
            self.assertEqual(Path(self.app.clipboard().mimeData().urls()[0].toLocalFile()), p)
            self.app.clipboard().clear()
            window.close()

    def test_lock_hides_recovered_and_clears_names(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as temp:
            window = Window()
            window.vault = SimpleNamespace(cloud_root=Path(temp) / "encrypted")
            window.filter.setText("nombre sensible")
            window.show_recovered(Path(temp))
            self.assertFalse(window.recovered.isHidden())
            window.lock()
            self.assertTrue(window.recovered.isHidden())
            self.assertEqual(window.filter.text(), "")
            self.assertIsNone(window.vault)
            window.close()

    def test_reject_remote_urls_and_folders(self):
        mime = QMimeData()
        mime.setUrls([QUrl("https://example.com/file")])
        with self.assertRaises(Exception):
            local_drop_paths(mime)
        with tempfile.TemporaryDirectory() as temp:
            mime.setUrls([QUrl.fromLocalFile(temp)])
            with self.assertRaises(Exception):
                local_drop_paths(mime)

    def test_drop_dispatch_native_event(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "entrada.txt"
            p.write_bytes(b"datos")
            window = Window()
            window.vault = object()
            # Reemplazar la importación real aquí; el motor se prueba con archivos en test_vault.
            window.files.dropped.disconnect()
            received = []
            window.files.dropped.connect(lambda paths: received.extend(paths))
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(p))])
            enter = QDragEnterEvent(QPoint(2, 2), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            window.files.dragEnterEvent(enter)
            self.assertTrue(enter.isAccepted())
            drop = QDropEvent(QPointF(2, 2), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            window.files.dropEvent(drop)
            self.assertTrue(drop.isAccepted())
            self.assertEqual(received, [p.resolve()])
            window.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
