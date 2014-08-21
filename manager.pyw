#!/usr/bin/python3

from mainwindow import *
import sys
import time, datetime

root = MainWindow()
if '-m' in sys.argv:
    root.iconify()
if '-log' in sys.argv:
    sys.stdout = sys.stderr = open('manager.log', 'a')
    print(str(datetime.datetime(*time.localtime()[:6])).center(30).center(80, '='))
root.mainloop()
