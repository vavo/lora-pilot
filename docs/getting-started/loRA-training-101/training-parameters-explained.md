# Training Parameters Explained

Training parameters are like the controls on a professional camera. Understanding what each parameter does helps you get the results you want. This guide explains all the important training settings in simple terms.

## 🎯 The Big Picture

### What Training Parameters Do

Think of training parameters as instructions you give to the AI during training:

```
Your Examples + Training Parameters = Trained Model
     ↓              ↓                    ↓
Photos of cat + "Learn these features" → Model that knows your cat
```

### Why Parameters Matter

- **Quality Control**: Better parameters = better trained model
- **Efficiency**: Right settings = faster, more efficient training
- **Consistency**: Proper settings = more reliable results
- **Resource Usage**: Optimized settings = better hardware utilization

---

## 📊 Core Training Parameters

### Steps (Training Iterations)

#### What It Is
The number of times the AI looks at your training examples and updates its understanding.

#### How It Works
```
Step 1: AI looks at your photos, makes initial guess
Step 2: AI compares guess with photos, makes small improvement
Step 3: AI looks again, makes another small improvement
...continues for specified number of steps
```

#### Step Count Guidelines

| Training Type | Steps | When to Use |
|---------------|--------|--------------|
| Quick Test | 100-500 | Testing ideas, quick experiments |
| Basic Training | 1000-1500 | Good quality results |
| Quality Training | 2000-3000 | High-quality, professional results |
| Maximum Quality | 4000+ | When you need best possible results |

#### Practical Tips
- **Start Small**: 500-1000 steps to test if training is working
- **Monitor Progress**: Watch sample images during training
- **Diminishing Returns**: After 2000-3000 steps, improvements are minimal
- **Quality over Quantity**: Better to train longer with good data than short with lots of data

### Learning Rate

#### What It Is
How much the AI changes its understanding with each step. Think of it as "learning speed."

#### How It Works
```
High Learning Rate: Big changes each step (fast but risky)
Low Learning Rate: Small changes each step (slow but safe)
```

#### Learning Rate Guidelines

| Rate Range | Effect | When to Use |
|-------------|---------|--------------|
| 1e-3 to 1e-4 | Very slow, safe | Complex training, fine details |
| 5e-4 to 1e-3 | Slow, steady | Most training scenarios |
| 1e-3 to 5e-3 | Medium, balanced | Quick training, good results |
| 5e-3 to 1e-2 | Fast, risky | Simple concepts, quick experiments |
| 1e-2 to 1e-1 | Very fast, very risky | Testing only |

#### Practical Tips
- **Start Conservative**: 1e-4 is usually safe
- **Monitor Loss**: If loss increases, lower learning rate
- **Use Schedulers**: Learning rate schedulers help optimize
- **Model-Specific**: Different models may prefer different rates

### Batch Size

#### What It Is
How many training examples the AI looks at before updating its understanding.

#### How It Works
```
Batch Size 1: Look at 1 photo → Update understanding
Batch Size 2: Look at 2 photos → Update understanding
Batch Size 4: Look at 4 photos → Update understanding
```

#### Batch Size Guidelines

| Batch Size | VRAM Needed | Effect | When to Use |
|-------------|---------------|---------|--------------|
| 1 | Low | Stable, safe | Most training scenarios |
| 2 | Medium | Faster training | When you have enough VRAM |
| 4 | High | Much faster | Large datasets, powerful hardware |
| 8+ | Very High | Fastest possible | Professional training setups |

#### Practical Tips
- **Start with 1**: Most stable and reliable
- **Increase Gradually**: Try 2 if you have VRAM
- **Monitor Memory**: Watch VRAM usage during training
- **Consider Dataset Size**: Larger datasets can handle larger batches

---

## 🎨 Model Architecture Parameters

### Network Rank (Dimension)

#### What It Is
The "size" or "complexity" of your LoRA model. Higher rank = more capacity to learn details.

#### How It Works
```
Low Rank (16): Can learn basic features, small file
High Rank (128): Can learn complex details, larger file
```

#### Rank Guidelines

| Rank | File Size | Quality | When to Use |
|-------|------------|---------|--------------|
| 8-16 | Very Small | Basic concepts, simple characters |
| 16-32 | Small | Good balance of quality and size |
| 32-64 | Medium | High quality, most use cases |
| 64-128 | Large | Maximum quality, complex concepts |
| 128+ | Very Large | Professional quality, large datasets |

#### Practical Tips
- **Start with 32**: Good balance for most cases
- **Consider Dataset**: Larger datasets can handle higher ranks
- **Monitor Quality**: Higher rank doesn't always mean better results
- **File Size**: Higher rank = larger files

### Network Alpha

#### What It Is
Controls how strongly the LoRA influences the base model. Think of it as "volume control."

#### How It Works
```
Low Alpha (8): Subtle influence, blends with base model
High Alpha (32): Strong influence, overpowers base model
```

#### Alpha Guidelines

| Alpha | Effect | When to Use |
|-------|---------|--------------|
| 8-16 | Subtle | When you want to enhance base model |
| 16-32 | Balanced | Most training scenarios |
| 32-64 | Strong | When you want to override base model |
| 64+ | Very Strong | Complete style/character replacement |

#### Practical Tips
- **Match to Rank**: Often set alpha equal to rank
- **Test Different Values**: Find what works best for your case
- **Consider Use**: Subtle for style enhancement, strong for character replacement
- **Combine with Weight**: Use with LoRA weight in generation

---

## 🔧 Optimization Parameters

### Gradient Checkpointing

#### What It Is
A technique to reduce memory usage during training by temporarily forgetting intermediate calculations.

#### How It Works
```
Normal Training: Keeps all calculations in memory (uses lots of VRAM)
Gradient Checkpointing: Forgets intermediate, recalculates when needed (saves VRAM)
```

#### When to Use
- **Low VRAM**: When you have limited graphics memory
- **Large Models**: When training with high rank or batch size
- **Memory Errors**: When you get out-of-memory errors
- **Resource Optimization**: When you want to train larger models

#### Practical Tips
- **Enable for Memory**: Almost always safe to enable
- **Slower Training**: Slightly slower but saves memory
- **Monitor Impact**: Check if it's significantly slowing training
- **Default Recommendation**: Usually enabled by default in modern tools

### Mixed Precision Training

#### What It Is
Using lower-precision numbers (like FP16) instead of full precision (FP32) during training.

#### How It Works
```
FP32 Training: Uses full precision numbers (accurate but memory intensive)
FP16 Training: Uses half precision numbers (slightly less accurate but saves memory)
```

#### Precision Types

| Precision | Memory Usage | Quality | When to Use |
|-----------|---------------|---------|--------------|
| FP32 | High | Highest accuracy | When quality is critical |
| FP16 | Medium | Good accuracy | Most training scenarios |
| BF16 | Medium | Good accuracy | Modern models, good balance |

#### Practical Tips
- **Use FP16**: Good balance for most training
- **Consider BF16**: For modern models like FLUX.1
- **Monitor Quality**: Check if precision affects your results
- **Hardware Support**: Ensure your GPU supports mixed precision

---

## 📊 Regularization Parameters

### Weight Decay

#### What It Is
Penalizes large weights to prevent the model from becoming too complex or overfitting.

#### How It Works
```
No Weight Decay: Model can grow very large weights (risk of overfitting)
Weight Decay: Model keeps weights smaller (more general, less overfitting)
```

#### Weight Decay Guidelines

| Value | Effect | When to Use |
|-------|---------|--------------|
| 0.0 | No decay | When you want maximum learning |
| 0.01 | Light decay | Most training scenarios |
| 0.1 | Medium decay | When overfitting is a concern |
| 0.2+ | Heavy decay | When you see clear overfitting |

#### Practical Tips
- **Start with 0.01**: Good default for most cases
- **Monitor Overfitting**: If model only reproduces training images, increase decay
- **Learning Rate Interaction**: May need to adjust learning rate with decay
- **Dataset Size**: Larger datasets may need less decay

### Dropout

#### What It Is
Randomly "turns off" some neurons during training to prevent over-reliance on specific features.

#### How It Works
```
No Dropout: Model uses all neurons every time (risk of overfitting)
Dropout: Model randomly ignores some neurons (learns more robustly)
```

#### When to Use
- **Large Datasets**: When you have many training images
- **Complex Models**: When training with high rank
- **Overfitting Concern**: When model memorizes training data
- **Generalization**: When you want model to work on new prompts

#### Practical Tips
- **Usually Not Needed**: Most LoRA training doesn't require dropout
- **Monitor Results**: Check if dropout improves generalization
- **Start Small**: 0.1 is typical starting point
- **Dataset Dependent**: Larger datasets benefit more from dropout

---

## 🎯 Advanced Parameters

### Learning Rate Scheduler

#### What It Is
Automatically adjusts learning rate during training to optimize results.

#### Common Schedulers

| Scheduler | How It Works | When to Use |
|------------|----------------|--------------|
| Constant | Same learning rate throughout | Simple training |
| Cosine | Starts high, ends low | Most training scenarios |
| Linear | Decreases linearly | When you want gradual reduction |
| Exponential | Decreases exponentially | When you want rapid reduction |

#### Practical Tips
- **Cosine is Default**: Works well for most cases
- **Monitor Loss**: Watch how loss changes with scheduler
- **Adjust Based on Results**: Different schedulers work better for different cases
- **Learning Rate Interaction**: May need to adjust initial learning rate

### Warmup Steps

#### What It Is
Number of steps at the beginning of training where learning rate starts low and gradually increases.

#### How It Works
```
Step 1-100: Learning rate gradually increases from 0 to target rate
Step 101+: Learning rate stays at target rate
```

#### When to Use
- **Stable Training**: Helps training start smoothly
- **Large Models**: Prevents shock to model at start
- **Complex Datasets**: Helps model adapt gradually
- **Learning Rate Issues**: When training is unstable at start

#### Practical Tips
- **5-10% of Steps**: Common warmup duration
- **Monitor Loss**: Watch loss during warmup period
- **Adjust Learning Rate**: May need to adjust target rate
- **Not Always Needed**: Many trainings work fine without warmup

---

## 🔍 Parameter Combinations

### Beginner-Friendly Combinations

#### Quick Test Training
```
Steps: 500
Learning Rate: 1e-3
Batch Size: 1
Rank: 16
Alpha: 16
```

#### Standard Character Training
```
Steps: 1500
Learning Rate: 1e-4
Batch Size: 1
Rank: 32
Alpha: 32
Gradient Checkpointing: Enabled
Mixed Precision: FP16
```

### Advanced Combinations

#### High-Quality Character
```
Steps: 3000
Learning Rate: 5e-5
Batch Size: 2
Rank: 64
Alpha: 64
Weight Decay: 0.01
Learning Rate Scheduler: Cosine
Warmup Steps: 100
```

#### Style Training
```
Steps: 2000
Learning Rate: 1e-4
Batch Size: 1
Rank: 32
Alpha: 32
Dropout: 0.1
Mixed Precision: BF16
```

---

## 💡 Practical Tips

### Start Simple
- **Use Defaults**: Most tools have good default settings
- **Change One Parameter**: Adjust one thing at a time
- **Monitor Progress**: Watch samples during training
- **Learn Effects**: Understand what each parameter does

### Monitor Training
- **Sample Images**: Check generated samples regularly
- **Loss Curves**: Watch training loss over time
- **Resource Usage**: Monitor VRAM and training speed
- **Quality Assessment**: Evaluate if training is working

### Save Checkpoints
- **Regular Saves**: Save training progress every 100-500 steps
- **Multiple Versions**: Keep different training stages
- **Test Checkpoints**: Try different checkpoints to find best
- **Backup Important**: Save your best models separately

### Document Settings
- **Record Parameters**: Write down what worked
- **Note Results**: Document quality of each training
- **Compare Experiments**: Learn from different parameter combinations
- **Build Knowledge**: Create your own parameter guide

---

## 🔧 Troubleshooting Parameters

### Common Issues

#### Training is Unstable
- **Symptoms**: Loss jumps around, training crashes
- **Solutions**: Lower learning rate, enable gradient checkpointing
- **Check**: Learning rate might be too high

#### Model Overfits
- **Symptoms**: Only reproduces training images, poor generalization
- **Solutions**: Increase weight decay, add dropout, reduce steps
- **Check**: Dataset might be too small or repetitive

#### Training is Too Slow
- **Symptoms**: Training takes much longer than expected
- **Solutions**: Increase batch size, disable gradient checkpointing
- **Check**: VRAM usage, batch size might be too small

#### Quality is Poor
- **Symptoms**: Trained model doesn't work well
- **Solutions**: Increase steps, adjust learning rate, check dataset
- **Check**: Training parameters might be too conservative

### Parameter Optimization

#### Quality vs Speed
- **Higher Quality**: More steps, smaller learning rate, higher rank
- **Faster Training**: Larger batch size, gradient checkpointing
- **Balance**: Find sweet spot for your needs

#### Resource Optimization
- **Low VRAM**: Gradient checkpointing, mixed precision, small batch size
- **High VRAM**: Larger batch size, higher rank, no checkpointing
- **Memory Management**: Monitor and adjust based on your hardware

---

## 🚀 What's Next?

Now that you understand training parameters, you're ready to:

1. **[Dataset Preparation](dataset-preparation.md)** - Prepare your training data
2. **[Training Workflows](training-workflows.md)** - Learn step-by-step processes
3. **[Practical Training Projects](practical-training-projects.md)** - Start your first training project
4. **[Advanced Training Techniques](advanced-training-techniques.md)** - Master professional methods

---

*Last updated: 2025-02-11*
