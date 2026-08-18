from luciole_toolbox import __version__


def test_version():
    assert isinstance(__version__, str)
    assert __version__ != ""
