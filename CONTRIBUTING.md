# Contributing to Velvet Chain

First off, thank you for considering contributing to Velvet Chain! It's people like you that make Velvet Chain such a great blockchain.

## 🌟 Ways to Contribute

### 1. Run a Node
The best way to contribute is to run a Velvet Chain node! This helps:
- Decentralize the network
- Validate transactions
- Relay blocks to other nodes
- Secure the blockchain

### 2. Mine Blocks
Start mining to:
- Earn VELVET tokens
- Process transactions
- Add blocks to the chain
- Strengthen network security

### 3. Report Bugs
Found a bug? Please report it!
- Check if the issue already exists
- Use the GitHub issue template
- Provide detailed reproduction steps
- Include your environment details

### 4. Suggest Features
Have an idea? We'd love to hear it!
- Open a feature request issue
- Describe the problem it solves
- Explain your proposed solution
- Discuss alternatives you've considered

### 5. Write Code
Contribute code improvements:
- Fix bugs
- Add features
- Improve performance
- Enhance security
- Write tests

### 6. Improve Documentation
Documentation is crucial:
- Fix typos and errors
- Clarify confusing sections
- Add examples
- Translate to other languages

## 🚀 Getting Started

### Setup Development Environment

1. **Fork the repository**
```bash
# Click "Fork" on GitHub, then:
git clone https://github.com/YOUR_USERNAME/velvet-chain.git
cd velvet-chain
```

2. **Create a branch**
```bash
git checkout -b feature/amazing-feature
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If available
```

4. **Make your changes**
```bash
# Edit files
# Test your changes
```

5. **Run tests**
```bash
python -m pytest tests/
python -m pylint node.py
```

6. **Commit your changes**
```bash
git add .
git commit -m "Add amazing feature"
```

7. **Push to your fork**
```bash
git push origin feature/amazing-feature
```

8. **Open a Pull Request**
- Go to the original repository
- Click "New Pull Request"
- Select your fork and branch
- Describe your changes
- Submit!

## 📝 Code Style

### Python Style Guide
- Follow PEP 8
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to functions and classes

### Example:
```python
def mine_block(self, difficulty: int) -> Block:
    """
    Mine a new block using Proof of Work.
    
    Args:
        difficulty: Number of leading zeros required
        
    Returns:
        Block: The newly mined block
    """
    # Implementation here
    pass
```

### Commit Messages
Use clear, descriptive commit messages:

**Good:**
- `Add difficulty adjustment algorithm`
- `Fix transaction validation bug`
- `Improve P2P peer discovery`
- `Update README with new examples`

**Bad:**
- `fix bug`
- `update`
- `changes`
- `wip`

### Commit Message Format:
```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## 🔍 Pull Request Guidelines

### Before Submitting
- [ ] Code follows style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings

### PR Title Format
```
[Type] Brief description

Examples:
[Feature] Add smart contract support
[Fix] Resolve transaction validation issue
[Docs] Update mining guide
```

### PR Description Template
```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots here

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest tests/test_blockchain.py

# Run with coverage
python -m pytest --cov=node
```

### Writing Tests
```python
import pytest
from node import VelvetChain, Block

def test_genesis_block_creation():
    """Test genesis block is created correctly."""
    chain = VelvetChain()
    assert len(chain.chain) == 1
    assert chain.chain[0].number == 0
    assert chain.chain[0].previous_hash == '0x' + '0' * 64
```

## 🐛 Bug Reports

### Before Reporting
- Search existing issues
- Try latest version
- Reproduce the bug

### Bug Report Template
```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python Version: [e.g., 3.11.0]
- Velvet Chain Version: [e.g., 1.0.0]

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

### Feature Request Template
```markdown
**Problem**
What problem does this solve?

**Proposed Solution**
Describe your solution

**Alternatives**
Other solutions you've considered

**Additional Context**
Any other relevant information
```

## 📋 Coding Standards

### Security
- Never commit private keys
- Validate all user inputs
- Use parameterized queries
- Handle errors gracefully
- Log security events

### Performance
- Optimize database queries
- Use caching where appropriate
- Profile code for bottlenecks
- Minimize network calls
- Use efficient algorithms

### Documentation
- Document all public APIs
- Add inline comments for complex logic
- Update README for user-facing changes
- Keep documentation in sync with code

## 🎯 Priority Areas

We especially welcome contributions in:

1. **Smart Contract Support** - EVM bytecode execution
2. **Performance** - Optimization and scaling
3. **Security** - Audits and improvements
4. **Mobile Wallets** - iOS/Android apps
5. **Bridge Development** - Cross-chain bridges
6. **DeFi Protocols** - DEX, lending, staking
7. **Testing** - Unit, integration, e2e tests
8. **Documentation** - Tutorials and guides

## 👥 Community

### Communication Channels
- **Discord:** https://discord.gg/velvetchain
- **Twitter:** https://twitter.com/velvetchain
- **Telegram:** https://t.me/velvetchain
- **Email:** dev@velvetchain.network

### Code of Conduct
- Be respectful and inclusive
- Welcome newcomers
- Give constructive feedback
- Focus on what's best for the community
- Show empathy towards others

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Featured on our website
- Eligible for community rewards

## 📜 Legal

By contributing, you agree that:
- Your contributions are your original work
- You have the right to submit the contribution
- Your contribution is licensed under MIT License
- You understand and accept the Contributor License Agreement

## ❓ Questions?

Need help? Reach out:
- Open a discussion on GitHub
- Ask in Discord #dev channel
- Email: dev@velvetchain.network

---

**Thank you for contributing to Velvet Chain! 🚀**

Together, we're building the future of decentralized blockchain technology.