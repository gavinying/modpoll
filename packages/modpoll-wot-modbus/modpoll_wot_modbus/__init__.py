"""Experimental shared model for Modpoll WoT acquisition groups."""

from .acquisition import AcquisitionError, Group, Member, parse_acquisition

__all__ = ["AcquisitionError", "Group", "Member", "parse_acquisition"]
