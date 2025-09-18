FROM python:3.13

# Install UV
ADD https://astral.sh/uv/0.8.11/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen

COPY . .

ENTRYPOINT [ "/app/scripts/dev.sh" ]
