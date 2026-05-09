# Mars Agent Self-Profile + Comparison Dimensions

> Pre-filled baseline so the mars-scanner agent supplements rather than rediscovers.
> The mars-scanner should verify this profile is still accurate via mcp__code_index__architecture_overview.

## Mars Agent Self-Profile

### Identity
- **Project**: Mars Agent v5.x
- **Type**: Multi-agent AI orchestration platform
- **Stack**: LangGraph Platform + FastAPI (backend), Next.js 16 + React 19 (frontend)
- **Deployment**: Docker Compose (4 containers: frontend, backend, browser-mcp, redis) + Nginx reverse proxy

### Architecture
- **Pattern**: Multi-agent system with middleware pipeline
- **Backend**: FastAPI + LangGraph, 27+ middleware, 14 API routers, 10 MCP services
- **Frontend**: Next.js App Router, 64+ custom hooks, 27 component directories
- **Storage**: PostgreSQL (Cloud SQL) for checkpoints, GCS for user data, BigQuery for analytics
- **Auth**: Supabase Auth with JWT, Redis token blacklist

### LLM Integration
- **Primary**: Gemini 3 Flash (mars_agent), Gemini 3 Pro (mars_deep)
- **Image**: Gemini Vision (mars_image)
- **Fallback**: Gemini 3.1 Flash Lite (mars_mini, 429 fallback)
- **Features**: Context Cache, Files API, streaming, extended thinking

### Key Features
- Browser automation (Playwright + AgentBay persistent sessions)
- Livestream data collection (Douyin, WeChat Channels)
- VIP client management (relationship profiles, behavior scoring)
- Memory system (GCS markdown, BM25+vector hybrid recall)
- Multi-model orchestration with fallback chains
- Real-time streaming (SSE with reconnect)
- Skill system (55+ Claude Code skills)

### Quality
- Adversarial code review (/review skill)
- Experience library (24 indexed lessons)
- 529 archived features
- Structured logging (no console.log/print)
- English-first codebase with strict naming conventions

---

## Comparison Dimensions

Use these dimensions when building the comparison matrix. Not all apply to every project — skip irrelevant ones.

### Architecture
- [ ] Architecture pattern (monolith / microservice / graph-based / library)
- [ ] State management approach
- [ ] Module organization (by feature / by layer / hybrid)
- [ ] Middleware / plugin pipeline

### LLM Integration
- [ ] LLM integration pattern (direct API / framework / abstraction layer)
- [ ] Multi-model support
- [ ] Streaming architecture
- [ ] Context management (caching, compression, windowing)
- [ ] Tool / function calling

### Data & Storage
- [ ] Data persistence strategy
- [ ] User data isolation
- [ ] Analytics / observability

### Developer Experience
- [ ] Setup complexity (time to first run)
- [ ] Documentation quality
- [ ] Extension / plugin system
- [ ] Testing strategy
- [ ] CI/CD maturity

### Production Readiness
- [ ] Authentication / authorization
- [ ] Error handling / resilience
- [ ] Real-time capabilities (streaming / SSE / WebSocket)
- [ ] Deployment model (Docker / serverless / hybrid)
- [ ] Performance optimization patterns

### Unique Differentiators
- [ ] What does this project do that no other project in the space does?
- [ ] What does Mars Agent do that this project does not?

---

## Rating Scale

| Rating | Criteria |
|--------|----------|
| Excellent | Industry-leading, comprehensive, well-documented |
| Good | Solid implementation, covers most use cases |
| Average | Functional but with notable gaps |
| Below Average | Minimal or problematic implementation |
| N/A | Not applicable or not enough evidence |
