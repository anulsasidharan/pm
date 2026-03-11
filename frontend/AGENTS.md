# Frontend Agent Guide

## Purpose

This folder contains the Next.js frontend for the Project Management MVP.
It provides the Kanban UI, login experience, and AI chat sidebar experience.

## Product Responsibilities

- Render the Kanban board at `/` after authentication
- Support card create/edit/move interactions with drag and drop
- Integrate with backend API for board fetch/save
- Provide login/logout flow using MVP credentials (`user` / `password`)
- Provide AI sidebar chat UI that can trigger board updates via backend

## Technical Expectations

- Keep implementation simple and focused on MVP scope
- Use idiomatic, current Next.js and React patterns
- Avoid unnecessary abstractions and extra features
- Keep API calls clearly separated from presentation logic

## Testing Expectations

- Maintain at least **80% unit test coverage** for frontend testable logic
- Include robust integration testing for end-user flows, including login/logout, Kanban interactions, backend persistence, and AI-driven board updates

## Styling and UX

- Follow project color scheme from root `AGENTS.md`
- Keep UI clear, responsive, and practical for desktop and mobile
- Ensure loading and error states are visible and actionable