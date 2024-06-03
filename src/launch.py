# -*- coding: utf-8 -*-
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
import os
import subprocess as sp
from subprocess import Popen
import numpy as np
import logging

# modules in lc

from bids import BIDSLayout
from dask.distributed import progress

from prepare_inputs import dask_scheduler_config as dsq
from prepare_inputs import prepare as prepare
from prepare_inputs import utils as do

logger = logging.getLogger("GENERAL")


# %% launchcontainers
def generate_cmd(
    lc_config, sub, ses, dir_analysis, lst_container_specific_configs, run_lc
):
    """Puts together the command to send to the container.

    Args:
        lc_config (str): _description_
        sub (str): _description_
        ses (str): _description_
        dir_analysis (str): _description_
        lst_container_specific_configs (list): _description_
        run_lc (str): _description_

    Raises:
        ValueError: Raised in presence of a faulty config.yaml file, or when the formed command is not recognized.

    Returns:
        _type_: _description_
    """

    # Relevant directories
    # All other relevant directories stem from this one
    basedir = lc_config["general"]["basedir"]

    homedir = os.path.join(basedir, "singularity_home")
    container = lc_config["general"]["container"]
    host = lc_config["general"]["host"]
    containerdir = lc_config["general"]["containerdir"]

    # Information relevant to the host and container
    jobqueue_config = lc_config["host_options"][host]
    version = lc_config["container_specific"][container]["version"]
    use_module = jobqueue_config["use_module"]
    bind_options = jobqueue_config["bind_options"]

    # Location of the Singularity Image File (.sif)
    container_name = os.path.join(containerdir, f"{container}_{version}.sif")
    # Define the directory and the file name to output the log of each subject
    logdir = os.path.join(dir_analysis, "sub-" + sub, "ses-" + ses, "output", "log")
    logfilename = f"{logdir}/t-{container}-sub-{sub}_ses-{ses}"

    path_to_sub_derivatives = os.path.join(dir_analysis, f"sub-{sub}", f"ses-{ses}")

    bind_cmd = ""
    for bind in bind_options:
        bind_cmd += f"--bind {bind}:{bind} "

    env_cmd = ""
    if host == "local":
        if use_module == True:
            env_cmd = f"module load {jobqueue_config['apptainer']} &&"

    if container in ["anatrois", "rtppreproc", "rtp-pipeline"]:
        logger.info("\n" + "start to generate the DWI PIPELINE command")
        logger.debug(
            f"\n the sub is {sub} \n the ses is {ses} \n the analysis dir is {dir_analysis}"
        )

        cmd = (
            f"{env_cmd} singularity run -e --no-home {bind_cmd}"
            f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "
            f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "
            f"--bind {path_to_sub_derivatives}/output/log/config.json:/flywheel/v0/config.json "
            f"{container_name} 1>> {logfilename}.o 2>> {logfilename}.e  "
        )

    if container == "freesurferator":
        logger.info("\n" + "FREESURFERATOR command")
        logger.debug(
            f"\n the sub is {sub} \n the ses is {ses} \n the analysis dir is {dir_analysis}"
        )

        cmd = (
            f"{env_cmd} apptainer run --containall --pwd /flywheel/v0 {bind_cmd}"
            f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "
            f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "
            f"--bind {path_to_sub_derivatives}/work:/flywheel/v0/work "
            f"--bind {path_to_sub_derivatives}/output/log/config.json:/flywheel/v0/config.json "
            f"--env PATH=/opt/freesurfer/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/freesurfer/fsfast/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/sbin:/bin:/opt/ants/bin "
            f"--env LANG=C.UTF-8 "
            f"--env GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568 "
            f"--env PYTHON_VERSION=3.9.15 "
            f"--env PYTHON_PIP_VERSION=22.0.4 "
            f"--env PYTHON_SETUPTOOLS_VERSION=58.1.0 "
            f"--env PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/66030fa03382b4914d4c4d0896961a0bdeeeb274/public/get-pip.py "
            f"--env PYTHON_GET_PIP_SHA256=1e501cf004eac1b7eb1f97266d28f995ae835d30250bec7f8850562703067dc6 "
            f"--env FLYWHEEL=/flywheel/v0 "
            f"--env ANTSPATH=/opt/ants/bin/ "
            f"--env FREESURFER_HOME=/opt/freesurfer "
            f"--env FREESURFER=/opt/freesurfer "
            f"--env DISPLAY=:50.0 "
            f"--env FS_LICENSE=/flywheel/v0/work/license.txt "
            f"--env OS=Linux "
            f"--env FS_OVERRIDE=0 "
            f"--env FSF_OUTPUT_FORMAT=nii.gz "
            f"--env MNI_DIR=/opt/freesurfer/mni "
            f"--env LOCAL_DIR=/opt/freesurfer/local "
            f"--env FSFAST_HOME=/opt/freesurfer/fsfast "
            f"--env MINC_BIN_DIR=/opt/freesurfer/mni/bin "
            f"--env MINC_LIB_DIR=/opt/freesurfer/mni/lib "
            f"--env MNI_DATAPATH=/opt/freesurfer/mni/data "
            f"--env FMRI_ANALYSIS_DIR=/opt/freesurfer/fsfast "
            f"--env PERL5LIB=/opt/freesurfer/mni/lib/perl5/5.8.5 "
            f"--env MNI_PERL5LIB=/opt/freesurfer/mni/lib/perl5/5.8.5 "
            f"--env XAPPLRESDIR=/opt/freesurfer/MCRv97/X11/app-defaults "
            f"--env MCR_CACHE_ROOT=/flywheel/v0/output "
            f"--env MCR_CACHE_DIR=/flywheel/v0/output/.mcrCache9.7 "
            f"--env FSL_OUTPUT_FORMAT=nii.gz "
            f"--env ANTS_VERSION=v2.4.2 "
            f"--env QT_QPA_PLATFORM=xcb "
            f"--env PWD=/flywheel/v0 "
            f"{container_name} "
            f"-c python run.py 1> {logfilename}.o 2> {logfilename}.e  "
        )

    if container == "rtp2-preproc":
        logger.info("\n" + "rtp2-preproc command")
        logger.debug(
            f"\n the sub is {sub} \n the ses is {ses} \n the analysis dir is {dir_analysis}"
        )

        cmd = (
            f"{env_cmd} apptainer run --containall --pwd /flywheel/v0 {bind_cmd}"
            f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "
            f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "
            f"--bind {path_to_sub_derivatives}/work:/flywheel/v0/work "
            f"--bind {path_to_sub_derivatives}/output/log/config.json:/flywheel/v0/config.json "
            f"--env FLYWHEEL=/flywheel/v0 "
            f"--env LD_LIBRARY_PATH=/opt/fsl/lib:  "
            f"--env FSLWISH=/opt/fsl/bin/fslwish  "
            f"--env FSLTCLSH=/opt/fsl/bin/fsltclsh  "
            f"--env FSLMULTIFILEQUIT=TRUE "
            f"--env FSLOUTPUTTYPE=NIFTI_GZ  "
            f"--env FSLDIR=/opt/fsl  "
            f"--env FREESURFER_HOME=/opt/freesurfer  "
            f"--env ARTHOME=/opt/art  "
            f"--env ANTSPATH=/opt/ants/bin  "
            f"--env PYTHON_GET_PIP_SHA256=1e501cf004eac1b7eb1f97266d28f995ae835d30250bec7f8850562703067dc6 "
            f"--env PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/66030fa03382b4914d4c4d0896961a0bdeeeb274/public/get-pip.py "
            f"--env PYTHON_PIP_VERSION=22.0.4  "
            f"--env PYTHON_VERSION=3.9.15  "
            f"--env GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568  "
            f"--env LANG=C.UTF-8  "
            f"--env PATH=/opt/mrtrix3/bin:/opt/ants/bin:/opt/art/bin:/opt/fsl/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "
            f"--env PYTHON_SETUPTOOLS_VERSION=58.1.0 -e DISPLAY=:50.0 -e QT_QPA_PLATFORM=xcb  "
            f"--env FS_LICENSE=/opt/freesurfer/license.txt  "
            f"--env PWD=/flywheel/v0 "
            f"{container_name} "
            f"-c python run.py 1> {logfilename}.o 2> {logfilename}.e  "
        )
    
    if container == "rtp2-pipeline":
        logger.info("\n" + "rtp2-pipeline command")
        logger.debug(
            f"\n the sub is {sub} \n the ses is {ses} \n the analysis dir is {dir_analysis}"
        )

        cmd = (
            f"{env_cmd} apptainer run --containall --pwd /flywheel/v0 {bind_cmd}"
            f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "
            f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "
            f"--bind {path_to_sub_derivatives}/work:/flywheel/v0/work "
            f"--bind {path_to_sub_derivatives}/output/log/config.json:/flywheel/v0/config.json "
            f"--env PATH=/opt/mrtrix3/bin:/opt/ants/bin:/opt/art/bin:/opt/fsl/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin "
            f"--env LANG=C.UTF-8 -e GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568 "
            f"--env PYTHON_VERSION=3.9.15 "
            f"--env PYTHON_PIP_VERSION=22.0.4 "
            f"--env PYTHON_SETUPTOOLS_VERSION=58.1.0 "
            f"--env PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/66030fa03382b4914d4c4d0896961a0bdeeeb274/public/get-pip.py "
            f"--env PYTHON_GET_PIP_SHA256=1e501cf004eac1b7eb1f97266d28f995ae835d30250bec7f8850562703067dc6 "
            f"--env ANTSPATH=/opt/ants/bin "
            f"--env ARTHOME=/opt/art "
            f"--env FREESURFER_HOME=/opt/freesurfer "
            f"--env FSLDIR=/opt/fsl "
            f"--env FSLOUTPUTTYPE=NIFTI_GZ "
            f"--env FSLMULTIFILEQUIT=TRUE "
            f"--env FSLTCLSH=/opt/fsl/bin/fsltclsh "
            f"--env FSLWISH=/opt/fsl/bin/fslwish "
            f"--env LD_LIBRARY_PATH=/opt/mcr/v99/runtime/glnxa64:/opt/mcr/v99/bin/glnxa64:/opt/mcr/v99/sys/os/glnxa64:/opt/mcr/v99/extern/bin/glnxa64:/opt/fsl/lib: "
            f"--env FLYWHEEL=/flywheel/v0 "
            f"--env TEMPLATES=/templates "
            f"--env XAPPLRESDIR=/opt/mcr/v99/X11/app-defaults "
            f"--env MCR_CACHE_FOLDER_NAME=/flywheel/v0/output/.mcrCache9.9 "
            f"--env MCR_CACHE_ROOT=/flywheel/v0/output "
            f"--env MRTRIX_TMPFILE_DIR=/flywheel/v0/output/tmp "
            f"--env PWD=/flywheel/v0 "
            f"{container_name} "
            f"-c python run.py 1> {logfilename}.o 2> {logfilename}.e  "
        )
    
    # Check which container we are using, and define the command accordingly
    if container == "fmriprep":
        logger.info("\n" + f"start to generate the FMRIPREP command")

        nthreads = lc_config["container_specific"][container]["nthreads"]
        mem = lc_config["container_specific"][container]["mem"]
        fs_license = lc_config["container_specific"][container]["fs_license"]
        containerdir = lc_config["general"]["containerdir"]
        container_path = os.path.join(
            containerdir,
            f"{container}_{lc_config['container_specific'][container]['version']}.sif",
        )
        precommand = f"mkdir -p {homedir}; " f"unset PYTHONPATH; "
        if "local" == host:
            cmd = (
                precommand + f"singularity run "
                f"-H {homedir} "
                f"-B {basedir}:/base -B {fs_license}:/license "
                f"--cleanenv {container_path} "
                f"-w {dir_analysis} "
                f"/base/BIDS {dir_analysis} participant "
                f"--participant-label sub-{sub} "
                f"--skip-bids-validation "
                f"--output-spaces func fsnative fsaverage T1w MNI152NLin2009cAsym "
                f"--dummy-scans 0 "
                f"--use-syn-sdc "
                f"--fs-license-file /license/license.txt "
                f"--nthreads {nthreads} "
                f"--omp-nthreads {nthreads} "
                f"--stop-on-first-crash "
                f"--mem_mb {(mem*1000)-5000} "
            )
        if host in ["BCBL", "DIPC"]:
            cmd = (
                precommand + f"singularity run "
                f"-H {homedir} "
                f"-B {basedir}:/base -B {fs_license}:/license "
                f"--cleanenv {container_path} "
                f"-w {dir_analysis} "
                f"/base/BIDS {dir_analysis} participant "
                f"--participant-label sub-{sub} "
                f"--skip-bids-validation "
                f"--output-spaces func fsnative fsaverage T1w MNI152NLin2009cAsym "
                f"--dummy-scans 0 "
                f"--use-syn-sdc "
                f"--fs-license-file /license/license.txt "
                f"--nthreads {nthreads} "
                f"--omp-nthreads {nthreads} "
                f"--stop-on-first-crash "
                f"--mem_mb {(mem*1000)-5000} "
            )

    if container in ["prfprepare", "prfreport", "prfanalyze-vista"]:
        config_name = lc_config["container_specific"][container]["config_name"]
        homedir = os.path.join(basedir, "singularity_home")
        container_path = os.path.join(
            containerdir,
            f"{container}_{lc_config['container_specific'][container]['version']}.sif",
        )
        if host in ["BCBL", "DIPC"]:
            cmd = (
                "unset PYTHONPATH; "
                f"singularity run "
                f"-H {homedir} "
                f"-B {basedir}/derivatives/fmriprep:/flywheel/v0/input "
                f"-B {dir_analysis}:/flywheel/v0/output "
                f"-B {basedir}/BIDS:/flywheel/v0/BIDS "
                f"-B {dir_analysis}/{config_name}.json:/flywheel/v0/config.json "
                f"-B {basedir}/license/license.txt:/opt/freesurfer/.license "
                f"--cleanenv {container_path} "
            )
        elif host == "local":
            cmd = (
                "unset PYTHONPATH; "
                f"singularity run "
                f"-H {homedir} "
                f"-B {basedir}/derivatives/fmriprep:/flywheel/v0/input "
                f"-B {dir_analysis}:/flywheel/v0/output "
                f"-B {basedir}/BIDS:/flywheel/v0/BIDS "
                f"-B {dir_analysis}/{config_name}.json:/flywheel/v0/config.json "
                f"-B {basedir}/license/license.txt:/opt/freesurfer/.license "
                f"--cleanenv {container_path} "
            )
    # If after all configuration, we do not have command, raise an error
    if cmd is None:
        logger.error(
            "\n"
            + f"the DWI PIPELINE command is not assigned, please check your config.yaml[general][host] session\n"
        )
        raise ValueError("cmd is not defined, aborting")

    # GLU: I don't think this is right, run is done below, I will make it work just for local but not in here,
    #      it is good that this function just creates the cmd, I would keep it like that
    if run_lc:
       return(sp.run(cmd, shell = True))
    else:
        return cmd
    #     sp.run(cmd, shell=True)
    #return cmd


# %% the launchcontainer
def launchcontainer(
    dir_analysis,
    lc_config,
    sub_ses_list,
    parser_namespace,
    path_to_analysis_container_specific_config
):
    """
    This function launches containers generically in different Docker/Singularity HPCs
    This function is going to assume that all files are where they need to be.

    Args:
        dir_analysis (str): _description_
        lc_config (str): path to launchcontainer config.yaml file
        sub_ses_list (_type_): parsed CSV containing the subject list to be analyzed, and the analysis options
        parser_namespace (argparse.Namespace): command line arguments
    """
    logger.info("\n" + "#####################################################\n")

    # Get the host and jobqueue config info from the config.yaml file
    host = lc_config["general"]["host"]
    jobqueue_config = lc_config["host_options"][host]
    if host == "local":
        launch_mode = jobqueue_config["launch_mode"]
    logger.debug(f"\n,, this is the job_queue config {jobqueue_config}")

    force = lc_config["general"]["force"]
    logdir = os.path.join(dir_analysis, "daskworker_log")

    # Count how many jobs we need to launch from  sub_ses_list
    n_jobs = np.sum(sub_ses_list.RUN == "True")

    run_lc = parser_namespace.run_lc

    lc_configs = []
    subs = []
    sess = []
    dir_analysiss = []
    paths_to_analysis_config_json = []
    run_lcs = []
    # PREPARATION mode
    if not run_lc:
        logger.critical(
            f"\nlaunchcontainers.py was run in PREPARATION mode (without option --run_lc)\n"
            f"Please check that: \n"
            f"    (1) launchcontainers.py prepared the input data properly\n"
            f"    (2) the command created for each subject is properly formed\n"
            f"         (you can copy the command for one subject and launch it "
            f"on the prompt before you launch multiple subjects\n"
            f"    (3) Once the check is done, launch the jobs by adding --run_lc to the first command you executed.\n"
        )
        # If the host is not local, print the job script to be launched in the cluster.
        if host != "local" or (host == "local" and launch_mode == "dask_worker"):
            client, cluster = create_cluster_client(jobqueue_config, n_jobs, logdir)
            if host != "local":
                logger.critical(
                    f"The cluster job script for this command is:\n"
                    f"{cluster.job_script()}"
                )
            elif host == "local" and launch_mode == "dask_worker":
                logger.critical(
                    f"The cluster job script for this command is:\n"
                    f"{cluster}"
                )
    # Iterate over the provided subject list
    commands = list()
    for row in sub_ses_list.itertuples(index=True, name="Pandas"):
        sub = row.sub
        ses = row.ses
        RUN = row.RUN
        dwi = row.dwi

        if RUN == "True":
            # Append config, subject, session, and path info in corresponding lists
            lc_configs.append(lc_config)
            subs.append(sub)
            sess.append(ses)
            dir_analysiss.append(dir_analysis)
            paths_to_analysis_config_json.append(
                path_to_analysis_container_specific_config[0]
            )
            run_lcs.append(run_lc)

            # This cmd is only for print the command
            command = generate_cmd(
                lc_config,
                sub,
                ses,
                dir_analysis,
                path_to_analysis_container_specific_config,
                False # always False if Print only
            )
            commands.append(command)
            if not run_lc:
                logger.critical(
                    f"\nCOMMAND for subject-{sub}, and session-{ses}:\n"
                    f"{command}\n\n"
                )

                if not run_lc and lc_config["general"]["container"] == "fmriprep":
                    logger.critical(
                        f"\n"
                        f"fmriprep now can not deal with session specification, "
                        f"so the analysis are running on all sessions of the "
                        f"subject you are specifying"
                    )

    # RUN mode
    if run_lc and host != "local":
        run_dask(
            jobqueue_config, 
            n_jobs, 
            logdir, 
            lc_configs, 
            subs, 
            sess, 
            dir_analysiss,
            paths_to_analysis_config_json,
            run_lcs
        )

    if run_lc and host == "local":
        if launch_mode == "parallel":
            logger.critical(
                f"\nLocally launching {len(commands)} jobs in parallel, check "
                f"your server's memory, some jobs might fail\n"
            )
            procs = [ Popen(i, shell=True) for i in commands ]
            for p in procs:
                p.wait()
        elif launch_mode == "dask_worker":
            logger.critical(
                f"\nLocally launching {len(commands)} jobs with dask-worker, "
                f" keep an eye on your server's memory\n"
            )
            run_dask(
                jobqueue_config, 
                n_jobs, 
                logdir, 
                lc_configs, 
                subs, 
                sess, 
                dir_analysiss,
                paths_to_analysis_config_json,
                run_lcs
            )
        elif launch_mode == "serial":  # Run this with dask...
            logger.critical(
                f"Locally launching {len(commands)} jobs in series, this might take a lot of time"
            )
            serial_cmd = ""
            for i, cmd in enumerate(commands):
                if i == 0:
                    serial_cmd = cmd
                else:
                    serial_cmd += f" && {cmd}"
            logger.critical(
                f"LAUNCHING SUPER SERIAL {len(commands)} JOBS:\n{serial_cmd}\n"
            )
            sp.run(serial_cmd, shell=True)

    return

def create_cluster_client(jobqueue_config, n_jobs, logdir):
    client, cluster = dsq.dask_scheduler(jobqueue_config, n_jobs, logdir)
    return client, cluster

def run_dask(
    jobqueue_config, 
    n_jobs, 
    logdir, 
    lc_configs, 
    subs, 
    sess, 
    dir_analysiss,
    paths_to_analysis_config_json,
    run_lcs
    ):
    
    client, cluster = create_cluster_client(jobqueue_config, n_jobs, logdir)
    logger.info(
        "---this is the cluster and client\n" + f"{client} \n cluster: {cluster} \n"
    )
    print(subs)
    print(sess)
    # Compose the command to run in the cluster
    futures = client.map(
        generate_cmd,
        lc_configs,
        subs,
        sess,
        dir_analysiss,
        paths_to_analysis_config_json,
        run_lcs
    )
    # Record the progress
    progress(futures)
    # Get the info and report it in the logger
    results = client.gather(futures)
    logger.info(results)
    logger.info("###########")
    # Close the connection with the client and the cluster, and inform about it
    client.close()
    cluster.close()

    logger.critical("\n" + "launchcontainer finished, all the jobs are done")
    #return client, cluster


# %% main()
def main():
    # Set the logging level to get the command
    do.setup_logger()

    # Get the path from command line input
    parser_namespace = do.get_parser()
    lc_config_path = parser_namespace.lc_config
    lc_config = do.read_yaml(lc_config_path)

    # Get general information from the config.yaml file
    container = lc_config["general"]["container"]
    basedir = lc_config["general"]["basedir"]
    bidsdir_name = lc_config["general"]["bidsdir_name"]
    sub_ses_list_path = parser_namespace.sub_ses_list
    sub_ses_list = do.read_df(sub_ses_list_path)

    # Stored value
    verbose = parser_namespace.verbose
    debug = parser_namespace.DEBUG

    # Set the verbosity level
    print_command_only = lc_config["general"][
        "print_command_only"
    ]  # TODO: this should be defined using -v and -print command only

    # Set logger message level
    # TODO: this implementation should allow changing the level of verbosity in the three levels
    if print_command_only:
        logger.setLevel(logging.CRITICAL)
    if verbose:
        logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.critical("Reading the BIDS layout...")
    # Prepare file and launch containers
    # First of all prepare the analysis folder: it create you the analysis folder automatically so that you are not messing up with different analysis
    dir_analysis, path_to_analysis_container_specific_config = (
        prepare.prepare_analysis_folder(parser_namespace, lc_config)
    )
    layout = BIDSLayout(os.path.join(basedir, bidsdir_name))
    logger.critical("                       ... finished reading the BIDS layout.")

    # Prepare mode
    if container in [
        "anatrois",
        "rtppreproc",
        "rtp-pipeline",
        "freesurferator"
    ]:  # TODO: define list in another module for reusability accross modules and functions
        prepare.prepare_dwi_input(
            parser_namespace, dir_analysis, lc_config, sub_ses_list, layout, path_to_analysis_container_specific_config
        )

    if container == "fmriprep":
        prepare.fmriprep_intended_for(sub_ses_list, layout)

    if container in ["prfprepare", "prfanalyze-vista", "prfreport"]:
        logger.info(f"Container not implemented yet.")
        pass

    # Run mode
    launchcontainer(
        dir_analysis,
        lc_config,
        sub_ses_list,
        parser_namespace,
        path_to_analysis_container_specific_config
    )


# #%%
if __name__ == "__main__":
    main()
