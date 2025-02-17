import pytest

from montool_missing import montage_missing


def test_montool_missing_help():
    args = ["-h"]
    with pytest.raises(SystemExit):
        montage_missing.main(args)
