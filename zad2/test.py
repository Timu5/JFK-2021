import glob
import sys, os
from main import Driver



_stderr = sys.stderr
_stdout = sys.stdout

null = open(os.devnull,'wb')
#sys.stdout = sys.stderr = null

files = glob.glob("./examples/*")


for f in files:
    print("-----------------------------------------------",file=_stdout)
    print(f,file=_stdout)
    sys.argv = ['main.py', '--run', f]
    d = Driver()
    d.main()
    print("-----------------------------------------------",file=_stdout)
