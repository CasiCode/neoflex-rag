FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY requirements.txt .
COPY config.yaml .
COPY constants.py .
COPY neoflex_rag.ipynb .
COPY prompts/ prompts/
COPY web_scrapers.py

RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN playwright install

EXPOSE 8888

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]
