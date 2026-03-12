  # 🚀 Project Management App

<p align="center">
<img src="https://img.shields.io/github/stars/anulsasidharan/pm?style=social"/>
<img src="https://img.shields.io/github/forks/anulsasidharan/pm?style=social"/>
<img src="https://img.shields.io/github/last-commit/anulsasidharan/pm"/>
<img src="https://img.shields.io/github/repo-size/anulsasidharan/pm"/>
<img src="https://komarev.com/ghpvc/?username=anulsasidharan&repo=pm&color=blue"/>
</p>

A **full-stack Project Management application** built with modern development tools and **AI-assisted coding using GitHub Copilot**.

This project is part of my **Vibe Coding learning journey**, where I explore building real applications faster using AI development assistants.

---

## 🌟 Project Highlights

- Built using **AI-assisted development**
- Designed with **modern full-stack architecture**
- Demonstrates **rapid prototyping with GitHub Copilot**
- Structured for **scalability and modular development**

## 📌 Project Overview

The **Project Management App** allows users to:

- Create and manage projects
- Organize tasks
- Track progress
- Maintain structured workflows

This project focuses on learning **AI-assisted development workflows** and modern **full-stack architecture**.

---

## 🏗 System Architecture

The Project Management application follows a **layered architecture** separating the frontend, backend services, and data storage. This design ensures modularity, scalability, and maintainability.

```mermaid
flowchart TD

    U[User Browser]

    subgraph Client Layer
        F[Frontend UI]
        F1[HTML]
        F2[CSS]
        F3[JavaScript]
    end

    subgraph Application Layer
        B[Backend API Server]
        B1[REST API Endpoints]
        B2[Business Logic]
        B3[Request Validation]
    end

    subgraph Data Layer
        D[(Database)]
        D1[Projects Table]
        D2[Tasks Table]
        D3[Users Table]
    end

    U -->|Access Application| F
    F -->|API Requests| B
    B -->|Process Logic| B1
    B --> B2
    B --> B3
    B -->|Query Data| D
    D --> D1
    D --> D2
    D --> D3
```

---

## ⚙️ Development Workflow

This project was built using **AI-assisted development** with GitHub Copilot to accelerate coding and experimentation.

```mermaid
flowchart LR

    A[Developer]
    B[VS Code]
    C[GitHub Copilot]
    D[Code Implementation]
    E[Local Testing]
    F[GitHub Repository]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
```

---

## 🚀 Deployment Architecture

The application can be deployed using a typical **web application architecture**.

```mermaid
flowchart TD

    User[User Browser]

    subgraph Web Layer
        FE[Frontend Application]
    end

    subgraph Server Layer
        API[Backend API Server]
    end

    subgraph Data Layer
        DB[(Database Server)]
    end

    User --> FE
    FE -->|API Calls| API
    API -->|Read/Write| DB
```

---

## 🔄 CI/CD Pipeline

The project can be integrated with **GitHub workflows for continuous integration and deployment**.

```mermaid
flowchart LR

    A[Developer Commit]
    B[GitHub Repository]
    C[CI Pipeline]
    D[Build & Test]
    E[Deployment]

    A --> B
    B --> C
    C --> D
    D --> E
```

---

## 🤖 AI-Assisted Development

This project demonstrates **AI-assisted software development using GitHub Copilot**.

Benefits observed during development:

- Faster code generation
- Rapid prototyping
- Improved developer productivity
- Assistance with repetitive coding tasks

AI tools used:

- GitHub Copilot
- VS Code AI suggestions

---

## 📌 Architecture Summary

The system follows a **modern web application architecture**:

```
User
  ↓
Frontend (UI Layer)
  ↓
Backend API (Application Layer)
  ↓
Database (Data Layer)
```

This modular structure allows the system to scale easily while keeping components independent.


## 🎥 Demo

*(Add demo GIF or video here later)*
![alt text](Animation.gif)


---

# ✨ Features

- 📁 Project creation and management  
- ✅ Task tracking and organization  
- 📊 Project progress monitoring  
- ⚡ AI-assisted coding workflow  
- 📦 Modular project structure  

---

## 🧰 Tech Stack

### Frontend
<p>
<img src="https://skillicons.dev/icons?i=html,css,js"/>
</p>

### Backend
<p>
<img src="https://skillicons.dev/icons?i=nodejs,express"/>
</p>

### Development Tools
<p>
<img src="https://skillicons.dev/icons?i=git,github,vscode"/>
</p>

💻 Built with **AI-assisted development using GitHub Copilot**


