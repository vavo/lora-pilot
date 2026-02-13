# Architecture

LoRA Pilot is built as a comprehensive, containerized AI workspace that integrates multiple diffusion model tools into a unified system. This document outlines the system architecture, component relationships, and design principles.

## 🏗️ System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LoRA Pilot System                        │
├─────────────────────────────────────────────────────────────┤
│  ControlPilot (FastAPI/React)                               │
│  ├── Service Management (Supervisor)                        │
│  ├── Model Management                                       │
│  ├── Dataset Tools                                          │
│  └── API Gateway                                           │
├─────────────────────────────────────────────────────────────┤
│  Training Stack                                             │
│  ├── Kohya SS (Flask/React)                                │
│  ├── AI Toolkit (Next.js/Gradio)                           │
│  └── Diffusion Pipe (Python/TensorBoard)                   │
├─────────────────────────────────────────────────────────────┤
│  Inference Stack                                            │
│  ├── ComfyUI (React/WebGL)                                  │
│  └── InvokeAI (React/FastAPI)                               │
├─────────────────────────────────────────────────────────────┤
│  Management Tools                                           │
│  ├── TrainPilot (Python/CLI)                                │
│  ├── TagPilot (React/FastAPI)                               │
│  ├── MediaPilot (React/FastAPI)                             │
│  └── Copilot Sidecar (FastAPI)                              │
├─────────────────────────────────────────────────────────────┤
│  Development Environment                                     │
│  ├── JupyterLab (Python/Jupyter)                            │
│  └── Code Server (VS Code)                                  │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure                                             │
│  ├── Docker Containers                                       │
│  ├── Supervisor (Process Management)                        │
│  ├── Nginx (Reverse Proxy)                                  │
│  └── Shared Workspace (/workspace)                           │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Containerization**: All components run in Docker containers
2. **Service Isolation**: Each component is an independent service
3. **Shared Resources**: Common workspace and model storage
4. **API Integration**: Components communicate via REST APIs
5. **Process Management**: Supervisor manages all services
6. **Persistent Storage**: All data persists in /workspace

## 🐳 Container Architecture

### Container Organization

```
lora-pilot (Main Container)
├── ControlPilot (Port 7878)
│   ├── FastAPI Backend
│   └── React Frontend
├── Kohya SS (Port 6666)
│   ├── Flask Backend
│   └── React Frontend
├── AI Toolkit (Port 8675)
│   ├── Next.js Frontend
│   └── Gradio Backend
├── ComfyUI (Port 5555)
│   ├── React Frontend
│   └── Python Backend
├── InvokeAI (Port 9090)
│   ├── React Frontend
│   └── FastAPI Backend
├── JupyterLab (Port 8888)
├── Code Server (Port 8443)
├── TrainPilot (CLI Tool)
├── TagPilot (Integrated)
├── MediaPilot (Integrated)
└── Copilot Sidecar (Port 7879)
```

### Container Networking

#### Internal Network
```yaml
# Docker Compose Network
networks:
  lora-pilot-net:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### Service Communication
```yaml
# Services communicate via localhost
# All services share the same network namespace
# API calls use localhost:port
# File sharing via /workspace volume
```

### Volume Management

#### Persistent Volumes
```yaml
volumes:
  # Main workspace
  - ./workspace:/workspace
  
  # Model storage
  - ./models:/workspace/models
  
  # Configuration
  - ./config:/workspace/config
  
  # Logs
  - ./logs:/workspace/logs
```

#### Temporary Volumes
```yaml
# Temporary storage
  - /tmp:/tmp
  
  # Cache storage
  - /cache:/workspace/cache
  
  # Build artifacts
  - /build:/workspace/build
```

##  Service Architecture

### Supervisor Configuration

#### Service Definitions
```ini
[program:controlpilot]
directory=/workspace
autostart=true
autorestart=true
startsecs=5
stdout_logfile=/workspace/logs/controlpilot.out.log
stderr_logfile=/workspace/logs/controlpilot.err.log
command=/bin/bash -lc 'source /opt/venvs/core/bin/activate && cd /workspace/apps/Portal && python app.py'

[program:kohya]
directory=/workspace
autostart=true
autorestart=true
startsecs=10
stdout_logfile=/workspace/logs/kohya.out.log
stderr_logfile=/workspace/logs/kohya.err.log
command=/bin/bash -lc 'source /opt/venvs/core/bin/activate && cd /workspace/apps/kohya && python gui.py --listen 0.0.0.0 --port 6666'

[program:comfyui]
directory=/workspace
autostart=true
autorestart=true
startsecs=5
stdout_logfile=/workspace/logs/comfyui.out.log
stderr_logfile=/workspace/logs/comfyui.err.log
command=/bin/bash -lc 'source /opt/venvs/core/bin/activate && cd /workspace/apps/comfy && python main.py --listen 0.0.0.0 --port 5555'
```

#### Service Dependencies
```ini
# Service startup order
[program:controlpilot]
priority=100

[program:kohya]
priority=200
depends_on=controlpilot

[program:comfyui]
priority=300
depends_on=controlpilot
```

### API Gateway

#### ControlPilot as Gateway
```python
# ControlPilot API routes
@app.get("/api/services")
async def get_services():
    """List all services and their status"""
    return supervisor_status()

@app.get("/api/models")
async def get_models():
    """List available models"""
    return scan_models_directory()

@app.post("/api/services/{service}/start")
async def start_service(service: str):
    """Start a specific service"""
    return supervisor_start_service(service)
```

#### Service Integration
```python
# Service communication
class ServiceManager:
    def __init__(self):
        self.services = {
            'kohya': 'http://localhost:6666',
            'comfyui': 'http://localhost:5555',
            'invokeai': 'http://localhost:9090',
            'ai-toolkit': 'http://localhost:8675'
        }
    
    async def call_service(self, service: str, endpoint: str):
        """Make API call to specific service"""
        url = f"{self.services[service]}{endpoint}"
        return await httpx.get(url)
```

##  Data Architecture

### Workspace Structure

```
/workspace/
├── datasets/                   # Training datasets
│   ├── images/                # Image datasets
│   │   ├── 1_dataset_name/
│   │   │   ├── images/
│   │   │   └── captions/
│   │   └── 2_another_dataset/
│   └── processed/            # Processed datasets
├── outputs/                   # Training outputs
│   ├── kohya/                # Kohya outputs
│   ├── ai-toolkit/           # AI Toolkit outputs
│   └── diffusion-pipe/       # Diffusion Pipe outputs
├── models/                    # Model storage
│   ├── stable-diffusion/     # Base models
│   ├── lora/                  # LoRA models
│   ├── controlnet/            # ControlNet models
│   └── vae/                   # VAE models
├── cache/                     # Cache storage
│   ├── latents/              # Latent cache
│   ├── embeddings/           # Embedding cache
│   └── temp/                 # Temporary cache
├── config/                    # Configuration files
│   ├── ai-toolkit/           # AI Toolkit config
│   ├── jupyter/              # Jupyter config
│   └── supervisor/           # Supervisor config
├── logs/                      # Log files
│   ├── controlpilot/         # ControlPilot logs
│   ├── kohya/                # Kohya logs
│   └── comfyui/              # ComfyUI logs
└── home/                      # User home directory
    ├── .config/              # User config
    └── .cache/               # User cache
```

### Data Flow

#### Training Data Flow
```
Dataset Creation → TagPilot → Dataset Storage → Training Stack → Model Output → Inference Stack
```

#### Model Data Flow
```
Model Download → Model Storage → Component Integration → Training/Inference → Result Storage
```

#### API Data Flow
```
Client Request → ControlPilot API → Service API → Data Processing → Response → Client
```

## 🧩 Component Integration

### Model Integration

#### Shared Model Storage
```python
# Model discovery system
class ModelManager:
    def __init__(self):
        self.model_paths = {
            'stable-diffusion': '/workspace/models/stable-diffusion',
            'lora': '/workspace/models/lora',
            'controlnet': '/workspace/models/controlnet'
        }
    
    def scan_models(self):
        """Scan and index all models"""
        models = {}
        for category, path in self.model_paths.items():
            models[category] = self.scan_directory(path)
        return models
    
    def get_model_info(self, model_path: str):
        """Get detailed model information"""
        return {
            'path': model_path,
            'size': os.path.getsize(model_path),
            'type': self.detect_model_type(model_path),
            'metadata': self.extract_metadata(model_path)
        }
```

#### Component Model Access
```python
# Each component accesses models through shared paths
# Kohya SS: /workspace/models/stable-diffusion/
# ComfyUI: /workspace/models/ (all types)
# AI Toolkit: /workspace/models/stable-diffusion/
```

### Dataset Integration

#### Dataset Management
```python
# Dataset shared between components
class DatasetManager:
    def __init__(self):
        self.dataset_path = '/workspace/datasets/images/'
    
    def create_dataset(self, name: str, images: List[str]):
        """Create new dataset"""
        dataset_dir = f"{self.dataset_path}/1_{name}"
        os.makedirs(dataset_dir, exist_ok=True)
        return dataset_dir
    
    def get_datasets(self):
        """List all datasets"""
        return [d for d in os.listdir(self.dataset_path) if d.startswith('1_')]
```

#### Component Dataset Access
```python
# TagPilot creates datasets
# Training stacks use datasets
# All components access same dataset directory
```

### Service Integration

#### Service Discovery
```python
# Service discovery and health checking
class ServiceRegistry:
    def __init__(self):
        self.services = {
            'controlpilot': {'port': 7878, 'health': '/api/health'},
            'kohya': {'port': 6666, 'health': '/'},
            'comfyui': {'port': 5555, 'health': '/system_stats'},
            'invokeai': {'port': 9090, 'health': '/api/v1/session'}
        }
    
    async def check_health(self, service: str):
        """Check service health"""
        config = self.services[service]
        try:
            response = await httpx.get(f"http://localhost:{config['port']}{config['health']}")
            return response.status_code == 200
        except:
            return False
```

#### Service Communication
```python
# Inter-service communication
class ServiceCommunicator:
    def __init__(self):
        self.base_urls = {
            'kohya': 'http://localhost:6666',
            'comfyui': 'http://localhost:5555',
            'invokeai': 'http://localhost:9090'
        }
    
    async def call_service(self, service: str, endpoint: str, data: dict = None):
        """Make API call to service"""
        url = f"{self.base_urls[service]}{endpoint}"
        if data:
            return await httpx.post(url, json=data)
        else:
            return await httpx.get(url)
```

## 🔒 Security Architecture

### Container Security

#### Isolation
```yaml
# Container isolation
security_opt:
  - no-new-privileges:true
read_only: false  # Required for /workspace
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

#### User Management
```dockerfile
# Non-root user
RUN useradd -m -u 1000 pilot
USER pilot
```

### Network Security

#### Port Management
```yaml
# Only expose necessary ports
ports:
  - "7878:7878"      # ControlPilot
  - "5555:5555"      # ComfyUI
  - "6666:6666"      # Kohya SS
  - "9090:9090"      # InvokeAI
  - "8888:8888"      # JupyterLab
  - "8443:8443"      # Code Server
  - "8675:8675"      # AI Toolkit
```

#### Access Control
```python
# API authentication
class SecurityMiddleware:
    def __init__(self):
        self.admin_password = os.getenv('SUPERVISOR_ADMIN_PASSWORD')
    
    async def authenticate(self, request: Request):
        """Authenticate API requests"""
        auth_header = request.headers.get('Authorization')
        if not self.validate_token(auth_header):
            raise HTTPException(401, "Unauthorized")
```

### Data Security

#### File Permissions
```bash
# Secure file permissions
chmod 755 /workspace
chmod 644 /workspace/models/*
chmod 600 /workspace/config/*.conf
```

#### Environment Variable Security
```bash
# Sensitive data in environment variables
HF_TOKEN=your_token_here
SUPERVISOR_ADMIN_PASSWORD=secure_password
```

##  Performance Architecture

### Resource Management

#### GPU Management
```python
# GPU resource allocation
class GPUManager:
    def __init__(self):
        self.gpu_memory = self.get_gpu_memory()
        self.allocations = {}
    
    def allocate_gpu(self, service: str, memory_gb: int):
        """Allocate GPU memory to service"""
        if self.get_available_memory() >= memory_gb:
            self.allocations[service] = memory_gb
            return True
        return False
    
    def get_available_memory(self):
        """Get available GPU memory"""
        total = self.gpu_memory
        allocated = sum(self.allocations.values())
        return total - allocated
```

#### Memory Management
```python
# Memory optimization
class MemoryManager:
    def __init__(self):
        self.memory_limit = self.get_system_memory()
    
    def optimize_memory(self):
        """Optimize memory usage"""
        # Clear caches
        self.clear_model_cache()
        # Garbage collect
        gc.collect()
        # Optimize tensors
        torch.cuda.empty_cache()
```

### Caching Architecture

#### Model Caching
```python
# Model loading cache
class ModelCache:
    def __init__(self):
        self.cache = {}
        self.max_size = 5  # Max cached models
    
    def get_model(self, model_path: str):
        """Get model from cache"""
        if model_path in self.cache:
            return self.cache[model_path]
        model = self.load_model(model_path)
        self.cache_model(model_path, model)
        return model
    
    def cache_model(self, path: str, model):
        """Cache model if space available"""
        if len(self.cache) >= self.max_size:
            self.evict_oldest()
        self.cache[path] = model
```

#### Dataset Caching
```python
# Dataset processing cache
class DatasetCache:
    def __init__(self):
        self.cache_dir = '/workspace/cache/datasets'
    
    def cache_latents(self, dataset_path: str, latents: np.ndarray):
        """Cache processed latents"""
        cache_file = f"{self.cache_dir}/{dataset_path}.npy"
        np.save(cache_file, latents)
    
    def get_cached_latents(self, dataset_path: str):
        """Get cached latents"""
        cache_file = f"{self.cache_dir}/{dataset_path}.npy"
        if os.path.exists(cache_file):
            return np.load(cache_file)
        return None
```

##  Scalability Architecture

### Horizontal Scaling

#### Service Scaling
```yaml
# Docker Compose scaling
services:
  kohya:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

#### Load Balancing
```python
# Load balancer for multiple instances
class LoadBalancer:
    def __init__(self, services: List[str]):
        self.services = services
        self.current_index = 0
    
    def get_next_service(self):
        """Get next service instance"""
        service = self.services[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.services)
        return service
```

### Vertical Scaling

#### Resource Scaling
```yaml
# Resource scaling based on workload
services:
  lora-pilot:
    deploy:
      resources:
        reservations:
          memory: 16G
          cpus: '8'
        limits:
          memory: 64G
          cpus: '16'
```

#### Dynamic Resource Allocation
```python
# Dynamic resource allocation
class ResourceScaler:
    def __init__(self):
        self.monitor = ResourceMonitor()
    
    async def scale_resources(self):
        """Scale resources based on demand"""
        usage = self.monitor.get_usage()
        if usage.gpu > 0.8:
            await self.scale_up()
        elif usage.gpu < 0.2:
            await self.scale_down()
```

##  Monitoring Architecture

### Health Monitoring

#### Service Health
```python
# Health monitoring system
class HealthMonitor:
    def __init__(self):
        self.services = self.get_service_list()
    
    async def check_all_services(self):
        """Check health of all services"""
        health_status = {}
        for service in self.services:
            health_status[service] = await self.check_service_health(service)
        return health_status
    
    async def check_service_health(self, service: str):
        """Check individual service health"""
        try:
            response = await self.ping_service(service)
            return {
                'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                'response_time': response.elapsed.total_seconds(),
                'last_check': datetime.now()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'last_check': datetime.now()
            }
```

#### Performance Monitoring
```python
# Performance metrics collection
class PerformanceMonitor:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    async def collect_metrics(self):
        """Collect performance metrics"""
        return {
            'gpu_usage': self.get_gpu_usage(),
            'memory_usage': self.get_memory_usage(),
            'disk_usage': self.get_disk_usage(),
            'network_usage': self.get_network_usage(),
            'service_response_times': self.get_response_times()
        }
```

### Logging Architecture

#### Structured Logging
```python
# Structured logging system
class StructuredLogger:
    def __init__(self):
        self.logger = logging.getLogger('lora-pilot')
        self.setup_logging()
    
    def setup_logging(self):
        """Setup structured logging"""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_event(self, event: str, level: str, **kwargs):
        """Log structured event"""
        log_data = {
            'event': event,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        getattr(self.logger, level)(json.dumps(log_data))
```

#### Log Aggregation
```python
# Log aggregation system
class LogAggregator:
    def __init__(self):
        self.log_sources = [
            '/workspace/logs/controlpilot',
            '/workspace/logs/kohya',
            '/workspace/logs/comfyui'
        ]
    
    async def aggregate_logs(self, service: str, lines: int = 100):
        """Aggregate logs from service"""
        log_file = f"/workspace/logs/{service}/{service}.out.log"
        return await self.read_log_file(log_file, lines)
```

## 🔮 Future Architecture

### Microservices Transition

#### Service Decomposition
```yaml
# Future microservices architecture
services:
  api-gateway:
    # Central API gateway
  model-service:
    # Model management service
  training-service:
    # Training orchestration service
  inference-service:
    # Inference management service
  dataset-service:
    # Dataset management service
```

#### Event-Driven Architecture
```python
# Event-driven communication
class EventBus:
    def __init__(self):
        self.subscribers = {}
    
    async def publish(self, event: str, data: dict):
        """Publish event to subscribers"""
        for subscriber in self.subscribers.get(event, []):
            await subscriber.handle_event(data)
    
    def subscribe(self, event: str, handler):
        """Subscribe to event"""
        if event not in self.subscribers:
            self.subscribers[event] = []
        self.subscribers[event].append(handler)
```

### Cloud Native Architecture

#### Kubernetes Deployment
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lora-pilot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lora-pilot
  template:
    metadata:
      labels:
        app: lora-pilot
    spec:
      containers:
      - name: controlpilot
        image: vavo/lora-pilot:latest
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: 1
```

#### Cloud Storage Integration
```python
# Cloud storage integration
class CloudStorageManager:
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    async def sync_to_cloud(self, local_path: str, cloud_path: str):
        """Sync local storage to cloud"""
        for root, dirs, files in os.walk(local_path):
            for file in files:
                local_file = os.path.join(root, file)
                cloud_file = os.path.join(cloud_path, file)
                await self.upload_file(local_file, cloud_file)
```

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


