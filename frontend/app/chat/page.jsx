import { Suspense } from "react";
import ChatWorkspace from "@/components/ChatWorkspace";

export default function ChatPage() {
  return (
    <Suspense fallback={<main className="page center">Loading...</main>}>
      <ChatWorkspace />
    </Suspense>
  );
}
