# satlas2_gui.py
# NOTE: This script requires PyQt5 and satlas2. If you encounter ModuleNotFoundError, install them via:
# pip install PyQt5 satlas2

import sys
import os
import re
import numpy as np
import matplotlib.pyplot as plt

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QLabel, QPushButton, QVBoxLayout,
                                 QWidget, QLineEdit, QTextEdit, QHBoxLayout, QMessageBox, QComboBox)
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
except ModuleNotFoundError:
    print("[ERROR] PyQt5 is not installed. GUI will not run. Please install it with 'pip install PyQt5'.")
    QApplication = QMainWindow = QFileDialog = QLabel = QPushButton = QVBoxLayout = QWidget = QLineEdit = QTextEdit = QHBoxLayout = QMessageBox = QComboBox = object
    FigureCanvas = object

try:
    import satlas2
except ModuleNotFoundError:
    print("[ERROR] satlas2 module is not installed. Please install it with 'pip install satlas2'.")
    satlas2 = None

if 'object' in str(type(QApplication)) or satlas2 is None:
    print("[INFO] Exiting gracefully due to missing dependencies.")
else:
    class Satlas2GUI(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("SATLAS2 GUI")
            self.setGeometry(100, 100, 1000, 700)
            self.initUI()

        def initUI(self):
            layout = QVBoxLayout()

            # File selection
            self.file_label = QLabel("No file selected")
            self.load_button = QPushButton("Load Data File")
            self.load_button.clicked.connect(self.load_file)

            # Input fields
            self.freq_offset_input = QLineEdit("508332000.0")
            self.freq_offset_input.setFixedWidth(120)

            self.mu_input = QLineEdit("1.660538921e-27")
            self.mu_input.setFixedWidth(120)

            self.mion_input = QLineEdit("20.99765446")
            self.mion_input.setFixedWidth(100)

            self.applv_input = QLineEdit("19.9195")
            self.applv_input.setFixedWidth(80)

            self.mode_select = QComboBox()
            self.mode_select.addItems(["co", "anti"])

            self.param_input = QTextEdit()
            self.param_input.setPlainText(
                "spin = 1.5\n"
                "J = [0.5, 0.5]\n"
                "A = [953.7, 102.6]\n"
                "B = [0, 0]\n"
                "C = [0.5, 1.5]\n"
                "FWHMG = 220\n"
                "FWHML = 20\n"
                "centroid = 250\n"
                "bkg = 7\n"
                "scale = 60"
            )
            self.param_input.setFixedHeight(80)

            # Fit button
            self.fit_button = QPushButton("Fit Spectrum")
            self.fit_button.clicked.connect(self.fit_spectrum)

            # Result view
            self.result_text = QTextEdit()
            self.result_text.setReadOnly(True)
            self.result_text.setMinimumHeight(150)

            # Plot canvas
            self.canvas = FigureCanvas(plt.Figure(figsize=(5, 3)))
            self.ax = self.canvas.figure.add_subplot(111)
            self.canvas.setMinimumHeight(300)

            # Layouts
            file_layout = QHBoxLayout()
            file_layout.addWidget(self.load_button)
            file_layout.addWidget(self.file_label)

            freq_layout = QHBoxLayout()
            freq_layout.addWidget(QLabel("Laser Frequency Offset:"))
            freq_layout.addWidget(self.freq_offset_input)

            mu_layout = QHBoxLayout()
            mu_layout.addWidget(QLabel("m_u:"))
            mu_layout.addWidget(self.mu_input)
            mu_layout.addWidget(QLabel("m_ion:"))
            mu_layout.addWidget(self.mion_input)
            mu_layout.addWidget(QLabel("appl_V:"))
            mu_layout.addWidget(self.applv_input)

            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("Beam Mode:"))
            mode_layout.addWidget(self.mode_select)

            # Add widgets to main layout
            layout.addLayout(file_layout)
            layout.addLayout(freq_layout)
            layout.addLayout(mu_layout)
            layout.addLayout(mode_layout)

            layout.addWidget(QLabel("Fit Parameters:"))
            layout.addWidget(self.param_input, stretch=0)
            layout.addWidget(self.fit_button)

            layout.addWidget(QLabel("Fit Result:"))
            layout.addWidget(self.result_text, stretch=1)

            layout.addWidget(QLabel("Fit Plot:"))
            layout.addWidget(self.canvas, stretch=2)

            # Finalize
            central_widget = QWidget()
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)

            self.file_path = None



        def load_file(self):
            path, _ = QFileDialog.getOpenFileName(self, "Open Data File", "", "All Files (*.*)")
            if path:
                self.file_path = path
                self.file_label.setText(os.path.basename(path))
            else:
                self.file_label.setText("No file selected")

        def fit_spectrum(self):
            if not self.file_path:
                QMessageBox.warning(self, "Warning", "No file loaded.")
                return

            try:
                namespace = {}
                exec(self.param_input.toPlainText(), {}, namespace)
                spin = namespace['spin']
                J, A, B, C = namespace['J'], namespace['A'], namespace['B'], namespace['C']
                FWHMG, FWHML = namespace['FWHMG'], namespace['FWHML']
                centroid, bkg, scale = namespace['centroid'], namespace['bkg'], namespace['scale']
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Parameter parsing error: {e}")
                return

            try:
                freq_offset = float(self.freq_offset_input.text())
                m_u = float(self.mu_input.text())
                m_ion = float(self.mion_input.text())
                appl_V = float(self.applv_input.text())
                mode = self.mode_select.currentText()
            except ValueError as e:
                QMessageBox.critical(self, "Input Error", f"Invalid numerical input: {e}")
                return

            try:
                with open(self.file_path, encoding='utf-8') as f:
                    lines = f.readlines()[3:]  # skip 1st, 2nd, and header line
                data = [line.strip().split() for line in lines if len(line.strip().split()) >= 7]
                AOut = np.array([float(row[0]) for row in data])
                y = np.array([float(row[3]) for row in data])
                Freq = np.array([float(row[5]) for row in data])
            except Exception as e:
                QMessageBox.critical(self, "Error", f"File loading failed: {e}")
                return

            c = 299792458.0
            e = 1.60217653e-19

            def get_beta(AOut):
                return np.sqrt(1 - (m_u**2 * m_ion**2 * c**4) / ((e * 1000. * (appl_V - AOut) + m_u * m_ion * c**2)**2))

            def doppler_shift(Freq, beta, mode='co'):
                if mode == 'co':
                    return Freq * np.sqrt((1 - beta) / (1 + beta))
                elif mode == 'anti':
                    return Freq * np.sqrt((1 + beta) / (1 - beta))

            def modifiedSqrt(input):
                output = np.sqrt(input)
                output[input <= 0] = 1
                return output

            beta = get_beta(AOut)
            Freq_adj = doppler_shift(Freq, beta, mode=mode)
            Freq_adj = Freq_adj * 1e6 - freq_offset

            # original_name = os.path.basename(self.file_path)
            # safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', original_name)  # remove colons and spaces
            original_name = os.path.basename(self.file_path)
            safe_name = "fitdata"


            f = satlas2.Fitter()
            source = satlas2.Source(Freq_adj, y, yerr=modifiedSqrt, name=safe_name)
            hfs = satlas2.HFS(spin, J, A=A, B=B, C=C, scale=scale, df=centroid,
                              name='HFS_' + safe_name, racah=True, fwhmg=FWHMG, fwhml=FWHML)
            bkgm = satlas2.Polynomial([bkg], name='bkg_' + safe_name)
            source.addModel(hfs)
            source.addModel(bkgm)
            f.addSource(source)

            try:
                f.fit()
                report = f.reportFit()
                self.result_text.setPlainText(report)

                self.ax.clear()
                self.ax.plot(source.x, source.y, drawstyle='steps-mid', label='Data')
                smooth_x = np.linspace(source.x.min(), source.x.max(), 1000)
                self.ax.plot(smooth_x, source.evaluate(smooth_x), label='Fit')
                self.ax.set_title(f"Fit: {original_name} ({mode})")
                self.ax.set_xlabel("Frequency [MHz]")
                self.ax.set_ylabel("Counts")
                self.ax.legend()
                self.canvas.draw()

            except Exception as e:
                QMessageBox.critical(self, "Fit Error", f"Fitting failed: {e}")

    if __name__ == '__main__':
        app = QApplication(sys.argv)
        gui = Satlas2GUI()
        gui.show()
        sys.exit(app.exec_())
