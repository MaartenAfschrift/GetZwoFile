import argparse
import re
import sys
from enum import Enum
import os

import requests
from lxml import etree, html
from lxml.builder import E
from lxml.html import fromstring


import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5 import QtGui
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
    QFormLayout,
    QScrollArea,
)



class StepPosition(Enum):
    FIRST = 0
    MIDDLE = 1
    LAST = 2

def calc_duration(hrs,mins, secs):
    d = 0
    if secs:
        d += int(secs)
    if mins:
        d += int(mins) * 60
    if hrs:
        d += int(hrs) * 60 * 60
    return d

def ramp(match, pos):
    label = {
        StepPosition.FIRST: "Warmup",
        StepPosition.LAST: "Cooldown"
    }.get(pos, "Ramp")
    duration = calc_duration(match["hrs"], match["mins"], match["secs"])
    cadence = match.get("cadence")
    low_power = match["low"] / 100.0
    high_power = match["high"] / 100.0
    node = etree.Element(label)
    node.set("Duration", str(duration))
    node.set("PowerLow", str(low_power))
    node.set("PowerHigh", str(high_power))
    node.set("pace", str(0))
    if cadence:
        node.set("Cadence", str(cadence))
    return node

def steady(match, pos):
    duration = calc_duration(match["hrs"], match["mins"], match["secs"])
    cadence = match.get("cadence")
    power = match["power"] / 100.0
    node = E.SteadyState(Duration=str(duration), Power=str(power), pace=str(0))
    if cadence:
        node.set("Cadence", str(cadence))
    return node

def intervals(match, pos):
    on_duration = calc_duration(match["on_hrs"], match["on_mins"], match["on_secs"])
    off_duration = calc_duration(match["on_hrs"], match["off_mins"], match["off_secs"])
    reps = match["reps"]
    on_power = match["on_power"] / 100.0
    off_power = match["off_power"] / 100.0
    on_cadence = match.get("on_cadence")
    off_cadence = match.get("off_cadence")
    node = E.IntervalsT(
        Repeat=str(reps),
        OnDuration=str(on_duration),
        OffDuration=str(off_duration),
        OnPower=str(on_power),
        OffPower=str(off_power),
        pace=str(0),
    )
    if on_cadence and off_cadence:
        node.set("Cadence", str(on_cadence))
        node.set("CadenceResting", str(off_cadence))
    return node

def free_ride(match, pos):
    # TODO: can have cadence?
    duration = calc_duration(match["hrs"], match["mins"], match["secs"])
    return E.FreeRide(Duration=str(duration), FlatRoad=str(0))

RAMP_RE = re.compile(
    r'(?:(?P<hrs>\d+)hr )?(?:(?P<mins>\d+)min )?(?:(?P<secs>\d+)sec )?'
    r'(?:@ (?P<cadence>\d+)rpm, )?from (?P<low>\d+) to (?P<high>\d+)% FTP'
)

STEADY_RE = re.compile(
    r'(?:(?P<hrs>\d+)hr )?(?:(?P<mins>\d+)min )?(?:(?P<secs>\d+)sec )?'
    r'@ (?:(?P<cadence>\d+)rpm, )?(?P<power>\d+)% FTP'
)

INTERVALS_RE = re.compile(
    r'(?P<reps>\d+)x (?:(?P<on_hrs>\d+)hr )?(?:(?P<on_mins>\d+)min )?(?:(?P<on_secs>\d+)sec )?'
    r'@ (?:(?P<on_cadence>\d+)rpm, )?(?P<on_power>\d+)% FTP,'
    r'(?:(?P<off_hrs>\d+)hr )?(?:(?P<off_mins>\d+)min )?(?:(?P<off_secs>\d+)sec )?'
    r'@ (?:(?P<off_cadence>\d+)rpm, )?(?P<off_power>\d+)% FTP'
)

FREE_RIDE_RE = re.compile(
    r'(?:(?P<hrs>\d+)hr )?(?:(?P<mins>\d+)min )?(?:(?P<secs>\d+)sec )?free ride'
)

#OVER_UNDER_RE = re.compile(
#    r'(?:(?P<hrs>\d+)hr )?(?:(?P<mins>\d+)min )?(?:(?P<secs>\d+)sec )?free ride'
#)

BLOCKS = [
    (RAMP_RE, ramp),
    (STEADY_RE, steady),
    (INTERVALS_RE, intervals),
    (FREE_RIDE_RE, free_ride),
]
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="file or URL")
    return ap.parse_args()

def parse_node(step, pos):
    text = step.text_content()
    for regex, func in BLOCKS:
        match = regex.match(text)
        if match:
            match_int = {
                k: int(v) if v else None for k, v in match.groupdict().items()
            }
            return func(match_int, pos)
    raise RuntimeError(f"Couldn't parse {text}")

def fetch_url(url):
    return requests.get(url).content

def read_file(path):
    try:
        return open(path).read()
    except FileNotFoundError as e:
        return None

def text(tree, selector):
    return tree.xpath(f"{selector}/text()")[0]

def element_text(element, text):
    node = etree.Element(element)
    node.text = text
    return node


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QtGui.QIcon('Logo_TMD1.png'))
        self.dirsel = "C:\\Temp\\ZwoFiles\\"
        self.hmtlsel = 'https://whatsonzwift.com/workouts/pebble-pounder'
        self.acceptDrops()

        self.setWindowTitle("Widgets App")

        layout = QVBoxLayout()
        self.label_widget = QLabel("Download training programs from whatsonzwift")
        self.label_widget.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.label_widget)

        topLayout = QFormLayout()
        self.line_edit_widget = QLineEdit("https://whatsonzwift.com/workouts/pebble-pounder")
        self.line_edit_widget.textEdited.connect(self.text_edited)
        topLayout.addRow("URL : ", self.line_edit_widget)
        layout.addLayout(topLayout)

        self.download_widget = QPushButton("Download")
        self.download_widget.clicked.connect(self.download)
        layout.addWidget(self.download_widget)

        self.setdir_widget = QPushButton("select folder")
        self.setdir_widget.clicked.connect(self.getDirectory)
        layout.addWidget(self.setdir_widget)

        self.labelDownload = QLabel("App info: ")
        self.labelDownload.setWordWrap(True)
        self.labelDownload.setAlignment(Qt.AlignHCenter)
        layout.addWidget(self.labelDownload)

        self.labelx1 = QLabel("Tip: you can run the training programs for free on this excellent App by Dimitar Marinov")
        self.labelx1.setWordWrap(True)
        urlLink1 = "<a href=\"https://flux-web.vercel.app/\">'Click this link to go to the trainer App'</a>"
        self.labelx2 = QLabel(urlLink1)
        self.labelx2.setWordWrap(True)
        urlLink2 = "<a href=\"https://github.com/dvmarinoff/Flux/\">'Click this link to go to the source code'</a>"
        self.labelx3 = QLabel(urlLink2)
        self.labelx3.setWordWrap(True)
        layout.addWidget(self.labelx1)
        layout.addWidget(self.labelx2)
        self.labelx2.setOpenExternalLinks(True)
        layout.addWidget(self.labelx3)
        self.labelx3.setOpenExternalLinks(True)

        # # add scroll area
        # self.vbox = QVBoxLayout()
        # self.scroll_layout = QScrollArea()
        # #self.scroll_widget = QWidget()
        # for i in range(1, 10):
        #     object = QLabel("TextLabel")
        #     self.vbox.addWidget(object)
        # # Scroll Area Properties
        # self.scroll_layout.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # self.scroll_layout.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.scroll_layout.setWidgetResizable(True)
        #
        # #self.scroll_layout.setWidget(self.widget)
        # layout.addLayout(self.vbox)

        #self.setCentralWidget(self.scroll)

        #self.setGeometry(600, 100, 1000, 900)
        #self.setWindowTitle('Scroll Area Demonstration')

        # creating label
        self.labelpict = QLabel(self)
        layout.addWidget(self.labelpict)

        # loading image
        self.pixmap = QPixmap('Logo_TMD2.png')

        # adding image to label
        self.labelpict.setPixmap(self.pixmap)
        self.labelpict.setAlignment(Qt.AlignCenter)

        # Optional, resize label to image size
        self.labelpict.resize(self.pixmap.width(),
                          self.pixmap.height())

        widget = QWidget()
        widget.setLayout(layout)

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.setWindowTitle("Download .zwo files")
        self.setCentralWidget(widget)
        self.resize(600, 400)

        # show the GUI
        self.show()

    def text_edited(self, s):
        print("URL edited: ")
        self.hmtlsel = s
        print(s)
        self.labelDownload.setText("App info: URL updated")

    def getDirectory(self):
        self.dirsel = QFileDialog.getExistingDirectory(
            self,
            caption='Select a folder'
        )
        print('Directory selected')
        print(self.dirsel)
        self.labelDownload.setText("App info: output directory updated")
        return (self.dirsel)

    def getzwofilesC(self):

        self.labelDownload.setText("App info: download .zwo files started")
        content = fetch_url(self.hmtlsel)
        # content = fetch_url('https://whatsonzwift.com/workouts/pebble-pounder')
        tree = html.fromstring(content)
        title = text(tree, '//h4[contains(@class, "flaticon-bike")]').strip()
        desc = text(tree, '//div[contains(@class, "workoutdescription")]/p')
        steps = tree.xpath('//div[contains(@class, "workoutlist")]/div')

        WorkoutNames = tree.xpath('//h4[@class="glyph-icon flaticon-bike"]')
        descNames = tree.xpath('//div[contains(@class, "workoutdescription")]/div')

        linesource = []
        for il, node in enumerate(steps):
            linesource.append(node.sourceline)

        # get difference between lines
        ctfiles = 1
        inewfile = []
        for i in range(0, len(linesource) - 1):
            diffLines = linesource[i + 1] - linesource[i]
            if diffLines > 10:
                ctfiles = ctfiles + 1
                inewfile.append(i + 1)
        inewfile.append(len(linesource))
        self.labelDownload.setText("App info: " + str(ctfiles) + "found")

        for ifile in range(0, ctfiles - 1):
            root = etree.Element("workout_file")
            root.append(element_text("author", "M. Afschrift"))
            titlesel = WorkoutNames[ifile + 1]
            title = titlesel.text_content()
            root.append(element_text("name", title))

            # find the descrtion after the title
            root.append(element_text("description", "ToDo"))
            root.append(element_text("sportType", "bike"))
            root.append(etree.Element("tags"))
            workout = etree.Element("workout")

            # selected indices in this file
            stepindices = range(inewfile[ifile], inewfile[ifile + 1])

            for i in range(0, len(stepindices)):
                node = steps[stepindices[i]]
                if i == 0:
                    pos = StepPosition.FIRST
                elif i == len(steps) - 1:
                    pos = StepPosition.LAST
                else:
                    pos = StepPosition.MIDDLE
                workout.append(parse_node(node, pos))
            root.append(workout)
            # write the file
            etree.indent(root, space="    ")
            strfilename = 'training ' + str(ifile) + ' ' + title + '.zwo'
            # check for slash in strfilename and remove if needed
            strfilename = strfilename.replace('/', '_')
            datapath = self.dirsel
            if not (os.path.isdir(datapath)):
                os.makedirs(datapath)
                #print('open file ', datapath)
            with open(datapath + '/' + strfilename, 'w') as f:
                f.write(
                    etree.tostring(root, pretty_print=True, encoding="unicode"),
                )
            #print('open file ', datapath)
            print('file ', datapath + '/' + strfilename , ' done')
        self.labelDownload.setText("App info: " + str(ctfiles) + " zwo files downloaded")
    def download(self):

        # message that download started
        self.getzwofilesC()
        print('download finished')

if __name__ == "__main__":
    myapp = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    myapp.exec()

