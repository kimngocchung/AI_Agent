# Dockerfile cho Streamlit App (AI Agent)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in stages to improve caching and reliability
RUN pip install --no-cache-dir --upgrade pip

# 1. Install Core & Web libs (Lightweight)
RUN pip install --no-cache-dir \
    python-dotenv \
    pydantic \
    rich \
    streamlit \
    requests \
    Flask

# 2. Install Google GenAI & LangChain Core
RUN pip install --no-cache-dir \
    google-generativeai \
    langchain-core \
    langchain-google-genai

# 3. Install Heavy RAG & Community libs (Most likely to hang)
RUN pip install --no-cache-dir \
    faiss-cpu \
    langchain-community \
    langchain-huggingface \
    langchain \
    sentence-transformers

# Copy application code
COPY . .

# Create directory for chat history
RUN mkdir -p /app/data

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
