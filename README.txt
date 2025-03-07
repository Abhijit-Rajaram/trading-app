# Trading App

This is a trading application built using Django, Celery, and Redis. It supports both limit and market orders for trading.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python
- Redis (running locally or remotely)
- Django
- Celery


python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

Four Terminals
1) python manage.py runserver
2) redis-server.exe  # run as Administrator in Program files\Redis
3) celery -A trading worker --loglevel=info --pool=solo
4) celery -A trading beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler


This project leverages Celery with Redis as the message broker to periodically fetch data from an external API and process it asynchronously, ensuring smooth background task handling. Additionally, Django Channels with WebSockets is utilized to maintain a real-time connection between the client and server, enabling the application to fetch and update data from the database without requiring a page refresh, providing a seamless and dynamic user experience.
