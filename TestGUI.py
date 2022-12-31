import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Widgets App")

        layout = QVBoxLayout()
        #widgets = [
        #    QLabel,
        #    QLineEdit,
        #    QPushButton,
        #]
        #for w in widgets:
        #    layout.addWidget(w())
        self.label_widget = QLabel("My first label")
        self.label_widget.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.label_widget)

        self.line_edit_widget = QLineEdit("copy paste URL here")
        self.line_edit_widget.textEdited.connect(self.text_edited)
        layout.addWidget(self.line_edit_widget)

        self.download_widget = QPushButton("Dowload")
        self.download_widget.clicked.connect(self.download)
        layout.addWidget(self.download_widget)

        self.setdir_widget = QPushButton("select folder")
        self.setdir_widget.clicked.connect(self.getDirectory)
        layout.addWidget(self.setdir_widget)



        #self.QT_FileDialog = self.QFileDialog()
        #file = str(self.QT_FileDialog.getExistingDirectory(self, "Select Directory"))
        #layout.addWidget(self.QT_FileDialog)

        widget = QWidget()
        widget.setLayout(layout)



        #folderpath = widget.QFileDialog.getExistingDirectory(self, 'Select Folder')

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.setWindowTitle("Download .zwo files")
        self.setCentralWidget(widget)


    def text_edited(self, s):
        print("Text edited...")
        print(s)

    def getDirectory(self):
        response = QFileDialog.getExistingDirectory(
            self,
            caption='Select a folder'
        )
        print(response)
        return response

    def download(self):
        print('donwloading zwo files')


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec()