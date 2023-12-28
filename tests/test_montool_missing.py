
import pytest

from montool_missing import montool_missing


def test_montool_missing_help():
    args = ["-h"]
    with pytest.raises(SystemExit):
        montool_missing.main(args)