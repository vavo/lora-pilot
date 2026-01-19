# LoRA Pilot Docker Compose Setup

This directory contains Docker Compose configurations for running LoRA Pilot locally.

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose**:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **NVIDIA Docker Toolkit** (for GPU support):
   ```bash
   # Ubuntu/Debian
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

### Basic Usage

1. **Clone and prepare workspace**:
   ```bash
   git clone <your-repo>
   cd lora-pilot
   mkdir -p workspace/{models,datasets,outputs,logs,config,cache}
   ```

2. **Start the container**:
   ```bash
   # Standard GPU setup
   docker-compose up -d
   
   # CPU-only setup
   docker-compose -f docker-compose.cpu.yml up -d
   
   # Development setup
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Access services**:
   - **ControlPilot**: http://localhost:7878
   - **JupyterLab**: http://localhost:8888 (token in workspace/config/secrets.env)
   - **VS Code Server**: http://localhost:8443 (password in workspace/config/secrets.env)
   - **ComfyUI**: http://localhost:5555
   - **Kohya SS**: http://localhost:6666
   - **InvokeAI**: http://localhost:9090
   - **Diffusion Pipe**: http://localhost:4444

## 📁 Configuration Files

### `docker-compose.yml` (Standard)
- **GPU enabled** (if NVIDIA Docker installed)
- **All services exposed**
- **Persistent workspace storage**
- **Health checks included**

### `docker-compose.cpu.yml` (CPU Only)
- **No GPU requirements**
- **Only essential ports exposed**
- **Optimized for CPU inference**
- **Resource limits are not enforced by local Docker Compose (use Docker runtime limits if needed)**

### `docker-compose.dev.yml` (Development)
- **Source code mounting**
- **Development environment variables**
- **Debug mode enabled**
- **TTY for interactive debugging**

## ⚙️ Customization

### Environment Variables

Create a `.env` file to customize settings:

```bash
# Timezone
TZ=America/New_York

# Hugging Face token (for private models)
HF_TOKEN=your_token_here

# Custom ports
JUPYTER_PORT=8888
CODE_SERVER_PORT=8443
COMFY_PORT=5555
KOHYA_PORT=6666
INVOKE_PORT=9090
DIFFPIPE_PORT=4444

# Supervisor password
SUPERVISOR_ADMIN_PASSWORD=your_secure_password
```

### Volume Mounting

Mount your existing data:

```yaml
volumes:
  # Main workspace
  - ./workspace:/workspace
  
  # Custom models directory
  - /path/to/my/models:/workspace/models
  
  # Custom datasets
  - /path/to/my/datasets:/workspace/datasets
  
  # Cache for faster downloads
  - ./huggingface-cache:/root/.cache/huggingface
```

### Port Changes

Modify ports in the compose file:

```yaml
ports:
  - "8080:7878"  # Access ControlPilot on port 8080
  - "9999:8888"  # Access Jupyter on port 9999
```

## 🔧 Management Commands

### Container Management

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f lora-pilot

# Access container shell
docker-compose exec lora-pilot bash

# Restart services
docker-compose restart lora-pilot

# Update image
docker-compose pull && docker-compose up -d
```

### Monitoring

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats lora-pilot

# Check health
docker-compose exec lora-pilot curl http://localhost:7878/api/services
```

## 🐛 Troubleshooting

### Common Issues

1. **GPU not detected**:
   ```bash
   # Check NVIDIA Docker
   docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi
   ```

2. **Permission denied**:
   ```bash
   # Fix workspace permissions
   sudo chown -R $USER:$USER ./workspace
   ```

3. **Port conflicts**:
   ```bash
   # Check what's using ports
   netstat -tulpn | grep :7878
   
   # Or change ports in compose file
   ```

4. **Out of memory**:
   ```bash
   # Use Docker runtime limits (local Compose ignores deploy.* limits)
   docker run --memory=16g --cpus=4 ...
   ```

### Debug Mode

For troubleshooting, use the development compose file:

```bash
docker-compose -f docker-compose.dev.yml up -d
docker-compose -f docker-compose.dev.yml exec lora-pilot bash
```

### Logs

Check service logs:

```bash
# Main application logs
docker-compose logs -f lora-pilot

# Specific service logs
docker-compose exec lora-pilot tail -f /workspace/logs/controlpilot.out.log

# Supervisor logs
docker-compose exec lora-pilot supervisorctl status
```

## 🚀 Production Tips

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Security**: Don't expose all ports publicly
3. **Backups**: Regularly backup the workspace directory
4. **Monitoring**: Use health checks and monitoring tools
5. **Updates**: Pin to specific image versions for stability

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-container-toolkit)
- [LoRA Pilot README](../README.md)

## 🆘 Support

If you encounter issues:

1. Check the logs above
2. Verify GPU drivers and NVIDIA Docker
3. Ensure sufficient disk space and memory
4. Check for port conflicts
5. Create an issue with your system details
