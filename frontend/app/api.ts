export type Card = {
  id: string;
  title: string;
};

export type Column = {
  id: string;
  name: string;
  cards: Card[];
};

export type Board = {
  columns: Column[];
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AiChatResponse = {
  reply: string;
  operation_type: "chat_only" | "board_update" | "fallback_invalid_output";
  board: Board | null;
};

type BoardEnvelope = {
  board: Board;
};

type LoginPayload = {
  username: string;
  password: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseJsonSafe(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    ...init
  });

  if (!response.ok) {
    const payload = await parseJsonSafe(response);
    const message =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;

    throw new ApiError(response.status, message);
  }

  return (await parseJsonSafe(response)) as T;
}

export async function login(payload: LoginPayload): Promise<void> {
  await request<{ status: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function logout(): Promise<void> {
  await request<{ status: string }>("/api/auth/logout", {
    method: "POST",
    body: JSON.stringify({})
  });
}

export async function fetchBoard(): Promise<Board> {
  const response = await request<BoardEnvelope>("/api/board", {
    method: "GET"
  });
  return response.board;
}

export async function saveBoard(board: Board): Promise<Board> {
  const response = await request<BoardEnvelope>("/api/board", {
    method: "PUT",
    body: JSON.stringify({ board })
  });
  return response.board;
}

export async function sendAiChat(message: string, history: ChatMessage[]): Promise<AiChatResponse> {
  return request<AiChatResponse>("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify({ message, history })
  });
}
