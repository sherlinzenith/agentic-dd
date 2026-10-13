import "./globals.css";

export const metadata = {
  title: "Agentic Due Diligence Platform | Enterprise M&A Diligence OS",
  description: "Enterprise Autonomous Multi-Agent Due Diligence Platform for M&A, Private Equity, and Institutional Audit",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body>{children}</body>
    </html>
  );
}
