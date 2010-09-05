import doctest
import sys
import os
sys.path.insert(0, '..')
sys.path.insert(0, os.path.join('..','plugins'))
doctest.testfile("arturo.doctest")
