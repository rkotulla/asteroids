#!/usr/bin/env python


import pyfits
import numpy
import math
import scipy
import os, sys
import time
import warnings

_dir, _ = os.path.split(os.path.abspath(sys.argv[0]))
sys.path.append(_dir+"/../")

import matplotlib.pyplot

from podi_commandline import *
from podi_definitions import *
from profile import *
from meanprofile import *
import podi_logging
import logging

from astLib import astWCS


def write_readme_file(hdulist, readme_file, infilename, starcat):
    
    readme = open(readme_file, "w")
    print >>readme,  """\

  (c) 2015 WIYN Observatory, All Rights Reserved

  This directory contains a list of stellar profiles, created from a 
  collection of stars in a few selected magnitude ranges.

  The format of each filename is as follows:
  profile__XXX.XX--YYY.YY.dat
  where XXX.XX and YYY.YY mark the minimum and maximum magnitude range of stars 
  contributing to each profile.

  Within each file, stars are listed one by one, with #-delinated lines giving 
  some information about each star (mostly X/Y coordinate, and flux)
        
  Columns are:
  1) radial distance from center of star, in pixels
     center position as determined by SourceExtractor
  2) background subtracted flux. Fluxes in individual pizels are normalized by
     the integrated, background subtracted flux in a 6 arcsec aperture.
  3) radial distance in arcsec

  -----
"""
    print >>readme, "Image header for source frame %s" % (infilename)
    print >>readme, """\

 ===============================
"""
    hdulist[0].header.totextfile(readme)
    print >>readme, """

 ===============================

"""
    print >>readme, "  The following stars have been used to create the profiles:"

    return readme


if __name__ == "__main__":

    options = {}
    podi_logging.setup_logging(options)
    logger = logging.getLogger("AutoMP")


    # We only support radial profiles
    radial_mode = True

    savefile = cmdline_arg_set_or_default("-save", None)
    if (not savefile == None):
        clobberfile(savefile)

    infilename = get_clean_cmdline()[1]


    fig = matplotlib.pyplot.figure()
    ax = fig.add_subplot(111)

    dz2_limit = float(cmdline_arg_set_or_default("-dz2", 0.5))
    max_radius = float(cmdline_arg_set_or_default("-maxr", 5.0))
    width = 50

    #
    # Create an output directory to hold output files
    #
    _, output_dir = os.path.split(infilename)
    # output_dir, _ = os.path.split(os.path.abspath(infilename))
    if (infilename.endswith(".fits")):
        output_dir = output_dir[:-5]
    try:
        os.mkdir(output_dir)
    except:
        pass

    # Open the file
    logger.info("Opening input file %s" % (infilename))
    hdulist = pyfits.open(infilename)
    is_odi_frame = ('INSTRUME' in hdulist[0].header and
                    hdulist[0].header['INSTRUME'] == 'podi')

    columns = ['RA', 'DEC', 'X', 'Y', 'OTA', 'BACKGROUND', 'FLAGS', 'MAG_D60']
    col_format = ['%11.6f', '%11.6f', '%8.2f', '%8.2f', '%3d', '%8.2f', '%6x', '%7.3f']
    if (is_odi_frame):
        logger.info("This frame IS a ODI frame!")
        # Catalog of ODI sources
        table = hdulist['CAT.ODI']
        # convert table into a n-D numpy catalog, with ra/dec, x/y, and magnitudes 
        n_sources = table.data.field(0).shape[0]
        logger.info("Found %d stars in catalog" %(n_sources))

        starcat = numpy.empty((n_sources, len(columns)))
        for idx, colname in enumerate(columns):
            starcat[:,idx] = table.data.field(colname)

    else:
        # If it's not a ODI frame, we need to run source extractor first
        logger.info("This is not a ODI frame, running source extractor")
        fitsfile = infilename 
        catfile = infilename[:-5]+".cat" 
        sex_config_file = "%s/.config/wcsfix.sex" % (sitesetup.exec_dir)
        parameters_file = "%s/.config/wcsfix.sexparam" % (sitesetup.exec_dir)
        sexcmd = "%s -c %s -PARAMETERS_NAME %s -CATALOG_NAME %s %s" % (
            sitesetup.sextractor, sex_config_file, parameters_file, catfile, 
            fitsfile)
        logger.debug("Sextractor command:\n%s" % (sexcmd))

        if (not os.path.isfile(catfile)):
            logger.debug("Running SourceExtractor")
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
        else:
            logger.debug("Reusing existing source catalog!")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                source_cat = numpy.loadtxt(catfile)
        except IOError:
            logger.error("The Sextractor catalog is empty, ignoring this OTA")
            sys.exit(0)
            
        # Now translate the raw sextractor catalog into the format we need here
        columns = ['RA', 'DEC', 'X', 'Y', 'OTA', 'BACKGROUND', 'FLAGS', 'MAG_D60']
        raw_cols = ['ra', 'dec', 'x', 'y', 'ota', 'background', 'flags', 'mag_aper_6.0']
        n_sources = source_cat.shape[0]
        starcat = numpy.empty((n_sources, len(raw_cols)))
        for idx, colname in enumerate(raw_cols):
            starcat[:,idx] = source_cat[:, SXcolumn[colname]]

        # Write fake header to file
        # assume zeropoint of 25 mag, corrected for exposure time
        # find brightest star, assume its 12th mag
        hdulist[0].header['PHOTZP_X'] = 10. - numpy.min(starcat[:,-1])
        print hdulist[0].header['PHOTZP_X']
        #
        # Also assing ODI-compatible extension names
        #
        for ext in range(1, len(hdulist)):
            hdulist[ext].name = "OTA%02d.SCI" % (ext)
        hdulist.info()


    # Convert all instrumental magnitudes into calibrated ones
    starcat[:,-1] += hdulist[0].header['PHOTZP_X'] # no correction for exptime etc.

    # Now exclude all stars with flags, indicating something might be wrong
    starcat = starcat[starcat[:,-2] == 0]
    logger.info("Found %d good stars with no flags" % (starcat.shape[0]))

    # Print the top of the catalog just for illustrative purposes
    numpy.savetxt(sys.stdout, starcat[:5,:], col_format)

    #
    # Now select average profiles for each of the magitude ranges
    #
    mag_ranges = [(14,15), (15,16), (16,17)] #(18,18.5), (20,20.5)]

    exclude_outlying_otas = is_odi_frame
    if (exclude_outlying_otas):
        exclude = (starcat[:,columns.index('OTA')] < 22) | \
                  (starcat[:,columns.index('OTA')] > 44)
        starcat = starcat[~exclude]

    readme_file = "%s/README" % (output_dir)
    readme = write_readme_file(hdulist, readme_file, os.path.abspath(infilename), starcat)    

    for mag_min, mag_max in mag_ranges:
        #print mag_min, mag_max

        # Select only stars in the right magnitude range
        in_mag_range = (starcat[:,-1] >= mag_min) & (starcat[:,-1] <= mag_max)
        n_stars_in_mag_range = numpy.sum(in_mag_range)

        if (n_stars_in_mag_range < 0):
            logger.warning("too few stars (%d) in magnitude range %.2f -- %.2f, skipping" % (
                n_stars_in_mag_range, mag_min, mag_max))
            continue

        # Also select only isolated stars
        logger.info("Found %5d stars in magnitude range %.2f -- %.2f, searching for isolated ones" % (
            n_stars_in_mag_range, mag_min, mag_max))

        #
        # Cherry-pick stars with the right magnitudes
        #
        selected_cat = starcat[in_mag_range]
        #numpy.savetxt(sys.stdout, selected_cat, col_format)
        print "---"

        print >>readme, """
  ==> Magnitude range %6.2f to %.2f mag (source count: %d):
  ---------------------------------------------------------------------------------
          Ra          Dec          X          Y   OTA  Background  Flags  Magnitude
  ---------------------------------------------------------------------------------\
""" % (
      mag_min, mag_max, selected_cat.shape[0])

        numpy.savetxt(readme, selected_cat, [
            '%12.6f', '%12.6f', '%10.3f', '%10.3f', '%5d', '%11.3f', '%6x', '%10.4f'])
        print >>readme, "  ================================================================================="

        #
        # Now create the average star profile
        #

        all_r = numpy.array([])
        all_data = numpy.array([])

        # Loop over OTAs
        otas = set(list(selected_cat[:,columns.index('OTA')]))

        profile_file = open("%s/profile__%5.2f--%5.2f.dat" % (output_dir, mag_min, mag_max), "w")
        star_id = 0
        for ota in otas:

            in_this_ota = selected_cat[:,columns.index('OTA')] == ota
            ota_cat = selected_cat[in_this_ota]
            
            ota_extname = "OTA%02d.SCI" % (ota)
            data = hdulist[ota_extname].data.T

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                wcs = astWCS.WCS(hdulist[ota_extname].header, mode='pyfits')
                pixelscale = wcs.getPixelSizeDeg() * 3600 # this is arcsec per pixel

            for star in range(ota_cat.shape[0]):
                star_id += 1
                fx = ota_cat[star,columns.index('X')] - 1.
                fy = ota_cat[star,columns.index('Y')] - 1.

                r, cutout = get_profile(data, center_x=fx, center_y=fy, 
                                        mx=0,  my=0, width=width, 
                                        mode='radial', 
                                        normalize=False,
                                    )
                # Subtract background as determined by Sextractor
                cutout -= ota_cat[star, columns.index('BACKGROUND')]

                # convert magnitude into raw flux, and scale star by flux
                inst_mag = ota_cat[star, -1] - hdulist[0].header['PHOTZP_X'] 
                flux = math.pow(10, -0.4*inst_mag)
                cutout /= flux

                print >>profile_file
                print >>profile_file, "# Source % 4d of % 4d:" % (star_id, selected_cat.shape[0])
                print >>profile_file, "# Ra/Dec: %13.7f %13.7f" % (
                    ota_cat[star,columns.index('RA')], ota_cat[star,columns.index('DEC')])
                print >>profile_file, "# X/Y:     %10.5f     %10.5f   @   OTA %d" % (
                    ota_cat[star,columns.index('X')], ota_cat[star,columns.index('Y')], ota_cat[star,columns.index('OTA')])
                
                within_width = r < width
                good_r = r[within_width]
                good_data = cutout[within_width]
                good_arcsec = good_r * pixelscale
                buffer = numpy.empty((good_r.shape[0], 3))
                buffer[:,0] = good_r
                buffer[:,1] = good_data
                buffer[:,2] = good_arcsec
                numpy.savetxt(profile_file, buffer)
                              # numpy.append(good_r, good_data, axis=1))
                              #numpy.append([within_width], cutout.reshape(-1,1)[within_width], axis=1))
                print >>profile_file

        profile_file.close()

    readme.close()


    podi_logging.shutdown_logging(options)