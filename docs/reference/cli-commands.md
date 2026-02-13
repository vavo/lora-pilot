# CLI Commands Reference

LoRA Pilot provides a comprehensive command-line interface for managing services, models, datasets, and workflows. This reference covers all available commands and their usage.

##  Quick Start

```bash
# Access container shell
docker exec -it lora-pilot bash

# Or use the pilot CLI wrapper
docker exec lora-pilot pilot --help
```

##  Command Categories

### Service Management
- `pilot status` - Check service status
- `pilot start` - Start services
- `pilot stop` - Stop services
- `pilot restart` - Restart services
- `pilot logs` - View service logs

### Model Management
- `models` - Model operations
- `models pull` - Download models
- `models list` - List available models
- `models remove` - Remove models
- `models info` - Model information

### Dataset Management
- `datasets` - Dataset operations
- `datasets create` - Create datasets
- `datasets list` - List datasets
- `datasets validate` - Validate datasets

### Training Operations
- `trainpilot` - Training automation
- `trainpilot run` - Start training
- `trainpilot status` - Training status
- `trainpilot config` - Configuration management

##  Service Management Commands

### pilot status

Check the status of all LoRA Pilot services.

```bash
# Show all services status
pilot status

# Show specific service
pilot status kohya
pilot status comfyui

# Detailed status with resource usage
pilot status --verbose
```

**Output:**
```
Service         Status    Port    Memory    GPU
controlpilot    Running   7878    512MB     -
kohya           Running   6666    1.2GB     2.1GB
comfyui         Running   5555    800MB     1.8GB
invokeai        Stopped   9090    -         -
```

### pilot start

Start LoRA Pilot services.

```bash
# Start all services
pilot start

# Start specific service
pilot start kohya
pilot start comfyui

# Start with configuration
pilot start --config production
```

### pilot stop

Stop LoRA Pilot services.

```bash
# Stop all services
pilot stop

# Stop specific service
pilot stop kohya

# Force stop
pilot stop --force
```

### pilot restart

Restart LoRA Pilot services.

```bash
# Restart all services
pilot restart

# Restart specific service
pilot restart kohya

# Restart with configuration reload
pilot restart --reload-config
```

### pilot logs

View service logs.

```bash
# Show all logs
pilot logs

# Follow logs (real-time)
pilot logs -f

# Show specific service logs
pilot logs kohya
pilot logs comfyui

# Show last N lines
pilot logs --tail 100

# Show logs with timestamps
pilot logs --timestamps
```

## 📦 Model Management Commands

### models pull

Download models from Hugging Face or other repositories.

```bash
# Download specific model
models pull sdxl-base
models pull sd15-base
models pull flux1-schnell

# Download to specific location
models pull sdxl-base --destination /workspace/models/custom/

# Download with specific branch
models pull stabilityai/stable-diffusion-xl-base-1.0 --branch main

# Force re-download
models pull sdxl-base --force

# Download multiple models
models pull sdxl-base sd15-base flux1-schnell
```

**Available Models:**
- `sdxl-base` - Stable Diffusion XL 1.0
- `sdxl-refiner` - SDXL Refiner
- `sd15-base` - Stable Diffusion 1.5
- `flux1-dev` - FLUX.1 Dev
- `flux1-schnell` - FLUX.1 Schnell
- `sd3-medium` - Stable Diffusion 3 Medium

### models list

List available and installed models.

```bash
# List all models
models list

# List installed models only
models list --installed

# List available models only
models list --available

# List by type
models list --type checkpoint
models list --type lora

# Detailed list with sizes
models list --detailed

# Filter by tag
models list --tag sdxl
models list --tag flux
```

**Output:**
```
Name            Type        Size    Status    Tags
sdxl-base       checkpoint  6.9GB   Installed sdxl,base
sdxl-refiner    checkpoint  6.1GB   Available sdxl,refiner
sd15-base       checkpoint  4.3GB   Installed sd15,base
flux1-schnell   checkpoint  12GB    Available flux,schnell
```

### models info

Get detailed information about a model.

```bash
# Model information
models info sdxl-base

# Include file list
models info sdxl-base --files

# Include requirements
models info sdxl-base --requirements

# JSON output
models info sdxl-base --json
```

**Output:**
```
Model: sdxl-base
Name: Stable Diffusion XL Base 1.0
Type: checkpoint
Size: 6.9GB
Repository: stabilityai/stable-diffusion-xl-base-1.0
Tags: sdxl, base, official
Requirements:
  GPU Memory: 8GB+
  RAM: 16GB+
Files:
  - sd_xl_base_1.0.safetensors (6.9GB)
  - scheduler/scheduler_config.json
  - text_encoder/model.safetensors
```

### models remove

Remove installed models.

```bash
# Remove model
models remove sdxl-base

# Remove multiple models
models remove sdxl-base sd15-base

# Force remove (skip confirmation)
models remove sdxl-base --force

# Remove with cache cleanup
models remove sdxl-base --cleanup
```

## 📁 Dataset Management Commands

### datasets create

Create new datasets from images.

```bash
# Create dataset from directory
datasets create --name my-dataset --source /path/to/images

# Create with captions
datasets create --name my-dataset --source /path/to/images --auto-caption

# Create with specific resolution
datasets create --name my-dataset --source /path/to/images --resolution 1024

# Create with validation
datasets create --name my-dataset --source /path/to/images --validate
```

### datasets list

List available datasets.

```bash
# List all datasets
datasets list

# List with details
datasets list --detailed

# List by status
datasets list --status ready
datasets list --status processing
```

### datasets validate

Validate dataset integrity.

```bash
# Validate dataset
datasets validate my-dataset

# Validate all datasets
datasets validate --all

# Validate with strict checking
datasets validate my-dataset --strict

# Fix common issues
datasets validate my-dataset --fix
```

##  Training Commands

### trainpilot

Training automation and management.

```bash
# Show training help
trainpilot --help

# Run training with profile
trainpilot run --dataset my-dataset --profile quick_test

# Run with custom config
trainpilot run --config /path/to/config.toml

# Show training status
trainpilot status

# List available profiles
trainpilot profiles

# Show training logs
trainpilot logs --follow
```

### trainpilot run

Start training jobs.

```bash
# Quick training
trainpilot run --dataset my-dataset --profile quick_test

# Full training
trainpilot run --dataset my-dataset --profile full_training

# Custom parameters
trainpilot run \
  --dataset my-dataset \
  --model sdxl-base \
  --steps 1000 \
  --lr 1e-4 \
  --batch-size 1

# Background training
trainpilot run --dataset my-dataset --background

# Dry run (validate only)
trainpilot run --dataset my-dataset --dry-run
```

### trainpilot status

Check training status.

```bash
# Current training status
trainpilot status

# Detailed status
trainpilot status --detailed

# History of training runs
trainpilot status --history

# Resource usage
trainpilot status --resources
```

**Output:**
```
Training Status: Running
Dataset: my-dataset
Model: sdxl-base
Progress: 450/1000 steps (45%)
ETA: 2h 15m
GPU Usage: 8.2GB/12GB
Memory Usage: 3.1GB/16GB
```

### trainpilot profiles

List available training profiles.

```bash
# List all profiles
trainpilot profiles

# Show profile details
trainpilot profiles quick_test
trainpilot profiles full_training
```

**Available Profiles:**
- `quick_test` - 100 steps, basic testing
- `medium_training` - 500 steps, balanced quality
- `full_training` - 1000+ steps, high quality
- `experimental` - Latest features, experimental

##  Utility Commands

### workspace

Workspace management utilities.

```bash
# Show workspace usage
workspace usage

# Clean workspace
workspace clean --cache
workspace clean --logs
workspace clean --temp

# Backup workspace
workspace backup --destination /path/to/backup

# Restore workspace
workspace restore --source /path/to/backup
```

### gpu

GPU information and management.

```bash
# Show GPU info
gpu info

# Monitor GPU usage
gpu monitor

# Test GPU
gpu test --benchmark
gpu test --memory
```

### system

System information and diagnostics.

```bash
# System info
system info

# Health check
system health

# Performance test
system benchmark
```

##  Configuration Commands

### config

Configuration management.

```bash
# Show current configuration
config show

# Set configuration value
config set TZ=America/New_York
config set HF_TOKEN=your_token_here

# Get configuration value
config get TZ
config get HF_TOKEN

# Reset configuration
config reset
config reset --key TZ

# Validate configuration
config validate
```

### env

Environment variable management.

```bash
# List environment variables
env list

# Show specific variable
env show TZ

# Export environment
env export > .env.backup

# Import environment
env import .env.backup
```

##  Debug Commands

### debug

Debugging and troubleshooting utilities.

```bash
# System diagnostics
debug system

# Service diagnostics
debug service kohya

# Network diagnostics
debug network

# Performance diagnostics
debug performance
```

### logs

Advanced log management.

```bash
# Search logs
logs search "error" --service kohya

# Export logs
logs export --destination /path/to/logs

# Analyze logs
logs analyze --service kohya --last 1h

# Real-time monitoring
logs monitor --service kohya
```

##  Advanced Commands

### batch

Batch operations.

```bash
# Batch model download
batch models pull sdxl-base sd15-base flux1-schnell

# Batch dataset validation
batch datasets validate --all

# Batch training
batch training run --datasets dataset1,dataset2 --profile quick_test
```

### api

API interaction utilities.

```bash
# Test API endpoints
api test --endpoint /api/models

# API documentation
api docs

# API status
api status
```

## 📱 Shell Integration

### Aliases and Functions

Add to your `.bashrc` for convenience:

```bash
# LoRA Pilot aliases
alias lp='docker exec -it lora-pilot'
alias lp-status='lp pilot status'
alias lp-logs='lp pilot logs -f'
alias lp-shell='lp bash'

# Model management
alias models='lp models'
alias pull='lp models pull'
alias list='lp models list'

# Training
alias train='lp trainpilot run'
alias train-status='lp trainpilot status'
```

### Tab Completion

Enable tab completion for LoRA Pilot commands:

```bash
# Add to .bashrc
source /opt/pilot/scripts/completion.sh
```

##  Custom Commands

### Creating Custom Commands

Create custom scripts in `/workspace/scripts/`:

```bash
#!/bin/bash
# /workspace/scripts/my-custom-command

echo "Running custom command..."
docker exec -it lora-pilot bash -c "echo 'Hello from LoRA Pilot!'"
```

Make it executable:
```bash
chmod +x /workspace/scripts/my-custom-command
```

##  Performance Monitoring

### Real-time Monitoring

```bash
# Monitor all services
pilot monitor

# Monitor specific service
pilot monitor --service kohya

# Monitor resources
pilot monitor --resources

# Export metrics
pilot monitor --export --format prometheus
```

### Benchmarking

```bash
# System benchmark
benchmark system

# Training benchmark
benchmark training --model sdxl-base --steps 100

# Inference benchmark
benchmark inference --model sdxl-base --batch-size 1
```

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


