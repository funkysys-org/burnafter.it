import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "@fontsource/silkscreen/400.css";
import "@fontsource/silkscreen/700.css";
import "@fontsource/vt323/400.css";
import "./index.css";
import HomePage from "./pages/HomePage";
import CreatorPage from "./pages/CreatorPage";
import ReaderPage from "./pages/ReaderPage";

// NOTE: the SPA deliberately has NO /stream_any route. Browser
// NAVIGATION to /stream_any/<type>/<hash> must reach the raw gated
// API (nginx proxies it), not a page — raw clients keep raw serving.
// The branded reader lives at /read/:type/:hash.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/create" element={<CreatorPage />} />
        <Route path="/read/:type/:hash" element={<ReaderPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
