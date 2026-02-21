"use client";

import React from "react";

type Props = {
  children: React.ReactNode;
  className?: string;
};

export default function ExpandableCard({ children, className }: Props) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <>
      <div
        onClick={() => setExpanded(true)}
        className={`${className ?? ""} transition-transform duration-300 ease-out transform hover:scale-105 hover:-translate-y-2 hover:shadow-2xl cursor-pointer`}
      >
        {children}
      </div>

      {expanded && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-12">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setExpanded(false)}
            aria-hidden
          />

          <div className="relative z-60 w-full max-w-5xl px-4">
            <div className="rounded-2xl bg-zinc-950/95 border border-white/10 p-6 shadow-2xl transform scale-110">
              <div style={{ position: "absolute", right: 12, top: 12, zIndex: 9999 }}>
                <button
                  onClick={() => setExpanded(false)}
                  style={{ zIndex: 10000, position: 'relative' }}
                  className="rounded-full bg-black/40 text-white/90 px-3 py-1 text-sm backdrop-blur"
                >
                  Close
                </button>
              </div>
              {children}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
