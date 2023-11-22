import logging
import prepare_dwi as dwipre
import prepare_prf as prfpre
import os
import utils as do
import numpy as np 
import os.path as path
import json
from os import rename
from glob import glob
from os import path, symlink, unlink
from scipy.io import loadmat

import sys

logger=logging.getLogger("GENERAL")
#%% copy configs or create new analysis
def prepare_analysis_folder(parser_namespace, lc_config):
    '''
    this function is the very very first step of everything, it is IMPORTANT, 
    it will provide a check if your desired analysis has been running before
    and it will help you keep track of your input parameters so that you know what you are doing in your analysis    

    the option force will not be useful at the analysis_folder level, if you insist to do so, you need to delete the old analysis folder by hand
    
    after determine the analysis folder, this function will copy your input configs to the analysis folder, and it will read only from there
    '''
    # read parameters from lc_config
    
    basedir = lc_config['general']['basedir']
    container = lc_config['general']['container']
    force = lc_config["general"]["force"]
    analysis_name= lc_config['general']['analysis_name']
    
    run_lc = parser_namespace.run_lc
    
    force= force or run_lc    
    
    version = lc_config["container_specific"][container]["version"]    
    # get the analysis folder information
    
    container_folder = os.path.join(basedir, 'BIDS','derivatives',f'{container}_{version}')
    if not os.path.isdir(container_folder):
        os.makedirs(container_folder)
    
    

    Dir_analysis = os.path.join(
        container_folder, ##########before , there is _{version}
        f"analysis-{analysis_name}",
                )
    
        
    # define the potential exist config files
    path_to_analysis_lc_config = os.path.join(Dir_analysis, "lc_config.yaml")
    path_to_analysis_sub_ses_list = os.path.join(Dir_analysis, "subSesList.txt")
    
    if container  not in ['rtp-pipeline', 'fmriprep']:    
        path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, "config.json")]
    if container == 'rtp-pipeline':
        path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, "config.json"), os.path.join(Dir_analysis, "tractparams.csv")]
    if container == 'fmriprep':
        path_to_analysis_container_specific_config=[]
    #TODO: heudiconv, nordic, presurfer
    


    if not run_lc:
        logger.warning(f'\nthis is PREPARE MODE, starts to  create analysis folder and copy the configs')
        if not os.path.isdir(Dir_analysis):
            os.makedirs(Dir_analysis)
        
        # backup the config info
        
        do.copy_file(parser_namespace.lc_config, path_to_analysis_lc_config, force) 
        do.copy_file(parser_namespace.sub_ses_list,path_to_analysis_sub_ses_list,force)
        for orig_config_json, copy_config_json in zip(parser_namespace.container_specific_config,path_to_analysis_container_specific_config):
            do.copy_file(orig_config_json, copy_config_json, force)    
        logger.debug(f'\n the analysis folder is {Dir_analysis}, all the cofigs has been copied') 
    
    if run_lc:
        logger.warning(f'\n RUN MODE, this is the analysis folder that we are going to run:\n {Dir_analysis}')
        # also copy the newest
        do.copy_file(parser_namespace.lc_config, path_to_analysis_lc_config, force) 
        do.copy_file(parser_namespace.sub_ses_list,path_to_analysis_sub_ses_list,force)
        for orig_config_json, copy_config_json in zip(parser_namespace.container_specific_config,path_to_analysis_container_specific_config):
            do.copy_file(orig_config_json, copy_config_json, force)    
        logger.debug(f'\n the analysis folder is {Dir_analysis}, all the configs has been copied')         
        
        copies = [path_to_analysis_lc_config, path_to_analysis_sub_ses_list] + path_to_analysis_container_specific_config
    
        all_copies_present= all(os.path.isfile(copy_path) for copy_path in copies)

        if all_copies_present:
            pass
        else:
            logger.error(f'\n did NOT detect back up configs in the analysis folder, Please check then continue the run mode')
    return Dir_analysis 

# %% prepare_input_files
def prepare_dwi_input(parser_namespace, Dir_analysis, lc_config, df_subSes, layout):
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
    logger.info("\n"+
                "#####################################################\n"
                +"---starting to prepare the input files for analysis\n")
    
    container = lc_config["general"]["container"]
    version = lc_config["container_specific"][container]["version"]
 
    
    # first thing, if the container specific config is not correct, then not doing anything
    if len(parser_namespace.container_specific_config)==0:
                logger.error("\n"
                              +f"Input file error: the container specific config is not provided")
                raise FileNotFoundError("Didn't input container_specific_config, please indicate it in your command line flag -cc")
    
    
    for row in df_subSes.itertuples(index=True, name="Pandas"):
        sub = row.sub
        ses = row.ses
        RUN = row.RUN
        dwi = row.dwi
        
        logger.info(f'dwi is {dwi}')
        logger.info("\n"
                    +"The current run is: \n"
                    +f"{sub}_{ses}_{container}_{version}\n")
        

        if RUN == "True" and dwi == "True":
                        
            tmpdir = os.path.join(
                Dir_analysis,
                "sub-" + sub,
                "ses-" + ses,
                "output", "tmp"
            )
            logdir = os.path.join(
                Dir_analysis,
                "sub-" + sub,
                "ses-" + ses,
                "output", "log"
            )

            if not os.path.isdir(tmpdir):
                os.makedirs(tmpdir)
            logger.info(f"\n the tmp dir is created at {tmpdir}, and it is {os.path.isdir(tmpdir)} that this file exists")
            if not os.path.isdir(logdir):
                os.makedirs(logdir)
            
            if "rtppreproc" in container:
                dwipre.rtppreproc(parser_namespace, Dir_analysis, lc_config, sub, ses, layout)
            
            elif "rtp-pipeline" in container:
                
                if not len(parser_namespace.container_specific_config) == 2:
                    logger.error("\n"
                              +f"Input file error: the RTP-PIPELINE config is not provided completely")
                    raise FileNotFoundError('The RTP-PIPELINE needs the config.json and tratparams.csv as container specific configs')
                
                dwipre.rtppipeline(parser_namespace, Dir_analysis,lc_config, sub, ses, layout)
            
            elif "anatrois" in container:
                logger.info('we do the anatrois')
                dwipre.anatrois(parser_namespace, Dir_analysis,lc_config,sub, ses, layout)
            
            else:
                logger.error("\n"+
                             f"***An error occurred"
                             +f"{container} is not created, check for typos or contact admin for singularity images\n"
                )

        else:
            continue
    logger.info("\n"+
                "#####################################################\n")
    return  
def prepare_prf_input ():
    """
    the input you may want to use: 
    #input parser_namespace, your input path of the 3 files
    Dir_analysis, analysis folder which already created
    lc_config, the dictionary
    sub_ses_list, the dataframe of subseslist, 
    layout,  : BIDS layout object, already have content
    
    1. call funtion in prepare_prf to store the visadisplog into BIDS folder, maybe createsymlink, 
        if you want to use createsymlink, I got a function called force_link in prepare_dwi.py, you can call that so that it works with 
        the option force in the lc_config['general']['force'] to control if we want to overwrite file or not
    2. prepare the json file with certain sub and session and store as the config json 
        a. options: if there is no input json, write based on config.yaml
            you can do len(parser_namespace.container_specific_json)>0 to do the check
        b. options: if there is input json, stay with the json only write the sub and ses info
    
    3. we add parameters to the yaml['container_specific']['prfprepare'] to control how we are going to do the link_visadisplog 
        with the name we want


# by the end of this afternoon, we are able to run prfprepare with the 3 features we have.
    """
    
    return

def fmrprep_intended_for(sub_ses_list, bidslayout):
    '''
    not implement yet, thinking how to smartly do the job
    '''
    layout= bidslayout
    #number_of_topups= fmriprep_configs['number_of_topups'] # a str
    #index_of_new_topups= fmriprep_configs['number_of_topups'] # a str about the functional run 
    exp_TRs= [2] #fmriprep_configs['exp_TRs'] # a list
    
    for row in sub_ses_list.itertuples(index=True, name="Pandas"):
        sub = row.sub
        ses = row.ses
        RUN = row.RUN
        func = row.func
        
        if RUN == "True" and func == "True":

            logger.info(f'\n working on {sub}...')

        
            # load func and fmaps
            funcNiftis = layout.get(subject=sub, session=ses, extension='.nii.gz', datatype='func')
            fmapNiftis = layout.get(subject=sub, session=ses, extension='.nii.gz', datatype='fmap')

            funcNiftisMeta = [funcNiftis[i].get_metadata() for i in range(len(funcNiftis))]
            fmapNiftisMeta = [fmapNiftis[i].get_metadata() for i in range(len(fmapNiftis))]

            for res in exp_TRs:
                funcN = np.array(funcNiftis)[[i['RepetitionTime'] == res for i in funcNiftisMeta]]
                # fmapN = np.array(fmapNiftis)[[i['RepetitionTime'] == res for i in fmapNiftisMeta]]
                fmapN = fmapNiftis
                
                # make list with all relative paths of func
                funcNiftisRelPaths = [path.join(*funcN[i].relpath.split("/")[1:]) for i in range(len(funcN))]
                funcNiftisRelPaths = [fp for fp in funcNiftisRelPaths if ((fp.endswith('_bold.nii.gz') or 
                                                                        fp.endswith('_sbref.nii.gz')) and 
                                                                        all([k not in fp for k in ['mag', 'phase']]))]

                # add list to IntendedFor field in fmap json
                for fmapNifti in fmapN:
                    if not path.exists(fmapNifti.filename.replace('.nii.gz', '_orig.json')):
                        f = fmapNifti.path.replace('.nii.gz', '.json')

                        with open(f, 'r') as file:
                            j = json.load(file)

                        j['IntendedFor'] = [f.replace("\\", "/") for f in funcNiftisRelPaths]

                        rename(f, f.replace('.json', '_orig.json'))

                        with open(f, 'w') as file:
                            json.dump(j, file, indent=2)
        
    '''add a function to check, if all the intended for is here, if so, return fmriprep'''
    
    return 

