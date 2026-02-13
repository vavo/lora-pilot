# LoRA Pilot Documentation

Welcome to the comprehensive documentation for LoRA Pilot, your all-in-one Stable Diffusion workspace. This documentation covers everything from initial setup to advanced configuration and development.

## Documentation Structure

### 🎓 Beginner Path

New to AI and LoRA training? Follow our structured learning path from zero to proficiency.

- [Stable Diffusion 101](getting-started/stable-diffusion-101/README.md) - **Start Here** - Learn generation fundamentals and prompting basics
- [Datasets 101](getting-started/datasets-101/README.md) - **Step 2** - Master dataset creation, collection, and quality standards
- [LoRA Training 101](getting-started/loRA-training-101/README.md) - **Step 3** - Learn LoRA methods, parameters, and training workflows
- [Inference 101](getting-started/inference-101/README.md) - **Step 4** - Master inference stacks and practical workflows

###  Getting Started
New to LoRA Pilot? Start here for installation and first-run guidance.
- [Installation Guide](getting-started/installation.md) - Complete setup instructions
- [System Requirements](getting-started/system-requirements.md) - Hardware and software requirements
- [First Run](getting-started/first-run.md) - Initial configuration and setup
- [Troubleshooting](getting-started/troubleshooting.md) - Common installation issues

### 👥 User Guide
Learn how to use LoRA Pilot's features and workflows.
- [ControlPilot](user-guide/control-pilot.md) - Main web interface
- [Training Workflows](user-guide/training-workflows.md) - Training with Kohya and AI Toolkit
- [Model Management](user-guide/model-management.md) - Download and manage models
- [Dataset Preparation](user-guide/dataset-preparation.md) - Create and tag datasets
- [Inference](user-guide/inference.md) - Using ComfyUI and InvokeAI

### 🧩 Components
Detailed guides for each LoRA Pilot component.
- [Kohya SS](components/kohya-ss.md) - Battle-tested LoRA trainer
- [AI Toolkit](components/ai-toolkit.md) - Modern training stack
- [Diffusion Pipe](components/diffusion-pipe.md) - Scalable training pipeline
- [ComfyUI](components/comfyui.md) - Node-based inference
- [InvokeAI](components/invokeai.md) - Dedicated inference stack
- [TrainPilot](components/trainpilot.md) - Guided Kohya automation
- [TagPilot](components/tagpilot.md) - Dataset tagging tool
- [MediaPilot](components/mediapilot.md) - Image management
- [Copilot Sidecar](components/copilot-sidecar.md) - GitHub Copilot integration

### ⚙️ Configuration
Configure LoRA Pilot for your specific needs.
- [Environment Variables](configuration/environment-variables.md) - Complete reference
- [Docker Compose](configuration/docker-compose.md) - Container configurations
- [Models Manifest](configuration/models-manifest.md) - Model configuration
- [Supervisor](configuration/supervisor.md) - Service management
- [Custom Setup](configuration/custom-setup.md) - Advanced configurations

### 💻 Development
For developers who want to contribute or extend LoRA Pilot.
- [Architecture](development/architecture.md) - System design and components
- [Building](development/building.md) - Build from source
- [Contributing](development/contributing.md) - Contribution guidelines
- [Debugging](development/debugging.md) - Debugging guide
- [API Reference](development/api-reference.md) - Complete API documentation

###  Deployment
Deploy LoRA Pilot in production environments.
- [Production](deployment/production.md) - Production deployment
- [Cloud Platforms](deployment/cloud-platforms.md) - Cloud deployment options
- [Windows Installer](deployment/windows-installer.md) - Creating Windows installers
- [Performance Tuning](deployment/performance-tuning.md) - Optimization guides

### 📖 Reference
Quick reference materials and troubleshooting.
- [CLI Commands](reference/cli-commands.md) - Command-line interface
- [File Structure](reference/file-structure.md) - Directory structure reference
- [Supported Models](reference/supported-models.md) - Compatible model families
- [Troubleshooting](reference/troubleshooting.md) - Common issues and solutions
- [Changelog](reference/changelog.md) - Version history

##  Quick Start

1. **Install Docker Desktop** - [Installation Guide](getting-started/installation.md)
2. **Clone and Run** - [First Run](getting-started/first-run.md)
3. **Access ControlPilot** - [User Guide](user-guide/control-pilot.md)
4. **Start Training** - [Training Workflows](user-guide/training-workflows.md)

## 🏗️ What's in LoRA Pilot?

LoRA Pilot bundles multiple AI tools into one integrated workspace:

- **Training**: Kohya SS, AI Toolkit, Diffusion Pipe
- **Inference**: ComfyUI, InvokeAI
- **Management**: ControlPilot, Model Management, Dataset Tools
- **Development**: JupyterLab, Code Server, API Access

Everything is orchestrated by supervisord and persists to `/workspace`, ensuring your work survives container restarts.

## 🔗 External Resources

- **GitHub Repository**: https://github.com/vavo/lora-pilot
- **Docker Hub**: https://hub.docker.com/r/vavo/lora-pilot
- **Community**: [Discussions on GitHub](https://github.com/vavo/lora-pilot/discussions)
- **Issues**: [Bug Reports and Feature Requests](https://github.com/vavo/lora-pilot/issues)

##  Contributing to Documentation

Found an error or want to improve the documentation? Please see the [Contributing Guide](development/contributing.md) for guidelines on how to submit documentation updates.  
*Documentation version: 2.0*

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


