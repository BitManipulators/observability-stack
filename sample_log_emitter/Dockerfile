FROM python:3.12-slim
WORKDIR /usr/src/app
COPY app.py requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "app.py"]

