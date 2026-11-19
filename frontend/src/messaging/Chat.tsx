import { Fragment, useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatMessage } from "../realtime/socket";
import { PlayerChip } from "../ui/PlayerChip";

type Props = {
  messages: ChatMessage[];
  ownLabel: string | null;
  open: boolean;
  notice: string | null;
  onSend(text: string): void;
};

/** Every message renders and animates identically, whoever sent it. */
export function Chat({ messages, ownLabel, open, notice, onSend }: Props) {
  const [text, setText] = useState("");
  const list = useRef<HTMLDivElement>(null);
  // Messages already present when the chat first appears are history and do not
  // animate; every later message rises in the same way.
  const historyUpTo = useRef(messages.length ? messages[messages.length - 1].number : 0);

  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [messages.length]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!open || !text.trim()) return;
    onSend(text);
    setText("");
  };

  return (
    <section className="card chat-card" aria-label="Chat">
      <div className="chat-messages" ref={list}>
        {messages.length === 0 && <p className="chat-empty">No messages yet</p>}
        {messages.map((m, i) => (
          <Fragment key={m.number}>
            {i > 0 && m.round !== messages[i - 1].round && (
              <div className="round-divider" role="separator">
                <span className="round-divider-label">Round {m.round}</span>
              </div>
            )}
            <article className={`chat-msg${m.number > historyUpTo.current ? " chat-msg-enter" : ""}`}>
              <div className="chat-msg-head">
                <PlayerChip label={m.author} />
                <span className="chat-msg-name">{m.author}</span>
                {m.author === ownLabel && <span className="chat-you-tag">You</span>}
              </div>
              <p className="chat-msg-body">{m.text}</p>
            </article>
          </Fragment>
        ))}
      </div>
      {notice && <p className="notice" role="alert">{notice}</p>}
      <form className="chat-composer" autoComplete="off" onSubmit={submit}>
        <input
          className="chat-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!open}
          maxLength={500}
          placeholder={open ? "Write a message" : "Chat is closed"}
          aria-label="Write a message"
        />
        <button type="submit" className="btn btn-primary" disabled={!open}>
          Send
        </button>
      </form>
      {!open && <p className="chat-closed-note">Chat is open only during discussion.</p>}
    </section>
  );
}
