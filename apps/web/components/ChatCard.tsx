"use client";

import React from "react";
import { sendChat } from "@/lib/api";
import ExpandableCard from './ExpandableCard'

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

  const promptChips = [
    "Left knee pain after runs",
    "Shin splints when increasing mileage",
    "Achilles tightness in the morning"
  ];

  const handleChipClick = (chip: string) => {
    setInput(chip);
  };

  return (
    <ExpandableCard>
      <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur shadow-xl p-6">
      {/* Card Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">💬</span>
          <h2 className="text-xl font-semibold">Pain-to-Exercises Coach</h2>
        </div>
        <div className="h-1 w-32 bg-gradient-to-r from-emerald-400/60 to-amber-400/60 rounded-full" />
      </div>

      {/* Disclaimer Banner */}
      <div className="rounded-xl bg-amber-500/10 border border-amber-400/20 text-amber-100 p-4 mb-6 text-sm">
        <strong>Not medical advice:</strong> This coach provides general running exercise guidance only.
        If pain is severe, sharp, worsening, or persistent, please see a qualified clinician.
      </div>

      {/* Prompt Chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        {promptChips.map((chip, idx) => (
          <button
            key={idx}
            onClick={() => handleChipClick(chip)}
            className="rounded-full bg-white/5 border border-white/10 hover:bg-white/10 text-sm px-3 py-1.5 text-zinc-200 transition cursor-pointer"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* Chat Window */}
      <div className="h-96 overflow-y-auto rounded-xl border border-white/10 bg-black/20 p-4 mb-4 space-y-4">
        {msgs.length === 0 ? (
          <p className="text-zinc-500 text-sm">Start chatting to get personalized advice...</p>
        ) : (
          msgs.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-xs rounded-lg px-4 py-3 text-sm border ${
                  m.role === "user"
                    ? "bg-emerald-500/20 border-emerald-400/20 text-emerald-100"
                    : "bg-white/5 border-white/10 text-zinc-200"
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{m.text}</p>
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 text-zinc-400 rounded-lg px-4 py-3 text-sm">
              Coach is typing...
            </div>
          </div>
        )}
      </div>

      {/* Input Row */}
      <div className="flex gap-3">
        <input
          className="flex-1 rounded-xl bg-black/30 border border-white/10 px-4 py-3 placeholder:text-zinc-500 text-zinc-100 focus:outline-none focus:border-white/20 transition"
          placeholder="Describe your pain..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
        />
        <button
          className="rounded-xl bg-zinc-100 text-zinc-900 px-4 py-3 font-medium hover:bg-white transition disabled:opacity-50"
          disabled={loading}
          onClick={onSend}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>

        {error && (
          <div className="rounded-xl bg-red-500/10 border border-red-400/20 text-red-100 p-3 mt-4 text-sm">
            {error}
          </div>
        )}
      </div>
    </ExpandableCard>
  );
}