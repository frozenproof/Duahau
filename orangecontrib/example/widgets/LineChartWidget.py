import sys
import numpy as np
from Orange.data import Table, Domain, ContinuousVariable, StringVariable
from Orange.widgets import gui
from Orange.widgets.widget import OWWidget, Input, Output
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QApplication
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

    class Inputs:
        data = Input("Data", Table)

    def __init__(self):
        super().__init__()
        self.data = None
        self._setup_ui()
        self.resize(800, 600)

    def _setup_ui(self):
        self.mainArea.layout().addWidget(QLabel("Line Chart"))
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.mainArea.layout().addWidget(self.canvas)

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
            ax.set_title("Line Chart")
            ax.set_xlabel(x_axis_name)
            ax.set_ylabel("Value")

            # Plot each row as a line
            for i, (name, row) in enumerate(zip(line_names, y_values)):
                ax.plot(x_values, row, label=name, marker='o')

            # Add legend
            ax.legend()

            # Add grid
            ax.grid(True, linestyle='--', alpha=0.7)

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