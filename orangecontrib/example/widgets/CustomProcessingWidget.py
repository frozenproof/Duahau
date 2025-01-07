import sys
import ast
import inspect
import numpy as np
import pandas as pd
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets.settings import Setting
# Add to imports
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QApplication, 
                            QSizePolicy, QWidget, QPushButton, QTextEdit, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
                            QFileDialog)
import os
from datetime import datetime

from PyQt5.QtCore import Qt

# Update DEFAULT_CODE with file operation imports and example
DEFAULT_CODE = """# Common imports for file operations
import os
from pathlib import Path
from datetime import datetime

# Current working directory is available as 'work_dir'
# Example: print(f"Working in: {work_dir}")

def fn_0(arr_0, arr_1):
    '''Example: Sum and save to file
    arr_0, arr_1: Input columns
    Returns array of sums and saves results
    '''
    result = arr_0 + arr_1
    
    # Example: Save results with timestamp
    # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # output_file = Path(work_dir) / f'sum_result_{timestamp}.txt'
    # np.savetxt(output_file, result)
    
    return result

def fn_1(arr_0):
    '''Example: Load config and process
    arr_0: Input values
    Returns processed values
    '''
    # Example: Read from config file if exists
    # config_file = Path(work_dir) / 'config.yaml'
    multiplier = 2  # default value
    
    # if config_file.exists():
    #     import yaml  # import only if needed
    #     with open(config_file, 'r') as f:
    #         config = yaml.safe_load(f)
    #         multiplier = config.get('multiplier', multiplier)
    
    return arr_0 * multiplier"""


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
    
    # Add new settings
    # Settings with version control
    settings_version = 2  # Increment this when making significant changes to defaults
    settings_changed_time = Setting("2025-01-07 02:13:06")  # Current timestamp
    code = Setting(DEFAULT_CODE)
    auto_process = Setting(True)  # New setting for auto-processing
    
    class Inputs:
        data = Input("Data", Table)
        
    class Outputs:
        data = Output("Processed Data", Table)

    @classmethod
    def migrate_settings(cls, settings, version):
        """Migrate settings to newer version."""
        if version < 2:
            # Update code to new default
            settings["code"] = DEFAULT_CODE
            settings["settings_changed_time"] = "2025-01-07 02:13:06"
        
        # Example of how to handle future versions
        # if version < 3:
        #     # Handle migration to version 3
        #     pass

    def save_settings(self):
        """Override save_settings to update timestamp."""
        self.settings_changed_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        super().save_settings()

    def load_settings(self):
        """Override load_settings to handle version checking."""
        super().load_settings()
        
        # Check if settings are from a newer version
        try:
            settings_time = datetime.strptime(self.settings_changed_time, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.strptime("2025-01-07 02:13:06", "%Y-%m-%d %H:%M:%S")
            
            if settings_time > current_time:
                # Settings are from a future version, reset to defaults
                self.code = DEFAULT_CODE
                self.settings_changed_time = "2025-01-07 02:13:06"
                
        except (ValueError, TypeError):
            # If there's any error parsing dates, reset to defaults
            self.code = DEFAULT_CODE
            self.settings_changed_time = "2025-01-07 02:13:06"
            
    def __init__(self):
        super().__init__()
        self.data = None
        self.input_mapping = {}
        self.work_dir = os.getcwd()  # Get current working directory
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

        # Add auto-process checkbox
        auto_process_box = gui.widgetBox(self.controlArea, "Settings")
        self.auto_process_cb = gui.checkBox(
            auto_process_box, self, 'auto_process',
            'Auto-process on data load',
            tooltip='Automatically process data when new data is loaded',
            callback=self.auto_process_changed
        )

        # Add working directory display
        work_dir_box = gui.widgetBox(self.controlArea, "Working Directory")
        self.dir_label = QLabel(f"Current directory:\n{self.work_dir}")
        self.dir_label.setStyleSheet("""
            QLabel {
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 5px;
                word-wrap: break-word;
            }
        """)
        self.dir_label.setWordWrap(True)
        work_dir_box.layout().addWidget(self.dir_label)

        # Main Area (Right Side)
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.mainArea.layout().addWidget(main_widget)
        
        # Split into upper and lower sections
        upper_widget = QWidget()
        upper_layout = QHBoxLayout()
        upper_widget.setLayout(upper_layout)
        
        # Input mapping table section
        mapping_box = gui.widgetBox(upper_widget, "Input Column Mapping")
        mapping_box.setMinimumWidth(300)
        self.mapping_table = InputMappingTable()
        mapping_box.layout().addWidget(self.mapping_table)
        upper_layout.addWidget(mapping_box)
        
        # Code editor section
        code_box = gui.widgetBox(upper_widget, "Python Code")
        code_box.setMinimumWidth(500)
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
        
        # Status indicator for auto-process
        self.status_indicator = QLabel()
        self.status_indicator.setStyleSheet("""
            QLabel {
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
        """)
        lower_layout.addWidget(self.status_indicator)
        
        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("padding: 5px;")
        lower_layout.addWidget(self.info_label)
        
        # Add spacer to push button to the right
        lower_layout.addStretch()
        
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

        # Initialize status
        self.update_status_indicator()

    def update_status_indicator(self):
        """Update the status indicator based on auto-process setting."""
        if self.auto_process:
            self.status_indicator.setText("🔄 Auto-process: ON")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    padding: 5px;
                    border-radius: 3px;
                    font-weight: bold;
                    color: #28a745;
                }
            """)
        else:
            self.status_indicator.setText("⏸️ Auto-process: OFF")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    padding: 5px;
                    border-radius: 3px;
                    font-weight: bold;
                    color: #6c757d;
                }
            """)

    def auto_process_changed(self):
        """Handle changes to auto-process setting."""
        self.update_status_indicator()
        if self.auto_process and self.data is not None:
            self.process_data()

    def validate_code(self):
        """Validate the current code and return True if valid."""
        try:
            functions = self.extract_functions(self.code)
            return bool(functions)  # Return True if we have valid functions
        except Exception:
            return False
            
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
            
            # Auto-process if enabled and code is valid
            if self.auto_process and self.validate_code():
                self.process_data()
        else:
            self.info_label.setText("No data loaded")
            self.process_button.setEnabled(False)
            self.mapping_table.setRowCount(0)
            
    def extract_functions(self, code):
        """Extract and validate functions from the code."""
        try:
            # Create namespace with essential items including work_dir
            namespace = {
                'np': np, 
                'pd': pd,
                'work_dir': self.work_dir  # Always provide the current working directory
            }
            
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
                
            # Update status to show processing
            self.update_status("Processing data...", False)
            self.process_button.setEnabled(False)
                
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
            
            # Update status with success message
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
        finally:
            self.process_button.setEnabled(True)

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(CustomProcessingWidget).run()