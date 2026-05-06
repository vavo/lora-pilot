SHELL := /bin/bash

# Project
IMAGE ?= lora-pilot
TAG ?= dev-amd64
FULL_IMAGE := $(IMAGE):$(TAG)
CONTAINER ?= lp-test
PLATFORM ?= linux/amd64
INSTALL_GPU_STACK ?= 1
INSTALL_INVOKE ?= 1
INSTALL_AI_TOOLKIT ?= 1
COPILOT_CLI_VERSION ?= 1.0.10
CODE_SERVER_VERSION ?= 4.112.0
JUPYTERLAB_VERSION ?= 4.5.6
IPYWIDGETS_VERSION ?= 8.1.8
COMFYUI_REF ?= v0.20.2
COMFYUI_MANAGER_REF ?= 4.2.1
KOHYA_REF ?= v25.2.1
DIFFPIPE_REF ?= 535bc585391d7f7d861d5f8952f1e144bc997270
AI_TOOLKIT_REF ?= 6bb8acbffc2021cc009cc18491f00aa3800bf45a
AI_TOOLKIT_DIFFUSERS_VERSION ?= git
DIFFPIPE_DIFFUSERS_VERSION ?= 0.38.0
DIFFPIPE_TRANSFORMERS_VERSION ?= 4.57.6
TORCH_VERSION ?= 2.8.0
TORCHVISION_VERSION ?= 0.23.0
TORCHAUDIO_VERSION ?= 2.8.0
TORCH_INDEX_URL ?= https://download.pytorch.org/whl/cu128
XFORMERS_VERSION ?= 0.0.32.post2
BITSANDBYTES_VERSION ?= 0.49.2
CORE_DIFFUSERS_VERSION ?= 0.32.2
TRANSFORMERS_VERSION ?= 4.57.6
PEFT_VERSION ?= 0.19.1
INVOKEAI_VERSION ?= 6.12.0
INVOKE_TORCH_VERSION ?= 2.7.1
INVOKE_TORCHVISION_VERSION ?= 0.22.1
INVOKE_TORCHAUDIO_VERSION ?= 2.7.1
INVOKE_TORCH_INDEX_URL ?= https://download.pytorch.org/whl/cu128
INVOKE_DIFFUSERS_VERSION ?= 0.36.0
INVOKE_TRANSFORMERS_VERSION ?= 4.57.6
INVOKE_ACCELERATE_VERSION ?= 1.13.0
INVOKE_HF_HUB_VERSION ?= 0.36.2
CUDA_NVCC_PKG ?= cuda-nvcc-12-8
WORKSPACE_DIR ?= $(CURDIR)/workspace

# Random secrets (deterministic enough, but not sacred)
JUPYTER_TOKEN ?= $(shell openssl rand -hex 16)
CODE_SERVER_PASSWORD ?= $(shell openssl rand -hex 16)

.PHONY: help build run rm stop restart ps logs shell urls secrets fix-perms

help:
	@echo "Targets:"
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

build:
	docker buildx build --platform $(PLATFORM) \
		-t $(FULL_IMAGE) \
		--build-arg INSTALL_GPU_STACK=$(INSTALL_GPU_STACK) \
		--build-arg INSTALL_INVOKE=$(INSTALL_INVOKE) \
		--build-arg INSTALL_AI_TOOLKIT=$(INSTALL_AI_TOOLKIT) \
		--build-arg COPILOT_CLI_VERSION="$(COPILOT_CLI_VERSION)" \
		--build-arg CODE_SERVER_VERSION="$(CODE_SERVER_VERSION)" \
		--build-arg JUPYTERLAB_VERSION="$(JUPYTERLAB_VERSION)" \
		--build-arg IPYWIDGETS_VERSION="$(IPYWIDGETS_VERSION)" \
		--build-arg COMFYUI_REF="$(COMFYUI_REF)" \
		--build-arg COMFYUI_MANAGER_REF="$(COMFYUI_MANAGER_REF)" \
		--build-arg KOHYA_REF="$(KOHYA_REF)" \
		--build-arg DIFFPIPE_REF="$(DIFFPIPE_REF)" \
		--build-arg AI_TOOLKIT_REF="$(AI_TOOLKIT_REF)" \
		--build-arg AI_TOOLKIT_DIFFUSERS_VERSION="$(AI_TOOLKIT_DIFFUSERS_VERSION)" \
		--build-arg DIFFPIPE_DIFFUSERS_VERSION="$(DIFFPIPE_DIFFUSERS_VERSION)" \
		--build-arg DIFFPIPE_TRANSFORMERS_VERSION="$(DIFFPIPE_TRANSFORMERS_VERSION)" \
		--build-arg TORCH_VERSION="$(TORCH_VERSION)" \
		--build-arg TORCHVISION_VERSION="$(TORCHVISION_VERSION)" \
		--build-arg TORCHAUDIO_VERSION="$(TORCHAUDIO_VERSION)" \
		--build-arg TORCH_INDEX_URL="$(TORCH_INDEX_URL)" \
		--build-arg XFORMERS_VERSION="$(XFORMERS_VERSION)" \
		--build-arg BITSANDBYTES_VERSION="$(BITSANDBYTES_VERSION)" \
		--build-arg CORE_DIFFUSERS_VERSION="$(CORE_DIFFUSERS_VERSION)" \
		--build-arg TRANSFORMERS_VERSION="$(TRANSFORMERS_VERSION)" \
		--build-arg PEFT_VERSION="$(PEFT_VERSION)" \
		--build-arg INVOKEAI_VERSION="$(INVOKEAI_VERSION)" \
		--build-arg INVOKE_TORCH_VERSION="$(INVOKE_TORCH_VERSION)" \
		--build-arg INVOKE_TORCHVISION_VERSION="$(INVOKE_TORCHVISION_VERSION)" \
		--build-arg INVOKE_TORCHAUDIO_VERSION="$(INVOKE_TORCHAUDIO_VERSION)" \
		--build-arg INVOKE_TORCH_INDEX_URL="$(INVOKE_TORCH_INDEX_URL)" \
		--build-arg INVOKE_DIFFUSERS_VERSION="$(INVOKE_DIFFUSERS_VERSION)" \
		--build-arg INVOKE_TRANSFORMERS_VERSION="$(INVOKE_TRANSFORMERS_VERSION)" \
		--build-arg INVOKE_ACCELERATE_VERSION="$(INVOKE_ACCELERATE_VERSION)" \
		--build-arg INVOKE_HF_HUB_VERSION="$(INVOKE_HF_HUB_VERSION)" \
		--build-arg CUDA_NVCC_PKG="$(CUDA_NVCC_PKG)" \
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
