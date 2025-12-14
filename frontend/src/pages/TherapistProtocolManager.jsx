import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const TherapistProtocolManager = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('create'); 

  // --- REAL STATE (No more Mocks) ---
  const [exercises, setExercises] = useState([]);
  const [patients, setPatients] = useState([]);
  const [protocols, setProtocols] = useState([]);
  const [loading, setLoading] = useState(true);

  // --- FORM STATE ---
  const [protocolName, setProtocolName] = useState('');
  const [selectedExercises, setSelectedExercises] = useState([]);
  const [selectedPatients, setSelectedPatients] = useState([]);
  const [step, setStep] = useState(1); // 1 = Define, 2 = Assign

  // --- 1. FETCH INITIAL DATA FROM DB ---
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [exRes, patRes, protRes] = await Promise.all([
          axios.get('http://localhost:5001/api/therapist/exercises'),
          axios.get('http://localhost:5001/api/therapist/patients'),
          axios.get('http://localhost:5001/api/therapist/protocols')
        ]);

        setExercises(exRes.data);
        setPatients(patRes.data.patients || patRes.data); // Handle different response structures
        setProtocols(protRes.data);
        setLoading(false);
      } catch (err) {
        console.error("Error fetching data:", err);
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // --- HANDLERS ---

  const handleAddExerciseToProtocol = (exercise) => {
    // Add exercise with default values
    setSelectedExercises([
      ...selectedExercises, 
      { 
        id: exercise.id, // Keep ID for backend reference
        name: exercise.name, 
        sets: 3, 
        reps: 10 
      }
    ]);
  };

  const handleUpdateExerciseDetail = (index, field, value) => {
    const updated = [...selectedExercises];
    updated[index][field] = value;
    setSelectedExercises(updated);
  };

  const handleTogglePatient = (email) => {
    if (selectedPatients.includes(email)) {
      setSelectedPatients(selectedPatients.filter(e => e !== email));
    } else {
      setSelectedPatients([...selectedPatients, email]);
    }
  };

  const handleSubmitProtocol = async () => {
    if (!protocolName || selectedExercises.length === 0 || selectedPatients.length === 0) {
      alert("Please complete all fields (Name, Exercises, and Patients)");
      return;
    }

    try {
      const payload = {
        name: protocolName,
        exercises: selectedExercises,
        assigned_patients: selectedPatients
      };

      // POST to backend
      await axios.post('http://localhost:5001/api/therapist/protocols', payload);
      
      alert("✅ Protocol Created & Assigned Successfully!");
      
      // Reset Form
      setStep(1);
      setProtocolName('');
      setSelectedExercises([]);
      setSelectedPatients([]);
      
      // Refresh Protocol List
      const res = await axios.get('http://localhost:5001/api/therapist/protocols');
      setProtocols(res.data);

    } catch (err) {
      console.error(err);
      alert("Failed to save protocol.");
    }
  };

  if (loading) return <div className="p-10 text-center">Loading Library & Patients...</div>;

  return (
    <div style={styles.container}>
      <button onClick={() => navigate('/therapist-dashboard')} style={styles.backLink}>
         ← Back to Dashboard
      </button>
      
      <h1 style={styles.header}>Protocol Manager</h1>

      {/* TABS */}
      <div style={styles.tabContainer}>
        <button 
          onClick={() => setActiveTab('create')} 
          style={{...styles.tabButton, ...(activeTab === 'create' ? styles.activeTab : {})}}
        >
          Create New Protocol
        </button>
        <button 
          onClick={() => setActiveTab('view')} 
          style={{...styles.tabButton, ...(activeTab === 'view' ? styles.activeTab : {})}}
        >
          View Active Protocols
        </button>
      </div>

      <div style={styles.content}>
        
        {/* --- VIEW 1: CREATE PROTOCOL --- */}
        {activeTab === 'create' && (
          <div>
            {step === 1 ? (
              // STEP 1: DEFINE EXERCISES
              <div>
                <h2 style={styles.sectionHeader}>Step 1: Define Protocol</h2>
                <input 
                  type="text" 
                  placeholder="Protocol Name (e.g. ACL Rehab Phase 1)" 
                  value={protocolName}
                  onChange={(e) => setProtocolName(e.target.value)}
                  style={styles.inputField}
                />

                {/* Selected Exercises List */}
                <h3 style={{marginTop:'20px'}}>Selected Exercises ({selectedExercises.length})</h3>
                {selectedExercises.length === 0 && <p style={{color:'#888', fontStyle:'italic'}}>No exercises added yet. Click from library below.</p>}
                
                {selectedExercises.map((ex, idx) => (
                  <div key={idx} style={styles.selectedExerciseCard}>
                    <strong>{ex.name}</strong>
                    <div>
                      <label style={{fontSize:'0.8rem', marginRight:'5px'}}>Sets:</label>
                      <input 
                        type="number" 
                        value={ex.sets} 
                        onChange={(e) => handleUpdateExerciseDetail(idx, 'sets', e.target.value)}
                        style={styles.smallInputField} 
                      />
                      <label style={{fontSize:'0.8rem', margin:'0 5px'}}>Reps:</label>
                      <input 
                        type="number" 
                        value={ex.reps} 
                        onChange={(e) => handleUpdateExerciseDetail(idx, 'reps', e.target.value)}
                        style={styles.smallInputField} 
                      />
                    </div>
                  </div>
                ))}

                <button 
                  onClick={() => selectedExercises.length > 0 && setStep(2)}
                  disabled={selectedExercises.length === 0}
                  style={selectedExercises.length > 0 ? styles.createButton : styles.disabledButton}
                >
                  Next: Assign Patients →
                </button>

                {/* Exercise Library Picker */}
                <div style={{marginTop: '40px', borderTop:'1px solid #eee', paddingTop:'20px'}}>
                  <h3 style={{marginBottom:'15px', color:'#555'}}>Exercise Library (Click to Add)</h3>
                  <div style={styles.exercisePickerGrid}>
                    {exercises.map(ex => (
                      <div key={ex.id} style={styles.pickerCard}>
                        <div style={{fontWeight:'bold', color:'#2c3e50'}}>{ex.name}</div>
                        <div style={{fontSize:'0.8rem', color:'#7f8c8d'}}>{ex.difficulty}</div>
                        <button onClick={() => handleAddExerciseToProtocol(ex)} style={styles.addButton}>
                          + Add
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              // STEP 2: ASSIGN PATIENTS
              <div style={styles.stepContainer}>
                <h2 style={styles.sectionHeader}>Step 2: Assign to Patients</h2>
                <p>Who should receive the <strong>"{protocolName}"</strong> protocol?</p>
                
                <div style={styles.patientListContainer}>
                  {patients.map(p => (
                    <div key={p.id} style={styles.patientSelectCard}>
                      <input 
                        type="checkbox" 
                        checked={selectedPatients.includes(p.email)}
                        onChange={() => handleTogglePatient(p.email)}
                        id={`p-${p.id}`}
                        style={{transform: 'scale(1.2)', marginRight:'10px'}}
                      />
                      <label htmlFor={`p-${p.id}`} style={{cursor:'pointer', width:'100%'}}>
                        <span style={{fontWeight:'bold'}}>{p.name}</span>
                        <span style={{color:'#888', marginLeft:'10px'}}>({p.email})</span>
                      </label>
                    </div>
                  ))}
                </div>

                <div style={{display:'flex', justifyContent:'space-between', marginTop:'20px'}}>
                  <button onClick={() => setStep(1)} style={styles.backButton}>← Back</button>
                  <button onClick={handleSubmitProtocol} style={styles.assignButton}>
                    Confirm & Assign Protocol
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* --- VIEW 2: ACTIVE PROTOCOLS --- */}
        {activeTab === 'view' && (
          <div>
            <h2 style={styles.sectionHeader}>Active Protocols</h2>
            {protocols.length === 0 ? (
              <p style={{color:'#888'}}>No protocols created yet.</p>
            ) : (
              <div style={{display:'grid', gap:'15px'}}>
                {protocols.map(p => (
                  <div key={p.id} style={styles.protocolCard}>
                    <h3 style={{margin:'0 0 5px 0', color:'#0050b3'}}>{p.name}</h3>
                    <div style={{fontSize:'0.9rem', color:'#555'}}>
                      <p><strong>Exercises:</strong> {p.exercises?.length || 0}</p>
                      <p><strong>Assigned Patients:</strong> {p.assigned_patients?.length || 0}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// --- STYLES ---
const styles = {
  container: { padding: '30px', backgroundColor: '#f0f2f5', minHeight: '100vh', fontFamily: 'Inter, sans-serif' },
  backLink: { background: 'none', border: 'none', color: '#1890ff', cursor: 'pointer', marginBottom: '15px', padding: 0, textDecoration: 'underline' },
  header: { color: '#0050b3', borderBottom: '2px solid #e8e8e8', paddingBottom: '15px', marginBottom: '20px' },
  tabContainer: { display: 'flex', marginBottom: '20px' },
  tabButton: { padding: '12px 25px', border: 'none', backgroundColor: '#e6f7ff', cursor: 'pointer', fontSize: '1rem', marginRight:'5px', borderRadius:'8px 8px 0 0' },
  activeTab: { backgroundColor: 'white', fontWeight: 'bold', borderTop:'3px solid #0050b3' },
  content: { backgroundColor: 'white', padding: '30px', borderRadius: '0 8px 8px 8px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' },
  sectionHeader: { color: '#333', marginBottom: '15px' },
  inputField: { width: '100%', padding: '12px', marginBottom: '15px', borderRadius: '6px', border: '1px solid #d9d9d9', fontSize:'1rem' },
  smallInputField: { width: '70px', padding: '5px', borderRadius: '4px', border: '1px solid #d9d9d9' },
  selectedExerciseCard: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px', border: '1px solid #e8e8e8', borderRadius: '6px', marginBottom: '10px', backgroundColor:'#fafafa' },
  exercisePickerGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' },
  pickerCard: { padding: '15px', border: '1px solid #bae7ff', backgroundColor: '#e6f7ff', borderRadius: '6px', textAlign: 'center', cursor:'pointer', transition:'0.2s' },
  addButton: { marginTop:'10px', backgroundColor:'#1890ff', color:'white', border:'none', padding:'5px 15px', borderRadius:'15px', cursor:'pointer' },
  createButton: { padding: '12px 30px', backgroundColor: '#0050b3', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', marginTop: '20px', fontWeight: 'bold', float:'right' },
  disabledButton: { padding: '12px 30px', backgroundColor: '#ccc', color: '#666', border: 'none', borderRadius: '6px', marginTop: '20px', float:'right', cursor:'not-allowed' },
  stepContainer: { border: '1px solid #e8e8e8', padding: '25px', borderRadius: '8px' },
  patientListContainer: { maxHeight:'300px', overflowY:'auto', border:'1px solid #eee', borderRadius:'6px', marginTop:'15px' },
  patientSelectCard: { display:'flex', alignItems:'center', padding: '12px', borderBottom: '1px solid #eee' },
  backButton: { padding: '10px 20px', backgroundColor: '#f5f5f5', border: '1px solid #ddd', borderRadius: '6px', cursor: 'pointer' },
  assignButton: { padding: '10px 25px', backgroundColor: '#52c41a', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' },
  protocolCard: { border:'1px solid #e8e8e8', padding:'20px', borderRadius:'8px', backgroundColor:'#fafafa', borderLeft:'4px solid #1890ff' }
};

export default TherapistProtocolManager;