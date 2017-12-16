#!/usr/bin/env python

import os, sys, numpy

import podi_ephemerides as ephem
import multiprocessing


def handler(queue, **kwargs):

    # print kwargs

    ephemdata = None
    # print "querying MPC"

    ephemdata = ephem.get_ephemerides_for_object(**kwargs)
    #     object_name=object_name,
    #     start_datetime=start_datetime,
    #     end_datetime=end_datetime,
    #     time_interval=time_interval,
    #     session_log_file=log_file,
    #     verbose=False,
    # )

    queue.put(ephemdata)

    return

def query_horizons(timeout, **kwargs):

    queue = multiprocessing.Queue()

    kwargs['queue'] = queue
    #kwargs['verbose'] = True

    p = multiprocessing.Process(target=handler, kwargs=kwargs)
    p.start()
    p.join(timeout)
    if (p.is_alive()):
        print "Terminating task after timeout"
        p.terminate()
        results = None
    else:
        results = queue.get()

    # print kwargs

    return results

if __name__ == "__main__":

    start_datetime = '2017-12-10'
    end_datetime = '2018-01-15'
    time_interval = '6h'

    fn = sys.argv[1]
    with open(fn, "r") as f:
        comets = f.readlines()

    try:
        output_dir = sys.argv[2]
    except:
        output_dir = "."
        pass

    timeout = 60

    for line_number, line in enumerate(comets):
        if (line_number < 583):
            continue

        name = line[102:158]
        # print name

        object_name = " ".join(name.split(' ')[:2])
        if (object_name.find('/') >= 0):
            object_name = object_name.split("/")[0]
            print "REFINED:", object_name

        save_filename = name.strip()
        for c in [' ', '/', '(', ')', ' ']:
            save_filename = save_filename.replace(c, '_')
        print "% 4d :: %50s ==> %s" %(line_number, name, save_filename)

        if (save_filename[-1] == "_"): save_filename = save_filename[:-1]
        log_file = "%s/%s.log" % (output_dir, save_filename)
        ephem_file = "%s/%s.ephem" % (output_dir, save_filename)

        ephemdata = query_horizons(timeout=timeout,
                                   object_name = object_name,
                                   start_datetime = start_datetime,
                                   end_datetime = end_datetime,
                                   time_interval = time_interval,
                                   session_log_file=log_file,
                                   verbose=False,
                                   )

        # ephemdata = ephem.get_ephemerides_for_object(
        #     object_name = object_name,
        #     start_datetime = start_datetime,
        #     end_datetime = end_datetime,
        #     time_interval = time_interval,
        #     session_log_file=log_file,
        #     verbose=False,
        #     )

        if (ephemdata is not None):
            numpy.savetxt(ephem_file, ephemdata['data'])
        #with open(save_filename, "w") as ef:
        #    ef.write(ephemdata)


        # break
            
