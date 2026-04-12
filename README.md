# Gantry

## Dev notes

### Pre-commit

- Pls install the pre commit hooks to ensure code quality
- To install run: `uv run pre-commit install`

### Formatting

- Run `./scripts/tidy.sh` to format and sort imports. THIS IS VERY IMPORTANT!!!

### Running the dev server

1. Check out [Getting API key](#getting-api-keys)
1. Copy [`example.gantry.toml`](./example.gantry.toml) to `gantry.toml` then find all the `#apikey` and put yours in.
1. Start DBs and other services: `docker compose -f compose.dev.yaml up`
1. Install dependency: `uv sync --dev --frozen`
1. Migrate DB: `uv run gantry server -f gantry.toml migrate`
1. Start server: `uv run gantry server -f gantry.toml`

### Some useful scripts

- Generate `example.env` files for `.env` files: `scripts/gen-example-env.sh`
- Reset the database state: `scripts/reset-db.sh`. Remember to migrate and recreate the test account.

### Getting API keys

#### LLM

1. Go to <https://groq.com/> and get a free API key, this is `GROQ_API_KEY`

#### Google Programmable search API key

1. clc.fitus.edu.vn is not gonna work
1. Go to <https://programmablesearchengine.google.com/about/> and create a new customized search engine, then grab **Search engine ID**, this is `GOOGLE_PROGRAMMABLE_SEARCH_CX` env variable
1. Go to <https://developers.google.com/custom-search/v1/introduction> and get a free api key, this is `GOOGLE_PROGRAMMABLE_SEARCH_API_KEY` env variable