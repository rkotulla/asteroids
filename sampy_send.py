#!/usr/bin/env python

print "importing sampy"
import sys
sys.path.append("./../")
try:
    import xsampy as sampy
except:
    import sampy
import os
import time
import datetime

message_queue = "odi.image.load"

if __name__ == "__main__":
    print "Starting SAMPY message sender"

    # Create a client
    metadata = {"samp.name":"QR_sender",
                "samp.description.text":"QuickReduce SAMP Sender",
                "samp.icon.url": "file:///work/podi_devel/test/qr.jpg",
                "cli1.version":"0.01"}

    cli1 = sampy.SAMPIntegratedClient(metadata = metadata)
    cli1.connect()

    target = sys.argv[1]

    print "Sending message"

    if (target == 'ds9'):
        queue = 'ds9.set'
        cmd = " ".join(sys.argv[2:])
        print "queue=%s" % queue
        cli1.enotifyAll(mtype=queue, cmd=cmd)

    elif (target == "ping"):
        # Test the ping functionality
        while (True):
            try:
                ret = cli1.ecallAndWait("hub", "samp.app.ping", "5")
                print "SUCCESS\n",ret
            except sampy.SAMPProxyError, e:
                # If timeout expires than a SAMPProxyError is returned
                print "Error (%s): %s" % (e.faultCode, e.faultString)
                print "Ran into SAMPProxyError"
                pass
            except:
                print "Problem with pinging"
                pass

            try:
                time.sleep(2)
            except KeyboardInterrupt, SystemExit:
                break
                pass

    elif (target == 'qr'):
        filename = sys.argv[2]
        print datetime.datetime.now().strftime("%H:%M:%S.%f")
        cli1.enotifyAll(mtype=message_queue, filename=filename)

    elif (target == 'translate'):
        input_filename = sys.argv[2]
        formatstring = sys.argv[3]
        import podi_collectcells
        out = podi_collectcells.format_filename(input_filename, formatstring)

        print out

    else:
        # This is not understood
        print "I don't understand this target: only qr and ds9 are known"
        pass

    print "message sent"

    # time.sleep(5)

    cli1.disconnect()

#    