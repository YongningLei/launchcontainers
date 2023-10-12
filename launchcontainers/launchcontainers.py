import os
import subprocess as sp
import numpy as np
import logging
from dask.distributed import progress
# modules in lc
import dask_scheduler_config as dsq
import prepare_input as prepare
import utils as do
from bids import BIDSLayout

logger=logging.getLogger("GENERAL")

# %% launchcontainers
def generate_cmd(new_lc_config,sub,ses,Dir_analysis, path_to_analysis_config_json,run_lc):
    
    basedir=new_lc_config['general']['basedir']
    homedir= os.path.join(basedir,'singularity_home')
    container= new_lc_config['general']['container']
    host = new_lc_config['general']['host']
    sif_path=  new_lc_config['general']['sif_path']  
    
    containersif = os.path.join(sif_path,container+'_'+new_lc_config['container_specific'][container]['version']+'.sif')

    jobqueue_config= new_lc_config['host_options'][host]

    envcmd= f"module load {jobqueue_config['sin_ver']} "\
    
    if container in ['anatrois', 'rtppreproc','rtp-pipeline']:
        logger.info("\n"+ f'start to generate the DWI PIPELINE command')
        logdir= os.path.join(
                Dir_analysis,
                "sub-" + sub,
                "ses-" + ses,
                "output", "log"
            )
        logfilename=f"{logdir}/t-{container}-sub-{sub}_ses-{ses}"
        path_to_sub_derivatives=os.path.join(Dir_analysis,
                                        f"sub-{sub}",
                                        f"ses-{ses}")
        
        if "BCBL" == host :
            cmd=f"singularity run -e --no-home "\
                f"--bind /bcbl:/bcbl "\
                f"--bind /tmp:/tmp "\
                f"--bind /export:/export "\
                f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "\
                f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "\
                f"--bind {path_to_analysis_config_json}:/flywheel/v0/config.json "\
                f"{sif_path} 2>> {logfilename}.e 1>> {logfilename}.o "
        if ("local" == host):
            path_to_config_json = path_to_analysis_config_json[0]
            cmd=f"singularity run -e --no-home "\
                f"--bind /bcbl:/bcbl "\
                f"--bind /tmp:/tmp "\
                f"--bind /export:/export "\
                f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "\
                f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "\
                f"--bind {path_to_config_json}:/flywheel/v0/config.json "\
                f"{containersif} 2>> {logfilename}.e 1>> {logfilename}.o "
        
        elif "DIPC" == host:
            cmd=f"singularity run --no-home "\
                f"--bind /scratch:/scratch "\
                f"--bind {path_to_sub_derivatives}/input:/flywheel/v0/input:ro "\
                f"--bind {path_to_sub_derivatives}/output:/flywheel/v0/output "\
                f"--bind {path_to_analysis_config_json}:/flywheel/v0/config.json "\
                f"{sif_path} 2>> {logfilename}.e 1>> {logfilename}.o "
    
    if container == 'fmriprep':
        logger.info("\n"+ f'start to generate the FMRIPREP command')
                
        nthreads=new_lc_config["container_specific"][container]['nthreads']
        mem=new_lc_config["container_specific"][container]['mem'] 
        fs_license=new_lc_config["container_specific"][container]['fs_license']
        sif_path=  new_lc_config['general']['sif_path']  
        container_path= os.path.join(sif_path, f"{container}_{new_lc_config['container_specific'][container]['version']}.sif")
        precommand=f'mkdir -p {homedir}; '\
                f'unset PYTHONPATH; ' \
        
        if "local" == host:
            cmd = envcmd + precommand+f'singularity run '\
                    f'-H {homedir} '\
                    f'-B {basedir}:/base -B {fs_license}:/license '\
                    f'--cleanenv {container_path} '\
                    f'-w {Dir_analysis} '\
                    f'/base/BIDS {Dir_analysis} participant '\
                        f'--participant-label sub-{sub} '\
                    f'--skip-bids-validation '\
                    f'--output-spaces func fsnative fsaverage T1w MNI152NLin2009cAsym '\
                    f'--dummy-scans 0 '\
                    f'--use-syn-sdc '\
                    f'--fs-license-file /license/license.txt '\
                    f'--nthreads {nthreads} '\
                    f'--omp-nthreads {nthreads} '\
                    f'--stop-on-first-crash '\
                    f'--mem_mb {(mem*1000)-5000} '\
        
        if host in ['BCBL','DIPC']:
            cmd = precommand+f'singularity run '\
                    f'-H {homedir} '\
                    f'-B {basedir}:/base -B {fs_license}:/license '\
                    f'--cleanenv {container_path} '\
                    f'-w {Dir_analysis} '\
                    f'/base/BIDS {Dir_analysis} participant '\
                        f'--participant-label sub-{sub} '\
                    f'--skip-bids-validation '\
                    f'--output-spaces func fsnative fsaverage T1w MNI152NLin2009cAsym '\
                    f'--dummy-scans 0 '\
                    f'--use-syn-sdc '\
                    f'--fs-license-file /license/license.txt '\
                    f'--nthreads {nthreads} '\
                    f'--omp-nthreads {nthreads} '\
                    f'--stop-on-first-crash '\
                    f'--mem_mb {(mem*1000)-5000} '\

    
    if container in ['prfprepare','prfreport','prfanalyze-vista']:
        config_name=new_lc_config['container_specific'][container]['config_name']
        homedir= os.path.join(basedir,'singularity_home')
        container_path= os.path.join(sif_path, f"{container}_{new_lc_config['container_specific'][container]['version']}.sif")
        if host in ['BCBL','DIPC']:
            cmd=   'unset PYTHONPATH; '\
                f'singularity run '\
                f'-H {homedir} '\
                f'-B {basedir}/derivatives/fmriprep:/flywheel/v0/input '\
                f'-B {Dir_analysis}:/flywheel/v0/output '\
                f'-B {basedir}/BIDS:/flywheel/v0/BIDS '\
                    f'-B {Dir_analysis}/{config_name}.json:/flywheel/v0/config.json '\
	            f'-B {basedir}/license/license.txt:/opt/freesurfer/.license '\
                f'--cleanenv {container_path} '\
        
        elif host == 'local':
            cmd= envcmd+  'unset PYTHONPATH; '\
                f'singularity run '\
                f'-H {homedir} '\
                f'-B {basedir}/derivatives/fmriprep:/flywheel/v0/input '\
                f'-B {Dir_analysis}:/flywheel/v0/output '\
                f'-B {basedir}/BIDS:/flywheel/v0/BIDS '\
                    f'-B {Dir_analysis}/{config_name}.json:/flywheel/v0/config.json '\
	            f'-B {basedir}/license/license.txt:/opt/freesurfer/.license '\
                f'--cleanenv {container_path} '\

    if cmd is None:
        logger.error("\n"+ f'the DWI PIPELINE command is not assigned, please check your config.yaml[general][host] session\n')
        raise ValueError('cmd is not defined, aborting')
    if run_lc:
        sp.run(cmd, shell=True)
    
    return cmd
 
#%% the launchcontainer
def launchcontainer(Dir_analysis, new_lc_config, sub_ses_list, Dict_configs_under_analysisfolder, run_lc):
    """
    This function launches containers generically in different Docker/Singularity HPCs
    This function is going to assume that all files are where they need to be.

    Parameters
    ----------

  
   
   """
    logger.info("\n"+
                "#####################################################\n")

    host = new_lc_config["general"]["host"]
    jobqueue_config= new_lc_config["host_options"][host]
    logger.debug(f'\n,, this is the job_queue config {jobqueue_config}')
    
    force = new_lc_config["general"]["force"]    
    
    # Count how many jobs we need to launch from  sub_ses_list
    n_jobs = np.sum(sub_ses_list.RUN == "True")

    client, cluster = dsq.dask_scheduler(jobqueue_config,n_jobs)
    
    logger.info("---this is the cluster and client\n"
                +f"{client} \n cluster: {cluster} \n")

    new_lc_configs=[]
    subs=[]
    sess=[]
    Dir_analysiss=[]
    paths_to_analysis_config_json=[]
    run_lcs=[]
    
    if not run_lc:
        logger.critical(f"\nlaunchcontainers.py was run in PREPARATION mode (without option --run_lc)\n" \
                            f"Please check that: \n" \
                            f"    (1) launchcontainers.py prepared the input data properly\n" \
                            f"    (2) the command created for each subject is properly formed\n" \
                            f"         (you can copy the command for one subject and launch it " \
                                      f"on the prompt before you launch multiple subjects\n" \
                            f"    (3) Once the check is done, launch the jobs by adding --run_lc to the original command.\n"
        )
        if not (host == 'local'):
            logger.critical(
                        f"The cluster job script for this command is:\n" \
                        f"{cluster.job_script()}"
                        )

    for row in sub_ses_list.itertuples(index=True, name='Pandas'):
        sub  = row.sub
        ses  = row.ses
        RUN  = row.RUN
        dwi  = row.dwi
        if RUN=="True":



            path_to_analysis_config_json = Dict_configs_under_analysisfolder["new_container_specific_config_path"]
            path_to_config_yaml = Dict_configs_under_analysisfolder["new_lc_config_path"]
            path_to_subSesList  = Dict_configs_under_analysisfolder["new_sub_ses_list_path"]


    
            
            new_lc_configs.append(new_lc_config)
            subs.append(sub)
            sess.append(ses)
            Dir_analysiss.append(Dir_analysis)
            paths_to_analysis_config_json.append(path_to_analysis_config_json)
            run_lcs.append(run_lc)
            
            if not run_lc:
                # this cmd is only for print the command 
                command= generate_cmd(new_lc_config,sub,ses,Dir_analysis, path_to_analysis_config_json,run_lc)
                logger.critical(f"\nCOMMAND for subject-{sub}, and session-{ses}:\n" \
                                f"{command}\n\n"
                                )
                if new_lc_config['general']['container']=='fmriprep':
                    logger.critical('\n'+ 'fmriprep now can not deal with session specification, so the analysis are running on all sessions of the subject you are specifying')

   


  
        
    if run_lc:
        futures = client.map(generate_cmd,new_lc_configs,subs,sess,Dir_analysiss,paths_to_analysis_config_json, run_lcs)
        progress(futures)
        results = client.gather(futures)
        logger.info(results)
        logger.info('###########')
        client.close()
        cluster.close()
        
        logger.critical("\n"
                        + "lanchcontainer finished, all the jobs are done")
    
    return
# %% main()
def main():
    #get the path from commandline input
    parser_namespace = do.get_parser()
    lc_config_path = parser_namespace.lc_config
    lc_config = do.read_yaml(lc_config_path)   
    container= lc_config['general']['container']
    sub_ses_list_path = parser_namespace.sub_ses_list
    sub_ses_list = do.read_df(sub_ses_list_path)    
    
    # stored value
    run_lc = parser_namespace.run_lc
    verbose=parser_namespace.verbose
    debug= parser_namespace.DEBUG
    
    #set the logging level to get the command
    do.setup_logger()    
    print_command_only=lc_config["general"]["print_command_only"] #TODO this should be defined using -v and -print command only
    
    # set logger message level TODO: this should be implement to be changeable for future 
    if print_command_only:    
        logger.setLevel(logging.CRITICAL)
    if verbose:
        logger.setLevel(logging.INFO)    
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # prepare file and launch containers
    # first of all prepare the analysis folder: it create you the analysis folder automatically so that you are not messing up with different analysis
    Dir_analysis, Dict_configs_under_analysisfolder = prepare.prepare_analysis_folder(parser_namespace, lc_config)
    
    # the config information that goes to the container
    new_lc_config=do.read_yaml(Dict_configs_under_analysisfolder["new_lc_config_path"])
    new_sub_ses_list=do.read_df(Dict_configs_under_analysisfolder["new_sub_ses_list_path"])
    basedir=new_lc_config['general']['basedir']
    
    # for DWI pipeline
    if container in ['anatrois', 'rtppreproc', 'rtp-pipeline']:
        prepare.prepare_dwi_input(parser_namespace, Dir_analysis, lc_config, sub_ses_list, run_lc)
    
    if container == 'fmriprep':
        bidslayout= BIDSLayout(os.path.join(basedir,'BIDS'))
        prepare.fmrprep_intended_for(sub_ses_list, bidslayout)
    
    if container in ['prfprepare', 'prfanalyze-vista', 'prfreport']:
        bidslayout= BIDSLayout(os.path.join(basedir,'BIDS'))
        config_name=new_lc_config['container_specific'][container]['config_name']
        config_path= os.path.join(Dir_analysis, f'{config_name}.json')
        prepare.prepare_prf_input(basedir, container, config_path,sub_ses_list, bidslayout ,run_lc)
    

    
    launchcontainer(Dir_analysis, new_lc_config , new_sub_ses_list, Dict_configs_under_analysisfolder, run_lc)
    

    
# #%%
if __name__ == "__main__":
    main()
