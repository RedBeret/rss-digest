FROM python:3.12-slim

WORKDIR /app

# Install signal-cli (optional — only needed for Signal channel)
# Uncomment and update if you want Signal support:
# RUN apt-get update && apt-get install -y default-jre wget && \
#     wget -q https://github.com/AsamK/signal-cli/releases/download/v0.13.4/signal-cli-0.13.4-Linux-native.tar.gz && \
#     tar -xzf signal-cli-*.tar.gz -C /usr/local && \
#     ln -s /usr/local/signal-cli-*/bin/signal-cli /usr/local/bin/signal-cli && \
#     rm signal-cli-*.tar.gz

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

# Mount your config and data here
VOLUME ["/config", "/data"]

# Override DB path via environment variable
ENV RSS_DIGEST_DB=/data/feeds.db

ENTRYPOINT ["rss-digest"]
CMD ["--help"]
