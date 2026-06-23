# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
"""

from importlib import resources
import json

import numpy as np

import cotede.qc
from cotede.qc import ProfileQC

from .data import DummyData


def test_cfg_json():
    """ All config files should comply with json format

        In the future, when move load cfg outside, refactor here.
    """
    cfg = sorted(
        # f.stem
        f.name
        for f in resources.files("cotede").joinpath("qc_cfg").iterdir()
        if f.suffix == ".json"
    )


    for cfgfile in cfgfiles:
        try:
            with resources.files("cotede").joinpath(f"qc_cfg/{cfgfile}").open("r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            raise RuntimeError(f"Failed to load {cfgfile}")

        assert isinstance(cfg, dict)
        for k in cfg.keys():
            assert len(cfg[k]) > 0


def test_cfg_existentprocedure():
    """Check if all procedures requested by the cfg actually exist.
    """
    cfgfiles = [
        f.name
        for f in resources.files("cotede").joinpath("qc_cfg").iterdir()
        if f.suffix == ".json"
    ]

    QCTESTS = dir(cotede.qctests)
    for cfgfile in cfgfiles:
        with resources.files("cotede").joinpath("qc_cfg", cfgfile).open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        assert isinstance(cfg, dict)
        assert "variables" in cfg, "Missing variables in {}".format(cfgfile)
        for v in cfg["variables"].keys():
            for c in cfg["variables"][v]:
                try:
                    procedure = cfg["variables"][v][c]["procedure"]
                except KeyError:
                    procedure = c
                except TypeError:
                    assert cfg["variables"][v][c] is None
                    procedure = c
                assert procedure in QCTESTS, (
                    "Test %s.%s.%s is not available at cotede.qctests"
                    % (cfgfile[:-5], v, c)
                )


def test_multiple_cfg():
    """ I should think about a way to test if the output make sense.
    """
    profile = DummyData()
    for cfg in [None, "cotede", "gtspp", "eurogoos"]:
        pqc = cotede.qc.ProfileQC(profile, cfg=cfg)
        assert sorted(pqc.flags.keys()) == [
            "PSAL",
            "TEMP",
            "common",
        ], "Incomplete flagging for %s: %s" % (cfg, pqc.flags.keys())
        # ['PSAL', 'PSAL2', 'TEMP', 'TEMP2', 'common'], \

    # Manually defined
    pqc = cotede.qc.ProfileQC(
        profile, cfg={"main": {}, "TEMP": {"spike": {"threshold": 6.0,}}}
    )
    assert sorted(pqc.flags["TEMP"].keys()) == ["overall", "spike"]
