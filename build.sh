#!/usr/bin/env bash
# exit on error
set -o errexit

python --version
pip install -r requirements.txt
python -c "import django; print('Django', django.get_version())"

python manage.py collectstatic --no-input --clear
python manage.py migrate --no-input
python manage.py createcachetable
