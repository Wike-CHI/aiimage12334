# Project Context

## Purpose
AI-powered white background image generator (白底图生成器). Removes backgrounds from uploaded images using Gemini AI to create clean white-background product images. Features user authentication, credit system, and task history.

## Tech Stack

### Frontend
- **Framework**: React 18.3 + TypeScript + Vite 5.x
- **UI Components**: shadcn/ui (52+ components in `src/components/ui/`)
- **Styling**: Tailwind CSS 3.4
- **State Management**: TanStack Query 5 (server state), React Context (auth)
- **Routing**: React Router DOM 6.x
- **Forms**: React Hook Form + Zod

### Backend
- **Framework**: FastAPI 0.109
- **Database**: MySQL + SQLAlchemy 2.0
- **Auth**: JWT (python-jose) + bcrypt
- **HTTP Client**: httpx

### External Services
- **AI**: Gemini 1.5 Flash API (image background removal)

## Project Conventions

### Code Style
- Path alias: `@` maps to `src/` (configured in tsconfig.json and vite.config.ts)
- Component file naming: PascalCase (e.g., `ImageUploader.tsx`)
- Hook file naming: camelCase with `use` prefix (e.g., `useAuth.tsx`)
- Utility function: `cn()` in `src/lib/utils.ts` for className merging

### Architecture Patterns

#### Frontend
```
src/
├── components/
│   ├── ui/           # shadcn/ui base components
│   └── *.tsx         # Composite components
├── hooks/
│   ├── useAuth.tsx   # Auth context provider
│   └── useTaskHistory.ts  # Task history with server state
├── integrations/
│   └── api/client.ts # Axios HTTP client for FastAPI
├── pages/
│   ├── Index.tsx     # Main generator UI
│   └── Auth.tsx      # Authentication page
└── lib/utils.ts      # Utility functions
```

#### Backend
```
backend/app/
├── config.py         # Pydantic Settings (env vars)
├── database.py       # SQLAlchemy engine + session
├── models.py         # SQLAlchemy models (User, GenerationTask)
├── schemas.py        # Pydantic schemas for API
├── auth.py           # JWT token handling
├── main.py           # FastAPI app entry
└── routes/
    ├── auth.py       # /api/auth endpoints
    └── generation.py # /api/generate endpoints
```

### Git Workflow
- Main branch: `main`
- Feature branches: `feature/*`
- Commit messages: English, imperative mood

## Domain Context
- User registration/login with email + password
- New users get 10 credits by default
- Each image generation consumes 1 credit
- Generated images are stored locally in `backend/uploads/` and `backend/results/`

## Important Constraints
- Keep Supabase cloud dependencies removed (migrated to local FastAPI + MySQL)
- Gemini API key required for image generation functionality

## External Dependencies
- **Gemini API**: `https://generativelanguage.googleapis.com` for AI image processing
- **MySQL**: Local MySQL server (default: localhost:3306)
