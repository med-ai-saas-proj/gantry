FROM python:3.13

# Install UV
ADD https://astral.sh/uv/0.8.11/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Add GitHub's public key to known_hosts
# RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --all-extras --no-dev
RUN uv run --no-sync crawl4ai-setup

COPY . .

ENTRYPOINT [ "/app/scripts/prod.sh" ]