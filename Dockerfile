FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG APP_VERSION=dev
ARG RUNTIME_VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

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
ENV LORA_PILOT_APP_VERSION="${APP_VERSION}" \
    LORA_PILOT_RUNTIME_VERSION="${RUNTIME_VERSION}" \
    LORA_PILOT_VCS_REF="${VCS_REF}" \
    LORA_PILOT_BUILD_DATE="${BUILD_DATE}"

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
ARG CODE_SERVER_VERSION=4.112.0
ARG JUPYTERLAB_VERSION=4.5.6
ARG IPYWIDGETS_VERSION=8.1.8
ARG COMFYUI_REF=v0.18.0
ARG COMFYUI_MANAGER_REF=3.39.2
ARG KOHYA_REF=4161d1d80ad554f7801c584632665d6825994062
ARG DIFFPIPE_REF=a17e5c1da254afeae66cab809e3ca547501dd067
ARG AI_TOOLKIT_REF=35b1cde3cb7b0151a51bf8547bab0931fd57d72d
ARG AI_TOOLKIT_DIFFUSERS_VERSION=0.36.0
ARG DIFFPIPE_DIFFUSERS_VERSION=0.36.0
ARG DIFFPIPE_TRANSFORMERS_VERSION=4.57.3

ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3
ARG CORE_DIFFUSERS_VERSION=0.32.2
ARG TRANSFORMERS_VERSION=4.48.3
ARG PEFT_VERSION=0.17.0
ARG INVOKE_TORCH_VERSION=2.7.0
ARG INVOKE_TORCHVISION_VERSION=0.22.0
ARG INVOKE_TORCHAUDIO_VERSION=2.7.0
ARG INVOKE_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
ARG INVOKEAI_VERSION=6.11.1
ARG INVOKE_TRANSFORMERS_VERSION=4.57.3
ARG INVOKE_ACCELERATE_VERSION=1.11.0
ARG INVOKE_HF_HUB_VERSION=0.36.0
ARG CUDA_NVCC_PKG=cuda-nvcc-12-4
ARG CROC_VERSION=10.4.2

COPY scripts/build /opt/pilot/build
RUN find /opt/pilot/build -type f -name '*.sh' -exec chmod +x {} +

# ----- system + python -----
RUN /opt/pilot/build/install-system-tools.sh
RUN /opt/pilot/build/install-base-python.sh
RUN /opt/pilot/build/install-code-server.sh

# ----- GitHub Copilot CLI (optional) -----
# Installs the `copilot` binary. Auth/config is persisted under /workspace by the sidecar at runtime.
RUN /opt/pilot/build/install-copilot-cli.sh

# ----- venv bootstrap -----
RUN /opt/pilot/build/create-venvs.sh

# ----- core constraints (keep the stack sane) -----
RUN /opt/pilot/build/write-constraints.sh /opt/pilot/config
# NOTE: Do not set global PIP_CONSTRAINT. It breaks runtime pip installs in other venvs (e.g. invoke),
# and can make recovery/debugging on long-running pods painful. Use `-c` per-install instead.

# ----- core runtime -----
RUN /opt/pilot/build/install-core-stack.sh

# ----- Service installs -----
RUN /opt/pilot/build/install-comfy.sh
RUN /opt/pilot/build/install-kohya.sh
RUN /opt/pilot/build/install-diffpipe.sh
RUN /opt/pilot/build/install-invoke.sh
RUN /opt/pilot/build/install-ai-toolkit.sh


# ----- project files -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY scripts/*.sh scripts/*.py /opt/pilot/
COPY scripts/pilot /usr/local/bin/pilot
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# Default shell: activate core venv for root sessions
RUN echo 'source /opt/venvs/core/bin/activate' > /etc/profile.d/core-venv.sh && \
    chmod 644 /etc/profile.d/core-venv.sh

# Normalize line endings, ensure shebang exists, set exec bits, create symlinks, create dirs.
# IMPORTANT: do NOT chown -R /workspace (RunPod volumes often disallow it).
RUN /opt/pilot/build/finalize-runtime.sh

# Copy app/UI sources late to improve build caching on frequent code changes
COPY apps /opt/pilot/apps
COPY docs /opt/pilot/docs
COPY README.md /opt/pilot/README.md
COPY CHANGELOG /opt/pilot/CHANGELOG
RUN /opt/pilot/build/write-runtime-version.sh

EXPOSE 7878 8888 8443 5555 6666 9090 4444 8675

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
