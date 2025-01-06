import numpy as np
from Orange.data import Table, Domain
from Orange.widgets import gui
from Orange.widgets.widget import OWWidget, Input, Output
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout

class CleanTableWidget(OWWidget):
    """Widget that cleans a table by removing constant columns and rows with empty values."""

    # Widget metadata
    name = "Clean Table Widget"
    description = "Removes constant columns and rows with empty values."
    icon = "icons/mywidget.svg"
    priority = 100
    keywords = ["widget", "data", "clean"]
    want_main_area = False
    resizing_enabled = True  # Allow resizing

    # I/O definitions
    class Inputs:
        data = Input("Data", Table)

    class Outputs:
        result = Output("Result", Table, default=True)

    def __init__(self):
        """Initialize the widget and setup UI components."""
        super().__init__()
        self.data = None

        # Setup UI
        self._setup_ui()

        # Set the default size of the widget
        self.resize(800, 600)  # Width: 800, Height: 600

    def _setup_ui(self):
        """Initialize and setup the user interface components."""
        self.layout = QVBoxLayout()
        self.controlArea.setLayout(self.layout)

        # Add a button to trigger cleaning
        gui.button(self.controlArea, self, "Clean Table", callback=self.clean_table)
        self.result_table = QTableWidget()
        self.layout.addWidget(self.result_table)

    @Inputs.data
    def set_data(self, data):
        """Handle input data and update UI accordingly."""
        self.data = data
        self.clean_table()

    def clean_table(self):
        """Clean the input table and create output table."""
        if not self.data:
            self._clear_results()
            return

        try:
            clean_data = self._remove_constant_columns(self.data)
            clean_data = self._remove_rows_with_empty_values(clean_data)
            self.Outputs.result.send(clean_data)
            self._display_results(clean_data)
        except Exception as e:
            print(f"Error during cleaning: {e}")
            self._clear_results()

    def _remove_constant_columns(self, data):
        """Remove columns that have the same value in all rows or are entirely empty."""
        new_attributes = [var for var in data.domain.attributes if not self._is_constant_column(data, var)]
        new_domain = Domain(new_attributes)
        new_data = data.transform(new_domain)
        return new_data

    def _is_constant_column(self, data, var):
        """Check if a column is constant (same value in all rows or all empty)."""
        column_values = data[:, var].X.flatten()
        unique_values = np.unique(column_values[~np.isnan(column_values)])
        return len(unique_values) <= 1

    def _remove_rows_with_empty_values(self, data):
        """Remove rows that contain empty values."""
        mask = ~np.isnan(data.X).any(axis=1)
        clean_data = data[mask]
        return clean_data

    def _clear_results(self):
        """Clear the results table and output."""
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.Outputs.result.send(None)

    def _display_results(self, clean_data):
        """Display the cleaned data in the result table."""
        self.result_table.setRowCount(len(clean_data))
        self.result_table.setColumnCount(len(clean_data.domain.attributes))
        headers = [var.name for var in clean_data.domain.attributes]
        self.result_table.setHorizontalHeaderLabels(headers)
        for i in range(len(clean_data)):
            for j, var in enumerate(clean_data.domain.attributes):
                value = clean_data[i, var].value if getattr(var, "is_discrete", False) else clean_data[i, var]
                self.result_table.setItem(i, j, QTableWidgetItem(str(value)))
        print("Cleaned data displayed in the table")

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(CleanTableWidget).run()