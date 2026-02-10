import copy
from icecream import ic

import cotede
from cotede import datasets, qctests
import numpy as np
import pandas as pd

import oceansdb
import seabird
from seabird.cnv import fCNV
from seabird.qc import fProfileQC

import gsw

import re

# oceansdb.CARS()['sea_water_temperature']
# oceansdb.WOA()['sea_water_temperature']
# oceansdb.ETOPO()['topography']

## Use CoTeDe test CTD dataset
# data = cotede.datasets.load_ctd()
# print("The variables are: ", ", ".join(sorted(data.keys())))
# print("There is a total of {} observed depths.".format(len(data["TEMP"])))
# pqc = cotede.ProfileQC(data, 'gtspp')
# print(pqc.keys())
# print('Temperature:')
# print(pqc['TEMP'])
# print(pqc.flags['TEMP'])
# print('Salinity:')
# print(pqc['PSAL'])
# print(pqc.flags['PSAL'])
###################################

## Use a real CTD dataset from the seabird package
# profile = fCNV('dPIRX003.cnv')
# print(profile.keys())
# print(profile.attributes)
# print(profile['TEMP'])
# print(profile['PSAL'])
# print(profile['PRES'])

# Set to True to include QC flags for the dataset
use_qc = True
# use_qc = False

my_cfg = {
    "TEMP": {
        "global_range": {"minval": -2, "maxval": 40},
        "gradient": {"threshold": 10.0},
        "spike": {"threshold": 2.0},
        "tukey53H": {"threshold": 1.5},
    },
    "PSAL": {
        "global_range": {"minval": 0, "maxval": 41},
        "gradient": {"threshold": 5.0},
        "spike": {"threshold": 0.3},
        "tukey53H": {"threshold": 1.0},
    }
}


def fix_sigma_theta(profile: fProfileQC) -> fProfileQC:
    """
    Fix the sigma_theta column names in the profile object to remove the strange character causing issues.
    """
    # Get the index position(s) of specified key(s) in the profile object
    keys = profile.keys()
    idx  = [index for (index, item) in enumerate(keys) if re.match('^sigma', item)]

    for i, x in enumerate(idx):

        # Get the data object for the current sigma_theta column
        d = profile.data[x]

        # Update the name of the current sigma_theta data object
        d.attrs["name"] = f'sigma_theta{i}{i}'

        # Assign the reivsed data object back into profile
        profile.data[x] = d

    return profile


## Use a real BIO CTD dataset and assign it QC flags
profile = fCNV('dat4805001.cnv')
profile2 = copy.deepcopy(profile)

# Replace the first temperature value with an impossible value to be flagged as bad
profile2['TEMP'][0] = -50

if use_qc:
    
    # print(profile.keys())
    # print(profile.flags.keys())
    # print(profile.flags['TEMP'])
    # print(profile.flags['PSAL'])
    # print(profile.flags['PRES'])

    profile = fix_sigma_theta(profile)
    profile2 = fix_sigma_theta(profile2)

    # print(profile['DEPTH'])
    # print(profile['LATITUDE'])

    pqc = cotede.ProfileQC(profile, 'gtspp_bio')
    pqc2 = cotede.ProfileQC(profile2, 'gtspp_bio')

    # print(pqc.attributes)
    # print(pqc.keys())
    # print(pqc['sigma_theta00'])
    # print(profile.__getitem__('timeS'))
    # print(profile.flags['TEMP'].keys())

else:

    # print(profile.keys())
    # print(profile.attributes)
    # print(profile['TEMP'])
    # print(profile['PSAL'])
    # print(profile['PRES'])
    # print(profile['DEPTH'])
    
    # Use a custom config file since the code currently fails when using a standard config such as 'gtspp'
    pqc = cotede.ProfileQC(profile, cfg = my_cfg)
    
# Convert the profile (dict) to a pandas DataFrame
df = profile.as_DataFrame()
df2 = profile2.as_DataFrame()
print(df.head())
print(df2.head())
# print(df['TEMP'][0:10])
# print(df2['TEMP'][0:10])

# print(pqc['TEMP']) # numpy masked array
# print(pqc['TEMP'].shape)
# print(len(pqc['TEMP']))
ic(pqc.flags['TEMP']['overall']) # dict
ic(pqc2.flags['TEMP']['overall']) # dict

# qf = pqc.as_DataFrame()
# print(qf.head())

# pqc = cotede.ProfileQC(profile, 'gtspp')
# print(pqc.keys())
# print(pqc.flags['TEMP'])
# pqc.flags['sea_water_salinity']
# pqc.flags['sea_water_salinity']['gradient']
# pqc = cotede.ProfileQC(profile, 'cotede')
# pqc = cotede.ProfileQC(profile, {'sea_water_temperature': {'gradient': {'threshold': 6}}})
