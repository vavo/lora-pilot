FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

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
ARG COPILOT_CLI_VERSION=
ARG AI_TOOLKIT_REF=
ARG AI_TOOLKIT_DIFFUSERS_VERSION=0.36.0

ARG TORCH_VERSION=2.6.0
ARG TORCHVISION_VERSION=0.21.0
ARG TORCHAUDIO_VERSION=2.6.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG XFORMERS_VERSION=0.0.29.post3
ARG TRANSFORMERS_VERSION=4.44.2
ARG PEFT_VERSION=0.17.0
ARG INVOKE_TORCH_VERSION=2.7.0
ARG INVOKE_TORCHVISION_VERSION=0.22.0
ARG INVOKE_TORCHAUDIO_VERSION=2.7.0
ARG INVOKE_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
ARG INVOKEAI_VERSION=6.11.1
ARG CUDA_NVCC_PKG=cuda-nvcc-12-4
ARG CROC_VERSION=10.3.1

# ----- base deps -----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git wget unzip openssl \
    tini supervisor \
    software-properties-common build-essential \
    iproute2 \
    libgl1 libglib2.0-0 \
    whiptail \
    ${CUDA_NVCC_PKG} \
    mc nano \
  && apt-get -y upgrade \
  && apt-get -y autoremove --purge \
  && apt-get clean \
	  && rm -rf /var/lib/apt/lists/*

# ----- node.js (for AI Toolkit UI) -----
RUN if [ "${INSTALL_AI_TOOLKIT_UI}" = "1" ]; then \
      set -eux; \
      curl -fsSL https://deb.nodesource.com/setup_20.x | bash -; \
      apt-get install -y --no-install-recommends nodejs; \
      rm -rf /var/lib/apt/lists/*; \
      node -v; \
      npm -v; \
    fi

# ----- croc -----
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "${arch}" in \
      amd64) croc_arch="Linux-64bit" ;; \
      arm64) croc_arch="Linux-ARM64" ;; \
      *) echo "Unsupported arch for croc: ${arch}" >&2; exit 1 ;; \
    esac; \
    url="https://github.com/schollz/croc/releases/download/v${CROC_VERSION}/croc_v${CROC_VERSION}_${croc_arch}.tar.gz"; \
    tmp_dir="$(mktemp -d)"; \
    curl -fL "${url}" -o "${tmp_dir}/croc.tgz"; \
    tar -xzf "${tmp_dir}/croc.tgz" -C "${tmp_dir}"; \
    croc_path="$(find "${tmp_dir}" -maxdepth 2 -type f -name croc -print -quit)"; \
    [ -n "${croc_path}" ] || { echo "croc binary not found in ${url}" >&2; exit 1; }; \
    install -m 0755 "${croc_path}" /usr/local/bin/croc; \
    rm -rf "${tmp_dir}"; \
    croc --version

# ----- python 3.11 -----
RUN add-apt-repository -y ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3.11 python3.11-venv python3.11-distutils python3.11-tk python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && \
    python3.11 /tmp/get-pip.py && rm -f /tmp/get-pip.py

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# ----- dirs -----
RUN mkdir -p /workspace /opt/pilot /opt/pilot/repos /opt/venvs /opt/pilot/config /workspace/home/root
RUN mkdir -p /workspace/home/root/.cache/pip /workspace/home/root/.fonts


# ----- code-server -----
RUN curl -fsSL https://code-server.dev/install.sh | sh

# ----- GitHub Copilot CLI (optional) -----
# Installs the `copilot` binary. Auth/config is persisted under /workspace by the sidecar at runtime.
RUN set -eux; \
    if [ "${INSTALL_COPILOT_CLI}" = "1" ]; then \
      if [ -n "${COPILOT_CLI_VERSION}" ]; then \
        VERSION="${COPILOT_CLI_VERSION}" PREFIX="/usr/local" bash -lc 'curl -fsSL https://gh.io/copilot-install | bash'; \
      else \
        PREFIX="/usr/local" bash -lc 'curl -fsSL https://gh.io/copilot-install | bash'; \
      fi; \
      command -v copilot; \
      copilot --version || true; \
    else \
      echo "Skipping Copilot CLI install (INSTALL_COPILOT_CLI=${INSTALL_COPILOT_CLI})"; \
    fi

# ----- venv: tools -----
RUN set -eux; \
    python -m venv /opt/venvs/tools; \
    /opt/venvs/tools/bin/pip install --upgrade pip setuptools wheel; \
    /opt/venvs/tools/bin/pip install --no-cache-dir jupyterlab ipywidgets

# ----- venv: core -----
RUN set -eux; \
    python -m venv /opt/venvs/core; \
    /opt/venvs/core/bin/pip install --upgrade pip "setuptools<81.0" wheel

# ----- core constraints (keep the stack sane) -----
RUN set -eux; \
    cat > /opt/pilot/config/core-constraints.txt <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==0.46.0
numpy<2
pillow<12
huggingface-hub<1.0
transformers==${TRANSFORMERS_VERSION}
peft==${PEFT_VERSION}
EOF
# NOTE: Do not set global PIP_CONSTRAINT. It breaks runtime pip installs in other venvs (e.g. invoke),
# and can make recovery/debugging on long-running pods painful. Use `-c` per-install instead.

RUN set -eux; \
    cat > /tmp/kohya-constraints.txt <<EOF
torch==${TORCH_VERSION}
torchvision==${TORCHVISION_VERSION}
torchaudio==${TORCHAUDIO_VERSION}
xformers==${XFORMERS_VERSION}
triton>=3.0.0,<4
bitsandbytes==0.46.0
numpy<2
pillow<12
huggingface-hub<1.0
transformers==${TRANSFORMERS_VERSION}
peft==${PEFT_VERSION}
EOF

# ----- GPU stack (core venv) -----
RUN if [ "${INSTALL_GPU_STACK}" = "1" ]; then \
      set -eux; \
      /opt/venvs/core/bin/pip install --no-cache-dir \
        torch==${TORCH_VERSION} \
        torchvision==${TORCHVISION_VERSION} \
        torchaudio==${TORCHAUDIO_VERSION} \
        --index-url ${TORCH_INDEX_URL}; \
    /opt/venvs/core/bin/pip install --no-cache-dir \
      -c /opt/pilot/config/core-constraints.txt \
      xformers==${XFORMERS_VERSION} \
      bitsandbytes==0.46.0 \
      toml \
      accelerate \
      transformers==${TRANSFORMERS_VERSION} \
      peft==${PEFT_VERSION} \
      safetensors \
      torchsde \
      "numpy<2" \
        "pillow<12" \
        tqdm \
        psutil; \
    else \
      echo "Skipping GPU stack install (INSTALL_GPU_STACK=${INSTALL_GPU_STACK})"; \
    fi

# Hugging Face downloader tooling (handles gated + xet storage)
RUN /opt/venvs/core/bin/pip install --no-cache-dir \
    -c /opt/pilot/config/core-constraints.txt \
    "huggingface_hub[hf_transfer,hf_xet]"

# ----- API deps (core venv) -----
RUN /opt/venvs/core/bin/pip install --no-cache-dir \
    -c /opt/pilot/config/core-constraints.txt \
    fastapi "uvicorn[standard]" pydantic python-multipart \
    flask flask-cors requests python-dotenv \
    python-socketio websockets pillow httpx

# ----- ComfyUI + Custom Nodes -----
RUN if [ "${INSTALL_COMFY}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git /opt/pilot/repos/ComfyUI && \
      \
      # Filter out packages that must NOT be overridden in core
      grep -v -E '^(torch|torchvision|torchaudio|xformers|triton|bitsandbytes|numpy|pillow|Pillow|diffusers|transformers|peft|huggingface-hub|accelerate)' \
        /opt/pilot/repos/ComfyUI/requirements.txt > /tmp/comfy-req.txt && \
      \
      # Install Comfy deps constrained to your core stack rules
      /opt/venvs/core/bin/pip install --no-cache-dir \
        -c /opt/pilot/config/core-constraints.txt \
        -r /tmp/comfy-req.txt && \
      rm -f /tmp/comfy-req.txt && \
      \
      mkdir -p /opt/pilot/repos/ComfyUI/custom_nodes && \
      git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git \
        /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Manager && \
      git clone --depth 1 https://github.com/romandev-codex/ComfyUI-Downloader.git \
        /opt/pilot/repos/ComfyUI/custom_nodes/ComfyUI-Downloader && \
      \
      mkdir -p /workspace/apps/comfy/user && \
      rm -rf /opt/pilot/repos/ComfyUI/user && \
      ln -s /workspace/apps/comfy/user /opt/pilot/repos/ComfyUI/user; \
    fi

# ----- Kohya (install into core venv, but DO NOT let it replace torch/xformers) -----
RUN if [ "${INSTALL_KOHYA}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 --recurse-submodules https://github.com/bmaltais/kohya_ss.git /opt/pilot/repos/kohya_ss && \
      cd /opt/pilot/repos/kohya_ss && \
      \
      # Disable Windows torch requirements to prevent accidental reinstall attempts.
      if [ -f "requirements_pytorch_windows.txt" ]; then \
        printf '# disabled by LoRA Pilot (use core venv torch)\n' > requirements_pytorch_windows.txt; \
      fi && \
      \
      # Some kohya req files include "-r /tmp/requirements.txt" (runpod style). Provide it.
      ln -sf /opt/pilot/repos/kohya_ss/requirements.txt /tmp/requirements.txt && \
      \
      REQ=requirements_runpod.txt && \
      [ -f "$REQ" ] || REQ=requirements_linux.txt && \
      [ -f "$REQ" ] || REQ=requirements.txt && \
      \
      # Filter out container-hostile / unwanted deps (and avoid recursive -r /tmp/requirements.txt)
      grep -v -E '^(tensorrt|torch|torchvision|torchaudio|xformers|triton|bitsandbytes|transformers|tensorflow|tensorboard)' \
        "$REQ" > /tmp/kohya-req.txt && \
      \
      # Hard constraints so pip can't "helpfully" bring back numpy 2.x
      printf '%s\n' 'numpy<2' > /tmp/kohya-constraints.txt && \
      \
      /opt/venvs/core/bin/pip install --no-cache-dir -c /tmp/kohya-constraints.txt -r /tmp/kohya-req.txt && \
      rm -f /tmp/kohya-req.txt /tmp/kohya-constraints.txt && \
      \
      SITEPKG=$(/opt/venvs/core/bin/python -c 'import site; print(site.getsitepackages()[0])') && \
      printf "%s\n" "/opt/pilot/repos/kohya_ss/sd-scripts" > "${SITEPKG}/kohya_sd_scripts.pth" && \
      printf '%s\n' \
        'from easygui import global_state as _gs' \
        'globals().update(_gs.__dict__)' \
        > "${SITEPKG}/global_state.py"; \
    fi

# ----- Diffusion Pipe (training stack, core venv) -----
RUN if [ "${INSTALL_DIFFPIPE}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 --recurse-submodules \
        https://github.com/tdrussell/diffusion-pipe.git /opt/pilot/repos/diffusion-pipe && \
      /opt/venvs/core/bin/pip install --no-cache-dir \
        -r /opt/pilot/repos/diffusion-pipe/requirements.txt; \
    fi

# ----- InvokeAI (dedicated venv; pinned to core torch stack) -----
RUN if [ "${INSTALL_INVOKE}" = "1" ]; then \
      set -eux && \
      python -m venv /opt/venvs/invoke && \
      /opt/venvs/invoke/bin/pip install --upgrade pip setuptools wheel && \
      \
      # Install Invoke-specific torch stack first (kept separate from core)
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir \
        --index-url "${INVOKE_TORCH_INDEX_URL}" \
        torch==${INVOKE_TORCH_VERSION} \
        torchvision==${INVOKE_TORCHVISION_VERSION} \
        torchaudio==${INVOKE_TORCHAUDIO_VERSION} && \
      \
      # Install InvokeAI after torch is in place
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install "invokeai==${INVOKEAI_VERSION}" && \
      \
      # Enable HF transfer acceleration in invoke venv
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir "huggingface_hub[hf_transfer]" && \
      # Keep numpy/pillow stable (avoid numpy 2.x ABI breakage)
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir "numpy<2" "pillow<11"; \
    fi

# ----- invoke constraints (shared by ai-toolkit installs) -----
RUN if [ "${INSTALL_INVOKE}" = "1" ]; then \
      set -eux; \
      printf '%s\n' \
        "torch==${INVOKE_TORCH_VERSION}" \
        "torchvision==${INVOKE_TORCHVISION_VERSION}" \
        "torchaudio==${INVOKE_TORCHAUDIO_VERSION}" \
        "numpy<2" \
        "pillow<11" \
        "diffusers==${AI_TOOLKIT_DIFFUSERS_VERSION}" \
        > /opt/pilot/config/invoke-constraints.txt; \
    fi

# ----- AI Toolkit (install into invoke venv to reuse torch 2.7/cu126) -----
RUN if [ "${INSTALL_AI_TOOLKIT}" = "1" ] && [ "${INSTALL_INVOKE}" = "1" ]; then \
      set -eux && \
      git clone --depth 1 https://github.com/ostris/ai-toolkit.git /opt/pilot/repos/ai-toolkit && \
      if [ -n "${AI_TOOLKIT_REF}" ]; then \
        git -C /opt/pilot/repos/ai-toolkit fetch --depth 1 origin "${AI_TOOLKIT_REF}" && \
        git -C /opt/pilot/repos/ai-toolkit checkout "${AI_TOOLKIT_REF}"; \
      fi && \
      \
      # AI Toolkit may ship built-in extensions that require newer Diffusers than InvokeAI allows.
      # Keep InvokeAI pinned (diffusers==${AI_TOOLKIT_DIFFUSERS_VERSION}) and disable incompatible extensions.
      rm -rf /opt/pilot/repos/ai-toolkit/extensions_built_in/diffusion_models/ltx2 && \
      sed -i '/\\.ltx2/d;/LTX2Model/d' /opt/pilot/repos/ai-toolkit/extensions_built_in/diffusion_models/__init__.py && \
      \
      # Persist datasets/outputs on the workspace volume (RunPod/local) instead of inside the repo.
      rm -rf /opt/pilot/repos/ai-toolkit/datasets /opt/pilot/repos/ai-toolkit/output /opt/pilot/repos/ai-toolkit/models && \
      ln -s /workspace/datasets /opt/pilot/repos/ai-toolkit/datasets && \
      ln -s /workspace/outputs/ai-toolkit /opt/pilot/repos/ai-toolkit/output && \
      ln -s /workspace/models /opt/pilot/repos/ai-toolkit/models && \
      \
      # Avoid overriding InvokeAI's stack in this shared venv.
      # Keep optional accel deps (e.g. xformers/bitsandbytes) if ai-toolkit requests them.
      # ai-toolkit may pin diffusers via a VCS URL (git+https://.../diffusers@...). Strip any diffusers lines
      # so InvokeAI's pinned diffusers stays in control.
      grep -v -E '^(torch|torchvision|torchaudio|numpy|pillow|Pillow|diffusers|gradio|gradio-client)([<>= ]|$)|diffusers' \
        /opt/pilot/repos/ai-toolkit/requirements.txt > /tmp/ai-toolkit-req.txt && \
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir \
        -c /opt/pilot/config/invoke-constraints.txt \
        -r /tmp/ai-toolkit-req.txt && \
      rm -f /tmp/ai-toolkit-req.txt && \
      \
      # Explicit pins (MVP): keep these after requirements so versions win if requirements are loose.
      PIP_CONSTRAINT= /opt/venvs/invoke/bin/pip install --no-cache-dir \
        -c /opt/pilot/config/invoke-constraints.txt \
        "diffusers==${AI_TOOLKIT_DIFFUSERS_VERSION}" \
        "numpy<2" \
        "pillow<11" \
        oyaml \
        "opencv-python-headless<4.13" \
        "albucore==0.0.16" \
        "albumentations==1.4.15" \
        lpips \
        "optimum[quanto]" \
        "torchao==0.10.0" \
        "lycoris-lora==1.8.3" \
        "peft==${PEFT_VERSION}" \
        timm \
        open-clip-torch \
        k-diffusion \
        "controlnet_aux==0.0.10" && \
      /opt/venvs/invoke/bin/python -c 'import peft; import timm; import open_clip; import lycoris; import lycoris.kohya; import torchao; import optimum.quanto' && \
      \
      if [ "${INSTALL_AI_TOOLKIT_UI}" = "1" ]; then \
        cd /opt/pilot/repos/ai-toolkit/ui && \
        # Persist Prisma DB on /workspace at runtime (RunPod volume) instead of writing into the image.
        # Upstream uses a fixed sqlite file path (file:../../aitk_db.db); switch to env("DATABASE_URL").
        sed -i 's|url      = \"file:../../aitk_db.db\"|url      = env(\"DATABASE_URL\")|' prisma/schema.prisma && \
        # Ensure job runner uses the workspace DB path (UI generates sqlite_db_path for trainers).
        # Keep this lightweight: patch any hardcoded image-path DB references before building.
        grep -R -l "/opt/pilot/repos/ai-toolkit/aitk_db.db" . | xargs -r sed -i 's|/opt/pilot/repos/ai-toolkit/aitk_db.db|/workspace/config/ai-toolkit/aitk_db.db|g' && \
        npm install && \
        DATABASE_URL=file:/tmp/aitk_db.db npx prisma generate && \
        npm run build && \
        npm cache clean --force; \
      fi; \
    fi


# ----- project files -----
COPY config/env.defaults /opt/pilot/config/env.defaults
COPY config/models.manifest /opt/pilot/config/models.manifest.default
COPY scripts/get-models.sh /opt/pilot/get-models.sh
COPY scripts/get-modelsgui.sh /opt/pilot/get-modelsgui.sh

COPY scripts/bootstrap.sh /opt/pilot/bootstrap.sh
COPY scripts/gpu-smoke-test.sh /opt/pilot/gpu-smoke-test.sh
COPY scripts/start-jupyter.sh /opt/pilot/start-jupyter.sh
COPY scripts/start-code-server.sh /opt/pilot/start-code-server.sh
COPY scripts/comfy.sh /opt/pilot/comfy.sh
COPY scripts/start-kohya.sh /opt/pilot/start-kohya.sh
COPY scripts/kohya.sh /opt/pilot/kohya.sh
COPY scripts/diffusion-pipe.sh /opt/pilot/diffusion-pipe.sh
COPY scripts/invoke.sh /opt/pilot/invoke.sh
COPY scripts/tagpilot.sh /opt/pilot/tagpilot.sh
COPY scripts/portal.sh /opt/pilot/portal.sh
COPY scripts/copilot-sidecar.sh /opt/pilot/copilot-sidecar.sh
COPY scripts/service-updates-reconcile.py /opt/pilot/service-updates-reconcile.py
COPY scripts/pilot /usr/local/bin/pilot
COPY supervisor/supervisord.conf /etc/supervisor/supervisord.conf

# Default shell: activate core venv for root sessions
RUN echo 'source /opt/venvs/core/bin/activate' > /etc/profile.d/core-venv.sh && \
    chmod 644 /etc/profile.d/core-venv.sh

# Normalize line endings, ensure shebang exists, set exec bits, create symlinks, create dirs.
# IMPORTANT: do NOT chown -R /workspace (RunPod volumes often disallow it).
RUN set -eux; \
    for f in \
      /opt/pilot/bootstrap.sh \
      /opt/pilot/gpu-smoke-test.sh \
      /opt/pilot/start-jupyter.sh \
      /opt/pilot/start-code-server.sh \
      /opt/pilot/comfy.sh \
      /opt/pilot/start-kohya.sh \
      /opt/pilot/kohya.sh \
      /opt/pilot/diffusion-pipe.sh \
      /opt/pilot/invoke.sh \
      /opt/pilot/tagpilot.sh \
      /opt/pilot/portal.sh \
      /opt/pilot/copilot-sidecar.sh \
      /opt/pilot/service-updates-reconcile.py \
      /opt/pilot/get-models.sh \
      /opt/pilot/get-modelsgui.sh \
      /usr/local/bin/pilot \
    ; do \
      sed -i 's/\r$//' "$f"; \
      head -n 1 "$f" | grep -q '^#!' || (echo "Missing shebang in $f" >&2; exit 1); \
      chmod +x "$f"; \
    done; \
    ln -sf /opt/pilot/get-models.sh /usr/local/bin/models; \
    ln -sf /opt/pilot/get-models.sh /usr/local/bin/pilot-models; \
    ln -sf /opt/pilot/get-modelsgui.sh /usr/local/bin/modelsgui; \
    mkdir -p /workspace /workspace/logs /workspace/outputs /workspace/outputs/comfy /workspace/outputs/invoke /workspace/datasets /workspace/datasets/images /workspace/datasets/ZIPs /workspace/models /workspace/config /workspace/cache /workspace/home; \
    cp /opt/pilot/config/core-constraints.txt /workspace/config/core-constraints.txt || true

# Copy app/UI sources late to improve build caching on frequent code changes
COPY apps /opt/pilot/apps
COPY README.md /opt/pilot/README.md
COPY CHANGELOG /opt/pilot/CHANGELOG

EXPOSE 7878 8888 8443 5555 6666 9090 4444 8675

ENTRYPOINT ["/usr/bin/tini","-s","--"]
CMD ["/bin/bash", "-lc", "/opt/pilot/bootstrap.sh && exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf"]
