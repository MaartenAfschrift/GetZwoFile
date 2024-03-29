import argparse
import re
import sys
from enum import Enum
import os

import requests
from lxml import etree, html
from lxml.builder import E
from lxml.html import fromstring

class StepPosition(Enum):
    FIRST = 0
    MIDDLE = 1
    LAST = 2

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

def main():
    args = parse_args()
    #content = read_file("https://whatsonzwift.com/workouts/build-me-up/week-4-pedaling-drills")
    content = read_file(args.target)
    #if not content:
    content = fetch_url(args.target)
    #content = fetch_url('https://whatsonzwift.com/workouts/pebble-pounder')
    tree = html.fromstring(content)
    title = text(tree, '//h4[contains(@class, "flaticon-bike")]').strip()
    desc = text(tree, '//div[contains(@class, "workoutdescription")]/p')
    steps = tree.xpath('//div[contains(@class, "workoutlist")]/div')

    WorkoutNames = tree.xpath('//h4[@class="glyph-icon flaticon-bike"]')
    descNames = tree.xpath('//div[contains(@class, "workoutdescription")]/div')

    linesource = []
    for il, node in enumerate(steps):
        linesource.append(node.sourceline)

    #get difference between lines
    ctfiles = 1
    inewfile = []
    for i in range(0, len(linesource)-1):
        diffLines = linesource[i+1] - linesource[i]
        if diffLines > 10:
            ctfiles = ctfiles+1
            inewfile.append(i+1)
    inewfile.append(len(linesource))

    for ifile in range(0, ctfiles-1):
        root = etree.Element("workout_file")
        root.append(element_text("author", "M. Afschrift"))
        titlesel = WorkoutNames[ifile+1]
        title = titlesel.text_content()
        root.append(element_text("name", title))

        # find the descrtion after the title

        root.append(element_text("description", "ToDo"))
        root.append(element_text("sportType", "bike"))
        root.append(etree.Element("tags"))
        workout = etree.Element("workout")

        # selected indices in this file
        stepindices = range(inewfile[ifile],inewfile[ifile+1])

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
        #write the file
        etree.indent(root, space="    ")
        strfilename = title + '.zwo'
        # check for slash in strfilename and remove if needed
        strfilename = strfilename.replace('/', '_')
        datapath = "C:\\Temp\\ZwoFiles\\"
        if not(os.path.isdir(datapath)):
            os.makedirs(datapath)
        with open(datapath + strfilename, 'w') as f:
            f.write(
                etree.tostring(root, pretty_print=True, encoding="unicode"),
            )
        #print('file one done')

if __name__ == "__main__":
    main()
