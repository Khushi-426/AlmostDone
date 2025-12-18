import React, { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const TherapistPatientMonitoring = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  // 🔹 NEW: floating pill visibility
  const [showBack, setShowBack] = useState(true);

  useEffect(() => {
    fetchPatients();

    // 🔹 NEW: hide/show floating pill on scroll
    let lastScrollY = window.scrollY;

    const handleScroll = () => {
      if (window.scrollY > lastScrollY && window.scrollY > 80) {
        setShowBack(false);
      } else {
        setShowBack(true);
      }
      lastScrollY = window.scrollY;
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const fetchPatients = async () => {
    const res = await axios.get("http://localhost:5001/api/therapist/patients");
    setPatients(res.data.patients || []);
    setLoading(false);
  };

  const filteredPatients = patients.filter((p) => {
    const matchesSearch = p.name
      .toLowerCase()
      .includes(search.toLowerCase());
    const matchesFilter =
      filter === "All" ? true : p.status === filter;
    return matchesSearch && matchesFilter;
  });

  const getStatus = (status) =>
    status === "High Risk"
      ? { bg: "#ffecec", color: "#e53935", label: "High Risk" }
      : { bg: "#eaffea", color: "#2e7d32", label: "Normal" };

  const getTrend = (status) =>
    status === "High Risk"
      ? { text: "↓ Declining", color: "#e53935", pulse: true }
      : { text: "↑ Improving", color: "#2e7d32", pulse: false };

  if (loading) return <div style={styles.center}>Loading…</div>;

  return (
    <div style={styles.container}>
      {/* FLOATING NAVIGATION PILL */}
      <div
        style={{
          ...styles.floatingBack,
          transform: showBack ? "translateY(0)" : "translateY(-120%)",
          opacity: showBack ? 1 : 0,
        }}
        onClick={() => navigate("/therapist-dashboard")}
      >
        <span style={styles.backIcon}>←</span>
        <span style={styles.backText}>Dashboard</span>
      </div>

      <h1 style={styles.title}>
        Patient Monitoring Overview ({filteredPatients.length} Active)
      </h1>

      {/* SEARCH + FILTER BAR */}
      <div style={styles.controls}>
        <input
          placeholder="Search patients…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.search}
        />

        <div style={styles.filters}>
          {["All", "Normal", "High Risk"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                ...styles.filterBtn,
                ...(filter === f ? styles.filterActive : {}),
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* TABLE */}
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th>Patient Name</th>
              <th>Status</th>
              <th>Compliance</th>
              <th>Trend</th>
              <th>Last Session</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {filteredPatients.map((p, i) => {
              const status = getStatus(p.status);
              const trend = getTrend(p.status);

              return (
                <tr
                  key={p.email}
                  className="row"
                  style={{
                    background: p.status === "High Risk" ? "#fff5f5" : "#fff",
                    animation: `fadeIn 0.3s ease ${i * 0.03}s both`,
                  }}
                >
                  <td style={styles.name}>{p.name}</td>

                  <td>
                    <span
                      style={{
                        ...styles.badge,
                        background: status.bg,
                        color: status.color,
                      }}
                    >
                      {status.label}
                    </span>
                  </td>

                  <td>
                    <div style={styles.progressBg}>
                      <div
                        style={{
                          ...styles.progressFill,
                          width: `${p.compliance || 0}%`,
                        }}
                      />
                    </div>
                    <span style={styles.percent}>{p.compliance || 0}%</span>
                  </td>

                  <td
                    style={{
                      color: trend.color,
                      fontWeight: 600,
                      animation: trend.pulse ? "pulse 1.5s infinite" : "none",
                    }}
                  >
                    {trend.text}
                  </td>

                  <td>{p.last_session || "—"}</td>

                  <td>
                    <button
                      style={styles.actionBtn}
                      onClick={() =>
                        navigate(`/therapist/patient-detail/${p.email}`)
                      }
                    >
                      View Report
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ANIMATIONS */}
      <style>{`
        thead th {
          position: sticky;
          top: 0;
          background: #f8fafc;
          z-index: 5;
        }

        tr.row {
          transition: all 0.25s ease;
        }

        tr.row:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 28px rgba(0,0,0,0.12);
          background: #f9fbff;
        }

        button:hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 18px rgba(30,136,229,0.35);
        }

        button:active {
          transform: scale(0.95);
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to { opacity: 1; transform: translateY(0); }
        }

        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.6; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

/* STYLES */
const styles = {
  container: {
    height: "100vh",
    padding: "20px 24px",
    paddingTop: "96px", // space reserved for floating pill
    background: "linear-gradient(180deg,#f8fafc,#eef2f7)",
    fontFamily: "Inter, sans-serif",
    position: "relative",
  },

  /* FLOATING NAV PILL */
  floatingBack: {
    position: "fixed",
    top: "20px",
    left: "20px",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "10px 16px",
    borderRadius: "999px",
    background: "rgba(255,255,255,0.75)",
    backdropFilter: "blur(12px)",
    border: "1px solid rgba(30,136,229,0.25)",
    color: "#1e88e5",
    fontWeight: 600,
    cursor: "pointer",
    boxShadow: "0 12px 30px rgba(0,0,0,0.12)",
    transition: "all 0.35s ease",
    zIndex: 50,
  },
  backIcon: {
    fontSize: "18px",
    lineHeight: 1,
  },
  backText: {
    fontSize: "14px",
  },

  title: {
    fontSize: "26px",
    fontWeight: 700,
    marginBottom: "16px",
  },
  controls: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "12px",
    gap: "12px",
  },
  search: {
    padding: "10px 14px",
    width: "280px",
    borderRadius: "8px",
    border: "1px solid #d1d5db",
  },
  filters: {
    display: "flex",
    gap: "8px",
  },
  filterBtn: {
    padding: "8px 14px",
    borderRadius: "20px",
    border: "1px solid #d1d5db",
    background: "#fff",
    cursor: "pointer",
  },
  filterActive: {
    background: "#1e88e5",
    color: "#fff",
    borderColor: "#1e88e5",
  },
  tableWrapper: {
    height: "calc(100vh - 200px)",
    background: "#fff",
    borderRadius: "10px",
    boxShadow: "0 10px 30px rgba(0,0,0,0.08)",
    overflow: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  name: {
    fontWeight: 600,
    color: "#0b3c91",
  },
  badge: {
    padding: "6px 14px",
    borderRadius: "20px",
    fontSize: "13px",
    fontWeight: 600,
  },
  progressBg: {
    width: "110px",
    height: "8px",
    background: "#e5e7eb",
    borderRadius: "6px",
    display: "inline-block",
    marginRight: "8px",
  },
  progressFill: {
    height: "100%",
    background: "#3b82f6",
    borderRadius: "6px",
    transition: "width 0.6s ease",
  },
  percent: {
    fontSize: "13px",
    fontWeight: 600,
  },
  actionBtn: {
    background: "#1e88e5",
    color: "#fff",
    border: "none",
    padding: "8px 14px",
    borderRadius: "8px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  center: {
    height: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
};

export default TherapistPatientMonitoring;
