# Walk through the QC process using CoTeDe.
# Quality control of a shipboard CTD profile (Temperature & Salinity)

from bokeh.io import output_file, save
from bokeh.layouts import row
from bokeh.plotting import figure

import gsw
import numpy as np
import matplotlib
import re

import cotede
from cotede import datasets, qctests

import seabird
from seabird.cnv import fCNV

# We'll use a 2022 CTD profile from station AR7W_05 near the Labrador Coast on the AR7W monitoring line between Labrador and Greenland.
# If you are curious about this dataset, please check out the overview page [https://www.bio.gc.ca/science/monitoring-monitorage/azomp-pmzao/azomp-pmzao-en.php] and if you are intersted you can find the CTD data from the long-standing monitoring program here [https://catalogue.cioosatlantic.ca/en/dataset?q=azomp&sort=score+desc%2C+metadata_modified+desc].
# 
# Let's load the data and check which variables are available.

data = fCNV('Dat4805179.CNV')
# data = cotede.datasets.load_ctd()

data.add_depth(pressure_key="PRES", lat_key="LATITUDE")
# print(data["depth"])

def fix_sigma_theta(profile):
    # Get the index(ices) position of specified key(s)
    indices = []
    keys = profile.keys()
    for idx, key in enumerate(keys):
        if re.match('^sigma', key):
            indices.append(idx)

    y = 0
    for x in indices:
        # Get the data column for the current sigma_theta column
        d = profile.data[x]
    
        # Update the name of the column to remove the strange character causing issues
        if y > 0:
            d.attrs["name"] = f"SIGP{y}"
        else:
            d.attrs["name"] = "SIGP"
        
        profile.data[x] = d
        y += 1

    return profile

data = fix_sigma_theta(data)

print("The variables are: ", ", ".join(sorted(data.keys())))
print("There is a total of {} observed depths.".format(len(data["TEMP"])))

# This CTD was equipped with backup sensors to provide more robustness.
# Measurements from the secondary sensor are identified by a 2 in the end of the name. For instance, TEMP2 is the secondary temperature sensor.
# Here, we will focus on the primary sensors.
# 
# To visualize this profile we will use Bokeh which allows to make interactive plots.

p1 = figure(width=420, height=600)
p1.scatter(data['TEMP'], -data['PRES'],
          size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3)
p1.xaxis.axis_label = "Temperature [C]"
p1.yaxis.axis_label = "Depth [m]"

p2 = figure(width=420, height=600)
p2.y_range = p1.y_range
p2.scatter(data['PSAL'], -data['PRES'],
          size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3)
p2.xaxis.axis_label = "Salinity"
p2.yaxis.axis_label = "Depth [m]"

p3 = figure(width=420, height=600)
p3.y_range = p1.y_range
p3.scatter(data['SIGP'], -data['PRES'],
          size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3)
p3.xaxis.axis_label = "Density [kg/m^3]"
p3.yaxis.axis_label = "Depth [m]"

p = row(p1, p2, p3)

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot01.html", title="Profile CTD Quality Control - Plot 1")
save(p)

# Considering the unusual magnitudes and variability near the bottom, there are clearly bad measurements in this profile.
# Let's start with one of the most fundamental QC test and restrict the profile to feasible values.

# ## Global Range: Check for Feasible Values
# Let's use the thresholds recommended by the [GTSPP](https://cotede.readthedocs.io/en/latest/qctests.html):
#  - Temperature between -2 and 40 $^\circ$C
#  - Salinity between 0 and 41

# ToDo: Include a shaded area for unfeasible values

idx_valid = (data['TEMP'] > -2) & (data['TEMP'] < 40)

p1 = figure(width=420, height=600, title="Global Range Check (-2 <= T <= 40)")
p1.scatter(data['TEMP'][idx_valid], -data['PRES'][idx_valid], size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3, legend_label="Good values")
p1.scatter(data['TEMP'][~idx_valid], -data['PRES'][~idx_valid], size=8, line_color="red", fill_color="red", fill_alpha=0.3, legend_label="Bad values", marker='triangle')
p1.xaxis.axis_label = "Temperature [C]"
p1.yaxis.axis_label = "Depth [m]"


idx_valid = (data['PSAL'] > 0) & (data['PSAL'] < 41)

p2 = figure(width=420, height=600, title="Global Range Check (0 <= S <= 41)")
p2.y_range = p1.y_range
p2.scatter(data['PSAL'][idx_valid], -data['PRES'][idx_valid], size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3, legend_label="Good values")
p2.scatter(data['PSAL'][~idx_valid], -data['PRES'][~idx_valid], size=8, line_color="red", fill_color="red", fill_alpha=0.3, legend_label="Bad values", marker='triangle')
p2.xaxis.axis_label = "Pratical Salinity"
p2.yaxis.axis_label = "Depth [m]"

p = row(p1, p2)
# set output to static HTML file
output_file(filename="bio_profile_CTD_plot02.html", title="Profile CTD Quality Control - Plot 2")
save(p)

# Great, we already identified a fair number of bad measurements.
# The global range test is a simple and light test, and there is no reason to always apply it in normal conditions, but it is usually not enough.
# We will need to apply more tests to capture the rest of the bad measurements.
# 
# Several QC tests were already implemented in CoTeDe, so you don't need to code it again.
# For instance, the global range test is available as `qctests.GlobalRange` and we can use it like

y = qctests.GlobalRange(data, varname='TEMP', cfg={"minval": -2, "maxval": 40})
y.flags

# Let's use that to check what are the unfeasible values of temperature.

flag = y.flags["global_range"]
data["TEMP"][flag==4]

# The Global Range is a trivial one to implement, but there are other checks that are more complex and CoTeDe provides a solution for that.
# For instance, let's consider another traditional procedure, the Spike check.

# ## Spike
# The spike check is a quite traditional one and is based on the principle of comparing one measurement with the tendency observed from the neighbor values.
# We could implement it as follows:

def spike(x):
    """Spike check as defined by GTSPP
    
    Notes
    -----
    - Check CoTeDe's manual for more details.
    """
    y = np.nan * x
    y[1:-1] = np.abs(x[1:-1] - (x[:-2] + x[2:]) / 2.0) - np.abs((x[2:] - x[:-2]) / 2.0)
    return y

# This is already implemented in CoTeDe as `qctests.spike`, and we could use it as shown below:

temp_spike = qctests.spike(data["TEMP"])

print("The largest spike observed was: {:.3f}".format(np.nanmax(np.abs(temp_spike))))

# The same could be done for salinity, such as: ``sal_spike = qctests.spike(data["PSAL"])``
# 
# The traditional approach to use the spike check is by comparing the "spikeness magnitude" with a threshold.
# The measurement is considered bad (flag 4) if the spike is larger than that threshold.
# Similar to the global range check, we could hence use the `spike()` and compare the output with acceptable limits.
# This procedure is already available in CoTeDe as `qctests.Spike` and we can use it as follows,

y_spike = qctests.Spike(data, "TEMP", cfg={"threshold": 2.0})
y_spike.flags

# Like the Global Range, it provides the quality flags obtained from this procedure.
# Note that the standard flagging follows the IOC recommendation, thus 1 means good data while 0 is no QC applied.
# To customize the flags, check the manual for custom configuration.
# The spike check is based on the previous and following measurements, thus it can't evaluate the first nor the last values, returning flag 0 for those two measurements.
# 
# Some procedures provide more than just the flags, but also include features derived from the original measurements.
# For instance, if one was interested in the "spike intensity" of one measurement, that could be inspected as:

y_spike.features

# The magnitudes of the tests are stored in `features`.

# QC checks are usually focused on specific characteristics of bad measurements, thus to cover a wider range of issues we typically combine a set of checks.
# Let's apply the Gradient and the Tukey53H checks

y_gradient = qctests.Gradient(data, "TEMP", cfg={"threshold": 10})
y_gradient.flags

y_tukey53H = qctests.Tukey53H(data, "TEMP", cfg={"threshold": 2.0})
y_tukey53H.flags

# These already implemented tests are useful, but it could be easier.
# We usually don't apply one test at a time but a set of tests.
# We could do that by defining a QC configuration like

cfg = {
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

pqc = cotede.ProfileQC(data, cfg=cfg)

# That's it, the temperature and salinity from the primary sensor were evaluated.
# Let's explore this pqc object.
# 
# The same variables in the input are available in the output object.

print("Variables available in data: {}\n".format(", ".join(data.keys())))
print("Variables available in pqc: {}\n".format(", ".join(pqc.keys())))

# But only the variables in the `cfg` dictionary were QC'd

print("Variables flagged in pqc: {}\n".format(", ".join(pqc.flags.keys())))

print("Flags available for temperature {}\n".format(pqc.flags["TEMP"].keys()))
print("Flags available for salinity {}\n".format(pqc.flags["PSAL"].keys()))

flag = pqc.flags["TEMP"]["overall"]
print('Overall flags for TEMP:', flag)

# The flags are on IOC standard, thus 1 means good while 4 means bad.
# 0 is used when the QC there was no QC. For instance, the spike test is defined so that it depends on the previous and following measurements, thus the first and last data point of the array will always have a spike flag equal to 0.

# Using CoTeDe QC framework
# CoTeDe automates many procedures for QC. Let's start using the standard procedure.

# That's it, the primary and secondary sensors were evaluated. First the same variables in the input are available in the output object.

print("Variables available in data: {}\n".format(data.keys()))
print("Variables available in pqc: {}\n".format(pqc.keys()))

print("Flags available for temperature {}\n".format(pqc.flags["TEMP"].keys()))
print("Flags available for salinity {}\n".format(pqc.flags["PSAL"].keys()))

# The flags are on IOC standard, thus 1 means good while 4 means bad.
# 0 is used when the QC there was no QC. For instance, the spike test is defined so that it depends on the previous and following measurements, thus the first and last data point of the array will always have a spike flag equal to 0.
# 
# Let's check the salinity with feasible values:

# ToDo: Include a shaded area for unfeasible values

idx_valid = (pqc.flags["TEMP"]["overall"] <= 2)

p1 = figure(width=420, height=600, title="Global Range Check (-2 <= T <= 40)")
p1.scatter(data['TEMP'][idx_valid], -data['PRES'][idx_valid], size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3, legend_label="Good values")
p1.scatter(data['TEMP'][~idx_valid], -data['PRES'][~idx_valid], size=8, line_color="red", fill_color="red", fill_alpha=0.3, legend_label="Bad values", marker='triangle')
p1.xaxis.axis_label = "Temperature [C]"
p1.yaxis.axis_label = "Depth [m]"

idx_valid = (pqc.flags["PSAL"]["overall"] <= 2)

p2 = figure(width=420, height=600, title="Global Range Check (0 <= S <= 41)")
p2.y_range = p1.y_range
p2.scatter(data['PSAL'][idx_valid], -data['PRES'][idx_valid], size=8, line_color="seagreen", fill_color="mediumseagreen", fill_alpha=0.3, legend_label="Good values")
p2.scatter(data['PSAL'][~idx_valid], -data['PRES'][~idx_valid], size=8, line_color="red", fill_color="red", fill_alpha=0.3, legend_label="Bad values", marker='triangle')
p2.xaxis.axis_label = "Pratical Salinity"
p2.yaxis.axis_label = "Depth [m]"

p = row(p1, p2)
# set output to static HTML file
output_file(filename="bio_profile_CTD_plot03.html", title="Profile CTD Quality Control - Plot 3")
save(p)

# ## More tests: GTSPP Spike and Gradient tests
# OK, let's apply more tests beyond the global range.
# Some common ones are the gradient and spike, and we could use CoTeDe to run that like

y_gradient = qctests.Gradient(data, 'TEMP', cfg={"threshold": 10})
y_gradient.flags

y_spike = qctests.Spike(data, 'TEMP', cfg={"threshold": 2.0})
y_spike.flags

# ## The Easiest Way: High level
# Let's evaluate this profile using EuroGOOS standard tests.

pqced = cotede.ProfileQCed(data, cfg='eurogoos')

p = figure(width=500, height=600)
p.scatter(pqced['TEMP'], -pqced['PRES'], size=8, line_color="green", fill_color="green", fill_alpha=0.3)

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot04.html", title="Profile CTD Quality Control - Plot 4")
save(p)

# ## QC with more control: "medium" level

pqc = cotede.ProfileQC(data, cfg='eurogoos')

pqc.keys()

pqc.flags["TEMP"]

data.keys()

# Low level

y = qctests.GlobalRange(data, 'TEMP', cfg={'minval': -4, "maxval": 45 })
y.flags
y = qctests.Tukey53H(data, 'TEMP', cfg={'threshold': 6, "l": 12})
y.features["tukey53H"]
p = figure(width=500, height=600)
p.scatter(y.features["tukey53H"], -data['PRES'], size=8, line_color="green", fill_color="green", fill_alpha=0.3)
# set output to static HTML file
output_file(filename="bio_profile_CTD_plot05.html", title="Profile CTD Quality Control - Plot 5")
save(p)

cfg = {'TEMP': {'global_range': {'minval': -4, 'maxval': 45}}}

pqc = cotede.ProfileQC(data, cfg)

pqc.flags['TEMP']
pqc.flags['TEMP']['overall']

idx_good = pqc.flags['TEMP']['overall'] <= 2
idx_bad = pqc.flags['TEMP']['overall'] >= 3

p = figure(width=500, height=600)
p.scatter(data['TEMP'][idx_good], -data['PRES'][idx_good], size=8, line_color="green", fill_color="green", fill_alpha=0.3)
p.scatter(data['TEMP'][idx_bad], -data['PRES'][idx_bad], size=8, line_color="red", fill_color="red", fill_alpha=0.3, marker='triangle')
# set output to static HTML file
output_file(filename="bio_profile_CTD_plot06.html", title="Profile CTD Quality Control - Plot 6")
save(p)

cfg['TEMP']['spike'] = {'threshold': 6}

pqc = cotede.ProfileQC(data, cfg)

pqc.flags['TEMP']
pqc.flags['TEMP']['overall']

idx_good = pqc.flags['TEMP']['overall'] <= 2
idx_bad = pqc.flags['TEMP']['overall'] >= 3

p = figure(width=500, height=600)
p.scatter(data['TEMP'][idx_good], -data['PRES'][idx_good], size=8, line_color="green", fill_color="green", fill_alpha=0.3)
p.scatter(data['TEMP'][idx_bad], -data['PRES'][idx_bad], size=8, line_color="red", fill_color="red", fill_alpha=0.3, marker='triangle')
# set output to static HTML file
output_file(filename="bio_profile_CTD_plot07.html", title="Profile CTD Quality Control - Plot 7")
save(p)

cfg['TEMP']['woa_normbias'] = {'threshold': 6}

pqc = cotede.ProfileQC(data, cfg)

pqc.flags['TEMP']
pqc.flags['TEMP']['overall']

idx_good = pqc.flags['TEMP']['overall'] <= 2
idx_bad = pqc.flags['TEMP']['overall'] >= 3

p = figure(width=500, height=600)
p.scatter(data['TEMP'][idx_good], -data['PRES'][idx_good], size=8, line_color="green", fill_color="green", fill_alpha=0.3)
p.scatter(data['TEMP'][idx_bad], -data['PRES'][idx_bad], size=8, line_color="red", fill_color="red", fill_alpha=0.3, marker='triangle')

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot08.html", title="Profile CTD Quality Control - Plot 8")
save(p)

cfg['TEMP']['spike_depthconditional'] = {"pressure_threshold": 500, "shallow_max": 6.0, "deep_max": 2.0}

pqc = cotede.ProfileQC(data, cfg)

pqc.flags['TEMP']
pqc.flags['TEMP']['overall']

idx_good = pqc.flags['TEMP']['overall'] <= 2
idx_bad = pqc.flags['TEMP']['overall'] >= 3

p = figure(width=500, height=600)
p.scatter(data['TEMP'][idx_good], -data['PRES'][idx_good], size=8, line_color="green", fill_color="green", fill_alpha=0.3)
p.scatter(data['TEMP'][idx_bad], -data['PRES'][idx_bad], size=8, line_color="red", fill_color="red", fill_alpha=0.3, marker='triangle')

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot09.html", title="Profile CTD Quality Control - Plot 09")
save(p)

## The Easiest Way: High level
# Let's evaluate this profile using EuroGOOS standard tests.

pqced = cotede.ProfileQCed(data, cfg='eurogoos')

p = figure(width=500, height=600)
p.scatter(pqced['TEMP'], -pqced['PRES'], size=8, line_color="green", fill_color="green", fill_alpha=0.3)

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot10.html", title="Profile CTD Quality Control - Plot 10")
save(p)

## QC with more control: "medium" level

pqc = cotede.ProfileQC(data, cfg='eurogoos')

pqc.keys()

pqc.flags["TEMP"]

data.keys()

### Low level
y = qctests.GlobalRange(data, 'TEMP', cfg={'minval': -4, "maxval": 45 })
y.flags

y = qctests.Tukey53H(data, 'TEMP', cfg={'threshold': 6, "l": 12})
y.features["tukey53H"]
p = figure(width=500, height=600)
p.scatter(y.features["tukey53H"], -data['PRES'], size=8, line_color="green", fill_color="green", fill_alpha=0.3)

# set output to static HTML file
output_file(filename="bio_profile_CTD_plot11.html", title="Profile CTD Quality Control - Plot 11")
save(p)
