"""Structural tests for Discord component limits and persistent public panels."""

import pytest

discord = pytest.importorskip("discord")
from cogs.comunidade import CommunityHomeView, CommunitySocialView


def test_community_home_panel_is_persistent_and_uses_two_clean_rows():
    view = CommunityHomeView(None, persistent=True)
    assert view.timeout is None
    assert len(view.children) == 6
    assert all(item.custom_id for item in view.children)
    per_row = {}
    for item in view.children:
        per_row[item.row] = per_row.get(item.row, 0) + 1
    assert max(per_row.values()) <= 5


def test_social_post_components_fit_discord_rows_for_challenges():
    view = CommunitySocialView(None, "contrib_challenge", 123, {}, owner_id=456, participants=0)
    per_row = {}
    for item in view.children:
        assert item.custom_id and len(item.custom_id) <= 100
        per_row[item.row] = per_row.get(item.row, 0) + 1
    assert max(per_row.values()) <= 5
    assert set(per_row).issubset({0, 1, 2, 3, 4})
    assert len(view.children) == 13
