python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser --no-input --username admin --email admin@gmail.com
python manage.py runserver
