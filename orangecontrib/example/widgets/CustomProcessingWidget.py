import sys
import ast
import inspect
import numpy as np
import pandas as pd
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets.settings import Setting
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QApplication, 
                            QSizePolicy, QWidget, QPushButton, QTextEdit, 
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt

DEFAULT_CODE = """def fn_0(arr_0, arr_1):
    '''Example: Sum of two columns
    arr_0: First column values
    arr_1: Second column values
    Returns array of sums
    '''
    return arr_0 + arr_1

def fn_1(arr_0):
    '''Example: Double the values
    arr_0: Input column values
    Returns array of doubled values
    '''
    return arr_0 * 2

def fn_2(arr_0, arr_1, arr_2):
    '''Example: Custom calculation
    Returns single value for each row
    '''
    return np.where(arr_2 > 0, arr_0 / arr_1, arr_0 * arr_1)"""

class InputMappingTable(QTableWidget):
    """Table showing mapping between input array names and column names."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Input Name", "Column Name"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def update_mapping(self, mapping):
        """Update table with new mapping."""
        self.setRowCount(len(mapping))
        for i, (arr_name, col_name) in enumerate(mapping.items()):
            self.setItem(i, 0, QTableWidgetItem(arr_name))
            self.setItem(i, 1, QTableWidgetItem(col_name))

class CustomProcessingWidget(OWWidget):
    name = "Custom Processing"
    description = "Process data using custom Python code with automatic column generation"
    icon = "icons/CustomProcess.svg"
    priority = 100
    keywords = ["custom", "python", "process"]
    
    # Settings
    code = Setting(DEFAULT_CODE)
    
    class Inputs:
        data = Input("Data", Table)
        
    class Outputs:
        data = Output("Processed Data", Table)
        
    def __init__(self):
        super().__init__()
        self.data = None
        self.input_mapping = {}
        self.setup_gui()
        
    def setup_gui(self):
        # Main layout with left and right sections
        main_layout = QHBoxLayout()
        left_panel = QWidget()
        right_panel = QWidget()
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        right_panel.setLayout(right_layout)
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        # Left panel - Input mapping table
        mapping_box = gui.widgetBox(left_panel, "Input Column Mapping")
        self.mapping_table = InputMappingTable()
        mapping_box.layout().addWidget(self.mapping_table)
        
        # Right panel - Code editor
        code_box = gui.widgetBox(right_panel, "Python Code")
        self.code_edit = QTextEdit()
        self.code_edit.setPlainText(self.code)
        self.code_edit.textChanged.connect(self.code_changed)
        code_box.layout().addWidget(self.code_edit)
        
        # Status and info
        self.info_label = QLabel()
        right_layout.addWidget(self.info_label)
        
        # Process button
        self.process_button = gui.button(
            right_panel, self, "Process Data",
            callback=self.process_data
        )
        
        # Set the main layout
        widget = QWidget()
        widget.setLayout(main_layout)
        self.controlArea.layout().addWidget(widget)
        
    def code_changed(self):
        """Handle code changes."""
        self.code = self.code_edit.toPlainText()
        
    def update_input_mapping(self):
        """Update input mapping when data changes."""
        if self.data is None:
            return
            
        column_names = [var.name for var in self.data.domain.attributes]
        self.input_mapping = {
            f"arr_{i}": name 
            for i, name in enumerate(column_names)
        }
        self.mapping_table.update_mapping(self.input_mapping)
        
        # Update info label
        self.info_label.setText(
            f"Available columns: {len(column_names)}\n"
            "Use input names (arr_0, arr_1, etc.) in your functions"
        )
        
    @Inputs.data
    def set_data(self, data):
        """Handle input data."""
        self.data = data
        if data is not None:
            self.update_input_mapping()
            self.process_button.setEnabled(True)
        else:
            self.info_label.setText("No data loaded")
            self.process_button.setEnabled(False)
            self.mapping_table.setRowCount(0)
            
    def extract_functions(self, code):
        """Extract and validate functions from the code."""
        try:
            # Create namespace for code execution
            namespace = {'np': np, 'pd': pd}
            exec(code, namespace)
            
            # Get only the functions
            functions = {
                name: func for name, func in namespace.items()
                if inspect.isfunction(func) and name.startswith('fn_')
            }
            
            return functions
        except Exception as e:
            gui.messageBox(self, f"Error in code: {str(e)}")
            return {}
            
    def process_data(self):
        """Process the data using the custom code."""
        if self.data is None:
            return
            
        try:
            # Get functions from code
            functions = self.extract_functions(self.code)
            if not functions:
                gui.messageBox(self, "No valid functions found in code!")
                return
                
            # Convert input data to DataFrame
            df = pd.DataFrame(self.data.X, columns=[var.name for var in self.data.domain.attributes])
            
            # Create input arrays dictionary
            input_arrays = {
                arr_name: df[col_name].values 
                for arr_name, col_name in self.input_mapping.items()
            }
            
            # Process each function
            new_columns = {}
            for func_name, func in functions.items():
                # Get function parameters
                params = inspect.signature(func).parameters
                
                # Check if all required parameters are available
                if not all(param in input_arrays for param in params):
                    gui.messageBox(self, f"Missing input arrays for function {func_name}")
                    continue
                
                # Execute function with input arrays
                args = [input_arrays[param] for param in params]
                result = func(*args)
                
                # Convert result to numpy array if it's not already
                if not isinstance(result, np.ndarray):
                    result = np.full(len(df), result)
                
                # Store result
                new_columns[func_name] = result
            
            # Create new Orange table with additional columns
            new_domain = Domain(
                self.data.domain.attributes + tuple(
                    ContinuousVariable(name) for name in new_columns.keys()
                ),
                self.data.domain.class_vars,
                self.data.domain.metas
            )
            
            # Create new table
            new_data = Table.from_numpy(
                new_domain,
                np.column_stack([
                    self.data.X,
                    np.column_stack([new_columns[name] for name in new_columns])
                ]),
                self.data.Y,
                self.data.metas
            )
            
            # Send output
            self.Outputs.data.send(new_data)
            
            # Update status
            self.info_label.setText(
                f"Processing complete: {len(new_columns)} new columns added\n"
                f"Total columns: {len(new_domain.attributes)}"
            )
            
        except Exception as e:
            gui.messageBox(self, f"Error processing data: {str(e)}")

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(CustomProcessingWidget).run()