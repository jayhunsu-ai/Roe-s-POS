import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { logout } from '../../redux/slices/authSlice';
import apiClient from '../../api/axiosClient';
import './IMDashboard.css';

const IMDashboardScreen = () => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);

  const [stats, setStats] = useState({
    totalInventoryItems: 0,
    lowInventoryItems: 0,
    totalStoreItems: 0,
    lowStoreItems: 0,
    recentTransactions: [],
  });
  const [loading, setLoading] = useState(true);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [invRes, storeRes, storeTxRes] = await Promise.allSettled([
          apiClient.get('/inventory/items/?active_only=true'),
          apiClient.get('/store/items/?active_only=true'),
          apiClient.get('/store/transactions/?limit=5'),
        ]);

        const invItems = invRes.status === 'fulfilled'
          ? (invRes.value.data?.results || invRes.value.data || []) : [];
        const storeItems = storeRes.status === 'fulfilled'
          ? (storeRes.value.data?.results || storeRes.value.data || []) : [];
        const storeTx = storeTxRes.status === 'fulfilled'
          ? (storeTxRes.value.data?.results || storeTxRes.value.data || []) : [];

        setStats({
          totalInventoryItems: invItems.length,
          lowInventoryItems: invItems.filter(i => i.isLowStock || i.is_low_stock).length,
          totalStoreItems: storeItems.length,
          lowStoreItems: storeItems.filter(i => i.is_low_stock).length,
          recentTransactions: storeTx.slice(0, 5),
        });
      } catch (e) {
        console.error('Dashboard fetch error', e);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
  };

  const greeting = () => {
    const h = time.getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const formatTime = (d) =>
    d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const formatDate = (d) =>
    d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  const txTypeConfig = {
    received: { label: 'Received', color: '#22c55e', icon: '↑' },
    used:     { label: 'Used',     color: '#f59e0b', icon: '↓' },
    damaged:  { label: 'Damaged',  color: '#ef4444', icon: '✕' },
    adjusted: { label: 'Adjusted', color: '#6366f1', icon: '~' },
  };

  return (
    <div className="im-root">
      {/* Ambient background orbs */}
      <div className="im-orb im-orb-1" />
      <div className="im-orb im-orb-2" />
      <div className="im-orb im-orb-3" />

      {/* ── HEADER ── */}
      <header className="im-header">
        <div className="im-header-left">
          <div className="im-logo">
            <span className="im-logo-icon">🍽</span>
            <span className="im-logo-text">Roe's POS</span>
            <span className="im-logo-badge">IM</span>
          </div>
        </div>
        <div className="im-header-right">
          <div className="im-time-block">
            <span className="im-time">{formatTime(time)}</span>
            <span className="im-date">{formatDate(time)}</span>
          </div>
          <div className="im-user-chip">
            <div className="im-avatar">{user?.staffName?.charAt(0) || 'I'}</div>
            <div className="im-user-info">
              <span className="im-user-name">{user?.staffName || 'Manager'}</span>
              <span className="im-user-role">Inventory Manager</span>
            </div>
          </div>
          <button className="im-logout-btn" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      {/* ── MAIN ── */}
      <main className="im-main">

        {/* Greeting */}
        <div className="im-greeting-row">
          <div>
            <h1 className="im-greeting">{greeting()}, {user?.staffName?.split(' ')[0] || 'Manager'} 👋</h1>
            <p className="im-subgreeting">Here's what's happening in the store today.</p>
          </div>
        </div>

        {/* ── STAT CARDS ── */}
        <div className="im-stat-grid">
          <div className="im-stat-card im-stat-inv">
            <div className="im-stat-icon">📦</div>
            <div className="im-stat-body">
              <span className="im-stat-number">{loading ? '—' : stats.totalInventoryItems}</span>
              <span className="im-stat-label">Inventory Items</span>
            </div>
            {stats.lowInventoryItems > 0 && (
              <div className="im-stat-alert">
                ⚠ {stats.lowInventoryItems} low
              </div>
            )}
          </div>

          <div className="im-stat-card im-stat-store">
            <div className="im-stat-icon">🏪</div>
            <div className="im-stat-body">
              <span className="im-stat-number">{loading ? '—' : stats.totalStoreItems}</span>
              <span className="im-stat-label">Store Items</span>
            </div>
            {stats.lowStoreItems > 0 && (
              <div className="im-stat-alert">
                ⚠ {stats.lowStoreItems} low
              </div>
            )}
          </div>

          <div className="im-stat-card im-stat-tx">
            <div className="im-stat-icon">📋</div>
            <div className="im-stat-body">
              <span className="im-stat-number">{loading ? '—' : stats.recentTransactions.length}</span>
              <span className="im-stat-label">Recent Movements</span>
            </div>
          </div>
        </div>

        {/* ── NAV CARDS ── */}
        <div className="im-nav-grid">
          <button className="im-nav-card im-nav-inventory" onClick={() => navigate('/inventory')}>
            <div className="im-nav-card-inner">
              <div className="im-nav-icon-wrap">
                <span className="im-nav-icon">📦</span>
              </div>
              <div className="im-nav-content">
                <h2 className="im-nav-title">Inventory</h2>
                <p className="im-nav-desc">
                  Manage prepped food stock — track portions, units ready for service.
                </p>
                <div className="im-nav-meta">
                  {loading ? '...' : `${stats.totalInventoryItems} items tracked`}
                  {stats.lowInventoryItems > 0 && (
                    <span className="im-nav-warning"> · {stats.lowInventoryItems} need attention</span>
                  )}
                </div>
              </div>
              <span className="im-nav-arrow">→</span>
            </div>
            <div className="im-nav-shimmer" />
          </button>

          <button className="im-nav-card im-nav-store" onClick={() => navigate('/store')}>
            <div className="im-nav-card-inner">
              <div className="im-nav-icon-wrap">
                <span className="im-nav-icon">🏪</span>
              </div>
              <div className="im-nav-content">
                <h2 className="im-nav-title">Store</h2>
                <p className="im-nav-desc">
                  Raw ingredients & supplies — log usage, receive stock, record damage.
                </p>
                <div className="im-nav-meta">
                  {loading ? '...' : `${stats.totalStoreItems} items tracked`}
                  {stats.lowStoreItems > 0 && (
                    <span className="im-nav-warning"> · {stats.lowStoreItems} need attention</span>
                  )}
                </div>
              </div>
              <span className="im-nav-arrow">→</span>
            </div>
            <div className="im-nav-shimmer" />
          </button>
        </div>

        {/* ── RECENT TRANSACTIONS ── */}
        <div className="im-recent">
          <div className="im-section-header">
            <h3 className="im-section-title">Recent Store Movements</h3>
            <button className="im-section-link" onClick={() => navigate('/store')}>
              View all →
            </button>
          </div>

          {loading ? (
            <div className="im-skeleton-list">
              {[1,2,3].map(i => <div key={i} className="im-skeleton-row" />)}
            </div>
          ) : stats.recentTransactions.length === 0 ? (
            <div className="im-empty">
              <span className="im-empty-icon">📭</span>
              <span>No store movements yet.</span>
            </div>
          ) : (
            <div className="im-tx-list">
              {stats.recentTransactions.map((tx) => {
                const cfg = txTypeConfig[tx.transaction_type] || { label: tx.transaction_type, color: '#888', icon: '·' };
                return (
                  <div key={tx.id} className="im-tx-row">
                    <div className="im-tx-icon-wrap" style={{ background: cfg.color + '22', color: cfg.color }}>
                      {cfg.icon}
                    </div>
                    <div className="im-tx-info">
                      <span className="im-tx-name">{tx.item_name}</span>
                      <span className="im-tx-note">{tx.note || cfg.label}</span>
                    </div>
                    <div className="im-tx-right">
                      <span className="im-tx-qty" style={{ color: cfg.color }}>
                        {cfg.icon} {tx.quantity} {tx.item_unit}
                      </span>
                      <span className="im-tx-time">
                        {new Date(tx.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default IMDashboardScreen;
