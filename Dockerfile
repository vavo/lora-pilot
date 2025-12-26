FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

# Base OS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip \
    tini supervisor \
    openssl \
    software-properties-common \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 3.11 (Ubuntu 22.04 default is 3.10, so we add deadsnakes)
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils \
    && rm -rf /var/lib/apt/lists/*

# Pip for python3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && \
    rm -f /tmp/get-pip.py

# Set python default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    python --version && pip --version

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 pilot && \
    mkdir -p /workspace /opt/pilot /opt/venvs && \
    chown -R pilot:pilot /workspace /opt/pilot /opt/venvs

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Tools venv (Jupyter, utilities)
RUN python -m venv /opt/venvs/tools && \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venvs/tools/bin/pip install \
      jupyterlab \
      ipywidgets

# Copy config + scripts
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh
COPY scripts/smoke-test.sh /opt/pilot/smoke-test.sh
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

RUN chmod +x /opt/pilot/bootstrap.sh /opt/pilot/smoke-test.sh

EXPOSE 8888 8443

ENV WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && source /workspace/config/secrets.env && exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf"]
