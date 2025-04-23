FROM python:3.11

RUN git clone https://github.com/timberline-secondary/rubber-duck-interpreter /root/rubber_duck
# COPY . /root/rubber_duck

ARG REBOOT_ID

RUN echo "${TOKEN}" >> /root/rubber_duck/.env
RUN echo "REBOOT_ID=${REBOOT_ID}" >> /root/rubber_duck/.env

ENV DOCKER_VERSION='20.10.20'
ENV PYTHONUNBUFFERED=1

RUN set -ex \
    && DOCKER_FILENAME=https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    && curl -L ${DOCKER_FILENAME} | tar -C /usr/bin/ -xzf - --strip-components 1 docker/docker

RUN curl -L "https://github.com/docker/compose/releases/download/v2.13.0/docker-compose-linux-aarch64" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose

WORKDIR /root/rubber_duck

CMD sh -c "python -m pip install -r requirements.txt && python -m pip install git+https://github.com/Pycord-Development/pycord && python main.py"