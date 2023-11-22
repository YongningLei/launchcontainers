import logging
import prepare_dwi as dwipre
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
