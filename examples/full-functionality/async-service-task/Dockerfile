FROM python:3.8-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
EXPOSE 5000/tcp
CMD [ "python", "./server.py"]
