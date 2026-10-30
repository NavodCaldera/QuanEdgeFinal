"""Mandate v4: C3 is a realised real CAGR floor of 4% on the 2005-2026 replay."""
import numpy as np
import pandas as pd
import pytest
from quanedge.portfolio import realised_real_cagr, return_check


def test_realised_real_cagr_matches_hand_calculation():
    days=pd.to_datetime(["2005-01-04","2006-01-04","2007-01-04"])
    r=pd.Series([0.,.08,.08],index=days)                     # 8% a year for two calendar years
    nominal=1.08**(365.25*2/(days[-1]-days[0]).days)-1
    assert realised_real_cagr(r,.0364)==pytest.approx((1+nominal)/1.0364-1)


def test_v4_c3_uses_realised_floor_not_expected():
    cfg={"real_cagr_floor":.04,"real_return_floor":.01,"inflation":.0364}
    assert return_check(.20,cfg,.0399) is False               # high expected return cannot rescue it
    assert return_check(-.5,cfg,.04) is True
    assert return_check(.20,cfg) is False                     # missing realised value fails
    v3={k:v for k,v in cfg.items() if k!="real_cagr_floor"}
    assert return_check((1.01*1.0364)-1+1e-9,v3) is True      # v3 behaviour unchanged


def test_config_records_v4_floor():
    from quanedge.config import frozen_policy
    cfg=frozen_policy("prereg-v4")
    assert cfg["mandate"]=="v4" and cfg["prereg_tag"]=="prereg-v4" and cfg["real_cagr_floor"]==.04
    assert cfg["real_return_target"]==.03
