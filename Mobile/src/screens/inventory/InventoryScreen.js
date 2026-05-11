import React, { useEffect, useState, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { fetchInventory, updateInventoryItem } from '../../redux/slices/inventorySlice';
import './Inventory.css';

const getStockStatus = (item) => {
  const current = Number(item.current_stock ?? item.quantityInStock ?? 0);
  const minimum = Number(item.min_stock_level ?? item.lowStockThreshold ?? 1);
  const pct = minimum > 0 ? (current / minimum) * 100 : 100;
  if (pct <= 25) return { label: 'Low',    color: '#ef4444', dot: '#ef4444' };
  if (pct <= 75) return { label: 'Medium', color: '#f59e0b', dot: '#f59e0b' };
  return              { label: 'Good',   color: '#22c55e', dot: '#22c55e' };
};

const InventoryScreen = () => {
  const dispatch  = useDispatch();
  const navigate  = useNavigate();
  const { items, isLoading, error } = useSelector((state) => state.inventory);

  const [search,      setSearch]      = useState('');
  const [filter,      setFilter]      = useState('all');
  const [selected,    setSelected]    = useState(null);
  const [newStock,    setNewStock]    = useState('');
  const [saving,      setSaving]      = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError,   setSaveError]   = useState('');

  useEffect(() => { dispatch(fetchInventory()); }, [dispatch]);

  // Reset detail state when item changes
  useEffect(() => {
    if (selected) {
      setNewStock(String(selected.current_stock ?? selected.quantityInStock ?? 0));
      setSaveSuccess(false);
      setSaveError('');
    }
  }, [selected]);

  const filtered = useMemo(() => {
    return items.filter((item) => {
      const name = (item.name || '').toLowerCase();
      if (search && !name.includes(search.toLowerCase())) return false;
      if (filter === 'low') {
        const st = getStockStatus(item);
        return st.label === 'Low';
      }
      return true;
    });
  }, [items, search, filter]);

  const lowCount = useMemo(() =>
    items.filter(i => getStockStatus(i).label === 'Low').length, [items]);

  const handleSelect = (item) => {
    setSelected(prev => prev?.id === item.id ? null : item);
  };

  const handleStepStock = (delta) => {
    setNewStock(prev => {
      const val = parseFloat(prev) || 0;
      return String(Math.max(0, val + delta));
    });
  };

  const handleSave = async () => {
    const stockValue = parseFloat(newStock);
    if (isNaN(stockValue) || stockValue < 0) {
      setSaveError('Please enter a valid stock value.');
      return;
    }
    setSaving(true);
    setSaveError('');
    try {
      await dispatch(updateInventoryItem({
        itemId: selected.id ?? selected.inventoryItemId,
        data: { current_stock: stockValue, quantityInStock: stockValue },
      })).unwrap();
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      // Refresh the selected item from updated store
      dispatch(fetchInventory());
    } catch (e) {
      setSaveError('Failed to update stock. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const isBodySplit = !!selected;

  return (
    <div className="inv-root">
      <div className="inv-grain" />

      {/* ── HEADER ── */}
      <header className="inv-header">
        <div className="inv-header-left">
          <button className="inv-back" onClick={() => navigate('/im/dashboard')}>
            ← Dashboard
          </button>
          <div className="inv-header-title-group">
            <h1 className="inv-title">Inventory</h1>
            <span className="inv-subtitle">
              {isLoading ? 'Loading…' : `${items.length} items tracked`}
              {lowCount > 0 && ` · ${lowCount} low`}
            </span>
          </div>
        </div>
      </header>

      {/* ── FILTER BAR ── */}
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

      {/* ── BODY ── */}
      <div className={`inv-body${isBodySplit ? ' inv-body-split' : ''}`}>

        {/* List */}
        <div className="inv-list-panel">
          {error && (
            <div className="inv-update-error" style={{ marginBottom: 16 }}>
              {String(error)}
            </div>
          )}

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
                      <span className="inv-item-unit">
                        Min: {Number(item.min_stock_level ?? item.lowStockThreshold ?? 0)} {item.unit}
                      </span>
                    </div>
                  </div>
                  <div className="inv-item-right">
                    <span className="inv-item-qty">{current}</span>
                    <span
                      className="inv-badge"
                      style={{ background: st.color + '22', color: st.color }}
                    >
                      {st.label}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Detail / Update Panel */}
        {selected && (() => {
          const st      = getStockStatus(selected);
          const current = Number(selected.current_stock ?? selected.quantityInStock ?? 0);
          const minimum = Number(selected.min_stock_level ?? selected.lowStockThreshold ?? 0);
          return (
            <div className="inv-detail-panel">
              <button className="inv-close-panel" onClick={() => setSelected(null)}>✕</button>

              <div className="inv-detail-header">
                <div>
                  <h2 className="inv-detail-name">{selected.name}</h2>
                  <div className="inv-detail-meta">
                    <span
                      className="inv-badge"
                      style={{ background: st.color + '22', color: st.color }}
                    >
                      {st.label} Stock
                    </span>
                    <span className="inv-detail-unit">{selected.unit}</span>
                  </div>
                </div>
                <div className="inv-detail-qty-block">
                  <span className="inv-detail-qty-num">{current}</span>
                  <span className="inv-detail-qty-label">{selected.unit} in stock</span>
                </div>
              </div>

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

              {/* Update stock */}
              <div className="inv-update-section">
                <p className="inv-update-title">Update Stock Level</p>
                <div className="inv-qty-input-wrap">
                  <button className="inv-qty-stepper" onClick={() => handleStepStock(-1)}>−</button>
                  <input
                    className="inv-qty-input"
                    type="number"
                    value={newStock}
                    onChange={e => setNewStock(e.target.value)}
                    min="0"
                  />
                  <span className="inv-qty-unit">{selected.unit}</span>
                  <button className="inv-qty-stepper" onClick={() => handleStepStock(1)}>+</button>
                </div>

                {saveError && <div className="inv-update-error">{saveError}</div>}

                <button
                  className={`inv-update-btn${saveSuccess ? ' inv-update-btn-success' : ''}`}
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? 'Saving…' : saveSuccess ? '✓ Saved' : 'Save Stock Level'}
                </button>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
};

export default InventoryScreen;
