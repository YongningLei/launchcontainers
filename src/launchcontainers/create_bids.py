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
def setup_logger(verbose=True, log_dir=None, log_filename=None):
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
    # read ymal and setup the bids folder
    
    newcontainer_config_path = parser_namespace.creat_bids_config
    newcontainer_config = do.read_yaml(newcontainer_config_path)
    

    # Get general information from the config.yaml file
    basedir=newcontainer_config["general"]["basedir"]
    bidsdir_name=newcontainer_config["general"]["bidsdir_name"]
    container=newcontainer_config["general"]["container"]
    version=newcontainer_config["general"]["version"]
    analysis_name=newcontainer_config["general"]["analysis_name"]
    file_name=newcontainer_config["general"]["file_name"]
    
    log_dir=newcontainer_config["general"]["log_dir"]
    log_filename=newcontainer_config["general"]["log_filename"]
    
    # get stuff from subseslist for future jobs scheduling
    sub_ses_list_path = parser_namespace.sub_ses_list
    sub_ses_list,num_of_true_run = do.read_df(sub_ses_list_path)
    

    
    if not container == "nifti":
        if log_dir=="analysis_dir":
            log_dir=op.join(basedir,bidsdir_name,'derivatives',f'{container}_{version}',f"analysis-{analysis_name}")
        setup_logger(True, log_dir, log_filename)
        for row in sub_ses_list.itertuples(index=True, name="Pandas"):
            sub = row.sub
            ses = row.ses
            RUN = row.RUN
            
            session_dir = op.join(
                basedir,
                bidsdir_name,
                "derivatives",
                f'{container}_{version}',
                "analysis-" + analysis_name,
                "sub-" + sub,
                "ses-" + ses
                )
            input_dir=op.join(session_dir,'input')
            outpt_dir=op.join(session_dir,'output')
            fake_file=op.join(outpt_dir,file_name)
            if not op.exists(input_dir):
                os.makedirs(input_dir)
            else:
                logger.info(f"Input folder for sub-{sub}/ses-{ses} is there")
            if not op.exists(outpt_dir):
                os.makedirs(outpt_dir)
            else:
                logger.info(f"Output folder for sub-{sub}/ses-{ses} is there")
            if not Path(fake_file).is_file():
                Path(fake_file).touch()
            else:
                logger.info(f"The file for sub-{sub}/ses-{ses}/output is there")      
    else:
        if log_dir=="analysis_dir":
            log_dir=op.join(basedir,bidsdir_name,'nifti_log')
        setup_logger(True, log_dir, log_filename)

        for row in sub_ses_list.itertuples(index=True, name="Pandas"):
            sub = row.sub
            ses = row.ses
            RUN = row.RUN
            
            session_dir = op.join(
                basedir,
                bidsdir_name,
                "sub-" + sub,
                "ses-" + ses
                )
            description_file= op.join(
                basedir,
                bidsdir_name,
                "dataset_description.json")
            Path(description_file).touch()
            anat_dir=op.join(session_dir,'anat')
            fmri_dir=op.join(session_dir,'fmri')
            dwi_dir=op.join(session_dir,'dwi')
            
            if not op.exists(anat_dir):
                os.makedirs(anat_dir)
            else:
                logger.info(f"anat folder for sub-{sub}/ses-{ses} is there")
            if not op.exists(fmri_dir):
                os.makedirs(fmri_dir)
            else:
                logger.info(f"fmri folder for sub-{sub}/ses-{ses} is there")
            if not op.exists(dwi_dir):
                os.makedirs(dwi_dir)
            else:
                logger.info(f"dwi folder for sub-{sub}/ses-{ses} is there")            


# #%%
if __name__ == "__main__":
    main()
