import { useCallback, useEffect, useReducer, useRef } from "react";
import { join, leave } from "../session/api";
import { openSocket, type Socket } from "../realtime/socket";
import { rememberPhaseLength } from "./phaseClock";
import { initialState, reduce } from "./reducer";

export function useExperiment() {
  const [state, dispatch] = useReducer(reduce, initialState);
  const socket = useRef<Socket | null>(null);
  const phaseSeq = useRef(0);
  phaseSeq.current = state.session?.phaseSeq ?? 0;

  const phaseLength = state.session?.phaseLength ?? null;
  useEffect(() => {
    if (phaseLength !== null) rememberPhaseLength(phaseSeq.current, phaseLength);
  }, [phaseLength]);

  const claim = useCallback(async () => {
    dispatch({ type: "joining" });
    try {
      const seat = await join();
      socket.current?.close();
      socket.current = openSocket(seat.seat_token, {
        onMessage: (message) => dispatch({ type: "server", message }),
        onSeatGone: () => dispatch({ type: "ended" }),
      });
      dispatch({ type: "joined" });
    } catch (err) {
      dispatch({ type: "error", message: (err as Error).message });
    }
  }, []);

  // No StrictMode in main.tsx: every socket open and close is a logged
  // connection event, so effects must not run twice.
  useEffect(() => {
    void claim();
    return () => socket.current?.close();
  }, [claim]);

  const leaveWaitingRoom = useCallback(async () => {
    socket.current?.mute(); // the server closes it when the seat is released
    try {
      await leave();
      socket.current?.close();
      socket.current = null;
      dispatch({ type: "left" });
    } catch (err) {
      dispatch({ type: "error", message: (err as Error).message });
    }
  }, []);

  const sendMessage = useCallback((text: string) => {
    socket.current?.send({ type: "message.send", text, expected_phase_seq: phaseSeq.current });
  }, []);

  const sendVote = useCallback((target: string) => {
    socket.current?.send({ type: "vote.submit", target, expected_phase_seq: phaseSeq.current });
  }, []);

  return { state, claim, leaveWaitingRoom, sendMessage, sendVote };
}
