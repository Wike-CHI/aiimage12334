<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

White background image generator (白底图生成器) - An AI-powered web application that removes backgrounds from images using Gemini 3 Pro Image via a Python FastAPI backend.

## Commands

```bash
npm run dev          # Start Vite dev server (port 8080)
npm run build        # Production build
npm run build:dev    # Development build
npm run lint         # Run ESLint
npm run preview      # Preview production build
npm run tauri dev    # Start Tauri desktop app dev mode
npm run tauri build  # Build Tauri desktop app
```

## Architecture

### Core Stack
- **React 18 + TypeScript** with Vite 5.x
- **Tailwind CSS 3.4** with shadcn/ui component library
- **Python FastAPI** backend with MySQL database
- **TanStack Query 5** for server state
- **React Router 6** for routing
- **Tauri 2.0** for cross-platform desktop app

### Backend Structure

```
backend/
├── app/
│   ├── routes/           # API endpoints
│   │   ├── auth.py       # Authentication (JWT)
│   │   └── generation_v2.py  # V2 image processing API
│   ├── services/         # Business logic
│   │   ├── image_gen_v2.py   # V2 image processing pipeline
│   │   ├── task_queue.py     # Background task queue
│   │   └── prompt_template.py # AI prompt templates
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic schemas
│   ├── auth.py           # JWT handling
│   ├── config.py         # Environment configuration
│   └── main.py           # FastAPI application
├── init_db.py            # Database initialization
└── migrate_*.py          # Database migrations
```

### Path Alias
`@` maps to `src/` (configured in `tsconfig.json` and `vite.config.ts`)

### API Integration
- **Axios client** with JWT interceptor (`src/integrations/api/client.ts`)
- **V2 API** (recommended): `/api/v2/process/upload` - synchronous image processing
- **Legacy V1 API**: `/api/generate` - async processing with polling
- Backend URL configured via `VITE_API_URL` (defaults to `http://localhost:8001`)

### Key Patterns

1. **Server State**: TanStack Query hooks for data fetching, caching, and polling
2. **Auth**: React Context pattern via `useAuth()` hook with JWT tokens
3. **Image Processing**: Axios API calls with template chains (remove_bg -> standardize -> ecommerce -> color_correct)
4. **UI Components**: shadcn/ui style - base components in `ui/`, composite components at root level

### Important Files

- `src/App.tsx` - Providers hierarchy (QueryClient, Auth, Router)
- `src/pages/Index.tsx` - Main generator UI
- `src/hooks/useAuth.tsx` - Auth context with signIn/signUp/signOut
- `src/hooks/useTaskHistory.ts` - Task history with optional polling
- `src/hooks/useImageGenerationV2.ts` - Synchronous V2 image processing
- `src/integrations/api/client.ts` - Axios client with JWT interceptor + API endpoints
- `src/config/index.ts` - Centralized configuration
- `src/lib/utils.ts` - `cn()` utility (clsx + tailwind-merge)
