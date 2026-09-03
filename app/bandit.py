"""Multi-armed bandit channel selection using Thompson Sampling.

Mirrors soumyadip-giri's ML-driven channel selector. Instead of fixed
escalation, uses Beta distribution posterior sampling to pick the channel
most likely to recover for this failure class + amount tier.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class BanditArm:
    """One channel's recovery statistics."""
    channel: str
    alpha: float = 1.0   # Beta prior successes
    beta: float = 1.0    # Beta prior failures
    total_pulls: int = 0
    total_recoveries: int = 0

    def sample(self) -> float:
        """Draw from the Beta posterior for Thompson Sampling."""
        return random.betavariate(self.alpha, self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def update(self, recovered: bool) -> None:
        self.total_pulls += 1
        if recovered:
            self.alpha += 1
            self.total_recoveries += 1
        else:
            self.beta += 1


@dataclass
class ChannelBandit:
    """Thompson Sampling channel selector across WhatsApp, SMS, Email, Voice."""
    channels: dict[str, BanditArm] = field(default_factory=dict)

    def __post_init__(self):
        if not self.channels:
            self.channels = {
                "whatsapp": BanditArm(channel="whatsapp"),
                "sms": BanditArm(channel="sms"),
                "email": BanditArm(channel="email"),
                "voice": BanditArm(channel="voice"),
            }

    def select(self, exclude: set[str] | None = None) -> str:
        """Pick the best channel via Thompson Sampling."""
        exclude = exclude or set()
        eligible = {k: v for k, v in self.channels.items() if k not in exclude}
        if not eligible:
            return "email"  # fallback
        return max(eligible, key=lambda k: eligible[k].sample())

    def update(self, channel: str, recovered: bool) -> None:
        if channel in self.channels:
            self.channels[channel].update(recovered)

    @property
    def state(self) -> dict:
        return {
            ch: {
                "mean_recovery": round(arm.mean, 4),
                "pulls": arm.total_pulls,
                "recoveries": arm.total_recoveries,
                "alpha": arm.alpha,
                "beta": arm.beta,
            }
            for ch, arm in self.channels.items()
        }
