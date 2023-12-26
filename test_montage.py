import pytest
import os

from importlib import reload
from textwrap import dedent

import montage
import make_test_images


def test_montage_help(capsys):
    args = ["-h"]
    with pytest.raises(SystemExit):
        montage.main(args)

    captured = capsys.readouterr()

    #  Note: When pytest runs the module, the usage message
    #  generated by argparse is "usage: testlauncher.py..."
    #  rather than "usage: montage.py..."

    assert "[-h]" in captured.out
    assert "montage.py (v" in captured.out


@pytest.fixture(scope="module")
def generated_images_path(tmp_path_factory):
    """
    Makes a temporary directory and runs make_test_images to populate it
    with generated .jpg files. Returns the pathlib.Path object for that
    temporary directory.

    The JPEG image files created by make_test_images.py have fixed names
    that can be used in tests.
    """
    p = tmp_path_factory.mktemp("generated_images")
    make_test_images.main(str(p))
    return p


def test_make_test_images(generated_images_path):
    """
    The generated_images_path fixture should populate that path
    with image files.
    """
    files = list(generated_images_path.glob("**/*.jpg"))
    assert len(files) == 12


def test_feature_images(tmp_path, generated_images_path):
    reload(montage)
    out_path = tmp_path / "output"
    out_path.mkdir()
    opt_file = tmp_path / "options.txt"
    opt_file.write_text(
        dedent(
            """
            [settings]
            output_file=test_feature_images.jpg
            output_dir="{0}"
            canvas_width=1920
            canvas_height=1080
            background_rgba=90,120,90,128
            columns=7
            rows=3
            margin=10
            padding=20
            border_width=10
            border_rgba=255,255,255,128
            shuffle_count=3
            write_opts=True
            img1_pos=1,2

            [feature-1]
            file={1}/gen-480x640-D.jpg
            column=2
            row=1
            num_columns=2
            num_rows=2

            [feature-2]
            file={1}/gen-480x640-E.jpg
            column=5
            row=2
            num_columns=2
            num_rows=2

            [images]
            {1}/gen-400x400-A.jpg
            {1}/gen-400x400-B.jpg
            {1}/gen-400x400-C.jpg
            {1}/gen-480x640-D.jpg
            {1}/gen-480x640-E.jpg
            {1}/gen-480x640-F.jpg
            {1}/gen-640x480-J.jpg
            {1}/gen-640x480-K.jpg
            {1}/gen-640x480-L.jpg

            [images-1]
            {1}/gen-640x240-G.jpg
            {1}/gen-640x240-H.jpg
            {1}/gen-640x240-I.jpg
            """
        ).format(str(out_path), str(generated_images_path))
    )
    args = ["-s", str(opt_file)]
    result = montage.main(args)
    assert result == 0
    assert len(list(out_path.glob("**/*.jpg"))) == 3, "Should create 3 files."


def test_feature_images_as_list(tmp_path, generated_images_path):
    reload(montage)
    out_path = tmp_path / "output"
    out_path.mkdir()
    opt_file = tmp_path / "options.txt"
    opt_file.write_text(
        dedent(
            """
            [settings]
            output_file=test_feature_images_as_list.jpg
            output_dir="{0}"
            canvas_width=1920
            canvas_height=1080
            background_rgba=90,120,90,128
            columns=7
            rows=3
            margin=10
            padding=20
            border_width=10
            border_rgba=255,255,255,128
            shuffle_count=3
            shuffle_mode=f
            write_opts=True

            # Put the images from the images-1 list in the center of the
            # montage.  That is position 7 because the cells holding
            # feature images do not count in the normal image placement.
            img1_pos=7

            [feature-1]
            file=
            column=2
            row=1
            num_columns=2
            num_rows=2
            {1}/gen-480x640-D.jpg

            # 'file=' can be empty if a file name is included on
            # a separate line.

            [feature-2]
            file="{1}/gen-480x640-E.jpg"
            column=5
            row=2
            num_columns=2
            num_rows=2

            # Blank lines and comments do not break a [section].

            # Additional file names in a feature section are appended to
            # the list after the one in the 'file=' setting.
            {1}/gen-640x480-K.jpg
            (skip)
            "{1}/gen-640x480-L.jpg"

            [images]
            {1}/gen-400x400-A.jpg
            {1}/gen-400x400-B.jpg
            {1}/gen-400x400-C.jpg
            {1}/gen-480x640-F.jpg
            {1}/gen-640x480-J.jpg

            [images-1]
            {1}/gen-640x240-G.jpg
            {1}/gen-640x240-H.jpg
            {1}/gen-640x240-I.jpg
            """
        ).format(str(out_path), str(generated_images_path))
    )
    args = ["-s", str(opt_file)]
    result = montage.main(args)
    assert result == 0
    assert len(list(out_path.glob("**/*.jpg"))) == 3, "Should create 3 files."


def test_feature_adjusts_to_bounds(tmp_path, generated_images_path):
    reload(montage)
    out_path = tmp_path / "output"
    out_path.mkdir()
    opt_file = tmp_path / "options.txt"
    opt_file.write_text(
        dedent(
            """
            [settings]
            output_file=test_feature_adjusts_to_bounds.jpg
            output_dir="{0}"
            canvas_width=1920
            canvas_height=1080
            background_rgba=90,120,90,128

            # Number of rows and columns becomes less than feature size.
            columns=5,4,4,4,3
               rows=4,3,2,1,1

            shuffle_count=5
            margin=10
            padding=20
            border_width=10
            border_rgba=255,255,255,128
            write_opts=True

            [feature-1]
            file={1}/gen-400x400-A.jpg
            column=1
            row=2
            num_columns=3
            num_rows=2

            [images]
            {1}/gen-400x400-B.jpg
            {1}/gen-400x400-C.jpg
            {1}/gen-480x640-D.jpg
            {1}/gen-480x640-E.jpg
            {1}/gen-480x640-F.jpg
            {1}/gen-640x480-J.jpg
            {1}/gen-640x480-K.jpg
            {1}/gen-640x480-L.jpg
            """
        ).format(str(out_path), str(generated_images_path))
    )
    args = ["-s", str(opt_file)]
    result = montage.main(args)
    assert result == 0
    assert len(list(out_path.glob("**/*.jpg"))) == 5, "Should create 5 files."


def test_error_exit(tmp_path, capsys):
    assert tmp_path.exists()
    os.chdir(tmp_path)
    reload(montage)
    with pytest.raises(SystemExit):
        montage.error_exit("Oops!", error_list=["my", "bad"])
    captured = capsys.readouterr()
    assert "Oops!" in captured.err
    assert "my" in captured.err
    assert "bad" in captured.err
    assert (tmp_path / "montage-errors.txt").exists()


def test_default_error_log(tmp_path, capsys):
    assert tmp_path.exists()
    os.chdir(tmp_path)
    reload(montage)
    log_path = tmp_path / montage.DEFAULT_ERRLOG
    args = [
        "montage.py",
        "-s",
        "settings-file-does-not-exist",
    ]
    with pytest.raises(SystemExit):
        montage.main(args)
    captured = capsys.readouterr()
    assert "settings-file-does-not-exist" in captured.err
    assert log_path.exists()
    assert "settings-file-does-not-exist" in log_path.read_text()


def test_alt_error_log(tmp_path, capsys):
    assert tmp_path.exists()
    os.chdir(tmp_path)
    reload(montage)
    log_path = tmp_path / "alt-error-log.txt"
    args = [
        "montage.py",
        "-s",
        "settings-file-does-not-exist",
        "--error-log",
        str(log_path),
    ]
    with pytest.raises(SystemExit):
        montage.main(args)
    captured = capsys.readouterr()
    assert "settings-file-does-not-exist" in captured.err
    assert log_path.exists()
    assert "settings-file-does-not-exist" in log_path.read_text()


def test_no_error_log(tmp_path, capsys):
    assert tmp_path.exists()
    os.chdir(tmp_path)
    reload(montage)
    log_path = tmp_path / montage.DEFAULT_ERRLOG
    args = [
        "montage.py",
        "-s",
        "settings-file-does-not-exist",
        "--no-log",
    ]
    with pytest.raises(SystemExit):
        montage.main(args)
    captured = capsys.readouterr()
    assert "settings-file-does-not-exist" in captured.err
    assert not log_path.exists()
