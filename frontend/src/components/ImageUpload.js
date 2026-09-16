/**
 * ImageUpload component — drag-and-drop or click-to-upload for defect images.
 */

"use client";

import { useState, useRef } from "react";
import styles from "./ImageUpload.module.css";

export default function ImageUpload({ sessionId, onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file || !file.type.startsWith("image/")) return;

    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);

    // Upload
    setUploading(true);
    try {
      // TODO: call uploadImage(sessionId, file) from lib/api.js
      if (onUploadComplete) onUploadComplete({ fileName: file.name });
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer?.files?.[0];
    handleFile(file);
  };

  return (
    <div className={styles.container}>
      <div
        className={`${styles.dropzone} ${isDragging ? styles.dragging : ""}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        id="image-upload-zone"
      >
        {preview ? (
          <img src={preview} alt="Preview" className={styles.preview} />
        ) : (
          <div className={styles.placeholder}>
            <span className={styles.icon}>📷</span>
            <p>Drop an image here or click to upload</p>
            <p className={styles.hint}>JPEG or PNG — dispensing defect photo</p>
          </div>
        )}
        {uploading && <div className={styles.overlay}>Uploading...</div>}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png"
        onChange={(e) => handleFile(e.target.files?.[0])}
        className={styles.hidden}
        id="image-file-input"
      />
    </div>
  );
}
