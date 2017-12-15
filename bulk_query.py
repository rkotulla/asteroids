#!/usr/bin/env python

import os, sys, numpy

import podi_ephemerides as ephem

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


    for line in comets[211:]:
        name = line[102:158]
        # print name

        object_name = " ".join(name.split(' ')[:2])

        save_filename = name.strip()
        for c in [' ', '/', '(', ')', ' ']:
            save_filename = save_filename.replace(c, '_')
        print "%50s ==> %s" %(name, save_filename)

        if (save_filename[-1] == "_"): save_filename = save_filename[:-1]
        log_file = "%s/%s.log" % (output_dir, save_filename)
        ephem_file = "%s/%s.ephem" % (output_dir, save_filename)

        ephemdata = ephem.get_ephemerides_for_object(
            object_name = object_name,
            start_datetime = start_datetime,
            end_datetime = end_datetime,
            time_interval = time_interval,
            session_log_file=log_file,
            verbose=False,
            )

        numpy.savetxt(ephem_file, ephemdata['data'])
        #with open(save_filename, "w") as ef:
        #    ef.write(ephemdata)

            
