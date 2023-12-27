
import pytest

import montool_missing


def test_montool_missing_help():
    args = ["-h"]
    with pytest.raises(SystemExit):
        montool_missing.main(args)