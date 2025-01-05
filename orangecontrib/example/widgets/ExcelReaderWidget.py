import pandas as pd
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui, widget, settings
from PyQt5.QtWidgets import QSizePolicy, QFileDialog, QLineEdit

class ExcelReaderWidget(widget.OWWidget):
    name = "Excel Reader Widget"
    description = "Reads data from an Excel file and outputs a data table."
    icon = "icons/excel.svg"
    priority = 100
    keywords = ["widget", "excel", "data"]
    want_main_area = False
    resizing_enabled = True

    class Outputs:
        data = widget.Output("Data", Table, default=True)
    
    class Error(widget.OWWidget.Error):
        read_error = widget.Msg("Failed to read the Excel file.")
    
    filename = settings.Setting("")

    def __init__(self):
        super().__init__()

        # Set the default size and allow resizing
        self.setMinimumSize(400, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Add a button to select the Excel file
        self.file_button = gui.button(self.controlArea, self, "Select Excel File", callback=self.select_file)

        # Add a text box to display the selected file path
        self.file_path_edit = gui.lineEdit(self.controlArea, self, "", box="Selected File", callback=None)
        self.file_path_edit.setReadOnly(True)

    def select_file(self):
        # Open a file dialog to select the Excel file
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Excel File", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_path:
            self.filename = file_path
            self.file_path_edit.setText(file_path)
            self.read_excel_file(file_path)

    def read_excel_file(self, file_path):
        try:
            # Read the Excel file into a pandas DataFrame
            df = pd.read_excel(file_path)
            # Create Orange data table from the DataFrame
            domain = Domain([ContinuousVariable(col) if pd.api.types.is_numeric_dtype(df[col]) else StringVariable(col) for col in df.columns])
            table = Table.from_numpy(domain, df.to_numpy())

            self.Outputs.data.send(table)
        except Exception as e:
            self.Error.read_error()
            self.Outputs.data.send(None)
            print(f"Error reading Excel file: {e}")

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(ExcelReaderWidget).run()