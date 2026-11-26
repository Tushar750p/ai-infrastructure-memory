"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState("Verifying your email...");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;

    fetch(API_BASE + "/api/auth/email-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ token }),
    })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Email verification failed");
        if (active) setStatus("Email verified successfully. You can now sign in.");
      })
      .catch((err) => {
        if (!active) return;
        setStatus("");
        setError(err instanceof Error ? err.message : "Email verification failed");
      });

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <main style={{ minHeight: "100vh", background: "#07111f", color: "#e2e8f0", display: "grid", placeItems: "center", padding: 24, fontFamily: "Arial, sans-serif" }}>
      <section style={{ width: "100%", maxWidth: 520, background: "#0b1728", border: "1px solid #1e293b", borderRadius: 14, padding: 28, textAlign: "center" }}>
        <div style={{ color: "#38bdf8", fontSize: 13, letterSpacing: 2, fontWeight: 700 }}>AIME CONSOLE</div>
        <h1 style={{ margin: "10px 0" }}>Email Verification</h1>
        {!token && <p style={{ color: "#fb7185" }}>Verification token is missing.</p>}
        {token && status && <p style={{ color: "#94a3b8" }}>{status}</p>}
        {error && <p style={{ color: "#fb7185" }}>{error}</p>}
        <Link href="/" style={{ display: "inline-block", marginTop: 18, color: "#7dd3fc", textDecoration: "none" }}>Back to AIME</Link>
      </section>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<main style={{ minHeight: "100vh", background: "#07111f" }} />}>
      <VerifyEmailContent />
    </Suspense>
  );
}
