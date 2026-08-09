import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CrisisMesh — Incident Command",
  description: "Real-time, multi-source disaster intelligence and response coordination.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
