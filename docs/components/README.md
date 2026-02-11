# Components Overview

LoRA Pilot integrates multiple AI tools and services into a unified workspace. Each component serves a specific purpose in the AI workflow, from dataset preparation to model training and inference.

## 🧩 Component Architecture

```
LoRA Pilot
├── Training Components
│   ├── Kohya SS - Traditional LoRA trainer
│   ├── AI Toolkit - Modern training stack
│   └── Diffusion Pipe - Scalable pipeline
├── Inference Components
│   ├── ComfyUI - Node-based inference
│   └── InvokeAI - User-friendly interface
├── Management Components
│   ├── ControlPilot - Central dashboard
│   ├── TrainPilot - Training automation
│   ├── TagPilot - Dataset tagging
│   └── MediaPilot - Media management
└── Development Components
    ├── JupyterLab - Notebook environment
    ├── Code Server - VS Code in browser
    └── Copilot Sidecar - AI assistant
```

## 🎯 Component Matrix

| Component | Purpose | Port | Technology | Use Case |
|-----------|---------|------|------------|----------|
| **ControlPilot** | Central management | 7878 | FastAPI/React | Service orchestration |
| **Kohya SS** | LoRA training | 6666 | Flask/React | Traditional training |
| **AI Toolkit** | Modern training | 8675 | Next.js/Gradio | FLUX/SDXL training |
| **Diffusion Pipe** | Pipeline training | 4444 | Python/TensorBoard | Large-scale training |
| **ComfyUI** | Node-based inference | 5555 | React/WebGL | Complex workflows |
| **InvokeAI** | User inference | 9090 | React/FastAPI | Easy image generation |
| **TrainPilot** | Training automation | - | Python/CLI | Guided training |
| **TagPilot** | Dataset tagging | - | React/FastAPI | Dataset preparation |
| **MediaPilot** | Media management | - | React/FastAPI | Image organization |
| **JupyterLab** | Notebook environment | 8888 | Python/Jupyter | Development |
| **Code Server** | Browser IDE | 8443 | VS Code | Development |
| **Copilot Sidecar** | AI assistant | 7879 | FastAPI | Code assistance |

## 🔄 Integration Benefits

### Shared Resources
- **Models**: All components access `/workspace/models`
- **Datasets**: Shared dataset storage in `/workspace/datasets`
- **Outputs**: Unified output directory `/workspace/outputs`
- **Configuration**: Centralized config in `/workspace/config`

### Service Orchestration
- **Supervisor**: All services managed by supervisord
- **Health Monitoring**: Automatic restart and health checks
- **Log Aggregation**: Centralized logging system
- **Resource Management**: Shared GPU and memory management

### Workflow Integration
- **Seamless Transitions**: Move between tools without data loss
- **Format Compatibility**: Standardized model and dataset formats
- **API Integration**: Components communicate via APIs
- **Web Interface**: Unified access through ControlPilot

## 🚀 Component Deep Dives

### Training Stack

#### Kohya SS
- **Strengths**: Battle-tested, extensive model support
- **Best For**: Traditional LoRA training, fine-tuning
- **Models**: SD1.5, SDXL, SD3, custom architectures
- **Features**: Advanced config, extensive documentation

#### AI Toolkit
- **Strengths**: Modern stack, FLUX.1 support, Next.js UI
- **Best For**: Latest model training, FLUX/SDXL
- **Models**: FLUX.1, SDXL, SD3, experimental models
- **Features**: Gradio interface, modern workflows

#### Diffusion Pipe
- **Strengths**: Scalable, TensorBoard integration
- **Best For**: Large-scale training, experiment tracking
- **Models**: All supported models
- **Features**: Pipeline architecture, experiment management

### Inference Stack

#### ComfyUI
- **Strengths**: Node-based, extensible, custom workflows
- **Best For**: Complex generation workflows, automation
- **Features**: Custom nodes, workflow sharing, batch processing

#### InvokeAI
- **Strengths**: User-friendly, stable, good for beginners
- **Best For**: Simple generation, image editing
- **Features**: Canvas mode, inpainting, upscaling

### Management Tools

#### ControlPilot
- **Role**: Central command center
- **Features**: Service control, model management, file browser
- **Integration**: Manages all other components

#### TrainPilot
- **Role**: Training automation
- **Features**: Guided setup, profile management, progress tracking
- **Integration**: Works with Kohya and AI Toolkit

#### TagPilot
- **Role**: Dataset preparation
- **Features**: Image tagging, captioning, dataset export
- **Integration**: Feeds datasets to all trainers

#### MediaPilot
- **Role**: Media organization
- **Features**: Image browsing, metadata, batch operations
- **Integration**: Works with all generated content

## 🛠️ Technology Stack

### Backend Technologies
- **Python 3.11**: Primary language for most components
- **FastAPI**: API framework for web services
- **Flask**: Legacy support (Kohya SS)
- **Node.js**: AI Toolkit UI and Next.js

### Frontend Technologies
- **React**: Modern UI framework
- **Vue.js**: Legacy support (some components)
- **Gradio**: AI Toolkit interface
- **WebGL**: ComfyUI rendering

### Infrastructure
- **Docker**: Containerization
- **Supervisor**: Process management
- **Nginx**: Reverse proxy (some components)
- **SQLite**: Local databases

## 🔧 Configuration

### Service Configuration
Each component has its own configuration:
- **Environment Variables**: Service-specific settings
- **Config Files**: YAML/TOML configuration
- **Database**: SQLite for state management
- **Logging**: Structured logging to files

### Resource Allocation
- **GPU Sharing**: Components share GPU resources
- **Memory Management**: Automatic memory optimization
- **Storage**: Shared workspace with quotas
- **Network**: Port-based service isolation

## 📊 Performance Characteristics

### Training Performance
| Component | Speed | Memory Usage | Model Support |
|-----------|-------|--------------|---------------|
| Kohya SS | Medium | Medium | Excellent |
| AI Toolkit | Fast | High | Good |
| Diffusion Pipe | Fast | Medium | Excellent |

### Inference Performance
| Component | Speed | Memory Usage | Features |
|-----------|-------|--------------|----------|
| ComfyUI | Fast | Medium | Extensive |
| InvokeAI | Medium | Low | User-friendly |

## 🔄 Version Compatibility

### Component Versions
- **Kohya SS**: Latest stable from upstream
- **AI Toolkit**: Tracked to specific commits
- **ComfyUI**: Latest with custom nodes
- **InvokeAI**: Pinned stable version

### Dependency Management
- **Shared Venvs**: Components share Python environments
- **Version Pinning**: Critical dependencies are pinned
- **Conflict Resolution**: Separate venvs for conflicting packages
- **Update Strategy**: Controlled updates with testing

## 🚀 Future Components

### Planned Additions
- **Training Scheduler**: Advanced training scheduling
- **Model Registry**: Centralized model versioning
- **Experiment Tracker**: ML experiment management
- **API Gateway**: Unified API for all services

### Integration Opportunities
- **Cloud Storage**: S3/Google Drive integration
- **Model Sharing**: Community model sharing
- **Collaboration**: Multi-user workspaces
- **Automation**: Workflow automation tools

---

*Last updated: 2025-02-11*
