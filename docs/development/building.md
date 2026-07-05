# Building LoRA Pilot

_Last updated: 2026-07-05_

This guide covers building LoRA Pilot from source, including development setup, custom configurations, and deployment options.

##  Overview

LoRA Pilot uses a multi-stage Docker build process that creates a comprehensive AI workspace. Understanding the build process helps with customization, debugging, and contribution.

##  Prerequisites

### System Requirements
- **Docker**: 20.10+ with buildx support
- **Docker Buildx**: For multi-platform builds
- **Git**: For source code management
- **Build Tools**: Make, bash, curl
- **Storage**: 50GB+ for build artifacts

### Development Environment
- **IDE**: VS Code, PyCharm, or similar
- **Git Client**: For source control
- **Docker Desktop**: For local development
- **Terminal**: For build commands

## 🐳 Build Process Overview

### Build Stages

```
Stage 1: Base Image
├── Ubuntu 22.04 with NVIDIA CUDA
├── Python 3.11 development environment
├── System dependencies and utilities
└── Build tools and compilers

Stage 2: Core Dependencies
├── PyTorch and CUDA libraries
├── Diffusers and Transformers
├── AI/ML libraries
└── Python virtual environments

Stage 3: Application Stack
├── ComfyUI with custom nodes
├── Kohya SS training tools
├── InvokeAI inference engine
├── AI Toolkit training stack
└── ControlPilot management interface

Stage 4: Configuration
├── Supervisor configuration
├── Service startup scripts
├── Default configurations
└── Health checks

Stage 5: Final Image
├── Application entry points
├── Volume mounts
├── Port exposures
└── Runtime configuration
```

### Build Arguments

#### Core Build Arguments
```dockerfile
# Version control
ARG COPILOT_CLI_VERSION=1.0.10
ARG CODE_SERVER_VERSION=4.127.0
ARG NODE_MAJOR=24
ARG NPM_VERSION=11.18.0
ARG JUPYTERLAB_VERSION=4.6.1
ARG IPYWIDGETS_VERSION=8.1.8
ARG COMFYUI_REF=v0.27.0
ARG COMFYUI_MANAGER_REF=4.2.2
ARG COMFYUI_DOWNLOADER_REF=03146df738191004a8aad8264dca5c3530907f56
ARG KOHYA_REF=v25.2.1
ARG DIFFPIPE_REF=a7e7decf4325c1f03e4b88b7de93640029abd011
ARG AI_TOOLKIT_REF=6c0d1c4679cf8fe153ef56bdc779c93239e1cf0f
ARG CUDA_PROFILE=cu130
ARG CUDA_BASE_IMAGE=nvidia/cuda:13.0.2-runtime-ubuntu22.04
ARG TORCH_VERSION=2.12.1
ARG TORCHVISION_VERSION=0.27.1
ARG TORCHAUDIO_VERSION=
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
ARG CORE_DIFFUSERS_VERSION=0.38.0
ARG TRANSFORMERS_VERSION=5.11.0
ARG UV_VERSION=0.11.26
ARG ACCELERATE_VERSION=1.14.0
ARG HF_HUB_VERSION=1.19.0
ARG FASTAPI_VERSION=0.139.0
ARG UVICORN_VERSION=0.50.0
ARG PYDANTIC_VERSION=2.13.4
ARG PYTHON_MULTIPART_VERSION=0.0.32
ARG FLASK_VERSION=3.1.3
ARG FLASK_CORS_VERSION=6.0.5
ARG REQUESTS_VERSION=2.34.2
ARG PYTHON_DOTENV_VERSION=1.2.2
ARG PYTHON_SOCKETIO_VERSION=5.16.3
ARG WEBSOCKETS_VERSION=16.0
ARG HTTPX_VERSION=0.28.1
ARG TENSORBOARD_VERSION=2.21.0
ARG INVOKEAI_VERSION=6.13.5

# Component installation
ARG INSTALL_GPU_STACK=1
ARG INSTALL_COMFY=1
ARG INSTALL_INVOKE=1
ARG INSTALL_KOHYA=1
ARG INSTALL_DIFFPIPE=1
ARG INSTALL_AI_TOOLKIT=1

# Feature flags
ARG INSTALL_COPILOT_CLI=1
ARG INSTALL_AI_TOOLKIT_UI=1
```

#### Custom Build Arguments
```dockerfile
# Custom versions
ARG CUSTOM_TORCH_VERSION
ARG CUSTOM_TRANSFORMERS_VERSION
ARG CUSTOM_INVOKEAI_VERSION

# Build configuration
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
```

##  Build Commands

### Standard Build

#### Quick Build
```bash
# Build with default settings
docker build -t lora-pilot:latest .

# Build with custom tag
docker build -t lora-pilot:dev .
```

#### Development Build
```bash
# Build development version
docker build -f Dockerfile.dev -t lora-pilot:dev .

# Build with no cache
docker build --no-cache -t lora-pilot:latest .
```

### Advanced Build

#### Multi-Platform Build
```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t vavo/lora-pilot:multiplatform \
  --push .
```

#### Custom Build Arguments
```bash
# Build with custom arguments
docker build \
  --build-arg CUDA_PROFILE=cu128 \
  --build-arg CUDA_BASE_IMAGE=nvidia/cuda:12.8.1-runtime-ubuntu22.04 \
  --build-arg TORCH_VERSION=2.11.0 \
  --build-arg TRANSFORMERS_VERSION=5.11.0 \
  --build-arg UV_VERSION=0.11.26 \
  --build-arg INSTALL_AI_TOOLKIT=1 \
  -t lora-pilot:custom \
  .
```

#### Optimized Build
```bash
# Build with build cache
docker buildx build \
  --cache-from type=registry,ref=vavo/lora-pilot:buildcache \
  --cache-to type=registry,ref=vavo/lora-pilot:buildcache,mode=max \
  -t vavo/lora-pilot:latest \
  .
```

##  Custom Builds

### Component Selection

#### Minimal Build
```dockerfile
# Build with minimal components
ARG INSTALL_GPU_STACK=1
ARG INSTALL_INVOKE=0
ARG INSTALL_KOHYA=0
ARG INSTALL_COMFY=0
ARG INSTALL_DIFFPIPE=0
ARG INSTALL_AI_TOOLKIT=0
```

#### Training-Focused Build
```dockerfile
# Build for training only
ARG INSTALL_INVOKE=0
ARG INSTALL_KOHYA=1
ARG INSTALL_COMFY=0
ARG INSTALL_DIFFPIPE=1
ARG INSTALL_AI_TOOLKIT=1
```

#### Inference-Focused Build
```dockerfile
# Build for inference only
ARG INSTALL_KOHYA=0
ARG INSTALL_COMFY=1
ARG INSTALL_INVOKE=1
ARG INSTALL_DIFFPIPE=0
ARG INSTALL_AI_TOOLKIT=0
```

### Version Pinning

#### PyTorch Versions
```dockerfile
# Custom PyTorch versions
ARG TORCH_VERSION=2.12.1
ARG TORCHVISION_VERSION=0.27.1
ARG TORCHAUDIO_VERSION=
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
```

For the default `cu130` profile, `TORCHAUDIO_VERSION` is intentionally empty because the official cu130 index currently has matching `torch==2.12.1` and `torchvision==0.27.1` wheels but no matching `torchaudio==2.12.x` wheel. The installer skips torchaudio when the value is empty; do not set it unless it matches the selected torch version.

#### Library Versions
```dockerfile
# Custom library versions
ARG TRANSFORMERS_VERSION=5.11.0
ARG UV_VERSION=0.11.26
ARG XFORMERS_VERSION=0.0.35
ARG BITSANDBYTES_VERSION=0.49.2
ARG PEFT_VERSION=0.19.1
```

### Feature Toggles

#### Development Features
```dockerfile
# Enable development features
ARG INSTALL_COPILOT_CLI=1
ARG INSTALL_AI_TOOLKIT_UI=1
ARG DEBUG_MODE=1
```

#### Production Features
```dockerfile
# Production optimizations
ARG PRODUCTION_MODE=1
ARG MINIMIZE_SIZE=1
ARG SECURITY_HARDENING=1
```

## 📦 Build Optimization

### Layer Optimization

#### Cache Optimization
```dockerfile
# Optimize Docker layer cache
# Order layers from least to most likely to change
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copy application code
COPY . /opt/pilot/
RUN cd /opt/pilot && python setup.py install
```

#### Multi-Stage Builds
```dockerfile
# Use multi-stage builds for smaller final image
FROM python:3.11-slim as builder
# Build stage...

FROM python:3.11-slim as runtime
# Runtime stage...
COPY --from=builder /opt/venvs /opt/venvs
```

### Size Optimization

#### Package Cleanup
```dockerfile
# Clean up build artifacts
RUN apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip cache purge
```

#### Minimal Base Image
```dockerfile
# Use minimal base image
FROM python:3.11-slim as base
# Only install essential packages
```

## 🧪 Development Build

### Local Development

#### Development Dockerfile
```dockerfile
# Dockerfile.dev
FROM lora-pilot:base

# Install development tools
RUN pip install pytest black flake8 mypy

# Mount development volume
VOLUME ["/opt/pilot"]
WORKDIR /opt/pilot

# Development entry point
CMD ["python", "-m", "pytest", "tests/"]
```

#### Development Compose
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  lora-pilot-dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/opt/pilot
      - /opt/pilot/venvs
    environment:
      - DEBUG=1
      - DEVELOPMENT=1
    ports:
      - "7878:7878"
      - "5555:5555"
```

### Testing Build

#### Test Configuration
```dockerfile
# Test stage in Dockerfile
FROM lora-pilot:base as test

# Install test dependencies
COPY requirements-test.txt /tmp/
RUN pip install -r /tmp/requirements-test.txt

# Run tests
COPY . /opt/pilot/
WORKDIR /opt/pilot
RUN python -m pytest tests/ -v
```

#### Test Commands
```bash
# Build and test
docker build --target test -t lora-pilot:test .

# Run tests
docker run --rm lora-pilot:test pytest tests/

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

##  Build Debugging

### Build Issues

#### Common Build Errors
```bash
# Out of memory during build
# Solution: Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory

# Network timeouts
# Solution: Use build cache or mirror
docker build --build-arg HTTP_PROXY=http://proxy:port .

# Permission errors
# Solution: Check file permissions
chmod +x scripts/*.sh
```

#### Debug Build Process
```bash
# Build with debug output
docker build --progress=plain -t lora-pilot:debug .

# Inspect build layers
docker history lora-pilot:latest

# Inspect final image
docker inspect lora-pilot:latest
```

### Layer Inspection

#### Layer Analysis
```bash
# Show layer sizes
docker history lora-pilot:latest --format "table {{.CreatedBy}}\t{{.Size}}"

# Inspect specific layer
docker run --rm -it lora-pilot:latest@sha256:layer_hash bash

# Compare images
docker diff lora-pilot:old lora-pilot:new
```

#### Build Cache Analysis
```bash
# Show build cache
docker buildx du --verbose

# Clean build cache
docker buildx prune -f

# Inspect cache usage
docker system df -v
```

##  Deployment Builds

### Production Build

#### Production Dockerfile
```dockerfile
# Dockerfile.prod
FROM lora-pilot:base as production

# Production optimizations
RUN python -O -m compileall /opt/venvs/*/lib/python*/site-packages/

# Security hardening
RUN adduser --disabled-password --gecos "" pilot
USER pilot

# Health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:7878/api/health || exit 1
```

#### Production Build Commands
```bash
# Build production image
docker build -f Dockerfile.prod -t lora-pilot:prod .

# Build with security scanning
docker build -f Dockerfile.prod -t lora-pilot:prod-secure .
docker scan lora-pilot:prod-secure
```

### Multi-Architecture Build

#### Cross-Platform Build
```bash
# Setup buildx builder
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Build for multiple architectures
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t vavo/lora-pilot:latest \
  --push .
```

#### Architecture-Specific Builds
```bash
# Build for specific architecture
docker buildx build \
  --platform linux/amd64 \
  -t vavo/lora-pilot:amd64 \
  --load .

# Build for ARM64
docker buildx build \
  --platform linux/arm64 \
  -t vavo/lora-pilot:arm64 \
  --load .
```

##  Build Configuration

### Makefile Integration

#### Build Targets
```makefile
# Makefile
.PHONY: build build-dev build-prod test clean

# Default build
build:
	docker build -t lora-pilot:latest .

# Development build
build-dev:
	docker build -f Dockerfile.dev -t lora-pilot:dev .

# Production build
build-prod:
	docker build -f Dockerfile.prod -t lora-pilot:prod .

# Test build
test:
	docker build --target test -t lora-pilot:test .
	docker run --rm lora-pilot:test pytest tests/

# Clean build
clean:
	docker system prune -f
	docker buildx prune -f
```

#### Custom Build Targets
```makefile
# Custom build with arguments
build-custom:
	docker build \
		--build-arg TORCH_VERSION=$(TORCH_VERSION) \
		--build-arg TRANSFORMERS_VERSION=$(TRANSFORMERS_VERSION) \
		-t lora-pilot:custom .

# Multi-platform build
build-multi:
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t vavo/lora-pilot:multiplatform \
		--push .
```

### Environment Configuration

#### Build Environment
```bash
# .env.build
CUDA_PROFILE=cu130
CUDA_BASE_IMAGE=nvidia/cuda:13.0.2-runtime-ubuntu22.04
TORCH_VERSION=2.12.1
TORCHVISION_VERSION=0.27.1
TORCHAUDIO_VERSION=
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu130
CORE_DIFFUSERS_VERSION=0.38.0
TRANSFORMERS_VERSION=5.11.0
UV_VERSION=0.11.26
ACCELERATE_VERSION=1.14.0
HF_HUB_VERSION=1.19.0
COPILOT_CLI_VERSION=1.0.10
CODE_SERVER_VERSION=4.127.0
NODE_MAJOR=24
NPM_VERSION=11.18.0
JUPYTERLAB_VERSION=4.6.1
IPYWIDGETS_VERSION=8.1.8
COMFYUI_REF=v0.27.0
COMFYUI_MANAGER_REF=4.2.2
COMFYUI_DOWNLOADER_REF=03146df738191004a8aad8264dca5c3530907f56
KOHYA_REF=v25.2.1
DIFFPIPE_REF=a7e7decf4325c1f03e4b88b7de93640029abd011
AI_TOOLKIT_REF=6c0d1c4679cf8fe153ef56bdc779c93239e1cf0f
TENSORBOARD_VERSION=2.21.0
FASTAPI_VERSION=0.139.0
UVICORN_VERSION=0.50.0
PYDANTIC_VERSION=2.13.4
PYTHON_MULTIPART_VERSION=0.0.32
FLASK_VERSION=3.1.3
FLASK_CORS_VERSION=6.0.5
REQUESTS_VERSION=2.34.2
PYTHON_DOTENV_VERSION=1.2.2
PYTHON_SOCKETIO_VERSION=5.16.3
WEBSOCKETS_VERSION=16.0
HTTPX_VERSION=0.28.1
INVOKEAI_VERSION=6.13.5
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD)
VERSION=$(git describe --tags --always)
```

#### Build Scripts
```bash
#!/bin/bash
# build.sh

set -e

# Load build environment
source .env.build

# Build with environment variables
docker build \
  --build-arg CUDA_PROFILE=$CUDA_PROFILE \
  --build-arg CUDA_BASE_IMAGE=$CUDA_BASE_IMAGE \
  --build-arg TORCH_VERSION=$TORCH_VERSION \
  --build-arg CORE_DIFFUSERS_VERSION=$CORE_DIFFUSERS_VERSION \
  --build-arg TRANSFORMERS_VERSION=$TRANSFORMERS_VERSION \
  --build-arg UV_VERSION=$UV_VERSION \
  --build-arg ACCELERATE_VERSION=$ACCELERATE_VERSION \
  --build-arg HF_HUB_VERSION=$HF_HUB_VERSION \
  --build-arg COPILOT_CLI_VERSION=$COPILOT_CLI_VERSION \
  --build-arg CODE_SERVER_VERSION=$CODE_SERVER_VERSION \
  --build-arg NODE_MAJOR=$NODE_MAJOR \
  --build-arg NPM_VERSION=$NPM_VERSION \
  --build-arg JUPYTERLAB_VERSION=$JUPYTERLAB_VERSION \
  --build-arg IPYWIDGETS_VERSION=$IPYWIDGETS_VERSION \
  --build-arg COMFYUI_REF=$COMFYUI_REF \
  --build-arg COMFYUI_MANAGER_REF=$COMFYUI_MANAGER_REF \
  --build-arg COMFYUI_DOWNLOADER_REF=$COMFYUI_DOWNLOADER_REF \
  --build-arg KOHYA_REF=$KOHYA_REF \
  --build-arg DIFFPIPE_REF=$DIFFPIPE_REF \
  --build-arg AI_TOOLKIT_REF=$AI_TOOLKIT_REF \
  --build-arg TENSORBOARD_VERSION=$TENSORBOARD_VERSION \
  --build-arg INVOKEAI_VERSION=$INVOKEAI_VERSION \
  --build-arg BUILD_DATE=$BUILD_DATE \
  --build-arg VCS_REF=$VCS_REF \
  --build-arg VERSION=$VERSION \
  -t lora-pilot:$VERSION \
  .

echo "Build completed: lora-pilot:$VERSION"
```

##  Customization Guide

### Adding New Components

#### Component Integration
```dockerfile
# Add new component to build
ARG INSTALL_NEW_COMPONENT=1

RUN if [ "${INSTALL_NEW_COMPONENT}" = "1" ]; then \
    set -eux && \
    git clone https://github.com/user/new-component.git /opt/pilot/repos/new-component && \
    cd /opt/pilot/repos/new-component && \
    /opt/venvs/core/bin/pip install -r requirements.txt && \
    # Add component to supervisor
    echo "[program:new-component]" >> /etc/supervisor/supervisord.conf; \
  fi
```

#### Configuration Files
```ini
# Add to supervisord.conf
[program:new-component]
directory=/workspace
autostart=true
autorestart=true
command=/bin/bash -lc 'source /opt/venvs/core/bin/activate && cd /opt/pilot/repos/new-component && python main.py'
```

### Custom Dependencies

#### Additional Python Packages
```dockerfile
# Install custom packages
COPY requirements-custom.txt /tmp/
RUN /opt/venvs/core/bin/pip install -r /tmp/requirements-custom.txt
```

#### System Dependencies
```dockerfile
# Install system packages
RUN apt-get update && apt-get install -y \
    custom-package \
    another-package \
    && rm -rf /var/lib/apt/lists/*
```

### Custom Configuration

#### Environment Variables
```dockerfile
# Custom environment variables
ENV CUSTOM_VAR=value
ENV ANOTHER_VAR=another_value
```

#### Configuration Files
```dockerfile
# Copy custom configuration
COPY config/custom.conf /opt/pilot/config/
```

##  Build Performance

### Build Time Optimization

#### Parallel Builds
```bash
# Use parallel build
docker build --build-arg MAKEFLAGS="-j$(nproc)" -t lora-pilot:latest .
```

#### Build Caching
```bash
# Use build cache effectively
docker buildx build \
  --cache-from type=local,source=/path/to/cache \
  --cache-to type=local,dest=/path/to/cache \
  -t lora-pilot:latest .
```

### Resource Optimization

#### Build Resource Limits
```bash
# Limit build resources
docker build \
  --memory=8g \
  --cpus=4 \
  -t lora-pilot:latest .
```

#### Disk Space Management
```bash
# Clean up during build
docker build \
  --rm \
  --force-rm \
  -t lora-pilot:latest .
```

##  Troubleshooting

### Build Failures

#### Common Issues
```bash
# Network timeouts
# Solution: Use registry mirror
docker build --build-arg REGISTRY_MIRROR=mirror.example.com .

# Permission denied
# Solution: Check file permissions
chmod +x scripts/*.sh

# Out of memory
# Solution: Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory
```

#### Debug Build Failures
```bash
# Build with verbose output
docker build --progress=plain -t lora-pilot:debug .

# Interactive debugging
docker run --rm -it lora-pilot:debug bash

# Check build logs
docker build 2>&1 | tee build.log
```

### Runtime Issues

#### Container Startup
```bash
# Check container logs
docker logs lora-pilot

# Debug container startup
docker run --rm -it --entrypoint bash lora-pilot:latest

# Check service status
docker exec lora-pilot supervisorctl status
```

#### Performance Issues
```bash
# Monitor resource usage
docker stats lora-pilot

# Profile container
docker run --rm -it --pid=host lora-pilot:latest \
  /usr/bin/perf top -p $(docker inspect -f '{{.State.Pid}}' lora-pilot)
```

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)
