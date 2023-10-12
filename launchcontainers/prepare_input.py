import logging
import createsymlinks as csl
import os
import filecmp
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
    host=lc_config['general']['host']
    config_name=lc_config['container_specific'][container]['config_name']
    analysis_name= lc_config['general']['analysis_name']
    
    found_analysis_dir=False
    run_lc = parser_namespace.run_lc
    
    force= force and (not run_lc)    
    
    version = lc_config["container_specific"][container]["version"]    
    # get the analysis folder information
    
    container_folder = os.path.join(basedir, 'BIDS','derivatives',f'{container}')
    
    if not os.path.isdir(container_folder):
        os.makedirs(container_folder)
        logger.warning(f"your container folder for {container} is empty, please rerun prepare mode it you didn't do so ") 
    entities= os.listdir(container_folder)
    if len(entities)==0:
        logger.critical('No valid analysis folder, prepare mode is incomplete, please rerun prepare mode and create correct analysis folder')
        print(container_folder)
        raise FileNotFoundError('the analysis folder is not found, aborting')
    analysis_folders= [dir_ana for dir_ana in entities if os.path.isdir(os.path.join(container_folder,dir_ana))]
    
    if not analysis_folders:
        analysis_num=1
    else:
        newest_analysis_dir= max(analysis_folders, key= lambda d: os.path.getmtime(os.path.join(container_folder,d)))
        logger.debug(f'this is the newest analysis dir we get {newest_analysis_dir}')
        
        detected_analysis_name= newest_analysis_dir.split('/')[-1].split('-')[1]
        detected_analysis_num= newest_analysis_dir.split('/')[-1].split('-')[2]

        if not detected_analysis_name == analysis_name:
            analysis_num=1
            logger.debug(f'detected analysis name is {detected_analysis_name}, it is different from what you provide in lc_config yaml {analysis_name}')
        else:
            analysis_num=int(detected_analysis_num)
    
    # Get the input config files from parser  
    original_files = [parser_namespace.lc_config, parser_namespace.sub_ses_list] + parser_namespace.container_specific_config
    

    # check: if the analysis folder is already exit
        # if it is exit, check if the config information of lc_yaml, the looping information of subseslist and container specific config are the same
        # if either one of them have any tiny mistake, make a new analysis folder, and copy them to there, and give a note: this is new thing, different from 
        # what you are indicating, we add a new thing for your
    while not found_analysis_dir and analysis_num <100 and not run_lc:
        
        
        Dir_analysis = os.path.join(
        basedir,
        "BIDS",
        "derivatives",
        f"{container}", ##########before , there is _{version}
        f"analysis-{analysis_name}-{analysis_num:02d}",
                )
        

        logger.debug(f'\n this is the analysis {analysis_num} we are searching')
        
        # define the potential exist config files
        path_to_analysis_lc_config = os.path.join(Dir_analysis, "lc_config.yaml")
        path_to_analysis_sub_ses_list = os.path.join(Dir_analysis, "subSesList.txt")
        
        if container  not in ['rtp-pipeline', 'fmriprep']:    
            path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, f"{config_name}.json")]
        if container == 'rtp-pipeline':
            path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, f"{config_name}",+".json"), os.path.join(Dir_analysis, "tractparams.csv")]
        if container == 'fmriprep':
            path_to_analysis_container_specific_config=[]
        
        Dict_configs_under_analysisfolder={
        'new_lc_config_path':path_to_analysis_lc_config,
        'new_sub_ses_list_path':path_to_analysis_sub_ses_list,
        'new_container_specific_config_path': path_to_analysis_container_specific_config
            }
        
        copies = [path_to_analysis_lc_config, path_to_analysis_sub_ses_list] + path_to_analysis_container_specific_config
    
        all_copies_present= all(os.path.isfile(copy_path) for copy_path in copies)
        
        logger.debug (f'\n the config.json is {path_to_analysis_container_specific_config}')
        
        # compare if all the files are the same
        general_input= lc_config["general"]
        container_input=lc_config["container_specific"][container]
        logger.debug(host)
        host_input= lc_config["host_options"][host]
        

        
        if os.path.isdir(Dir_analysis):
            logger.debug(f'\n we found the exist analysis dir, going to check if all the config information'
                         +'is the same as the input')

            if all_copies_present:
                lc_config_copy=do.read_yaml(path_to_analysis_lc_config)
                
                container_ana= lc_config_copy['general']['container']
                host_ana=lc_config_copy['general']['host']
                
                general_copy= lc_config_copy["general"]
                container_copy=lc_config_copy["container_specific"][container_ana]
                host_copy= lc_config_copy["host_options"][host_ana]
                
                logger.debug(f"\n this is the config from input {host_input}"
                             + f"\n this is the config from the copy of {Dir_analysis} \n {host_copy}"
                              + f"they are {host_input == host_copy} the same" )
                
                compare_config_yaml= (general_input==general_copy) and (container_input==container_copy) and (host_input==host_copy)

                are_they_same = all(filecmp.cmp(orig, copy, shallow=False)
                                for orig, copy in zip(original_files[1:], copies[1:])) and compare_config_yaml
            
                if are_they_same:
                    logger.debug(f'\n for the {Dir_analysis}, it has all the config copies and the config information are the same:\t {all_copies_present}')
                    logger.warning("\n"
                                + f"the config files in {Dir_analysis} are the same as your input, remain old filesif you are confident to run, type --run_lc flag")
                    #return Dir_analysis,Dict_configs_under_analysisfolder
                    break
                # if the config info are all the same, we didn't create new analysis folder
                else:
                    logger.info("\n"
                                + f"the config files in {Dir_analysis} are NOT the same as your input create new analysis folder"
                                + f"going to create analysis {analysis_num:02}")
                    analysis_num+=1   
            else:
                analysis_num+=1 

        if not os.path.isdir(Dir_analysis):
            
            os.makedirs(Dir_analysis)
            do.copy_file(parser_namespace.lc_config, path_to_analysis_lc_config, force) 
            do.copy_file(parser_namespace.sub_ses_list,path_to_analysis_sub_ses_list,force)
            for orig_config_json, copy_config_json in zip(parser_namespace.container_specific_config,path_to_analysis_container_specific_config):
                do.copy_file(orig_config_json, copy_config_json, force)    
            logger.debug(f'\n the analysis folder is not here, break the while loop') 
            break
    if run_lc:
        Dir_analysis= os.path.join(container_folder, newest_analysis_dir)
        
        path_to_analysis_lc_config = os.path.join(Dir_analysis, "lc_config.yaml")
        path_to_analysis_sub_ses_list = os.path.join(Dir_analysis, "subSesList.txt")
        
        if container  not in ['rtp-pipeline', 'fmriprep']:    
            path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, f"{config_name}.json")]
        if container == 'rtp-pipeline':
            path_to_analysis_container_specific_config = [os.path.join(Dir_analysis, f"{config_name}.json"), os.path.join(Dir_analysis, "tractparams.csv")]
        if container == 'fmriprep':
            path_to_analysis_container_specific_config=[]
        
        Dict_configs_under_analysisfolder={
        'new_lc_config_path':path_to_analysis_lc_config,
        'new_sub_ses_list_path':path_to_analysis_sub_ses_list,
        'new_container_specific_config_path': path_to_analysis_container_specific_config
            }
        
    logger.debug(f'\n this is the analysis folder that goes to other places:\n {Dir_analysis}')
    
    #sys.exit(1)
    #return  Dir_analysis
    return Dir_analysis, Dict_configs_under_analysisfolder

# %% prepare_input_files
def prepare_dwi_input(parser_namespace, Dir_analysis, lc_config, df_subSes, run_lc):
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
        
        logger.info("\n"
                    +"The current run is: \n"
                    +f"{sub}_{ses}_RUN-{RUN}_{container}_{version}\n")
        
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
            backup_configs = os.path.join(
                Dir_analysis,
                "sub-" + sub,
                "ses-" + ses,
                "output", "configs"
            )
            if not os.path.isdir(tmpdir):
                os.makedirs(tmpdir)
            if not os.path.isdir(logdir):
                os.makedirs(logdir)
            
            if "rtppreproc" in container:
                csl.rtppreproc(parser_namespace, Dir_analysis, lc_config, sub, ses)
            elif "rtp-pipeline" in container:
                
                if not len(parser_namespace.container_specific_config) == 2:
                    logger.error("\n"
                              +f"Input file error: the RTP-PIPELINE config is not provided completely")
                    raise FileNotFoundError('The RTP-PIPELINE needs the config.json and tratparams.csv as container specific configs')
                
                csl.rtppipeline(parser_namespace, Dir_analysis,lc_config, sub, ses, run_lc)
            elif "anatrois" in container:
                csl.anatrois(parser_namespace, Dir_analysis,lc_config,sub, ses)
            
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

def link_vistadisplog(basedir, sub_ses_list, bids_layout):
    
    
    
    baseP=os.path.join(basedir,'BIDS','sourcedata','vistadisplog')

    
    for row in sub_ses_list.itertuples(index=True, name='Pandas'):
        sub  = row.sub
        ses  = row.ses
        RUN  = row.RUN
        func = row.func
        if RUN ==True and func == True:
            taskdict=  {}
            tasks= bids_layout.get_tasks(subject=sub, session=ses)
            for index, item in enumerate(tasks):
                taskdict[item]=1
                logger.debug(taskdict)
            matFiles = np.sort(glob(path.join(baseP, f'sub-{sub}', f'ses-{ses}', '20*.mat')))
            logger.debug(f"\n {path.join(baseP, f'sub-{sub}', f'ses-{ses}', '20*.mat')}")
            logger.debug(f'\n {matFiles}')
            for matFile in matFiles:

                stimName = loadmat(matFile, simplify_cells=True)['params']['loadMatrix']
                print(stimName)
                for key in taskdict:
                    logger.debug(key)
                    if key[2:] in stimName:
                        if 'tr-2' in stimName:
                            linkName = path.join(path.dirname(matFile), f'{sub}_{ses}_task-{key}_run-0{taskdict[key]}_params.mat')
                            
                            taskdict[key] += 1

                    if path.islink(linkName):
                        unlink(linkName)

                    symlink(path.basename(matFile), linkName)

    return True
def prepare_prf_input(basedir, container, config_path, sub_ses_list, bids_layout ,run_lc):
    # first prepare the sourcedata, the vistadisp-log
    # then write the subject information to the config.json file

    if not run_lc:
        # if the container is prfprepare, do the preparation for vistadisplog
        # copy the container specific information to the prfprepare.json.
        # copy the information in subseslist to the prfprepare.json
        # question, in this way, do we still need the config.json???
        sub_list=[]
        ses_list=[]
        for row in sub_ses_list.itertuples(index=True, name='Pandas'):
            sub  = row.sub
            ses  = row.ses
            RUN  = row.RUN
            func = row.func
            logger.debug(f'\n run is {RUN},type run is {type(RUN)} func is {func} --{sub}-{ses}' )
            if RUN == "True" and func == "True":    # i mean yes, but there will always to better options
                sub_list.append(sub)
                ses_list.append(ses)
        logger.debug(f'\nthis is sublist{sub_list}, and ses list {ses_list}\n')        
        with open(config_path, 'r') as config_json:
            j= json.load(config_json)
        
        if container == 'prfprepare':   
            # do i need to add a check here? I don't think so
            if link_vistadisplog(basedir,sub_ses_list, bids_layout):
                logger.info('\n'
                + f'the {container} prestep link vistadisplog has been done!')
                j['subjects'] =' '.join(sub_list)
                j['sessions'] =' '.join(ses_list)

        if container =='prfresult':    
            j['subjects'] =' '.join(sub_list)
            j['sessions'] =' '.join(ses_list)
        if container == 'prfanalyze-vista':
            j['subjectName'] =' '.join(sub_list)
            j['sessionName'] =' '.join(ses_list)
       
        
        with open(config_path, 'w') as config_json:
            json.dump(j, config_json, indent=2)
    return
