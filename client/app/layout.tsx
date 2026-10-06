import type { Metadata } from "next";
import "@fontsource-variable/inter-tight";
import "@fontsource-variable/newsreader";
import "./globals.css";

export const metadata: Metadata = {
  title: "Retrievia — study from your own material",
  description: "Ask questions, get summaries and spot repeated exam topics across your notes, textbooks and past papers.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="h-full">{children}</body>
    </html>
  );
}
