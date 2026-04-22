import { useState, useEffect, useCallback } from "react";

// Uses relative paths — proxied to FastAPI in dev, same origin in production
const API_BASE = "/api/v1";

const apiFetch = async (path, options = {}) => {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json();
};

// ─────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────

const Toast = ({ message, type, onClose }) => (
  <div style={{
    position: "fixed", bottom: 28, right: 28, zIndex: 9999,
    background: type === "error" ? "#ff3b5c" : "#00c48c",
    color: "#fff", padding: "12px 22px", borderRadius: 10,
    fontFamily: "'DM Mono', monospace", fontSize: 13, fontWeight: 500,
    boxShadow: "0 8px 30px rgba(0,0,0,0.25)",
    display: "flex", alignItems: "center", gap: 12,
    animation: "slideUp 0.3s ease"
  }}>
    <span>{type === "error" ? "✕" : "✓"}</span>
    {message}
    <button onClick={onClose} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16, marginLeft: 4 }}>×</button>
  </div>
);

const StatCard = ({ label, value, sub, accent }) => (
  <div style={{
    background: "#0f1117", border: `1px solid ${accent}33`,
    borderRadius: 14, padding: "22px 26px", flex: 1, minWidth: 140,
    position: "relative", overflow: "hidden"
  }}>
    <div style={{ position: "absolute", top: -20, right: -20, width: 80, height: 80, background: `${accent}18`, borderRadius: "50%" }} />
    <div style={{ fontSize: 11, letterSpacing: 2, color: "#666", textTransform: "uppercase", fontFamily: "'DM Mono', monospace", marginBottom: 10 }}>{label}</div>
    <div style={{ fontSize: 36, fontWeight: 700, color: accent, fontFamily: "'Space Grotesk', sans-serif", lineHeight: 1 }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: "#555", marginTop: 6, fontFamily: "'DM Mono', monospace" }}>{sub}</div>}
  </div>
);

const ItemRow = ({ item, onEdit, onDelete, deleting }) => {
  const date = item.created_at
    ? new Date(item.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    : "—";
  return (
    <div
      style={{ display: "grid", gridTemplateColumns: "40px 1fr 2fr 120px 110px", gap: 16, alignItems: "center", padding: "14px 20px", borderBottom: "1px solid #1a1a2a", transition: "background 0.15s" }}
      onMouseEnter={e => e.currentTarget.style.background = "#0d0f1a"}
      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
    >
      <div style={{ width: 30, height: 30, borderRadius: 8, background: "#1e203a", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#5566aa", fontFamily: "'DM Mono', monospace", fontWeight: 600 }}>{item.id}</div>
      <div style={{ fontWeight: 600, color: "#e8eaf6", fontSize: 14, fontFamily: "'Space Grotesk', sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.name}</div>
      <div style={{ color: "#556", fontSize: 13, fontFamily: "'DM Mono', monospace", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
        {item.description || <em style={{ color: "#333" }}>No description</em>}
      </div>
      <div style={{ fontSize: 11, color: "#445", fontFamily: "'DM Mono', monospace" }}>{date}</div>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => onEdit(item)} style={{ padding: "5px 12px", borderRadius: 6, border: "1px solid #2a3060", background: "transparent", color: "#6688ff", cursor: "pointer", fontSize: 12, fontFamily: "'DM Mono', monospace" }}
          onMouseEnter={e => e.currentTarget.style.background = "#1e2050"}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
        >Edit</button>
        <button onClick={() => onDelete(item.id)} disabled={deleting === item.id} style={{ padding: "5px 10px", borderRadius: 6, border: "1px solid #3a1a22", background: "transparent", color: deleting === item.id ? "#444" : "#ff5577", cursor: deleting === item.id ? "not-allowed" : "pointer", fontSize: 12, fontFamily: "'DM Mono', monospace" }}
          onMouseEnter={e => { if (deleting !== item.id) e.currentTarget.style.background = "#2a0f16"; }}
          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
        >{deleting === item.id ? "..." : "Del"}</button>
      </div>
    </div>
  );
};

const Modal = ({ open, title, onClose, children }) => {
  if (!open) return null;
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", backdropFilter: "blur(4px)" }} onClick={onClose}>
      <div style={{ background: "#0f1117", border: "1px solid #1e2040", borderRadius: 18, padding: "32px 36px", minWidth: 420, boxShadow: "0 30px 80px rgba(0,0,0,0.6)", animation: "fadeIn 0.2s ease" }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#e8eaf6", fontFamily: "'Space Grotesk', sans-serif", marginBottom: 24 }}>{title}</div>
        {children}
      </div>
    </div>
  );
};

const Field = ({ label, value, onChange, placeholder, multiline }) => (
  <div style={{ marginBottom: 18 }}>
    <label style={{ display: "block", fontSize: 11, color: "#556", letterSpacing: 1.5, textTransform: "uppercase", fontFamily: "'DM Mono', monospace", marginBottom: 7 }}>{label}</label>
    {multiline
      ? <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={3} style={{ width: "100%", background: "#0a0b12", border: "1px solid #1e2040", borderRadius: 9, color: "#d0d4f0", padding: "10px 14px", fontSize: 13, fontFamily: "'DM Mono', monospace", outline: "none", resize: "vertical", boxSizing: "border-box" }}
          onFocus={e => e.target.style.borderColor = "#6688ff"} onBlur={e => e.target.style.borderColor = "#1e2040"} />
      : <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={{ width: "100%", background: "#0a0b12", border: "1px solid #1e2040", borderRadius: 9, color: "#d0d4f0", padding: "10px 14px", fontSize: 13, fontFamily: "'DM Mono', monospace", outline: "none", boxSizing: "border-box" }}
          onFocus={e => e.target.style.borderColor = "#6688ff"} onBlur={e => e.target.style.borderColor = "#1e2040"} />}
  </div>
);

// ─────────────────────────────────────────────
// MAIN DASHBOARD
// ─────────────────────────────────────────────

export default function ItemsDashboard() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 20;

  const [toast, setToast] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [form, setForm] = useState({ name: "", description: "" });
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(null);

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const loadStats = useCallback(async () => {
    try {
      const data = await apiFetch("/items/stats");
      setStats(data);
    } catch {
      // non-critical, silently skip
    }
  }, []);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, page_size: PAGE_SIZE });
      if (search) params.set("search", search);
      const data = await apiFetch(`/items?${params}`);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { setPage(1); }, [search]);
  useEffect(() => { loadItems(); }, [loadItems]);

  const openCreate = () => { setEditItem(null); setForm({ name: "", description: "" }); setModalOpen(true); };
  const openEdit = (item) => { setEditItem(item); setForm({ name: item.name, description: item.description || "" }); setModalOpen(true); };
  const closeModal = () => { setModalOpen(false); setEditItem(null); };

  const handleSubmit = async () => {
    if (!form.name.trim()) { showToast("Item name is required", "error"); return; }
    setSubmitting(true);
    try {
      if (editItem) {
        await apiFetch(`/items/${editItem.id}`, { method: "PUT", body: JSON.stringify(form) });
        showToast("Item updated successfully");
      } else {
        await apiFetch("/items", { method: "POST", body: JSON.stringify(form) });
        showToast("Item created successfully");
      }
      closeModal();
      loadItems();
      loadStats();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    setDeleting(id);
    try {
      await apiFetch(`/items/${id}`, { method: "DELETE" });
      showToast("Item deleted");
      loadItems();
      loadStats();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setDeleting(null);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const latestDate = stats?.latest_item_created_at
    ? new Date(stats.latest_item_created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })
    : "—";

  return (
    <div style={{ minHeight: "100vh", background: "#080910", fontFamily: "'DM Mono', monospace", padding: "0 0 60px 0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;600;700&display=swap');
        @keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #080910; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: #0a0b12; } ::-webkit-scrollbar-thumb { background: #1e2040; border-radius: 4px; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom: "1px solid #111320", padding: "22px 36px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 36, height: 36, background: "linear-gradient(135deg, #0033cc, #6688ff)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>🥤</div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: "#e8eaf6", fontFamily: "'Space Grotesk', sans-serif", letterSpacing: -0.5 }}>PepsiCo POC</div>
            <div style={{ fontSize: 11, color: "#445", letterSpacing: 1.5, textTransform: "uppercase" }}>Items Dashboard</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={() => { loadItems(); loadStats(); }} disabled={loading} style={{ padding: "8px 16px", background: "transparent", border: "1px solid #1e2040", borderRadius: 8, color: "#778", cursor: loading ? "not-allowed" : "pointer", fontSize: 12 }}>
            {loading ? "Syncing…" : "↻ Refresh"}
          </button>
          <button onClick={openCreate} style={{ padding: "8px 20px", background: "linear-gradient(135deg, #0033cc, #4455ee)", border: "none", borderRadius: 8, color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", boxShadow: "0 4px 20px #0033cc44" }}>
            + New Item
          </button>
        </div>
      </div>

      <div style={{ padding: "32px 36px" }}>
        {/* Stat Cards */}
        <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
          <StatCard label="Total Items" value={stats?.total_items ?? "—"} sub="in database" accent="#6688ff" />
          <StatCard label="With Description" value={stats?.items_with_description ?? "—"} sub={`${stats?.description_coverage_pct ?? 0}% coverage`} accent="#00c48c" />
          <StatCard label="Latest Added" value={latestDate} sub={stats?.latest_item_name ?? "—"} accent="#ffaa44" />
          <StatCard label="Page Results" value={items.length} sub={`of ${total} total`} accent="#cc44ff" />
        </div>

        {/* Table */}
        <div style={{ background: "#0a0b12", border: "1px solid #111320", borderRadius: 16, overflow: "hidden" }}>
          <div style={{ padding: "18px 20px", borderBottom: "1px solid #111320", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search by name or description…"
              style={{ flex: 1, maxWidth: 360, background: "#080910", border: "1px solid #1a1c30", borderRadius: 8, color: "#c0c4e0", padding: "9px 14px", fontSize: 13, fontFamily: "'DM Mono', monospace", outline: "none" }}
            />
            <span style={{ fontSize: 12, color: "#334" }}>{total} item{total !== 1 ? "s" : ""}</span>
          </div>

          {/* Column headers */}
          <div style={{ display: "grid", gridTemplateColumns: "40px 1fr 2fr 120px 110px", gap: 16, padding: "10px 20px", borderBottom: "1px solid #0e0f1c", fontSize: 10, color: "#334", textTransform: "uppercase", letterSpacing: 1.5 }}>
            <div>#</div><div>Name</div><div>Description</div><div>Created</div><div>Actions</div>
          </div>

          {loading ? (
            <div style={{ padding: "60px 20px", textAlign: "center", color: "#334", fontSize: 13 }}>Loading…</div>
          ) : items.length === 0 ? (
            <div style={{ padding: "60px 20px", textAlign: "center", color: "#334", fontSize: 13 }}>
              {search ? "No items match your search." : "No items yet — create your first one!"}
            </div>
          ) : (
            items.map(item => <ItemRow key={item.id} item={item} onEdit={openEdit} onDelete={handleDelete} deleting={deleting} />)
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ padding: "14px 20px", borderTop: "1px solid #111320", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ padding: "6px 16px", background: "transparent", border: "1px solid #1e2040", borderRadius: 7, color: page === 1 ? "#333" : "#778", cursor: page === 1 ? "not-allowed" : "pointer", fontSize: 12 }}>← Prev</button>
              <span style={{ fontSize: 12, color: "#445" }}>Page {page} of {totalPages}</span>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{ padding: "6px 16px", background: "transparent", border: "1px solid #1e2040", borderRadius: 7, color: page === totalPages ? "#333" : "#778", cursor: page === totalPages ? "not-allowed" : "pointer", fontSize: 12 }}>Next →</button>
            </div>
          )}
        </div>
      </div>

      {/* Create / Edit Modal */}
      <Modal open={modalOpen} title={editItem ? "Edit Item" : "Create New Item"} onClose={closeModal}>
        <Field label="Item Name *" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} placeholder="e.g. Pepsi Max 500ml" />
        <Field label="Description" value={form.description} onChange={v => setForm(f => ({ ...f, description: v }))} placeholder="Optional description…" multiline />
        <div style={{ display: "flex", gap: 10, marginTop: 8, justifyContent: "flex-end" }}>
          <button onClick={closeModal} style={{ padding: "10px 22px", background: "transparent", border: "1px solid #1e2040", borderRadius: 8, color: "#778", cursor: "pointer", fontSize: 13 }}>Cancel</button>
          <button onClick={handleSubmit} disabled={submitting} style={{ padding: "10px 24px", background: submitting ? "#1e2040" : "linear-gradient(135deg, #0033cc, #4455ee)", border: "none", borderRadius: 8, color: submitting ? "#556" : "#fff", cursor: submitting ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>
            {submitting ? "Saving…" : editItem ? "Save Changes" : "Create Item"}
          </button>
        </div>
      </Modal>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}
