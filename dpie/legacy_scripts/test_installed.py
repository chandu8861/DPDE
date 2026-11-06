#!/usr/bin/env python
import sys
import os

# Check site-packages
sp = r'C:\Users\AI&ML\AppData\Local\Programs\Python\Python311\lib\site-packages'
print('dpie files in site-packages:', [f for f in os.listdir(sp) if 'dpie' in f.lower()])

# Try importing
try:
    import dpie
    print('dpie imported successfully')
    print('Version:', dpie.__version__)
    print('File:', dpie.__file__)
except ModuleNotFoundError as e:
    print('Cannot import dpie:', e)
    
    # Check the editable pth file
    pth_file = os.path.join(sp, '__editable__.dpie-0.1.0.pth')
    if os.path.exists(pth_file):
        print('Editable pth file exists, content:')
        with open(pth_file) as f:
            print(f.read())