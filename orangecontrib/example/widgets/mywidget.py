import numpy as np
import hashlib
from Orange.data import Table, Domain, ContinuousVariable
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.widget import OWWidget, Input, Output
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout

class SumColumnsWidget(OWWidget):
    name = "Sum Columns Widget"
    description = "Calculates the sum of two selected columns."
    icon = "icons/mywidget.svg"
    priority = 100
    keywords = ["widget", "data"]
    want_main_area = False
    resizing_enabled = False
    
    selected_column1 = Setting(0)
    selected_column2 = Setting(1)
    selected_primary_key = Setting(0)
    concatenate = Setting(False)
    disallow_duplicate_names = Setting(False)
    
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

        # Create dropdowns for column selection
        self.column1_combo = gui.comboBox(
            self.controlArea, self, "selected_column1", box="Select Column 1",
            callback=self.update_column1
        )
        self.column2_combo = gui.comboBox(
            self.controlArea, self, "selected_column2", box="Select Column 2",
            callback=self.update_column2
        )

        # Tickbox to choose whether to concatenate columns
        self.concatenate_tickbox = gui.checkBox(
            self.controlArea, self, "concatenate", "Concatenate columns", callback=self.update_concatenate
        )

        # Tickbox to disallow duplicate names
        self.duplicate_names_tickbox = gui.checkBox(
            self.controlArea, self, "disallow_duplicate_names", "Disallow duplicate names"
        )

        # Combo box to select primary key if not concatenating
        self.primary_key_combo = gui.comboBox(
            self.controlArea, self, "selected_primary_key", box="Select Primary Key Column",
            callback=self.update_primary_key, enabled=not self.concatenate
        )

        # Add a button to trigger calculation
        self.calculate_button = gui.button(
            self.controlArea, self, "Calculate", callback=self.calculate_sum
        )

        # Table widget to display the results
        self.result_table = QTableWidget()
        self.layout.addWidget(self.result_table)
        
    def update_column1(self):
        # print(f"update_column1: {self.column1_combo.currentIndex()}")
        self.selected_column1 = self.column1_combo.currentIndex()

    def update_column2(self):
        # print(f"update_column2: {self.column2_combo.currentIndex()}")
        self.selected_column2 = self.column2_combo.currentIndex()

    def update_primary_key(self):
        # print(f"update_primary_key: {self.primary_key_combo.currentIndex()}")
        self.selected_primary_key = self.primary_key_combo.currentIndex()

    def update_concatenate(self):
        # print(f"update_concatenate: {self.concatenate}")
        self.primary_key_combo.setDisabled(self.concatenate)

    @Inputs.data
    def set_data(self, data):
        # print(f"set_data: {data}")
        self.data = data
        self.column1_combo.clear()
        self.column2_combo.clear()
        self.primary_key_combo.clear()
        if data:
            self.column_names = [var.name for var in data.domain.attributes]
            # print(f"column_names: {self.column_names}")
            for var in self.column_names:
                self.column1_combo.addItem(var)
                self.column2_combo.addItem(var)
                self.primary_key_combo.addItem(var)
            # Reset selected columns to valid indices
            self.selected_column1 = 0
            self.selected_column2 = min(1, len(self.column_names) - 1)
            self.selected_primary_key = 0
        else:
            self.column_names = []
        self.clear_results()
        
    def clear_results(self):
        # print("clear_results")
        self.result_table.clear()
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.Outputs.result.send(None)

    def calculate_sum(self):
        # print("calculate_sum")
        if not self.data:
            # print("No data available")
            self.clear_results()
            return

        if self.selected_column1 >= len(self.column_names) or self.selected_column2 >= len(self.column_names):
            # print(f"Invalid column selection: selected_column1={self.selected_column1}, selected_column2={self.selected_column2}")
            self.clear_results()
            return

        try:
            col1 = self.data[:, self.selected_column1].X.flatten()
            col2 = self.data[:, self.selected_column2].X.flatten()
            result = col1 + col2
            # print(f"col1: {col1}, col2: {col2}, result: {result}")

            if self.concatenate:
                try:
                    # Concatenate with proper data domains handling
                    new_domain = Domain(self.data.domain.attributes + (ContinuousVariable("Result"),))
                    new_data = np.column_stack((self.data.X, result.reshape(-1, 1)))
                    new_table = Table(new_domain, new_data)
                except Exception as e:
                    print(f"Error during concatenation: {e}")
                    self.clear_results()
                    return
            else:
                try:
                    # Select variables
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

                    # Fix for duplicate names by appending a hash to the primary key column name
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
                # print("Results displayed in the table")
            except Exception as e:
                print(f"Error displaying results: {e}")
                self.clear_results()
                return

            self.Outputs.result.send(new_table)
        except Exception as e:
            print(f"Error during calculation: {e}")
            self.clear_results()
            
    def get_unique_name(self, base_name, existing_names):
        """Generate a unique name by appending a number to the base name."""
        if base_name not in existing_names:
            return base_name
        counter = 1
        new_name = f"{base_name}_{counter}"
        while new_name in existing_names:
            counter += 1
            new_name = f"{base_name}_{counter}"
        return new_name

    def send_report(self):
        self.report_caption("Column Sum Widget Report")
        self.report_items("Settings", [("Selected Column 1", self.column_names[self.selected_column1]),
                                       ("Selected Column 2", self.column_names[self.selected_column2]),
                                       ("Concatenate", self.concatenate),
                                       ("Primary Key Column", self.column_names[self.selected_primary_key] if not self.concatenate else "N/A"),
                                       ("Disallow Duplicate Names", self.disallow_duplicate_names)])

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(SumColumnsWidget).run()