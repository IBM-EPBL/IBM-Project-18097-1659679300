FROM python:3.9.5
WORKDIR /flask app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python","flaskapi.py"]
