# How to Enable MCP and Mem0 in Alice

Alice now has **both MCP (Model Context Protocol) and Mem0** systems enabled! Here's what you need to know:

## ✅ What's Already Enabled

### 1. **Mem0 Client** (Persistent Memory)
- **Status**: ✅ Enabled in [agent.py](../Alice_code/agent.py)
- **Purpose**: Remembers user conversations and preferences across sessions
- **Features**:
  - Stores user context and history
  - Learns from interactions
  - Provides personalized responses

### 2. **MCP Client** (Dynamic Tool System)
- **Status**: ✅ Enabled in [agent.py](../Alice_code/agent.py)
- **Purpose**: Connects to external MCP servers for extended functionality
- **Features**:
  - Dynamic tool loading
  - File system operations
  - Database connections
  - API integrations

## 🔧 Setup Required

### For Mem0 (Memory System)
1. **Get API Key**: Visit [Mem0](https://mem0.ai) and create an account
2. **Set Environment Variable**:
   ```bash
   # Add to your .env file or environment
   MEM0_API_KEY=your_mem0_api_key_here
   ```
3. **That's it!** Alice will automatically use memory for personalization

### For MCP (Tool Extension)
1. **MCP Servers**: The system is ready but needs MCP servers to connect to
2. **Available Servers**:
   - File system operations
   - Database connections
   - Web scraping
   - API integrations
   
3. **Example Setup** (in [agent.py](../Alice_code/agent.py#L24)):
   ```python
   # Uncomment and configure MCP servers
   fs_server = MCPServerSse("http://localhost:8080/sse", name="filesystem")
   mcp_servers.append(fs_server)
   ```

## 🚀 Benefits Now Available

### With Mem0 Enabled:
- Alice remembers your preferences
- Learns your working style
- Provides contextual responses
- Maintains conversation history

### With MCP Enabled:
- Alice can connect to external tools
- Dynamic capability expansion
- Modular tool architecture
- Enterprise integrations

## 🧪 Testing

### Test Mem0:
1. Set your `MEM0_API_KEY`
2. Run Alice: `python Alice_code/agent.py`
3. Have a conversation - Alice will remember it next time!

### Test MCP:
1. Configure MCP servers in agent.py
2. Run Alice
3. Alice will load additional tools dynamically

## 📁 Key Files Modified

- ✅ [agent.py](../Alice_code/agent.py) - Main agent with both systems
- ✅ [mcp_client/](../Alice_code/mcp_client/) - MCP integration code
- ✅ Requirements already include `mem0` package

## 🔮 Next Steps

1. **Get Mem0 API Key** for instant memory benefits
2. **Set up MCP servers** for additional capabilities
3. **Enjoy enhanced Alice** with persistent memory and dynamic tools!

---

*Both systems work independently - you can enable just Mem0, just MCP, or both together!*