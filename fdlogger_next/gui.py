"""Minimal Qt GUI for the rewrite prototype."""

import argparse
import sys

from PyQt5 import QtCore, QtWidgets

from .models import QSO
from .scoring import calculate_score
from .store import EventStore


BANDS = ("160", "80", "40", "20", "15", "10", "6", "2")
MODES = ("CW", "PH", "DG")


class MainWindow(QtWidgets.QMainWindow):
    """Small working logger window for the next-generation prototype."""

    def __init__(self, database, station_id="", operator_call=""):
        super().__init__()
        self.database = database
        self.store = EventStore(database)
        self.station_id = station_id
        self.operator_call = operator_call

        self.setWindowTitle("FieldDayLogger Next")
        self.resize(980, 620)

        self.call_edit = QtWidgets.QLineEdit()
        self.call_edit.setPlaceholderText("K6ABC")
        self.class_edit = QtWidgets.QLineEdit()
        self.class_edit.setPlaceholderText("1A")
        self.section_edit = QtWidgets.QLineEdit()
        self.section_edit.setPlaceholderText("SCV")
        self.band_combo = QtWidgets.QComboBox()
        self.band_combo.addItems(BANDS)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(MODES)
        self.power_spin = QtWidgets.QSpinBox()
        self.power_spin.setRange(0, 2000)
        self.power_spin.setValue(100)
        self.frequency_spin = QtWidgets.QSpinBox()
        self.frequency_spin.setRange(0, 999999999)
        self.frequency_spin.setSingleStep(1000)
        self.station_edit = QtWidgets.QLineEdit(station_id)
        self.operator_edit = QtWidgets.QLineEdit(operator_call)

        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ("Time", "Call", "Class", "Section", "Band", "Mode", "Power", "Operator")
        )
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents
        )

        self.score_label = QtWidgets.QLabel()
        self.database_label = QtWidgets.QLabel(str(database))
        self.database_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        add_button = QtWidgets.QPushButton("Add QSO")
        clear_button = QtWidgets.QPushButton("Clear")
        rebuild_button = QtWidgets.QPushButton("Rebuild")

        add_button.clicked.connect(self.add_qso)
        clear_button.clicked.connect(self.clear_form)
        rebuild_button.clicked.connect(self.rebuild_contacts)
        for widget in (self.call_edit, self.class_edit, self.section_edit):
            widget.returnPressed.connect(self.add_qso)

        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.addWidget(QtWidgets.QLabel("Call"), 0, 0)
        form.addWidget(self.call_edit, 1, 0)
        form.addWidget(QtWidgets.QLabel("Class"), 0, 1)
        form.addWidget(self.class_edit, 1, 1)
        form.addWidget(QtWidgets.QLabel("Section"), 0, 2)
        form.addWidget(self.section_edit, 1, 2)
        form.addWidget(QtWidgets.QLabel("Band"), 0, 3)
        form.addWidget(self.band_combo, 1, 3)
        form.addWidget(QtWidgets.QLabel("Mode"), 0, 4)
        form.addWidget(self.mode_combo, 1, 4)
        form.addWidget(QtWidgets.QLabel("Power"), 0, 5)
        form.addWidget(self.power_spin, 1, 5)
        form.addWidget(QtWidgets.QLabel("Frequency"), 0, 6)
        form.addWidget(self.frequency_spin, 1, 6)
        form.addWidget(QtWidgets.QLabel("Station"), 2, 0)
        form.addWidget(self.station_edit, 3, 0, 1, 2)
        form.addWidget(QtWidgets.QLabel("Operator"), 2, 2)
        form.addWidget(self.operator_edit, 3, 2, 1, 2)
        form.addWidget(add_button, 3, 4)
        form.addWidget(clear_button, 3, 5)
        form.addWidget(rebuild_button, 3, 6)

        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(QtWidgets.QLabel("Database"))
        footer.addWidget(self.database_label, 1)
        footer.addWidget(self.score_label)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.table, 1)
        layout.addLayout(footer)

        central = QtWidgets.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.refresh()
        self.call_edit.setFocus()

    def add_qso(self):
        """Validate and store a QSO from the form."""
        call = self.call_edit.text().strip()
        qso_class = self.class_edit.text().strip()
        section = self.section_edit.text().strip()
        if not call or not qso_class or not section:
            QtWidgets.QMessageBox.warning(
                self,
                "Missing QSO data",
                "Call, class, and section are required.",
            )
            return

        qso = QSO.create(
            call=call,
            qso_class=qso_class,
            section=section,
            band=self.band_combo.currentText(),
            mode=self.mode_combo.currentText(),
            power=self.power_spin.value(),
            frequency=self.frequency_spin.value(),
            station_id=self.station_edit.text().strip(),
            operator_call=self.operator_edit.text().strip(),
        )
        self.store.create_qso(qso)
        self.clear_form(keep_station=True)
        self.refresh()

    def clear_form(self, keep_station=False):
        """Clear the QSO entry fields."""
        self.call_edit.clear()
        self.class_edit.clear()
        self.section_edit.clear()
        self.frequency_spin.setValue(0)
        if not keep_station:
            self.station_edit.setText(self.station_id)
            self.operator_edit.setText(self.operator_call)
        self.call_edit.setFocus()

    def rebuild_contacts(self):
        """Rebuild the materialized contact table and refresh the display."""
        count = self.store.rebuild_contacts()
        self.refresh()
        self.statusBar().showMessage(f"Rebuilt contacts from {count} events", 4000)

    def refresh(self):
        """Refresh the table and score from the store."""
        qsos = self.store.list_qsos()
        self.table.setRowCount(len(qsos))
        for row, qso in enumerate(qsos):
            values = (
                qso.date_time,
                qso.call,
                qso.qso_class,
                qso.section,
                f"{qso.band}M",
                qso.mode,
                f"{qso.power}W",
                qso.operator_call,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))

        total, base = calculate_score(qsos)
        self.score_label.setText(f"QSOs {len(qsos)}   Score {total}   Base {base}")


def build_parser():
    """Build the GUI command parser."""
    parser = argparse.ArgumentParser(prog="fdlogger-next")
    parser.add_argument(
        "database",
        nargs="?",
        default="FieldDayNext.db",
        help="prototype SQLite database",
    )
    parser.add_argument("--station", default="", help="default station id")
    parser.add_argument("--operator", default="", help="default operator call")
    return parser


def run(argv=None):
    """Run the prototype GUI."""
    args = build_parser().parse_args(argv)
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("FieldDayLogger Next")
    window = MainWindow(args.database, args.station, args.operator)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(run())
