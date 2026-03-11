# Backend Agent Guide

## Purpose

This folder contains the FastAPI backend for the Project Management MVP.

## Responsibilities

- Serve API routes under `/api/*`
- Serve temporary root HTML during scaffolding phase
- Handle authentication/session logic for MVP
- Persist board data in SQLite
- Integrate with OpenRouter AI APIs

## Standards

- Keep implementation simple and MVP-focused
- Use idiomatic FastAPI patterns
- Maintain >= 80% unit test coverage
- Add robust integration tests for major user flows