import os, sys, inspect

def add_current_dir_to_python_path():
    'Enables absolute imports starting from the current folder'
    path = os.path.split(inspect.getfile( inspect.currentframe() ))[0]
    path = os.path.realpath( os.path.abspath(path) )
    if path not in sys.path:
        sys.path.append(path)

# this is needed by almost all
# SBOLQuery's dependencies
add_current_dir_to_python_path()

from sbol_query import *
