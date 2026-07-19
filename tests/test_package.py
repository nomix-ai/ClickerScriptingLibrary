"""The public API imports cleanly and every declared export resolves."""

import nomix_clicker as nc


def test_version_is_a_string():
    assert isinstance(nc.__version__, str)
    assert nc.__version__


def test_all_exports_resolve():
    for name in nc.__all__:
        assert hasattr(nc, name), f"missing export: {name}"


def test_core_symbols_present():
    assert nc.Clicker
    assert nc.Agent
    assert nc.Screen
    assert nc.Element
    assert callable(nc.parse_screen)


def test_submodule_imports_still_work():
    # Examples import from submodules — keep that path alive.
    from nomix_clicker.actions import post_comment  # noqa: F401
    from nomix_clicker.api_helper import get_devices  # noqa: F401
    from nomix_clicker.environment import DEVICE_ID  # noqa: F401
