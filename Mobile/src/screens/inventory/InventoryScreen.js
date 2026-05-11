import React, { useEffect, useState, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  fetchInventory,
  createInventoryItem,
  updateInventoryItem,
  deleteInventoryItem,
} from '../../redux/slices/inventorySlice';
import './InventoryScreen.css';

const EMPTY_FORM = { name: '', unit: '', category: '', min_stock_level: '', current_stock: '' };

const getStockStatus = (item) => {
  const current = Number(item.current_stock ?? item.quantityInStock ?? 0);
  const minimum = Number(item.min_stock_level ?? item.lowStockThreshold ?? 1);
  const pct = minimum > 0 ? (current / minimum) * 100 : 100;
  if (pct <= 25) return { label: 'Low',    color: '#ef4444', dot: '#ef4444' };
  if (pct <= 75) return { label: 'Medium', color: '#f59e0b', dot: '#f59e0b' };
  return              { label: 'Good',   color: '#22c55e', dot: '#22c55e' };
};

// ── Small reusable field ──────────────────────────────────────────────────────
const Field = ({ label, value, onChange, type = 'text', min }) => (
  <div className="inv-field">
    <label className="inv-field-label">{label}</label>
    <input
      className="inv-field-input"
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      min={min}
    />
  </div>
);

// ── Add-Item Modal ────────────────────────────────────────────────────────────
const AddItemModal = ({ onClose, onSave }) => {
  const [form, setForm]   = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState('');

  const set = (key) => (val) => setForm(f => ({ ...f, [key]: val }));

  const handleSubmit = async () => {
    if (!form.name.trim()) { setError('Name is required.'); return; }
    const payload = {
      name:           form.name.trim(),
      unit:           form.unit.trim() || 'unit',
      category:       form.category.trim() || '',
      min_stock_level: parseFloat(form.min_stock_level) || 0,
      current_stock:  parseFloat(form.current_stock)   || 0,
    };
    setSaving(true);
    setError('');
    try {
      await onSave(payload);
      onClose();
    } catch {
      setError('Failed to create item. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="inv-modal-overlay" onClick={onClose}>
      <div className="inv-modal" onClick={e => e.stopPropagation()}>
        <div className="inv-modal-header">
          <h2 className="inv-modal-title">New Inventory Item</h2>
          <button className="inv-close-panel" onClick={onClose}>✕</button>
        </div>

        <div className="inv-modal-body">
          <Field label="Name *"         value={form.name}            onChange={set('name')} />
          <Field label="Unit"           value={form.unit}            onChange={set('unit')} />
          <Field label="Category"       value={form.category}        onChange={set('category')} />
          <Field label="Min Stock Level" value={form.min_stock_level} onChange={set('min_stock_level')} type="number" min="0" />
          <Field label="Opening Stock"  value={form.current_stock}   onChange={set('current_stock')}   type="number" min="0" />
        </div>

        {error && <div className="inv-update-error" style={{ margin: '0 0 12px' }}>{error}</div>}

        <div className="inv-modal-footer">
          <button className="inv-cancel-btn" onClick={onClose}>Cancel</button>
          <button className="inv-update-btn" onClick={handleSubmit} disabled={saving}>
            {saving ? 'Creating…' : 'Create Item'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main Screen ───────────────────────────────────────────────────────────────
const InventoryScreen = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { items, isLoading, error } = useSelector(s => s.inventory);

  const [search,      setSearch]      = useState('');
  const [filter,      setFilter]      = useState('all');
  const [selected,    setSelected]    = useState(null);
  const [editForm,    setEditForm]    = useState(null);   // null = view mode, object = edit mode
  const [saving,      setSaving]      = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError,   setSaveError]   = useState('');
  const [showAdd,     setShowAdd]     = useState(false);
  const [deleting,    setDeleting]    = useState(false);

  useEffect(() => { dispatch(fetchInventory()); }, [dispatch]);

  // Sync detail panel when selected item changes in store
  useEffect(() => {
    if (!selected) { setEditForm(null); return; }
    const fresh = items.find(i => i.id === selected.id);
    if (fresh) setSelected(fresh);
  }, [items]); // eslint-disable-line

  const filtered = useMemo(() => items.filter(item => {
    if (search && !(item.name || '').toLowerCase().includes(search.toLowerCase())) return false;
    if (filter === 'low' && getStockStatus(item).label !== 'Low') return false;
    return true;
  }), [items, search, filter]);

  const lowCount = useMemo(() =>
    items.filter(i => getStockStatus(i).label === 'Low').length, [items]);

  const handleSelect = (item) => {
    if (selected?.id === item.id) { setSelected(null); setEditForm(null); return; }
    setSelected(item);
    setEditForm(null);
    setSaveSuccess(false);
    setSaveError('');
  };

  const setEdit = (key) => (val) => setEditForm(f => ({ ...f, [key]: val }));

  const enterEdit = () => setEditForm({
    name:            selected.name || '',
    unit:            selected.unit || '',
    category:        selected.category || '',
    min_stock_level: String(selected.min_stock_level ?? selected.lowStockThreshold ?? 0),
    current_stock:   String(selected.current_stock   ?? selected.quantityInStock   ?? 0),
  });

  const handleSave = async () => {
    if (!editForm) return;
    const stockVal = parseFloat(editForm.current_stock);
    const minVal   = parseFloat(editForm.min_stock_level);
    if (isNaN(stockVal) || stockVal < 0) { setSaveError('Invalid stock value.'); return; }
    setSaving(true); setSaveError('');
    try {
      await dispatch(updateInventoryItem({
        itemId: selected.id ?? selected.inventoryItemId,
        data: {
          name:            editForm.name.trim(),
          unit:            editForm.unit.trim(),
          category:        editForm.category.trim(),
          min_stock_level: isNaN(minVal) ? 0 : minVal,
          current_stock:   stockVal,
          quantityInStock: stockVal,
        },
      })).unwrap();
      setSaveSuccess(true);
      setEditForm(null);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch {
      setSaveError('Failed to update. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${selected.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await dispatch(deleteInventoryItem(selected.id ?? selected.inventoryItemId)).unwrap();
      setSelected(null);
    } catch {
      setSaveError('Failed to delete item.');
    } finally {
      setDeleting(false);
    }
  };

  const handleCreate = async (payload) => {
    await dispatch(createInventoryItem(payload)).unwrap();
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="inv-root">
      <div className="inv-grain" />

      {showAdd && (
        <AddItemModal
          onClose={() => setShowAdd(false)}
          onSave={handleCreate}
        />
      )}

      {/* HEADER */}
      <header className="inv-header">
        <div className="inv-header-left">
          <button className="inv-back" onClick={() => navigate('/im/dashboard')}>← Dashboard</button>
          <div className="inv-header-title-group">
            <h1 className="inv-title">Inventory</h1>
            <span className="inv-subtitle">
              {isLoading ? 'Loading…' : `${items.length} items tracked`}
              {lowCount > 0 && ` · ${lowCount} low`}
            </span>
          </div>
        </div>
        <button className="inv-add-btn" onClick={() => setShowAdd(true)}>+ Add Item</button>
      </header>

      {/* FILTER BAR */}
      <div className="inv-filter-bar">
        <div className="inv-search-wrap">
          <span className="inv-search-icon">🔍</span>
          <input
            className="inv-search"
            placeholder="Search items…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="inv-filter-chips">
          {['all', 'low'].map(f => (
            <button
              key={f}
              className={`inv-chip${filter === f ? ' inv-chip-active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? 'All' : `⚠ Low Stock${lowCount > 0 ? ` (${lowCount})` : ''}`}
            </button>
          ))}
        </div>
      </div>

      {/* BODY */}
      <div className={`inv-body${selected ? ' inv-body-split' : ''}`}>

        {/* List panel */}
        <div className="inv-list-panel">
          {error && <div className="inv-update-error" style={{ marginBottom: 16 }}>{String(error)}</div>}
          {isLoading ? (
            <div className="inv-skeleton-wrap">
              {[1,2,3,4,5].map(i => <div key={i} className="inv-skeleton" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="inv-empty">
              <span className="inv-empty-icon">📦</span>
              <span>{search || filter !== 'all' ? 'No items match your filter.' : 'No inventory items yet.'}</span>
            </div>
          ) : (
            filtered.map((item, idx) => {
              const st      = getStockStatus(item);
              const current = Number(item.current_stock ?? item.quantityInStock ?? 0);
              const isActive = selected?.id === item.id;
              return (
                <div
                  key={String(item.id ?? item.inventoryItemId)}
                  className={`inv-item-row${isActive ? ' inv-item-row-active' : ''}`}
                  style={{ animationDelay: `${idx * 40}ms` }}
                  onClick={() => handleSelect(item)}
                >
                  <div className="inv-item-left">
                    <span className="inv-dot" style={{ background: st.dot }} />
                    <div className="inv-item-info">
                      <span className="inv-item-name">{item.name}</span>
                      <span className="inv-item-unit">Min: {Number(item.min_stock_level ?? item.lowStockThreshold ?? 0)} {item.unit}</span>
                    </div>
                  </div>
                  <div className="inv-item-right">
                    <span className="inv-item-qty">{current}</span>
                    <span className="inv-badge" style={{ background: st.color + '22', color: st.color }}>{st.label}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Detail / Edit panel */}
        {selected && (() => {
          const st      = getStockStatus(selected);
          const current = Number(selected.current_stock ?? selected.quantityInStock ?? 0);
          const minimum = Number(selected.min_stock_level ?? selected.lowStockThreshold ?? 0);
          const isEditing = !!editForm;
          return (
            <div className="inv-detail-panel">
              <button className="inv-close-panel" onClick={() => { setSelected(null); setEditForm(null); }}>✕</button>

              {/* Header */}
              <div className="inv-detail-header">
                <div>
                  <h2 className="inv-detail-name">{selected.name}</h2>
                  <div className="inv-detail-meta">
                    <span className="inv-badge" style={{ background: st.color + '22', color: st.color }}>{st.label} Stock</span>
                    <span className="inv-detail-unit">{selected.unit}</span>
                  </div>
                </div>
                <div className="inv-detail-qty-block">
                  <span className="inv-detail-qty-num">{current}</span>
                  <span className="inv-detail-qty-label">{selected.unit} in stock</span>
                </div>
              </div>

              {!isEditing ? (
                <>
                  {/* Info cards */}
                  <div className="inv-detail-info-row">
                    <div className="inv-detail-info-card">
                      <span className="inv-detail-info-label">Min Level</span>
                      <span className="inv-detail-info-val">{minimum} {selected.unit}</span>
                    </div>
                    <div className="inv-detail-info-card">
                      <span className="inv-detail-info-label">Category</span>
                      <span className="inv-detail-info-val">{selected.category || '—'}</span>
                    </div>
                    <div className="inv-detail-info-card">
                      <span className="inv-detail-info-label">Status</span>
                      <span className="inv-detail-info-val" style={{ color: st.color }}>{st.label}</span>
                    </div>
                    <div className="inv-detail-info-card">
                      <span className="inv-detail-info-label">Active</span>
                      <span className="inv-detail-info-val">{selected.is_active !== false ? 'Yes' : 'No'}</span>
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="inv-detail-actions">
                    <button className="inv-edit-btn" onClick={enterEdit}>✏ Edit Item</button>
                    <button className="inv-delete-btn" onClick={handleDelete} disabled={deleting}>
                      {deleting ? 'Deleting…' : '🗑 Delete'}
                    </button>
                  </div>

                  {saveSuccess && <div className="inv-update-success">✓ Saved successfully</div>}
                  {saveError   && <div className="inv-update-error">{saveError}</div>}
                </>
              ) : (
                /* Edit form */
                <div className="inv-update-section">
                  <p className="inv-update-title">Edit Item</p>
                  <Field label="Name"           value={editForm.name}            onChange={setEdit('name')} />
                  <Field label="Unit"           value={editForm.unit}            onChange={setEdit('unit')} />
                  <Field label="Category"       value={editForm.category}        onChange={setEdit('category')} />
                  <Field label="Min Stock Level" value={editForm.min_stock_level} onChange={setEdit('min_stock_level')} type="number" min="0" />
                  <Field label="Current Stock"  value={editForm.current_stock}   onChange={setEdit('current_stock')}   type="number" min="0" />

                  {saveError && <div className="inv-update-error">{saveError}</div>}

                  <div className="inv-modal-footer" style={{ marginTop: 16 }}>
                    <button className="inv-cancel-btn" onClick={() => { setEditForm(null); setSaveError(''); }}>Cancel</button>
                    <button
                      className={`inv-update-btn${saveSuccess ? ' inv-update-btn-success' : ''}`}
                      onClick={handleSave}
                      disabled={saving}
                    >
                      {saving ? 'Saving…' : saveSuccess ? '✓ Saved' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
};

export default InventoryScreen;
