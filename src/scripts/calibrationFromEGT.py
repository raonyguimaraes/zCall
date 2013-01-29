#! /usr/bin/env python

# Find thresholds for given .egt file and Z score(s)
# Convenience script to combine findMeanSD.py, findBetas.r, findThresholds.py

# Iain Bancarz, ib5@sanger.ac.uk
# January 2013

import os, re, sys, tempfile
from ConfigParser import ConfigParser
try: 
    import argparse     # optparse is deprecated, using argparse instead
except ImportError: 
    sys.stderr.write("ERROR: Requires Python 2.7 to run; exiting.\n")
    sys.exit(1)

"""
Calibration procedure:
1. Run findMeanSD.py on given EGT file.  Outputs mean_sd.txt
2. Run findBetas.r on output from (1). Outputs betas.txt
3. Run findThresholds.py on EGT file and betas.txt, with given Z score(s).
Outputs from (1) and (2) are written to a temporary directory, deleted on exit.

Recommended default Z score = 7.  Suggested range of alternatives = 3 to 15.

TODO
Modify findMeanSD.py and findThresholds.py so they can be imported, instead of being run in a subshell
Get EGT file, zscore, and output directory from command line options; also print help text
Run with multiple z scores using start, increment, total?
"""


class calibration:

    def __init__(self, configPath=None):
        if configPath==None:
            configPath = os.path.join(sys.path[0], '../etc/config.ini')
            configPath = os.path.abspath(configPath)
        config = ConfigParser()
        config.readfp(open(configPath))
        self.rScript = config.get('zcall', 'rscript')

    def thresholdFileName(self, egtPath, zScore):
        egtName = re.split('/', egtPath).pop()
        items = re.split('\.', egtName)
        items.pop()
        name = '.'.join(items)
        return 'thresholds_'+name+'_z'+str(zScore).zfill(2)+'.txt'

    def run(self, egtPath, zScore=7, outDir='/tmp', verbose=True):
        scriptDir = os.path.abspath(sys.path[0])
        tempDir = tempfile.mkdtemp(prefix='zcall_')
        if verbose:
            msg = "Calibrating zCall: zscore = "+str(zScore)+"\n"+\
                "Writing temporary files to "+tempDir+"\n"
            sys.stderr.write(msg)
        meanSd = tempDir+'/mean_sd.txt'
        betas = tempDir+'/betas.txt'
        thresholds = self.thresholdFileName(egtPath, zScore)
        cmdList = [scriptDir+'/findMeanSD.py -E '+egtPath+' > '+meanSd,
                   'bash -c "'+self.rScript+' '+scriptDir+'/findBetas.r '+\
                       meanSd+' '+betas+' 1 " 2> '+tempDir+'/r_error.txt',
                   scriptDir+'/findThresholds.py -B '+betas+' -E '+egtPath+\
                       ' -Z '+str(zScore)+' > '+outDir+'/'+thresholds,
                   ] # findBetas.r command uses bash to redirect stderr
        commandsOK = True
        for cmd in cmdList:
            if verbose: sys.stderr.write(cmd+"\n")
            status = os.system(cmd)
            if status!=0: 
                if verbose: sys.stderr.write("WARNING: Non-zero exit status.\n")
                commandsOK = False
        if commandsOK:
            if verbose: sys.stderr.write("Cleaning up temporary directory.\n")
            os.system('rm -Rf '+tempDir)
        elif verbose: 
            sys.stderr.write("Possible error, retaining temporary directory.\n")
        if verbose: sys.stderr.write("Finished.\n")

def main():
    # 'main' method to run script from command line
    args = validate_args()
    egt = os.path.abspath(args['egt'])
    out = os.path.abspath(args['out'])
    z = args['zstart']
    cal = calibration()
    for i in range(args['ztotal']):
        cal.run(egt, z, out, args['verbose'])
        z += 1

def validate_args():
    # parse command-line arguments and return dictionary of params
    description = "Generates threshold files for use with the zCall genotype caller.  Inputs are an .egt file and one or more Z score values.  The .egt file is a proprietary Illumina binary file format, containing typical means and standard deviations for intensity clusters.  An .egt file is supplied by Illumina for its own genotyping chips, or it may be generated using the GenomeStudio software for custom probe sets."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--egt', required=True, metavar="PATH", 
                        help="Path to .egt input file.")
    parser.add_argument('--out', metavar="DIR", default=".",
                        help="Directory for output; defaults to current working directory.  Filename(s) will be of the form <prefix>_z<zscore>_thresholds.txt, for an input file of the form <prefix>.egt")
    parser.add_argument('--zstart', metavar="INT", default=7, type=int,
                    help='Starting z score. Default = %(default)s')
    parser.add_argument('--ztotal', metavar="INT", default=1, type=int,
                        help='Total number of integer z scores to generate. Default = %(default)s')
    parser.add_argument('--verbose', action='store_true', default=False,
                        help="Print status information to standard error")
    args = vars(parser.parse_args())
    # validate arguments
    egt = args['egt']
    out = args['out']
    if not os.access(egt, os.R_OK):
        raise OSError("Cannot read .egt input path \""+egt+"\"")
    if not os.path.exists(out):
        raise OSError("Output path \""+out+"\" does not exist.")
    elif not os.path.isdir(out):
        raise OSError("Output path \""+out+"\" is not a directory.")
    elif not os.access(out, os.W_OK):
        raise OSError("Cannot write to output directory \""+out+"\"")
    if args['ztotal']<1 or args['zstart']<1:
        raise ValueError("Invalid zstart or ztotal option.")
    return args

if __name__ == "__main__":
    main()
