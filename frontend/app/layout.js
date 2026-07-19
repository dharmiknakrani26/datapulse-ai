import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata = {
  title: "DataPulse AI",
  description:
    "Autonomous Data Incident Intelligence & Response Agent powered by DataHub.",
};

export default function RootLayout({
  children,
}) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}