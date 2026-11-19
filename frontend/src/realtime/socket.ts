export type ServerMessage =
  | {
      type: "session.snapshot";
      phase: string;
      round: number | null;
      phase_seq: number;
      server_time: number;
      deadline: number | null;
      own_label: string | null;
      messages: ChatMessage[];
      ballots_cast: number | null;
      own_vote: string | null;
      vote1_totals: Totals | null;
      results: Results | null;
    }
  | {
      type: "phase.changed";
      phase: string;
      round: number | null;
      phase_seq: number;
      server_time: number;
      deadline: number | null;
    }
  | ({ type: "message.created" } & ChatMessage)
  | { type: "vote.recorded"; round: number; target: string }
  | { type: "vote.progress"; round: number; ballots_cast: number }
  | { type: "vote.summary"; round: number; totals: Totals }
  | ({ type: "results.ready" } & Results)
  | { type: "action.rejected"; action: string; reason: string };

export type Totals = Record<string, number>;
export type Results = { winner: string; totals: Totals };

export type ChatMessage = {
  /** 1-based count of chat messages in this run. */
  number: number;
  author: string;
  round: number;
  text: string;
  ts: number;
};

export type Socket = {
  send(message: object): void;
  /** Stop reconnecting and ignore anything further, without closing the socket. */
  mute(): void;
  close(): void;
};

const CLOSE_SEAT_GONE = 4401;

// Opens the participant socket and keeps it open: any close other than "your
// seat is gone" is retried, and the server resends a snapshot on every connect.
export function openSocket(
  token: string,
  handlers: { onMessage(message: ServerMessage): void; onSeatGone(): void },
): Socket {
  let ws: WebSocket | null = null;
  let stopped = false;
  let retry: ReturnType<typeof setTimeout> | undefined;

  const connect = () => {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${scheme}://${location.host}/api/ws?token=${encodeURIComponent(token)}`);
    ws.onmessage = (event) => {
      if (!stopped) handlers.onMessage(JSON.parse(event.data as string) as ServerMessage);
    };
    ws.onclose = (event) => {
      if (stopped) return;
      if (event.code === CLOSE_SEAT_GONE) handlers.onSeatGone();
      else retry = setTimeout(connect, 1000);
    };
  };
  connect();

  return {
    send(message) {
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(message));
    },
    mute() {
      stopped = true;
      clearTimeout(retry);
    },
    close() {
      stopped = true;
      clearTimeout(retry);
      ws?.close();
    },
  };
}
