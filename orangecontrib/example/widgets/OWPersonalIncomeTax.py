import numpy as np
import hashlib
from Orange.data import Table, Domain, ContinuousVariable
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.widget import OWWidget, Input, Output
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout


class CustomSumWidget(OWWidget):
    name = "Custom Sum Widget"
    description = "Calculates the sum or weighted sum of two selected columns."
    icon = "icons/custom_sum_widget.svg"
    priority = 100
    keywords = ["widget", "custom sum", "weighted sum"]
    want_main_area = False
    resizing_enabled = False

    selected_column1 = Setting(0)
    selected_column2 = Setting(1)
    selected_primary_key = Setting(0)
    concatenate = Setting(False)
    disallow_duplicate_names = Setting(False)
    use_weights = Setting(False)
    weight1 = Setting(1.0)
    weight2 = Setting(1.0)

    class Inputs:
        data = Input("Data", Table)

    class Outputs:
        result = Output("Result", Table, default=True)

    def __init__(self):
        super().__init__()
        self.data = None
        self.column_names = []

        self.layout = QVBoxLayout()
        self.controlArea.setLayout(self.layout)

        # Dropdowns for column selection
        self.column1_combo = gui.comboBox(
            self.controlArea, self, "selected_column1", box="Select Column 1",
            callback=self.update_column1
        )
        self.column2_combo = gui.comboBox(
            self.controlArea, self, "selected_column2", box="Select Column 2",
            callback=self.update_column2
        )

        # Checkbox for concatenation
        self.concatenate_tickbox = gui.checkBox(
            self.controlArea, self, "concatenate", "Concatenate columns", callback=self.update_concatenate
        )

        # Checkbox for disallowing duplicate names
        self.duplicate_names_tickbox = gui.checkBox(
            self.controlArea, self, "disallow_duplicate_names", "Disallow duplicate names"
        )

        # Checkbox for using weights
        self.weights_tickbox = gui.checkBox(
            self.controlArea, self, "use_weights", "Use weights for summation", callback=self.update_weights
        )

        # Input fields for weights
        self.weight1_input = gui.doubleSpin(
            self.controlArea, self, "weight1", 0.1, 10.0, step=0.1, label="Weight 1"
        )
        self.weight2_input = gui.doubleSpin(
            self.controlArea, self, "weight2", 0.1, 10.0, step=0.1, label="Weight 2"
        )

        # Combo box for primary key
        self.primary_key_combo = gui.comboBox(
            self.controlArea, self, "selected_primary_key", box="Select Primary Key Column",
            callback=self.update_primary_key, enabled=not self.concatenate
        )

        # Calculate button
        self.calculate_button = gui.button(
            self.controlArea, self, "Calculate", callback=self.calculate_sum
        )

        # Table for results
        self.result_table = QTableWidget()
        self.layout.addWidget(self.result_table)

    def update_column1(self):
        self.selected_column1 = self.column1_combo.currentIndex()

    def update_column2(self):
        self.selected_column2 = self.column2_combo.currentIndex()

    def update_primary_key(self):
        self.selected_primary_key = self.primary_key_combo.currentIndex()

    def update_concatenate(self):
        self.primary_key_combo.setDisabled(self.concatenate)

    def update_weights(self):
        self.weight1_input.setEnabled(self.use_weights)
        self.weight2_input.setEnabled(self.use_weights)

    @Inputs.data
    def set_data(self, data):
        self.data = data
        self.column1_combo.clear()
        self.column2_combo.clear()
        self.primary_key_combo.clear()
        if data:
            self.column_names = [var.name for var in data.domain.attributes]
            for var in self.column_names:
                self.column1_combo.addItem(var)
                self.column2_combo.addItem(var)
                self.primary_key_combo.addItem(var)
            self.selected_column1 = 0
            self.selected_column2 = min(1, len(self.column_names) - 1)
            self.selected_primary_key = 0
        else:
            self.column_names = []
        self.clear_results()

    def clear_results(self):
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.Outputs.result.send(None)

    def calculate_sum(self):
        if not self.data:
            self.clear_results()
            return

        if self.selected_column1 >= len(self.column_names) or self.selected_column2 >= len(self.column_names):
            self.clear_results()
            return

        try:
            col1 = self.data[:, self.selected_column1].X.flatten()
            col2 = self.data[:, self.selected_column2].X.flatten()

            # Use the custom_sum_function for calculations
            result = self.custom_sum_function(col1, col2)

            if self.concatenate:
                try:
                    new_domain = Domain(self.data.domain.attributes + (ContinuousVariable("Result"),))
                    new_data = np.column_stack((self.data.X, result.reshape(-1, 1)))
                    new_table = Table(new_domain, new_data)
                except Exception as e:
                    print(f"Error during concatenation: {e}")
                    self.clear_results()
                    return
            else:
                try:
                    selected_var1 = self.data.domain[self.selected_column1]
                    selected_var2 = self.data.domain[self.selected_column2]
                    primary_key_var = self.data.domain[self.selected_primary_key]

                    result_name = "Result"
                    if self.disallow_duplicate_names:
                        result_name = self.get_unique_name(result_name, self.column_names)

                    result_var = ContinuousVariable(result_name)

                    new_domain = Domain([primary_key_var, selected_var1, selected_var2, result_var])
                    primary_key_col = self.data[:, self.selected_primary_key].X.flatten()
                    new_data = np.column_stack((primary_key_col, col1, col2, result))
                    new_table = Table(new_domain, new_data)
                except Exception as e:
                    print(f"Error during table creation: {e}")

                    try:
                        primary_key_name = primary_key_var.name
                        primary_key_hash = hashlib.sha256(primary_key_name.encode()).hexdigest()[:8]
                        primary_key_var = ContinuousVariable(f"{primary_key_name}_{primary_key_hash}")
                        primary_key_col = self.data[:, self.selected_primary_key].X.flatten()
                        new_domain = Domain([primary_key_var, selected_var1, selected_var2, result_var])
                        new_data = np.column_stack((primary_key_col, col1, col2, result))
                        new_table = Table(new_domain, new_data)
                    except Exception as e:
                        print(f"Error during table creation with hash fix: {e}")
                        self.clear_results()
                        return

            # Display the result in the table widget
            try:
                self.result_table.setRowCount(len(result))
                self.result_table.setColumnCount(4 if not self.concatenate else len(new_domain.attributes))
                headers = [primary_key_var.name] if not self.concatenate else []
                headers.extend([self.column_names[self.selected_column1], self.column_names[self.selected_column2], result_name])
                self.result_table.setHorizontalHeaderLabels(headers)
                for i in range(len(result)):
                    if not self.concatenate:
                        self.result_table.setItem(i, 0, QTableWidgetItem(str(primary_key_col[i])))
                    self.result_table.setItem(i, 1 if not self.concatenate else len(self.data.domain.attributes) - 1, QTableWidgetItem(str(col1[i])))
                    self.result_table.setItem(i, 2 if not self.concatenate else len(self.data.domain.attributes), QTableWidgetItem(str(col2[i])))
                    self.result_table.setItem(i, 3 if not self.concatenate else len(self.data.domain.attributes) + 1, QTableWidgetItem(str(result[i])))
            except Exception as e:
                print(f"Error displaying results: {e}")
                self.clear_results()
                return

            self.Outputs.result.send(new_table)
        except Exception as e:
            print(f"Error during calculation: {e}")
            self.clear_results()

    def custom_sum_function(self, col1, col2):
        """
        Custom logic for column calculations.
        Modify this function to implement any specific logic for calculations.
        Custom logic for calculating the result of two columns.
        Modify this logic as needed for your specific use case.
        Parameters:
            col1 (numpy.ndarray): The first selected column data.
            col2 (numpy.ndarray): The second selected column data.

        Returns:
            numpy.ndarray: Result of the custom calculation.
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
            result.append(taxesFee)

        return np.array(result)

    def display_results(self, table, result_name):
        self.result_table.setRowCount(len(table))
        headers = ["Primary Key", "Column 1", "Column 2", result_name]
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        for i, row in enumerate(table.X):
            for j, value in enumerate(row):
                self.result_table.setItem(i, j, QTableWidgetItem(str(value)))

    def get_unique_name(self, base_name, existing_names):
        if base_name not in existing_names:
            return base_name
        counter = 1
        new_name = f"{base_name}_{counter}"
        while new_name in existing_names:
            counter += 1
            new_name = f"{base_name}_{counter}"
        return new_name

    def send_report(self):
        self.report_caption("Custom Sum Widget Report")
        self.report_items("Settings", [("Column 1", self.column_names[self.selected_column1]),
                                       ("Column 2", self.column_names[self.selected_column2]),
                                       ("Weights Used", self.use_weights),
                                       ("Weight 1", self.weight1),
                                       ("Weight 2", self.weight2),
                                       ("Concatenate", self.concatenate)])


if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(CustomSumWidget).run()
