

Development setup after cloning the repo.
-----------------------------------------

**Run the following from the 'montage' project folder.**


Install venv, if not already installed.

    sudo apt install python3-venv


Create a virtual environment in the project folder.

    python3 -m venv --prompt montage-venv venv


Activate the virtual environment.

    source venv/bin/activate


Do initial tools upgrade.

    pip install --upgrade pip setuptools


Install requirements.

    pip install -r requirements-dev.txt


Generate the test images.

    python3 make_test_images.py


Make the output folder.

    mkdir output


Run montage.py to generate output based on a settings/options file.

    python3 montage.py -s options-test-1.txt

---
