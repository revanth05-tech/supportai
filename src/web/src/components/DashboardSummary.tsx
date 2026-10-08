"use client";

import { useEffect, useState } from "react";
import { getSummary, type Summary } from "@/lib/dashboard";

export default function DashboardSummary() {
  const [s, setS] = useState<Summary | null>(null);
  useEffect(() => {
    getSummary()
      .then(setS)
      .catch(() => {});
  }, []);
  if (!s) return null;
  const cards = [
    { label: "Conversations", value: s.totalConversations },
    { label: "Active", value: s.activeConversations },
    { label: "Handed off", value: s.handedOffConversations },
    { label: "Leads", value: s.totalLeads },
    { label: "New leads", value: s.newLeads },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border p-4">
          <p className="text-2xl font-semibold">{c.value}</p>
          <p className="text-xs text-gray-500">{c.label}</p>
        </div>
      ))}
    </div>
  );
}
