# API HUB

AI related APIs for medical applications

## Dev notes

### Getting API keys

#### LLM

1. Go to <https://groq.com/> and get a free API key, this is `GROQ_API_KEY`

#### Google Programmable search API key

1. clc.fitus.edu.vn is not gonna work
1. Go to <https://programmablesearchengine.google.com/about/> and create a new customized search engine, then grab **Search engine ID**, this is `GOOGLE_PROGRAMMABLE_SEARCH_CX` env variable
1. Go to <https://developers.google.com/custom-search/v1/introduction> and get a free api key, this is `GOOGLE_PROGRAMMABLE_SEARCH_API_KEY` env variable

### Running the dev server

### Setup the test account and env file

1. Register test account and api key: `docker exec api_hub_server uv run script/setup_test_account.py`
1. Docs site: <http://localhost:8000/docs/>
1. Env file:
    - `.env.postgres`:

    ```env
    POSTGRES_DB=tailm
    POSTGRES_USER=internet_crawler
    POSTGRES_PASSWORD=123456
    ```

    - `.env`:

    ```env
    CORE_DNS=postgresql://internet_crawler:123456@localhost:5432/tailm
    STAGE=local
    DEBUG=1

    GROQ_API_KEY=
    GOOGLE_PROGRAMMABLE_SEARCH_API_KEY=""
    GOOGLE_PROGRAMMABLE_SEARCH_CX=
    ```

## Frontend dev notes

1. Check out [Getting API key](#getting-api-keys) and [Setup test account and env file](#setup-the-test-account-and-env-file)
1. Build server: `docker compose build --ssh schema_repo_read_ssh_key=$HOME/.ssh/<ssh key with access to Venera-AI/patient-record-processing>`
1. Start server: `docker compose up`

## Feat todo

- [ ] Login + SignUp with CSRF protection
  - [ ] Backend (DB schema, JWT, 2FA, <https://fastapi.tiangolo.com/tutorial/security/>)
  - [ ] Frontend (React/Svelte/Solid/HTML, prefer static site gen from server to support CSRF)
- [ ] API key + permission control
  - [ ] CRUD API key frontend (if static login then this static too, no need for REST, better security)
  - [ ] Verify API key + Redis cache
  - [ ] Permission control (Enable/Disable individual APIs, maybe allow to enable API key REST through some special mechanism (an API key for CRUD API keys only))
  - DB Schema
- [ ] Vector DB
  - [ ] Pick one
  - [ ] Setup
- [ ] Docs site
  - [ ] Pick (Refer OpenAPI compatible frontend, Recommend: <https://github.com/scalar/scalar>)
  - [ ] Integrate with fastapi auto gen OpenAPI docs
- [ ] Conversation
  - [ ] DB schema
  - [ ] Messages
  - [ ] Media
  - [ ] Setup storage
  - [ ] Upload
  - [ ] Temporary link
- [ ] Crawler
  - [x] Setup (Crawl4ai)
  - [ ] Redis cache
  - [x] Search (Google Programmable API)
  - [x] Crawl + parse to markdown
  - [ ] Optimize markdown size
- [ ] AI search
  - [x] Agent
  - [ ] Prompt (Citation)
  - [ ] DB
  - [ ] Citation parser
- [ ] DB schema for storing tasks result
- [ ] Logging
- [ ] Storing & sharing api key
- [ ] Microservices? (Don't even dream of this)

## Stuff to do

- [ ] DB schemas
- [ ] API specs
  - [ ] Chat message schema
  - [ ] Support for realtime (like gemini/openai) in the future
  - [ ] Auto document from fast api
- [ ] Authentication
  - [x] Demo
  - [ ] Admin dashboard
  - [ ] User
  - [ ] API keys
- [ ] Authorization
  - [ ] Permission
- [ ] Usage
  - [ ] Rate limiting
  - [ ] Credits and pricing plan
  - [ ] Buy credits using money
  - [ ] Other way to acquire credits (discount, ...)
- [x] FHIR and VN_MOH schemas

- [ ] EHR Summarization
  - [x] Demo
- [x] RxAdvisor
  - [x] Demo
- [x] AI search
  - [x] Demo
- [ ] File handling
  - [ ] Temporary public URL
- [ ] Conversation
- [ ] Chat with medical models (Should be like openAI api)
- [ ] Rag tài liệu, bệnh viện up tài liệu lên rag trong đó, tài liệu về thủ tục đồ các thứ
- [ ] Rag bệnh án, tìm bệnh án tương tự
- [ ] OCR
- [ ] TTS
- [ ] STT
- [ ] Deep research cho bác sĩ
- [ ] AI hỗ trợ chuẩn đoán bệnh, Differential diagnosis

## How to run python script

`UV_ENV_FILE=.env uv run -m scripts.setup_test_account`

## Notes

- How to store Messages:
  - Many tables, each for a message part then use view for convenient query (sound stupid)
  - 1 table with jsonb
- Insert entry into db first then update generation result.
