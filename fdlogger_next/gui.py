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
        self.editing_qso_id = None
        self.qso_ids = []

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

        self.save_button = QtWidgets.QPushButton("Add QSO")
        self.edit_button = QtWidgets.QPushButton("Edit")
        self.delete_button = QtWidgets.QPushButton("Delete")
        clear_button = QtWidgets.QPushButton("Clear")
        rebuild_button = QtWidgets.QPushButton("Rebuild")
        self.configure_accessibility(clear_button, rebuild_button)

        self.save_button.clicked.connect(self.save_qso)
        self.edit_button.clicked.connect(self.edit_selected_qso)
        self.delete_button.clicked.connect(self.delete_selected_qso)
        clear_button.clicked.connect(self.clear_form)
        rebuild_button.clicked.connect(self.rebuild_contacts)
        for widget in (self.call_edit, self.class_edit, self.section_edit):
            widget.returnPressed.connect(self.save_qso)

        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        call_label = self.field_label("Call", self.call_edit)
        class_label = self.field_label("Class", self.class_edit)
        section_label = self.field_label("Section", self.section_edit)
        band_label = self.field_label("Band", self.band_combo)
        mode_label = self.field_label("Mode", self.mode_combo)
        power_label = self.field_label("Power", self.power_spin)
        frequency_label = self.field_label("Frequency", self.frequency_spin)
        station_label = self.field_label("Station", self.station_edit)
        operator_label = self.field_label("Operator", self.operator_edit)
        database_label = self.field_label("Database", self.database_label)

        form.addWidget(call_label, 0, 0)
        form.addWidget(self.call_edit, 1, 0)
        form.addWidget(class_label, 0, 1)
        form.addWidget(self.class_edit, 1, 1)
        form.addWidget(section_label, 0, 2)
        form.addWidget(self.section_edit, 1, 2)
        form.addWidget(band_label, 0, 3)
        form.addWidget(self.band_combo, 1, 3)
        form.addWidget(mode_label, 0, 4)
        form.addWidget(self.mode_combo, 1, 4)
        form.addWidget(power_label, 0, 5)
        form.addWidget(self.power_spin, 1, 5)
        form.addWidget(frequency_label, 0, 6)
        form.addWidget(self.frequency_spin, 1, 6)
        form.addWidget(station_label, 2, 0)
        form.addWidget(self.station_edit, 3, 0, 1, 2)
        form.addWidget(operator_label, 2, 2)
        form.addWidget(self.operator_edit, 3, 2, 1, 2)
        form.addWidget(self.save_button, 3, 4)
        form.addWidget(clear_button, 3, 5)
        form.addWidget(rebuild_button, 3, 6)

        action_bar = QtWidgets.QHBoxLayout()
        action_bar.addWidget(self.edit_button)
        action_bar.addWidget(self.delete_button)
        action_bar.addStretch(1)

        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(database_label)
        footer.addWidget(self.database_label, 1)
        footer.addWidget(self.score_label)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(action_bar)
        layout.addWidget(self.table, 1)
        layout.addLayout(footer)

        central = QtWidgets.QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.refresh()
        self.call_edit.setFocus()

    @staticmethod
    def field_label(text, buddy):
        """Create a label linked to a field for keyboard and assistive tech."""
        label = QtWidgets.QLabel(text)
        label.setBuddy(buddy)
        return label

    def configure_accessibility(self, clear_button, rebuild_button):
        """Set names and descriptions for assistive technologies."""
        accessible_fields = (
            (self.call_edit, "Call sign", "Call sign for the contact."),
            (self.class_edit, "Field Day class", "Exchange class, such as 1A."),
            (self.section_edit, "ARRL section", "Exchange section, such as SCV."),
            (self.band_combo, "Band", "Band for this contact."),
            (self.mode_combo, "Mode", "Mode for this contact."),
            (self.power_spin, "Power", "Transmit power in watts."),
            (self.frequency_spin, "Frequency", "Frequency in hertz, if known."),
            (self.station_edit, "Station ID", "Local station identifier."),
            (self.operator_edit, "Operator call", "Operator call sign."),
            (self.database_label, "Database path", "Current SQLite database path."),
            (self.score_label, "Current score", "Current QSO count and score."),
        )
        for widget, name, description in accessible_fields:
            widget.setAccessibleName(name)
            widget.setAccessibleDescription(description)

        self.table.setAccessibleName("QSO log")
        self.table.setAccessibleDescription("Active logged contacts.")
        self.statusBar().setAccessibleName("Status")
        self.statusBar().setAccessibleDescription("Latest logger status message.")

        accessible_buttons = (
            (self.save_button, "Add or save QSO"),
            (self.edit_button, "Edit selected QSO"),
            (self.delete_button, "Delete selected QSO"),
            (clear_button, "Clear QSO entry fields"),
            (rebuild_button, "Rebuild contacts from event log"),
        )
        for button, description in accessible_buttons:
            button.setAccessibleDescription(description)

    def save_qso(self):
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

        changes = self.form_values()
        duplicates = self.store.find_duplicates(
            call=changes["call"],
            band=changes["band"],
            mode=changes["mode"],
            exclude_qso_id=self.editing_qso_id or "",
        )
        if duplicates and not self.confirm_duplicate(duplicates):
            return

        if self.editing_qso_id:
            station_id, operator_call = self.event_actor()
            self.store.update_qso(
                self.editing_qso_id,
                changes,
                station_id=station_id,
                operator_call=operator_call,
            )
            self.statusBar().showMessage(f"Updated {changes['call']}", 4000)
        else:
            qso = QSO.create(**changes)
            self.store.create_qso(qso)
            self.statusBar().showMessage(f"Logged {qso.call}", 4000)

        self.clear_form(keep_station=True)
        self.refresh()

    def form_values(self):
        """Return field values for creating or updating a QSO."""
        return {
            "call": self.call_edit.text().strip(),
            "qso_class": self.class_edit.text().strip(),
            "section": self.section_edit.text().strip(),
            "band": self.band_combo.currentText(),
            "mode": self.mode_combo.currentText(),
            "power": self.power_spin.value(),
            "frequency": self.frequency_spin.value(),
            "station_id": self.station_edit.text().strip(),
            "operator_call": self.operator_edit.text().strip(),
        }

    def event_actor(self, qso=None):
        """Return station/operator metadata for an update or delete event."""
        station_id = self.station_edit.text().strip()
        operator_call = self.operator_edit.text().strip()
        if qso:
            station_id = station_id or qso.station_id
            operator_call = operator_call or qso.operator_call
        return station_id, operator_call

    def confirm_duplicate(self, duplicates):
        """Ask before adding or saving a duplicate contact."""
        first = duplicates[0]
        suffix = "" if len(duplicates) == 1 else f" and {len(duplicates) - 1} more"
        message = (
            f"{first.call} is already logged on {first.band}M {first.mode}{suffix}.\n\n"
            "Log it anyway?"
        )
        response = QtWidgets.QMessageBox.question(
            self,
            "Duplicate QSO",
            message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        return response == QtWidgets.QMessageBox.Yes

    def selected_qso_id(self):
        """Return the selected row's QSO id, if any."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.qso_ids):
            return None
        return self.qso_ids[row]

    def edit_selected_qso(self):
        """Load the selected QSO into the form for editing."""
        qso_id = self.selected_qso_id()
        if not qso_id:
            return
        qso = self.store.get_qso(qso_id)
        if not qso:
            self.refresh()
            return

        self.editing_qso_id = qso.qso_id
        self.call_edit.setText(qso.call)
        self.class_edit.setText(qso.qso_class)
        self.section_edit.setText(qso.section)
        self.set_combo_text(self.band_combo, qso.band)
        self.set_combo_text(self.mode_combo, qso.mode)
        self.power_spin.setValue(qso.power)
        self.frequency_spin.setValue(qso.frequency)
        self.station_edit.setText(qso.station_id)
        self.operator_edit.setText(qso.operator_call)
        self.save_button.setText("Save QSO")
        self.statusBar().showMessage(f"Editing {qso.call}", 4000)
        self.call_edit.setFocus()

    def delete_selected_qso(self):
        """Soft-delete the selected QSO through an event."""
        qso_id = self.selected_qso_id()
        if not qso_id:
            return
        qso = self.store.get_qso(qso_id)
        if not qso:
            self.refresh()
            return

        response = QtWidgets.QMessageBox.question(
            self,
            "Delete QSO",
            f"Delete {qso.call} on {qso.band}M {qso.mode}?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if response != QtWidgets.QMessageBox.Yes:
            return

        station_id, operator_call = self.event_actor(qso)
        self.store.delete_qso(qso.qso_id, station_id, operator_call)
        if self.editing_qso_id == qso.qso_id:
            self.clear_form(keep_station=True)
        self.refresh()
        self.statusBar().showMessage(f"Deleted {qso.call}", 4000)

    def clear_form(self, keep_station=False):
        """Clear the QSO entry fields."""
        self.editing_qso_id = None
        self.save_button.setText("Add QSO")
        self.call_edit.clear()
        self.class_edit.clear()
        self.section_edit.clear()
        self.frequency_spin.setValue(0)
        if not keep_station:
            self.station_edit.setText(self.station_id)
            self.operator_edit.setText(self.operator_call)
        self.call_edit.setFocus()

    @staticmethod
    def set_combo_text(combo, text):
        """Select an existing combo value."""
        index = combo.findText(str(text).upper().replace("M", ""))
        if index >= 0:
            combo.setCurrentIndex(index)

    def rebuild_contacts(self):
        """Rebuild the materialized contact table and refresh the display."""
        count = self.store.rebuild_contacts()
        self.refresh()
        self.statusBar().showMessage(f"Rebuilt contacts from {count} events", 4000)

    def refresh(self):
        """Refresh the table and score from the store."""
        qsos = self.store.list_qsos()
        self.qso_ids = [qso.qso_id for qso in qsos]
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
