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
    <html lang="en" className="h-full">
      <body className="h-full">{children}</body>
    </html>
  );
}
