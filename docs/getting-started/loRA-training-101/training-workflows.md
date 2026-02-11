# Training Workflows

Training workflows are step-by-step processes that guide you from dataset to trained model. This guide covers the complete training process using LoRA Pilot's tools.

## 🎯 Overview of Training Workflows

### The Training Pipeline

```
Dataset Preparation → Training Configuration → Training Execution → Model Testing → Model Refinement
```

### Available Tools in LoRA Pilot

1. **Kohya SS** - Traditional, feature-rich training interface
2. **AI Toolkit** - Modern, FLUX.1-optimized training
3. **TrainPilot** - Simplified training automation
4. **Manual Training** - Command-line training for advanced users

---

## 🎨 Kohya SS Workflow

### Overview

Kohya SS is the most established LoRA training tool with extensive configuration options and proven reliability.

### Step-by-Step Workflow

#### Step 1: Launch Kohya SS
1. **Access ControlPilot**: Go to Services tab
2. **Start Kohya SS**: Click "Open" next to Kohya SS
3. **Wait for Loading**: Interface will load in your browser
4. **Verify Access**: Should see Kohya SS interface

#### Step 2: Configure Basic Settings
1. **Go to Folders Tab**: Set up your directories
2. **Set Train Data Directory**: Point to your dataset folder
3. **Set Output Directory**: Choose where to save trained model
4. **Set Logging Directory**: For training logs

```
Example Paths:
Train Data: /workspace/datasets/images/1_my_character
Output: /workspace/outputs/my_character
Logging: /workspace/outputs/my_character/logs
```

#### Step 3: Configure Model Settings
1. **Go to Training Tab**: Main training configuration
2. **Select Base Model**: Choose your base model
3. **Set Model Parameters**:
   - **Resolution**: 512x512 (SD1.5) or 1024x1024 (SDXL)
   - **Batch Size**: 1 (recommended for stability)
   - **Save Every N Steps**: 100 (for checkpoints)

#### Step 4: Configure Network Settings
1. **Network Type**: Select "LoRA"
2. **Network Dim**: 32 (recommended starting point)
3. **Network Alpha**: 32 (match to dim)
4. **Convolution Dim**: 0 (unless training complex concepts)

#### Step 5: Configure Training Parameters
1. **Learning Rate**: 1e-4 (good starting point)
2. **Training Steps**: 1500 (good for character training)
3. **Learning Rate Scheduler**: Cosine (recommended)
4. **Optimizer**: AdamW8bit (recommended)

#### Step 6: Configure Dataset
1. **Enable Bucket**: For varied image sizes
2. **Min Bucket Resolution**: 512 (SD1.5) or 1024 (SDXL)
3. **Max Bucket Resolution**: 512 (SD1.5) or 1024 (SDXL)
4. **Caption Extension**: .txt

#### Step 7: Configure Optimization
1. **Mixed Precision**: FP16 (recommended)
2. **Gradient Checkpointing**: Enabled (saves memory)
3. **Cache Latents**: Enabled (speeds up training)
4. **Save Precision**: FP16 (saves space)

#### Step 8: Configure Sampling
1. **Sample Every**: 100 steps
2. **Sample Prompts**: Your trigger word with simple descriptions
3. **Sampler**: DPM++ 2M Karras
4. **CFG Scale**: 7.0

#### Step 9: Start Training
1. **Review Configuration**: Double-check all settings
2. **Start Training**: Click "Start Training" button
3. **Monitor Progress**: Watch samples and loss
4. **Save Checkpoints**: Let training save automatically

#### Step 10: Monitor and Adjust
1. **Watch Samples**: Check generated images every 100 steps
2. **Monitor Loss**: Look at training loss curve
3. **Adjust if Needed**: Stop and adjust if problems
4. **Continue Training**: Resume with new settings if needed

#### Step 11: Test Trained Model
1. **Locate Final Model**: Find in output directory
2. **Test in Generation Tool**: Use in ComfyUI or InvokeAI
3. **Evaluate Quality**: Test with various prompts
4. **Refine if Needed**: Consider additional training

### Kohya SS Tips

#### Best Practices
- **Start Conservative**: Use recommended settings first
- **Monitor Closely**: Check samples every 100 steps
- **Save Checkpoints**: Don't wait until training finishes
- **Test Early**: Test model before training completes

#### Common Issues
- **Out of Memory**: Reduce batch size or enable checkpointing
- **Poor Quality**: Check dataset quality and captions
- **Training Crashes**: Check VRAM usage and reduce complexity

---

## 🚀 AI Toolkit Workflow

### Overview

AI Toolkit is a modern training interface optimized for FLUX.1 and latest models, with a clean web interface.

### Step-by-Step Workflow

#### Step 1: Launch AI Toolkit
1. **Access ControlPilot**: Go to Services tab
2. **Start AI Toolkit**: Click "Open" next to AI Toolkit
3. **Wait for Loading**: Interface will load in your browser
4. **Verify Access**: Should see AI Toolkit interface

#### Step 2: Create Training Job
1. **Go to Training Tab**: Main training interface
2. **Click "Create Job"**: Start new training configuration
3. **Select Job Type**: Choose "LoRA Training"
4. **Name Your Job**: Give it a descriptive name

#### Step 3: Configure Model
1. **Select Base Model**: Choose from dropdown (e.g., FLUX.1 Schnell)
2. **Set Network Type**: LoRA
3. **Configure Network**:
   - **Linear**: 32 (recommended)
   - **Linear Alpha**: 32
   - **Conv**: 16 (optional)

#### Step 4: Configure Dataset
1. **Select Dataset**: Choose your prepared dataset
2. **Set Resolution**: 1024x1024 (for FLUX.1)
3. **Set Batch Size**: 1 (recommended)
4. **Set Repeats**: 1 (unless dataset is small)

#### Step 5: Configure Training
1. **Set Steps**: 3000 (good for FLUX.1)
2. **Set Learning Rate**: 1e-4 (recommended)
3. **Set Optimizer**: AdamW8bit
4. **Set Precision**: BF16 (recommended for FLUX.1)

#### Step 6: Configure Sampling
1. **Sample Every**: 250 steps
2. **Set Prompts**: Your trigger word with descriptions
3. **Set CFG Scale**: 7.0
4. **Set Steps**: 20-30 (for sampling)

#### Step 7: Configure Output
1. **Set Output Directory**: Where to save trained model
2. **Set Save Format**: Diffusers (recommended)
3. **Set Save Every**: 500 steps
4. **Set Max Saves**: Keep last 4 checkpoints

#### Step 8: Start Training
1. **Review Configuration**: Check all settings
2. **Start Job**: Click "Start Training"
3. **Monitor Progress**: Watch training dashboard
4. **View Samples**: Check generated samples

#### Step 9: Monitor Progress
1. **Training Dashboard**: Watch progress in real-time
2. **Sample Generation**: View samples as they're generated
3. **Loss Monitoring**: Check training loss curve
4. **Resource Usage**: Monitor GPU and memory usage

#### Step 10: Test Results
1. **Locate Trained Model**: Find in output directory
2. **Test in ComfyUI**: Load and test your LoRA
3. **Evaluate Quality**: Test with various prompts
4. **Compare Results**: Compare with your expectations

### AI Toolkit Tips

#### Best Practices
- **Use BF16**: Recommended for FLUX.1 training
- **Monitor GPU**: Watch GPU memory usage closely
- **Save Frequently**: Don't wait until completion
- **Test Early**: Test model during training

#### Common Issues
- **Memory Issues**: Reduce batch size or enable gradient checkpointing
- **Slow Training**: Check GPU utilization and settings
- **Poor Samples**: Check dataset quality and prompts
- **Connection Errors**: Verify dataset paths and permissions

---

## 🎯 TrainPilot Workflow

### Overview

TrainPilot is a simplified training automation tool that makes training easy for beginners.

### Step-by-Step Workflow

#### Step 1: Launch TrainPilot
1. **Access ControlPilot**: Go to Training tab
2. **Launch TrainPilot**: Click "Start Training Automation"
3. **Select Training Type**: Choose "LoRA Training"
4. **Follow Wizard**: Step-by-step guided setup

#### Step 2: Select Dataset
1. **Browse Datasets**: Choose from your prepared datasets
2. **Preview Dataset**: See sample images and captions
3. **Validate Dataset**: Check for common issues
4. **Confirm Selection**: Choose your dataset

#### Step 3: Choose Training Profile
1. **Quick Test**: 100 steps, basic settings
2. **Standard Training**: 1500 steps, balanced settings
3. **Quality Training**: 3000 steps, high quality
4. **Custom**: Advanced settings for experienced users

#### Step 4: Configure Base Model
1. **Select Model**: Choose from available models
2. **Auto-Configure**: Settings adjust based on model
3. **Manual Override**: Override if needed
4. **Verify Compatibility**: Check model supports your training type

#### Step 5: Review and Start
1. **Review Configuration**: Check all settings
2. **Start Training**: Begin training process
3. **Monitor Progress**: Watch training dashboard
4. **Receive Notifications**: Get alerts when training completes

#### Step 6: Test Results
1. **Automatic Testing**: TrainPilot can test automatically
2. **Manual Testing**: Test in your preferred tool
3. **Quality Assessment**: Evaluate trained model
4. **Save Results**: Save successful training

### TrainPilot Tips

#### Best Practices
- **Start with Profiles**: Use built-in profiles for best results
- **Monitor Progress**: Keep an eye on training progress
- **Test Early**: Don't wait until completion to test
- **Save Configurations**: Save successful training configurations

#### Common Issues
- **Dataset Issues**: Ensure dataset is properly formatted
- **Profile Mismatch**: Choose appropriate profile for your needs
- **Resource Limits**: Monitor GPU and memory usage
- **Permission Errors**: Check file and directory permissions

---

## 🔧 Manual Training Workflow

### Overview

For advanced users who want complete control over the training process.

### Step-by-Step Workflow

#### Step 1: Prepare Environment
1. **Access Container Shell**: `docker exec -it lora-pilot bash`
2. **Navigate to Training Directory**: `cd /workspace`
3. **Activate Environment**: `source /opt/venvs/core/bin/activate`
4. **Verify Setup**: Check tools and dependencies

#### Step 2: Prepare Configuration
1. **Create Config File**: YAML or JSON configuration
2. **Set Dataset Path**: Point to your dataset
3. **Set Output Path**: Choose output location
4. **Configure Parameters**: Set all training parameters

#### Step 3: Run Training
1. **Execute Training Command**: Run training script
2. **Monitor Progress**: Watch training logs
3. **Check GPU Usage**: Monitor resource utilization
4. **Handle Errors**: Address any issues that arise

#### Step 4: Post-Processing
1. **Convert Model**: Convert to desired format if needed
2. **Test Model**: Test in generation tool
3. **Optimize Model**: Apply optimizations if needed
4. **Package Model**: Prepare for distribution

### Manual Training Tips

#### Best Practices
- **Document Everything**: Keep detailed records of configurations
- **Version Control**: Use git for configuration management
- **Backup Regularly**: Save progress and intermediate results
- **Test Incrementally**: Test as you train

#### Common Issues
- **Environment Issues**: Verify all dependencies are installed
- **Configuration Errors**: Double-check all configuration files
- **Permission Problems**: Ensure proper file and directory permissions
- **Resource Limits**: Monitor and manage resource usage

---

## 📊 Workflow Comparison

### Ease of Use

| Tool | Beginner Friendly | Setup Time | Flexibility | Control |
|-------|------------------|-------------|----------|
| Kohya SS | Medium | 10-15 minutes | High | High |
| AI Toolkit | High | 5-10 minutes | Medium | Medium |
| TrainPilot | Very High | 5 minutes | Low | Low |
| Manual | Low | 30+ minutes | Very High | Very High |

### Feature Availability

| Feature | Kohya SS | AI Toolkit | TrainPilot | Manual |
|---------|-----------|-------------|-----------|--------|
| Visual Interface | Yes | Yes | Yes | No |
| Advanced Parameters | Yes | Medium | Low | Very High |
| Automation | Medium | Medium | High | None |
| FLUX.1 Support | Limited | Yes | Limited | Yes |
| Real-time Monitoring | Yes | Yes | Yes | No |

### Use Case Recommendations

#### For Beginners
1. **TrainPilot**: Easiest way to start
2. **AI Toolkit**: Modern interface, good for FLUX.1
3. **Kohya SS**: When you need more control
4. **Manual**: Only when you're experienced

#### For Character Training
1. **Kohya SS**: Most proven for character training
2. **AI Toolkit**: Good for FLUX.1 characters
3. **TrainPilot**: Quick character training
4. **Manual**: For complete control

#### For Style Training
1. **Kohya SS**: Traditional style training
2. **AI Toolkit**: Modern style training
3. **TrainPilot**: Simplified style training
4. **Manual**: For complex style training

#### For FLUX.1 Training
1. **AI Toolkit**: Optimized for FLUX.1
2. **Manual**: For complete control
3. **Kohya SS**: Limited FLUX.1 support
4. **TrainPilot**: Basic FLUX.1 support

---

## 💡 Workflow Optimization

### Speed Optimization

#### Parallel Processing
- **Multiple Datasets**: Train multiple models simultaneously
- **GPU Utilization**: Maximize GPU usage
- **Batch Processing**: Process multiple images at once
- **Resource Management**: Balance speed and stability

#### Caching Strategies
- **Latent Caching**: Pre-compute latents for faster training
- **Dataset Caching**: Cache dataset metadata
- **Model Caching**: Cache model weights
- **Memory Management**: Optimize memory usage

### Quality Optimization

#### Progressive Training
- **Start Small**: Begin with shorter training
- **Evaluate Results**: Test intermediate models
- **Continue Training**: Continue with best configuration
- **Final Training**: Full training with optimized settings

#### Parameter Tuning
- **Learning Rate Tuning**: Find optimal learning rate
- **Batch Size Optimization**: Find optimal batch size
- **Rank Selection**: Choose appropriate network rank
- **Scheduler Selection**: Find best scheduler for your case

---

## 🔍 Troubleshooting Workflows

### Common Training Issues

#### Training Fails to Start
- **Check Configuration**: Verify all settings are correct
- **Check Paths**: Ensure dataset and output paths exist
- **Check Permissions**: Verify file and directory permissions
- **Check Resources**: Verify GPU and memory availability

#### Training is Unstable
- **Reduce Learning Rate**: Lower learning rate by factor of 10
- **Enable Checkpointing**: Enable gradient checkpointing
- **Reduce Batch Size**: Use smaller batch size
- **Check Dataset**: Verify dataset quality and consistency

#### Poor Quality Results
- **Check Dataset Quality**: Ensure high-quality training data
- **Increase Training Steps**: Train for longer duration
- **Adjust Parameters**: Tune learning rate and other parameters
- **Review Configuration**: Check for configuration errors

### Resource Issues

#### Out of Memory Errors
- **Reduce Batch Size**: Use smaller batch size
- **Enable Checkpointing**: Enable gradient checkpointing
- **Use Mixed Precision**: Use FP16 or BF16
- **Reduce Model Complexity**: Lower rank or other parameters

#### Slow Training
- **Increase Batch Size**: Use larger batch size if possible
- **Optimize Dataset**: Ensure efficient data loading
- **Check GPU Utilization**: Ensure GPU is being used fully
- **Optimize I/O**: Use fast storage for dataset

---

## 🚀 What's Next?

Now that you understand training workflows, you're ready to:

1. **[Practical Training Projects](practical-training-projects.md)** - Start your first training project
2. **[Advanced Training Techniques](advanced-training-techniques.md)** - Master professional methods
3. **[Troubleshooting Training](troubleshooting-training.md)** - Handle common training issues
4. **[Model Management](../../user-guide/model-management.md)** - Organize your trained models

---

*Last updated: 2025-02-11*
