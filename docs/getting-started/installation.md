# Installation Guide

This comprehensive guide will walk you through installing LoRA Pilot on Windows, macOS, and Linux. LoRA Pilot uses Docker to provide a consistent, isolated environment for all AI tools.

## 🚀 Quick Install (Recommended)

For most users, the Docker Compose method is the simplest and most reliable:

```bash
# Clone the repository
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot

# Start all services
docker-compose up -d

# Access ControlPilot
open http://localhost:7878
```

## 📋 Prerequisites

Before installing, ensure you have:

1. **Docker Desktop** (Windows/macOS) or **Docker Engine** (Linux)
2. **NVIDIA GPU drivers** (if using GPU acceleration)
3. **Git** (for cloning the repository)
4. **100GB+ free disk space**

## 🖥️ Platform-Specific Installation

### Windows Installation

#### Option A: Docker Desktop GUI (Easiest)

1. **Install Docker Desktop**
   - Download from [docker.com](https://www.docker.com/products/docker-desktop)
   - Run installer with administrator privileges
   - Restart computer when prompted

2. **Configure WSL2**
   - Open PowerShell as Administrator
   - Run: `wsl --install`
   - Restart computer

3. **Clone and Start**
   ```powershell
   git clone https://github.com/vavo/lora-pilot.git
   cd lora-pilot
   docker-compose up -d
   ```

4. **Access Services**
   - Open browser: http://localhost:7878
   - Wait for services to start (2-5 minutes)

#### Option B: Command Line (Advanced)

1. **Install Prerequisites**
   ```powershell
   # Install Chocolatey (if not installed)
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   
   # Install Git
   choco install git
   
   # Install Docker Desktop
   choco install docker-desktop
   ```

2. **Start LoRA Pilot**
   ```powershell
   git clone https://github.com/vavo/lora-pilot.git
   cd lora-pilot
   docker-compose up -d
   ```

### macOS Installation

#### Option A: Docker Desktop (Recommended)

1. **Install Docker Desktop**
   - Download from [docker.com](https://www.docker.com/products/docker-desktop)
   - Drag Docker.app to Applications
   - Launch Docker Desktop from Applications

2. **Clone and Start**
   ```bash
   git clone https://github.com/vavo/lora-pilot.git
   cd lora-pilot
   docker-compose up -d
   ```

3. **Access Services**
   - Open browser: http://localhost:7878

#### Option B: Homebrew (Advanced)

1. **Install Homebrew** (if not installed)
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Docker**
   ```bash
   brew install --cask docker
   ```

3. **Start LoRA Pilot**
   ```bash
   git clone https://github.com/vavo/lora-pilot.git
   cd lora-pilot
   docker-compose up -d
   ```

### Linux Installation

#### Ubuntu/Debian

1. **Install Docker Engine**
   ```bash
   # Update package index
   sudo apt-get update
   
   # Install prerequisites
   sudo apt-get install -y ca-certificates curl gnupg lsb-release
   
   # Add Docker's official GPG key
   sudo mkdir -p /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   
   # Set up repository
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # Install Docker Engine
   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Install NVIDIA Container Toolkit** (for GPU support)
   ```bash
   # Add NVIDIA repositories
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   
   # Install NVIDIA Container Toolkit
   sudo apt-get update
   sudo apt-get install -y nvidia-container-toolkit
   
   # Configure Docker
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

3. **Start LoRA Pilot**
   ```bash
   git clone https://github.com/vavo/lora-pilot.git
   cd lora-pilot
   docker-compose up -d
   ```

#### CentOS/RHEL/Fedora

1. **Install Docker Engine**
   ```bash
   # Remove old versions
   sudo yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
   
   # Install prerequisites
   sudo yum install -y yum-utils
   
   # Add Docker repository
   sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   
   # Install Docker Engine
   sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   
   # Start and enable Docker
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   ```

## ⚙️ Configuration Options

### Environment Variables

Create a `.env` file to customize your installation:

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Key variables:
- `TZ` - Timezone (default: America/New_York)
- `SUPERVISOR_ADMIN_PASSWORD` - Supervisor web UI password
- `HF_TOKEN` - Hugging Face token for private models
- `INSTALL_AI_TOOLKIT` - Enable/disable AI Toolkit (default: 1)

### Docker Compose Variants

Choose the appropriate compose file:

```bash
# GPU-enabled (default)
docker-compose up -d

# CPU-only
docker-compose -f docker-compose.cpu.yml up -d

# Development mode
docker-compose -f docker-compose.dev.yml up -d
```

### Port Customization

Modify ports in `docker-compose.yml` if you have conflicts:

```yaml
services:
  lora-pilot:
    ports:
      - "7878:7878"    # ControlPilot
      - "5555:5555"    # ComfyUI
      - "6666:6666"    # Kohya SS
      - "9090:9090"    # InvokeAI
```

## 🔄 Verification Steps

After installation, verify everything is working:

### 1. Check Container Status
```bash
docker-compose ps
```

### 2. Check Service Logs
```bash
docker-compose logs -f
```

### 3. Access Web Interfaces
- **ControlPilot**: http://localhost:7878
- **ComfyUI**: http://localhost:5555
- **Kohya SS**: http://localhost:6666
- **InvokeAI**: http://localhost:9090

### 4. Test GPU Access
```bash
docker exec lora-pilot nvidia-smi
```

## 🛠️ Troubleshooting

### Common Issues

#### Docker Desktop Won't Start
- **Windows**: Ensure WSL2 is enabled and Hyper-V is active
- **macOS**: Check system preferences for Docker permissions
- **Linux**: Verify Docker service is running

#### Port Conflicts
- Change ports in `docker-compose.yml`
- Kill conflicting processes: `lsof -i :7878`

#### GPU Not Detected
- Verify NVIDIA drivers are installed
- Check NVIDIA Container Toolkit setup
- Test with: `docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi`

#### Out of Memory Errors
- Increase Docker memory allocation
- Use CPU-only compose file
- Close other GPU-intensive applications

#### Slow Performance
- Use SSD for workspace storage
- Increase RAM allocation to Docker
- Check GPU temperature and power limits

### Reset Installation

If you need to start fresh:

```bash
# Stop and remove containers
docker-compose down -v

# Remove images (optional)
docker system prune -a

# Re-clone repository
rm -rf lora-pilot
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot
docker-compose up -d
```

## 📱 Alternative Installation Methods

### Pre-built Image

```bash
docker run -d \
  --name lora-pilot \
  --gpus all \
  -p 7878:7878 \
  -p 5555:5555 \
  -p 6666:6666 \
  -p 9090:9090 \
  -v $(pwd)/workspace:/workspace \
  vavo/lora-pilot:latest
```

### Build from Source

```bash
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot
docker build -t lora-pilot:local .
docker-compose up -d
```

## 🎯 Next Steps

After successful installation:

1. **[First Run Setup](first-run.md)** - Initial configuration
2. **[User Guide](../user-guide/README.md)** - Learn the interface
3. **[Training Workflows](../user-guide/training-workflows.md)** - Start training

---

*Last updated: 2025-02-11*
