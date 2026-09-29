"use client";

import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      setMessage("Reset token is missing.");
      return;
    }
    if (password.length < 12) {
      setMessage("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(API_BASE + "/api/auth/password-reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token, new_password: password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Password reset failed");
      setSuccess(true);
      setPassword("");
      setConfirmPassword("");
      setMessage("Password changed successfully. You can now sign in.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Password reset failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", background: "#07111f", color: "#e2e8f0", display: "grid", placeItems: "center", padding: 24, fontFamily: "Arial, sans-serif" }}>
      <section style={{ width: "100%", maxWidth: 460, background: "#0b1728", border: "1px solid #1e293b", borderRadius: 14, padding: 28 }}>
        <div style={{ color: "#38bdf8", fontSize: 13, letterSpacing: 2, fontWeight: 700 }}>AIME CONSOLE</div>
        <h1 style={{ margin: "8px 0 6px" }}>Reset your password</h1>
        <p style={{ color: "#94a3b8", fontSize: 14 }}>Choose a new password for your AIME account.</p>

        {!token ? (
          <p style={{ color: "#f87171" }}>This reset link is incomplete or invalid.</p>
        ) : success ? (
          <div>
            <p style={{ color: "#4ade80" }}>{message}</p>
            <a href="/" style={{ color: "#38bdf8" }}>Return to sign in</a>
          </div>
        ) : (
          <form onSubmit={submit} style={{ display: "grid", gap: 12, marginTop: 20 }}>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="New password (12+ characters)"
              autoComplete="new-password"
              minLength={12}
              required
              style={{ padding: 12, borderRadius: 8, background: "#020617", color: "#e2e8f0", border: "1px solid #334155" }}
            />
            <input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
              autoComplete="new-password"
              minLength={12}
              required
              style={{ padding: 12, borderRadius: 8, background: "#020617", color: "#e2e8f0", border: "1px solid #334155" }}
            />
            <button type="submit" disabled={loading} style={{ padding: 12, borderRadius: 8, border: 0, background: "#2563eb", color: "white", fontWeight: 700 }}>
              {loading ? "Updating..." : "Reset password"}
            </button>
            {message && <div style={{ color: "#f87171", fontSize: 13 }}>{message}</div>}
          </form>
        )}
      </section>
    </main>
  );
}
