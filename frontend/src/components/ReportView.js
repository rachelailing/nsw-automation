/**
 * ReportView component — displays the final troubleshooting report.
 *
 * Shows the defect summary, ranked causes with confidence bars,
 * and the action plan checklist.
 */

"use client";

import styles from "./ReportView.module.css";

export default function ReportView({ report }) {
  if (!report) return null;

  return (
    <div className={styles.container} id="report-view">
      <h2 className={styles.title}>📋 Troubleshooting Report</h2>

      {report.summary && (
        <section className={styles.section}>
          <h3>Summary</h3>
          <p>{report.summary}</p>
        </section>
      )}

      {report.action_plan?.length > 0 && (
        <section className={styles.section}>
          <h3>Action Plan</h3>
          <ol className={styles.actionList}>
            {report.action_plan.map((step, i) => (
              <li key={i} className={styles.actionItem}>
                <div className={styles.actionHeader}>
                  <span className={`${styles.priority} ${styles[step.priority]}`}>
                    {step.priority}
                  </span>
                  <strong>{step.action}</strong>
                </div>
                <p className={styles.rationale}>{step.rationale}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {report.recommendations?.length > 0 && (
        <section className={styles.section}>
          <h3>Preventive Recommendations</h3>
          <ul className={styles.recommendations}>
            {report.recommendations.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
