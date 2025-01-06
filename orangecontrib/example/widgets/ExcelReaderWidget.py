import pandas as pd
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui, widget, settings
from PyQt5.QtWidgets import QSizePolicy, QFileDialog, QVBoxLayout
from PyQt5.QtCore import Qt

class ExcelReaderWidget(widget.OWWidget):
    """Widget for reading Excel files into Orange data tables."""
    
    # Widget metadata
    name = "Excel Reader"
    description = "Reads data from an Excel file and outputs a data table."
    icon = "icons/excel.svg"
    priority = 100
    keywords = ["widget", "excel", "data", "import"]
    want_main_area = False
    resizing_enabled = True

    # Output channel
    class Outputs:
        data = widget.Output("Data", Table, default=True)
    
    # Error handling
    class Error(widget.OWWidget.Error):
        read_error = widget.Msg("Failed to read the Excel file.")
        no_file_error = widget.Msg("No file selected.")
    
    # Settings
    filename = settings.Setting("")

    def __init__(self):
        super().__init__()
        self.setup_gui()

    def setup_gui(self):
        """Initialize the user interface."""
        # Set the default size and allow resizing
        self.setMinimumSize(400, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Create main layout
        layout = QVBoxLayout()
        self.controlArea.setLayout(layout)

        # File selection box
        file_box = gui.vBox(self.controlArea, "File Selection")
        
        # Add a text box to display the selected file path
        self.file_path_edit = gui.lineEdit(
            file_box, self, "filename", 
            label="Selected File:", 
            callback=None,
            readOnly=True,
            controlWidth=300
        )

        # Buttons box
        button_box = gui.hBox(file_box)
        
        # Add buttons for file selection and reload
        self.select_button = gui.button(
            button_box, self, "Select File", 
            callback=self.select_file,
            tooltip="Select an Excel file to import"
        )
        
        self.reload_button = gui.button(
            button_box, self, "Reload", 
            callback=self.reload_file,
            tooltip="Reload the current Excel file"
        )
        self.reload_button.setEnabled(False)

        # Info label
        self.info_label = gui.widgetLabel(
            self.controlArea, 
            "Select an Excel file to begin."
        )
        self.info_label.setAlignment(Qt.AlignCenter)

    def select_file(self):
        """Open a file dialog to select the Excel file."""
        self.clear_messages()
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls);;All Files (*)",
            options=options
        )
        
        if file_path:
            self.filename = file_path
            self.file_path_edit.setText(file_path)
            self.reload_button.setEnabled(True)
            self.load_file()

    def reload_file(self):
        """Reload the currently selected Excel file."""
        if self.filename:
            self.load_file()
        else:
            self.Error.no_file_error()

    def load_file(self):
        """Read and process the Excel file."""
        self.clear_messages()
        self.info_label.setText("Loading file...")
        
        try:
            # Read the Excel file into a pandas DataFrame
            df = pd.read_excel(self.filename)
            
            # Create domain from DataFrame columns
            domain = Domain([
                ContinuousVariable(col) if pd.api.types.is_numeric_dtype(df[col])
                else StringVariable(col) 
                for col in df.columns
            ])
            
            # Create Orange table from DataFrame
            table = Table.from_numpy(domain, df.to_numpy())
            
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
        """Clear all error messages."""
        self.Error.clear()

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(ExcelReaderWidget).run()