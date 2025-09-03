# FastMCP v2.0 - Dokumentasi Lengkap 🚀

## Daftar Isi
- [Pengenalan](#pengenalan)
- [Apa itu Model Context Protocol (MCP)?](#apa-itu-model-context-protocol-mcp)
- [Mengapa Menggunakan FastMCP?](#mengapa-menggunakan-fastmcp)
- [Instalasi](#instalasi)
- [Konsep Dasar](#konsep-dasar)
- [Fitur Lanjutan](#fitur-lanjutan)
- [Contoh Implementasi](#contoh-implementasi)
- [Menjalankan Server](#menjalankan-server)
- [Panduan Deployment](#panduan-deployment)
- [Testing](#testing)
- [Kontribusi](#kontribusi)
- [Referensi](#referensi)

---

## Pengenalan

FastMCP adalah framework standar untuk bekerja dengan Model Context Protocol (MCP). FastMCP 2.0 adalah versi yang aktif dikembangkan dan menyediakan toolkit lengkap untuk bekerja dengan ekosistem MCP.

### Key Features
- 🚀 **Fast**: Interface tingkat tinggi dengan kode minimal
- 🍀 **Simple**: Membangun MCP server dengan boilerplate minimal  
- 🐍 **Pythonic**: Terasa natural bagi developer Python
- 🔍 **Complete**: Platform komprehensif untuk semua use case MCP

### Statistik Project
- ⭐ **16.8k+ stars** di GitHub
- 🍴 **1.1k+ forks**
- 👥 **93+ contributors**
- 📦 **Digunakan oleh 4.2k+ repositories**

---

## Apa itu Model Context Protocol (MCP)?

Model Context Protocol (MCP) adalah cara standar baru untuk menyediakan konteks dan tools kepada LLM Anda. MCP sering digambarkan sebagai "port USB-C untuk AI", menyediakan cara seragam untuk menghubungkan LLM ke resources yang dapat mereka gunakan.

### MCP Server dapat:
- **Expose data** melalui Resources (seperti GET endpoints)
- **Menyediakan functionality** melalui Tools (seperti POST endpoints)
- **Mendefinisikan interaction patterns** melalui Prompts
- Dan masih banyak lagi!

---

## Mengapa Menggunakan FastMCP?

Protocol MCP sangat powerful tetapi implementasinya melibatkan banyak boilerplate - setup server, protocol handlers, content types, error management. FastMCP menangani semua detail protocol yang kompleks, sehingga Anda dapat fokus membangun tools yang hebat.

### Keunggulan FastMCP 2.0:
- **Client libraries** terintegrasi
- **Authentication systems** built-in
- **Deployment tools** siap pakai
- **Integrasi** dengan platform AI major
- **Testing frameworks** komprehensif
- **Production-ready infrastructure** patterns

---

## Instalasi

### Menggunakan uv (Recommended)
```bash
uv pip install fastmcp
```

### Menggunakan pip
```bash
pip install fastmcp
```

### Verifikasi Instalasi
```python
import fastmcp
print(fastmcp.__version__)
```

---

## Konsep Dasar

### 1. FastMCP Server

Server adalah objek pusat yang merepresentasikan aplikasi MCP Anda. Ia menyimpan tools, resources, dan prompts Anda.

```python
from fastmcp import FastMCP

# Membuat instance server
mcp = FastMCP("Demo Server 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Menambahkan dua angka"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

### 2. Tools

Tools memungkinkan LLM untuk melakukan aksi dengan mengeksekusi fungsi Python Anda. Ideal untuk komputasi, API calls, atau side effects.

```python
@mcp.tool
def multiply(a: float, b: float) -> float:
    """Mengalikan dua angka."""
    return a * b

@mcp.tool
async def fetch_weather(city: str) -> dict:
    """Mengambil data cuaca untuk kota tertentu."""
    # Implementasi async API call
    return {"city": city, "temp": 25, "condition": "sunny"}
```

### 3. Resources & Templates

Resources expose data sources read-only (seperti GET requests). Gunakan `@mcp.resource("your://uri")`.

```python
# Static resource
@mcp.resource("config://version")
def get_version(): 
    return "2.0.1"

# Dynamic resource template
@mcp.resource("users://{user_id}/profile")
def get_profile(user_id: int):
    return {"name": f"User {user_id}", "status": "active"}
```

### 4. Prompts

Prompts mendefinisikan template pesan yang dapat digunakan kembali untuk memandu interaksi LLM.

```python
@mcp.prompt
def summarize_request(text: str) -> str:
    """Generate a prompt asking for a summary."""
    return f"Please summarize the following text:\n\n{text}"

@mcp.prompt
def code_review_prompt(code: str, language: str) -> str:
    """Prompt untuk code review."""
    return f"Review the following {language} code for best practices:\n\n```{language}\n{code}\n```"
```

### 5. Context

Access kemampuan MCP session dalam tools, resources, atau prompts Anda dengan menambahkan parameter `ctx: Context`.

```python
from fastmcp import FastMCP, Context

mcp = FastMCP("My MCP Server")

@mcp.tool
async def process_data(uri: str, ctx: Context):
    # Log message ke client
    await ctx.info(f"Processing {uri}...")

    # Baca resource dari server
    data = await ctx.read_resource(uri)

    # Minta client LLM untuk summarize data
    summary = await ctx.sample(f"Summarize: {data.content[:500]}")

    # Return summary
    return summary.text
```

### 6. MCP Clients

Berinteraksi dengan MCP server secara programmatik menggunakan `fastmcp.Client`.

```python
from fastmcp import Client

async def main():
    # Connect via stdio ke script lokal
    async with Client("my_server.py") as client:
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(f"Result: {result.text}")

    # Connect via SSE
    async with Client("http://localhost:8000/sse") as client:
        # ... gunakan client
        pass
```

---

## Fitur Lanjutan

### 1. Proxy Servers

Membuat FastMCP server yang bertindak sebagai intermediary untuk server MCP lain.

```python
# Proxy untuk server remote
proxy = FastMCP.as_proxy("https://api.example.com/mcp")

# Proxy untuk server lokal dengan transport bridge
local_proxy = FastMCP.as_proxy("python ./remote_server.py")
```

### 2. Composing MCP Servers

Membangun aplikasi modular dengan mounting beberapa instance `FastMCP`.

```python
# Server utama
main_server = FastMCP("Main Server")

# Sub-servers
auth_server = FastMCP("Auth Server")
data_server = FastMCP("Data Server")

# Mount sub-servers
main_server.mount("/auth", auth_server)
main_server.mount("/data", data_server)
```

### 3. OpenAPI & FastAPI Integration

Generate FastMCP server dari OpenAPI spec atau FastAPI application.

```python
# Dari OpenAPI specification
openapi_server = FastMCP.from_openapi("https://api.example.com/openapi.json")

# Dari FastAPI application
from fastapi import FastAPI
fastapi_app = FastAPI()
mcp_server = FastMCP.from_fastapi(fastapi_app)
```

### 4. Authentication & Security

FastMCP menyediakan dukungan authentication built-in untuk mengamankan server dan client.

```python
# Server dengan authentication
mcp = FastMCP("Secure Server", auth_provider=my_auth_provider)

# Client dengan authentication
async with Client("https://secure-server.com/mcp", auth=my_auth) as client:
    # ... gunakan authenticated client
    pass
```

---

## Contoh Implementasi

### Server Sederhana dengan Multiple Tools

```python
from fastmcp import FastMCP, Context
import httpx
import json

mcp = FastMCP("Utility Server")

@mcp.tool
def calculate_area(length: float, width: float) -> float:
    """Menghitung luas persegi panjang."""
    return length * width

@mcp.tool
async def fetch_quote(ctx: Context) -> dict:
    """Mengambil quote inspirational dari API."""
    await ctx.info("Fetching inspirational quote...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.quotable.io/random")
        quote_data = response.json()
    
    await ctx.info("Quote fetched successfully!")
    return {
        "quote": quote_data["content"],
        "author": quote_data["author"]
    }

@mcp.resource("system://info")
def system_info():
    """Informasi sistem server."""
    return {
        "server_name": "Utility Server",
        "version": "1.0.0",
        "available_tools": ["calculate_area", "fetch_quote"]
    }

@mcp.prompt
def math_tutor_prompt(problem: str) -> str:
    """Prompt untuk math tutoring."""
    return f"""You are a helpful math tutor. Please solve this problem step by step and explain your reasoning:

Problem: {problem}

Please provide:
1. Step-by-step solution
2. Explanation of concepts used
3. Tips for similar problems"""

if __name__ == "__main__":
    mcp.run()
```

### Client untuk Testing Server

```python
import asyncio
from fastmcp import Client

async def test_server():
    async with Client("python server.py") as client:
        # List available tools
        tools = await client.list_tools()
        print("Available tools:", [tool.name for tool in tools])
        
        # Test calculate_area tool
        result = await client.call_tool("calculate_area", {
            "length": 10.0, 
            "width": 5.0
        })
        print(f"Area calculation: {result.text}")
        
        # Test fetch_quote tool
        quote_result = await client.call_tool("fetch_quote", {})
        quote_data = json.loads(quote_result.text)
        print(f"Quote: '{quote_data['quote']}' - {quote_data['author']}")
        
        # Read system info resource
        info = await client.read_resource("system://info")
        print("System info:", info.content)

if __name__ == "__main__":
    asyncio.run(test_server())
```

---

## Menjalankan Server

### Transport Protocols

FastMCP mendukung tiga transport protocols:

#### 1. STDIO (Default)
Terbaik untuk tools lokal dan command-line scripts.

```python
mcp.run(transport="stdio")  # Default
# atau
mcp.run()  # transport argument opsional
```

#### 2. HTTP (Streamable)
Direkomendasikan untuk web deployments.

```python
mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
```

#### 3. SSE (Server-Sent Events)
Untuk kompatibilitas dengan existing SSE clients.

```python
mcp.run(transport="sse", host="127.0.0.1", port=8000)
```

### Command Line

Jalankan server menggunakan FastMCP CLI:

```bash
# Jalankan server dari file
fastmcp run server.py

# Dengan custom host dan port
fastmcp run server.py --host 0.0.0.0 --port 8080

# Dengan transport tertentu
fastmcp run server.py --transport sse
```

---

## Panduan Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY server.py .

EXPOSE 8000

CMD ["python", "-m", "fastmcp", "run", "server.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  fastmcp-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - LOG_LEVEL=info
    volumes:
      - ./data:/app/data
```

### Production Considerations

1. **Environment Variables**: Gunakan environment variables untuk konfigurasi
2. **Logging**: Setup proper logging untuk monitoring
3. **Health Checks**: Implementasikan health check endpoints
4. **Rate Limiting**: Tambahkan rate limiting untuk production
5. **Authentication**: Always gunakan authentication di production

---

## Testing

### Unit Testing dengan Pytest

```python
import pytest
from fastmcp import FastMCP, Client

@pytest.fixture
def sample_server():
    mcp = FastMCP("Test Server")
    
    @mcp.tool
    def add_numbers(a: int, b: int) -> int:
        return a + b
    
    return mcp

@pytest.mark.asyncio
async def test_add_numbers(sample_server):
    async with Client(sample_server) as client:
        result = await client.call_tool("add_numbers", {"a": 5, "b": 3})
        assert result.text == "8"

@pytest.mark.asyncio
async def test_list_tools(sample_server):
    async with Client(sample_server) as client:
        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "add_numbers"
```

### Integration Testing

```python
import httpx
import pytest
from fastmcp import FastMCP
import threading
import time

@pytest.fixture
def http_server():
    mcp = FastMCP("HTTP Test Server")
    
    @mcp.tool
    def ping() -> str:
        return "pong"
    
    # Start server in background thread
    def run_server():
        mcp.run(transport="http", host="localhost", port=8999)
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    time.sleep(1)  # Wait for server to start
    
    yield "http://localhost:8999"

@pytest.mark.asyncio
async def test_http_endpoint(http_server):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{http_server}/mcp")
        assert response.status_code == 200
```

---

## Kontribusi

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (Recommended)

### Setup Development Environment

1. Clone repository:
```bash
git clone https://github.com/jlowin/fastmcp.git
cd fastmcp
```

2. Create dan sync environment:
```bash
uv sync
```

3. Activate virtual environment:
```bash
source .venv/bin/activate  # Linux/Mac
# atau
.venv\Scripts\activate     # Windows
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
uv run pytest --cov=src --cov=examples --cov-report=html
```

### Code Quality

FastMCP menggunakan `pre-commit` untuk formatting, linting, dan type-checking.

```bash
# Install hooks
uv run pre-commit install

# Run manually
pre-commit run --all-files
```

### Pull Request Guidelines

1. Fork repository di GitHub
2. Create feature branch dari `main`
3. Buat perubahan, termasuk tests dan dokumentasi
4. Pastikan tests dan pre-commit hooks pass
5. Commit perubahan dan push ke fork Anda
6. Buka pull request ke `main` branch

---

## Referensi

### Links Penting
- **Documentation**: https://gofastmcp.com/
- **GitHub Repository**: https://github.com/jlowin/fastmcp
- **PyPI Package**: https://pypi.org/project/fastmcp
- **Official MCP Documentation**: https://modelcontextprotocol.io/

### API Documentation
- **LLM-friendly docs**: https://gofastmcp.com/llms.txt
- **Complete docs**: https://gofastmcp.com/llms-full.txt

### Community
- **Issues**: https://github.com/jlowin/fastmcp/issues
- **Discussions**: https://github.com/jlowin/fastmcp/discussions
- **Pull Requests**: https://github.com/jlowin/fastmcp/pulls

### License
FastMCP adalah open source dengan lisensi Apache-2.0.

### Topics
- Python
- MCP (Model Context Protocol)
- AI Agents
- LLMs
- MCP Servers
- MCP Tools
- MCP Clients

---

**Made with ☕️ by [Prefect](https://www.prefect.io/)**

*Dokumentasi ini dibuat pada tanggal 26 Agustus 2025 berdasarkan FastMCP v2.11.3*
