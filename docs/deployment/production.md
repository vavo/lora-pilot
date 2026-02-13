# Production Deployment

This guide covers deploying LoRA Pilot in production environments, including scaling, security, monitoring, and maintenance considerations.

##  Production Overview

Production deployment of LoRA Pilot requires careful planning for:
- **Scalability**: Handling multiple users and workloads
- **Security**: Protecting models, data, and access
- **Reliability**: Ensuring high availability and uptime
- **Performance**: Optimizing for production workloads
- **Monitoring**: Tracking system health and usage

## 🏗️ Production Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Production Environment                    │
├─────────────────────────────────────────────────────────────┤
│  Load Balancer (Nginx/HAProxy)                              │
│  ├── SSL Termination                                         │
│  ├── Request Routing                                         │
│  └── Rate Limiting                                           │
├─────────────────────────────────────────────────────────────┤
│  Application Layer                                           │
│  ├── LoRA Pilot Instances (Multiple)                         │
│  ├── API Gateway                                             │
│  └── Service Discovery                                       │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ├── Shared Storage (NFS/S3)                                │
│  ├── Database (PostgreSQL)                                   │
│  └── Cache (Redis)                                           │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure                                             │
│  ├── Container Orchestration (Kubernetes/Docker Swarm)       │
│  ├── GPU Cluster                                             │
│  ├── Monitoring (Prometheus/Grafana)                         │
│  └── Logging (ELK Stack)                                    │
└─────────────────────────────────────────────────────────────┘
```

### Container Orchestration

#### Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lora-pilot
  labels:
    app: lora-pilot
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
      - name: lora-pilot
        image: vavo/lora-pilot:production
        ports:
        - containerPort: 7878
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: 1
          limits:
            memory: "32Gi"
            cpu: "8"
            nvidia.com/gpu: 1
        env:
        - name: TZ
          value: "UTC"
        - name: SUPERVISOR_ADMIN_PASSWORD
          valueFrom:
            secretKeyRef:
              name: lora-pilot-secrets
              key: admin-password
        volumeMounts:
        - name: workspace-storage
          mountPath: /workspace
        - name: model-storage
          mountPath: /workspace/models
      volumes:
      - name: workspace-storage
        persistentVolumeClaim:
          claimName: workspace-pvc
      - name: model-storage
        persistentVolumeClaim:
          claimName: models-pvc
```

#### Service Configuration
```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: lora-pilot-service
spec:
  selector:
    app: lora-pilot
  ports:
  - name: http
    port: 80
    targetPort: 7878
  type: ClusterIP
---
apiVersion: v1
kind: Service
metadata:
  name: lora-pilot-nodeport
spec:
  selector:
    app: lora-pilot
  ports:
  - name: http
    port: 7878
    nodePort: 30078
  type: NodePort
```

#### Ingress Configuration
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lora-pilot-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - lora-pilot.example.com
    secretName: lora-pilot-tls
  rules:
  - host: lora-pilot.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: lora-pilot-service
            port:
              number: 80
```

### Docker Swarm Deployment

#### Stack Configuration
```yaml
# docker-stack.yml
version: '3.8'

services:
  lora-pilot:
    image: vavo/lora-pilot:production
    deploy:
      replicas: 3
      resources:
        reservations:
          memory: 16G
          cpus: '4'
        limits:
          memory: 32G
          cpus: '8'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        monitor: 60s
        max_failure_ratio: 0.3
    environment:
      - TZ=UTC
      - SUPERVISOR_ADMIN_PASSWORD=${SUPERVISOR_ADMIN_PASSWORD}
    volumes:
      - workspace-data:/workspace
      - model-data:/workspace/models
    ports:
      - "7878:7878"
    networks:
      - lora-pilot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7878/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    deploy:
      replicas: 2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    networks:
      - lora-pilot-network
    depends_on:
      - lora-pilot

volumes:
  workspace-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs-server,rw
      device: ":/path/to/workspace"
  model-data:
    driver: local
    driver_opts:
      type: nfs
      o: addr=nfs-server,rw
      device: ":/path/to/models"

networks:
  lora-pilot-network:
    driver: overlay
    attachable: true
```

## 🔒 Security Configuration

### Authentication & Authorization

#### OAuth Integration
```python
# apps/Portal/auth/oauth.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://oauth.example.com/authorize",
    tokenUrl="https://oauth.example.com/token",
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from OAuth token"""
    user = await validate_oauth_token(token)
    if not user:
        raise HTTPException(401, "Invalid authentication")
    return user
```

#### Role-Based Access Control
```python
# apps/Portal/auth/rbac.py
from enum import Enum
from pydantic import BaseModel

class UserRole(str, Enum):
    ADMIN = "admin"
    TRAINER = "trainer"
    USER = "user"
    VIEWER = "viewer"

class User(BaseModel):
    id: str
    username: str
    role: UserRole
    permissions: List[str]

class PermissionManager:
    def __init__(self):
        self.role_permissions = {
            UserRole.ADMIN: ["*"],
            UserRole.TRAINER: ["train", "view_models", "manage_datasets"],
            UserRole.USER: ["view", "generate"],
            UserRole.VIEWER: ["view"],
        }
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has permission"""
        user_permissions = self.role_permissions.get(user.role, [])
        return "*" in user_permissions or permission in user_permissions
```

### Network Security

#### Firewall Configuration
```bash
# UFW firewall rules
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 7878/tcp   # Direct access to LoRA Pilot
ufw deny 5555/tcp   # Direct access to ComfyUI
ufw deny 6666/tcp   # Direct access to Kohya
ufw enable
```

#### Network Policies (Kubernetes)
```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: lora-pilot-netpol
spec:
  podSelector:
    matchLabels:
      app: lora-pilot
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 7878
  egress:
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

### Data Protection

#### Encryption at Rest
```yaml
# Kubernetes secret for sensitive data
apiVersion: v1
kind: Secret
metadata:
  name: lora-pilot-secrets
type: Opaque
data:
  admin-password: <base64-encoded-password>
  hf-token: <base64-encoded-hf-token>
  database-password: <base64-encoded-db-password>
```

#### Encryption in Transit
```nginx
# nginx.conf with SSL
server {
    listen 443 ssl http2;
    server_name lora-pilot.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://lora-pilot-service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

##  Monitoring & Logging

### Monitoring Stack

#### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'lora-pilot'
    static_configs:
      - targets: ['lora-pilot-service:7878']
    metrics_path: /api/metrics
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'gpu-exporter'
    static_configs:
      - targets: ['gpu-exporter:9445']
```

#### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "LoRA Pilot Production",
    "panels": [
      {
        "title": "Service Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"lora-pilot\"}"
          }
        ]
      },
      {
        "title": "GPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "nvidia_gpu_utilization_gpu"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{name=\"lora-pilot\"}"
          }
        ]
      }
    ]
  }
}
```

### Logging Stack

#### ELK Stack Configuration
```yaml
# logging/elasticsearch.yml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: elasticsearch
spec:
  serviceName: elasticsearch
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        env:
        - name: discovery.type
          value: single-node
        - name: ES_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
        ports:
        - containerPort: 9200
        volumeMounts:
        - name: elasticsearch-data
          mountPath: /usr/share/elasticsearch/data
  volumeClaimTemplates:
  - metadata:
      name: elasticsearch-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
```

#### Logstash Configuration
```ruby
# logging/logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "lora-pilot" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} - %{WORD:logger} - %{LOGLEVEL:level} - %{GREEDYDATA:message}" }
    }
    
    date {
      match => [ "timestamp", "ISO8601" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "lora-pilot-%{+YYYY.MM.dd}"
  }
}
```

##  Performance Optimization

### Resource Optimization

#### GPU Resource Management
```yaml
# GPU resource allocation
apiVersion: v1
kind: ResourceQuota
metadata:
  name: gpu-quota
spec:
  hard:
    requests.nvidia.com/gpu: "4"
    limits.nvidia.com/gpu: "8"
```

#### Memory Optimization
```python
# apps/Portal/utils/memory.py
import gc
import torch
from contextlib import contextmanager

@contextmanager
def memory_efficient_context():
    """Context manager for memory-efficient operations"""
    try:
        yield
    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

class MemoryManager:
    @staticmethod
    def get_memory_usage():
        """Get current memory usage"""
        return {
            'system_memory': psutil.virtual_memory().percent,
            'gpu_memory': torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        }
    
    @staticmethod
    def optimize_memory():
        """Optimize memory usage"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
```

### Caching Strategy

#### Redis Cache Configuration
```yaml
# cache/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
```

#### Cache Implementation
```python
# apps/Portal/cache/redis_cache.py
import redis
import json
from typing import Any, Optional

class RedisCache:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        value = self.redis_client.get(key)
        return json.loads(value) if value else None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache"""
        serialized_value = json.dumps(value)
        self.redis_client.setex(key, ttl, serialized_value)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        self.redis_client.delete(key)
    
    async def clear_pattern(self, pattern: str):
        """Clear keys matching pattern"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)
```

##  High Availability

### Multi-Zone Deployment

#### Kubernetes Multi-Zone
```yaml
# k8s/deployment-multi-zone.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lora-pilot
spec:
  replicas: 6
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - lora-pilot
              topologyKey: kubernetes.io/hostname
      nodeSelector:
        node-type: gpu
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
```

### Health Checks

#### Comprehensive Health Checks
```python
# apps/Portal/health/health_check.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter()

@router.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "resources": {},
        "version": get_app_version()
    }
    
    # Check services
    services = ["kohya", "comfyui", "invokeai", "ai-toolkit"]
    for service in services:
        try:
            status = await check_service_health(service)
            health_status["services"][service] = status
        except Exception as e:
            health_status["services"][service] = {"status": "error", "error": str(e)}
    
    # Check resources
    health_status["resources"] = await check_resource_health()
    
    # Determine overall health
    unhealthy_services = [
        service for service, status in health_status["services"].items()
        if status.get("status") != "healthy"
    ]
    
    if unhealthy_services:
        health_status["status"] = "degraded"
        if len(unhealthy_services) > len(services) / 2:
            health_status["status"] = "unhealthy"
    
    return health_status

async def check_service_health(service: str) -> Dict[str, Any]:
    """Check individual service health"""
    try:
        response = await httpx.get(f"http://localhost:{get_service_port(service)}/health")
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time": response.elapsed.total_seconds(),
            "last_check": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat()
        }
```

### Backup & Recovery

#### Automated Backup
```bash
#!/bin/bash
# scripts/backup.sh

set -e

BACKUP_DIR="/backups/lora-pilot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="lora-pilot-backup-$DATE"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup workspace
docker run --rm -v /workspace:/workspace -v "$BACKUP_DIR/$BACKUP_NAME":/backup \
  alpine tar czf /backup/workspace.tar.gz /workspace

# Backup database
docker exec postgres pg_dump -U postgres lora_pilot > "$BACKUP_DIR/$BACKUP_NAME/database.sql"

# Backup configurations
kubectl get configmaps -o yaml > "$BACKUP_DIR/$BACKUP_NAME/configmaps.yaml"
kubectl get secrets -o yaml > "$BACKUP_DIR/$BACKUP_NAME/secrets.yaml"

# Upload to cloud storage
aws s3 cp "$BACKUP_DIR/$BACKUP_NAME" s3://lora-pilot-backups/ --recursive

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -type d -name "lora-pilot-backup-*" -mtime +7 -exec rm -rf {} +

echo "Backup completed: $BACKUP_NAME"
```

#### Recovery Script
```bash
#!/bin/bash
# scripts/recover.sh

set -e

BACKUP_NAME=$1
BACKUP_DIR="/backups/lora-pilot"

if [ -z "$BACKUP_NAME" ]; then
    echo "Usage: $0 <backup-name>"
    exit 1
fi

# Download backup from cloud storage
aws s3 cp s3://lora-pilot-backups/$BACKUP_NAME "$BACKUP_DIR/" --recursive

# Stop services
kubectl scale deployment lora-pilot --replicas=0

# Restore workspace
docker run --rm -v /workspace:/workspace -v "$BACKUP_DIR/$BACKUP_NAME":/backup \
  alpine tar xzf /backup/workspace.tar.gz -C /

# Restore database
docker exec -i postgres psql -U postgres lora_pilot < "$BACKUP_DIR/$BACKUP_NAME/database.sql"

# Restore configurations
kubectl apply -f "$BACKUP_DIR/$BACKUP_NAME/configmaps.yaml"
kubectl apply -f "$BACKUP_DIR/$BACKUP_NAME/secrets.yaml"

# Start services
kubectl scale deployment lora-pilot --replicas=3

echo "Recovery completed: $BACKUP_NAME"
```

##  Maintenance Procedures

### Rolling Updates

#### Zero-Downtime Deployment
```yaml
# k8s/rolling-update.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lora-pilot
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: lora-pilot
        image: vavo/lora-pilot:v2.1.0
        readinessProbe:
          httpGet:
            path: /api/health
            port: 7878
          initialDelaySeconds: 30
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /api/health
            port: 7878
          initialDelaySeconds: 60
          periodSeconds: 30
```

### Maintenance Windows

#### Scheduled Maintenance
```python
# apps/Portal/maintenance/scheduler.py
import asyncio
from datetime import datetime, time

class MaintenanceScheduler:
    def __init__(self):
        self.maintenance_windows = [
            {"day": 0, "start": "02:00", "end": "04:00"},  # Sunday 2-4 AM
            {"day": 3, "start": "03:00", "end": "05:00"},  # Wednesday 3-5 AM
        ]
    
    async def schedule_maintenance(self, task: callable, scheduled_time: datetime):
        """Schedule maintenance task"""
        while datetime.now() < scheduled_time:
            await asyncio.sleep(60)
        
        await task()
    
    def is_maintenance_window(self) -> bool:
        """Check if currently in maintenance window"""
        now = datetime.now()
        current_day = now.weekday()
        current_time = now.time()
        
        for window in self.maintenance_windows:
            if window["day"] == current_day:
                start_time = time.fromisoformat(window["start"])
                end_time = time.fromisoformat(window["end"])
                if start_time <= current_time <= end_time:
                    return True
        
        return False
```

### Performance Tuning

#### Database Optimization
```sql
-- Database performance optimizations
-- Create indexes for frequently queried fields
CREATE INDEX CONCURRENTLY idx_training_jobs_status ON training_jobs(status);
CREATE INDEX CONCURRENTLY idx_models_created_at ON models(created_at);

-- Partition large tables
CREATE TABLE training_logs_partitioned (
    LIKE training_logs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM training_jobs WHERE status = 'running';
```

#### Application Optimization
```python
# apps/Portal/utils/performance.py
import asyncio
from functools import wraps
from time import time

def performance_monitor(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper

class ConnectionPool:
    def __init__(self, max_connections: int = 100):
        self.semaphore = asyncio.Semaphore(max_connections)
        self.connections = []
    
    async def get_connection(self):
        await self.semaphore.acquire()
        return self.connections.pop() if self.connections else await self.create_connection()
    
    async def release_connection(self, connection):
        self.connections.append(connection)
        self.semaphore.release()
```

##  Troubleshooting

### Common Production Issues

#### Service Discovery Problems
```bash
# Check service connectivity
kubectl exec -it lora-pilot-pod -- nslookup lora-pilot-service
kubectl exec -it lora-pilot-pod -- curl http://lora-pilot-service:7878/api/health

# Check DNS resolution
kubectl exec -it lora-pilot-pod -- nslookup kubernetes.default.svc.cluster.local
```

#### GPU Resource Issues
```bash
# Check GPU allocation
kubectl describe node | grep -A 10 "nvidia.com/gpu"

# Check GPU usage in pod
kubectl exec -it lora-pilot-pod -- nvidia-smi

# Check GPU metrics
kubectl top nodes --use-protocol-builtin
```

#### Storage Issues
```bash
# Check PVC status
kubectl get pvc
kubectl describe pvc workspace-pvc

# Check storage class
kubectl get storageclass
kubectl describe storageclass standard
```

### Debug Tools

#### Debug Container
```bash
# Debug container with all tools
kubectl run debug-container --image=nicolaka/netshoot --rm -it -- bash

# Network debugging
kubectl exec -it debug-container -- ping lora-pilot-service
kubectl exec -it debug-container -- telnet lora-pilot-service 7878
```

#### Performance Profiling
```python
# apps/Portal/utils/profiler.py
import cProfile
import pstats
from io import StringIO

def profile_function(func):
    """Profile function performance"""
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        
        s = StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(10)
        
        logger.info(f"Profile for {func.__name__}:\n{s.getvalue()}")
        return result
    return wrapper
```

##  SLA and Monitoring

### Service Level Agreement

#### SLA Metrics
```yaml
# sla/definition.yaml
service: lora-pilot
version: 1.0
sla:
  availability: 99.9%
  response_time:
    p50: 200ms
    p95: 500ms
    p99: 1000ms
  error_rate: 0.1%
  recovery_time: 5m
```

#### SLA Monitoring
```python
# apps/Portal/monitoring/sla.py
from datetime import datetime, timedelta
from typing import Dict, List

class SLAMonitor:
    def __init__(self):
        self.metrics = {
            'availability': 0.0,
            'response_times': [],
            'error_count': 0,
            'total_requests': 0
        }
    
    def record_request(self, response_time: float, status_code: int):
        """Record request metrics"""
        self.metrics['response_times'].append(response_time)
        self.metrics['total_requests'] += 1
        
        if status_code >= 500:
            self.metrics['error_count'] += 1
    
    def calculate_sla_metrics(self) -> Dict[str, float]:
        """Calculate SLA metrics"""
        total_requests = self.metrics['total_requests']
        if total_requests == 0:
            return {'availability': 0.0, 'error_rate': 0.0}
        
        error_rate = self.metrics['error_count'] / total_requests
        
        response_times = sorted(self.metrics['response_times'])
        n = len(response_times)
        
        return {
            'availability': self.metrics['availability'],
            'error_rate': error_rate,
            'p50_response_time': response_times[n // 2] if n > 0 else 0,
            'p95_response_time': response_times[int(n * 0.95)] if n > 0 else 0,
            'p99_response_time': response_times[int(n * 0.99)] if n > 0 else 0
        }
```

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


