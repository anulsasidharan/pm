"use client";

import React, { useEffect, useRef, useState } from "react";

import { ApiError, type Card, type Column, fetchBoard, login, logout, saveBoard } from "./api";

const DEFAULT_COLUMNS: Column[] = [
  { id: "todo", name: "To Do", cards: [] },
  { id: "in-progress", name: "In Progress", cards: [] },
  { id: "done", name: "Done", cards: [] }
];

function normalizeColumns(columns: Column[]): Column[] {
  const byId = new Map(columns.map((column) => [column.id, column]));

  return DEFAULT_COLUMNS.map((fallback) => {
    const existing = byId.get(fallback.id);
    return existing
      ? {
          ...existing,
          cards: Array.isArray(existing.cards) ? existing.cards : []
        }
      : {
          ...fallback,
          cards: []
        };
  });
}

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isBoardLoading, setIsBoardLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");
  const [boardError, setBoardError] = useState("");
  const [columns, setColumns] = useState<Column[]>(DEFAULT_COLUMNS);
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const pendingSaveCountRef = useRef(0);
  const saveQueueRef = useRef(Promise.resolve());
  const draggingCardIdRef = useRef<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function bootstrapSession() {
      setBoardError("");

      try {
        const board = await fetchBoard();
        if (!isMounted) {
          return;
        }

        const normalizedColumns = normalizeColumns(board.columns);
        setIsAuthenticated(true);
        setColumns(normalizedColumns);

        // Auto-heal persisted board shape when fixed columns are missing.
        if (JSON.stringify(normalizedColumns) !== JSON.stringify(board.columns)) {
          await saveBoard({ columns: normalizedColumns });
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          setIsAuthenticated(false);
          setColumns(DEFAULT_COLUMNS);
          return;
        }

        setBoardError("Unable to load board right now.");
      } finally {
        if (isMounted) {
          setIsInitializing(false);
        }
      }
    }

    void bootstrapSession();

    return () => {
      isMounted = false;
    };
  }, []);

  function findDraggingSource(cardId: string): { columnId: string; index: number } | null {
    for (const column of columns) {
      const index = column.cards.findIndex((card) => card.id === cardId);
      if (index !== -1) {
        return { columnId: column.id, index };
      }
    }

    return null;
  }

  function queueBoardSave(nextColumns: Column[]) {
    pendingSaveCountRef.current += 1;
    setIsSaving(true);
    setBoardError("");

    saveQueueRef.current = saveQueueRef.current
      .then(async () => {
        await saveBoard({ columns: nextColumns });
      })
      .catch(() => {
        setBoardError("Failed to save board changes.");
      })
      .finally(() => {
        pendingSaveCountRef.current -= 1;
        if (pendingSaveCountRef.current <= 0) {
          setIsSaving(false);
        }
      });
  }

  function applyColumnsUpdate(updater: (prev: Column[]) => Column[]) {
    setColumns((prev) => {
      const next = updater(prev);
      if (next !== prev && isAuthenticated) {
        queueBoardSave(next);
      }

      return next;
    });
  }

  function startEdit(card: { id: string; title: string }) {
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

    applyColumnsUpdate((prev) =>
      prev.map((column) => ({
        ...column,
        cards: column.cards.map((card) => (card.id === cardId ? { ...card, title: trimmed } : card))
      }))
    );
    cancelEdit();
  }

  function moveCard(cardId: string, targetColumnId: string, targetIndex: number) {
    applyColumnsUpdate((prev) => {
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

  function getDraggedCardIdFromEvent(event?: React.DragEvent): string | null {
    if (draggingCardIdRef.current) {
      return draggingCardIdRef.current;
    }

    const transferred = event?.dataTransfer?.getData("text/plain");
    return transferred || draggingCardId;
  }

  function handleCardDrop(event: React.DragEvent, targetColumnId: string, targetIndex: number) {
    event.preventDefault();

    const activeCardId = getDraggedCardIdFromEvent(event);
    if (!activeCardId) {
      return;
    }

    const source = findDraggingSource(activeCardId);
    if (!source) {
      return;
    }

    const sameColumn = source.columnId === targetColumnId;
    const adjustedIndex = sameColumn && source.index < targetIndex ? targetIndex - 1 : targetIndex;
    moveCard(activeCardId, targetColumnId, adjustedIndex);
    draggingCardIdRef.current = null;
    setDraggingCardId(null);
  }

  function handleColumnDrop(event: React.DragEvent, targetColumnId: string, targetLength: number) {
    event.preventDefault();

    const activeCardId = getDraggedCardIdFromEvent(event);
    if (!activeCardId) {
      return;
    }

    moveCard(activeCardId, targetColumnId, targetLength);
    draggingCardIdRef.current = null;
    setDraggingCardId(null);
  }

  async function loadBoardFromBackend() {
    setIsBoardLoading(true);
    setBoardError("");

    try {
      const board = await fetchBoard();
      const normalizedColumns = normalizeColumns(board.columns);
      setColumns(normalizedColumns);

      if (JSON.stringify(normalizedColumns) !== JSON.stringify(board.columns)) {
        await saveBoard({ columns: normalizedColumns });
      }
    } catch {
      setBoardError("Unable to load board right now.");
    } finally {
      setIsBoardLoading(false);
    }
  }

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");

    try {
      await login({ username, password });
      setIsAuthenticated(true);
      await loadBoardFromBackend();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setAuthError("Invalid username or password.");
        return;
      }

      setAuthError("Unable to sign in right now.");
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // Keep client state reset even if logout call fails.
    }

    setIsAuthenticated(false);
    setUsername("");
    setPassword("");
    setAuthError("");
    setBoardError("");
    setDraggingCardId(null);
    setEditingCardId(null);
    setEditingValue("");
    setColumns(DEFAULT_COLUMNS);
    setIsSaving(false);
    pendingSaveCountRef.current = 0;
    saveQueueRef.current = Promise.resolve();
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

      {isInitializing ? (
        <p className="sub">Checking session...</p>
      ) : isAuthenticated ? (
        <>
          <div className="session-row">
            <p className="sub">Signed in as user</p>
            <button type="button" className="primary" onClick={() => void handleLogout()}>
              Sign Out
            </button>
          </div>
          <div className="status-row" aria-live="polite">
            {isBoardLoading ? <p className="sub">Loading board...</p> : null}
            {isSaving ? <p className="sub">Saving changes...</p> : null}
            {boardError ? <p className="error">{boardError}</p> : null}
          </div>
          <section className="board" aria-label="Kanban board">
            {columns.map((column) => (
              <article
                key={column.id}
                className="column"
                onDragOver={(event) => {
                  event.preventDefault();
                  if (event.dataTransfer) {
                    event.dataTransfer.dropEffect = "move";
                  }
                }}
                onDrop={(event) => handleColumnDrop(event, column.id, column.cards.length)}
              >
                <h2>{column.name}</h2>
                <ul
                  onDragOver={(event) => {
                    event.preventDefault();
                    if (event.dataTransfer) {
                      event.dataTransfer.dropEffect = "move";
                    }
                  }}
                  onDrop={(event) => handleColumnDrop(event, column.id, column.cards.length)}
                  aria-label={`${column.name} cards`}
                >
                  {column.cards.map((card, index) => (
                    <li
                      key={card.id}
                      className="card"
                      draggable
                      onDragStart={(event) => {
                        event.dataTransfer?.setData("text/plain", card.id);
                        if (event.dataTransfer) {
                          event.dataTransfer.effectAllowed = "move";
                        }
                        draggingCardIdRef.current = card.id;
                        setDraggingCardId(card.id);
                      }}
                      onDragEnd={() => {
                        draggingCardIdRef.current = null;
                        setDraggingCardId(null);
                      }}
                      onDragOver={(event) => {
                        event.preventDefault();
                        if (event.dataTransfer) {
                          event.dataTransfer.dropEffect = "move";
                        }
                      }}
                      onDrop={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        handleCardDrop(event, column.id, index);
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
          <form onSubmit={(event) => void handleLogin(event)}>
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