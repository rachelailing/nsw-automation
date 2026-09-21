"use client";

import { useState } from "react";
import { downloadReportPdf } from "@/lib/api";
import styles from "./ReportDownload.module.css";


const REPORT_READY_STEPS = new Set([
  "awaiting_feedback",
  "awaiting_feedback_action",
  "awaiting_feedback_cause",
  "closed",
]);


export default function ReportDownload({ sessionId, currentStep }) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState("");

  if (!REPORT_READY_STEPS.has(currentStep)) return null;

  async function handleDownload() {
    setIsDownloading(true);
    setError("");
    try {
      const { blob, filename } = await downloadReportPdf(sessionId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className={styles.bar}>
      <div>
        <strong>Troubleshooting report ready</strong>
        {error && <span className={styles.error}>{error}</span>}
      </div>
      <button
        className={styles.button}
        disabled={isDownloading}
        onClick={handleDownload}
        type="button"
      >
        {isDownloading ? "Generating..." : "Download PDF"}
      </button>
    </div>
  );
}
