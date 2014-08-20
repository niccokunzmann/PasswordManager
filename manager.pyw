#!/usr/bin/python3

from mainwindow import *
import sys

root = MainWindow()
if '-m' in sys.argv:
    root.iconify()
root.mainloop()
