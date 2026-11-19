import { useState, type FormEvent } from "react";
import type { ChatMessage } from "../realtime/socket";

type Props = {
  messages: ChatMessage[];
  ownLabel: string | null;
  open: boolean;
  notice: string | null;
  onSend(text: string): void;
};

export function Chat({ messages, ownLabel, open, notice, onSend }: Props) {
  const [text, setText] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!open || !text.trim()) return;
    onSend(text);
    setText("");
  };

  return (
    <section>
      <h2>Chat</h2>
      <ul aria-label="chat history">
        {messages.map((m) => (
          <li key={m.seq}>
            [Round {m.round}] {m.author}
            {m.author === ownLabel ? " (you)" : ""}: {m.text}
          </li>
        ))}
      </ul>
      <form onSubmit={submit}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!open}
          maxLength={500}
          aria-label="message"
        />{" "}
        <button type="submit" disabled={!open}>
          Send
        </button>
      </form>
      {!open && <p>Chat is closed.</p>}
      {notice && <p role="alert">{notice}</p>}
    </section>
  );
}
