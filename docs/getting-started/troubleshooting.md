# Troubleshooting Guide

This guide covers common issues you might encounter during installation and first run of LoRA Pilot, along with their solutions.

## 🚨 Quick Diagnostics

### Health Check Script

Run this comprehensive diagnostic to identify issues:

```bash
# Access container shell
docker exec -it lora-pilot bash

# Run health check
curl -s http://localhost:7878/api/health || echo "ControlPilot not responding"
nvidia-smi || echo "GPU not detected"
df -h /workspace || echo "Workspace not accessible"
python -c "import torch; print('PyTorch:', torch.__version__, 'CUDA:', torch.cuda.is_available())"
```

### Service Status Check

```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs controlpilot
docker-compose logs kohya
docker-compose logs comfyui
```

## 🐳 Docker Issues

### Container Won't Start

#### Problem
```bash
ERROR: for lora-pilot  Cannot start service lora-pilot: OCI runtime create failed
```

#### Solutions
1. **Check Docker Desktop status**
   - Windows/macOS: Ensure Docker Desktop is running
   - Linux: `sudo systemctl status docker`

2. **Verify GPU support**
   ```bash
   # Test NVIDIA container runtime
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

3. **Check port conflicts**
   ```bash
   # Find what's using the ports
   netstat -tulpn | grep :7878
   lsof -i :7878
   ```

4. **Increase Docker memory**
   - Docker Desktop → Settings → Resources → Memory → 8GB+

### Out of Memory Errors

#### Problem
```bash
standard_init_linux.go:228: exec user process caused: memory cgroup: limit exceeded
```

#### Solutions
1. **Increase Docker memory allocation**
   - Docker Desktop → Settings → Resources → Memory → 16GB+

2. **Use CPU-only mode temporarily**
   ```bash
   docker-compose -f docker-compose.cpu.yml up -d
   ```

3. **Close other applications**
   - Free up system RAM
   - Close browser tabs and other memory-intensive apps

### Permission Issues

#### Problem
```bash
ERROR: permission denied while trying to connect to the Docker daemon socket
```

#### Solutions
1. **Add user to docker group**
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **Use sudo (temporary)**
   ```bash
   sudo docker-compose up -d
   ```

## 🎮 GPU Issues

### GPU Not Detected

#### Problem
```bash
docker exec lora-pilot nvidia-smi
NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.
```

#### Solutions
1. **Update NVIDIA drivers**
   - Download latest drivers from NVIDIA website
   - Restart computer after installation

2. **Check CUDA version compatibility**
   ```bash
   # Check driver version
   nvidia-smi
   
   # Should show CUDA 12.4+ capability
   ```

3. **Verify NVIDIA Container Toolkit**
   ```bash
   # Linux only
   sudo apt-get install nvidia-container-toolkit
   sudo systemctl restart docker
   ```

### CUDA Out of Memory

#### Problem
```bash
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
```

#### Solutions
1. **Reduce batch size**
   - In Kohya: Set batch size to 1
   - In AI Toolkit: Reduce `batch_size` in config

2. **Enable gradient checkpointing**
   ```yaml
   # In training config
   gradient_checkpointing: true
   ```

3. **Use CPU offloading**
   ```yaml
   # In training config
   model_kwargs:
     low_cpu_mem_mode: true
   ```

4. **Clear GPU cache**
   ```bash
   # In container shell
   python -c "import torch; torch.cuda.empty_cache()"
   ```

### Triton Compilation Errors

#### Problem
```bash
RuntimeError: Failed to import diffusers.models.autoencoders.autoencoder_kl
Command '['/usr/bin/gcc', ...] returned non-zero exit status 1.
```

#### Solutions
1. **Disable Triton**
   ```bash
   # Add to environment
   export TRITON_DISABLE=1
   export TORCHINDUCTOR_DISABLE=1
   ```

2. **Add to docker-compose.yml**
   ```yaml
   environment:
     - TRITON_DISABLE=1
     - TORCHINDUCTOR_DISABLE=1
   ```

3. **Restart services**
   ```bash
   docker-compose restart
   ```

## 🌐 Network Issues

### Ports Not Accessible

#### Problem
```bash
curl: (7) Failed to connect to localhost port 7878: Connection refused
```

#### Solutions
1. **Check if service is running**
   ```bash
   docker-compose ps
   docker-compose logs controlpilot
   ```

2. **Verify port mapping**
   ```bash
   # Check docker-compose.yml ports section
   grep -A 10 "ports:" docker-compose.yml
   ```

3. **Check firewall**
   ```bash
   # Linux
   sudo ufw status
   sudo ufw allow 7878
   
   # Windows
   # Check Windows Defender Firewall
   ```

### Slow Model Downloads

#### Problem
Models downloading very slowly or timing out.

#### Solutions
1. **Check internet connection**
   ```bash
   curl -o /dev/null http://speedtest.net/10mb.bin
   ```

2. **Use Hugging Face token**
   ```bash
   # Add to .env file
   HF_TOKEN=your_token_here
   ```

3. **Download manually**
   ```bash
   # In container shell
   cd /workspace/models/stable-diffusion
   wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
   ```

## 💾 Storage Issues

### Insufficient Disk Space

#### Problem
```bash
ERROR: no space left on device
```

#### Solutions
1. **Check disk usage**
   ```bash
   df -h
   du -sh /workspace/*
   ```

2. **Clean up unused images**
   ```bash
   docker system prune -a
   ```

3. **Move workspace to larger drive**
   ```bash
   # Update docker-compose.yml
   volumes:
     - /path/to/larger/drive/workspace:/workspace
   ```

### Slow I/O Performance

#### Problem
Training is very slow due to disk bottlenecks.

#### Solutions
1. **Use SSD for workspace**
   - Move `/workspace` to NVMe SSD
   - Use RAM disk for temporary files

2. **Increase cache size**
   ```bash
   # In training config
   cache_latents_to_disk: false  # Keep in RAM
   ```

3. **Optimize dataset location**
   ```bash
   # Move datasets to fastest storage
   mv /workspace/datasets /ramdisk/datasets
   ln -s /ramdisk/datasets /workspace/datasets
   ```

## 🔧 Service-Specific Issues

### Kohya SS Won't Start

#### Problem
```bash
kohya: ERROR (not running)
```

#### Solutions
1. **Check dependencies**
   ```bash
   docker exec lora-pilot /opt/venvs/core/bin/pip list | grep kohya
   ```

2. **Restart service**
   ```bash
   docker-compose restart kohya
   ```

3. **Check logs**
   ```bash
   docker-compose logs kohya | tail -50
   ```

### ComfyUI Not Loading

#### Problem
ComfyUI shows blank page or loading spinner.

#### Solutions
1. **Clear browser cache**
   - Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)

2. **Check ComfyUI logs**
   ```bash
   docker-compose logs comfyui
   ```

3. **Reset ComfyUI**
   ```bash
   docker-compose exec lora-pilot rm -rf /workspace/apps/comfy/user
   docker-compose restart comfyui
   ```

### AI Toolkit Database Errors

#### Problem
```bash
DatabaseError: unable to open database file
```

#### Solutions
1. **Create database directory**
   ```bash
   mkdir -p /workspace/config/ai-toolkit
   chmod 755 /workspace/config/ai-toolkit
   ```

2. **Reset database**
   ```bash
   rm -f /workspace/config/ai-toolkit/aitk_db.db
   docker-compose restart ai-toolkit
   ```

## 🔄 Reset and Recovery

### Full Reset

If you need to start completely fresh:

```bash
# Stop and remove everything
docker-compose down -v

# Remove all Docker data
docker system prune -a --volumes

# Re-clone repository
rm -rf lora-pilot
git clone https://github.com/vavo/lora-pilot.git
cd lora-pilot

# Start fresh
docker-compose up -d
```

### Backup Before Reset

```bash
# Save your workspace
tar -czf lora-pilot-backup.tar.gz workspace/

# Save configuration
cp .env .env.backup
```

### Selective Reset

```bash
# Reset specific service
docker-compose stop kohya
docker-compose rm -f kohya
docker-compose up -d kohya

# Reset workspace directory
rm -rf /workspace/outputs/*
```

## 📞 Getting Help

### Collect Debug Information

```bash
# Create debug report
docker exec lora-pilot bash -c "
echo '=== System Info ==='
uname -a
echo '=== Docker Info ==='
docker --version
echo '=== GPU Info ==='
nvidia-smi
echo '=== Disk Usage ==='
df -h
echo '=== Memory Usage ==='
free -h
echo '=== Service Status ==='
supervisorctl status
" > debug-info.txt
```

### Community Support

1. **GitHub Issues**: https://github.com/vavo/lora-pilot/issues
2. **Discussions**: https://github.com/vavo/lora-pilot/discussions
3. **Discord Community**: [Link to Discord if available]

### What to Include in Bug Reports

- **Operating system and version**
- **Docker version**
- **GPU model and driver version**
- **Complete error messages**
- **Steps to reproduce**
- **Debug information** (from above)

---

*Last updated: 2025-02-11*
