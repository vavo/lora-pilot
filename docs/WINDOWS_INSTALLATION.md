# Windows Installation Guide for LoRA Pilot

This guide will help Windows users install and run LoRA Pilot using Docker Desktop. LoRA Pilot is a comprehensive AI platform that includes ComfyUI, Kohya SS, JupyterLab, VS Code, and more in a single Docker container.

## ystem Requirements

### Hardware Requirements
- **RAM**: 16GB minimum (32GB+ recommended for training)
- **Storage**: 100GB+ free disk space for models and datasets
- **GPU**: NVIDIA GPU with 8GB+ VRAM (optional but recommended for training)
  - Supported: RTX 20xx, 30xx, 40xx series
  - CUDA 12.4 compatible drivers required

### Software Requirements
- **Windows 10/11** (64-bit)
- **Docker Desktop for Windows** (latest version)
- **NVIDIA GPU Driver** (if using GPU)
- **Git for Windows** (optional, for cloning repository)

## Step-by-Step Installation

### Step 1: Install Docker Desktop

1. **Download Docker Desktop**
   - Visit https://www.docker.com/products/docker-desktop
   - Download the Windows installer
   - Run the installer with administrator privileges

2. **Configure Docker Desktop**
   - Launch Docker Desktop after installation
   - Go to **Settings** → **General**
   - Enable "Use WSL 2 based engine" (recommended)
   - Restart Docker Desktop when prompted

3. **Verify Installation**
   ```powershell
   docker --version
   docker-compose --version
   ```

### Step 2: Install NVIDIA Container Toolkit (GPU Users Only)

1. **Install NVIDIA Drivers**
   - Download latest drivers from https://www.nvidia.com/drivers
   - Install and reboot your system

2. **Verify GPU Support**
   ```powershell
   nvidia-smi
   ```

3. **Test NVIDIA Docker Support**
   ```powershell
   docker run --rm --gpus all nvidia/cuda:12.4.1-runtime-ubuntu22.04 nvidia-smi
   ```

### Step 3: Download LoRA Pilot

#### Option A: Using Git (Recommended)
```powershell
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot
```

#### Option B: Direct Download
1. Download the repository as ZIP from GitHub
2. Extract to a folder (e.g., `C:\lora-pilot`)
3. Open PowerShell or Command Prompt in that folder

### Step 4: Configure Environment

1. **Copy Environment Template**
   ```powershell
   copy .env.example .env
   ```

2. **Edit Configuration** (optional)
   - Open `.env` in Notepad or VS Code
   - Adjust timezone if needed:
     ```
     TZ=America/New_York
     ```
   - Add your Hugging Face token for private models:
     ```
     HF_TOKEN=your_huggingface_token_here
     ```

### Step 5: Prepare Workspace

1. **Create Workspace Directory**
   ```powershell
   mkdir workspace
   mkdir workspace\models
   mkdir workspace\datasets
   mkdir workspace\datasets\images
   mkdir workspace\outputs
   mkdir workspace\logs
   mkdir workspace\config
   mkdir workspace\cache
   ```

### Step 6: Run LoRA Pilot

#### 🖱️ Option A: Using Docker Desktop GUI (Easiest)

1. **Open Docker Desktop**
   - Launch Docker Desktop application
   - Wait for it to show "Docker Desktop is running"

2. **Load Compose File**
   - Click **"+"** button in the top-left corner
   - Select **"Compose"**
   - Navigate to your `lora-pilot` folder
   - Select `docker-compose.yml` (for GPU) or `docker-compose.cpu.yml` (for CPU)
   - Click **"Open"**

3. **Start Services**
   - Docker Desktop will show the compose configuration
   - Click **"Start"** button (or right-click → "Start")
   - Wait for containers to download and start (green checkmarks)

4. **Access Services**
   - Click on the container name in Docker Desktop
   - View logs and access ports from the container details
   - Or open browser: http://localhost:7878

#### 💻 Option B: Using Command Line (Advanced)

##### GPU Setup (Recommended)
```powershell
docker-compose up -d
```

##### CPU-Only Setup
```powershell
docker-compose -f docker-compose.cpu.yml up -d
```

##### Development Setup
```powershell
docker-compose -f docker-compose.dev.yml up -d
```

### Step 7: Verify Installation

#### 🖱️ Using Docker Desktop GUI
1. **Check Container Status**
   - In Docker Desktop, look for green checkmarks next to your container
   - Click on the container to see detailed status
   - Check the **"Logs"** tab to ensure services started successfully

2. **Access Services**
   - Click on **"Ports"** tab in container details
   - Click on port numbers to open services in browser
   - Or manually navigate to: http://localhost:7878

#### 💻 Using Command Line (Advanced)

1. **Check Container Status**
   ```powershell
   docker-compose ps
   ```

2. **View Logs**
   ```powershell
   docker-compose logs -f
   ```

3. **Access Services**
   Open your web browser and navigate to:
   - **ControlPilot**: http://localhost:7878
   - **JupyterLab**: http://localhost:8888
   - **VS Code Server**: http://localhost:8443
   - **ComfyUI**: http://localhost:5555
   - **Kohya SS**: http://localhost:6666
   - **InvokeAI**: http://localhost:9090
   - **Diffusion Pipe**: http://localhost:4444

##  Common Windows Issues & Solutions

### Issue 1: "Docker daemon is not running"
**Solution:**
1. Make sure Docker Desktop is running
2. Restart Docker Desktop with administrator privileges
3. Check Windows Services if Docker service is running

### Issue 2: "Port already in use"
**Solution:**
1. Check what's using the port:
   ```powershell
   netstat -ano | findstr :7878
   ```
2. Kill the process or change ports in `docker-compose.yml`

### Issue 3: "GPU not detected"
**Solution:**
1. Verify NVIDIA drivers are installed:
   ```powershell
   nvidia-smi
   ```
2. Check WSL2 GPU support:
   ```powershell
   wsl --update
   wsl --shutdown
   ```
3. Restart Docker Desktop

### Issue 4: "Out of memory errors"
**Solution:**
1. Increase Docker memory allocation in Docker Desktop settings
2. Use CPU-only compose file for testing
3. Close unnecessary applications

### Issue 5: "Permission denied errors"
**Solution:**
1. Run PowerShell as Administrator
2. Check file permissions on workspace directory
3. Ensure Docker Desktop has proper permissions

## 📁 File Paths in Windows

### Docker Paths vs Windows Paths
- **Docker**: `/workspace` → **Windows**: `./workspace`
- **Docker**: `/workspace/models` → **Windows**: `./workspace/models`
- **Docker**: `/workspace/datasets` → **Windows**: `./workspace/datasets`

### Accessing Files from Windows
Your workspace is mounted at `./workspace` in the repository folder:
```
C:\lora-pilot\workspace\
├── models\          # Downloaded models
├── datasets\        # Training datasets
├── outputs\         # Generated images and trained models
├── logs\           # Service logs
└── config\         # Configuration files
```

##  Management Commands

### 🖱️ Using Docker Desktop GUI

#### Start Services
1. Open Docker Desktop
2. Find your LoRA Pilot container
3. Click **"Start"** button (or right-click → "Start")

#### Stop Services
1. In Docker Desktop, select your container
2. Click **"Stop"** button (or right-click → "Stop")

#### View Logs
1. Click on container name
2. Go to **"Logs"** tab
3. View real-time logs from all services

#### Update Container
1. Click **"Pull"** to get latest image
2. Container will restart with new version automatically

### 💻 Using Command Line (Advanced)

#### Start Services
```powershell
# Start all services
docker-compose up -d

# Start specific compose file
docker-compose -f docker-compose.cpu.yml up -d
```

#### Stop Services
```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

#### View Logs
```powershell
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f lora-pilot
```

#### Update Container
```powershell
# Pull latest image
docker-compose pull

# Restart with new image
docker-compose up -d --force-recreate
```

##  Quick Start Workflow

### 1. Download a Model
```powershell
# Access ControlPilot at http://localhost:7878
# Go to Models tab → Search "sdxl-base" → Click Download
```

### 2. Prepare Dataset
```powershell
# Place your images in:
C:\lora-pilot\workspace\datasets\images\my_dataset\
```

### 3. Start Training
```powershell
# Access ControlPilot → TrainPilot tab
# Select dataset → Choose quality → Start training
```

## 📞 Troubleshooting

### Getting Help
1. **Check logs**: `docker-compose logs -f`
2. **Verify ports**: Ensure no other services use ports 7878, 8888, 8443, 5555, 6666, 9090, 4444
3. **Disk space**: Ensure at least 100GB free space
4. **Memory**: Close other applications if experiencing memory issues

### Performance Tips
1. **SSD Storage**: Use SSD for better I/O performance
2. **RAM**: Allocate more RAM to Docker Desktop (Settings → Resources)
3. **GPU**: Use GPU setup for training and generation
4. **Network**: Use wired connection for faster model downloads

## 🆘 Support

If you encounter issues:
1. Check the [GitHub Issues](https://github.com/your-username/lora-pilot/issues)
2. Review the [main documentation](README.md)
3. Join the community Discord (if available)
4. Include system specs and error logs when reporting issues

---

**Happy AI creating! 🤖**

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


