import argparse
import os
import shutil as sh
import glob
import subprocess as sp
import numpy as np
import pandas as pd
import json

with open('config_launchcontainer.json','r') as v:
    vars=json.load(v)

basedir=vars["config"]["basedir"]
tool =vars["config"]["tool"]
analysis=vars["config"]["analysis"]
host =vars["config"]["host"] # possible values: dipc, bcbl
codedir=vars["config"]["codedir"]
container=vars["config"]["container"]+'/'+tool+'.sif'
qsub=vars["config"]["qsub"]
tmpdir=vars["config"]["tmpdir"]
logdir=vars["config"]["logdir"]

# If tmpdir and logdir do not exist, create them
if not os.path.isdir(tmpdir): os.mkdir(tmpdir)
if not os.path.isdir(logdir): os.mkdir(logdir)

if host == "BCBL":
    mem=vars["BCBL"]["mem"]
    que=vars["BCBL"]["que"]
    core=vars["BCBL"]["core"]
    sin_ver=vars["BCBL"]["sin_ver"]
elif host == "DIPC":
    mem=vars["DIPC"]["mem"]
    que=vars["DIPC"]["que"]
    core=vars["DIPC"]["core"]
    sin_ver=vars["DIPC"]["sin_ver"]

# Get the unique list of subjects and sessions
subseslist=os.path.join(basedir,"Nifti","subSesList.txt")
os.chdir(codedir)

# all arguments we need to submit the task
"""
-t tool       # which container we are running
-s sub        # subject
-e ses        # session
-a analysis   # analysis
-b basedir    # the base dir of project
-o codedir    # the git dir of project
-m mem        # how much memory to request for qsub
-q que        # queue to submit the tasks
-c core       # core numbers to request for qsub
-p tmpdir     # tmp dir for singularity containers
-g logdir     # log dir for error and output runs
-i sin_ver    # singularity version
-n container  # the location of the container to run
-u noqsub     # use qsub or not
-h host       # host where to run
"""

# READ THE FILE
dt = pd.read_csv(subseslist, sep=",", header=0)

for row in dt.itertuples(index=True, name='Pandas'):
    sub  = row.sub
    ses  = row.ses
    RUN  = row.RUN
    dwi  = row.dwi
    func = row.func
    if RUN and dwi:
        cmdstr = (f"{codedir}/qsub_generic.sh " +
                  f"-t {tool} " +
		  f"-s {sub} " +
		  f"-e {ses} " +
                  f"-a {analysis} "              +
                  f"-b {basedir} " +
		  f"-o {codedir} " +
                  f"-m {mem} " +
		  f"-q {que} " +
		  f"-c {core} " +
                  f"-p {tmpdir} " +
		  f"-g {logdir} " +
		  f"-i {sin_ver} " +
                  f"-n {container} " +
		  f"-u {qsub} " +
          f"-h {host} ")
        print(cmdstr)
        sp.call(cmdstr, shell=True)