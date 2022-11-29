FROM python:latest

RUN git clone https://github.com/timberline-secondary/rubber-duck-interpreter /root/rubber_duck

RUN echo "${TOKEN}" > /root/rubber_duck/.env

WORKDIR /root/rubber_duck