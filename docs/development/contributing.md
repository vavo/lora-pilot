# Contributing to LoRA Pilot

Thank you for your interest in contributing to LoRA Pilot! This guide covers how to contribute effectively, including development setup, contribution guidelines, and community practices.

##  Contribution Overview

LoRA Pilot welcomes contributions in many forms:
- **Code Contributions**: Bug fixes, new features, improvements
- **Documentation**: Documentation improvements, tutorials, guides
- **Testing**: Bug reports, test cases, quality assurance
- **Community**: Support, discussions, feedback
- **Design**: UI/UX improvements, visual assets

##  Getting Started

### Development Setup

#### Fork and Clone
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/your-username/lora-pilot.git
cd lora-pilot

# Add upstream remote
git remote add upstream https://github.com/vavo/lora-pilot.git
```

#### Development Environment
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Start development environment
docker-compose -f docker-compose.dev.yml up -d
```

#### IDE Configuration
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "/opt/venvs/core/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true
    }
}
```

### Project Structure

#### Key Directories
```
lora-pilot/
├── apps/                    # Application components
│   ├── Portal/              # ControlPilot
│   ├── Kohya/               # Kohya SS integration
│   ├── ComfyUI/             # ComfyUI integration
│   └── TrainPilot/          # Training automation
├── scripts/                 # Utility scripts
├── config/                  # Configuration files
├── docker-compose/          # Docker configurations
├── docs/                    # Documentation
├── tests/                   # Test files
└── Dockerfile               # Main build file
```

#### Component Architecture
```
apps/
├── Portal/                  # Main web interface
│   ├── static/              # Static assets
│   ├── templates/           # HTML templates
│   └── app.py               # FastAPI application
├── TrainPilot/              # Training automation
│   ├── trainpilot.py        # Main script
│   └── helpers.py           # Helper functions
└── TagPilot/                # Dataset tagging
    ├── app.py               # FastAPI application
    └── static/              # Static assets
```

##  Contribution Guidelines

### Code Standards

#### Python Code Style
```python
# Follow PEP 8
# Use Black for formatting
# Use type hints where appropriate
# Keep functions focused and small

# Example function
def process_dataset(
    dataset_path: str,
    output_path: str,
    config: Dict[str, Any],
) -> bool:
    """Process a dataset with given configuration.
    
    Args:
        dataset_path: Path to input dataset
        output_path: Path for processed output
        config: Processing configuration
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Implementation here
        return True
    except Exception as e:
        logger.error(f"Dataset processing failed: {e}")
        return False
```

#### JavaScript/TypeScript Code Style
```typescript
// Use TypeScript for new code
// Follow ESLint configuration
// Use meaningful variable names
// Add JSDoc comments

interface DatasetConfig {
  path: string;
  resolution: number[];
  batchSize: number;
}

/**
 * Process dataset with given configuration
 * @param config Dataset configuration
 * @returns Processing result
 */
async function processDataset(config: DatasetConfig): Promise<boolean> {
  // Implementation here
  return true;
}
```

#### Dockerfile Style
```dockerfile
# Use multi-stage builds
# Order layers from least to most likely to change
# Use specific versions
# Add comments for complex operations

# Example
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
```

### Commit Guidelines

#### Commit Message Format
```
type(scope): description

[optional body]

[optional footer]
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples
```
feat(training): add FLUX.1 training support

Add support for training FLUX.1 models using AI Toolkit
integration. Includes configuration updates and documentation.

Closes #123

fix(kohya): resolve memory leak in training process

Fix memory leak caused by unclosed file handles in
Kohya SS training process. Add proper resource cleanup.

Closes #124
```

### Pull Request Guidelines

#### PR Requirements
1. **Clear Description**: Explain what the PR does and why
2. **Testing**: Include tests for new functionality
3. **Documentation**: Update documentation for new features
4. **Compatibility**: Ensure backward compatibility
5. **Performance**: Consider performance impact

#### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🧪 Testing Guidelines

### Test Structure

#### Unit Tests
```python
# tests/test_trainpilot.py
import pytest
from unittest.mock import Mock, patch
from apps.TrainPilot.trainpilot import TrainingConfig

class TestTrainingConfig:
    def test_config_validation(self):
        """Test configuration validation"""
        config = TrainingConfig(
            steps=100,
            learning_rate=1e-4,
            batch_size=1
        )
        assert config.is_valid()
    
    def test_invalid_config(self):
        """Test invalid configuration handling"""
        config = TrainingConfig(
            steps=-1,  # Invalid
            learning_rate=1e-4,
            batch_size=1
        )
        assert not config.is_valid()
```

#### Integration Tests
```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from apps.Portal.app import app

class TestAPIIntegration:
    def test_health_check(self):
        """Test API health check endpoint"""
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

#### End-to-End Tests
```python
# tests/test_e2e.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By

class TestE2E:
    def test_training_workflow(self):
        """Test complete training workflow"""
        driver = webdriver.Chrome()
        try:
            # Navigate to ControlPilot
            driver.get("http://localhost:7878")
            
            # Create dataset
            driver.find_element(By.ID, "create-dataset").click()
            
            # Configure training
            driver.find_element(By.ID, "configure-training").click()
            
            # Start training
            driver.find_element(By.ID, "start-training").click()
            
            # Verify training started
            assert "Training started" in driver.page_source
        finally:
            driver.quit()
```

### Test Commands

#### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_trainpilot.py

# Run with coverage
pytest tests/ --cov=apps --cov-report=html

# Run integration tests
pytest tests/integration/

# Run e2e tests
pytest tests/e2e/
```

#### Test Configuration
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --cov=apps
    --cov-report=term-missing
```

## 🐛 Bug Reporting

### Bug Report Template

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to...
2. Click on...
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g., Ubuntu 22.04]
- Docker Version: [e.g., 20.10.17]
- LoRA Pilot Version: [e.g., v2.0]
- GPU: [e.g., RTX 4090]

## Additional Context
Any other relevant information

## Logs
Error logs, stack traces, etc.
```

### Debug Information

#### Collect Debug Info
```bash
# System information
docker exec lora-pilot uname -a
docker exec lora-pilot python --version
docker exec lora-pilot nvidia-smi

# Service status
docker exec lora-pilot supervisorctl status

# Logs
docker exec lora-pilot supervisorctl tail -100 controlpilot
```

#### Log Collection Script
```bash
#!/bin/bash
# collect-debug-info.sh

echo "=== System Information ==="
uname -a
docker --version
docker-compose --version

echo "=== Container Status ==="
docker-compose ps

echo "=== Service Logs ==="
docker-compose logs --tail=100

echo "=== Resource Usage ==="
docker stats --no-stream
```

## 💡 Feature Requests

### Feature Request Template

```markdown
## Feature Description
Clear description of the feature

## Problem Statement
What problem does this solve?

## Proposed Solution
How should this be implemented?

## Alternatives Considered
Other approaches considered

## Additional Context
Any other relevant information
```

### Feature Discussion

#### Before Implementation
1. **Search Issues**: Check for existing requests
2. **Discuss in Community**: Get feedback on approach
3. **Create Issue**: Formalize the request
4. **Plan Implementation**: Design the solution

#### Implementation Planning
```markdown
## Implementation Plan

### Phase 1: Core Functionality
- [ ] Basic implementation
- [ ] Unit tests
- [ ] Documentation

### Phase 2: Integration
- [ ] Integration with existing components
- [ ] Integration tests
- [ ] User documentation

### Phase 3: Polish
- [ ] UI/UX improvements
- [ ] Performance optimization
- [ ] Error handling
```

##  Documentation Contributions

### Documentation Types

#### User Documentation
- **Getting Started Guides**: Help new users get started
- **Tutorials**: Step-by-step guides for specific tasks
- **Reference Guides**: Comprehensive reference materials

#### Developer Documentation
- **Architecture Docs**: System design and architecture
- **API Documentation**: Complete API reference
- **Contributing Guide**: Guidelines for contributors

#### Technical Documentation
- **Build Instructions**: How to build from source
- **Deployment Guides**: Production deployment instructions
- **Troubleshooting**: Common issues and solutions

### Documentation Standards

#### Markdown Style
```markdown
# Heading 1
## Heading 2
### Heading 3

- Use bullet points for lists
- Use code blocks for code
- Use backticks for inline code

```python
# Code blocks with language
def example_function():
    return "Hello, World!"
```

**Bold text** for emphasis
*Italic text* for emphasis
```

#### Documentation Structure
```markdown
# Document Title

Brief description of what this document covers.

## Overview
More detailed overview

## Usage
How to use the feature

## Examples
Practical examples

## Troubleshooting
Common issues and solutions

## Related Documents
Links to related documentation
```

### Documentation Review

#### Review Checklist
- [ ] Content is accurate and up-to-date
- [ ] Examples are tested and working
- [ ] Links are valid and accessible
- [ ] Formatting is consistent
- [ ] Spelling and grammar are correct

#### Review Process
1. **Self-Review**: Review your own changes
2. **Peer Review**: Get feedback from others
3. **Technical Review**: Ensure technical accuracy
4. **User Review**: Test from user perspective

## 🤝 Community Guidelines

### Code of Conduct

#### Our Pledge
- Be inclusive and welcoming
- Be respectful of different viewpoints
- Focus on what is best for the community
- Show empathy toward other community members

#### Expected Behavior
- Use welcoming and inclusive language
- Be respectful of differing opinions and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy toward other community members

#### Unacceptable Behavior
- Harassment, bullying, or discrimination
- Publishing private information
- Anything that could be considered inappropriate

### Communication Guidelines

#### GitHub Issues
- **Be Specific**: Provide clear, detailed information
- **Be Respectful**: Treat others with respect
- **Be Constructive**: Focus on solutions, not problems
- **Be Patient**: Allow time for responses

#### Discussions
- **Stay On Topic**: Keep discussions relevant
- **Be Concise**: Keep messages focused and clear
- **Be Helpful**: Help others when you can
- **Be Professional**: Maintain professional conduct

## 🏆 Recognition

### Contributor Recognition

#### Contributors List
- **GitHub Contributors**: Automatic recognition via GitHub
- **Documentation Credits**: Credit in documentation
- **Release Notes**: Mention in release notes

#### Contribution Types
- **Code**: Bug fixes, features, improvements
- **Documentation**: Guides, tutorials, reference
- **Testing**: Bug reports, test cases, QA
- **Community**: Support, discussions, feedback
- **Design**: UI/UX, visual assets, branding

### Recognition Methods

#### GitHub Recognition
- **Contributor Badge**: GitHub automatically tracks contributions
- **Merge Commits**: Recognition in commit history
- **Release Notes**: Mentioned in release notes

#### Community Recognition
- **Thank You Posts**: Public appreciation in discussions
- **Contributor Spotlight**: Featured in community posts
- **Annual Recognition**: Year-end contributor highlights

##  Development Workflow

### Branch Strategy

#### Main Branch
- **main**: Stable, production-ready code
- **develop**: Development branch for next release
- **feature/***: Feature branches
- **bugfix/***: Bug fix branches
- **hotfix/***: Critical fixes

#### Branch Protection
```yaml
# .github/branch-protection.yml
protection:
  required_status_checks:
    strict: true
    contexts:
      - "CI/CD"
      - "Code Review"
  required_pull_request_reviews:
    required_approving_review_count: 1
    dismiss_stale_reviews: true
```

### Release Process

#### Version Management
```bash
# Semantic versioning
# MAJOR.MINOR.PATCH
# 1.0.0, 1.1.0, 1.1.1

# Release branches
# release/1.0.0
# release/1.1.0
```

#### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version bumped
- [ ] Changelog updated
- [ ] Release notes written
- [ ] Tag created
- [ ] Release published

### Quality Assurance

#### Code Review Process
1. **Self-Review**: Review your own code
2. **Peer Review**: Get feedback from team members
3. **Automated Review**: CI/CD checks
4. **Final Review**: Maintainer approval

#### Quality Gates
- **Code Coverage**: Minimum 80% coverage
- **Static Analysis**: No critical issues
- **Security Scan**: No vulnerabilities
- **Performance**: No performance regressions

##  Getting Help

### Support Channels

#### GitHub Issues
- **Bug Reports**: For bugs and issues
- **Feature Requests**: For new features
- **Questions**: For general questions

#### Discussions
- **General Discussion**: Open-ended conversations
- **Show and Tell**: Share your work
- **Help Wanted**: Get help from community

#### Documentation
- **README**: Basic getting started
- **Wiki**: Detailed documentation
- **API Docs**: API reference

### Resources

#### Learning Resources
- **Python Documentation**: https://docs.python.org/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Docker Documentation**: https://docs.docker.com/
- **React Documentation**: https://react.dev/

#### Community Resources
- **GitHub Discussions**: Community discussions
- **Discord Server**: Real-time chat (if available)
- **Stack Overflow**: Technical questions

## 📞 Contact Information

### Project Maintainers

#### Core Team
- **@vavo**: Project founder and maintainer
- **[Other maintainers]**: List of maintainers

#### Contact Methods
- **GitHub Issues**: For bugs and features
- **GitHub Discussions**: For general discussion
- **Email**: For private matters (if available)

### Contributing Timeline

#### Time Commitment
- **Small Contributions**: 1-2 hours
- **Medium Contributions**: 1-2 days
- **Large Contributions**: 1-2 weeks
- **Ongoing Contributions**: As time permits

#### Review Timeline
- **Initial Review**: 1-2 business days
- **Detailed Review**: 3-5 business days
- **Merge Decision**: 1-2 business days after review

---

## 📝 Feedback

Was this helpful? [Suggest improvements on GitHub Discussions](https://github.com/notri1/lora-pilot/discussions/categories/documentation-feedback)


