# API HUB

AI related APIs for medical applications

## Feat todo

- [ ] Login + SignUp with CSRF protection
  - [ ] Backend (DB schema, JWT, 2FA, https://fastapi.tiangolo.com/tutorial/security/)
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
  - [ ] Pick (Refer OpenAPI compatible frontend, Recommend: https://github.com/scalar/scalar)
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
