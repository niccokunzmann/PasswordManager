#!/usr/bin/python3

from mainwindow import *
import sys

root = MainWindow()
if '-m' in sys.argv:
    root.iconify()
if '-log' in sys.argv:
    sys.stdout = sys.stderr = open('manager.log', 'a')
root.mainloop()
