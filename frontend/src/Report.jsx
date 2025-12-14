import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle,
  Activity,
  Clock,
  AlertTriangle,
  ChevronDown,
} from "lucide-react";
import { motion } from "framer-motion";

// Component to display the final workout report
const Report = () => {
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        // Fetch report data from the backend's dedicated endpoint
        const response = await fetch("http://localhost:5000/report_data");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.error) {
          setError(data.error);
        } else {
          setReport(data);
        }
      } catch (e) {
        console.error("Failed to fetch report data:", e);
        setError(
          "Could not retrieve session report. Please check the backend connection."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, []);

  const calculateAccuracy = (reps, errors) => {
    if (reps === 0) return 100;
    // Heuristic used in AIEngine: 1 error penalizes 20% accuracy
    return Math.max(0, 100 - Math.floor((errors / reps) * 20));
  };

  // --- Helper to render UI elements ---
  const renderStatCard = (title, value, icon, color) => (
    <div
      style={{
        background: "#fff",
        borderRadius: "16px",
        padding: "20px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
        textAlign: "center",
      }}
    >
      <div style={{ color: color, marginBottom: "8px" }}>
        {React.createElement(icon, { size: 28 })}
      </div>
      <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#1A3C34" }}>
        {value}
      </div>
      <div
        style={{
          fontSize: "0.9rem",
          color: "#888",
          fontWeight: "600",
          textTransform: "uppercase",
        }}
      >
        {title}
      </div>
    </div>
  );

  // --- Main Render ---
  if (loading) {
    return (
      <div
        style={{ textAlign: "center", padding: "100px", fontSize: "1.2rem" }}
      >
        Loading report...
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "100px",
          fontSize: "1.2rem",
          color: "#D32F2F",
        }}
      >
        Error: {error}
      </div>
    );
  }

  if (!report || !report.summary) {
    return (
      <div
        style={{
          textAlign: "center",
          padding: "100px",
          fontSize: "1.2rem",
          color: "#888",
        }}
      >
        No session data found.
      </div>
    );
  }

  const right = report.summary.RIGHT;
  const left = report.summary.LEFT;

  const totalReps = right.total_reps + left.total_reps;
  const totalErrors = right.error_count + left.error_count;
  const overallAccuracy = calculateAccuracy(totalReps, totalErrors);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        maxWidth: "900px",
        margin: "0 auto",
        padding: "40px 5%",
        background: "#F9F7F3",
        minHeight: "100vh",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "40px",
        }}
      >
        <button
          onClick={() => navigate("/")}
          style={{
            background: "#fff",
            border: "1px solid #ddd",
            padding: "10px 20px",
            borderRadius: "30px",
            color: "#4A635D",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontWeight: "600",
            transition: "all 0.2s",
          }}
        >
          <ArrowLeft size={18} /> Back to Dashboard
        </button>
      </div>

      {/* Title - CRITICAL FIX: Use the dynamic exercise name */}
      <h1
        style={{
          fontSize: "2.5rem",
          color: "#1A3C34",
          fontWeight: "800",
          marginBottom: "10px",
        }}
      >
        {report.exercise_name || "Workout"} Report
      </h1>
      <p style={{ color: "#4A635D", fontSize: "1.1rem", marginBottom: "30px" }}>
        Detailed breakdown of your performance from the session completed on{" "}
        {new Date().toLocaleDateString()}.
      </p>

      {/* Key Stats Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "20px",
          marginBottom: "40px",
        }}
      >
        {renderStatCard("Total Reps", totalReps, CheckCircle, "#2C5D31")}
        {renderStatCard(
          "Duration",
          formatTime(Math.round(report.duration)),
          Clock,
          "#1E88E5"
        )}
        {renderStatCard(
          "Accuracy",
          `${overallAccuracy}%`,
          Activity,
          overallAccuracy > 75 ? "#2C5D31" : "#EF6C00"
        )}
        {renderStatCard(
          "Form Errors",
          totalErrors,
          AlertTriangle,
          totalErrors > 0 ? "#D32F2F" : "#2C5D31"
        )}
      </div>

      {/* Side-by-Side Summary */}
      <div
        style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px" }}
      >
        {/* Right Side */}
        <div
          style={{
            background: "#fff",
            borderRadius: "20px",
            padding: "30px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
          }}
        >
          <h2
            style={{
              color: "#1A3C34",
              fontWeight: "800",
              fontSize: "1.5rem",
              marginBottom: "20px",
            }}
          >
            Right Side
          </h2>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "15px" }}
          >
            <SummaryRow label="Reps Completed" value={right.total_reps} />
            <SummaryRow label="Min Rep Time" value={`${right.min_time}s`} />
            <SummaryRow
              label="Error Count"
              value={right.error_count}
              color={right.error_count > 0 ? "#D32F2F" : "#2C5D31"}
            />
            <SummaryRow
              label="Side Accuracy"
              value={`${calculateAccuracy(
                right.total_reps,
                right.error_count
              )}%`}
            />
          </div>
        </div>

        {/* Left Side */}
        <div
          style={{
            background: "#fff",
            borderRadius: "20px",
            padding: "30px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
          }}
        >
          <h2
            style={{
              color: "#1A3C34",
              fontWeight: "800",
              fontSize: "1.5rem",
              marginBottom: "20px",
            }}
          >
            Left Side
          </h2>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "15px" }}
          >
            <SummaryRow label="Reps Completed" value={left.total_reps} />
            <SummaryRow label="Min Rep Time" value={`${left.min_time}s`} />
            <SummaryRow
              label="Error Count"
              value={left.error_count}
              color={left.error_count > 0 ? "#D32F2F" : "#2C5D31"}
            />
            <SummaryRow
              label="Side Accuracy"
              value={`${calculateAccuracy(left.total_reps, left.error_count)}%`}
            />
          </div>
        </div>
      </div>

      {/* Calibration Summary */}
      <CalibrationDetail data={report.calibration} />
    </motion.div>
  );
};

// Helper component for summary rows
const SummaryRow = ({ label, value, color }) => (
  <div
    style={{
      display: "flex",
      justifyContent: "space-between",
      padding: "10px 0",
      borderBottom: "1px dashed #eee",
    }}
  >
    <span style={{ color: "#555", fontWeight: "500" }}>{label}</span>
    <span style={{ color: color || "#1A3C34", fontWeight: "700" }}>
      {value}
    </span>
  </div>
);

// Helper component for calibration details
const CalibrationDetail = ({ data }) => {
  const [isOpen, setIsOpen] = useState(false);

  // Determine the tracked joint name (e.g., Elbow, Knee) based on common defaults or external mapping
  // Since we don't have the exercise_config here, we default to the joint relevant to bicep/tricep movement,
  // but the actual angle data (the numbers) are correct from the backend.
  const jointName = "Joint Angle";

  return (
    <div
      style={{
        marginTop: "40px",
        background: "#fff",
        borderRadius: "20px",
        boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          padding: "25px",
          background: "#f8f9fa",
          border: "none",
          textAlign: "left",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: "1.2rem",
          fontWeight: "700",
          color: "#1A3C34",
        }}
      >
        Calibration & Range of Motion Details
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown size={20} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            style={{ padding: "25px", display: "flex", gap: "30px" }}
          >
            <div
              style={{
                flex: 1,
                borderRight: "1px solid #eee",
                paddingRight: "15px",
              }}
            >
              <h3
                style={{
                  fontSize: "1rem",
                  color: "#888",
                  marginBottom: "10px",
                }}
              >
                Calibration Results
              </h3>
              <SummaryRow
                label={`Contracted Threshold (${jointName})`}
                value={`${data.contracted_threshold}°`}
              />
              <SummaryRow
                label={`Extended Threshold (${jointName})`}
                value={`${data.extended_threshold}°`}
              />
            </div>
            <div style={{ flex: 1 }}>
              <h3
                style={{
                  fontSize: "1rem",
                  color: "#888",
                  marginBottom: "10px",
                }}
              >
                Safety Boundaries
              </h3>
              <SummaryRow
                label="Min Safe Angle"
                value={`${data.safe_min}°`}
                color="#2C5D31"
              />
              <SummaryRow
                label="Max Safe Angle"
                value={`${data.safe_max}°`}
                color="#2C5D31"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Report;
