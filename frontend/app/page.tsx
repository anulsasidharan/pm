"use client";

import React, { useMemo, useState } from "react";

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

export default function HomePage() {
  const [columns, setColumns] = useState<Column[]>(initialColumns);
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const [editingCardId, setEditingCardId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

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

  function handleColumnDrop(targetColumnId: string) {
    if (!draggingCardId) {
      return;
    }

    const targetColumn = columns.find((column) => column.id === targetColumnId);
    if (!targetColumn) {
      return;
    }

    moveCard(draggingCardId, targetColumnId, targetColumn.cards.length);
    setDraggingCardId(null);
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

      <section className="board" aria-label="Kanban board">
        {columns.map((column) => (
          <article key={column.id} className="column">
            <h2>{column.name}</h2>
            <ul
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => handleColumnDrop(column.id)}
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
    </main>
  );
}