import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App } from "./App";
import { LanguageProvider } from "./i18n";
import "./styles.css";
import "./visual.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <LanguageProvider><App /></LanguageProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
