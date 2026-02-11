# ControlPilot

ControlPilot is the central web interface for LoRA Pilot, providing a unified dashboard for managing all services, models, datasets, and training workflows. It's your command center for the entire AI workspace.

## 🎯 Overview

ControlPilot offers:
- **Service Management**: Start, stop, and monitor all LoRA Pilot services
- **Model Management**: Download, organize, and manage AI models
- **Dataset Tools**: Access TagPilot and MediaPilot for dataset work
- **Training Orchestration**: Launch and monitor training jobs
- **File Browser**: Navigate and manage workspace files
- **System Monitoring**: Track resource usage and system health

## 🚀 Access and Navigation

### Accessing ControlPilot

1. **Primary URL**: http://localhost:7878
2. **Via Docker**: `docker exec lora-pilot supervisorctl status controlpilot`
3. **From Container**: `curl http://localhost:7878/api/health`

### Navigation Structure

```
ControlPilot Dashboard
├── 🏠 Home              - Overview and quick actions
├── 🧩 Services          - Service management and control
├── 📦 Models            - Model downloading and management
├── 📁 Datasets          - Dataset tools and management
├── 🎯 Training          - Training job orchestration
├── 📂 File Browser      - Workspace file management
├── 📊 System            - Resource monitoring and logs
└── 📚 Docs              - Integrated documentation
```

## 🖥️ Interface Guide

### Home Dashboard

#### Quick Stats
- **Active Services**: Number of running services
- **GPU Usage**: Current GPU memory utilization
- **Storage Usage**: Workspace disk usage
- **Recent Jobs**: Latest training activities

#### Quick Actions
- **Start All Services**: Launch all LoRA Pilot components
- **Download Models**: Quick access to popular models
- **Create Dataset**: Launch TagPilot for dataset creation
- **Start Training**: Quick training setup with TrainPilot

#### System Health
- **Service Status**: Overall system health indicator
- **Resource Alerts**: Memory, storage, or GPU warnings
- **Recent Logs**: Latest system events and errors

### Services Management

#### Service Overview
Each service card displays:
- **Service Name**: Component identifier
- **Status**: Running, Stopped, or Error
- **Port**: Network port number
- **Resource Usage**: Memory and GPU consumption
- **Actions**: Start, Stop, Restart, Logs, Open

#### Service Controls
```bash
# Available actions for each service:
- Start: Launch the service
- Stop: Graceful shutdown
- Restart: Stop and start service
- Logs: View service logs
- Open: Launch service interface
- Update: Update to latest version
```

#### Service Details
Click on any service to see:
- **Configuration**: Current settings and environment
- **Resource Usage**: Real-time memory and GPU usage
- **Log History**: Recent log entries
- **Health Checks**: Service health status

### Model Management

#### Model Library
- **Available Models**: Browse downloadable models
- **Installed Models**: View installed models
- **Model Categories**: Filter by type (checkpoint, LoRA, etc.)
- **Search**: Find specific models quickly

#### Model Operations
```bash
# Model management actions:
- Download: Install model from repository
- Remove: Uninstall model (with confirmation)
- Info: View model details and requirements
- Update: Check for model updates
- Validate: Verify model integrity
```

#### Model Details
For each model, you can see:
- **Name and Description**: Model identifier and purpose
- **Size and Requirements**: Disk space and hardware needs
- **Tags and Categories**: Model classification
- **Installation Status**: Download progress and health
- **Usage Statistics**: How often used in training

### Dataset Tools

#### TagPilot Integration
- **Launch TagPilot**: Open dataset tagging interface
- **Recent Datasets**: View recently created datasets
- **Dataset Stats**: Image count, caption coverage
- **Quick Actions**: Create new dataset, import existing

#### MediaPilot Integration
- **Launch MediaPilot**: Open media management interface
- **Image Gallery**: Browse generated images
- **Batch Operations**: Organize and process images
- **Export Options**: Download or share collections

### Training Orchestration

#### TrainPilot Integration
- **Quick Training**: Fast setup with common profiles
- **Dataset Selection**: Choose from available datasets
- **Model Selection**: Pick base model for training
- **Configuration**: Training parameters and settings

#### Job Management
- **Active Jobs**: Currently running training jobs
- **Job Queue**: Pending training jobs
- **Job History**: Completed and failed jobs
- **Progress Tracking**: Real-time training progress

#### Training Profiles
```yaml
# Available training profiles:
- quick_test: 100 steps, basic testing
- medium_training: 500 steps, balanced quality
- full_training: 1000+ steps, high quality
- experimental: Latest features, experimental
```

### File Browser

#### Workspace Navigation
- **Directory Tree**: Browse workspace structure
- **File Operations**: Copy, move, delete, rename
- **Preview**: Quick file preview for images and text
- **Upload**: Upload files to workspace

#### Common Directories
```
/workspace/
├── datasets/           # Training datasets
├── outputs/           # Training outputs
├── models/            # Downloaded models
├── cache/             # Cache files
├── config/            # Configuration files
└── logs/              # Log files
```

### System Monitoring

#### Resource Usage
- **GPU Utilization**: Real-time GPU usage graphs
- **Memory Usage**: System and GPU memory consumption
- **Disk Usage**: Storage space and usage trends
- **Network Activity**: Data transfer rates

#### Service Health
- **Uptime**: Service running time
- **Response Times**: API response performance
- **Error Rates**: Service error frequency
- **Resource Limits**: Memory and CPU limits

#### Log Management
- **Live Logs**: Real-time log streaming
- **Log History**: Historical log entries
- **Log Filtering**: Filter by service or error level
- **Log Export**: Download logs for analysis

## 🔧 Advanced Features

### API Access

#### REST API
ControlPilot provides a REST API for automation:

```bash
# Service management
GET /api/services              # List all services
POST /api/services/{name}/start   # Start service
POST /api/services/{name}/stop    # Stop service

# Model management
GET /api/models               # List models
POST /api/models/pull         # Download model
DELETE /api/models/{name}     # Remove model

# Training management
GET /api/training/jobs        # List training jobs
POST /api/training/start      # Start training
GET /api/training/status      # Training status
```

#### API Authentication
```bash
# Set admin password in .env
SUPERVISOR_ADMIN_PASSWORD=your_secure_password

# Use in API calls
curl -u admin:password http://localhost:7878/api/services
```

### Custom Configuration

#### Environment Variables
```bash
# ControlPilot configuration
CONTROLPILOT_PORT=7878
CONTROLPILOT_HOST=0.0.0.0
SUPERVISOR_ADMIN_PASSWORD=secure_password
CONTROLPILOT_LOG_LEVEL=INFO
```

#### Custom Themes
```bash
# Custom CSS and themes
# Place custom.css in /workspace/config/controlpilot/
# Restart ControlPilot to apply
```

### Integration with Other Tools

#### JupyterLab Integration
- **Launch**: Open JupyterLab from ControlPilot
- **Workspace Access**: Direct access to workspace files
- **Kernel Management**: Switch between Python environments

#### Code Server Integration
- **VS Code in Browser**: Full VS Code experience
- **Workspace Mount**: Direct workspace access
- **Extension Support**: Install VS Code extensions

#### Copilot Sidecar Integration
- **AI Assistant**: GitHub Copilot integration
- **Code Generation**: AI-powered code assistance
- **Workspace Awareness**: Context-aware suggestions

## 📊 Performance Optimization

### Interface Optimization

#### Caching
- **Model Cache**: Cache model information for faster loading
- **Log Cache**: Cache log entries for better performance
- **Image Cache**: Cache thumbnails and previews

#### Lazy Loading
- **Service Status**: Load service information on demand
- **Model Lists**: Paginate model lists for large collections
- **Log History**: Load log entries incrementally

### Resource Management

#### Memory Optimization
- **Log Rotation**: Automatic log file rotation
- **Cache Management**: Intelligent cache cleanup
- **Resource Limits**: Set memory limits for components

#### Performance Monitoring
- **Response Time Tracking**: Monitor API response times
- **Resource Usage Alerts**: Alert on high resource usage
- **Performance Metrics**: Track system performance over time

## 🔍 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service logs
docker exec lora-pilot supervisorctl tail -100 controlpilot

# Check port availability
netstat -tulpn | grep :7878

# Restart service
docker exec lora-pilot supervisorctl restart controlpilot
```

#### Models Not Showing
```bash
# Check model directory
docker exec lora-pilot ls -la /workspace/models/

# Check model manifest
docker exec lora-pilot cat /opt/pilot/config/models.manifest

# Refresh model list
curl http://localhost:7878/api/models/refresh
```

#### Training Jobs Not Starting
```bash
# Check training service
docker exec lora-pilot supervisorctl status kohya
docker exec lora-pilot supervisorctl status ai-toolkit

# Check dataset availability
docker exec lora-pilot ls -la /workspace/datasets/images/

# Check model availability
docker exec lora-pilot ls -la /workspace/models/stable-diffusion/
```

### Debug Commands

#### Health Check
```bash
# API health check
curl http://localhost:7878/api/health

# Service status check
curl http://localhost:7878/api/services

# System information
curl http://localhost:7878/api/system/info
```

#### Log Analysis
```bash
# View ControlPilot logs
docker exec lora-pilot tail -f /workspace/logs/controlpilot.out.log

# Check for errors
docker exec lora-pilot grep -i error /workspace/logs/controlpilot.out.log

# Monitor resource usage
docker exec lora-pilot top -bn1 | head -20
```

## 🎯 Best Practices

### Service Management
1. **Start Services Gradually**: Start core services first
2. **Monitor Resources**: Keep an eye on GPU and memory usage
3. **Regular Restarts**: Restart services periodically for stability
4. **Log Management**: Regularly check and clean up logs

### Model Management
1. **Plan Storage**: Ensure sufficient disk space for models
2. **Organize Models**: Use consistent naming conventions
3. **Regular Cleanup**: Remove unused models to free space
4. **Backup Important Models**: Save trained models externally

### Training Workflows
1. **Test Small**: Start with small test datasets
2. **Monitor Progress**: Keep an eye on training progress
3. **Save Checkpoints**: Save training progress regularly
4. **Validate Results**: Test trained models before deployment

### System Maintenance
1. **Regular Updates**: Keep components updated
2. **Backup Configuration**: Save important configuration files
3. **Monitor Health**: Regularly check system health
4. **Performance Tuning**: Optimize settings based on usage patterns

---

*Last updated: 2025-02-11*
