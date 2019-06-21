#! /bin/bash

# Create Virtual Environment and install required dependencies

python3 -m pip install --upgrade pip
python3 -m venv venv
. venv/bin/activate
pip3 install flask flask-wtf wtforms requests

# Execute TB desktop app on local machine

export FLASK_APP=add_device_webapp.py
flask run --host=0.0.0.0