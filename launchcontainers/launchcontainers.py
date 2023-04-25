import nibabel as nib
import argparse
import importlib
from logging import DEBUG
import os
import glob
import subprocess as sp
import shutil
import numpy as np
import pandas as pd
import zipfile
import json
import sys
import yaml
from yaml.loader import SafeLoader
import pip
import pandas as pd
# Dask imports
from dask import compute
from dask import delayed as delayed_dask
from dask import config
from dask.distributed import Client
from dask_jobqueue import PBSCluster, SGECluster, SLURMCluster
from dask.distributed import progress
# My packages
import dask_schedule_queue as dsq
import createsymlinks as csl

"""
TODO: 
    4./ Add the check in launchcontainers.py, that only in some cases we wiill 
        need to use createSymLinks, and for the anatrois, rtppreproc and 
        rtp-pipeline, we will need to do it
    5./ Edit createSymLinks again and make one function per every container
        createSymLinks_anatrois.py
        createSymLinks_rtppreproc.py
        createSymLinks_rtp-pipeline.py
"""
# %% parser
def _get_parser():
    """
    Input:
    Parse command line inputs

    Returns:
    a dict stores information about the cmd input

    """
    parser = argparse.ArgumentParser(
        description= """This is a python program helps you analysis MRI data using different containers,\nbefore you make use of this program, please edit the required config files to match your analysis demand. \n
                      --------STEP 1
                      To begin the analysis, you need to first prepare and check the input files by typing this command in your bash prompt:\n
                      python path/to/the/launchcontianer.py -lcc path/to/launchcontainer_config.yaml -ssl path/to/subject_session_info.txt -cc path/to/contianer_specific_config.json \n
                      #--cc note, for the case of rtp-pipeline, you need to input two paths, one for config.json and one for tractparm.csv#
                      ------- STEP2
                      After you have done step 1, all the config files are copied to nifti/sub/ses/analysis/ directory \n
                      When you are confident everthing is there, press up arrow to recall the command in STEP 1, and just add --run_lc after it. \n
                      We add lots of check in the script to avoid program breakdowns. if you found new bugs while running, do not hesitate to contact us"""
    )
    parser.add_argument(
        "-lcc",
        "--lc_config",
        type=str,
        # default="/Users/tiger/TESTDATA/PROJ01/nifti/config_launchcontainer_copy.yaml",
        default="/export/home/tlei/tlei/TESTDATA/PROJ01/nifti/config_lc.yaml",
        help="path to the config file",
    )
    parser.add_argument(
        "-ssl",
        "--sub_ses_list",
        type=str,
        # default="/Users/tiger/TESTDATA/PROJ01/nifti/subSesList.txt",
        default="/export/home/tlei/tlei/TESTDATA/PROJ01/nifti/subSesList.txt",
        help="path to the subSesList",
    )
    parser.add_argument(
        "-cc",
        "--container_specific_config",
        nargs='+',
        # default="/Users/tiger/Documents/GitHub/launchcontainers/example_configs/container_especific_example_configs/anatrois/4.2.7_7.1.1/example_config.json",
        help="path to the container specific config file(s). First file needs to be the config.json file of the container. Some containers might need more config files (e.g., rtp-pipeline needs tractparams.csv). Add them here separated with a space.",
    )
   
    parser.add_argument('--run_lc', action='store_true',
                        help= "if you type --run_lc, the entire program will be launched, jobs will be send to \
                        cluster and launch the corresponding container you suggest in config_lc.yaml. \
                        We suggest that the first time you run launchcontainer.py, leave this arguement empty. \
                        then the launchcontainer.py will preapre \
                        all the input files for you and print the command you want to send to container, after you \
                        check all the configurations are correct and ready, you type --run_lc to make it run"
                        )
    parser.add_argument('--not_run_lc', dest='run_lc', action='store_false')
    parser.set_defaults(run_lc=False)



    parse_result = vars(parser.parse_args())
    print("1111111111111111111111111111111111111111111111111111111111111111111111\n")
    
    print ("This is the result from _get_parser()\n")
    print(parse_result,"\n")
    
    print("1111111111111111111111111111111111111111111111111111111111111111111111\n")
    return parse_result


# %% function to read launchcontainer config.yaml
def _read_config(path_to_config_file):
    """
    Input:
    the path to the config file

    Returns
    a dictionary that contains all the config info

    """
    print("2222222222222222222222222222222222222222222222222222222222222222222222\n")
    print(f"------Reading the config file {path_to_config_file} \n ")

    with open(path_to_config_file, "r") as v:
        config = yaml.load(v, Loader=SafeLoader)

    container = config["config"]["container"]

    print(f"----Successfully read config_lc.yaml")
    print(f'\nBasedir is: {config["config"]["basedir"]}')
    print(f'\nContainer is: {container}_{config["container_options"][container]["version"]}')
    print(f'\nAnalysis is: analysis-{config["config"]["analysis"]}\n')
    print("2222222222222222222222222222222222222222222222222222222222222222222222\n")

    return config


# %% function to read subSesList. txt
def _read_df(path_to_df_file):
    """
    Input:
    path to the subject and session list txt file

    Returns
    a dataframe

    """
    outputdf = pd.read_csv(path_to_df_file, sep=",", header=0)
    num_rows = len(outputdf)

    # Print the result
    print("3333333333333333333333333333333333333333333333333333333333333333333333\n")
    print(f'The dataframe{path_to_df_file} is successfully read. \n')
    print(f'The DataFrame has {num_rows} rows. \n')
    print("3333333333333333333333333333333333333333333333333333333333333333333333\n")
    

    return outputdf
#%% check if tractparam ROI was created in the anatrois fs.zip file
def check_tractparam(lc_config, sub, ses, tractparam_df):
    """

        Parameters
        ----------
        lc_config : dict
             the config info about lc
        sub : str
        ses: str
        tractparam_df : dataframe

            inherited parameters: path to the fs.zip file
                defined by lc_config, sub, ses
        Returns
        -------
        None.
    """
    # Define the list of required ROIs
    required_rois=set()
    for col in ['roi1', 'roi2', 'roi3', 'roi4',"roiexc1","roiexc2"]:
        for val in tractparam_df[col][~tractparam_df[col].isna()].unique():
            if val != "NO":
                required_rois.add(val)

    # Define the zip file
    basedir = lc_config["config"]["basedir"]
    container = lc_config["config"]["container"]
    precontainerfs = lc_config["container_options"][container]["precontainerfs"]
    preanalysisfs = lc_config["container_options"][container]["preanalysisfs"]
    fs_zip = os.path.join(
        basedir,
        "nifti",
        "derivatives",
        precontainerfs,
        "analysis-" + preanalysisfs,
        "sub-" + sub,
        "ses-" + ses,
        "output", "fs.zip"
    )
    # Extract .gz files from zip file and check if they are all present
    with zipfile.ZipFile(fs_zip, 'r') as zip:
        zip_gz_files = set(zip.namelist())
    required_gz_files = set(f"fs/ROIs/{file}.nii.gz" for file in required_rois)
    print(f"The following are the ROIs in fs.zip file: \n {zip_gz_files}")
    print(f"---there are {len(zip_gz_files)} .nii.gz files in fs.zip from anarois output\n")
    print(f"---There are {len(required_gz_files)} ROIs that are required to run RTP-PIPELINE\n")
    if required_gz_files.issubset(zip_gz_files):
        print("-----checked! All required .gz files are present in the fs.zip \n")
    else:
        missing_files = required_gz_files - zip_gz_files
        print(f"*****Error: there are {len(missing_files)} missed in fs.zip \n The following .gz files are missing in the zip file:\n {missing_files}")
        sys.exit(1)

    ROIs_are_there= required_gz_files.issubset(zip_gz_files)
    return ROIs_are_there
# %% prepare_input_files
def prepare_input_files(lc_config, lc_config_path, df_subSes, sub_ses_list_path, container_specific_config, run_lc):
    """

    Parameters
    ----------
    lc_config : TYPE
        DESCRIPTION.
    df_subSes : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    print("4444444444444444444444444444444444444444444444444444444444444444444444\n")
    print("-----starting to preprare the input files for analysis\n")
    


    for row in df_subSes.itertuples(index=True, name="Pandas"):
        sub = row.sub
        ses = row.ses
        RUN = row.RUN
        dwi = row.dwi
        func = row.func
        container = lc_config["config"]["container"]
        version = lc_config["container_options"][container]["version"]
        print("The current run is:")
        print(f"{sub}_{ses}_RUN-{RUN}_{container}_{version}\n")
        
        if RUN == "True":
            if "rtppreproc" in container:
                new_lc_config_path,new_sub_ses_list_path=csl.rtppreproc(lc_config, lc_config_path, sub, ses, sub_ses_list_path, container_specific_config,run_lc)
            elif "rtp-pipeline" in container:
                if not len(container_specific_config) == 2:
                    sys.exit('This container needs the config.json and tratparams.csv as container specific configs')
                new_lc_config_path,new_sub_ses_list_path=csl.rtppipeline(lc_config,lc_config_path, sub, ses,sub_ses_list_path,container_specific_config,run_lc)
                #srcFile_tractparam = container_specific_config[1]
                # tractparam_df=_read_df(srcFile_tractparam)
                # check_tractparam(lc_config, sub, ses, tractparam_df)
            elif "anatrois" in container:
                new_lc_config_path,new_sub_ses_list_path =csl.anatrois(lc_config, lc_config_path,sub, ses,sub_ses_list_path, container_specific_config,run_lc)
            # future container
            else:
                print(f"******************* ERROR ********************\n")
                print(
                    f"{container} is not created, check for typos or contact admin for singularity images\n"
                )

        else:
            continue
    print("4444444444444444444444444444444444444444444444444444444444444444444444\n")
    
    return new_lc_config_path, new_sub_ses_list_path

# %% launchcontainers

def launchcontainers(sub_ses_list, lc_config, run_it):
    """
    This function launches containers generically in different Docker/Singularity HPCs
    This function is going to assume that all files are where they need to be.

    Parameters
    ----------
    sub_ses_list: Pandas data frame
        Data frame with subject information and if run or not run
    lc_config : dict
        Dictionary with all the values in the configuracion yaml file
    run_it: boolean
        used to control if we run the launchcontainer, or not
    lc_config_path: Str
        the path to lc_config file, it is the input from parser
  
   
   """
    print("5555555555555555555555555555---------the real launchconatiner-----------55555555555555555555555555555555\n")
    tmpdir = lc_config["config"]["tmpdir"]
    logdir = lc_config["config"]["logdir"]
    
    # If tmpdir and logdir do not exist, create them
    if not os.path.isdir(tmpdir):
        os.mkdir(tmpdir)
    if not os.path.isdir(logdir):
        os.mkdir(logdir)
   
    host = lc_config["config"]["host"]
    jobqueue_config= lc_config["host_options"][host]
    

    basedir = lc_config["config"]["basedir"]
    container = lc_config["config"]["container"] 
    version = lc_config["container_options"][container]["version"]
    analysis = lc_config["config"]["analysis"] 
    containerdir = lc_config["config"]["containerdir"] 
    sif_path = os.path.join(containerdir, f"{container}_{version}.sif")
    
    # Count how many jobs we need to launch from  sub_ses_list
    n_jobs = np.sum(sub_ses_list.RUN == "True")

    client, cluster = dsq.dask_scheduler(jobqueue_config,n_jobs)
    print("\n~~~~this is the cluster and client\n")
    print(f"{client} \n cluster: {cluster} \n")
    ourlist=[]

    for row in sub_ses_list.itertuples(index=True, name='Pandas'):
        sub  = row.sub
        ses  = row.ses
        RUN  = row.RUN
        dwi  = row.dwi
        func = row.func
        if RUN=="True" and dwi=="True":

            # command for launch singularity
            path_to_sub_derivatives=os.path.join(basedir,"nifti","derivatives",
                                                 f"{container}_{version}",
                                                 f"analysis-{analysis}",
                                                 f"sub-{sub}",
                                                 f"ses-{ses}")
            print(f"~~~~~~~~~ this is the path to sub-ses folder: {path_to_sub_derivatives}\n ")
            path_to_config=os.path.join(basedir,"nifti","derivatives",
                                                 f"{container}_{version}",
                                                 f"analysis-{analysis}",
                                                 "analysis-"+analysis+"_config.json")
            # copy the config yaml for every subject and session
            # shutil.copyfile(os.path.join(basedir,"nifti", "config_lc.yaml"), os.path.join(path_to_sub_derivatives, "config_lc.yaml"))
            # print(f"--------succefully copied the config_lc.yaml to {path_to_sub_derivatives} folder! you can check this in the future ! \n")

            logfilename=f"{logdir}/t-{container}_a-{analysis}_sub-{sub}_ses-{ses}" 
            cmd=f"singularity run -e --no-home "\
                f"--bind /bcbl:/bcbl "\
                f"--bind /tmp:/tmp "\
                f"--bind /export:/export "\
                f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "\
                f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "\
                f"--bind {path_to_config}:/flywheel/v0/config.json "\
                f"{sif_path} 2>> {logfilename}.e 1>> {logfilename}.o "
            if run_it:
                print (f"~~~~~~~~~~~do we run it? {run_it}\n")
                                
                print(f"-------run_lc is True, we will launch this command: \n" \
                      f"$$$$$$-------{cmd}\n")
                print(f"-----------------\n-----------------\n client is {client}")
                
                ourlist.append(delayed_dask(sp.run)(cmd,shell=True,pure=False,dask_key_name='sub-'+sub+'_ses-'+ses))
               
                #shutil.copyfile(os.path.join(logfilename+".o"),
                #                os.path.join(path_to_sub_derivatives,"stdout.o"))
                #print("---copied the .o log file to {sub}-{ses} folder")
                #shutil.copyfile(os.path.join(logfilename+".e"),
                #                os.path.join(path_to_sub_derivatives,"stderr.e"))
                #print("---copied the .e error file to {sub}-{ses}")

            else:
                print(f"--------run_lc is false, if True, we would launch this command: \n" \
                      f"--------{cmd}\n")
                print(f"-------The cluster job_scipt is  {cluster.job_script()} \n")
                print("-----please check if the job_script is properlly defined and then starting run_lc \n")
    
    if run_it:
        print(ourlist)
        print('##########')
        results = client.compute(ourlist)
        progress(results)
        print(results)
        print('###########')
        results = client.gather(results)
        print(results)
        print('###########')
        print("5555555555555555555555555555555555555555555555555555555555555555555555\n")
        client.close()
        cluster.close()
    return

def backup_config_for_subj(sub, ses, basedir, ):
    """
    One of the TODO:
        make a function, when this file was run, create a copy of the original yaml file
        then rename it , add the date and time in the end
        stored the new yaml file under the output folder
        At the end, thiknk if we want it per subject, right now it is in the analysis folder
    """
    return None

# %% main()


def main():
    """launch_container entry point"""
    inputs = _get_parser()
    
    lc_config_path = inputs["lc_config"]
    lc_config = _read_config(lc_config_path)
    
    sub_ses_list = pd.read_csv(inputs["sub_ses_list"],sep=",",dtype=str)
    sub_ses_list_path = inputs["sub_ses_list"]
    
    container_specific_config = inputs["container_specific_config"]
    
    run_lc = inputs["run_lc"]
    
    basedir = lc_config['config']["basedir"]
    container = lc_config["config"]["container"]
    version = lc_config["container_options"][container]
 

    new_lc_config_path,new_sub_ses_list_path=prepare_input_files(lc_config, lc_config_path, sub_ses_list, sub_ses_list_path,container_specific_config,run_lc)
    
    new_lc_config=_read_config(new_lc_config_path)
    new_sub_ses_list= pd.read_csv(new_sub_ses_list_path,sep=",",dtype=str)
    
    if run_lc:
        launchcontainers(new_sub_ses_list, new_lc_config, True)
    else:
        launchcontainers(new_sub_ses_list, new_lc_config, False)

# #%%
if __name__ == "__main__":
    main()
