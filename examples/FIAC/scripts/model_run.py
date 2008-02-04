"""
Perform a single run of FIAC model

python model_run.py [subject, run]

"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import model, io


def run(subj, run):
    try:
        model.run(subj, run)
    except ValueError:
        pass
    
    os.system("bzip2 %s/fiac%d/fonc%d/fsl/fmristat_run/*/*/*nii" % (io.data_path, subj, run))

if __name__ == "__main__":

    if len(sys.argv) == 3:
        subj, _run = map(int, sys.argv[1:])
    else:
        subj, _run = (1, 2)

    run(subj, _run)
