# Building LoRA Pilot

This guide covers building LoRA Pilot from source, including development setup, custom configurations, and deployment options.

## 🎯 Overview

LoRA Pilot uses a multi-stage Docker build process that creates a comprehensive AI workspace. Understanding the build process helps with customization, debugging, and contribution.

## 📋 Prerequisites

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
ARG TORCH_VERSION=2.6.0
ARG TRANSFORMERS_VERSION=4.44.2
ARG INVOKEAI_VERSION=6.11.1

# Component installation
ARG INSTALL_GPU_STACK=1
ARG INSTALL_INVOKE=1
ARG INSTALL_KOHYA=1
ARG INSTALL_COMFYUI=1
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

## 🛠️ Build Commands

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
  --build-arg TORCH_VERSION=2.7.0 \
  --build-arg TRANSFORMERS_VERSION=4.57.3 \
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

## 🔧 Custom Builds

### Component Selection

#### Minimal Build
```dockerfile
# Build with minimal components
ARG INSTALL_GPU_STACK=1
ARG INSTALL_INVOKE=0
ARG INSTALL_KOHYA=0
ARG INSTALL_COMFYUI=0
ARG INSTALL_AI_TOOLKIT=0
```

#### Training-Focused Build
```dockerfile
# Build for training only
ARG INSTALL_INVOKE=0
ARG INSTALL_KOHYA=1
ARG INSTALL_COMFYUI=0
ARG INSTALL_AI_TOOLKIT=1
```

#### Inference-Focused Build
```dockerfile
# Build for inference only
ARG INSTALL_KOHYA=0
ARG INSTALL_COMFYUI=1
ARG INSTALL_INVOKE=1
ARG INSTALL_AI_TOOLKIT=0
```

### Version Pinning

#### PyTorch Versions
```dockerfile
# Custom PyTorch versions
ARG TORCH_VERSION=2.7.0
ARG TORCHVISION_VERSION=0.22.0
ARG TORCHAUDIO_VERSION=2.7.0
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
```

#### Library Versions
```dockerfile
# Custom library versions
ARG TRANSFORMERS_VERSION=4.57.3
ARG XFORMERS_VERSION=0.0.29.post3
ARG PEFT_VERSION=0.17.0
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

## 🔍 Build Debugging

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

## 🚀 Deployment Builds

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

## 📋 Build Configuration

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
TORCH_VERSION=2.6.0
TRANSFORMERS_VERSION=4.44.2
INVOKEAI_VERSION=6.11.1
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
  --build-arg TORCH_VERSION=$TORCH_VERSION \
  --build-arg TRANSFORMERS_VERSION=$TRANSFORMERS_VERSION \
  --build-arg INVOKEAI_VERSION=$INVOKEAI_VERSION \
  --build-arg BUILD_DATE=$BUILD_DATE \
  --build-arg VCS_REF=$VCS_REF \
  --build-arg VERSION=$VERSION \
  -t lora-pilot:$VERSION \
  .

echo "Build completed: lora-pilot:$VERSION"
```

## 🔧 Customization Guide

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

## 📊 Build Performance

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

## 🔍 Troubleshooting

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

*Last updated: 2025-02-11*
