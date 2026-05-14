"""Visual block-diagram of the end-to-end link."""

from gui.core.mpl_canvas import MplCanvas
from models.link_diagram import draw_link_diagram


def create_link_diagram_tab(mw):
    """Canvas with a clear-sky checkbox for weather toggling."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox

    tab = QWidget()
    lay = QVBoxLayout(tab)

    controls = QWidget()
    cl = QHBoxLayout(controls)
    cl.addWidget(QLabel("Weather Condition:"))
    mw.clear_sky_check = QCheckBox("Clear Sky (\u039a\u03b1\u03b8\u03b1\u03c1\u03cc\u03c2 \u039f\u03c5\u03c1\u03b1\u03bd\u03cc\u03c2)")
    mw.clear_sky_check.setChecked(True)
    mw.clear_sky_check.setToolTip("When unchecked, uses Rain Rate from parameters")
    mw.clear_sky_check.stateChanged.connect(mw.calculate_complete_link)
    cl.addWidget(mw.clear_sky_check)
    cl.addStretch()
    lay.addWidget(controls)

    mw.link_diagram_canvas = MplCanvas(mw, width=10, height=7, dpi=100)
    lay.addWidget(mw.link_diagram_canvas)
    return tab


def update_link_diagram_complete(mw, results, params):
    """Redraw the block diagram for the current link results."""
    draw_link_diagram(
        mw.link_diagram_canvas.figure,
        results, params,
        clear_sky=mw.clear_sky_check.isChecked(),
        sat_type_name=mw.sat_type_combo.currentText(),
        gs_rx_diameter_m=mw.gs_diameter_spin.value(),
        transponder=mw.transponder,
    )
    mw.link_diagram_canvas.draw()
