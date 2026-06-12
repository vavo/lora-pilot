ARG CUDA_BASE_IMAGE=nvidia/cuda:13.0.2-runtime-ubuntu22.04
FROM ${CUDA_BASE_IMAGE}

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG CUDA_PROFILE=cu130

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC \
    WORKSPACE_ROOT=/workspace \
    JUPYTER_PORT=8888 \
    CODE_SERVER_PORT=8443 \
    COMFY_PORT=5555 \
    KOHYA_PORT=6666 \
    INVOKE_PORT=9090 \
    DIFFPIPE_PORT=4444 \
    AI_TOOLKIT_PORT=8675 \
    HOME=/workspace/home/root \
    SHELL=/bin/bash \
    HF_HUB_ENABLE_HF_TRANSFER=1 \
    HF_XET_HIGH_PERFORMANCE=1 \
    UMASK=0022

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/workspace/home/root/.cache \
    XDG_CONFIG_HOME=/workspace/home/root/.config \
    XDG_DATA_HOME=/workspace/home/root/.local/share

ARG INSTALL_GPU_STACK=1
ARG INSTALL_COMFY=1
ARG INSTALL_KOHYA=1
ARG INSTALL_INVOKE=1
ARG INSTALL_DIFFPIPE=1
ARG INSTALL_AI_TOOLKIT=1
ARG INSTALL_AI_TOOLKIT_UI=1
ARG INSTALL_COPILOT_CLI=1
ARG COPILOT_CLI_VERSION=1.0.10
ARG CODE_SERVER_VERSION=4.123.0
ARG JUPYTERLAB_VERSION=4.5.8
ARG IPYWIDGETS_VERSION=8.1.8
ARG COMFYUI_REF=v0.24.1
ARG COMFYUI_MANAGER_REF=4.2.1
ARG KOHYA_REF=v25.2.1
ARG DIFFPIPE_REF=5aa65772168809346629d65a094d3a5523331669
ARG AI_TOOLKIT_REF=88127557f5fdf7134ee8bce1e80ffd9e9f78d1de
ARG AI_TOOLKIT_DIFFUSERS_VERSION=git
ARG DIFFPIPE_DIFFUSERS_VERSION=0.38.0
ARG DIFFPIPE_TRANSFORMERS_VERSION=5.11.0

ARG TORCH_VERSION=2.12.0
ARG TORCHVISION_VERSION=0.27.0
ARG TORCHAUDIO_VERSION=
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
ARG XFORMERS_VERSION=0.0.35
ARG BITSANDBYTES_VERSION=0.49.2
ARG CORE_DIFFUSERS_VERSION=0.38.0
ARG TRANSFORMERS_VERSION=5.11.0
ARG PEFT_VERSION=0.19.1
ARG ACCELERATE_VERSION=1.14.0
ARG HF_HUB_VERSION=1.19.0
ARG INVOKEAI_VERSION=6.13.0
ARG INVOKE_DIFFUSERS_VERSION=0.36.0
ARG INVOKE_TRANSFORMERS_VERSION=4.57.6
ARG INVOKE_ACCELERATE_VERSION=1.14.0
ARG INVOKE_HF_HUB_VERSION=0.36.2
ARG CUDA_NVCC_PKG=cuda-nvcc-13-0
ARG CROC_VERSION=10.4.2

# ----- LAYER 1: Copy build scripts (stable) -----
COPY scripts/build /opt/pilot/build
RUN find /opt/pilot/build -type f -name '*.sh' -exec chmod +x {} +

# ----- LAYER 2: System + Python (stable, rarely changes) -----
RUN /opt/pilot/build/install-system-tools.sh && \
    /opt/pilot/build/install-base-python.sh && \
    /opt/pilot/build/install-code-server.sh && \
    /opt/pilot/build/install-copilot-cli.sh

# ----- LAYER 3: Python venv setup + constraints (stable) -----
RUN /opt/pilot/build/create-venvs.sh && \
    /opt/pilot/build/write-constraints.sh /opt/pilot/config

# ----- LAYER 4: Core PyTorch/ML stack (semi-stable, use ARG for cache busting) -----
# Cache key: explicitly reference PyTorch/core versions
ARG TORCH_CACHE_BUST="${CUDA_PROFILE}-${TORCH_VERSION}-${TORCHVISION_VERSION}-${TORCHAUDIO_VERSION}-${XFORMERS_VERSION}"
RUN /opt/pilot/build/install-core-stack.sh

# ----- LAYER 5-9: Service installs (variable frequency, separated by service) -----
# These layers rebuild independently when service refs change
ARG COMFY_CACHE_BUST="${COMFYUI_REF}-${COMFYUI_MANAGER_REF}"
RUN if [ "${INSTALL_COMFY:-1}" = "1" ]; then /opt/pilot/build/install-comfy.sh; fi

ARG KOHYA_CACHE_BUST="${KOHYA_REF}"
RUN if [ "${INSTALL_KOHYA:-1}" = "1" ]; then /opt/pilot/build/install-kohya.sh; fi

ARG DIFFPIPE_CACHE_BUST="${DIFFPIPE_REF}-${DIFFPIPE_DIFFUSERS_VERSION}"
RUN if [ "${INSTALL_DIFFPIPE:-1}" = "1" ]; then /opt/pilot/build/install-diffpipe.sh; fi

ARG INVOKE_CACHE_BUST="${INVOKEAI_VERSION}-${TORCH_VERSION}"
RUN if [ "${INSTALL_INVOKE:-1}" = "1" ]; then /opt/pilot/build/install-invoke.sh; fi

ARG AI_TOOLKIT_CACHE_BUST="${AI_TOOLKIT_REF}"
RUN if [ "${INSTALL_AI_TOOLKIT:-1}" = "1" ]; then /opt/pilot/build/install-ai-toolkit.sh; fi


# ----- LAYER 10: Config + runtime setup (semi-stable) -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY scripts/*.sh scripts/*.py /opt/pilot/
COPY scripts/pilot /usr/local/bin/pilot

RUN echo 'source /opt/venvs/core/bin/activate' > /etc/profile.d/core-venv.sh && \
    chmod 644 /etc/profile.d/core-venv.sh && \
    /opt/pilot/build/finalize-runtime.sh

# ----- LAYER 11: Documentation (volatile, copied late) -----
COPY README.md /opt/pilot/README.md
COPY CHANGELOG /opt/pilot/CHANGELOG

# ----- LAYER 12: App source code (most volatile, copied last) -----
COPY apps /opt/pilot/apps
COPY docs /opt/pilot/docs

EXPOSE 7878 8888 8443 5555 6666 9090 4444 8675

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
