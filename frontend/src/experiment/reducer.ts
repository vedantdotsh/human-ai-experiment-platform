import type { ChatMessage, ServerMessage } from "../realtime/socket";

export type Session = {
  phase: string;
  round: number | null;
  phaseSeq: number;
  deadline: number | null;
  ownLabel: string | null;
  messages: ChatMessage[];
};

export type State = {
  status: "joining" | "joined" | "left" | "ended" | "error";
  error: string | null;
  session: Session | null;
  /** Server clock minus browser clock, refreshed with every server update. */
  clockOffset: number;
  notice: string | null;
};

export type Action =
  | { type: "joining" }
  | { type: "joined" }
  | { type: "left" }
  | { type: "ended" }
  | { type: "error"; message: string }
  | { type: "server"; message: ServerMessage };

export const initialState: State = {
  status: "joining",
  error: null,
  session: null,
  clockOffset: 0,
  notice: null,
};

const REASONS: Record<string, string> = {
  chat_closed: "Chat is closed right now.",
  stale_phase: "That phase just ended.",
  too_late: "Time is up for this phase.",
  invalid_message: "Messages must be 1 to 500 characters.",
};

export function reduce(state: State, action: Action): State {
  switch (action.type) {
    case "joining":
      return { ...initialState };
    case "joined":
      return { ...state, status: "joined" };
    case "left":
      return { ...initialState, status: "left" };
    case "ended":
      return { ...state, status: "ended" };
    case "error":
      return { ...state, status: "error", error: action.message };
    case "server":
      return applyServer(state, action.message);
  }
}

function applyServer(state: State, message: ServerMessage): State {
  const clockOffset = "server_time" in message ? message.server_time - Date.now() : state.clockOffset;
  switch (message.type) {
    case "session.snapshot":
      return {
        ...state,
        clockOffset,
        notice: null,
        session: {
          phase: message.phase,
          round: message.round,
          phaseSeq: message.phase_seq,
          deadline: message.deadline,
          ownLabel: message.own_label,
          messages: message.messages,
        },
      };
    case "phase.changed":
      if (!state.session || message.phase_seq <= state.session.phaseSeq) return state;
      return {
        ...state,
        clockOffset,
        notice: null,
        session: {
          ...state.session,
          phase: message.phase,
          round: message.round,
          phaseSeq: message.phase_seq,
          deadline: message.deadline,
        },
      };
    case "message.created": {
      if (!state.session || state.session.messages.some((m) => m.seq === message.seq)) return state;
      const { type: _type, ...chat } = message;
      return { ...state, session: { ...state.session, messages: [...state.session.messages, chat] } };
    }
    case "action.rejected":
      return { ...state, notice: REASONS[message.reason] ?? "That action was not accepted." };
  }
}
