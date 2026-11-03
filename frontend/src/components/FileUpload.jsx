
import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useAction } from "../hooks/useAction";
import { useToast } from "./Toast";
import ConfirmDialog from "./ConfirmDialog";


const PURPOSE_TYPES = {
  room_image: [
    "image/jpeg",
    "image/png",
    "image/webp",
  ],
  id_proof: [
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
  ],
  maintenance_photo: [
    "image/jpeg",
    "image/png",
    "image/webp",
  ],
};


function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}


function isPdfUrl(url) {
  if (!url) return false;

  const path = String(url).split("?")[0].toLowerCase();

  return path.endsWith(".pdf");
}


export default function FileUpload({
  purpose,
  recordId,
  value = null,
  label = "Upload file",
  helperText,
  maxBytes = 5242880,
  allowedTypes,
  onUploaded,
  onRemoved,
  disabled = false,
  allowRemove = true,
}) {
  const { notify } = useToast();

  const inputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [localPreview, setLocalPreview] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);

  const acceptedTypes =
    allowedTypes || PURPOSE_TYPES[purpose] || [];

  const accept = acceptedTypes.join(",");

  // Generate a temporary local preview for the selected file.
  useEffect(() => {
    if (!selectedFile) {
      setLocalPreview("");
      return undefined;
    }

    const url = URL.createObjectURL(selectedFile);

    setLocalPreview(url);

    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);


  // -------------------------------------------------------
  // Upload action
  // -------------------------------------------------------

  const {
    run: performUpload,
    busy: uploadBusy,
  } = useAction(async (file) => {
    const formData = new FormData();

    formData.append("file", file);

    const result = await api.upload(
      `/uploads/${purpose}/${recordId}`,
      formData,
    );

    setSelectedFile(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }

    await onUploaded?.(result);

    notify("File uploaded successfully", "success");

    return result;
  });


  // -------------------------------------------------------
  // Delete action
  // -------------------------------------------------------

  const {
    run: performRemove,
    busy: removeBusy,
  } = useAction(async () => {
    const result = await api.delete(
      `/uploads/${purpose}/${recordId}`,
    );

    setSelectedFile(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }

    setConfirmOpen(false);

    await onRemoved?.(result);

    notify("File removed successfully", "success");

    return result;
  });


  // -------------------------------------------------------
  // File validation
  // -------------------------------------------------------

  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    if (!acceptedTypes.includes(file.type)) {
      notify(
        `Unsupported file type. Allowed: ${acceptedTypes.join(", ")}`,
        "error",
      );

      event.target.value = "";
      return;
    }

    if (file.size === 0) {
      notify("The selected file is empty", "error");

      event.target.value = "";
      return;
    }

    if (file.size > maxBytes) {
      notify(
        `File is too large. Maximum size is ${formatBytes(maxBytes)}`,
        "error",
      );

      event.target.value = "";
      return;
    }

    setSelectedFile(file);
  }


  async function handleUpload() {
    if (!selectedFile) {
      notify("Please select a file first", "error");
      return;
    }

    try {
      await performUpload(selectedFile);
    } catch {
      // useAction already displays the error notification.
    }
  }


  async function handleRemove() {
    try {
      await performRemove();
    } catch {
      // useAction already displays the error notification.
    }
  }


  function handleCancelSelection() {
    setSelectedFile(null);

    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }


  const previewUrl = localPreview || value;

  const currentIsPdf = selectedFile
    ? selectedFile.type === "application/pdf"
    : isPdfUrl(value);

  const hasCurrentFile = Boolean(value);

  const busy = uploadBusy || removeBusy;


  // -------------------------------------------------------
  // Component UI
  // -------------------------------------------------------

  return (
    <div className="fileUpload">

      <div className="fileUploadHeader">
        <label className="fileUploadLabel">
          {label}
        </label>

        <span className="fieldHint">
          Maximum {formatBytes(maxBytes)}
        </span>
      </div>


      {previewUrl && (
        <div className="fileUploadPreview">

          {currentIsPdf ? (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="fileUploadDocument"
            >
              <span aria-hidden="true">📄</span>
              {selectedFile?.name || "View current PDF"}
            </a>
          ) : (
            <img
              src={previewUrl}
              alt={`${label} preview`}
              className="fileUploadImage"
            />
          )}

        </div>
      )}


      {!previewUrl && (
        <div className="fileUploadPlaceholder">
          <span aria-hidden="true">📁</span>
          <span>No file uploaded</span>
        </div>
      )}


      <div className="uploadRow">

        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleFileChange}
          disabled={disabled || busy}
          hidden
        />

        <button
          type="button"
          className="secondary"
          disabled={disabled || busy}
          onClick={() => inputRef.current?.click()}
        >
          Choose file
        </button>


        {selectedFile && (
          <>
            <button
              type="button"
              className="primary"
              disabled={disabled || busy}
              onClick={handleUpload}
            >
              {uploadBusy ? "Uploading..." : "Upload"}
            </button>

            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={handleCancelSelection}
            >
              Cancel
            </button>
          </>
        )}


        {!selectedFile && hasCurrentFile && allowRemove && (
          <button
            type="button"
            className="dangerButton"
            disabled={disabled || busy}
            onClick={() => setConfirmOpen(true)}
          >
            Remove
          </button>
        )}

      </div>


      {selectedFile && (
        <p className="fieldHint">
          Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})
        </p>
      )}


      {helperText && (
        <p className="fieldHint">
          {helperText}
        </p>
      )}


      <ConfirmDialog
        open={confirmOpen}
        title="Remove uploaded file?"
        message="This file will be removed from the hotel management system. This action cannot be undone."
        confirmLabel="Remove file"
        onConfirm={handleRemove}
        onCancel={() => setConfirmOpen(false)}
      />

    </div>
  );
}
