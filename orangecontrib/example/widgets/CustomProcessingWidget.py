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
    want_main_area = True  # Enable main area
    
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
        self.resize(1200, 800)

    def setup_gui(self):
        # Control Area (Left Side) - For execution status
        status_box = gui.widgetBox(self.controlArea, "Execution Status")
        self.status_text = gui.widgetLabel(status_box, "Ready")
        self.status_text.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                min-height: 100px;
            }
        """)

        # Main Area (Right Side)
        main_widget = QWidget()  # Create a main widget
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.mainArea.layout().addWidget(main_widget)  # Add to mainArea
        
        # Split into upper and lower sections
        upper_widget = QWidget()
        upper_layout = QHBoxLayout()
        upper_widget.setLayout(upper_layout)
        
        # Input mapping table section
        mapping_box = gui.widgetBox(upper_widget, "Input Column Mapping")
        mapping_box.setMinimumWidth(300)  # Set minimum width
        self.mapping_table = InputMappingTable()
        mapping_box.layout().addWidget(self.mapping_table)
        upper_layout.addWidget(mapping_box)
        
        # Code editor section
        code_box = gui.widgetBox(upper_widget, "Python Code")
        code_box.setMinimumWidth(500)  # Set minimum width
        self.code_edit = QTextEdit()
        self.code_edit.setPlainText(self.code)
        self.code_edit.textChanged.connect(self.code_changed)
        code_box.layout().addWidget(self.code_edit)
        upper_layout.addWidget(code_box, stretch=2)
        
        # Add upper section to main layout
        main_layout.addWidget(upper_widget)
        
        # Lower section for info and buttons
        lower_widget = QWidget()
        lower_layout = QHBoxLayout()
        lower_widget.setLayout(lower_layout)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("padding: 5px;")
        lower_layout.addWidget(self.info_label)
        
        # Process button
        self.process_button = QPushButton("Process Data")
        self.process_button.clicked.connect(self.process_data)
        self.process_button.setEnabled(False)
        self.process_button.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #007bff;
                color: white;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        lower_layout.addWidget(self.process_button)
        
        # Add lower section to main layout
        main_layout.addWidget(lower_widget)

    def update_status(self, message, is_error=False):
        """Update status message in the control area."""
        color = "#dc3545" if is_error else "#28a745"  # red for error, green for success
        self.status_text.setStyleSheet(f"""
            QLabel {{
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                min-height: 100px;
                color: {color};
            }}
        """)
        self.status_text.setText(message)
        
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
                self.update_status("No valid functions found in code!", True)
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
                    self.update_status(f"Missing input arrays for function {func_name}", True)
                    return
                
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
            success_message = (
                f"Processing complete:\n"
                f"- {len(new_columns)} new columns added\n"
                f"- Total columns: {len(new_domain.attributes)}\n"
                f"- Rows processed: {len(df)}"
            )
            self.update_status(success_message)
            
        except Exception as e:
            import traceback
            error_message = (
                f"Error processing data:\n"
                f"{str(e)}\n\n"
                f"Traceback:\n{traceback.format_exc()}"
            )
            self.update_status(error_message, True)

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(CustomProcessingWidget).run()