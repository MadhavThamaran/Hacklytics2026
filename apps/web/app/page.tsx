import UploadCard from "@/components/UploadCard";
import ChatCard from "@/components/ChatCard";
import "./globals.css";

export default function Page() {
  return (
    <div className="container">
      <div style={{ marginBottom: 14 }}>
        <h1 className="h1">Running Coach</h1>
        <p className="sub">
          Skeleton app first → then CV scoring + Vector DB chatbot → then beautify.
        </p>
      </div>

      <div className="grid">
        <UploadCard />
        <ChatCard />
      </div>

      <div style={{ marginTop: 14 }} className="small">
        Tip: set <code>NEXT_PUBLIC_API_URL</code> to your FastAPI server (default: http://localhost:8000).
      </div>
    </div>
  );
}
