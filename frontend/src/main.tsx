/**
 * main.tsx - Application entry point
 *
 * Mounts React app to DOM and imports global styles.
 * Referenced by index.html.
 */

import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);
