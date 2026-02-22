"use client";

import UploadCard from "@/components/UploadCard";
import ChatCard from "@/components/ChatCard";
import "./globals.css";

export default function Page() {
  return (
    <main className="min-h-screen animated-bg text-zinc-100">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Banner Logo (no box) */}
        <div className="mb-12 flex justify-center">
          <img
            src="/logo.png"
            alt="GaitKeepr"
            className="w-full max-w-5xl h-auto object-contain px-6"
          />
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          <UploadCard />
          <ChatCard />
        </div>
      </div>
    </main>
  );
}