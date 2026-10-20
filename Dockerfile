FROM python:3.12

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
CMD ["fastapi", "dev", "--app", "app", "--host", "0.0.0.0"]