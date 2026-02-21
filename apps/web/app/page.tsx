import UploadCard from "@/components/UploadCard";
import ChatCard from "@/components/ChatCard";
import "./globals.css";

export default function Page() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-950 text-zinc-100">
      <div className="max-w-6xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-semibold mb-2">AI Run Coach</h1>
          <p className="text-zinc-400">AI-powered gait analysis & injury-aware training feedback</p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <UploadCard />
          <ChatCard />
        </div>
      </div>
    </main>
  );
}
