# Contributing to PVE

Thank you for your interest in contributing to PVE (Platform Visual Engine)! This document provides guidelines and information for contributors.

## 🤝 Code of Conduct

By participating in this project, you agree to abide by our code of conduct:
- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment for all contributors

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/pve.git
   cd pve
   ```

2. **Environment Setup**
   ```bash
   cp env.example .env
   # Configure your local environment variables
   ```

3. **Start Development Environment**
   ```bash
   docker-compose up -d
   ```

### Project Structure

- `src/` - Vue.js frontend application
- `backend/pve/` - Python Flask backend
- `backend/pve/app/vpl/` - Visual Programming Language engine
- `backend/pve/app/pvebot/` - Trading bot management
- `src/components/custom_nodes/` - VPL node definitions

## 📝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use issue templates** when available
3. **Include relevant information**:
   - Environment details (OS, browser, Docker version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/logs if applicable

### Feature Requests

1. **Check the roadmap** in issues/discussions
2. **Describe the use case** and benefit
3. **Provide examples** of how it would work
4. **Consider implementation complexity**

### Pull Requests

#### Before You Start
- **Discuss major changes** in an issue first
- **Check existing PRs** to avoid duplicate work
- **Focus on one feature/fix** per PR

#### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow coding standards (see below)
   - Add tests when applicable
   - Update documentation

3. **Test your changes**
   ```bash
   # Frontend tests
   npm run test
   npm run lint
   
   # Backend tests
   cd backend
   python -m pytest
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "feat: add new RSI divergence node"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

#### PR Guidelines

- **Clear title and description**
- **Link related issues** with "Closes #123"
- **Add screenshots** for UI changes
- **Update documentation** if needed
- **Ensure CI passes**

## 🏗️ Development Areas

### 🧱 Adding New VPL Nodes

VPL nodes are the building blocks of trading strategies. Here's how to add new ones:

#### 1. Frontend Node Definition
Create in `src/components/custom_nodes/[category]/your_node.js`:

```javascript
import { LGraphNode } from 'litegraph.js';

class YourNode extends LGraphNode {
  constructor() {
    super();
    this.title = "Your Node";
    this.desc = "Description of what it does";
    
    // Define inputs
    this.addInput("input_name", "number");
    
    // Define outputs  
    this.addOutput("output_name", "number");
    
    // Define properties (user configurable)
    this.addProperty("period", 14, "number");
  }
  
  onExecute() {
    // Node execution logic for frontend preview
    const input = this.getInputData(0);
    const period = this.properties.period;
    
    // Process data
    const output = processData(input, period);
    
    this.setOutputData(0, output);
  }
}

// Register the node
LiteGraph.registerNodeType("indicators/your_node", YourNode);
YourNode.title = "Your Node";
```

#### 2. Backend Node Processing
Add processing logic in `backend/pve/app/vpl/nodes.py`:

```python
def process_your_node(node, candle_index):
    """Process your custom node logic"""
    try:
        # Get inputs
        input_value = get_input_value(node, 0, candle_index)
        period = node.properties.get('period', 14)
        
        # Your processing logic here
        result = calculate_your_indicator(input_value, period)
        
        # Set output
        node.output_values[0] = result
        
    except Exception as e:
        logger.error(f"Error in your_node: {e}")
        node.output_values[0] = None
```

#### 3. Register in Frontend
Add to `src/stores/graph.ts`:

```javascript
import '../components/custom_nodes/indicators/your_node.js'
```

### 🔌 Adding Exchange Integrations

To add support for new exchanges:

1. **Create exchange adapter** in `backend/pve/app/exchanges/`
2. **Implement standard interface**:
   - `get_account_info()`
   - `place_order()`
   - `get_positions()`
   - `get_market_data()`
3. **Add configuration** in exchange selection
4. **Update frontend** exchange selection UI

### 📊 Adding Technical Indicators

1. **Research the indicator** - understand the mathematical formula
2. **Create the node** following the VPL node pattern above
3. **Add comprehensive tests** with known values
4. **Document parameters** and usage examples

## 🎨 Coding Standards

### Python (Backend)
- **PEP 8** compliance
- **Type hints** for function parameters and returns
- **Docstrings** for classes and functions
- **Error handling** with appropriate logging
- **Tests** for new functionality

### JavaScript/TypeScript (Frontend)
- **ESLint** configuration compliance
- **Prettier** formatting
- **TypeScript** types for new code
- **Vue 3 Composition API** for new components
- **Component documentation** with JSDoc

### General Guidelines
- **Clear variable names** that explain purpose
- **Small, focused functions** (< 50 lines when possible)
- **Comments** for complex business logic
- **No hardcoded values** - use configuration
- **Error boundaries** and graceful degradation

## 🧪 Testing

### Frontend Testing
```bash
npm run test        # Unit tests
npm run test:e2e    # End-to-end tests
npm run lint        # Code linting
```

### Backend Testing
```bash
cd backend
python -m pytest                    # All tests
python -m pytest tests/test_vpl.py  # Specific module
python -m pytest -v                 # Verbose output
```

### Test Requirements
- **Unit tests** for new functions/classes
- **Integration tests** for API endpoints
- **Node tests** for new VPL nodes with sample data
- **Mock external services** (exchanges, APIs)

## 📚 Documentation

### Code Documentation
- **Inline comments** for complex logic
- **Function docstrings** with parameters and return values
- **README updates** for new features
- **API documentation** for new endpoints

### User Documentation
- **Node documentation** in the docs viewer
- **Strategy examples** for new features
- **Setup guides** for new integrations
- **Troubleshooting** for common issues

## 🏷️ Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers bumped
- [ ] Changelog updated
- [ ] Security review completed

## 💡 Ideas for Contributions

### High Impact Areas
- **Performance optimizations** for backtesting engine
- **New technical indicators** (MACD, Ichimoku, etc.)
- **Additional exchanges** (Binance, Coinbase, etc.)
- **Mobile-responsive** design improvements
- **WebSocket stability** improvements

### Good First Issues
- **Documentation** improvements and examples
- **UI/UX** enhancements and bug fixes
- **Simple nodes** (basic math operations)
- **Test coverage** improvements
- **Code cleanup** and refactoring

## 🆘 Getting Help

- **GitHub Discussions** - General questions and ideas
- **GitHub Issues** - Bug reports and feature requests
- **Documentation** - Check existing docs first
- **Discord/Telegram** - Real-time community support

## 📄 License

By contributing to PVE, you agree that your contributions will be licensed under the Apache License 2.0.

---

Thank you for contributing to PVE! Your efforts help make algorithmic trading more accessible to everyone. 🚀 