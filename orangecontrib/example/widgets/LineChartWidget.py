import sys
import os
import numpy as np
import matplotlib.pyplot as plt  # Add this line
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets.settings import Setting
from PyQt5.QtWidgets import (QVBoxLayout, QLabel, QApplication, 
                            QSizePolicy, QWidget, QFileDialog)
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class LineChartWidget(OWWidget):
    """Widget that draws a line chart based on the input data."""

    name = "Line Chart Widget"
    description = "Draws a line chart based on the input data."
    icon = "icons/mywidget.svg"
    priority = 100
    keywords = ["widget", "data", "line chart"]
    want_main_area = True
    resizing_enabled = True

    # Settings
    chart_title = Setting("Line Chart")
    last_save_dir = Setting("")  # Remember last save directory
    exact_x_values = Setting(False)  # Add this line
    show_all_xticks = Setting(False)  # Add this line

    class Inputs:
        data = Input("Data", Table)

    def __init__(self):
        super().__init__()
        self.data = None
        self._setup_gui()
        self.resize(800, 600)

    def _setup_gui(self):
        """Initialize and setup the user interface."""
        # Setup control area (left side)
        box = gui.vBox(self.controlArea, "Chart Settings")
        
        # Add title edit
        self.title_edit = gui.lineEdit(
            box, self, "chart_title", 
            "Chart Title: ", 
            callback=self.title_changed,
            callbackOnType=True
        )

        # Add save button
        self.save_button = gui.button(
            box, self, "Save Chart",
            callback=self.save_chart,
            tooltip="Save chart as PNG"
        )

        # Add X-axis controls - ADD THIS SECTION
        axis_box = gui.vBox(box, "X-Axis Settings")
        
        # Checkbox for exact x values
        gui.checkBox(
            axis_box, self,
            "exact_x_values",
            "Use exact X values",
            callback=self.draw_line_chart,
            tooltip="When checked, uses exact X values without rounding"
        )

        # Checkbox for showing all x ticks
        gui.checkBox(
            axis_box, self,
            "show_all_xticks",
            "Show all X-axis labels",
            callback=self.draw_line_chart,
            tooltip="When checked, shows all X-axis labels"
        )

        # Setup main area (right side)
        main_layout = QVBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.mainArea.layout().addWidget(main_widget)

        # Add title with proper styling
        self.gui_title = QLabel("Line Chart")
        self.gui_title.setAlignment(Qt.AlignCenter)
        self.gui_title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                padding: 5px;
            }
        """)
        self.gui_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        main_layout.addWidget(self.gui_title)

        # Create figure
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.canvas)

        # Set margins
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

    def save_chart(self):
        """Save the chart as a PNG file."""
        if not self.figure:
            return

        # Create a default filename from the chart title
        default_filename = f"{self.chart_title.replace(' ', '_')}.png"
        
        # Get the save location from user
        initial_dir = self.last_save_dir if self.last_save_dir else os.path.expanduser("~")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Chart",
            os.path.join(initial_dir, default_filename),
            "PNG Files (*.png);;All Files (*)"
        )

        if filename:
            # Remember the directory
            self.last_save_dir = os.path.dirname(filename)
            
            # Add .png extension if not present
            if not filename.lower().endswith('.png'):
                filename += '.png'

            try:
                # Save the figure
                self.figure.savefig(
                    filename,
                    format='png',
                    dpi=300,
                    bbox_inches='tight',
                    pad_inches=0.1
                )
                print(f"Chart saved successfully to: {filename}")
            except Exception as e:
                print(f"Error saving chart: {e}")

    def title_changed(self):
        """Handle chart title changes."""
        self.draw_line_chart()

    @Inputs.data
    def set_data(self, data):
        self.data = data
        self.draw_line_chart()

    def draw_line_chart(self):
        """Draw the line chart based on the input data."""
        if self.data is None:
            return

        # Clear the previous plot
        self.figure.clear()

        try:
            # Convert data to numpy array for easier handling
            data_array = self.data.X
            
            # Get the first row (which contains x-axis values)
            x_values = data_array[0][:]
            
            # Get line names from the meta column (excluding the first row)
            line_names = [str(value) for value in self.data.metas[1:, 0]]
            
            # Get y values (excluding the first row)
            y_values = data_array[1:]
            
            # Get x-axis label (first cell in meta)
            x_axis_name = str(self.data.metas[0, 0])

            # Create a new subplot
            ax = self.figure.add_subplot(111)
            ax.set_title(self.chart_title)
            ax.set_xlabel(x_axis_name)
            ax.set_ylabel("Value")

            # Plot each row as a line
            for i, (name, row) in enumerate(zip(line_names, y_values)):
                ax.plot(x_values, row, label=name, marker='o')

            # Add legend
            ax.legend()

            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)

            # Configure x-axis based on settings
            if self.exact_x_values:
                # Use exact values for x-axis
                ax.xaxis.set_major_locator(plt.FixedLocator(x_values))
                
            if self.show_all_xticks:
                # Show all x-axis labels
                ax.set_xticks(x_values)
                ax.set_xticklabels([str(x) for x in x_values])
            else:
                # Show fewer labels to avoid overcrowding
                if len(x_values) > 10:
                    step = len(x_values) // 10
                    ax.set_xticks(x_values[::step])
                    ax.set_xticklabels([str(x) for x in x_values[::step]])

            # Format x-axis ticks
            ax.tick_params(axis='x', rotation=45)
            
            # Adjust layout to prevent label cutoff
            self.figure.tight_layout()

            # Redraw the canvas
            self.canvas.draw()

        except Exception as e:
            print(f"Error drawing line chart: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    from Orange.widgets.utils.widgetpreview import WidgetPreview
    WidgetPreview(LineChartWidget).run()