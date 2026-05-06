"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getAuthSession } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const auth = getAuthSession();
    if (auth?.token && auth?.userId) {
      router.replace("/chat");
      return;
    }
    router.replace("/login");
  }, [router]);

  return <main className="page center">Routing...</main>;
}
