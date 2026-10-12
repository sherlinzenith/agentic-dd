import "./globals.css";

export const metadata = {
  title: "Agentic Due Diligence Platform | Multi-Agent AI System",
  description: "Autonomous Agentic Due Diligence powered by Qwen3, Docling, BGE-M3 and PostgreSQL pgvector",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>{children}</body>
    </html>
  );
}
