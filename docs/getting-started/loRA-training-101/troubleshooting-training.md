# Troubleshooting Training

Training problems can be frustrating, but most issues have clear solutions. This guide covers common training problems and their fixes.

##  Overview

### Why Troubleshooting Matters

Think of troubleshooting like medical diagnosis:
- **Symptoms**: What you observe going wrong
- **Diagnosis**: Understanding the root cause
- **Treatment**: Applying the right fix
- **Prevention**: Avoiding future issues

### The Troubleshooting Formula

```
Problem Identification + Root Cause Analysis + Correct Solution = Fixed Training
     ↓                    ↓                    ↓                    ↓
Observe Issue + Understand Why + Apply Fix = Success
```

---

##  Common Training Issues

### Training Won't Start

#### Symptoms
- Training process fails to initialize
- Error messages during startup
- Tools won't open or configure
- Progress bar stuck at 0%

#### Common Causes
- **Missing Dependencies**: Required software not installed
- **Permission Issues**: Insufficient file or directory permissions
- **Path Problems**: Incorrect file paths or missing files
- **Resource Conflicts**: Other processes using required resources

#### Solutions

**Check Dependencies**
```bash
# Check Python packages
pip list | grep -E "(torch|diffusers|accelerate)"

# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Check model files
ls -la /path/to/model/
```

**Fix Permissions**
```bash
# Fix directory permissions
chmod 755 /path/to/dataset/
chmod 644 /path/to/dataset/*

# Fix ownership if needed
sudo chown -R user:group /path/to/dataset/
```

**Verify Paths**
- Check all file paths in configuration
- Ensure dataset directory exists
- Verify model file is accessible
- Check for special characters in paths

---

### Out of Memory Errors

#### Symptoms
- CUDA out of memory errors
- Training crashes with memory errors
- GPU memory usage spikes to 100%
- System becomes unresponsive during training

#### Common Causes
- **Batch Size Too Large**: Too many samples processed at once
- **High Resolution**: Images too large for available VRAM
- **Model Too Big**: Base model requires more memory than available
- **Memory Leaks**: Previous processes still using memory

#### Solutions

**Reduce Batch Size**
- Start with batch size 1
- Gradually increase if memory allows
- Monitor memory usage during training

**Lower Resolution**
```
# Reduce image resolution
SD1.5: Use 512x512 instead of 768x768
SDXL: Use 1024x1024 instead of 1280x1280
```

**Enable Memory Optimization**
- Enable gradient checkpointing
- Use mixed precision training (FP16/BF16)
- Reduce network rank/dimension

**Clear Memory**
```bash
# Clear GPU memory between runs
python -c "import torch; torch.cuda.empty_cache()"

# Restart training process
pkill -f python
```

---

### Poor Training Quality

#### Symptoms
- Generated samples look poor quality
- Model doesn't learn training concepts
- Results are inconsistent or blurry
- Overfitting to training data

#### Common Causes
- **Poor Dataset Quality**: Low-quality or inconsistent images
- **Inadequate Captions**: Vague or inaccurate descriptions
- **Wrong Parameters**: Learning rate too high/low, steps insufficient
- **Insufficient Data**: Not enough training examples

#### Solutions

**Improve Dataset Quality**
- Remove low-quality or blurry images
- Ensure consistent lighting and focus
- Check for compression artifacts
- Verify subject consistency across dataset

**Enhance Captions**
- Make captions more descriptive and specific
- Include style and quality descriptors
- Ensure captions accurately match images
- Use consistent terminology

**Adjust Training Parameters**
```
# Conservative learning rate
learning_rate: 1e-4  # Start here
learning_rate: 5e-5  # If still unstable
learning_rate: 1e-5  # For stable training

# Increase training steps
steps: 1500-2000  # Basic training
steps: 3000-4000  # High quality training
```

**Add More Data**
- Collect more high-quality training images
- Ensure variety in poses, lighting, contexts
- Aim for at least 20-30 images for basic training
- Use 50+ images for high-quality results

---

### Overfitting Issues

#### Symptoms
- Model only reproduces training images
- Poor generalization to new prompts
- Results look like copies of training data
- Loss continues to decrease but quality doesn't improve

#### Common Causes
- **Too Many Training Steps**: Model memorizes training data
- **Learning Rate Too High**: Model learns too quickly
- **Dataset Too Small**: Not enough variety to generalize
- **Too Similar Data**: Training images too similar

#### Solutions

**Reduce Training Steps**
- Stop training when validation loss starts increasing
- Use early stopping based on validation performance
- Aim for 1000-2000 steps for most cases
- Monitor loss curves for overfitting signs

**Lower Learning Rate**
```
# Progressive learning rate reduction
initial_lr: 1e-4
mid_training_lr: 5e-5
final_lr: 1e-5
```

**Increase Dataset Variety**
- Add more diverse training images
- Include different poses, angles, lighting
- Vary backgrounds and contexts
- Ensure subject appears in different situations

**Use Regularization**
- Add weight decay to training parameters
- Use dropout if supported by training tool
- Implement data augmentation
- Use validation set to monitor generalization

---

### Training Instability

#### Symptoms
- Training loss jumps around erratically
- Model performance varies wildly between steps
- Training crashes randomly
- Generated samples are inconsistent

#### Common Causes
- **Learning Rate Too High**: Model can't converge properly
- **Inconsistent Data**: Quality varies too much across dataset
- **Hardware Issues**: GPU overheating or power supply problems
- **Software Conflicts**: Multiple processes competing for resources

#### Solutions

**Stabilize Learning Rate**
```
# Use learning rate scheduler
scheduler: "cosine"  # Smooth decay
scheduler: "linear"   # Predictable decay
scheduler: "polynomial" # Gentle decay

# Use warmup
warmup_steps: 100  # Gradual increase
```

**Improve Data Consistency**
- Standardize image quality across dataset
- Ensure consistent lighting and color balance
- Remove outlier images that are too different
- Use consistent captioning style

**Check Hardware**
- Monitor GPU temperature during training
- Ensure adequate power supply
- Check for memory errors in system logs
- Use monitoring tools to track hardware health

---

##  Advanced Issues

### Model Corruption

#### Symptoms
- Trained model file is corrupted or won't load
- Model produces garbage or random noise
- Training crashes and corrupts output files
- Model size is abnormal (too large/small)

#### Common Causes
- **Training Interruption**: Power loss or system crash during save
- **Disk Space Issues**: Insufficient space for model files
- **File System Errors**: Disk corruption or permission issues
- **Software Bugs**: Training tool has bugs affecting model saving

#### Solutions

**Regular Backups**
- Save checkpoints every 100-500 steps
- Use multiple backup locations
- Verify checkpoint integrity after saving
- Keep earlier versions as fallbacks

**Monitor Disk Space**
- Ensure adequate free space before training
- Monitor disk usage during training
- Clean up temporary files regularly
- Use external storage for large models

**Verify Model Files**
```python
# Check model integrity
import torch
model = torch.load("path/to/model.safetensors")
print(f"Model keys: {list(model.keys())}")

# Check model size
import os
size_bytes = os.path.getsize("path/to/model.safetensors")
size_mb = size_bytes / (1024 * 1024)
print(f"Model size: {size_mb:.2f} MB")
```

### Performance Issues

#### Symptoms
- Training is extremely slow
- GPU utilization is very low
- Memory usage is inefficient
- Training takes much longer than expected

#### Common Causes
- **CPU Bottlenecks**: Data loading limited by CPU
- **Inefficient Data Loading**: Poor data pipeline performance
- **Suboptimal Settings**: Non-optimal training parameters
- **Hardware Limitations**: Hardware not optimized for training

#### Solutions

**Optimize Data Loading**
- Use faster storage (SSD) for dataset
- Implement data prefetching and caching
- Use multiple data loader workers
- Optimize image preprocessing pipeline

**Improve GPU Utilization**
- Increase batch size if memory allows
- Use mixed precision training
- Enable gradient accumulation for effective larger batches
- Check GPU is not thermal throttling

**Profile Training**
```python
# Profile training performance
import torch.profiler

with torch.profiler.profile() as prof:
    # Training code here
    pass

# Export profile for analysis
prof.export_chrome_trace("trace.json")
```

---

## 💡 Diagnostic Tools

### Monitoring Scripts

#### Training Monitor
```python
import time
import psutil
import GPUtil

class TrainingMonitor:
    def __init__(self):
        self.start_time = time.time()
        
    def check_system(self):
        """Check system resources"""
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        gpu = GPUtil.getGPUs()[0]
        
        return {
            'cpu': cpu_percent,
            'memory': memory.percent,
            'gpu_memory': gpu.memoryUtil * 100,
            'gpu_temp': gpu.temperature
        }
        
    def log_status(self, step, loss):
        """Log training status"""
        status = self.check_system()
        elapsed = time.time() - self.start_time
        
        print(f"Step {step}: Loss={loss:.6f}, "
              f"CPU={status['cpu']:.1f}%, "
              f"RAM={status['memory']:.1f}%, "
              f"GPU={status['gpu_memory']:.1f}%, "
              f"Time={elapsed:.1f}s")

# Usage
monitor = TrainingMonitor()
# Call monitor.log_status(step, loss) during training
```

#### Loss Analyzer
```python
import matplotlib.pyplot as plt

def analyze_training_loss(loss_file):
    """Analyze training loss curve"""
    with open(loss_file, 'r') as f:
        losses = [float(line.strip()) for line in f]
    
    plt.figure(figsize=(10, 6))
    plt.plot(losses)
    plt.title('Training Loss Over Time')
    plt.xlabel('Training Step')
    plt.ylabel('Loss')
    plt.grid(True)
    plt.show()
    
    # Detect overfitting
    if len(losses) > 100:
        recent_avg = sum(losses[-50:]) / 50
        overall_avg = sum(losses) / len(losses)
        if recent_avg > overall_avg * 1.1:
            print("Warning: Possible overfitting detected")
```

### Health Check Scripts

#### Dataset Validator
```python
import os
from PIL import Image

def validate_dataset(dataset_path):
    """Validate dataset for common issues"""
    issues = []
    
    # Check file existence
    img_dir = os.path.join(dataset_path, 'images')
    cap_dir = os.path.join(dataset_path, 'captions')
    
    if not os.path.exists(img_dir):
        issues.append("Images directory missing")
    if not os.path.exists(cap_dir):
        issues.append("Captions directory missing")
    
    # Check image-caption pairs
    images = [f for f in os.listdir(img_dir) if f.endswith(('.jpg', '.png'))]
    for img in images[:5]:  # Check first 5 images
        base_name = os.path.splitext(img)[0]
        cap_file = os.path.join(cap_dir, f"{base_name}.txt")
        
        if not os.path.exists(cap_file):
            issues.append(f"Missing caption for {img}")
            continue
            
        # Check image quality
        img_path = os.path.join(img_dir, img)
        try:
            with Image.open(img_path) as image:
                if image.size[0] < 512 or image.size[1] < 512:
                    issues.append(f"Low resolution: {img}")
        except Exception as e:
            issues.append(f"Corrupted image: {img} - {str(e)}")
    
    return issues

# Usage
issues = validate_dataset("/path/to/dataset")
for issue in issues:
    print(f"Issue: {issue}")
```

---

##  Prevention Strategies

### Before Training

#### Environment Setup
- Verify all dependencies are installed
- Check GPU drivers are up to date
- Ensure sufficient disk space
- Test with small dataset first

#### Dataset Preparation
- Validate all image-caption pairs
- Check image quality and consistency
- Ensure proper file permissions
- Create backup of dataset

### During Training

#### Monitoring
- Monitor system resources continuously
- Watch training loss for anomalies
- Save checkpoints regularly
- Keep training logs

#### Progressive Testing
- Test model at regular intervals
- Validate with sample prompts
- Check for overfitting signs
- Adjust parameters based on results

---

##  Quick Reference

### Common Issues and Fixes

| Issue | Quick Fix | Prevention |
|--------|-------------|-------------|
| Out of Memory | Reduce batch size, enable gradient checkpointing | Use appropriate resolution, monitor memory |
| Poor Quality | Improve dataset, adjust learning rate | Use high-quality images, good captions |
| Overfitting | Reduce steps, add regularization | Use diverse dataset, early stopping |
| Training Crashes | Check hardware, reduce complexity | Monitor system health, save checkpoints |
| Slow Training | Optimize data loading, increase batch size | Use SSD storage, profile bottlenecks |
| Model Corruption | Save checkpoints regularly | Use reliable storage, verify files |

### Parameter Guidelines

| Parameter | Safe Start | When to Increase |
|------------|-------------|------------------|
| Learning Rate | 1e-4 | If training is stable |
| Batch Size | 1 | If memory allows |
| Training Steps | 1000-1500 | For basic training |
| Network Rank | 32 | For complex concepts |
| Resolution | 512x512 (SD1.5) | If memory allows |

---

##  Emergency Procedures

### Training Crashes

#### Immediate Actions
1. **Save Current State**: Save any partial progress
2. **Check Logs**: Review error messages for clues
3. **Free Resources**: Clear GPU memory and CPU
4. **Document**: Note what you were doing when it crashed

#### Recovery Steps
1. **Identify Cause**: Analyze logs and system state
2. **Fix Issue**: Address the root cause
3. **Resume Training**: Start from last good checkpoint
4. **Monitor Closely**: Watch for recurrence of the issue

### Data Loss

#### Prevention
- Use version control for datasets
- Regular backups to multiple locations
- Cloud storage for important datasets
- Document dataset changes and versions

#### Recovery
- Check recycle bin or trash
- Look for temporary files
- Check if training tool has auto-backups
- Restore from version control if available

---

##  Getting Help

### Community Resources

#### Forums and Communities
- **GitHub Issues**: Report bugs and get help
- **Discord/Slack**: Real-time community support
- **Reddit**: r/StableDiffusion, r/LocalLLaMA
- **Stack Overflow**: Technical questions and answers

#### Documentation
- **Official Docs**: Check tool-specific documentation
- **Tutorials**: Look for video tutorials
- **Examples**: Study working examples from others
- **Best Practices**: Learn from community experience

### Professional Help

#### When to Ask for Help
- **Complex Issues**: When you've tried basic solutions
- **Hardware Problems**: When you suspect hardware issues
- **Persistent Problems**: When issues keep recurring
- **Time-Sensitive**: When you need quick resolution

#### How to Ask Effectively
- **Provide Details**: Include error messages, system specs
- **Show Your Work**: Share your configuration and attempts
- **Be Specific**: Describe exactly what you're trying to do
- **Follow Up**: Respond to questions and provide updates

---

##  What's Next?

Now that you can troubleshoot training issues, you're ready to:

1. **[Model Management](../../user-guide/model-management.md)** - Manage your trained models
2. **[Advanced Development](../../development/README.md)** - Explore advanced topics
3. **[Community Sharing](../../README.md)** - Share your work and get help
4. **[Professional Development](../../development/README.md)** - Contribute to the project

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/vavo/lora-pilot/discussions/categories/documentation-feedback)


