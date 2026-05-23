import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SportsCast",
  description: "Post-game interview transcription and stats overlay",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" style={{ background: "#ffffff" }}>
      <body className="h-full" style={{ background: "#ffffff" }}>{children}</body>
    </html>
  );
}
