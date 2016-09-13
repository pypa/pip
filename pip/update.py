#!/usr/bin/python
import os

update_list = []
p = os.popen('sudo -H pip freeze --local',"r")
while 1:
    line = p.readline()
    if not line: break
    update_list.append(line.rstrip('\n').split('=')[0])
counter = 0
while counter < len(update_list):
        os.system('sudo -H pip install -U "' + update_list[counter] + '"')
        counter += 1
