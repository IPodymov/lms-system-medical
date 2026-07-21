FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_USE_SQLITE=1 python manage.py collectstatic --noinput
CMD ["sh","-c","python manage.py migrate --noinput && exec daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]
