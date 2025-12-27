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

White background image generator (白底图生成器) - An AI-powered web app that removes backgrounds from images using Gemini 3 Pro Image via Supabase Edge Functions.

## Commands

```bash
npm run dev          # Start Vite dev server (port 8080)
npm run build        # Production build
npm run build:dev    # Development build
npm run lint         # Run ESLint
npm run preview      # Preview production build
```

## Architecture

### Core Stack
- **React 18 + TypeScript** with Vite 5.x
- **Tailwind CSS 3.4** with shadcn/ui component library (52+ components in `src/components/ui/`)
- **Supabase** for Auth, Database, and Edge Functions
- **TanStack Query 5** for server state (`src/hooks/useTaskHistory.ts`)
- **React Router 6** for routing

### Path Alias
`@` maps to `src/` (configured in `tsconfig.json` and `vite.config.ts`)

### Key Patterns

1. **Server State**: All Supabase data fetching uses TanStack Query hooks for caching, optimistic updates, and realtime subscriptions
2. **Auth**: React Context pattern via `useAuth()` hook wrapping the app
3. **Image Generation**: Supabase Edge Function invoked via `supabase.functions.invoke('generate-white-bg')`
4. **UI Components**: shadcn/ui style - base components in `ui/`, composite components at root level

### Important Files

- `src/App.tsx` - Providers hierarchy (QueryClient, Auth, Router)
- `src/pages/Index.tsx` - Main generator UI
- `src/hooks/useTaskHistory.ts` - Task history with realtime updates
- `src/integrations/supabase/client.ts` - Supabase client configuration
- `src/lib/utils.ts` - `cn()` utility (clsx + tailwind-merge)
