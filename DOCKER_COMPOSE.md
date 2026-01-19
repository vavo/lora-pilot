# Docker Compose files for local LoRA Pilot deployment

## 📁 Files Created

### Core Files
- **`docker-compose.yml`** - Standard GPU setup with all services
- **`docker-compose.dev.yml`** - Development setup with source mounting
- **`docker-compose.cpu.yml`** - CPU-only setup (limits via local Compose are not enforced)
- **`.env.example`** - Environment variables template

### Documentation & Tools
- **`docker-compose/README.md`** - Comprehensive setup guide
- **`docker-compose-helper.sh`** - Easy management script

## 🚀 Quick Start

### 1. Basic Setup
```bash
# Clone and navigate to lora-pilot directory
cd lora-pilot

# Setup workspace and environment
./docker-compose-helper.sh setup

# Start with GPU support
./docker-compose-helper.sh start

# Or start CPU-only
./docker-compose-helper.sh start cpu
```

### 2. Access Services
- **ControlPilot**: http://localhost:7878
- **JupyterLab**: http://localhost:8888
- **VS Code Server**: http://localhost:8443
- **ComfyUI**: http://localhost:5555
- **Kohya SS**: http://localhost:6666
- **InvokeAI**: http://localhost:9090
- **Diffusion Pipe**: http://localhost:4444

## 🛠️ Management Commands

```bash
# Start services
./docker-compose-helper.sh start [standard|dev|cpu]

# Stop services  
./docker-compose-helper.sh stop [standard|dev|cpu]

# View logs
./docker-compose-helper.sh logs [standard|dev|cpu]

# Access container shell
./docker-compose-helper.sh shell [standard|dev|cpu]

# Check status
./docker-compose-helper.sh status [standard|dev|cpu]

# Update image
./docker-compose-helper.sh update

# Setup workspace
./docker-compose-helper.sh setup
```

## ⚙️ Configuration Options

### Environment Variables (.env)
```bash
# Timezone
TZ=America/New_York

# Hugging Face token
HF_TOKEN=your_token_here

# Custom ports
JUPYTER_PORT=8888
COMFY_PORT=5555
# ... etc
```

### Volume Mounting
```yaml
volumes:
  # Main workspace
  - ./workspace:/workspace
  
  # Custom models
  - ./my-models:/workspace/models
  
  # Custom datasets
  - ./my-datasets:/workspace/datasets
```

## 🎯 Use Cases

### Standard Setup (`docker-compose.yml`)
- ✅ Full GPU support
- ✅ All services exposed
- ✅ Health checks
- ✅ Production-ready

### Development Setup (`docker-compose.dev.yml`)
- ✅ Source code mounting
- ✅ Debug mode enabled
- ✅ Interactive shell access
- ✅ Live reloading

### CPU-Only Setup (`docker-compose.cpu.yml`)
- ✅ No GPU requirements
- ✅ Minimal ports
- ✅ Optimized for CPU inference
- ⚠️ Resource limits are not enforced by local Docker Compose (use Docker runtime limits if needed)

## 🐛 Troubleshooting

### Common Issues
1. **GPU not detected**: Check NVIDIA Docker installation
2. **Port conflicts**: Change ports in compose file
3. **Permission errors**: Fix workspace permissions
4. **Memory issues**: Use Docker runtime limits (`--memory`, `--cpus`) or Docker Desktop settings

### Debug Commands
```bash
# Check container status
docker-compose ps

# View logs
./docker-compose-helper.sh logs

# Access shell
./docker-compose-helper.sh shell

# Check GPU access
docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi
```

## 📚 Documentation

See `docker-compose/README.md` for comprehensive documentation including:
- Prerequisites and installation
- Customization options
- Troubleshooting guide
- Production tips
- Additional resources

## 🎉 Benefits

- **Easy Setup**: One-command deployment
- **Multiple Configurations**: GPU, CPU, Development modes
- **Persistent Storage**: Workspace data preserved
- **Health Monitoring**: Built-in health checks
- **Resource Management**: Use Docker runtime limits if needed
- **Development Friendly**: Source mounting and debug mode

**Users can now easily run LoRA Pilot locally with professional Docker Compose setup!** 🚀✨
