import sys
import os
import time
import platform
import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog,
    QComboBox, QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox
)
from PySide6.QtCore import Qt

try:
    import pwd  # For UNIX owner lookup
except ImportError:
    pwd = None

def get_owner(filepath):
    """
    Returns the owner of the file.
    - Works on Unix-like systems using pwd.
    - On Windows, returns a placeholder or tries to get an owner in a simplistic manner.
    """
    if platform.system() != "Windows":
        if pwd:
            return pwd.getpwuid(os.stat(filepath).st_uid).pw_name
        else:
            return "Unknown-Owner-UNIX"
    else:
        return "Unknown-Owner-Windows"

def search_files(paths, days_threshold, size_threshold, size_unit):
    """
    Searches for files that meet the criteria (age & size).
    Returns a list of tuples:
        (filepath, creation_time, owner, size_in_specified_unit, creation_timestamp)
    """
    results = []
    
    # Convert threshold from the specified unit to bytes
    unit_conversion = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    threshold_in_bytes = size_threshold * unit_conversion.get(size_unit, 1)

    now = time.time()
    cutoff_time = now - (days_threshold * 24 * 3600)

    for path in paths:
        if not os.path.isdir(path):
            continue  # Skip invalid directories
        for root, _, files in os.walk(path):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    c_time = os.path.getctime(filepath)
                    if c_time >= cutoff_time:  # Created within the last `days_threshold` days
                        f_size = os.path.getsize(filepath)
                        if f_size >= threshold_in_bytes:
                            owner = get_owner(filepath)
                            c_time_str = datetime.datetime.fromtimestamp(c_time).strftime('%Y-%m-%d %H:%M:%S')
                            displayed_size = f_size / unit_conversion[size_unit]
                            results.append((filepath, c_time_str, owner, displayed_size, c_time))
                except Exception:
                    pass  # Ignore files that can't be accessed
    return results

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Search Tool")
        self.setGeometry(100, 100, 1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Inputs layout
        input_layout = QHBoxLayout()

        self.paths_edit = QLineEdit()
        self.paths_edit.setPlaceholderText("Enter paths separated by semicolons...")
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_path)

        input_layout.addWidget(QLabel("Paths:"))
        input_layout.addWidget(self.paths_edit)
        input_layout.addWidget(btn_browse)

        layout.addLayout(input_layout)

        # Days filter
        days_layout = QHBoxLayout()
        days_label = QLabel("Days:")
        self.days_spin = QSpinBox()
        self.days_spin.setRange(0, 10000)
        self.days_spin.setValue(7)

        days_layout.addWidget(days_label)
        days_layout.addWidget(self.days_spin)
        layout.addLayout(days_layout)

        # File size threshold
        size_layout = QHBoxLayout()
        size_label = QLabel("Min Size:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 10_000_000)
        self.size_spin.setValue(100)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["B", "KB", "MB", "GB"])
        self.unit_combo.setCurrentText("KB")

        size_layout.addWidget(size_label)
        size_layout.addWidget(self.size_spin)
        size_layout.addWidget(self.unit_combo)
        layout.addLayout(size_layout)

        # Search button
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search)
        layout.addWidget(self.search_button)

        # Results table with sorting enabled
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["File Path", "Creation Time", "Owner", "Size"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSortingEnabled(True)  # Enable sorting by clicking on headers
        layout.addWidget(self.results_table)

    def browse_path(self):
        """
        Let the user browse for a directory and append it to the paths_edit field.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            current_text = self.paths_edit.text().strip()
            if current_text:
                new_text = current_text + ";" + directory
            else:
                new_text = directory
            self.paths_edit.setText(new_text)

    def on_search(self):
        """
        Executes the file search based on user inputs and populates the results table.
        """
        raw_paths = self.paths_edit.text().strip()
        if not raw_paths:
            QMessageBox.warning(self, "Warning", "Please enter at least one path.")
            return
        
        paths = [p.strip() for p in raw_paths.split(";") if p.strip()]
        days = self.days_spin.value()
        size_threshold = self.size_spin.value()
        size_unit = self.unit_combo.currentText()

        results = search_files(paths, days, size_threshold, size_unit)

        # Disable sorting while populating data
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(results))

        for row_idx, (fpath, ctime_str, owner, size_val, ctime_timestamp) in enumerate(results):
            path_item = QTableWidgetItem(fpath)
            ctime_item = QTableWidgetItem(ctime_str)
            owner_item = QTableWidgetItem(owner)
            size_item = QTableWidgetItem(f"{size_val:.2f} {size_unit}")

            # Store raw values for proper sorting
            path_item.setData(Qt.UserRole, fpath)  # String
            ctime_item.setData(Qt.UserRole, ctime_timestamp)  # Numeric timestamp for correct sorting
            owner_item.setData(Qt.UserRole, owner)  # String
            size_item.setData(Qt.UserRole, float(size_val))  # Numeric value for correct sorting

            self.results_table.setItem(row_idx, 0, path_item)
            self.results_table.setItem(row_idx, 1, ctime_item)
            self.results_table.setItem(row_idx, 2, owner_item)
            self.results_table.setItem(row_idx, 3, size_item)

        # Re-enable sorting after populating data
        self.results_table.setSortingEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
