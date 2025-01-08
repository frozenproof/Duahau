import pandas as pd
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui, widget, settings
from PyQt5.QtWidgets import (QSizePolicy, QFileDialog, QVBoxLayout, 
                           QProgressBar, QLabel, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from pathlib import Path
import os

class ExcelReaderWidget(widget.OWWidget):
    name = "Excel Reader"
    description = "Reads data from an Excel file and outputs a data table."
    icon = "icons/excel.svg"
    priority = 100
    keywords = ["widget", "excel", "data", "import"]
    want_main_area = False
    resizing_enabled = True

    class Outputs:
        data = widget.Output("Data", Table, default=True)
    
    class Error(widget.OWWidget.Error):
        read_error = widget.Msg("Failed to read the Excel file.")
        no_file_error = widget.Msg("No file selected.")
    
    class Warning(widget.OWWidget.Warning):
        large_file = widget.Msg("Large file, loading may take a while...")
    
    # Settings
    filename = settings.Setting("")
    recent_paths = settings.Setting([])  # Changed from recent_files to recent_paths
    MAX_RECENT = 5

    def __init__(self):
        super().__init__()
        self.data = None
        self.setup_gui()

    def setup_gui(self):
        """Initialize the user interface with enhanced styling."""
        # Set the default size and allow resizing
        self.setMinimumSize(500, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Main layout with styling
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.controlArea.setLayout(layout)

        # Title
        title_label = QLabel("Excel File Import")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #2b5c84;
                padding: 10px;
                background-color: #f0f0f0;
                border-radius: 5px;
            }
        """)
        layout.addWidget(title_label)

        # File selection box with enhanced styling
        file_box = gui.vBox(
            self.controlArea, "File Selection",
            spacing=10,
            styleSheet="""
                QGroupBox {
                    background-color: white;
                    border: 2px solid #cccccc;
                    border-radius: 6px;
                    margin-top: 0.5em;
                    padding: 10px;
                }
                QGroupBox::title {
                    color: #2b5c84;
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 3px 0 3px;
                }
            """
        )

        # File path display with styling
        self.file_path_edit = gui.lineEdit(
            file_box, self, "filename",
            label="Selected File:",
            callback=None,
            readOnly=True,
            controlWidth=350,
            styleSheet="""
                QLineEdit {
                    padding: 5px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    background-color: #f8f9fa;
                }
            """
        )

        # Buttons box
        button_box = gui.hBox(file_box)

        # Browse button (only one now)
        gui.button(
            button_box, self, "Browse",
            callback=self.select_file,
            tooltip="Browse for an Excel file",
            styleSheet="""
                QPushButton {
                    padding: 8px 15px;
                    background-color: #2b5c84;
                    color: white;
                    border-radius: 4px;
                    min-width: 100px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1f4360;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """
        )

        # Reload button
        self.reload_button = gui.button(
            button_box, self, "Reload",
            callback=self.reload_file,
            tooltip="Reload the current Excel file",
            styleSheet="""
                QPushButton {
                    padding: 8px 15px;
                    background-color: #28a745;
                    color: white;
                    border-radius: 4px;
                    min-width: 100px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1e7e34;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """
        )
        self.reload_button.setEnabled(False)

        # Recent files section
        recent_box = gui.vBox(
            self.controlArea, "Recent Files",
            styleSheet="""
                QGroupBox {
                    background-color: white;
                    border: 2px solid #cccccc;
                    border-radius: 6px;
                    margin-top: 0.5em;
                    padding: 10px;
                }
            """
        )
        
        # Create QListWidget for recent files
        self.recent_list = QListWidget()
        self.recent_list.itemDoubleClicked.connect(self.select_recent)
        recent_box.layout().addWidget(self.recent_list)
        
        # Initialize recent files list
        self._update_recent_list()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2b5c84;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Info label with enhanced styling
        self.info_label = QLabel("Select an Excel file to begin.")
        self.info_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                color: #495057;
            }
        """)
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

    def select_file(self):
        """Open a file dialog to select the Excel file."""
        self.clear_messages()
        
        start_dir = os.path.dirname(self.filename) if self.filename else os.path.expanduser("~")
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            start_dir,
            "Excel Files (*.xlsx *.xls);;All Files (*)",
            options=options
        )
        
        if file_path:
            self.filename = file_path
            self.file_path_edit.setText(file_path)
            self.reload_button.setEnabled(True)
            self.update_recent_files(file_path)
            self.load_file()

    def _update_recent_list(self):
        """Update the recent files list widget."""
        self.recent_list.clear()
        for path in self.recent_paths:
            item = QListWidgetItem(path)
            self.recent_list.addItem(item)

    def update_recent_files(self, file_path):
        """Update the list of recent files."""
        if file_path in self.recent_paths:
            self.recent_paths.remove(file_path)
        self.recent_paths.insert(0, file_path)
        self.recent_paths = self.recent_paths[:self.MAX_RECENT]
        self._update_recent_list()

    def select_recent(self, item):
        """Load a file from the recent files list."""
        file_path = item.text()
        if os.path.exists(file_path):
            self.filename = file_path
            self.file_path_edit.setText(file_path)
            self.reload_button.setEnabled(True)
            self.load_file()
        else:
            self.recent_paths.remove(file_path)
            self._update_recent_list()
            self.Error.no_file_error()

    def reload_file(self):
        """Reload the currently selected Excel file."""
        if self.filename:
            self.load_file()
        else:
            self.Error.no_file_error()

    def load_file(self):  # Fixed indentation - should be at same level as other methods
            """Read and process the Excel file."""
            self.clear_messages()
            self.info_label.setText("Loading file...")
            
            try:
                # Read the Excel file directly
                df = pd.read_excel(self.filename)
                
                # Convert all numeric columns to float for compatibility
                for col in df.columns:
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col] = df[col].astype(float)
                
                # Create domain with all columns as continuous variables
                domain = Domain(
                    [ContinuousVariable(str(col)) for col in df.columns],
                    []  # no class variables
                )
                
                # Create Orange table
                X = df.values.astype(float)
                table = Table.from_numpy(domain, X)
                
                # Send the data and update info
                self.Outputs.data.send(table)
                self.info_label.setText(
                    f"Loaded {len(df)} rows and {len(df.columns)} columns."
                )
                
            except Exception as e:
                self.Error.read_error()
                self.Outputs.data.send(None)
                self.info_label.setText("Error loading file.")
                print(f"Error reading Excel file: {e}")

    def clear_messages(self):
        """Clear all messages."""
        self.Error.clear()
        self.Warning.clear()

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(ExcelReaderWidget).run()