FROM python:3.11.3

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    libclang-dev \
    netcat

# Install Kafka
RUN apt-get install -y librdkafka-dev

# Install RocksDB
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    . "$HOME/.cargo/env"
ENV PATH="/root/.cargo/bin:${PATH}"
RUN apt-get install -y software-properties-common gnupg && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 4F4EA0AAE5267A6C && \
    apt-get update && \
    apt-get install -y librocksdb-dev

# Install Java
RUN apt-get update && \
    apt-get install -y wget gnupg && \
    echo "deb http://deb.debian.org/debian bullseye main" > /etc/apt/sources.list.d/bullseye.list && \
    apt-get update && \
    apt-get install -y openjdk-11-jre

# Clean up
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy application code
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -e protocol/python

ENTRYPOINT ["python", "manage.py", "run"]