type Card = {
  id: string;
  title: string;
};

type Column = {
  id: string;
  name: string;
  cards: Card[];
};

const columns: Column[] = [
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
            <ul>
              {column.cards.map((card) => (
                <li key={card.id} className="card">
                  {card.title}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>
    </main>
  );
}