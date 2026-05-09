import React, { useEffect, useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  fetchStoreItems,
  createStoreItem,
  updateStoreItem,
  logStoreTransaction,
  clearError,
} from '../../redux/slices/storeSlice';
import './StoreScreen.css';

// ── Constants ─────────────────────────────────────────────────────────────────
const UNITS = ['kg','g','L','ml','units','bags','cartons','bottles','packs','crates','pieces'];

const TX_CONFIG = {
  used:     { label: 'Use',     icon: '↓', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)'  },
  received: { label: 'Receive', icon: '↑', color: '#22c55e', bg: 'rgba(34,197,94,0.12)'   },
  damaged:  { label: 'Damage',  icon: '✕', color: '#ef4444', bg: 'rgba(239,68,68,0.12)'   },
  adjusted: { label: 'Adjust',  icon: '~', color: '#6366f1', bg: 'rgba(99,102,241,0.12)'  },
};

const getStockStatus = (item) => {
  const cur = Number(item.current_quantity ?? 0);
  const thr = Number(item.low_stock_threshold ?? 0);
  if (cur === 0)       return { label: 'Out of Stock', color: '#ef4444', bg: 'rgba(239,68,68,0.12)',   dot: '#ef4444' };
  if (thr > 0 && cur <= thr) return { label: 'Low Stock',    color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', dot: '#f59e0b' };
  return               { label: 'Good',         color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  dot: '#22c55e' };
};

// ── Sub-components ────────────────────────────────────────────────────────────

const StatusDot = ({ item }) => {
  const s = getStockStatus(item);
  return <span className="ss-dot" style={{ background: s.dot }} />;
};

const StockBadge = ({ item }) => {
  const s = getStockStatus(item);
  return (
    <span className="ss-badge" style={{ color: s.color, background: s.bg }}>
      {s.label}
    </span>
  );
};

// ── Main Component ────────────────────────────────────────────────────────────
const StoreScreen = () => {
  const dispatch   = useDispatch();
  const navigate   = useNavigate();
  const { items, isLoading, isTransacting, error, transactionError } = useSelector(s => s.store);

  // UI state
  const [search,       setSearch]       = useState('');
  const [filter,       setFilter]       = useState('all'); // all | low | out
  const [activeItem,   setActiveItem]   = useState(null);  // item panel
  const [txType,       setTxType]       = useState('used');
  const [txQty,        setTxQty]        = useState('');
  const [txNote,       setTxNote]       = useState('');
  const [txSuccess,    setTxSuccess]    = useState(false);
  const [showForm,     setShowForm]     = useState(false); // add/edit item dialog
  const [editItem,     setEditItem]     = useState(null);
  const [formData,     setFormData]     = useState({ name:'', unit:'units', low_stock_threshold:'', default_usage_quantity:'', note:'' });
  const [formError,    setFormError]    = useState('');

  useEffect(() => { dispatch(fetchStoreItems()); }, [dispatch]);

  // pre-fill tx quantity with default when type = used
  useEffect(() => {
    if (activeItem && txType === 'used') {
      setTxQty(String(activeItem.default_usage_quantity || ''));
    }
  }, [txType, activeItem]);

  const filtered = items.filter(item => {
    const matchSearch = item.name.toLowerCase().includes(search.toLowerCase());
    if (filter === 'low') return matchSearch && item.is_low_stock && item.current_quantity > 0;
    if (filter === 'out') return matchSearch && item.current_quantity === 0;
    return matchSearch;
  });

  const openItem = (item) => {
    setActiveItem(item);
    setTxType('used');
    setTxQty(String(item.default_usage_quantity || ''));
    setTxNote('');
    setTxSuccess(false);
    dispatch(clearError());
  };

  const handleTransact = async () => {
    const qty = parseFloat(txQty);
    if (!qty || qty <= 0) return;
    const result = await dispatch(logStoreTransaction({
      id: activeItem.id,
      transaction_type: txType,
      quantity: qty,
      note: txNote,
    }));
    if (!result.error) {
      setTxSuccess(true);
      setTxQty(String(activeItem.default_usage_quantity || ''));
      setTxNote('');
      // refresh item in panel
      const updated = items.find(i => i.id === activeItem.id);
      if (updated) setActiveItem({ ...updated, current_quantity: result.payload?.transaction?.quantity_after ?? updated.current_quantity });
      setTimeout(() => setTxSuccess(false), 2000);
    }
  };

  const openAdd = () => {
    setEditItem(null);
    setFormData({ name:'', unit:'units', low_stock_threshold:'', default_usage_quantity:'', note:'' });
    setFormError('');
    setShowForm(true);
  };

  const openEdit = (item, e) => {
    e.stopPropagation();
    setEditItem(item);
    setFormData({
      name: item.name,
      unit: item.unit,
      low_stock_threshold: String(item.low_stock_threshold ?? ''),
      default_usage_quantity: String(item.default_usage_quantity ?? ''),
      note: item.note ?? '',
    });
    setFormError('');
    setShowForm(true);
  };

  const handleFormSave = async () => {
    if (!formData.name.trim()) { setFormError('Name is required'); return; }
    const payload = {
      name: formData.name.trim(),
      unit: formData.unit,
      low_stock_threshold: parseFloat(formData.low_stock_threshold) || 0,
      default_usage_quantity: parseFloat(formData.default_usage_quantity) || 0,
      note: formData.note,
    };
    let result;
    if (editItem) {
      result = await dispatch(updateStoreItem({ id: editItem.id, data: payload }));
    } else {
      result = await dispatch(createStoreItem(payload));
    }
    if (!result.error) { setShowForm(false); dispatch(fetchStoreItems()); }
    else setFormError('Save failed. Please try again.');
  };

  const lowCount = items.filter(i => i.is_low_stock && i.current_quantity > 0).length;
  const outCount = items.filter(i => i.current_quantity === 0).length;

  return (
    <div className="ss-root">
      {/* bg grain */}
      <div className="ss-grain" />

      {/* ── HEADER ── */}
      <header className="ss-header">
        <div className="ss-header-left">
          <button className="ss-back" onClick={() => navigate('/im/dashboard')}>← Dashboard</button>
          <div className="ss-header-title-group">
            <h1 className="ss-title">Store</h1>
            <span className="ss-subtitle">{items.length} items tracked</span>
          </div>
        </div>
        <button className="ss-add-btn" onClick={openAdd}>+ New Item</button>
      </header>

      {/* ── FILTER BAR ── */}
      <div className="ss-filter-bar">
        <div className="ss-search-wrap">
          <span className="ss-search-icon">⌕</span>
          <input
            className="ss-search"
            placeholder="Search store items..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="ss-filter-chips">
          {[
            { key: 'all', label: `All  ${items.length}` },
            { key: 'low', label: `Low  ${lowCount}`,  color: '#f59e0b' },
            { key: 'out', label: `Out  ${outCount}`,  color: '#ef4444' },
          ].map(f => (
            <button
              key={f.key}
              className={`ss-chip ${filter === f.key ? 'ss-chip-active' : ''}`}
              style={filter === f.key && f.color ? { borderColor: f.color, color: f.color } : {}}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── BODY ── */}
      <div className={`ss-body ${activeItem ? 'ss-body-split' : ''}`}>

        {/* ── ITEM LIST ── */}
        <div className="ss-list-panel">
          {isLoading ? (
            <div className="ss-skeleton-wrap">
              {[1,2,3,4,5].map(i => <div key={i} className="ss-skeleton" />)}
            </div>
          ) : filtered.length === 0 ? (
            <div className="ss-empty">
              <span className="ss-empty-icon">📭</span>
              <span>No items found</span>
            </div>
          ) : (
            filtered.map(item => {
              const qty = Number(item.current_quantity ?? 0);
              const isActive = activeItem?.id === item.id;
              return (
                <div
                  key={item.id}
                  className={`ss-item-row ${isActive ? 'ss-item-row-active' : ''}`}
                  onClick={() => openItem(item)}
                >
                  <div className="ss-item-left">
                    <StatusDot item={item} />
                    <div className="ss-item-info">
                      <span className="ss-item-name">{item.name}</span>
                      <span className="ss-item-unit">{item.unit}</span>
                    </div>
                  </div>
                  <div className="ss-item-right">
                    <span className="ss-item-qty">{qty}</span>
                    <StockBadge item={item} />
                    <button className="ss-edit-btn" onClick={e => openEdit(item, e)}>✎</button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ── ITEM DETAIL PANEL ── */}
        {activeItem && (
          <div className="ss-detail-panel">
            <button className="ss-close-panel" onClick={() => setActiveItem(null)}>✕</button>

            {/* Item header */}
            <div className="ss-detail-header">
              <div>
                <h2 className="ss-detail-name">{activeItem.name}</h2>
                <div className="ss-detail-meta">
                  <StockBadge item={activeItem} />
                  <span className="ss-detail-unit">{activeItem.unit}</span>
                </div>
              </div>
              <div className="ss-detail-qty-block">
                <span className="ss-detail-qty-num">{Number(activeItem.current_quantity ?? 0)}</span>
                <span className="ss-detail-qty-label">in stock</span>
              </div>
            </div>

            {/* Info row */}
            <div className="ss-detail-info-row">
              <div className="ss-detail-info-card">
                <span className="ss-detail-info-label">Low stock at</span>
                <span className="ss-detail-info-val">{activeItem.low_stock_threshold} {activeItem.unit}</span>
              </div>
              <div className="ss-detail-info-card">
                <span className="ss-detail-info-label">Default usage</span>
                <span className="ss-detail-info-val">{activeItem.default_usage_quantity || '—'} {activeItem.default_usage_quantity ? activeItem.unit : ''}</span>
              </div>
            </div>

            {/* Transaction type selector */}
            <div className="ss-tx-type-row">
              {Object.entries(TX_CONFIG).map(([key, cfg]) => (
                <button
                  key={key}
                  className={`ss-tx-type-btn ${txType === key ? 'ss-tx-type-active' : ''}`}
                  style={txType === key ? { borderColor: cfg.color, color: cfg.color, background: cfg.bg } : {}}
                  onClick={() => {
                    setTxType(key);
                    if (key === 'used') setTxQty(String(activeItem.default_usage_quantity || ''));
                    else setTxQty('');
                  }}
                >
                  <span className="ss-tx-type-icon">{cfg.icon}</span>
                  {cfg.label}
                </button>
              ))}
            </div>

            {/* Quantity input */}
            <div className="ss-qty-row">
              <div className="ss-qty-input-wrap">
                <button
                  className="ss-qty-stepper"
                  onClick={() => setTxQty(v => String(Math.max(0, (parseFloat(v) || 0) - (activeItem.default_usage_quantity || 1))))}
                >−</button>
                <input
                  className="ss-qty-input"
                  type="number"
                  min="0"
                  step="any"
                  value={txQty}
                  onChange={e => setTxQty(e.target.value)}
                  placeholder="0"
                />
                <span className="ss-qty-unit">{activeItem.unit}</span>
                {txType !== 'adjusted' && (
                  <button
                    className="ss-qty-stepper"
                    onClick={() => setTxQty(v => String((parseFloat(v) || 0) + (activeItem.default_usage_quantity || 1)))}
                  >+</button>
                )}
              </div>
            </div>

            {/* Note input */}
            <input
              className="ss-note-input"
              placeholder="Note (optional)..."
              value={txNote}
              onChange={e => setTxNote(e.target.value)}
            />

            {/* Errors */}
            {transactionError && <div className="ss-tx-error">{String(transactionError)}</div>}

            {/* Submit */}
            <button
              className={`ss-tx-submit ${txSuccess ? 'ss-tx-success' : ''}`}
              style={!txSuccess ? { background: TX_CONFIG[txType].color } : {}}
              onClick={handleTransact}
              disabled={isTransacting || !txQty || parseFloat(txQty) <= 0}
            >
              {isTransacting ? '...' : txSuccess ? '✓ Done!' : `${TX_CONFIG[txType].icon} ${TX_CONFIG[txType].label} ${txQty || '0'} ${activeItem.unit}`}
            </button>

            {/* Recent transactions */}
            {activeItem.transactions?.length > 0 && (
              <div className="ss-tx-history">
                <h4 className="ss-tx-history-title">Recent</h4>
                {activeItem.transactions.slice(0, 6).map(tx => {
                  const cfg = TX_CONFIG[tx.transaction_type] || TX_CONFIG.adjusted;
                  return (
                    <div key={tx.id} className="ss-tx-hist-row">
                      <span className="ss-tx-hist-icon" style={{ color: cfg.color }}>{cfg.icon}</span>
                      <span className="ss-tx-hist-label">{tx.note || cfg.label}</span>
                      <span className="ss-tx-hist-qty" style={{ color: cfg.color }}>
                        {tx.quantity} {activeItem.unit}
                      </span>
                      <span className="ss-tx-hist-time">
                        {new Date(tx.created_at).toLocaleDateString('en-US', { month:'short', day:'numeric' })}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── ADD/EDIT DIALOG ── */}
      {showForm && (
        <div className="ss-overlay" onClick={() => setShowForm(false)}>
          <div className="ss-dialog" onClick={e => e.stopPropagation()}>
            <div className="ss-dialog-header">
              <h3 className="ss-dialog-title">{editItem ? 'Edit Item' : 'New Store Item'}</h3>
              <button className="ss-dialog-close" onClick={() => setShowForm(false)}>✕</button>
            </div>

            {formError && <div className="ss-form-error">{formError}</div>}

            <div className="ss-form-group">
              <label className="ss-label">Item Name</label>
              <input
                className="ss-input"
                placeholder="e.g. Raw Chicken"
                value={formData.name}
                onChange={e => setFormData(p => ({ ...p, name: e.target.value }))}
              />
            </div>

            <div className="ss-form-row">
              <div className="ss-form-group">
                <label className="ss-label">Unit</label>
                <select
                  className="ss-input ss-select"
                  value={formData.unit}
                  onChange={e => setFormData(p => ({ ...p, unit: e.target.value }))}
                >
                  {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <div className="ss-form-group">
                <label className="ss-label">Low Stock Threshold</label>
                <input
                  className="ss-input"
                  type="number"
                  min="0"
                  placeholder="e.g. 5"
                  value={formData.low_stock_threshold}
                  onChange={e => setFormData(p => ({ ...p, low_stock_threshold: e.target.value }))}
                />
              </div>
            </div>

            <div className="ss-form-group">
              <label className="ss-label">Default Usage Quantity
                <span className="ss-label-hint"> — pre-fills the "Use" button</span>
              </label>
              <input
                className="ss-input"
                type="number"
                min="0"
                placeholder={`e.g. 2 ${formData.unit}`}
                value={formData.default_usage_quantity}
                onChange={e => setFormData(p => ({ ...p, default_usage_quantity: e.target.value }))}
              />
            </div>

            <div className="ss-form-group">
              <label className="ss-label">Note (optional)</label>
              <input
                className="ss-input"
                placeholder="Any notes about this item..."
                value={formData.note}
                onChange={e => setFormData(p => ({ ...p, note: e.target.value }))}
              />
            </div>

            <div className="ss-dialog-actions">
              <button className="ss-btn-cancel" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="ss-btn-save" onClick={handleFormSave}>
                {editItem ? 'Save Changes' : 'Add Item'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StoreScreen;
