# examplenv
Utilities to generate example.env and merge them

## How to install

```bash
uv add --dev git+https://github.com/thng292/examplenv
```
Or run it straigt from source
```bash
uvx git+https://github.com/thng292/examplenv
```

## Demo
### Gen example env
```bash
$ cat .env
# It retain whitespace and comment
VAR1="DO NOT COMMIT YOUR ENVS"

VAR2="But this is not very secret"

$ cat ./.env.dev
STAGE=DEV
# It cut your secret out too. By putting !SECRET in the comment
OPENAI_API_KEY=sk-ldfkjslfjldsjflsd # !SECRET
APP_SECRET=ThisIsASecret # !SECRET

$ cat ./.env.prod
STAGE=DEV
# !MASK-ON You can mask a region
OPENAI_API_KEY=sk-ldfkjslfjldsjflsd
APP_SECRET=ThisIsASecret
# !MASK-OFF Ignore this to mask to EOF

$ uv run examplenv gen
Searching for .env files in: /workspaces/examplenv
.env.dev -> example.env.dev
.env.prod -> example.env.prod
.env -> example.env

$ cat ./example.env
# Example environment variables for .env
# It retain whitespace and comment
VAR1="DO NOT COMMIT YOUR ENVS"

VAR2="But this is not very secret"

$ cat ./example.env.dev 
# Example environment variables for .env.dev
STAGE=DEV
# It cut your secret out too. By putting !SECRET in the comment
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY> # !SECRET
APP_SECRET=<YOUR_APP_SECRET> # !SECRET

$ cat ./example.env.prod
# Example environment variables for .env.prod
STAGE=DEV
# !MASK-ON You can mask a region
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
APP_SECRET=<YOUR_APP_SECRET>
# !MASK-OFF Ignore this to mask to EOF
```
