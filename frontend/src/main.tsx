import { createRoot } from "react-dom/client";
import { App } from "./app/App";

// No StrictMode: its double-run of effects would open and close a socket on every
// page load, and each is a logged connection event.
createRoot(document.getElementById("root")!).render(<App />);
