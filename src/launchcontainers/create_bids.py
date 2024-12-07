"""
MIT License

Copyright (c) 2020-2024 Garikoitz Lerma-Usabiaga
Copyright (c) 2020-2022 Mengxing Liu
Copyright (c) 2022-2024 Leandro Lecca
Copyright (c) 2022-2024 Yongning Lei
Copyright (c) 2023 David Linhardt
Copyright (c) 2023 Iñigo Tellaetxe

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""

import os.path as op
import os
import logging
from pathlib import Path
import shutil

# modules in lc
from bids import BIDSLayout

# for package mode, the import needs to import launchcontainer module
from launchcontainers.prepare_inputs import utils as do

# for testing mode through , we can use relative import 
# from prepare_inputs import dask_scheduler_config as dsq
# from prepare_inputs import prepare as prepare
# from prepare_inputs import utils as do


logger = logging.getLogger("Create-bids")
# this will automatically create fake bids folder
def setup_logger_cb(verbose=True, log_dir=None, log_filename=None):
    '''
    stream_handler_level: str,  optional
        if no input, it will be default at INFO level, this will be the setting for the command line logging

    verbose: bool, optional
    debug: bool, optional
    log_dir: str, optional
        if no input, there will have nothing to be saved in log file but only the command line output

    log_filename: str, optional
        the name of your log_file.

    '''
    # set up the lowest level for the logger first, so that all the info will be get
    logger.setLevel(logging.DEBUG)
    

    # set up formatter and handler so that the logging info can go to stream or log files 
    # with specific format
    log_formatter = logging.Formatter(
        "%(asctime)s (%(name)s):[%(levelname)s] %(module)s - %(funcName)s() - line:%(lineno)d   $ %(message)s ",
        datefmt="%Y-%m-%d %H:%M:%S",
    )    

    stream_formatter = logging.Formatter(
        "(%(name)s):[%(levelname)s]  %(module)s:%(funcName)s:%(lineno)d %(message)s"
    )
    # Define handler and formatter
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    if verbose:
        stream_handler.setLevel(logging.INFO)
    else:
        stream_handler.setLevel(logging.WARNING)
    logger.addHandler(stream_handler)

    if log_dir:
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)
            

        file_handler_info = (
            logging.FileHandler(op.join(log_dir, f'{log_filename}_info.log'), mode='a') 
        ) 
        file_handler_error = (
            logging.FileHandler(op.join(log_dir, f'{log_filename}_error.log'), mode='a') 
        ) 
        file_handler_info.setFormatter(log_formatter)
        file_handler_error.setFormatter(log_formatter)
    
        file_handler_info.setLevel(logging.INFO)
        file_handler_error.setLevel(logging.ERROR)
        logger.addHandler(file_handler_info)
        logger.addHandler(file_handler_error)


    return logger
    
def main():
    parser_namespace,parse_dict = do.get_create_bids_parser()

    # Check if download_configs argument is provided
   
    print("You are creating a fake BIDS folder structure based on your input basedir, and subseslist")
    # Your main function logic here
    # e.g., launch_container(args.other_arg)
    # read yaml and setup the bids folder
    
    newcontainer_config_path = parser_namespace.creat_bids_config
    newcontainer_config = do.read_yaml(newcontainer_config_path)
    

    # Get general information from the config.yaml file
    basedir=newcontainer_config["general"]["basedir"]
    bidsdir_name=newcontainer_config["general"]["bidsdir_name"]
    container=newcontainer_config["general"]["container"]
    version=newcontainer_config["general"]["version"]
    analysis_name=newcontainer_config["general"]["analysis_name"]
    file_name=newcontainer_config["general"]["file_name"]
    bids_component_dir=newcontainer_config["general"]["bids_component_dir"]
    bids_folder_component=op.join(bids_component_dir,'bids_folder_component')
    bids_id_files=[op.join(bids_folder_component, file) for file in os.listdir(bids_folder_component)]
    log_dir=newcontainer_config["general"]["log_dir"]
    log_filename=newcontainer_config["general"]["log_filename"]
    
    # get stuff from subseslist for future jobs scheduling
    sub_ses_list_path = parser_namespace.sub_ses_list
    sub_ses_list,num_of_true_run = do.read_df(sub_ses_list_path)
    
    
    if log_dir=="analysis_dir":
        if version:
            log_dir=op.join(basedir,bidsdir_name,'derivatives',f'{container}_{version}',f"analysis-{analysis_name}")
        else:
            log_dir=op.join(basedir,bidsdir_name,'derivatives',f'{container}',f"analysis-{analysis_name}")

    setup_logger_cb(True, log_dir, log_filename)
    bids_dir=op.join(
            basedir,
            bidsdir_name)
    if not op.exists(bids_dir):
        os.makedirs(bids_dir)
    for bids_file in bids_id_files:
        shutil.copy(bids_file, bids_dir)
        logging.info(f"Copied {bids_file} to {bids_dir}")
    if container == "processed_nifti":
        analysis_dir= op.join(
                basedir,
                bidsdir_name,
                "derivatives",
                f'{container}',
                f"analysis-{analysis_name}")
        if not op.exists(analysis_dir):
            os.makedirs(analysis_dir)
        for bids_file in bids_id_files:
            shutil.copy(bids_file, analysis_dir)
            logging.info(f"Copied {bids_file} to {analysis_dir}")
    # figure out a way to copy the bids componement to the corresponding bids folder
    for row in sub_ses_list.itertuples(index=True, name="Pandas"):
        sub = row.sub
        ses = row.ses
        RUN = row.RUN
        
        bids_dir_subses= op.join(
            basedir,
            bidsdir_name,
            f"sub-{sub}" ,
            f"ses-{ses}" 
        )
        if not op.exists(bids_dir_subses):
            os.makedirs(bids_dir_subses)
            os.makedirs(op.join(bids_dir_subses,'anat'))
            fake_T1w=op.join(bids_dir_subses,'anat', f"sub-{sub}_ses-{ses}_T1w.nii.gz")
            if not Path(fake_T1w).is_file():
                Path(fake_T1w).touch()
            os.makedirs(op.join(bids_dir_subses,'func'))
            fake_bold=op.join(bids_dir_subses,'func', f"sub-{sub}_ses-{ses}_bold.nii.gz")
            fake_bold_json=op.join(bids_dir_subses,'func', f"sub-{sub}_ses-{ses}_bold.json")
            if not Path(fake_bold).is_file():
                Path(fake_bold).touch()
            if not Path(fake_bold_json).is_file():
                Path(fake_bold_json).touch()                
            os.makedirs(op.join(bids_dir_subses,'dwi'))
            fake_dwi=op.join(bids_dir_subses,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.nii.gz")
            fake_dwi_json=op.join(bids_dir_subses,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.json")
            fake_dwi_bvec=op.join(bids_dir_subses,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.bvec")
            fake_dwi_bval=op.join(bids_dir_subses,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.bval")
            if not Path(fake_dwi).is_file():
                Path(fake_dwi).touch()
            if not Path(fake_dwi_json).is_file():
                Path(fake_dwi_json).touch()  
            if not Path(fake_dwi_bvec).is_file():
                Path(fake_dwi_bvec).touch()
            if not Path(fake_dwi_bval).is_file():
                Path(fake_dwi_bval).touch()                              
        
        if version:
            session_dir = op.join(
                basedir,
                bidsdir_name,
                "derivatives",
                f'{container}_{version}',
                f"analysis-{analysis_name}",
                f"sub-{sub}" ,
                f"ses-{ses}" 
                )
        else:
            session_dir = op.join(
                basedir,
                bidsdir_name,
                "derivatives",
                f'{container}',
                f"analysis-{analysis_name}",
                f"sub-{sub}" ,
                f"ses-{ses}" 
                )
            
        if container != "Processed_nifti":
            input_dir=op.join(session_dir,'input')
            outpt_dir=op.join(session_dir,'output')

            
            if not op.exists(input_dir):
                os.makedirs(input_dir)
            else:
                logger.info(f"Input folder for sub-{sub}/ses-{ses} is there")
            if not op.exists(outpt_dir):
                os.makedirs(outpt_dir)
            else:
                logger.info(f"Output folder for sub-{sub}/ses-{ses} is there")
            if file_name:
                fake_file=op.join(outpt_dir,file_name)
                if not Path(fake_file).is_file():
                    Path(fake_file).touch()
                else:
                    logger.info(f"The file for sub-{sub}/ses-{ses}/output is there")           
        else:
            if not op.exists(session_dir):
                os.makedirs(session_dir)
                os.makedirs(op.join(session_dir,'anat'))
                fake_T1w=op.join(session_dir,'anat', f"sub-{sub}_ses-{ses}_T1w.nii.gz")
                if not Path(fake_T1w).is_file():
                    Path(fake_T1w).touch()
                os.makedirs(op.join(session_dir,'func'))
                fake_bold=op.join(session_dir,'func', f"sub-{sub}_ses-{ses}_bold.nii.gz")
                fake_bold_json=op.join(session_dir,'func', f"sub-{sub}_ses-{ses}_bold.json")
                if not Path(fake_bold).is_file():
                    Path(fake_bold).touch()
                if not Path(fake_bold_json).is_file():
                    Path(fake_bold_json).touch()                
                os.makedirs(op.join(session_dir,'dwi'))
                fake_dwi=op.join(session_dir,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.nii.gz")
                fake_dwi_json=op.join(session_dir,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.json")
                fake_dwi_bvec=op.join(session_dir,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.bvec")
                fake_dwi_bval=op.join(session_dir,'dwi', f"sub-{sub}_ses-{ses}_dir-AP_dwi.bval")
                if not Path(fake_dwi).is_file():
                    Path(fake_dwi).touch()
                if not Path(fake_dwi_json).is_file():
                    Path(fake_dwi_json).touch()  
                if not Path(fake_dwi_bvec).is_file():
                    Path(fake_dwi_bvec).touch()
                if not Path(fake_dwi_bval).is_file():
                    Path(fake_dwi_bval).touch()               
# #%%
if __name__ == "__main__":
    main()
