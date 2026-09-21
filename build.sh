#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Seed initial curriculum and demo data if not already present
python seed_curricula.py || true
python seed_data.py || true
