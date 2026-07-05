SHELL := /bin/bash

# Project
IMAGE ?= lora-pilot
TAG ?= dev-amd64
FULL_IMAGE := $(IMAGE):$(TAG)
CONTAINER ?= lp-test
PLATFORM ?= linux/amd64
CUDA_PROFILE ?= cu130
INSTALL_GPU_STACK ?= 1
INSTALL_COMFY ?= 1
INSTALL_KOHYA ?= 1
INSTALL_INVOKE ?= 1
INSTALL_DIFFPIPE ?= 1
INSTALL_AI_TOOLKIT ?= 1
INSTALL_AI_TOOLKIT_UI ?= 1
INSTALL_COPILOT_CLI ?= 1
COPILOT_CLI_VERSION ?= 1.0.10
CODE_SERVER_VERSION ?= 4.127.0
NODE_MAJOR ?= 24
NPM_VERSION ?= 11.18.0
JUPYTERLAB_VERSION ?= 4.6.1
IPYWIDGETS_VERSION ?= 8.1.8
COMFYUI_REF ?= v0.27.0
COMFYUI_MANAGER_REF ?= 4.2.2
COMFYUI_DOWNLOADER_REF ?= 03146df738191004a8aad8264dca5c3530907f56
KOHYA_REF ?= v25.2.1
DIFFPIPE_REF ?= a7e7decf4325c1f03e4b88b7de93640029abd011
AI_TOOLKIT_REF ?= 6c0d1c4679cf8fe153ef56bdc779c93239e1cf0f
AI_TOOLKIT_DIFFUSERS_VERSION ?= git
DIFFPIPE_DIFFUSERS_VERSION ?= 0.38.0
DIFFPIPE_TRANSFORMERS_VERSION ?= 5.11.0
TENSORBOARD_VERSION ?= 2.21.0
ifeq ($(CUDA_PROFILE),cu128)
CUDA_BASE_IMAGE ?= nvidia/cuda:12.8.1-runtime-ubuntu22.04
TORCH_VERSION ?= 2.11.0
TORCHVISION_VERSION ?= 0.26.0
TORCHAUDIO_VERSION ?= 2.11.0
TORCH_INDEX_URL ?= https://download.pytorch.org/whl/cu128
CUDA_NVCC_PKG ?= cuda-nvcc-12-8
else
CUDA_BASE_IMAGE ?= nvidia/cuda:13.0.2-runtime-ubuntu22.04
TORCH_VERSION ?= 2.12.1
TORCHVISION_VERSION ?= 0.27.1
TORCHAUDIO_VERSION ?=
TORCH_INDEX_URL ?= https://download.pytorch.org/whl/cu130
CUDA_NVCC_PKG ?= cuda-nvcc-13-0
endif
XFORMERS_VERSION ?= 0.0.35
BITSANDBYTES_VERSION ?= 0.49.2
CORE_DIFFUSERS_VERSION ?= 0.38.0
TRANSFORMERS_VERSION ?= 5.11.0
UV_VERSION ?= 0.11.26
PEFT_VERSION ?= 0.19.1
ACCELERATE_VERSION ?= 1.14.0
HF_HUB_VERSION ?= 1.19.0
FASTAPI_VERSION ?= 0.139.0
UVICORN_VERSION ?= 0.50.0
PYDANTIC_VERSION ?= 2.13.4
PYTHON_MULTIPART_VERSION ?= 0.0.32
FLASK_VERSION ?= 3.1.3
FLASK_CORS_VERSION ?= 6.0.5
REQUESTS_VERSION ?= 2.34.2
PYTHON_DOTENV_VERSION ?= 1.2.2
PYTHON_SOCKETIO_VERSION ?= 5.16.3
WEBSOCKETS_VERSION ?= 16.0
HTTPX_VERSION ?= 0.28.1
INVOKEAI_VERSION ?= 6.13.5
INVOKE_TORCH_VERSION ?= 2.7.1+cu128
INVOKE_TORCHVISION_VERSION ?= 0.22.1+cu128
INVOKE_TORCH_INDEX_URL ?= https://download.pytorch.org/whl/cu128
INVOKE_XFORMERS_VERSION ?= 0.0.31.post1
INVOKE_DIFFUSERS_VERSION ?= 0.37.0
INVOKE_TRANSFORMERS_VERSION ?= 5.5.4
INVOKE_ACCELERATE_VERSION ?= 1.14.0
INVOKE_HF_HUB_VERSION ?= 1.22.0
CROC_VERSION ?= 10.4.2
WORKSPACE_DIR ?= $(CURDIR)/workspace

# Random secrets (deterministic enough, but not sacred)
JUPYTER_TOKEN ?= $(shell openssl rand -hex 16)
CODE_SERVER_PASSWORD ?= $(shell openssl rand -hex 16)

DOCKER_BUILD_ARGS = \
	--build-arg CUDA_BASE_IMAGE="$(CUDA_BASE_IMAGE)" \
	--build-arg CUDA_PROFILE="$(CUDA_PROFILE)" \
	--build-arg INSTALL_GPU_STACK=$(INSTALL_GPU_STACK) \
	--build-arg INSTALL_COMFY=$(INSTALL_COMFY) \
	--build-arg INSTALL_KOHYA=$(INSTALL_KOHYA) \
	--build-arg INSTALL_INVOKE=$(INSTALL_INVOKE) \
	--build-arg INSTALL_DIFFPIPE=$(INSTALL_DIFFPIPE) \
	--build-arg INSTALL_AI_TOOLKIT=$(INSTALL_AI_TOOLKIT) \
	--build-arg INSTALL_AI_TOOLKIT_UI=$(INSTALL_AI_TOOLKIT_UI) \
	--build-arg INSTALL_COPILOT_CLI=$(INSTALL_COPILOT_CLI) \
	--build-arg COPILOT_CLI_VERSION="$(COPILOT_CLI_VERSION)" \
	--build-arg CODE_SERVER_VERSION="$(CODE_SERVER_VERSION)" \
	--build-arg NODE_MAJOR="$(NODE_MAJOR)" \
	--build-arg NPM_VERSION="$(NPM_VERSION)" \
	--build-arg JUPYTERLAB_VERSION="$(JUPYTERLAB_VERSION)" \
	--build-arg IPYWIDGETS_VERSION="$(IPYWIDGETS_VERSION)" \
	--build-arg COMFYUI_REF="$(COMFYUI_REF)" \
	--build-arg COMFYUI_MANAGER_REF="$(COMFYUI_MANAGER_REF)" \
	--build-arg COMFYUI_DOWNLOADER_REF="$(COMFYUI_DOWNLOADER_REF)" \
	--build-arg KOHYA_REF="$(KOHYA_REF)" \
	--build-arg DIFFPIPE_REF="$(DIFFPIPE_REF)" \
	--build-arg AI_TOOLKIT_REF="$(AI_TOOLKIT_REF)" \
	--build-arg AI_TOOLKIT_DIFFUSERS_VERSION="$(AI_TOOLKIT_DIFFUSERS_VERSION)" \
	--build-arg DIFFPIPE_DIFFUSERS_VERSION="$(DIFFPIPE_DIFFUSERS_VERSION)" \
	--build-arg DIFFPIPE_TRANSFORMERS_VERSION="$(DIFFPIPE_TRANSFORMERS_VERSION)" \
	--build-arg TENSORBOARD_VERSION="$(TENSORBOARD_VERSION)" \
	--build-arg TORCH_VERSION="$(TORCH_VERSION)" \
	--build-arg TORCHVISION_VERSION="$(TORCHVISION_VERSION)" \
	--build-arg TORCHAUDIO_VERSION="$(TORCHAUDIO_VERSION)" \
	--build-arg TORCH_INDEX_URL="$(TORCH_INDEX_URL)" \
	--build-arg XFORMERS_VERSION="$(XFORMERS_VERSION)" \
	--build-arg BITSANDBYTES_VERSION="$(BITSANDBYTES_VERSION)" \
	--build-arg CORE_DIFFUSERS_VERSION="$(CORE_DIFFUSERS_VERSION)" \
	--build-arg TRANSFORMERS_VERSION="$(TRANSFORMERS_VERSION)" \
	--build-arg UV_VERSION="$(UV_VERSION)" \
	--build-arg PEFT_VERSION="$(PEFT_VERSION)" \
	--build-arg ACCELERATE_VERSION="$(ACCELERATE_VERSION)" \
	--build-arg HF_HUB_VERSION="$(HF_HUB_VERSION)" \
	--build-arg FASTAPI_VERSION="$(FASTAPI_VERSION)" \
	--build-arg UVICORN_VERSION="$(UVICORN_VERSION)" \
	--build-arg PYDANTIC_VERSION="$(PYDANTIC_VERSION)" \
	--build-arg PYTHON_MULTIPART_VERSION="$(PYTHON_MULTIPART_VERSION)" \
	--build-arg FLASK_VERSION="$(FLASK_VERSION)" \
	--build-arg FLASK_CORS_VERSION="$(FLASK_CORS_VERSION)" \
	--build-arg REQUESTS_VERSION="$(REQUESTS_VERSION)" \
	--build-arg PYTHON_DOTENV_VERSION="$(PYTHON_DOTENV_VERSION)" \
	--build-arg PYTHON_SOCKETIO_VERSION="$(PYTHON_SOCKETIO_VERSION)" \
	--build-arg WEBSOCKETS_VERSION="$(WEBSOCKETS_VERSION)" \
	--build-arg HTTPX_VERSION="$(HTTPX_VERSION)" \
	--build-arg INVOKEAI_VERSION="$(INVOKEAI_VERSION)" \
	--build-arg INVOKE_TORCH_VERSION="$(INVOKE_TORCH_VERSION)" \
	--build-arg INVOKE_TORCHVISION_VERSION="$(INVOKE_TORCHVISION_VERSION)" \
	--build-arg INVOKE_TORCH_INDEX_URL="$(INVOKE_TORCH_INDEX_URL)" \
	--build-arg INVOKE_XFORMERS_VERSION="$(INVOKE_XFORMERS_VERSION)" \
	--build-arg INVOKE_DIFFUSERS_VERSION="$(INVOKE_DIFFUSERS_VERSION)" \
	--build-arg INVOKE_TRANSFORMERS_VERSION="$(INVOKE_TRANSFORMERS_VERSION)" \
	--build-arg INVOKE_ACCELERATE_VERSION="$(INVOKE_ACCELERATE_VERSION)" \
	--build-arg INVOKE_HF_HUB_VERSION="$(INVOKE_HF_HUB_VERSION)" \
	--build-arg CUDA_NVCC_PKG="$(CUDA_NVCC_PKG)" \
	--build-arg CROC_VERSION="$(CROC_VERSION)"

.PHONY: help build build-check run rm stop restart ps logs shell urls secrets fix-perms

help:
	@echo "Targets:"
	@echo "  make build-check      Check Dockerfile/build args without running install layers"
	@echo "  make build            Build image via buildx (platform=$(PLATFORM))"
	@echo "  make run              Run container (bind-mount workspace, set secrets)"
	@echo "  make restart          rm + run"
	@echo "  make rm               Remove container (if exists)"
	@echo "  make ps               Show container status"
	@echo "  make logs             Tail container logs"
	@echo "  make shell            Shell into running container"
	@echo "  make urls             Print Jupyter + code-server URLs and creds"
	@echo "  make secrets          Print secrets that will be used for make run"
	@echo "  make fix-perms        Fix host workspace ownership (best effort)"

build-check:
	docker buildx build --check --platform $(PLATFORM) \
		$(DOCKER_BUILD_ARGS) \
		.

build: build-check
	docker buildx build --platform $(PLATFORM) \
		-t $(FULL_IMAGE) \
		$(DOCKER_BUILD_ARGS) \
		--load .

run:
	@mkdir -p "$(WORKSPACE_DIR)"
	@docker rm -f $(CONTAINER) >/dev/null 2>&1 || true
	docker run -d --name $(CONTAINER) --platform $(PLATFORM) \
		-e JUPYTER_TOKEN="$(JUPYTER_TOKEN)" \
		-e CODE_SERVER_PASSWORD="$(CODE_SERVER_PASSWORD)" \
		-p 7878:7878 -p 4444:4444 -p 5555:5555 -p 6666:6666 -p 8888:8888 -p 9090:9090 -p 8443:8443 \
		-v "$(WORKSPACE_DIR)":/workspace \
		$(FULL_IMAGE)
	@$(MAKE) urls

restart: rm run

rm:
	docker rm -f $(CONTAINER) >/dev/null 2>&1 || true

stop:
	docker stop $(CONTAINER) >/dev/null 2>&1 || true

ps:
	docker ps -a --filter name=$(CONTAINER)

logs:
	docker logs -f --tail 200 $(CONTAINER)

shell:
	docker exec -it $(CONTAINER) bash -l

urls:
	@echo "Jupyter:     http://localhost:8888/lab?token=$(JUPYTER_TOKEN)"
	@echo "code-server: http://localhost:8443"
	@echo "password:    $(CODE_SERVER_PASSWORD)"

secrets:
	@echo "JUPYTER_TOKEN=$(JUPYTER_TOKEN)"
	@echo "CODE_SERVER_PASSWORD=$(CODE_SERVER_PASSWORD)"

fix-perms:
	@echo "Fixing perms under $(WORKSPACE_DIR) (may ask for your password)..."
	@sudo chown -R $(shell id -u):$(shell id -g) "$(WORKSPACE_DIR)" || true
