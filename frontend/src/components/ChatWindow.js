/**
 * ChatWindow component — displays the conversation between user and AI.
 *
 * Shows message bubbles, a typing indicator when waiting for AI response,
 * and the current step in the troubleshooting flow.
 */

"use client";

import styles from "./ChatWindow.module.css";

export default function ChatWindow({ messages, isLoading, currentStep }) {
  return (
    <div className={styles.container}>
      <div className={styles.stepIndicator}>
        Step: <span className={styles.stepBadge}>{currentStep}</span>
      </div>

      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.welcome}>
            <h2>👋 Welcome to Defect Detective</h2>
            <p>
              Describe your dispensing problem and I&apos;ll help you identify the
              defect, rank probable causes, and create an action plan.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`${styles.message} ${
              msg.role === "user" ? styles.user : styles.assistant
            }`}
          >
            <div className={styles.bubble}>{msg.content}</div>
          </div>
        ))}

        {isLoading && (
          <div className={`${styles.message} ${styles.assistant}`}>
            <div className={styles.bubble}>
              <span className={styles.typing}>
                <span></span>
                <span></span>
                <span></span>
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
