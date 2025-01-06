import numpy as np
import hashlib
from Orange.data import Table, Domain, ContinuousVariable
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.widget import OWWidget, Input, Output
from PyQt5.QtWidgets import QTableWidget, QVBoxLayout

class TaxCalculatorWidget(OWWidget):  # Changed from SumColumnsWidget
    """Widget that calculates tax based on salary and dependents."""
    
    # Widget metadata
    name = "Tax Calculator"  # Changed from "Sum Columns Widget"
    description = "Calculates income tax based on salary and number of dependents."
    icon = "icons/mywidget.svg"
    priority = 100
    keywords = ["widget", "tax", "calculator"]  # Updated keywords
    want_main_area = False
    resizing_enabled = False
    
    # Settings
    selected_column1 = Setting(0)
    selected_column2 = Setting(1)
    selected_primary_key = Setting(0)
    concatenate = Setting(False)
    
    # I/O definitions
    class Inputs:
        data = Input("Data", Table)

    class Outputs:
        result = Output("Result", Table, default=True)
    
    def __init__(self):
        """Initialize the widget and setup UI components."""
        super().__init__()
        self.data = None
        self.column_names = []
        self.previous_columns = {}
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize and setup the user interface components."""
        self.layout = QVBoxLayout()
        self.controlArea.setLayout(self.layout)

        # Column selection controls
        self.column1_combo = gui.comboBox(
            self.controlArea, self, "selected_column1", 
            box="Select Salary Column",  # Changed label
            callback=lambda: self._update_selection('column1')
        )
        self.column2_combo = gui.comboBox(
            self.controlArea, self, "selected_column2",
            box="Select Dependents Column",  # Changed label
            callback=lambda: self._update_selection('column2')
        )

        # Concatenation controls
        self.concatenate_tickbox = gui.checkBox(
            self.controlArea, self, "concatenate", 
            "Concatenate columns", callback=self._toggle_primary_key
        )

        self.primary_key_combo = gui.comboBox(
            self.controlArea, self, "selected_primary_key",
            box="Select Primary Key Column",
            callback=lambda: self._update_selection('primary_key'),
            enabled=not self.concatenate
        )

        gui.button(self.controlArea, self, "Calculate", callback=self.calculate_sum)
        self.result_table = QTableWidget()

    def _update_selection(self, field):
        """Update the selected column indices."""
        if field == 'column1':
            self.selected_column1 = self.column1_combo.currentIndex()
        elif field == 'column2':
            self.selected_column2 = self.column2_combo.currentIndex()
        elif field == 'primary_key':
            self.selected_primary_key = self.primary_key_combo.currentIndex()

    def _toggle_primary_key(self):
        """Toggle primary key combo box based on concatenate checkbox."""
        self.primary_key_combo.setDisabled(self.concatenate)

    @Inputs.data
    def set_data(self, data):
        """Handle input data and update UI accordingly."""
        self.data = data
        self._reset_combos()
        
        if data:
            self.column_names = [var.name for var in data.domain.attributes]
            self._populate_combos()
            self.calculate_sum()
        else:
            self.column_names = []
            self.previous_columns = {}

    def _reset_combos(self):
        """Clear all combo boxes."""
        for combo in [self.column1_combo, self.column2_combo, self.primary_key_combo]:
            combo.clear()

    def _populate_combos(self):
        """Populate combo boxes with column names."""
        for var in self.column_names:
            for combo in [self.column1_combo, self.column2_combo, self.primary_key_combo]:
                combo.addItem(var)
        
        # Set default selections
        self.selected_column1 = 0
        self.selected_column2 = min(1, len(self.column_names) - 1)
        self.selected_primary_key = 0

    def _clear_results(self):
        """Clear the results table and output."""
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.Outputs.result.send(None)

    def custom_sum_function(self, col1, col2):
        """
        Calculate income tax based on salary and number of dependents.
        
        Parameters:
            col1 (numpy.ndarray): Salary data
            col2 (numpy.ndarray): Number of dependents data

        Returns:
            numpy.ndarray: Calculated tax amounts
        """
        personalDeduction = 11000000
        dependentsDeduction = 4400000
        result = []

        for salary, person in zip(col1, col2):
            incomeTaxes = salary - personalDeduction - dependentsDeduction * person
            taxesFee = 0
            if incomeTaxes > 80000000:
                taxesFee = incomeTaxes * 0.35 - 18150000 - 9850000
            elif incomeTaxes > 52000000:
                taxesFee = incomeTaxes * 0.30 - 9750000 - 5850000
            elif incomeTaxes > 32000000:
                taxesFee = incomeTaxes * 0.25 - 4750000 - 3250000
            elif incomeTaxes > 18000000:
                taxesFee = incomeTaxes * 0.20 - 1950000 - 1650000
            elif incomeTaxes > 10000000:
                taxesFee = incomeTaxes * 0.15 - 750000 - 750000
            elif incomeTaxes > 5000000:
                taxesFee = incomeTaxes * 0.10 - 250000 - 250000
            else:
                taxesFee = incomeTaxes * 0.05
            result.append(max(0, taxesFee))  # Ensure tax is not negative

        return np.array(result)

    def calculate_sum(self):
        """Calculate tax based on salary and dependents."""
        if not self._validate_input():
            self._clear_results()
            return

        try:
            # Get column data
            salary_data = self.data[:, self.selected_column1].X.flatten()
            dependents_data = self.data[:, self.selected_column2].X.flatten()
            result = self.custom_sum_function(salary_data, dependents_data)  # Changed this line

            # Create output table
            new_table = self._create_output_table(salary_data, dependents_data, result)
            if new_table:
                self.Outputs.result.send(new_table)

        except Exception as e:
            print(f"Error during tax calculation: {e}")
            self._clear_results()

    def _validate_input(self):
        """Validate input data and column selections."""
        if not self.data:
            return False
        if self.selected_column1 >= len(self.column_names) or \
           self.selected_column2 >= len(self.column_names):
            return False
        return True

    def _create_output_table(self, col1, col2, result):
        """Create output table based on concatenation setting."""
        try:
            if self.concatenate:
                return self._create_concatenated_table(result)
            return self._create_separate_table(col1, col2, result)
        except Exception as e:
            print(f"Error creating output table: {e}")
            return None

    def _create_concatenated_table(self, result):
        """Create a table with concatenated columns."""
        new_domain = Domain(self.data.domain.attributes + (ContinuousVariable("Result"),))
        new_data = np.column_stack((self.data.X, result.reshape(-1, 1)))
        return Table(new_domain, new_data)

    def _create_separate_table(self, col1, col2, result):
        """Create a table with separate columns including primary key."""
        try:
            # Get variables
            selected_var1 = self.data.domain[self.selected_column1]
            selected_var2 = self.data.domain[self.selected_column2]
            primary_key_var = self.data.domain[self.selected_primary_key]
            result_var = ContinuousVariable("Result")

            # Create unique primary key name if needed
            if len({primary_key_var.name, selected_var1.name, selected_var2.name}) < 3:
                primary_key_var = self._create_unique_primary_key(primary_key_var.name)

            new_domain = Domain([primary_key_var, selected_var1, selected_var2, result_var])
            primary_key_col = self.data[:, self.selected_primary_key].X.flatten()
            new_data = np.column_stack((primary_key_col, col1, col2, result))
            return Table(new_domain, new_data)
        except Exception as e:
            print(f"Error in create_separate_table: {e}")
            return None

    def _create_unique_primary_key(self, base_name):
        """Create a unique primary key variable name."""
        key_hash = hashlib.sha256(base_name.encode()).hexdigest()[:8]
        return ContinuousVariable(f"{base_name}_{key_hash}")

    def send_report(self):
        """Generate widget report."""
        self.report_caption("Column Sum Widget Report")
        self.report_items("Settings", [
            ("Selected Column 1", self.column_names[self.selected_column1]),
            ("Selected Column 2", self.column_names[self.selected_column2]),
            ("Concatenate", self.concatenate),
            ("Primary Key Column", self.column_names[self.selected_primary_key] \
             if not self.concatenate else "N/A")
        ])

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(TaxCalculatorWidget).run()  # Changed from SumColumnsWidget