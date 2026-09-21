"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  deleteKnowledgeSource,
  getActiveKnowledgePack,
  importKnowledgeSource,
} from "@/lib/api";
import styles from "./KnowledgePackPanel.module.css";

const CONTENT_TABS = [
  ["materials", "Materials"],
  ["defect_rules", "Defect rules"],
  ["troubleshooting_actions", "Actions"],
];

function ContentRows({ type, rows }) {
  if (!rows?.length) {
    return <div className={styles.empty}>No approved records</div>;
  }

  return (
    <div className={styles.rows}>
      {rows.map((row) => (
        <article className={styles.row} key={`${type}-${row.id}`}>
          <div className={styles.rowMain}>
            <strong>
              {type === "materials" && row.name}
              {type === "defect_rules" && row.possible_cause}
              {type === "troubleshooting_actions" && row.action}
            </strong>
            <span>
              {type === "materials" && (row.material_type || "Material")}
              {type === "defect_rules" && `${row.defect_type} · ${row.category}`}
              {type === "troubleshooting_actions" && `${row.defect_type} · Step ${row.sequence}`}
            </span>
          </div>
          <code>source:{row.source_id ?? "unlinked"}</code>
        </article>
      ))}
    </div>
  );
}

function DraftSummary({ source }) {
  const extracted = source?.extracted_content;
  if (!source) return null;

  if (!extracted) {
    return (
      <section className={styles.draft}>
        <div className={styles.sectionHeading}>
          <div>
            <p className={styles.eyebrow}>Source details</p>
            <h3>{source.original_filename || source.source_name}</h3>
          </div>
          <span className={styles.failed}>{source.extraction_status}</span>
        </div>
        <div className={styles.failureMessage}>
          {source.error_message || "No extracted content is available for this source."}
        </div>
      </section>
    );
  }

  const visibleConditions = (conditions = {}) =>
    Object.entries(conditions).filter(([, value]) => {
      if (Array.isArray(value)) return value.length > 0;
      return value !== null && value !== undefined && value !== "";
    });

  return (
    <section className={styles.draft}>
      <div className={styles.sectionHeading}>
        <div>
          <p className={styles.eyebrow}>Extraction preview</p>
          <h3>{source.original_filename || source.source_name}</h3>
        </div>
        <span className={styles.pending}>{source.review_status?.replace("_", " ")}</span>
      </div>
      <div className={styles.draftCounts}>
        <span>{extracted.materials?.length || 0} materials</span>
        <span>{extracted.defect_rules?.length || 0} rules</span>
        <span>{extracted.troubleshooting_actions?.length || 0} actions</span>
      </div>
      {extracted.warnings?.length > 0 && (
        <div className={styles.warning}>{extracted.warnings.join(" ")}</div>
      )}

      <div className={styles.draftContent}>
        <section className={styles.draftGroup}>
          <h4>Materials</h4>
          {extracted.materials?.length ? (
            extracted.materials.map((material, index) => (
              <article className={styles.draftItem} key={`${material.name}-${index}`}>
                <div className={styles.itemHeading}>
                  <strong>{material.name}</strong>
                  <span>{material.material_type || "Material"}</span>
                </div>
                {(material.viscosity_min != null || material.viscosity_max != null) && (
                  <p>
                    <b>Viscosity:</b> {material.viscosity_min ?? "-"} to{" "}
                    {material.viscosity_max ?? "-"} {material.viscosity_unit || ""}
                  </p>
                )}
                {material.aliases?.length > 0 && (
                  <p><b>Aliases:</b> {material.aliases.join(", ")}</p>
                )}
                {material.handling_notes && (
                  <p><b>Handling:</b> {material.handling_notes}</p>
                )}
                {material.storage_conditions && (
                  <p><b>Storage:</b> {material.storage_conditions}</p>
                )}
              </article>
            ))
          ) : (
            <div className={styles.emptyGroup}>No materials extracted</div>
          )}
        </section>

        <section className={styles.draftGroup}>
          <h4>Defect rules</h4>
          {extracted.defect_rules?.length ? (
            extracted.defect_rules.map((rule, index) => (
              <article className={styles.draftItem} key={`${rule.possible_cause}-${index}`}>
                <div className={styles.itemHeading}>
                  <strong>{rule.possible_cause}</strong>
                  <span>{rule.defect_type}</span>
                </div>
                <p><b>Category:</b> {rule.category}</p>
                <p><b>Reasoning:</b> {rule.reasoning}</p>
                <p><b>Evidence weight:</b> {rule.evidence_weight}</p>
                {visibleConditions(rule.conditions).length > 0 && (
                  <div className={styles.conditions}>
                    {visibleConditions(rule.conditions).map(([key, value]) => (
                      <span key={key}>
                        {key.replaceAll("_", " ")}: {Array.isArray(value) ? value.join(", ") : String(value)}
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))
          ) : (
            <div className={styles.emptyGroup}>No defect rules extracted</div>
          )}
        </section>

        <section className={styles.draftGroup}>
          <h4>Troubleshooting actions</h4>
          {extracted.troubleshooting_actions?.length ? (
            extracted.troubleshooting_actions.map((action, index) => (
              <article className={styles.draftItem} key={`${action.action}-${index}`}>
                <div className={styles.itemHeading}>
                  <strong>{action.sequence}. {action.action}</strong>
                  <span>{action.defect_type}</span>
                </div>
                <p><b>Cause:</b> {action.cause}</p>
                {action.safety_notes && (
                  <p><b>Safety:</b> {action.safety_notes}</p>
                )}
                <p>
                  <b>Approval:</b>{" "}
                  {action.requires_approval ? "Engineer approval required" : "No additional approval specified"}
                </p>
              </article>
            ))
          ) : (
            <div className={styles.emptyGroup}>No actions extracted</div>
          )}
        </section>
      </div>
    </section>
  );
}

export default function KnowledgePackPanel() {
  const inputRef = useRef(null);
  const [data, setData] = useState(null);
  const [activeTab, setActiveTab] = useState("materials");
  const [selectedSourceId, setSelectedSourceId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState("");

  async function refresh(preferredSourceId = null) {
    const response = await getActiveKnowledgePack();
    setData(response);
    setSelectedSourceId((current) => {
      const candidate = preferredSourceId || current;
      const candidateExists = response.sources?.some((source) => source.id === candidate);
      return candidateExists ? candidate : response.sources?.[0]?.id || null;
    });
  }

  useEffect(() => {
    getActiveKnowledgePack()
      .then((response) => {
        setData(response);
        setSelectedSourceId(response.sources?.[0]?.id || null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  const selectedSource = useMemo(
    () => data?.sources?.find((source) => source.id === selectedSourceId),
    [data, selectedSourceId],
  );

  async function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setIsUploading(true);
    setError("");
    try {
      const source = await importKnowledgeSource(file);
      await refresh(source.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteSource() {
    if (!selectedSource || selectedSource.review_status === "approved") return;

    const filename = selectedSource.original_filename || selectedSource.source_name;
    if (!window.confirm(`Delete ${filename}? This cannot be undone.`)) return;

    setIsDeleting(true);
    setError("");
    try {
      await deleteKnowledgeSource(selectedSource.id);
      setSelectedSourceId(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return <div className={styles.centerState}>Loading Knowledge Pack...</div>;
  }

  return (
    <div className={styles.panel}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Active Knowledge Pack</p>
          <h2>{data?.pack?.name || "Unavailable"}</h2>
          <p className={styles.meta}>
            Version {data?.pack?.version ?? "-"} · {data?.pack?.status || "unknown"}
          </p>
        </div>
        <button
          className={styles.importButton}
          disabled={isUploading}
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          {isUploading ? "Extracting..." : "Import source"}
        </button>
        <input
          ref={inputRef}
          className={styles.fileInput}
          type="file"
          accept=".json,.md,.pdf,.txt"
          onChange={handleFile}
        />
      </header>

      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.metrics}>
        <span><strong>{data?.content?.materials?.length || 0}</strong> materials</span>
        <span><strong>{data?.content?.defect_rules?.length || 0}</strong> rules</span>
        <span><strong>{data?.content?.troubleshooting_actions?.length || 0}</strong> actions</span>
        <span><strong>{data?.sources?.length || 0}</strong> sources</span>
      </div>

      <section className={styles.contentSection}>
        <div className={styles.tabs} role="tablist" aria-label="Knowledge content">
          {CONTENT_TABS.map(([key, label]) => (
            <button
              className={activeTab === key ? styles.activeTab : styles.tab}
              key={key}
              onClick={() => setActiveTab(key)}
              role="tab"
              aria-selected={activeTab === key}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <ContentRows type={activeTab} rows={data?.content?.[activeTab]} />
      </section>

      <section className={styles.sourcesSection}>
        <div className={styles.sectionHeading}>
          <div>
            <p className={styles.eyebrow}>Provenance</p>
            <h3>Sources</h3>
          </div>
          {selectedSource && selectedSource.review_status !== "approved" && (
            <button
              className={styles.deleteButton}
              disabled={isDeleting}
              onClick={handleDeleteSource}
              type="button"
            >
              {isDeleting ? "Deleting..." : "Delete source"}
            </button>
          )}
        </div>
        <div className={styles.sourceList}>
          {data?.sources?.map((source) => (
            <button
              className={source.id === selectedSourceId ? styles.selectedSource : styles.source}
              key={source.id}
              onClick={() => setSelectedSourceId(source.id)}
              type="button"
            >
              <span>{source.original_filename || source.source_name}</span>
              <small>{source.extraction_status} · {source.review_status}</small>
            </button>
          ))}
        </div>
      </section>

      <DraftSummary source={selectedSource} />
    </div>
  );
}
