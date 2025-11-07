# User Dashboard

An OpenAI-esque dashboard application built with React.

## Stack

- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS 4
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Routing**: React Router DOM
- **Forms**: React Hook Form + Zod
- **HTTP Client**: Axios
- **Code Quality**: Biome
- **Package Manager**: pnpm

## Prerequisites

- Node.js (latest LTS [recommended](https://nodejs.org/en))
- pnpm (Install [here](https://pnpm.io/))

## Installation

```bash
pnpm install
```

## Development

Start the development server:

```bash
pnpm dev
```

## Building

Create a production build:

```bash
pnpm build
```

Preview the production build:

```bash
pnpm preview
```

## Code Quality
**Note:** All for the following steps are done automatically when you make a commit, handled by `husky` and `lint-staged`.

**Recommended:** Install the [Biome](https://biomejs.dev/reference/vscode/) extension for auto formatting and error highlighting.

Format code:

```bash
pnpm format
```

Lint code:

```bash
pnpm lint
```

Fix all issues:

```bash
pnpm check:fix
```

## Adding UI Components

This project uses [shadcn/ui](https://ui.shadcn.com/) for pre-built components.

Install components using the CLI:

```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add input
```

Browse available components at [ui.shadcn.com](https://ui.shadcn.com/).
