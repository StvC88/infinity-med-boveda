"""Interfaz Qt: URLs nativas de Windows para arrastrar en ambos sentidos."""
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QMimeData, QUrl, Qt
from PySide6.QtGui import QDrag, QIcon, QPixmap, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QAbstractItemView, QProgressBar,
    QFileDialog, QInputDialog, QLineEdit, QMessageBox, QMenu, QTreeView, QFileSystemModel, QFrame, QStyle, QFileIconProvider,
)
from terabox_local import Vault, VaultError, read_header, safe_path, outside, inside, check_cancel


def folder_icon(color):
    pix = QPixmap(32, 28)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color).darker(110))
    painter.drawRoundedRect(2, 3, 14, 8, 2, 2)
    painter.drawRoundedRect(2, 8, 28, 18, 3, 3)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(2, 10, 28, 16, 3, 3)
    painter.end()
    return QIcon(pix)


class ColoredFolders(QFileIconProvider):
    def icon(self, info):
        if hasattr(info, "isDir") and info.isDir():
            colors = ("#58afba", "#d9ae52", "#9d8cc4")
            return folder_icon(colors[sum(map(ord, info.fileName())) % len(colors)])
        return super().icon(info)


class RecoveryModel(QFileSystemModel):
    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return {0: "Nombre", 1: "Tamaño", 2: "Tipo", 3: "Modificado"}.get(section)
        return super().headerData(section, orientation, role)


def local_drop_paths(mime):
    if not mime.hasUrls() or not mime.urls() or any(not u.isLocalFile() for u in mime.urls()):
        raise VaultError("Arrastre archivos locales de Windows, sin enlaces web.")
    paths = [safe_path(u.toLocalFile()) for u in mime.urls()]
    if any(not p.is_file() for p in paths):
        raise VaultError("Este prototipo acepta archivos; seleccione los archivos dentro de las carpetas.")
    return paths


class Bridge(QObject):
    completed = Signal(object, object, object)
    progress = Signal(int, str)


class FileList(QListWidget):
    dropped = Signal(object)

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if not self.owner.busy and self.owner.vault and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        if self.owner.busy or not self.owner.vault:
            event.ignore()
            return
        try:
            paths = local_drop_paths(event.mimeData())
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            self.dropped.emit(paths)
        except Exception as exc:
            event.ignore()
            self.owner.error(exc)

    def export_mime(self):
        entries = [item.data(Qt.ItemDataRole.UserRole) for item in self.selectedItems()]
        if not entries:
            raise VaultError("Seleccione archivos.")
        paths = [self.owner.prepared.get(e) for e in entries]
        if any(p is None or not p.is_file() for p in paths):
            raise VaultError("Pulse «Preparar arrastre / Recuperar» primero. Los archivos grandes necesitan tiempo y espacio local.")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
        return mime

    def startDrag(self, actions):
        return  # Encriptados nunca exporta por arrastre.


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Infinity Med · Bóveda local")
        self.resize(1180, 760)
        self.setStyleSheet("""
        QWidget {font-family: Segoe UI; font-size: 13px; color: #242424; background: #f5f5f5;}
        QPushButton {border: none; border-radius: 5px; padding: 9px 13px; background: transparent;}
        QPushButton:hover {background: #e6eef6;}
        QPushButton:disabled {color: #999;}
        QLineEdit {background: white; border: 1px solid #e1e1e1; border-radius: 18px; padding: 10px 16px;}
        QListWidget, QTreeView {background: white; border: 1px solid #e7e7e7; border-radius: 9px; outline: none;}
        QListWidget::item {padding: 12px; border-bottom: 1px solid #f3f3f3;}
        QListWidget::item:selected {background: #e6f2ff; color: #005a9e;}
        QTreeView::item {height: 36px;}
        QHeaderView::section {background: white; border: none; padding: 10px; font-weight: 400;}
        QProgressBar {border: none; background: #eee; max-height: 5px;}
        QProgressBar::chunk {background: #0078d4;}
        """)
        self.vault = None
        self.folder = None
        self.cloud_root = None
        self.staging = None
        self.busy = False
        self.cancel = threading.Event()
        self.prepared = {}
        self.controls = []
        self.bridge = Bridge()
        self.bridge.completed.connect(self.completed)
        self.bridge.progress.connect(self.progress)
        layout = QVBoxLayout(self)
        title = QLabel("Infinity Med · Bóveda")
        title.setStyleSheet("font-size: 22px; font-weight: 400")
        brand = QHBoxLayout()
        logo_path = Path(__file__).resolve().parent / "assets" / "infinity-med.png"
        logo = QPixmap(str(logo_path))
        if not logo.isNull():
            mark = QLabel()
            mark.setPixmap(logo.scaled(270, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            brand.addWidget(mark)
            self.setWindowIcon(QIcon(str(logo_path)))
        brand.addStretch()
        brand.addWidget(title)
        layout.addLayout(brand)
        label = QLabel("Arrastre archivos desde Windows para cifrarlos. Compatible con carpetas locales de nube; la subida depende del cliente.")
        label.setWordWrap(True)
        layout.addWidget(label)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.button(row, "Abrir carpeta cifrada…", self.choose)
        self.button(row, "Carpeta temporal cifrada…", self.choose_stage)
        self.path_label = QLabel("Elija una carpeta cifrada y otra para temporales, separadas y en el mismo volumen.")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        self.hint_label = QLabel("Pista pública: —")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.button(row, "Crear bóveda", self.create)
        self.button(row, "Desbloquear", self.unlock)
        self.button(row, "Bloquear", self.lock)
        self.button(row, "Actualizar", self.refresh)
        self.button(row, "Verificar repositorio", self.verify_repository)
        self.files = FileList(self)
        self.files.dropped.connect(self.import_paths)
        self.files.setSortingEnabled(True)
        self.files.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.files.customContextMenuRequested.connect(self.context_menu)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Buscar por nombre…")
        self.filter.textChanged.connect(self.filter_files)
        layout.addWidget(self.filter)
        panels = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("Encriptados"))
        self.button(left_header, "Carpeta ▾", self.choose)
        self.controls[-1].setIcon(folder_icon("#d9ae52"))
        left.addLayout(left_header)
        left.addWidget(self.files)
        left.addWidget(QLabel("Arrastre aquí archivos desde Windows"))
        panels.addLayout(left, 1)
        self.button(panels, "→", self.restore)
        right_header = QHBoxLayout()
        right_header.addWidget(QLabel("Desencriptados"))
        self.button(right_header, "Carpeta ▾", self.choose_recovered)
        self.controls[-1].setIcon(folder_icon("#58afba"))
        right.addLayout(right_header)
        self.recovered = QTreeView()
        self.recovered_model = RecoveryModel(self)
        self.recovered_icons = ColoredFolders()
        self.recovered_model.setIconProvider(self.recovered_icons)
        self.recovered_model.setReadOnly(True)
        self.recovered.setModel(self.recovered_model)
        self.recovered.setVisible(False)
        self.recovered.setDragEnabled(True)
        self.recovered.setAcceptDrops(False)
        self.recovered.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.recovered.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.recovered.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.recovered.setSortingEnabled(True)
        self.recovered.setColumnWidth(0, 250)
        self.recovered.hideColumn(2)
        right.addWidget(self.recovered)
        right.addWidget(QLabel("Archivos recuperados · puede arrastrarlos al escritorio"))
        panels.addLayout(right, 1)
        layout.addLayout(panels, 1)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.button(row, "Agregar archivos…", self.add)
        self.button(row, "Desencriptar selección →", self.restore)
        self.button(row, "Copiar archivos", self.copy_files)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.button(row, "Rotar a una bóveda nueva…", self.migrate)
        self.button(row, "Limpiar versión anterior…", self.cleanup)
        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.cancel.set)
        row.addWidget(cancel_button)
        self.bar = QProgressBar()
        layout.addWidget(self.bar)
        self.status = QLabel("Estado LOCAL. Sin conexión a su cuenta de TeraBox.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        note = QLabel("Para arrastrar hacia Windows, prepare primero los archivos. Se conservarán descifrados en la carpeta de recuperación que elija. No hay recuperación de contraseña.")
        note.setWordWrap(True)
        layout.addWidget(note)

    def button(self, row, text, callback):
        b = QPushButton(text)
        def guarded():
            try:
                callback()
            except Exception as exc:
                self.error(exc)
        b.clicked.connect(guarded)
        row.addWidget(b)
        self.controls.append(b)

    def error(self, exc):
        QMessageBox.warning(self, "Bóveda local", str(exc))

    def filter_files(self, text):
        for i in range(self.files.count()):
            item = self.files.item(i)
            item.setHidden(text.casefold() not in item.text().casefold())

    def context_menu(self, point):
        if self.busy:
            return
        menu = QMenu(self)
        menu.addAction("Recuperar / Preparar para copiar…", lambda: self.safe_action(self.restore))
        
        menu.exec(self.files.mapToGlobal(point))

    def safe_action(self, action):
        try:
            action()
        except Exception as exc:
            self.error(exc)

    def update_paths(self):
        self.path_label.setText(f"Repositorio: {self.folder.name if self.folder else 'sin seleccionar'} · Temporales cifrados: {self.staging.name if self.staging else 'sin seleccionar'}")
        self.path_label.setToolTip(f"Bóveda: {self.folder}\nÁrea de nube: {self.cloud_root}\nTemporales: {self.staging}")

    def choose(self):
        path = QFileDialog.getExistingDirectory(self, "Carpeta cifrada; vacía para crear")
        if not path:
            return
        cloud = QFileDialog.getExistingDirectory(self, "Área COMPLETA sincronizada por su nube (puede ser la misma carpeta)", path)
        if not cloud:
            return
        if not inside(safe_path(path), safe_path(cloud)):
            raise VaultError("La bóveda debe quedar dentro del área de nube declarada.")
        self.lock()
        self.cloud_root = safe_path(cloud)
        self.folder = Path(path)
        self.update_paths()
        try:
            h = read_header(path)
            self.hint_label.setText("Pista pública: " + (h["hint"] or "sin pista"))
        except FileNotFoundError:
            self.hint_label.setText("Bóveda todavía no creada.")

    def choose_stage(self):
        path = QFileDialog.getExistingDirectory(self, "Temporales cifrados: FUERA de las bóvedas y del área sincronizada")
        if path:
            if self.cloud_root:
                outside(path, self.cloud_root)
            self.staging = Path(path)
            self.update_paths()

    def password(self, title, twice=False):
        prompt = "Use una frase larga y única (12 o más caracteres recomendados):" if twice else "Contraseña del repositorio:"
        value, ok = QInputDialog.getText(self, title, prompt, QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if twice:
            repeat, ok = QInputDialog.getText(self, title, "Repita la contraseña:", QLineEdit.EchoMode.Password)
            if not ok:
                return None
            if value != repeat:
                raise VaultError("Las contraseñas no coinciden.")
        return value

    def hint(self):
        text, ok = QInputDialog.getText(self, "Pista opcional", "Se guarda legible. No revele la contraseña:")
        return text if ok else None

    def require(self):
        if self.vault is None:
            raise VaultError("Primero cree o desbloquee la bóveda.")
        return self.vault

    def start(self, task, callback):
        if self.busy:
            raise VaultError("Espere a que termine la operación actual.")
        self.busy = True
        self.cancel.clear()
        self.bar.setValue(0)
        self.status.setText("Procesando localmente…")
        for b in self.controls:
            b.setEnabled(False)
        self.files.setEnabled(False)
        self.last_progress = 0
        def run():
            try:
                self.bridge.completed.emit(callback, task(), None)
            except Exception as exc:
                self.bridge.completed.emit(callback, None, exc)
        threading.Thread(target=run, daemon=True).start()

    def report(self, done, total, text="Procesando archivo"):
        now = time.monotonic()
        if now - self.last_progress >= 0.1 or done == total:
            self.last_progress = now
            self.bridge.progress.emit(int(100 * done / max(1, total)), f"{text}: {done:,} / {total:,} bytes")

    def progress(self, value, text):
        self.bar.setValue(value)
        self.status.setText(text)

    def completed(self, callback, result, error):
        self.busy = False
        for b in self.controls:
            b.setEnabled(True)
        self.files.setEnabled(True)
        if error:
            self.status.setText("Interrumpida. Se conservan los archivos completos. Revise el destino; una migración fallida sigue marcada incompleta.")
            self.error(error)
        else:
            self.bar.setValue(100)
            self.status.setText("Operación local completada.")
            try:
                callback(result)
            except Exception as exc:
                self.error(exc)

    def create(self):
        if self.folder is None or self.staging is None:
            raise VaultError("Elija primero ambas carpetas.")
        p = self.password("Crear bóveda · sin recuperación", True)
        if p is None:
            return
        hint = self.hint()
        if hint is not None:
            folder, staging = self.folder, self.staging
            outside(staging, self.cloud_root)
            self.start(lambda: Vault.create(folder, p, hint, staging), self.opened)

    def unlock(self):
        if self.folder is None:
            raise VaultError("Elija una carpeta cifrada.")
        p = self.password("Desbloquear")
        if p is not None:
            folder = self.folder
            self.start(lambda: Vault.unlock(folder, p), self.opened)

    def opened(self, vault):
        if self.cloud_root and inside(vault.folder, self.cloud_root):
            vault.set_cloud_root(self.cloud_root)
        else:
            self.cloud_root = vault.folder
        self.vault = vault
        self.folder = vault.folder
        self.prepared.clear()
        self.update_paths()
        self.hint_label.setText("Pista pública: " + (vault.header["hint"] or "sin pista"))
        if vault.header["state"] == "migration-incomplete":
            QMessageBox.warning(self, "Migración incompleta", "Contiene sólo lo completado. Conserve la bóveda anterior. Para repetir la migración use otra carpeta vacía.")
        self.refresh()

    def lock(self):
        self.vault = None
        self.prepared.clear()
        self.files.clear()
        self.filter.clear()
        self.recovered.setVisible(False)
        self.recovered_model.setRootPath("")
        self.recovered.clearSelection()
        self.status.setText("Bloqueada. Los archivos recuperados se conservan. Cierre la app al terminar.")

    def verify_repository(self):
        v = self.require()
        def done(result):
            suffix = "Inventario autenticado comprobado." if result["inventory"] else "Formato antiguo: no permite detectar archivos desaparecidos."
            self.status.setText(f"Verificación local completa: {result['files']} archivos. {suffix}")
        self.start(lambda: v.verify(lambda n, total: self.report(n, total, "Verificando archivos"), self.cancel), done)

    def refresh(self):
        v = self.require()
        def task():
            rows = []
            entries = v.entries()
            inventory = v._read_inventory()
            if inventory is not None and sorted(inventory) != entries:
                raise VaultError("Faltan archivos o hay objetos no registrados. Revise la sincronización y conserve todos los archivos.")
            for entry in entries:
                check_cancel(self.cancel)
                rows.append((entry, v.metadata(entry)))
            return rows
        def show(rows):
            self.files.clear()
            for entry, meta in rows:
                item = QListWidgetItem(f"{meta['name']}    ·    {meta['size']:,} bytes")
                item.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                item.setData(Qt.ItemDataRole.UserRole, entry)
                self.files.addItem(item)
            self.filter_files(self.filter.text())
            state = {"ready": "Lista", "migration-incomplete": "Migración incompleta", "migration-complete": "Migración verificada"}[v.header["state"]]
            version = " · Formato antiguo sin inventario" if v.header["version"] == 1 else ""
            self.status.setText(f"{len(rows)} archivos · {state}{version}. Guardado localmente; subida pendiente de comprobar en su cliente de nube.")
        self.start(task, show)

    def add(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Archivos originales (se conservan)")
        if paths:
            self.import_paths([Path(p) for p in paths])

    def import_paths(self, paths):
        try:
            v = self.require()
            stage = self.staging
            if stage is None:
                raise VaultError("Elija la carpeta temporal cifrada.")
            def task():
                for path in paths:
                    v.add(path, stage, self.report, self.cancel)
            self.start(task, lambda _: self.refresh())
        except Exception as exc:
            self.error(exc)

    def restore(self):
        v = self.require()
        entries = [i.data(Qt.ItemDataRole.UserRole) for i in self.files.selectedItems()]
        if not entries:
            raise VaultError("Seleccione archivos de la lista.")
        dest = QFileDialog.getExistingDirectory(self, "Destino FINAL fuera de toda carpeta sincronizada; los archivos recuperados se conservan")
        if not dest:
            return
        outside(dest, v.cloud_root)
        if self.staging and safe_path(dest) == safe_path(self.staging):
            raise VaultError("Reserve la carpeta temporal cifrada exclusivamente para cifrado. Elija otra para texto claro.")
        self.status.setText("Preparando / Descifrando…")
        def task():
            result = {}
            for entry in entries:
                path = v.restore(entry, dest, self.report, self.cancel)
                result[entry] = path
            return result
        def done(result):
            self.prepared.update(result)
            self.show_recovered(dest)
            self.status.setText(f"Listo para copiar o arrastrar. Descifrado verificado en: {dest}. Los archivos recuperados se conservan; no hay caché adicional.")
        self.start(task, done)

    def show_recovered(self, destination):
        outside(destination, self.require().cloud_root)
        self.recovered.setVisible(True)
        root = self.recovered_model.setRootPath(str(destination))
        self.recovered.setRootIndex(root)

    def choose_recovered(self):
        v = self.require()
        dest = QFileDialog.getExistingDirectory(self, "Carpeta desencriptada fuera del área de nube")
        if dest:
            outside(dest, v.cloud_root)
            self.show_recovered(dest)

    def copy_files(self):
        indexes = self.recovered.selectionModel().selectedRows(0)
        if not indexes:
            raise VaultError("Seleccione archivos o carpetas del panel Desencriptados.")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(self.recovered_model.filePath(i)) for i in indexes])
        QApplication.clipboard().setMimeData(mime)
        self.status.setText("Listo para pegar en Explorer.")

    def migrate(self):
        v = self.require()
        if self.staging is None:
            raise VaultError("Elija temporales cifrados fuera de ambas bóvedas.")
        current = self.password("Rotación · contraseña actual obligatoria")
        if current is None:
            return
        new = self.password("Nueva contraseña", True)
        if new is None:
            return
        hint = self.hint()
        if hint is None:
            return
        dest = QFileDialog.getExistingDirectory(self, "Bóveda nueva: carpeta vacía y separada")
        if not dest:
            return
        QMessageBox.information(self, "Rotación completa", "Se volverá a cifrar TODO con una clave independiente y se verificará la copia completa. Necesita tiempo y espacio para ambas bóvedas más el temporal del archivo mayor. La anterior se conserva hasta que elija limpiarla.")
        stage = self.staging
        def progress(i, count, done, total):
            self.report(done, total, f"Migrando {i} de {count}")
        self.start(lambda: v.migrate(current, dest, new, hint, stage, progress, self.cancel), self.opened)

    def cleanup(self):
        v = self.require()
        answer = QMessageBox.question(self, "Comprobar subida en TeraBox", "¿El cliente TeraBox ya mostró que TODOS los archivos de la NUEVA bóveda se cargaron y usted lo comprobó?\n\nSe verificará otra vez toda la nueva copia local antes de eliminar exclusivamente los archivos antiguos registrados. La app no verifica la nube. Papelera y versiones pueden conservar copias.")
        if answer != QMessageBox.StandardButton.Yes:
            return
        p = self.password("Contraseña de la bóveda nueva")
        if p is not None:
            self.start(lambda: v.cleanup_previous(p, True, self.cancel), lambda _: self.status.setText("Limpieza LOCAL finalizada. Propagación de cambios y borrados depende de TeraBox."))

    def closeEvent(self, event):
        if self.busy:
            self.cancel.set()
            self.status.setText("Cancelando… espere antes de cerrar.")
            event.ignore()
        else:
            event.accept()


def run_gui():
    app = QApplication.instance() or QApplication(sys.argv)
    window = Window()
    window.show()
    if "--smoke-test" in sys.argv:
        from PySide6.QtCore import QTimer
        # Prueba reproducible de arranque del binario sin archivos ni cuentas reales.
        def smoke():
            target = sys.argv[sys.argv.index("--smoke-test") + 1]
            import json, struct, tempfile
            result = {"gui_started": True, "pointer_bits": struct.calcsize("P") * 8, "frozen": bool(getattr(sys, "frozen", False))}
            try:
                with tempfile.TemporaryDirectory(prefix="exe-selftest-", dir=Path(target).parent) as temp:
                    base = Path(temp)
                    for name in ("old", "new", "stage", "out"):
                        (base / name).mkdir()
                    source = base / "prueba.txt"
                    source.write_bytes(b"prueba binario" * 90000)
                    v = Vault.create(base / "old", "actual", "", base / "stage")
                    entry = v.add(source, base / "stage")
                    new = v.migrate("actual", base / "new", "nueva", "", base / "stage")
                    path = new.restore(new.entries()[0], base / "out")
                    assert path.read_bytes() == source.read_bytes()
                    new.cleanup_previous("nueva", True)
                    result.update({"crypto_roundtrip": True, "full_rotation": True, "safe_cleanup": True})
                code = 0
            except Exception as exc:
                result["error"] = str(exc)
                code = 1
            Path(target).write_text(json.dumps(result), encoding="utf-8")
            app.exit(code)
        QTimer.singleShot(1500, smoke)
    app.exec()
