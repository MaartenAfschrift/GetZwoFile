# GetZwoFile

download .zwo files from whatsonzwift.com

Workflow:

1. Install the requirments.txt

2. Run GetZwo from command line with URL as input

```python
python GetZwo.py 'https://whatsonzwift.com/workouts/build-me-up'
```

Create installer
pyinstaller.exe --onefile --windowed --name myapps --icon=Logo_TMD1.ico App.py
pyinstaller.exe --onefile --name GetZwoFiles --icon=Logo_TMD1.ico App.py
