#
# Copyright (C) 2014, Ralf Kotulla
#                     kotulla@uwm.edu
#
# All rights reserved
#

import numpy
import logging
import multiprocessing
import os
import time
import subprocess

import podi_sitesetup as sitesetup


def parallel_sourceextractor(queue, dummy):

    logger = logging.getLogger("ParSEx")

    while (True):

        cmd = queue.get()
        if (cmd == None):
            queue.task_done()
            break

        sexcmd, fitsfile = cmd
        logger.info("Creating source catalog for %s" % (fitsfile))
        start_time = time.time()
        try:
            ret = subprocess.Popen(sexcmd.split(), 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            (sex_stdout, sex_stderr) = ret.communicate()
            #os.system(sexcmd)
            if (ret.returncode != 0):
                logger.warning("Sextractor might have a problem, check the log")
                logger.debug("Stdout=\n"+sex_stdout)
                logger.debug("Stderr=\n"+sex_stderr)
        except OSError as e:
            podi_logging.log_exception()
            print >>sys.stderr, "Execution failed:", e
        end_time = time.time()
        logger.debug("SourceExtractor returned after %.3f seconds" % (end_time - start_time))

        queue.task_done()

def make_catalogs(inputlist, sex_config, sex_param, use_weight=True):

    jobqueue = multiprocessing.JoinableQueue()

    logger = logging.getLogger("MakeCat")

    number_sex_runs = 0
    for fitsfile in inputlist:
        catfile = "%s.cat" % (fitsfile[:-5])

        if (os.path.isfile(catfile)):
            # Don't do anything if the catalog already exists
            continue

        # check if there is a weight image available; if so, use it
        weight_params = ""
        weightfile = fitsfile[:-5]+".weight.fits"
        if (os.path.isfile(weightfile) and use_weight):
            weight_params = "-WEIGHT_TYPE MAP_WEIGHT -WEIGHT_IMAGE %s" % (weightfile)

        logger.debug("Ordering source catalog for %s" % (fitsfile))
        sex_config_file = "%s/config/%s" % (sitesetup.exec_dir, sex_config)
        parameters_file = "%s/config/%s" % (sitesetup.exec_dir, sex_param)
        sexcmd = "%(sex)s -c %(config)s -PARAMETERS_NAME %(param)s -CATALOG_NAME %(catname)s %(weight)s %(inputfile)s" % {
            'sex': sitesetup.sextractor,
            'config': sex_config_file,
            'param': parameters_file, 
            'catname': catfile, 
            'weight': weight_params,
            'inputfile': fitsfile,
        }
        
        jobqueue.put((sexcmd, fitsfile))
        number_sex_runs += 1

    logger.info("Ordered %d new source catalogs, please wait" % (number_sex_runs))

    #
    # Start worker processes
    #
    worker_args = (jobqueue, "")
    processes = []
    for i in range(sitesetup.number_cpus):
        p = multiprocessing.Process(target=parallel_sourceextractor, args=worker_args)
        p.start()
        processes.append(p)

        # also add a quit-command for each process
        jobqueue.put(None)
        
    #
    # wait until all work is done
    #
    jobqueue.join()
    logger.info("All source catalogs have been created!")

    return

