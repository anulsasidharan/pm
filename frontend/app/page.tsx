"use client";

import React, { useEffect, useMemo, useState } from "react";

type Card = {
  id: string;
  title: string;
};

type Column = {
  id: string;
  name: string;
  cards: Card[];
};

const initialColumns: Column[] = [
  {
    id: "todo",
    name: "To Do",
    cards: [
      { id: "c1", title: "Draft project milestones" },
      { id: "c2", title: "Review API contract" }
    ]
  },
  {
    id: "in-progress",
    name: "In Progress",
    cards: [{ id: "c3", title: "Integrate frontend build output" }]
  },
  {
    id: "done",
    name: "Done",
    cards: [{ id: "c4", title: "Scaffold FastAPI in Docker" }]
  }
];

const AUTH_STORAGE_KEY = "pm-authenticated";
const HARDCODED_USER = "user";
const HARDCODED_PASSWORD = "password";

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [columns, setColumns] = useState<Column[]>(initialColumns);
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  useEffect(() => {
    if (window.localStorage.getItem(AUTH_STORAGE_KEY) === "1") {
      setIsAuthenticated(true);
    }
  }, []);

  const draggingSource = useMemo(() => {
    if (!draggingCardId) {
      return null;
    }

    for (const column of columns) {
      const index = column.cards.findIndex((card) => card.id === draggingCardId);
      if (index !== -1) {
        return { columnId: column.id, index };
      }
    }

    return null;
  }, [columns, draggingCardId]);

  function startEdit(card: Card) {
    setEditingCardId(card.id);
    setEditingValue(card.title);
  }

  function cancelEdit() {
    setEditingCardId(null);
    setEditingValue("");
  }

  function saveEdit(cardId: string) {
    const trimmed = editingValue.trim();
    if (!trimmed) {
      return;
    }

    setColumns((prev) =>
      prev.map((column) => ({
        ...column,
        cards: column.cards.map((card) => (card.id === cardId ? { ...card, title: trimmed } : card))
      }))
    );
    cancelEdit();
  }

  function moveCard(cardId: string, targetColumnId: string, targetIndex: number) {
    setColumns((prev) => {
      let movingCard: Card | null = null;

      const withoutCard = prev.map((column) => {
        const idx = column.cards.findIndex((card) => card.id === cardId);
        if (idx === -1) {
          return column;
        }

        movingCard = column.cards[idx];
        return {
          ...column,
          cards: [...column.cards.slice(0, idx), ...column.cards.slice(idx + 1)]
        };
      });

      if (!movingCard) {
        return prev;
      }

      return withoutCard.map((column) => {
        if (column.id !== targetColumnId) {
          return column;
        }

        const safeIndex = Math.max(0, Math.min(targetIndex, column.cards.length));
        return {
          ...column,
          cards: [
            ...column.cards.slice(0, safeIndex),
            movingCard as Card,
            ...column.cards.slice(safeIndex)
          ]
        };
      });
    });
  }

  function handleCardDrop(targetColumnId: string, targetIndex: number) {
    if (!draggingCardId || !draggingSource) {
      return;
    }

    const sameColumn = draggingSource.columnId === targetColumnId;
    const adjustedIndex = sameColumn && draggingSource.index < targetIndex ? targetIndex - 1 : targetIndex;
    moveCard(draggingCardId, targetColumnId, adjustedIndex);
    setDraggingCardId(null);
  }

  function handleColumnDrop(targetColumnId: string, targetLength: number) {
    if (!draggingCardId) {
      return;
    }

    moveCard(draggingCardId, targetColumnId, targetLength);
    setDraggingCardId(null);
  }

  function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (username === HARDCODED_USER && password === HARDCODED_PASSWORD) {
      setIsAuthenticated(true);
      setAuthError("");
      window.localStorage.setItem(AUTH_STORAGE_KEY, "1");
      return;
    }

    setAuthError("Invalid username or password.");
  }

  function handleLogout() {
    setIsAuthenticated(false);
    setUsername("");
    setPassword("");
    setAuthError("");
    setDraggingCardId(null);
    setEditingCardId(null);
    setEditingValue("");
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  return (
    <main className="page">
      <header className="header">
        <h1>Project Management MVP</h1>
        <p className="sub">Kanban board preview</p>
        <p className="sub">Hello world from FastAPI inside Docker.</p>
        <p className="sub">
          Example check call: <code>fetch('/api/health')</code>
        </p>
      </header>

      {isAuthenticated ? (
        <>
          <div className="session-row">
            <p className="sub">Signed in as user</p>
            <button type="button" className="primary" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
          <section className="board" aria-label="Kanban board">
            {columns.map((column) => (
              <article key={column.id} className="column">
                <h2>{column.name}</h2>
                <ul
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => handleColumnDrop(column.id, column.cards.length)}
                  aria-label={`${column.name} cards`}
                >
                  {column.cards.map((card, index) => (
                    <li
                      key={card.id}
                      className="card"
                      draggable
                      onDragStart={() => setDraggingCardId(card.id)}
                      onDragEnd={() => setDraggingCardId(null)}
                      onDragOver={(event) => event.preventDefault()}
                      onDrop={(event) => {
                        event.stopPropagation();
                        handleCardDrop(column.id, index);
                      }}
                    >
                      {editingCardId === card.id ? (
                        <form
                          className="card-edit"
                          onSubmit={(event) => {
                            event.preventDefault();
                            saveEdit(card.id);
                          }}
                        >
                          <input
                            aria-label={`Edit ${card.title}`}
                            value={editingValue}
                            onChange={(event) => setEditingValue(event.target.value)}
                          />
                          <div className="card-actions">
                            <button type="submit">Save</button>
                            <button type="button" onClick={cancelEdit}>
                              Cancel
                            </button>
                          </div>
                        </form>
                      ) : (
                        <>
                          <p>{card.title}</p>
                          <button type="button" onClick={() => startEdit(card)}>
                            Edit
                          </button>
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </section>
        </>
      ) : (
        <section className="login" aria-label="Sign in form">
          <h2>Sign In</h2>
          <form onSubmit={handleLogin}>
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
            {authError ? <p className="error">{authError}</p> : null}
            <button type="submit" className="primary">
              Sign In
            </button>
          </form>
        </section>
      )}
    </main>
  );
}