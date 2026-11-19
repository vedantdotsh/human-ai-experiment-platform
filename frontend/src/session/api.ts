export type Seat = { seat_token: string; phase: string };

const TOKEN_KEY = "seatToken";

// Per-tab seat token: sessionStorage is separate for every tab and survives refresh.
export function readToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function saveToken(token: string | null): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage unavailable: the seat just cannot be reclaimed after a refresh.
  }
}

async function post(path: string, body: unknown): Promise<Response> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res;
}

let inflight: Promise<Seat> | null = null;

// Claims a seat, or reclaims this tab's seat when its token is still valid.
// Concurrent callers (such as React StrictMode's double effect) share one request.
export function join(): Promise<Seat> {
  inflight ??= post("/api/join", { seat_token: readToken() })
    .then((res) => res.json() as Promise<Seat>)
    .then((seat) => {
      saveToken(seat.seat_token);
      return seat;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

export async function leave(): Promise<void> {
  const token = readToken();
  if (token) await post("/api/leave", { seat_token: token });
  saveToken(null);
}
