"use client";

import React from "react";
import { sendChat } from "@/lib/api";

type ChatMsg = { role: "user" | "assistant"; text: string };

export default function ChatCard() {
  const [msgs, setMsgs] = React.useState<ChatMsg[]>([
    { role: "assistant", text: "Tell me what hurts (e.g., left shin, right knee) and whether you want warm-up, stretching, or strengthening." }
  ]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function onSend() {
    const text = input.trim();
    if (!text) return;

    setMsgs((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendChat(text);
      let assistantText = res.message;
      if (res.citations?.length) {
        assistantText += "\n\nSources:\n" + res.citations.map(c => `- ${c.title}: ${c.note}`).join("\n");
      }
      setMsgs((m) => [...m, { role: "assistant", text: assistantText }]);
    } catch (e: any) {
      setError(e?.message ?? "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <h2 className="h1">Pain-to-Exercises Coach</h2>
          <p className="sub">Chatbot (mock now). Later: RAG via Actian VectorAI DB.</p>
        </div>
        <span className="badge">MVP Skeleton</span>
      </div>

      <div
        style={{
          marginTop: 10,
          marginBottom: 10,
          padding: "10px 12px",
          borderRadius: 8,
          border: "1px solid #f0c36d",
          background: "#fff7e6",
          color: "#7a4b00",
          fontSize: 14
        }}
      >
        <strong>Not medical advice:</strong> This coach provides general running exercise guidance only.
        If pain is severe, sharp, worsening, or persistent, please see a qualified clinician.
      </div>

      <div className="chat">
        {msgs.map((m, i) => (
          <p key={i} className="msg">
            <b>{m.role === "user" ? "You" : "Coach"}</b>
            {m.text}
          </p>
        ))}
      </div>

      <div className="row" style={{ marginTop: 10 }}>
        <input
          className="input"
          placeholder='e.g., "My left shin hurts after runs. Warm-up ideas?"'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") onSend(); }}
        />
        <button className="btn" disabled={loading} onClick={onSend}>
          {loading ? "..." : "Send"}
        </button>
      </div>

      {error && <p className="small" style={{ color: "crimson", marginTop: 10 }}>{error}</p>}
    </div>
  );
}