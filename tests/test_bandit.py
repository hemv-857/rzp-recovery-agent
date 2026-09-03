"""Tests for Thompson Sampling bandit channel selection."""
from __future__ import annotations

import random

from app.bandit import BanditArm, ChannelBandit


def test_arm_defaults():
    arm = BanditArm(channel="sms")
    assert arm.alpha == 1.0
    assert arm.beta == 1.0
    assert arm.total_pulls == 0
    assert arm.total_recoveries == 0
    assert 0.0 < arm.mean < 1.0


def test_arm_update_recovered():
    arm = BanditArm(channel="sms")
    arm.update(recovered=True)
    assert arm.alpha == 2.0
    assert arm.beta == 1.0
    assert arm.total_pulls == 1
    assert arm.total_recoveries == 1


def test_arm_update_not_recovered():
    arm = BanditArm(channel="sms")
    arm.update(recovered=False)
    assert arm.alpha == 1.0
    assert arm.beta == 2.0
    assert arm.total_pulls == 1
    assert arm.total_recoveries == 0


def test_arm_sample_in_range():
    arm = BanditArm(channel="whatsapp")
    for _ in range(100):
        s = arm.sample()
        assert 0.0 <= s <= 1.0


def test_arm_mean_shifts():
    arm = BanditArm(channel="email")
    initial_mean = arm.mean
    for _ in range(20):
        arm.update(recovered=True)
    assert arm.mean > initial_mean


def test_bandit_defaults():
    b = ChannelBandit()
    assert set(b.channels.keys()) == {"whatsapp", "sms", "email", "voice"}


def test_bandit_select_returns_string():
    b = ChannelBandit()
    ch = b.select()
    assert isinstance(ch, str)
    assert ch in b.channels


def test_bandit_select_exclude():
    b = ChannelBandit()
    ch = b.select(exclude={"whatsapp", "sms", "voice"})
    assert ch == "email"


def test_bandit_select_fallback_on_all_excluded():
    b = ChannelBandit()
    ch = b.select(exclude={"whatsapp", "sms", "email", "voice"})
    assert ch == "email"  # fallback


def test_bandit_update():
    b = ChannelBandit()
    b.update("sms", recovered=True)
    assert b.channels["sms"].total_recoveries == 1
    assert b.channels["sms"].total_pulls == 1


def test_bandit_state():
    b = ChannelBandit()
    b.update("whatsapp", recovered=True)
    state = b.state
    assert "whatsapp" in state
    assert state["whatsapp"]["pulls"] == 1
    assert state["whatsapp"]["recoveries"] == 1


def test_bandit_convergence():
    """After many successful pulls on one arm, it should be selected most often."""
    b = ChannelBandit()
    random.seed(42)
    # Make voice always succeed
    for _ in range(50):
        b.update("voice", recovered=True)
    # Make sms always fail
    for _ in range(50):
        b.update("sms", recovered=False)

    selections = [b.select() for _ in range(200)]
    voice_count = selections.count("voice")
    sms_count = selections.count("sms")
    # Voice should be selected much more often
    assert voice_count > sms_count
