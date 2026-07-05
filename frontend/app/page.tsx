"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, ArrowLeft, CheckCircle2, FileText, Loader2, Plus, Send, Trash2, UploadCloud } from "lucide-react";
import {
  askQuestion,
  createWorkspace,
  deleteWorkspace,
  DocumentItem,
  listDocuments,
  listWorkspaces,
  uploadDocuments,
  Workspace,
} from "@/lib/api";

type Message = {
  id: string;
  role: "user" | "assistant";
  text: string;
  citations?: Array<{ filename: string; page: number }>;
};

const WORKSPACE_KEY = "pdfqa.workspaceId";

export default function Home() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceName, setWorkspaceName] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [deletingWorkspaceId, setDeletingWorkspaceId] = useState<string | null>(null);
  const [workspaceToDelete, setWorkspaceToDelete] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const hasReadyDocument = documents.some((document) => document.status === "ready");
  const hasActiveJob = documents.some((document) => ["queued", "processing"].includes(document.status));

  const statusCounts = useMemo(
    () => ({
      ready: documents.filter((document) => document.status === "ready").length,
      processing: documents.filter((document) => ["queued", "processing"].includes(document.status)).length,
      failed: documents.filter((document) => document.status === "failed").length,
    }),
    [documents],
  );

  useEffect(() => {
    async function loadWorkspaceList() {
      const existingId = window.localStorage.getItem(WORKSPACE_KEY);
      const items = await listWorkspaces();
      setWorkspaces(items);

      if (existingId && items.some((workspace) => workspace.id === existingId)) {
        setWorkspaceId(existingId);
      } else {
        window.localStorage.removeItem(WORKSPACE_KEY);
      }
    }

    loadWorkspaceList().catch((caught) => setError(readError(caught)));
  }, []);

  useEffect(() => {
    if (!workspaceId) {
      return;
    }

    let cancelled = false;

    async function refresh() {
      try {
        const items = await listDocuments(workspaceId);
        if (!cancelled) {
          setDocuments(items);
          setError(null);
        }
      } catch (caught) {
        if (!cancelled) {
          const message = readError(caught);
          if (message.includes("Workspace not found")) {
            leaveWorkspace();
            const items = await listWorkspaces();
            setWorkspaces(items);
            setError(null);
          } else {
            setError(message);
          }
        }
      }
    }

    refresh();
    const intervalId = window.setInterval(refresh, hasActiveJob ? 2000 : 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [workspaceId, hasActiveJob]);

  async function handleCreateWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceName.trim() || isCreatingWorkspace) {
      return;
    }

    setError(null);
    setIsCreatingWorkspace(true);
    try {
      const workspace = await createWorkspace(workspaceName.trim());
      setWorkspaces((current) => [workspace, ...current]);
      selectWorkspace(workspace.id);
      setWorkspaceName("");
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setIsCreatingWorkspace(false);
    }
  }

  function selectWorkspace(id: string) {
    window.localStorage.setItem(WORKSPACE_KEY, id);
    setWorkspaceId(id);
    setDocuments([]);
    setMessages([]);
    setQuestion("");
  }

  function leaveWorkspace() {
    window.localStorage.removeItem(WORKSPACE_KEY);
    setWorkspaceId(null);
    setDocuments([]);
    setMessages([]);
    setQuestion("");
  }

  async function handleDeleteWorkspace() {
    if (!workspaceToDelete) {
      return;
    }

    setError(null);
    setDeletingWorkspaceId(workspaceToDelete.id);
    try {
      await deleteWorkspace(workspaceToDelete.id);
      const items = await listWorkspaces();
      setWorkspaces(items);
      if (window.localStorage.getItem(WORKSPACE_KEY) === workspaceToDelete.id) {
        leaveWorkspace();
      }
      setWorkspaceToDelete(null);
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setDeletingWorkspaceId(null);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length || !workspaceId) {
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const response = await uploadDocuments(workspaceId, files);
      setDocuments((current) => [...response.documents, ...current]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !question.trim() || isAsking) {
      return;
    }

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      text: question.trim(),
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setError(null);
    setIsAsking(true);

    try {
      const response = await askQuestion(workspaceId, userMessage.text);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: response.answer,
          citations: response.citations,
        },
      ]);
    } catch (caught) {
      setError(readError(caught));
    } finally {
      setIsAsking(false);
    }
  }

  if (!workspaceId) {
    return (
      <main className="app-shell">
        <section className="workspace-panel">
          <div>
            <p className="eyebrow">Document QA</p>
            <h1>Choose a workspace</h1>
          </div>
        </section>

        {error ? (
          <div className="notice error" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        <section className="workspace-home">
          <form className="new-workspace" onSubmit={handleCreateWorkspace}>
            <div>
              <div className="section-title">New Workspace</div>
              <input
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
                placeholder="Workspace name"
                maxLength={120}
              />
            </div>
            <button type="submit" disabled={!workspaceName.trim() || isCreatingWorkspace}>
              {isCreatingWorkspace ? <Loader2 size={18} className="spin" /> : <Plus size={18} />}
              <span>Create</span>
            </button>
          </form>

          <div className="workspace-list">
            <div className="section-title">Existing Workspaces</div>
            {workspaces.length === 0 ? (
              <p className="muted">No workspaces yet.</p>
            ) : (
              workspaces.map((workspace) => (
                <div key={workspace.id} className="workspace-row">
                  <button className="workspace-button" onClick={() => selectWorkspace(workspace.id)}>
                    <span>{workspace.name}</span>
                    <small>{new Date(workspace.created_at).toLocaleString()}</small>
                  </button>
                  <button
                    className="icon-button danger"
                    onClick={() => setWorkspaceToDelete(workspace)}
                    disabled={deletingWorkspaceId === workspace.id}
                    aria-label={`Delete ${workspace.name}`}
                    title={`Delete ${workspace.name}`}
                  >
                    {deletingWorkspaceId === workspace.id ? <Loader2 size={17} className="spin" /> : <Trash2 size={17} />}
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        {workspaceToDelete ? (
          <div className="modal-backdrop" role="presentation">
            <div className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-workspace-title">
              <div>
                <p className="eyebrow">Delete Workspace</p>
                <h2 id="delete-workspace-title">{workspaceToDelete.name}</h2>
                <p className="muted">This will remove the workspace, uploaded documents, processing jobs, and indexed chunks.</p>
              </div>
              <div className="dialog-actions">
                <button className="secondary-button" onClick={() => setWorkspaceToDelete(null)}>
                  Cancel
                </button>
                <button className="danger-button" onClick={handleDeleteWorkspace} disabled={deletingWorkspaceId === workspaceToDelete.id}>
                  {deletingWorkspaceId === workspaceToDelete.id ? <Loader2 size={17} className="spin" /> : <Trash2 size={17} />}
                  <span>Delete</span>
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    );
  }

  const selectedWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);

  return (
    <main className="app-shell">
      <section className="workspace-panel">
        <div>
          <p className="eyebrow">Document QA</p>
          <h1>{selectedWorkspace?.name ?? "Workspace"}</h1>
        </div>
        <div className="workspace-actions">
          <button className="secondary-button" onClick={leaveWorkspace}>
            <ArrowLeft size={16} />
            <span>Workspaces</span>
          </button>
          <div className="metrics" aria-label="Document processing summary">
            <span>{statusCounts.ready} ready</span>
            <span>{statusCounts.processing} processing</span>
            <span>{statusCounts.failed} failed</span>
          </div>
        </div>
      </section>

      {error ? (
        <div className="notice error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <section className="layout-grid">
        <aside className="side-panel">
          <label className="upload-zone">
            <UploadCloud size={28} />
            <span>{isUploading ? "Uploading..." : "Upload PDFs"}</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              multiple
              disabled={isUploading || !workspaceId}
              onChange={(event) => handleUpload(event.target.files)}
            />
          </label>

          <div className="document-list">
            <div className="section-title">Documents</div>
            {documents.length === 0 ? (
              <p className="muted">No PDFs uploaded yet.</p>
            ) : (
              documents.map((document) => <DocumentRow key={document.id} document={document} />)
            )}
          </div>
        </aside>

        <section className="chat-panel">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                <FileText size={32} />
                <p>Upload a PDF, wait until it is ready, then ask a question.</p>
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}
            {isAsking ? (
              <div className="message assistant loading">
                <Loader2 size={16} className="spin" />
                <span>Reading the documents...</span>
              </div>
            ) : null}
          </div>

          <form className="composer" onSubmit={handleAsk}>
            <input
              value={question}
              disabled={!hasReadyDocument || isAsking}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={hasReadyDocument ? "Ask a question about your PDFs" : "Waiting for a ready document"}
            />
            <button type="submit" disabled={!hasReadyDocument || isAsking || !question.trim()} aria-label="Send question">
              <Send size={18} />
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function DocumentRow({ document }: { document: DocumentItem }) {
  return (
    <div className="document-row">
      <FileText size={18} />
      <div>
        <div className="filename">{document.filename}</div>
        {document.job?.error_message ? <div className="error-text">{document.job.error_message}</div> : null}
      </div>
      <StatusBadge status={document.status} />
    </div>
  );
}

function StatusBadge({ status }: { status: DocumentItem["status"] }) {
  const icon = status === "ready" ? <CheckCircle2 size={14} /> : status === "failed" ? <AlertCircle size={14} /> : <Loader2 size={14} className="spin" />;
  return (
    <span className={`status ${status}`}>
      {icon}
      {status}
    </span>
  );
}

function MessageBubble({ message }: { message: Message }) {
  return (
    <article className={`message ${message.role}`}>
      <p>{message.text}</p>
      {message.citations?.length ? (
        <div className="citations">
          {message.citations.map((citation) => (
            <span key={`${citation.filename}-${citation.page}`}>
              {citation.filename}, page {citation.page}
            </span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function readError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}
