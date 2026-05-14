"""Waterfall Diagram tab — creation and update logic."""

from gui.core.mpl_canvas import MplCanvas
from models.link_diagram import draw_waterfall_figure


def create_waterfall_tab(mw):
    """Create Waterfall Diagram tab."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout

    tab = QWidget()
    layout = QVBoxLayout(tab)
    mw.waterfall_canvas = MplCanvas(mw, width=14, height=9, dpi=100)
    layout.addWidget(mw.waterfall_canvas, 1)
    return tab


def update_waterfall_diagram(mw, results, params):
    """Create detailed waterfall diagram based on link mode."""
    draw_waterfall_figure(mw.waterfall_canvas.figure, results, params)
    mw.waterfall_canvas.draw()
