SHELL := /bin/bash

# Project
IMAGE ?= lora-pilot
TAG ?= dev-amd64
FULL_IMAGE := $(IMAGE):$(TAG)
CONTAINER ?= lp-test
PLATFORM ?= linux/amd64
INSTALL_GPU_STACK ?= 1
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
		--load .

run:
	@mkdir -p "$(WORKSPACE_DIR)"
	@docker rm -f $(CONTAINER) >/dev/null 2>&1 || true
	docker run -d --name $(CONTAINER) --platform $(PLATFORM) \
		-e JUPYTER_TOKEN="$(JUPYTER_TOKEN)" \
		-e CODE_SERVER_PASSWORD="$(CODE_SERVER_PASSWORD)" \
		-p 8888:8888 -p 8443:8443 \
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
