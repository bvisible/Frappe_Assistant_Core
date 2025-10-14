# Changelog

All notable changes to Frappe Assistant Core will be documented in this file.

## [2.2.0] - 2025-10-13 - StreamableHTTP Transport Migration

### 🎯 Major Release - Transport Layer Overhaul

This release migrates Frappe Assistant Core from STDIO bridge to StreamableHTTP transport with OAuth 2.0 authentication, enabling web-based MCP clients and improving security, compatibility, and deployment flexibility.

#### Transport Layer Migration
- **Migrated** from STDIO subprocess bridge to HTTP-based StreamableHTTP transport
- **Replaced** API key authentication with industry-standard OAuth 2.0
- **Enabled** web-based client support (Claude Web, browser-based tools)
- **Improved** cross-platform compatibility and deployment options
- **Eliminated** subprocess management complexity

#### OAuth 2.0 Security Implementation
- **OAuth 2.0 Dynamic Client Registration** (RFC 7591) for automatic client setup
- **Authorization Server Metadata** (RFC 8414) for endpoint discovery
- **Protected Resource Metadata** (RFC 9728) for resource information
- **PKCE Support** (RFC 7636) for secure authorization code flow
- **Automatic token refresh** with refresh_token grant type
- **CORS handling** for public clients (browser-based)
- **Discovery endpoints** at /.well-known/openid-configuration

#### Custom FAC MCP Server
- **Built custom MCP server** optimized for Frappe's data types and architecture
- **Fixed JSON serialization** for datetime, Decimal, and other non-JSON Frappe types
- **Removed Pydantic dependency** for lighter footprint and better Frappe integration
- **Enhanced error handling** with full tracebacks for debugging
- **Deep Frappe integration** with session, permissions, and ORM
- **Tool adapter pattern** for seamless BaseTool compatibility

#### Documentation Improvements
- **Converted all diagrams** from ASCII to Mermaid format for GitHub rendering
- **Rewrote Getting Started** with LLM-specific instructions (Claude Desktop, ChatGPT, Claude Web)
- **Added comprehensive OAuth setup guide** with troubleshooting
- **Added MCP StreamableHTTP integration guide** with technical details
- **Simplified onboarding** to zero manual steps after installation

#### API & Endpoints
- **MCP Endpoint**: `/api/method/frappe_assistant_core.api.fac_endpoint.handle_mcp`
- **OAuth Endpoints**: authorize, token, register, introspect, revoke
- **Discovery Endpoints**: /.well-known/openid-configuration, oauth-authorization-server, oauth-protected-resource
- **HEAD method support** for connectivity checks (Claude Web compatibility)
- **Bearer token validation** middleware for all MCP requests

#### Configuration & UX
- **Simplified configuration** via site_config.json for CORS
- **Frappe v15/v16 compatibility** with dual CORS mechanism
- **Default-enabled assistant access** for new users
- **FAC Admin page** displaying MCP endpoint URL
- **Automatic custom field setup** during installation
- **Proper uninstall cleanup** removing custom fields

### 🐛 Bug Fixes

#### Authentication & CORS
- **Fixed CORS headers** for OPTIONS preflight requests
- **Added MCP-Protocol-Version** to CORS allowed headers
- **Fixed 401 responses** with proper WWW-Authenticate headers per RFC 9728
- **Fixed HTTP 417 errors** with proper HTTP method registration

#### Plugin Management
- **Fixed plugin toggle** to use plugin IDs instead of display names
- **Fixed state persistence** after page refresh
- **Added plugin_id fields** to API responses for correct identification

#### Migration System
- **Fixed missing patch files** causing ModuleNotFoundError
- **Added idempotent patches** for safe fresh installs and upgrades
- **Added assistant_enabled default** update patch
- **Added page rename patch** (assistant-admin → fac-admin)

### ✨ New Features

#### Security
- **OAuth 2.0 authorization** with PKCE for all flows
- **Bearer token authentication** for API access
- **Token expiration** and automatic refresh
- **Dynamic client registration** with origin validation
- **Public and confidential** client support
- **Token revocation** and introspection endpoints

#### Developer Experience
- **MCP Inspector integration** with Quick OAuth Flow
- **Custom Python client examples** in documentation
- **Comprehensive debugging** with OAuth error logging
- **Connection pooling** support for HTTP clients
- **Auto-discovery** via well-known endpoints

#### Admin Features
- **FAC Admin page** with endpoint URL display
- **Plugin enable/disable** functionality
- **Tool registry display** with categories
- **Real-time monitoring** and health checks

### 🔧 Architecture Changes

| Feature | Before (STDIO) | After (StreamableHTTP) |
|---------|---------------|----------------------|
| **Transport** | stdin/stdout subprocess | HTTP POST requests |
| **Authentication** | API Key in environment | OAuth 2.0 Bearer tokens |
| **Client Support** | Subprocess-capable only | Any HTTP-capable client |
| **Security** | Basic API key | Industry-standard OAuth |
| **Discovery** | Manual configuration | Auto-discovery via .well-known |
| **Token Management** | No refresh | Automatic token refresh |
| **Web Compatibility** | ❌ No | ✅ Yes |
| **Deployment** | Complex subprocess setup | Simple HTTP endpoint |

### 🚨 Breaking Changes

#### Migration Required
- **STDIO bridge no longer supported** - must migrate to StreamableHTTP
- **API key authentication removed** - must use OAuth 2.0
- **Client configuration changes** - update MCP client configs

#### Migration Steps

1. **Update Application**
   ```bash
   cd apps/frappe_assistant_core
   git pull
   bench migrate
   ```

2. **Configure OAuth**
   - Go to Assistant Core Settings
   - Enable Dynamic Client Registration
   - Configure Allowed Public Client Origins (if needed)

3. **Update MCP Clients**
   - **Claude Desktop**: Update config to StreamableHTTP with OAuth discovery
   - **MCP Inspector**: Use OAuth authentication flow
   - **Custom Clients**: Implement OAuth 2.0 with PKCE

4. **Test Integration**
   - Visit FAC Admin page
   - Copy MCP endpoint URL
   - Authenticate with OAuth flow

### 📊 Benefits of Migration

- ✅ **Better Security**: OAuth 2.0 with PKCE vs simple API keys
- ✅ **Web Client Support**: Claude Web, browser-based tools now work
- ✅ **Simpler Deployment**: HTTP endpoint vs subprocess management
- ✅ **Better Error Handling**: HTTP status codes vs stdout parsing
- ✅ **Auto-Discovery**: Clients discover endpoints automatically
- ✅ **Token Refresh**: Long-lived sessions with automatic renewal
- ✅ **Cross-Platform**: Works anywhere HTTP works

### 📝 Documentation Updates

#### New Guides
- [MCP_STREAMABLEHTTP_GUIDE.md](../architecture/MCP_STREAMABLEHTTP_GUIDE.md) - Complete technical integration guide
- [oauth_setup_guide.md](../getting-started/oauth/oauth_setup_guide.md) - OAuth configuration guide
- [OAUTH_CORS_CONFIGURATION.md](../getting-started/oauth/OAUTH_CORS_CONFIGURATION.md) - CORS setup guide

#### Updated Documentation
- [README.md](../../README.md) - Simplified getting started with LLM-specific steps
- All architecture diagrams converted to Mermaid format
- Updated version references from v2.0.0 to v2.2.0

## [2.1.0] - 2025-08-29 - Major Performance & Feature Release

### 🌟 Major Enhancements

#### 📄 Enhanced File Processing & Data Science Plugin
- **New Tool**: `extract_file_content` - Comprehensive file support (PDF, images/OCR, spreadsheets, documents)
- **LLM-Optimized**: Content extraction optimized for AI analysis
- **Batch Processing**: Efficient multi-file handling capabilities
- **Smart Formatting**: Structure preservation for better AI understanding

#### ⚙️ Revamped Admin Interface
- **Modern UI/UX**: Complete redesign with intuitive controls
- **Real-time Monitoring**: Live plugin status and health indicators
- **Bulk Operations**: Multi-select plugin management
- **Enhanced Configuration**: Visual configuration management with validation

#### 📊 Improved Reporting Tools
- **Smart Discovery**: Intelligent report finding and filtering
- **Requirements Analysis**: Automatic parameter detection
- **Template System**: Pre-configured report templates
- **Batch Generation**: Execute multiple reports simultaneously

#### ⚡ Concurrency & Performance Improvements
- **Thread Pool Architecture**: Multi-threaded request processing (+300% throughput)
- **Optimized Timeouts**: Reduced from 30s to 5s (Claude-compatible)
- **Memory Efficiency**: 15% reduction in memory footprint
- **Faster Plugin Loading**: 40% improvement in discovery time

### 🔧 Technical Improvements

#### Bridge Architecture Enhancements
- **Concurrent Processing**: Thread pool in `frappe_assistant_stdio_bridge.py`
- **Timeout Optimization**: Aligned with Claude's 6-second limits
- **Error Handling**: Explicit timeout error handling
- **Local Development**: Default server URL changed to `http://localhost:8000`

#### Configuration & Manifest Updates
- **Version 2.1.0**: Updated manifest metadata
- **Enhanced Validation**: Boolean controls and field validation
- **Tool Descriptions**: Improved guidance for best practices
- **Python Requirements**: Explicit runtime version specifications

### 🐛 Bug Fixes & Stability
- **Fixed**: Thread safety in concurrent operations
- **Fixed**: Memory leaks in long-running processes
- **Fixed**: Admin interface loading on slower connections
- **Enhanced**: Error recovery and connection stability
- **Improved**: Resource cleanup and garbage collection

### 📈 Performance Metrics
- **+300% throughput** with thread pool architecture
- **+83% faster response times** with optimized timeouts
- **-15% memory footprint** with efficiency improvements
- **+40% faster** plugin loading and discovery

## [2.0.0] - 2025-07-22 - Major Architecture Evolution

**License Change: MIT → AGPL-3.0** | **Breaking Changes: Yes**

This major release transforms Frappe Assistant Core into a fully extensible, plugin-based platform with enhanced visualization capabilities and stronger open source protection through AGPL-3.0 licensing.

### 🌟 Release Highlights

- **🏗️ Plugin-Based Architecture**: Custom tool development with auto-discovery and runtime management
- **📊 Enhanced Visualization System**: Rebuilt chart engine with advanced dashboard support
- **🔒 Stronger Open Source Protection**: AGPL-3.0 license ensures modifications remain open source
- **🐛 Major Bug Fixes**: Tool reliability improvements and data processing enhancements
- **⚡ Performance Improvements**: 30% faster tool execution, 25% reduced memory footprint

### 🚀 New Features

#### 🏗️ Plugin-Based Architecture

- **Custom Tool Development**: Create your own tools using the new plugin system
- **Auto-Discovery**: Zero-configuration plugin loading and registration
- **Runtime Management**: Enable/disable plugins through web interface
- **Extensible Framework**: Clean APIs for third-party developers

#### 📊 Enhanced Visualization System

- **Rebuilt Chart Engine**: Complete overhaul of chart creation system
- **Advanced Dashboard Support**: Improved dashboard creation and management
- **Multiple Chart Types**: Bar, Line, Pie, Scatter, Heatmap, Gauge, and more
- **Better Data Handling**: Improved data processing and validation
- **KPI Cards**: Professional metric tracking with trend indicators

#### 🔒 Stronger Open Source Protection

- **AGPL-3.0 License**: Ensures modifications remain open source
- **Complete Compliance**: All 125+ files properly licensed with headers
- **Network Service Requirements**: Source disclosure for SaaS usage
- **Community Growth**: Prevents proprietary forks while encouraging contributions

### 🚨 Breaking Changes & Migration

#### License Impact

⚠️ **Critical**: Review AGPL-3.0 compliance requirements

- All derivative works must be AGPL-3.0 licensed
- SaaS deployments must provide source code access to users
- Commercial use requires AGPL compliance or dual licensing

#### API Changes

⚠️ **Development Impact**: Some APIs have been refactored

- **Plugin Registration**: New plugin-based system
- **Tool Configuration**: Updated configuration format
- **Hook System**: Enhanced with external app support

#### Migration Steps

##### For End Users

1. **License Review**: Understand AGPL-3.0 implications
2. **Update Deployment**: Test in staging environment first
3. **Verify Functionality**: Ensure all tools work as expected

##### For Developers

1. **License Headers**: Add AGPL-3.0 headers to custom code
2. **Plugin Migration**: Convert custom tools to plugin architecture
3. **API Updates**: Update to new plugin registration system

##### For SaaS Providers

1. **Compliance Review**: Ensure AGPL-3.0 compliance
2. **Source Availability**: Implement source code provision mechanism
3. **User Notification**: Inform users of their source code rights

### 📊 Performance Improvements

#### System Optimization

- **30% faster tool execution** through optimized plugin loading
- **25% reduced memory footprint** with better resource management
- **Enhanced error recovery** with graceful failure handling
- **50% faster repeated operations** with improved caching system

#### Scalability Enhancements

- **Plugin lazy loading** reduces startup time
- **Concurrent tool execution** support
- **Better database query optimization**
- **Enhanced connection pooling**

## [1.2.0] - Modern Architecture Features

### 🏗️ Architecture Improvements

- **📦 Modular Handlers**: Separated API concerns into focused modules
- **🔧 Centralized Constants**: All configuration and strings in dedicated module
- **📝 Professional Logging**: Structured logging with proper levels and formatting
- **📋 Modern Packaging**: pyproject.toml with development and analysis dependency groups
- **🐛 Error Handling**: Robust error management with centralized error codes
- **🔍 Tool Execution Engine**: Dedicated tool validation and execution system

## [1.1.0] - Enhanced Features

### New Capabilities

- **🧪 Data Science Plugin**: Python execution and statistical analysis
- **📊 Visualization Plugin**: Chart and dashboard creation
- **⚡ Batch Processing Plugin**: Bulk operations with progress tracking
- **🔄 Modern MCP Protocol**: JSON-RPC 2.0 with modular handler architecture
- **🌐 SSE Bridge Integration**: Real-time streaming communication with Claude API

## [1.0.0] - Initial Release

### Core Features

- **📄 Document Operations**: Complete CRUD operations for Frappe documents
- **📈 Advanced Reporting**: Execute Frappe reports with debugging support
- **🔍 Advanced Analytics**: Statistical analysis and business intelligence
- **📄 File Processing**: PDF, image OCR, and spreadsheet content extraction
- **🔎 Global Search**: Search across all accessible documents and data
- **🗂️ Metadata Access**: Query DocType schemas and permissions
- **📋 Audit Logging**: Comprehensive operation tracking
- **⚙️ Admin Interface**: Web-based management interface
- **🔧 Tool Registry**: Auto-discovery tool system

### Security & Permissions

- **🛡️ Enterprise Security**: Built-in permissions and audit logging
- **🔐 Secure Authentication**: API key and session validation
- **🔒 Permission Integration**: Respects Frappe's permission system
- **📋 Audit Trail**: Complete operation tracking with user context

### Integration Features

- **🔌 Plug & Play AI Integration**: Seamless Claude and AI assistant connectivity
- **🚀 Production Ready**: Rate limiting and robust error handling
- **📝 Professional Logging**: Structured logging for debugging and monitoring
- **🤝 Community Driven**: Open source with active development

---

## Roadmap

### Planned Features (v2.1.0)

- **Websocket Integration**: Enhanced real-time communication
- **Batch Processing Support**: Advanced bulk operation capabilities
- **Advanced Analytics**: Machine learning integrations
- **Real-time Collaboration**: WebSocket-based features

### Long-term Vision (v3.0.0)

- **Multi-tenant Architecture**: Enhanced scalability
- **Advanced Security**: Enhanced authentication options
- **International Support**: Multi-language capabilities
- **Cloud Integration**: Native cloud service integration

---

*For detailed technical changes, see individual commit messages and pull requests.*