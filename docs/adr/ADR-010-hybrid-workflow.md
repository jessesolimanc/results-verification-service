# ADR-010: Hybrid planning and implementation workflow

## Status
Accepted

## Context
The project needed a development workflow that supports both high-level design discussion and active code implementation. Two tools are available: Claude.ai (conversational, good for planning and architecture) and Claude Code (CLI tool with direct filesystem access, good for implementation).

## Decision
Adopt a hybrid workflow:
- **Claude.ai** for planning, architecture decisions, design discussion, code review, and debugging logic problems
- **Claude Code** for implementation — writing function bodies, running code, installing dependencies, and iterating on the codebase directly

## Reasoning
- Each tool is used for what it does best
- Planning decisions are made and documented before implementation begins, reducing rework
- The developer gets hands-on implementation practice using Claude Code as a coding assistant, which builds real-world experience
- Architecture context accumulated in Claude.ai conversations informs implementation without being lost

## Consequences
- A deliberate handoff step is needed between planning and implementation — agreeing on what to build before switching tools
- ADRs and design docs should be kept current so Claude Code has accurate context when needed
- The rhythm per session is: plan here → implement in Claude Code → review here

## Alternatives considered
- Implement everything via Claude.ai file generation and download — rejected due to friction of copy/paste loop for active development
- Implement everything in Claude Code — rejected because it lacks the conversational planning layer that has been valuable throughout this project
